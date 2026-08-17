"""Đính kèm khai tử: giấy báo tử vào Ô CÓ SẴN STT 2, CCCD/tờ khai giấy thêm thành phần mới."""

import json

from app.pipelines.khai_tu.attach import planner as khai_tu
from app.process.schemas import FileItem


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_khai_tu_attachment_plan_routes_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN 040203015844"},
            {"name": "giay-bao-tu.pdf", "text": "GIẤY BÁO TỬ Số 12/GBT"},
            {"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI TỬ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "requester_identity", "title": "Căn cước công dân"},
            {"index": 1, "type": "death_notice", "title": "Giấy báo tử"},
            {"index": 2, "type": "paper_declaration", "title": "Tờ khai đăng ký khai tử"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    res = await khai_tu.plan_khai_tu_attachments(
        [_file("cccd.pdf"), _file("giay-bao-tu.pdf"), _file("to-khai.pdf")], {}, None)
    items = res["attachments"]

    # CCCD người yêu cầu → thành phần MỚI.
    assert items[0]["target"] == "new" and items[0]["needsAddComponent"] is True
    assert items[0]["documentName"] == "Căn cước công dân người yêu cầu"
    # Giấy báo tử → ô CÓ SẴN STT 2 (khớp trang thongtin/khai tử đính kèm).
    assert items[1]["target"] == "existing" and items[1]["componentIndex"] == 2
    assert "Giấy báo tử hoặc giấy tờ thay Giấy báo tử" in items[1]["componentName"]
    # Tờ khai bản giấy → thành phần mới.
    assert items[2]["target"] == "new"
    assert items[2]["documentName"] == "Tờ khai đăng ký khai tử bản giấy"
    assert not res["errors"]


async def test_khai_tu_attachment_plan_existing_rows_3_va_5(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "chung-cu.pdf", "text": "Giấy xác nhận sự kiện chết"},
            {"name": "noi-chet.pdf", "text": "Xác nhận nơi phát hiện thi thể"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "death_event_proof", "title": "Giấy xác nhận sự kiện chết"},
            {"index": 1, "type": "death_place_proof", "title": "Xác nhận nơi phát hiện thi thể"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    res = await khai_tu.plan_khai_tu_attachments([_file("chung-cu.pdf"), _file("noi-chet.pdf")], {}, None)
    items = res["attachments"]

    assert items[0]["componentIndex"] == 3 and "chứng minh sự kiện chết" in items[0]["componentName"]
    assert items[1]["componentIndex"] == 5 and "nơi phát hiện thi thể" in items[1]["componentName"]


async def test_khai_tu_attachment_plan_canh_bao_cccd_lech_nguoi_yeu_cau(monkeypatch):
    """CCCD upload không chứa số định danh người yêu cầu từ bước kê khai → cảnh báo."""
    async def fake_ocr_per_file(files):
        return [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN 111111111111"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "requester_identity"}]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    session = {"fields": [{"name": "SoDinhDanhC", "value": "040203015844"}]}
    res = await khai_tu.plan_khai_tu_attachments([_file("cccd.pdf")], {}, session)

    assert any("không khớp số định danh" in e for e in res["errors"])
