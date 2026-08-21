import json

from app.pipelines.chung_thuc_tu_choi_di_san.attach import planner
from app.pipelines.chung_thuc_tu_choi_di_san.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_tu_choi_di_san_routes_draft_and_groups_required_supporting_docs(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "van-ban-tu-choi.pdf": (
                "VĂN BẢN TỪ CHỐI NHẬN DI SẢN THỪA KẾ\n"
                "Tôi từ chối nhận phần di sản do ông Nguyễn Văn A để lại.\n"
                "Theo Giấy chứng nhận quyền sử dụng đất số BC 466500 và Trích lục khai tử số 37/2025/TLKT.\n"
                "Căn cước công dân số 012173002914."
            ),
            "so-do.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 77, tờ bản đồ số 49.",
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012173002914\nIDVNM173002914",
            "trich-luc-khai-tu.pdf": "TRÍCH LỤC KHAI TỬ\nNgười chết: Nguyễn Văn A\nNgày chết: 24/08/2025",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 1, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
                {"index": 2, "type": "identity_document", "title": "Căn cước công dân"},
                {"index": 3, "type": "death_proof", "title": "Trích lục khai tử"},
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [_file("van-ban-tu-choi.pdf"), _file("so-do.pdf"), _file("cccd.pdf"), _file("trich-luc-khai-tu.pdf")],
        {},
        {"request_id": "req_tu_choi_di_san"},
    )
    items = res["attachments"]

    assert len(items) == 2
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == "+ Dự thảo văn bản từ chối nhận di sản;"
    assert items[0]["documentName"] == "Văn bản từ chối nhận di sản"
    assert items[0]["sourceFileIndexes"] == [0]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert "giấy chứng nhận quyền sở hữu, quyền sử dụng" in items[1]["componentName"]
    assert items[1]["documentName"] == "Giấy tờ kèm theo hồ sơ từ chối nhận di sản"
    assert items[1]["sourceFileIndexes"] == [1, 2, 3]
    assert not res["errors"]

    by_name = {entry["fileName"]: entry for entry in res["extracted"]["classified"]}
    assert by_name["van-ban-tu-choi.pdf"]["docType"] == "refusal_draft"
    assert by_name["so-do.pdf"]["docType"] == "asset_ownership_proof"
    assert by_name["cccd.pdf"]["docType"] == "identity_document"
    assert by_name["trich-luc-khai-tu.pdf"]["docType"] == "death_proof"


async def test_tu_choi_di_san_identity_only_still_goes_to_required_row2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "can-cuoc.pdf",
            "text": "CĂN CƯỚC\nSố định danh cá nhân: 025085013037\nHọ tên: TRẦN THANH BÌNH",
            "provider": "tiengnoi",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("can-cuoc.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "existing"
    assert item["componentIndex"] == 2
    assert item["documentName"] == "Căn cước công dân"


async def test_tu_choi_di_san_authorization_adds_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN\nBên ủy quyền, bên được ủy quyền.", "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": "Tài liệu khác"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("uy-quyen.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentName"] == "Văn bản ủy quyền"
    assert item["needsAddComponent"] is True


def test_tu_choi_di_san_registry_is_attach_only():
    key = "chung-thuc-tu-choi-nhan-di-san"
    proc = get_procedure(key)

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert "GCN/CCCD/trích lục khai tử" in proc["uploadHint"]
    assert get_pipeline(key) is None
    assert get_attach_pipeline(key) is not None


def test_tu_choi_di_san_prompt_uses_ocr_text_only():
    assert "refusal_draft" in SYSTEM_PROMPT
    assert "death_proof" in SYSTEM_PROMPT
    assert "Dòng 2 nhận và gộp chung" in SYSTEM_PROMPT
    assert "VĂN BẢN TỪ CHỐI NHẬN DI SẢN" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "van-ban-tu-choi.pdf",
            "text": "VĂN BẢN TỪ CHỐI NHẬN DI SẢN",
        }
    ])

    assert "ocrText" in user_prompt
    assert "VĂN BẢN TỪ CHỐI NHẬN DI SẢN" in user_prompt
    assert "van-ban-tu-choi.pdf" not in user_prompt
    assert "fileName" not in user_prompt
