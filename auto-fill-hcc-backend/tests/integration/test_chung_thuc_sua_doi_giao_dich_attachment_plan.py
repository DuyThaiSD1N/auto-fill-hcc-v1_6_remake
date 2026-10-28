import base64
import json

from app.pipelines.chung_thuc_sua_doi_giao_dich.attach import planner
from app.pipelines.chung_thuc_sua_doi_giao_dich.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name):
    # Nội dung giả theo tên: tệp khác tên là tệp khác, cùng tên là tệp chọn trùng.
    data = base64.b64encode(name.encode()).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="doc")


async def test_sua_doi_giao_dich_moi_file_mot_dong_khong_gop(monkeypatch):
    """LLM quyết loại; mỗi file đính nguyên một dòng — dự thảo STT1, giao dịch cũ STT2, còn lại thêm mới."""
    async def fake_ocr_per_file(files):
        texts = {
            "van-ban-huy-bo.pdf": "VĂN BẢN HỦY BỎ HỢP ĐỒNG TẶNG CHO",
            "gcn-qsd.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT",
            "hop-dong-cu.pdf": "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\nLỜI CHỨNG\nSố chứng thực 123.",
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012345678901",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "modification_draft", "title": "Văn bản hủy bỏ hợp đồng tặng cho"},
                {"index": 1, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 2, "type": "certified_transaction", "title": "Hợp đồng tặng cho đã chứng thực"},
                {"index": 3, "type": "identity_document", "title": "Căn cước công dân"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [_file("van-ban-huy-bo.pdf"), _file("gcn-qsd.pdf"), _file("hop-dong-cu.pdf"), _file("cccd.pdf")],
        {},
        {"request_id": "req_sua_doi_giao_dich"},
    )
    items = {item["fileIndex"]: item for item in res["attachments"]}

    assert len(items) == 4
    assert all(not item.get("sourceFileIndexes") for item in items.values()), "không gộp PDF"
    assert (items[0]["target"], items[0]["componentIndex"]) == ("existing", 1)
    assert "Dự thảo giao dịch sửa đổi" in items[0]["componentName"]
    assert (items[2]["target"], items[2]["componentIndex"]) == ("existing", 2)
    assert items[2]["componentName"] == "Giao dịch đã được chứng thực"
    assert items[1]["target"] == "new" and items[1]["componentName"] == "Giấy chứng nhận quyền sử dụng đất"
    assert items[3]["target"] == "new" and items[3]["componentName"] == "Căn cước công dân"
    assert {entry["source"] for entry in res["extracted"]["classified"]} == {"llm"}
    assert not res["errors"]


async def test_sua_doi_giao_dich_hop_dong_cu_co_dieu_khoan_sua_doi_khong_bi_rule_de(monkeypatch):
    """Hợp đồng cũ có điều khoản "sửa đổi, bổ sung hợp đồng": LLM nói giao dịch cũ thì phải vào STT2."""
    async def fake_ocr_per_file(files):
        texts = {
            "hd-cu.pdf": (
                "HỢP ĐỒNG THẾ CHẤP QUYỀN SỬ DỤNG ĐẤT\n"
                "Điều 9. Sửa đổi, bổ sung hợp đồng: mọi sửa đổi bổ sung hợp đồng phải lập thành văn bản.\n"
                "Lời chứng của người thực hiện chứng thực. Số chứng thực 15."
            ),
            "vb-sua-doi.pdf": "VĂN BẢN SỬA ĐỔI, BỔ SUNG HỢP ĐỒNG THẾ CHẤP",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "certified_transaction", "title": "Hợp đồng thế chấp quyền sử dụng đất"},
                {"index": 1, "type": "modification_draft", "title": "Văn bản sửa đổi bổ sung hợp đồng thế chấp"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("hd-cu.pdf"), _file("vb-sua-doi.pdf")], {}, None)
    items = {item["fileIndex"]: item for item in res["attachments"]}

    assert len(items) == 2
    assert items[0]["componentIndex"] == 2
    assert items[1]["componentIndex"] == 1
    assert all(not item.get("sourceFileIndexes") for item in items.values())


async def test_sua_doi_giao_dich_llm_loi_moi_dung_rule_du_phong(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "hop-dong-tang-cho-cu.pdf",
            "text": "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\nLỜI CHỨNG của người thực hiện chứng thực. Số chứng thực 88.",
            "provider": "tiengnoi",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("hop-dong-tang-cho-cu.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["componentIndex"] == 2
    assert res["extracted"]["classified"][0]["docType"] == "certified_transaction"
    assert res["extracted"]["classified"][0]["source"] == "rule"


async def test_sua_doi_giao_dich_khong_co_du_thao_thi_giay_to_tai_san_vao_stt1(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "OCR", "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "certified_transaction", "title": "Hợp đồng tặng cho"},
                {"index": 1, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("hd.pdf"), _file("so-do.pdf")], {}, None)
    items = {item["fileIndex"]: item for item in res["attachments"]}

    assert items[0]["componentIndex"] == 2
    assert items[1]["componentIndex"] == 1


async def test_sua_doi_giao_dich_unknown_document_adds_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "phieu-hen.pdf", "text": "PHIẾU HẸN TRẢ KẾT QUẢ", "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": "Phiếu hẹn"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("phieu-hen.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentName"] == "Phiếu hẹn"
    assert item["needsAddComponent"] is True
    assert not res["errors"]


def test_sua_doi_giao_dich_registry_is_attach_only():
    key = "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich"
    proc = get_procedure(key)

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert "không gộp" in proc["uploadHint"]
    assert get_pipeline(key) is None
    assert get_attach_pipeline(key) is not None


def test_sua_doi_giao_dich_prompt_uses_ocr_text_only():
    assert "modification_draft" in SYSTEM_PROMPT
    assert "certified_transaction" in SYSTEM_PROMPT
    assert "asset_ownership_proof" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "VĂN BẢN HỦY BỎ HỢP ĐỒNG" in SYSTEM_PROMPT
    assert "giao dịch/hợp đồng cũ đã được chứng thực" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "van-ban-huy-bo.pdf",
            "text": "VĂN BẢN HỦY BỎ HỢP ĐỒNG TẶNG CHO",
        }
    ])

    assert "ocrText" in user_prompt
    assert "VĂN BẢN HỦY BỎ HỢP ĐỒNG TẶNG CHO" in user_prompt
    assert "van-ban-huy-bo.pdf" not in user_prompt
    assert "fileName" not in user_prompt


async def test_sua_doi_giao_dich_tep_chon_hai_lan_chi_dinh_mot_lan(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "VĂN BẢN HỦY GIAO DỊCH TẶNG CHO", "provider": "tiengnoi"} for f in files]

    seen = {}

    async def fake_chat(messages, max_tokens, enable_thinking):
        seen["prompt"] = messages[-1]["content"]
        return json.dumps({"documents": [{"index": 0, "type": "modification_draft", "title": "Văn bản hủy giao dịch"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("du-thao.pdf"), _file("du-thao.pdf")], {}, None)

    assert [item["fileIndex"] for item in res["attachments"]] == [0]
    assert res["attachments"][0]["componentIndex"] == 1
    assert any("Đã bỏ 1 tệp trùng" in err for err in res["errors"])
    assert '"index": 1' not in seen["prompt"], "tệp trùng không gửi LLM"


async def test_sua_doi_giao_dich_dong_1_dung_truoc_dong_2_du_tep_giao_dich_cu_chon_truoc(monkeypatch):
    """Tên dòng 2 nằm trọn trong chữ dòng 1: engine tìm dòng trống theo tên từ trên xuống, nên mục dòng 1
    phải đi trước, kể cả khi cán bộ chọn hợp đồng cũ trước văn bản sửa đổi."""
    async def fake_ocr_per_file(files):
        texts = {"hd-cu.pdf": "HỢP ĐỒNG THẾ CHẤP", "sua-doi.pdf": "VĂN BẢN SỬA ĐỔI, BỔ SUNG HỢP ĐỒNG THẾ CHẤP"}
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "certified_transaction", "title": "Hợp đồng thế chấp"},
            {"index": 1, "type": "modification_draft", "title": "Văn bản sửa đổi bổ sung hợp đồng thế chấp"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("hd-cu.pdf"), _file("sua-doi.pdf")], {}, {"request_id": "req_thu_tu"})

    assert [(item["fileIndex"], item["componentIndex"]) for item in res["attachments"]] == [(1, 1), (0, 2)]
