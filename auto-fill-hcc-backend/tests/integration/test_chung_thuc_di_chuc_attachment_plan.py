import json

from app.pipelines.chung_thuc_di_chuc.attach import planner
from app.pipelines.chung_thuc_di_chuc.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_chung_thuc_di_chuc_attachment_plan_merges_identity_into_will(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "di-chuc.pdf", "text": "DỰ THẢO DI CHÚC\nNgười lập di chúc định đoạt tài sản"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844"},
            {"name": "so-do.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 12"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("di-chuc.pdf"), _file("cccd.pdf"), _file("so-do.pdf")], {}, None)
    items = res["attachments"]

    assert len(items) == 2
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == "+ Dự thảo di chúc;"
    assert items[0]["documentName"] == "Dự thảo di chúc kèm căn cước công dân"
    assert items[0]["sourceFileIndexes"] == [0, 1]
    assert items[0]["needsAddComponent"] is False

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert "giấy chứng nhận quyền sở hữu, quyền sử dụng" in items[1]["componentName"]
    assert items[1]["documentName"] == "Giấy tờ sở hữu tài sản"
    assert items[1]["sourceFileIndexes"] == [2]
    assert items[1]["needsAddComponent"] is False

    identity_meta = next(x for x in res["extracted"]["classified"] if x["fileName"] == "cccd.pdf")
    assert identity_meta["target"] == "merged"
    assert identity_meta["mergedIntoFileIndex"] == 0


async def test_chung_thuc_di_chuc_multiple_identities_merge_into_will(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "di-chuc.pdf", "text": "DI CHÚC\nNGƯỜI LẬP DI CHÚC"},
            {"name": "cccd-nguoi-lap.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012345678901"},
            {"name": "cccd-nguoi-huong.pdf", "text": "THẺ CĂN CƯỚC\nSố định danh cá nhân: 098765432109"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan(
        [_file("di-chuc.pdf"), _file("cccd-nguoi-lap.pdf"), _file("cccd-nguoi-huong.pdf")],
        {},
        None,
    )
    items = res["attachments"]

    assert len(items) == 1
    assert items[0]["componentIndex"] == 1
    assert items[0]["sourceFileIndexes"] == [0, 1, 2]
    assert items[0]["documentName"] == "Dự thảo di chúc kèm căn cước công dân"


async def test_chung_thuc_di_chuc_asset_plus_identity_combined_file_goes_to_asset_row(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "ho-so-gop.pdf",
                "text": (
                    "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân: 040203015844\n"
                    "GIẤY CHỨNG NHẬN ĐĂNG KÝ XE MÔ TÔ"
                ),
            }
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{"index": 0, "type": "identity_document", "title": "Căn cước công dân"}]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("ho-so-gop.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "existing"
    assert item["componentIndex"] == 2
    assert item["needsAddComponent"] is False


async def test_chung_thuc_di_chuc_identity_without_will_falls_back_to_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("cccd.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["componentName"] == "Căn cước công dân"
    assert item["sourceFileIndexes"] == [0]


async def test_chung_thuc_di_chuc_will_with_asset_references_stays_on_will_row(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "Du_thao_Di_chuc.pdf",
                "text": (
                    "DI CHÚC\n"
                    "Tôi lập bản di chúc này để định đoạt tài sản của tôi sau khi tôi qua đời.\n"
                    "Điều 1. Tài sản để lại gồm quyền sử dụng đất và tài sản gắn liền với đất "
                    "theo Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở số ...; "
                    "xe ô tô theo Giấy đăng ký xe số ...\n"
                    "NGƯỜI LẬP DI CHÚC\nNGUYỄN VĂN A"
                ),
            }
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "index": 0,
                    "type": "asset_ownership_proof",
                    "title": "Giấy chứng nhận quyền sử dụng đất",
                }
            ]
        })

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("Du_thao_Di_chuc.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "existing"
    assert item["componentIndex"] == 1
    assert item["componentName"] == "+ Dự thảo di chúc;"
    assert item["documentName"] == "Dự thảo di chúc"
    assert item["needsAddComponent"] is False
    assert res["extracted"]["classified"][0]["type"] == "will_draft"
    assert res["extracted"]["classified"][0]["source"] == "rule"


async def test_chung_thuc_di_chuc_unknown_document_is_skipped(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "phieu-hen.pdf", "text": "PHIẾU HẸN TRẢ KẾT QUẢ"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "other", "title": "Phiếu hẹn"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("phieu-hen.pdf")], {}, None)

    assert res["attachments"] == []
    assert any("đã bỏ qua" in err for err in res["errors"])


def test_chung_thuc_di_chuc_procedure_is_attach_only():
    proc = get_procedure("chung-thuc-di-chuc")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert "Dự thảo di chúc" in proc["uploadHint"]
    assert "BE yêu cầu FE gộp chúng vào PDF dự thảo di chúc" in proc["uploadHint"]
    assert get_pipeline("chung-thuc-di-chuc") is None
    assert get_attach_pipeline("chung-thuc-di-chuc") is not None


def test_chung_thuc_di_chuc_prompt_uses_ocr_text_only():
    assert "will_draft" in SYSTEM_PROMPT
    assert "asset_ownership_proof" in SYSTEM_PROMPT
    assert "identity_document" in SYSTEM_PROMPT
    assert "Dòng 1 chỉ nhận dự thảo di chúc" in SYSTEM_PROMPT
    assert "gộp các file identity_document vào cùng PDF của will_draft" in SYSTEM_PROMPT
    assert "không biến nó thành asset_ownership_proof" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "di-chuc.pdf",
            "text": "DỰ THẢO DI CHÚC",
        }
    ])

    assert "ocrText" in prompt
    assert "DỰ THẢO DI CHÚC" in prompt
    assert "di-chuc.pdf" not in prompt
    assert "fileName" not in prompt
