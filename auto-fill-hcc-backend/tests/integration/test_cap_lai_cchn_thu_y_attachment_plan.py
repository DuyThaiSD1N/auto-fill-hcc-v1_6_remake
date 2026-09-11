"""Attachment plan cho "Cấp lại Chứng chỉ hành nghề thú y" — bảng 1 dòng Đơn 03.HNTY, engine attp-row."""

import json

from app.pipelines.cap_lai_CCHN_thu_y.attach import planner as cchn_thu_y_attach
from app.process.schemas import FileItem

_DON_TEXT = (
    "ĐƠN ĐĂNG KÝ CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ THÚ Y\n"
    "Kính gửi: Sở Nông nghiệp và Môi trường tỉnh Lai Châu\n"
    "Bằng cấp chuyên môn: Bác sĩ Thú y\nNGƯỜI LÀM ĐƠN"
)
_CCHN_TEXT = "CHỨNG CHỈ HÀNH NGHỀ THÚ Y\nSố đăng ký: 123/CCHN-TY\nChứng chỉ có giá trị đến ngày 31/12/2026"
_CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901\nNơi thường trú: Xã Tân Uyên, Tỉnh Lai Châu"


def _pdf(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _jpg(name: str) -> FileItem:
    return FileItem(name=name, type="image/jpeg", dataUrl="data:image/jpeg;base64,AAA", role="doc")


async def test_cchn_thu_y_attach_maps_don_to_row_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": _DON_TEXT},
            {"name": "cccd.jpg", "text": _CCCD_TEXT},
            {"name": "cchn-cu.jpg", "text": _CCHN_TEXT},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "don_cap_lai"},
                {"index": 1, "docType": "cccd"},
                {"index": 2, "docType": "cchn_cu"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cchn_thu_y_attach.client, "chat", fake_chat)

    res = await cchn_thu_y_attach.plan(
        [_pdf("don.pdf"), _jpg("cccd.jpg"), _jpg("cchn-cu.jpg")],
        {},
        {"procedure": "cap-lai-chung-chi-hanh-nghe-thu-y"},
    )

    items = res["attachments"]
    by_file = {item["fileName"]: item for item in items}
    # CCCD chỉ dùng ở bước thông tin → không có dòng nào để đính.
    assert "cccd.jpg" not in by_file
    assert set(by_file) == {"don.pdf", "cchn-cu.jpg"}
    # Form chỉ có 1 dòng → mọi giấy tờ còn lại vào dòng đó, loại bản "Bản chính".
    for item in items:
        assert item["target"] == "attp-row"
        assert item["componentName"] == "Đơn đăng ký cấp lại"
        assert item["loaiBan"] == "Bản chính"
        assert item["needsAddComponent"] is False
    assert by_file["don.pdf"]["documentName"].startswith("Đơn đăng ký cấp lại Chứng chỉ hành nghề thú y")
    # Giấy tờ phụ giữ TÊN GỐC để không trùng tên tài liệu trên dòng.
    assert by_file["cchn-cu.jpg"]["documentName"] == "cchn-cu.jpg"
    assert res["errors"] == []


async def test_cchn_thu_y_attach_rule_fallback_and_photo_detection(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": _DON_TEXT},
            {"name": "anh4x6.jpg", "text": ""},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cchn_thu_y_attach.client, "chat", fake_chat)

    res = await cchn_thu_y_attach.plan([_pdf("don.pdf"), _jpg("anh4x6.jpg")], {}, {})

    by_file = {item["fileName"]: item for item in res["attachments"]}
    assert by_file["don.pdf"]["detectedType"] == "don_cap_lai"
    # Ảnh 4x6 không OCR ra chữ → nhận là ảnh chân dung, không cảnh báo "không xác định được loại".
    assert by_file["anh4x6.jpg"]["detectedType"] == "anh_the"
    assert not any("Không xác định được loại giấy tờ" in err for err in res["errors"])
    assert any("llm down" in err for err in res["errors"])


async def test_cchn_thu_y_attach_warns_when_don_missing(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cchn-cu.jpg", "text": _CCHN_TEXT}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "cchn_cu"}]}, ensure_ascii=False)

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(cchn_thu_y_attach.client, "chat", fake_chat)

    res = await cchn_thu_y_attach.plan([_jpg("cchn-cu.jpg")], {}, {})

    assert any("Mẫu 03.HNTY" in err for err in res["errors"])
