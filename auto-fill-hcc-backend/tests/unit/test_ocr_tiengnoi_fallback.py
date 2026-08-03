import pytest

from app.services import ocr
from app.services import ocr_cache


@pytest.mark.asyncio
async def test_tiengnoi_page_headers_only_fall_back_to_gemini(monkeypatch):
    files = [{"name": "quynh.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}]

    async def fake_tiengnoi(_files, max_tokens):
        return [{
            "name": "quynh.pdf",
            "type": "application/pdf",
            "text": "───── Trang 1/2 ─────\n\n\n───── Trang 2/2 ─────\n",
        }]

    async def fake_gemini(_files):
        return [{
            "name": "quynh.pdf",
            "type": "application/pdf",
            "text": "GIẤY ĐỀ NGHỊ Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh",
        }]

    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(ocr.ocr_gemini, "ocr_per_file", fake_gemini)
    result = await ocr._tiengnoi_then_gemini(files)

    assert result[0]["provider"] == "gemini"
    assert result[0]["text"].startswith("GIẤY ĐỀ NGHỊ")


@pytest.mark.asyncio
async def test_tiengnoi_real_content_is_not_replaced(monkeypatch):
    files = [{"name": "form.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}]
    gemini_called = False

    async def fake_tiengnoi(_files, max_tokens):
        return [{
            "name": "form.pdf",
            "type": "application/pdf",
            "text": "───── Trang 1/1 ─────\nHọ và tên: Nguyễn Văn A",
        }]

    async def fake_gemini(_files):
        nonlocal gemini_called
        gemini_called = True
        return []

    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(ocr.ocr_gemini, "ocr_per_file", fake_gemini)
    result = await ocr._tiengnoi_then_gemini(files)

    assert result[0]["provider"] == "tiengnoi"
    assert "Nguyễn Văn A" in result[0]["text"]
    assert gemini_called is False


@pytest.mark.asyncio
async def test_header_only_cached_result_is_treated_as_cache_miss(monkeypatch):
    files = [{"name": "quynh.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}]
    fresh_called = False

    monkeypatch.setattr(ocr.settings, "ocr_cache_enabled", True)
    monkeypatch.setattr(ocr_cache, "content_key", lambda _value: "same-pdf")

    async def fake_get_many(_keys):
        return {"same-pdf": {"text": "───── Trang 1/2 ─────\n───── Trang 2/2 ─────", "provider": "tiengnoi"}}

    async def fake_uncached(_files, _provider):
        nonlocal fresh_called
        fresh_called = True
        return [{"name": "quynh.pdf", "type": "application/pdf", "text": "GIẤY ĐỀ NGHỊ", "provider": "gemini"}]

    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    monkeypatch.setattr(ocr_cache, "put_many_bg", lambda _items: None)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)

    result = await ocr.ocr_per_file(files)
    assert fresh_called is True
    assert result[0]["provider"] == "gemini"
    assert result[0]["text"] == "GIẤY ĐỀ NGHỊ"
