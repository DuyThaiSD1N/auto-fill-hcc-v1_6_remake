"""Plan đính kèm bước 3 cho "Thay đổi, cải chính hộ tịch"."""
import json

from app.pipelines.thay_doi_ho_tich.attach import planner
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _by_file(items):
    return {it["fileName"]: it for it in items}


async def test_routes_ho_tich_authorization_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "tlkh.pdf", "text": "TRÍCH LỤC GHI CHÚ KẾT HÔN"},
            {"name": "uyquyen.pdf", "text": "GIẤY ỦY QUYỀN"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "ho_tich_doc", "documentName": "Trích lục kết hôn"},
            {"index": 1, "type": "authorization", "documentName": "Văn bản ủy quyền"},
            {"index": 2, "type": "identity", "documentName": "Căn cước công dân"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("tlkh.pdf"), _file("uyquyen.pdf"), _file("cccd.pdf")], {}, {"request_id": "r1"}
    )
    items = _by_file(res["attachments"])

    # Giấy tờ hộ tịch → ô có sẵn STT2.
    assert items["tlkh.pdf"]["target"] == "existing"
    assert items["tlkh.pdf"]["componentIndex"] == 2
    # Ủy quyền → ô có sẵn STT3.
    assert items["uyquyen.pdf"]["target"] == "existing"
    assert items["uyquyen.pdf"]["componentIndex"] == 3
    # CCCD → thành phần hồ sơ MỚI.
    assert items["cccd.pdf"]["target"] == "new"
    assert items["cccd.pdf"]["needsAddComponent"] is True
    assert items["cccd.pdf"]["componentName"] == "Căn cước công dân"


async def test_birth_cert_goes_to_existing_slot_2(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "gks.pdf", "text": "GIẤY KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "ho_tich_doc", "documentName": "Giấy khai sinh"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan_thay_doi_ho_tich_attachments([_file("gks.pdf")], {}, None)
    it = res["attachments"][0]
    assert it["target"] == "existing"
    assert it["componentIndex"] == 2
    assert it["documentName"] == "Giấy khai sinh"


async def test_dedup_same_type_names(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "a.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}, {"name": "b.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "identity", "documentName": "Căn cước công dân"},
            {"index": 1, "type": "identity", "documentName": "Căn cước công dân"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan_thay_doi_ho_tich_attachments([_file("a.pdf"), _file("b.pdf")], {}, None)
    names = [it["documentName"] for it in res["attachments"]]
    assert len(set(names)) == 2  # không trùng tên


def test_procedure_has_attachment_step():
    proc = get_procedure("thay-doi-cai-chinh-ho-tich")
    assert proc["hasAttachmentStep"] is True
