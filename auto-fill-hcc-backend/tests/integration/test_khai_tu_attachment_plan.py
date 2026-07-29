import json

from app.pipelines.khai_tu.attach import planner as khai_tu
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_khai_tu_test",
        "procedure": "khai-tu",
        "fields": [
            {"name": "SoDinhDanhC", "value": "040203015844"},
            {"name": "HoVaTenC", "value": "VŨ ĐÌNH THIẾT"},
        ],
    }


async def test_khai_tu_attachment_plan_routes_existing_default_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "giay-bao-tu.pdf", "text": "GIẤY BÁO TỬ"},
            {"name": "su-kien-chet.pdf", "text": "GIẤY TỜ CHỨNG MINH SỰ KIỆN CHẾT"},
            {"name": "noi-chet.pdf", "text": "GIẤY TỜ CHỨNG MINH NƠI PHÁT HIỆN THI THỂ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "death_notice", "title": "Giấy báo tử"},
                {"index": 1, "type": "death_event_proof", "title": "Giấy tờ chứng minh sự kiện chết"},
                {"index": 2, "type": "death_place_proof", "title": "Giấy tờ chứng minh nơi phát hiện thi thể"},
            ]
        })

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    res = await khai_tu.plan_khai_tu_attachments(
        [_file("giay-bao-tu.pdf"), _file("su-kien-chet.pdf"), _file("noi-chet.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Giấy báo tử" in items[0]["componentName"]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "chứng minh sự kiện chết" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 5
    assert "nơi phát hiện thi thể" in items[2]["componentName"]


async def test_khai_tu_attachment_plan_adds_identity_and_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-nguoi-yc.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 040203015844"},
            {"name": "to-khai-giay.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ tên người yêu cầu"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "requester_identity", "title": "Căn cước công dân người yêu cầu"},
                {"index": 1, "type": "paper_declaration", "title": "Tờ khai đăng ký khai tử bản giấy"},
            ]
        })

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    res = await khai_tu.plan_khai_tu_attachments(
        [_file("cccd-nguoi-yc.pdf"), _file("to-khai-giay.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "new"
    assert items[0]["componentIndex"] is None
    assert items[0]["documentName"] == "Căn cước công dân người yêu cầu"
    assert items[0]["componentName"] == "Căn cước công dân người yêu cầu"

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["documentName"] == "Tờ khai đăng ký khai tử bản giấy"
    assert items[1]["componentName"] == "Tờ khai đăng ký khai tử bản giấy"


async def test_khai_tu_attachment_plan_warns_identity_mismatch(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd-khac.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 025203007360"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "requester_identity", "title": "Căn cước công dân người yêu cầu"},
            ]
        })

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    res = await khai_tu.plan_khai_tu_attachments([_file("cccd-khac.pdf")], {}, _session())

    assert res["attachments"][0]["componentName"] == "Căn cước công dân người yêu cầu"
    assert any("không khớp số định danh người yêu cầu" in err for err in res["errors"])


def test_khai_tu_procedure_has_attachment_step():
    proc = get_procedure("khai-tu")

    assert proc["hasAttachmentStep"] is True
