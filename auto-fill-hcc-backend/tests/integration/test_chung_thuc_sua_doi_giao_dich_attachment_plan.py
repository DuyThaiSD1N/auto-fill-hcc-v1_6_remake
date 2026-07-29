import json

from app.pipelines.chung_thuc_sua_doi_giao_dich.attach import planner
from app.pipelines.chung_thuc_sua_doi_giao_dich.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_sua_doi_giao_dich_attachment_groups_draft_and_asset_then_routes_old_transaction(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "van-ban-huy-bo.pdf": (
                "VĂN BẢN HỦY BỎ HỢP ĐỒNG TẶNG CHO\n"
                "Các bên thống nhất hủy bỏ hợp đồng tặng cho quyền sử dụng đất đã được chứng thực."
            ),
            "gcn-qsd.pdf": (
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\n"
                "Thửa đất số 77, tờ bản đồ số 49."
            ),
            "hop-dong-cu.pdf": (
                "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\n"
                "LỜI CHỨNG\n"
                "Số chứng thực 123, quyển số chứng thực 01/2025."
            ),
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012173002914\nIDVNM173002914",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "gemini"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "certified_transaction", "title": "Hợp đồng tặng cho đã chứng thực"},
                {"index": 1, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 2, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
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
    items = res["attachments"]

    assert len(items) == 3
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert "Dự thảo giao dịch sửa đổi" in items[0]["componentName"]
    assert items[0]["documentName"] == "Dự thảo sửa đổi giao dịch và giấy tờ tài sản"
    assert items[0]["sourceFileIndexes"] == [0, 1]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert items[1]["componentName"] == "Giao dịch đã được chứng thực"
    assert items[1]["documentName"] == "Giao dịch đã được chứng thực"
    assert items[1]["sourceFileIndexes"] == [2]

    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Căn cước công dân"
    assert items[2]["needsAddComponent"] is True
    assert not res["errors"]

    assert any(
        entry["fileName"] == "van-ban-huy-bo.pdf"
        and entry["docType"] == "modification_draft"
        and entry["source"] == "rule"
        and entry["componentIndex"] == 1
        for entry in res["extracted"]["classified"]
    )


async def test_sua_doi_giao_dich_old_contract_not_misrouted_as_asset(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "hop-dong-tang-cho-cu.pdf",
            "text": (
                "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\n"
                "Bên tặng cho thửa đất số 10, tờ bản đồ số 2.\n"
                "LỜI CHỨNG của người thực hiện chứng thực. Số chứng thực 88."
            ),
            "provider": "gemini",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{"index": 0, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"}]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("hop-dong-tang-cho-cu.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["componentIndex"] == 2
    assert item["componentName"] == "Giao dịch đã được chứng thực"
    assert item["sourceFileIndexes"] == [0]
    assert res["extracted"]["classified"][0]["docType"] == "certified_transaction"
    assert res["extracted"]["classified"][0]["source"] == "rule"


async def test_sua_doi_giao_dich_user_case_routes_cancellation_asset_and_old_contract(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "thoa-thuan-huy.pdf": (
                "THỎA THUẬN HỦY HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\n"
                "THÔNG TIN HỢP ĐỒNG TẶNG CHO:\n"
                "Hợp đồng tặng cho quyền sử dụng đất được ký ngày 19/12/2025, công chứng tại Ủy ban nhân dân phường Tân Phong.\n"
                "THỎA THUẬN HỦY HỢP ĐỒNG:\n"
                "Hai bên đồng thuận hủy hợp đồng tặng cho quyền sử dụng đất số 29."
            ),
            "cccd-2-ben.pdf": (
                "CĂN CƯỚC CÔNG DÂN\n"
                "Số / No.: 012093000910\n"
                "CĂN CƯỚC CÔNG DÂN\n"
                "Số / No.: 012060000361"
            ),
            "gcn-qsd-cu.pdf": (
                "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\n"
                "ỦY BAN NHÂN DÂN Huyện Phong Thổ CHỨNG NHẬN Hộ ông Trần Văn Quí.\n"
                "Vào sổ cấp giấy chứng nhận quyền sử dụng đất số 00074 QSDĐ/747/QĐ-UB/H-UBND.\n"
                "Ngày 16 tháng 12 năm 1999 Chủ tịch UBND."
            ),
            "hop-dong-tang-cho.pdf": (
                "HỢP ĐỒNG TẶNG CHO QUYỀN SỬ DỤNG ĐẤT\n"
                "Theo Giấy chứng nhận quyền sử dụng đất số Q 086383.\n"
                "Lời chứng chứng thực hợp đồng tại Trung tâm Phục vụ hành chính công.\n"
                "Số chứng thực 29 quyển số 01 -SCT/HĐ,GD."
            ),
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "gemini"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "certified_transaction", "title": "Giao dịch đã được chứng thực"},
                {"index": 1, "type": "identity_document", "title": "Căn cước công dân"},
                {"index": 2, "type": "certified_transaction", "title": "Giao dịch đã được chứng thực"},
                {"index": 3, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("thoa-thuan-huy.pdf"),
            _file("cccd-2-ben.pdf"),
            _file("gcn-qsd-cu.pdf"),
            _file("hop-dong-tang-cho.pdf"),
        ],
        {},
        None,
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[0]["documentName"] == "Dự thảo sửa đổi giao dịch và giấy tờ tài sản"
    assert items[0]["sourceFileIndexes"] == [0, 2]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert items[1]["componentName"] == "Giao dịch đã được chứng thực"
    assert items[1]["sourceFileIndexes"] == [3]

    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Căn cước công dân"

    by_name = {entry["fileName"]: entry for entry in res["extracted"]["classified"]}
    assert by_name["thoa-thuan-huy.pdf"]["docType"] == "modification_draft"
    assert by_name["gcn-qsd-cu.pdf"]["docType"] == "asset_ownership_proof"
    assert by_name["hop-dong-tang-cho.pdf"]["docType"] == "certified_transaction"


async def test_sua_doi_giao_dich_unknown_document_adds_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "phieu-hen.pdf", "text": "PHIẾU HẸN TRẢ KẾT QUẢ", "provider": "gemini"}]

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
    assert "gộp dự thảo sửa đổi/bổ sung/hủy bỏ với giấy tờ tài sản" in proc["uploadHint"]
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
