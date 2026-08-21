import httpx
import pytest
import respx

from app.config import settings
from app.services import attach_classify, ocr, ocr_cache, ocr_tiengnoi


@pytest.mark.asyncio
async def test_fill_ocr_uses_tiengnoi_and_fill_token_limit(monkeypatch):
    captured = {}

    async def fake_tiengnoi(files, max_tokens=None):
        captured["max_tokens"] = max_tokens
        return [{"name": "form.pdf", "text": "Họ và tên: Nguyễn Văn A"}]

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "form.pdf"}])

    assert captured["max_tokens"] == settings.ocr_tiengnoi_fill_max_tokens
    assert result[0]["provider"] == "tiengnoi"
    assert ocr.resolved_label() == "tiengnoi"


@pytest.mark.asyncio
async def test_header_only_tiengnoi_result_is_reported_as_error(monkeypatch):
    async def fake_tiengnoi(files, max_tokens=None):
        return [{"name": "form.pdf", "text": "───── Trang 1/2 ─────\n───── Trang 2/2 ─────"}]

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "form.pdf"}])

    assert result[0]["provider"] == "tiengnoi"
    assert "không đọc được nội dung" in result[0]["error"]


@pytest.mark.asyncio
async def test_tiengnoi_failure_returns_per_file_errors(monkeypatch):
    async def failed_tiengnoi(files, max_tokens=None):
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", failed_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "a.jpg"}, {"name": "b.pdf"}])

    assert [item["name"] for item in result] == ["a.jpg", "b.pdf"]
    assert all(item["provider"] == "tiengnoi" for item in result)
    assert all("service unavailable" in item["error"] for item in result)


@pytest.mark.asyncio
async def test_header_only_cached_result_is_cache_miss(monkeypatch):
    files = [{"name": "form.pdf", "dataUrl": "data:application/pdf;base64,QUFB"}]
    fresh_called = False

    monkeypatch.setattr(settings, "ocr_cache_enabled", True)
    monkeypatch.setattr(ocr_cache, "content_key", lambda _value: "v2-tiengnoi:same-pdf")

    async def fake_get_many(_keys):
        return {
            "v2-tiengnoi:same-pdf": {
                "text": "───── Trang 1/2 ─────\n───── Trang 2/2 ─────",
                "provider": "tiengnoi",
            }
        }

    async def fake_uncached(_files):
        nonlocal fresh_called
        fresh_called = True
        return [{"name": "form.pdf", "text": "GIẤY ĐỀ NGHỊ", "provider": "tiengnoi"}]

    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    monkeypatch.setattr(ocr_cache, "put_many_bg", lambda _items: None)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)

    result = await ocr.ocr_per_file(files)
    assert fresh_called is True
    assert result[0]["provider"] == "tiengnoi"
    assert result[0]["text"] == "GIẤY ĐỀ NGHỊ"


@pytest.mark.asyncio
@respx.mock
async def test_tiengnoi_adapter_batches_files_and_preserves_order():
    route = respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"text": "Tệp thứ nhất"},
                    {"text": "Tệp thứ hai"},
                ]
            },
        )
    )
    files = [
        {"name": "a.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUFB"},
        {"name": "b.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QkJC"},
    ]

    result = await ocr_tiengnoi.ocr_per_file(files, max_tokens=321)

    assert [item["name"] for item in result] == ["a.jpg", "b.pdf"]
    assert [item["text"] for item in result] == ["Tệp thứ nhất", "Tệp thứ hai"]
    assert route.call_count == 1
    body = route.calls[0].request.content
    assert b'name="files"; filename="a.jpg"' in body
    assert b'name="files"; filename="b.pdf"' in body
    assert b"321" in body
    assert b"include_tokens" not in body


@pytest.mark.asyncio
@respx.mock
async def test_tiengnoi_review_uses_tokens_when_service_returns_them():
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "text": "CĂN CƯỚC",
                        "pages": [
                            {
                                "page": 0,
                                "tokens": [
                                    {
                                        "text": "CĂN",
                                        "bbox": [0.1, 0.2, 0.3, 0.4],
                                        "confidence": 0.98,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        )
    )
    files = [
        {"name": "cccd.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,QUFB"}
    ]

    result = await ocr_tiengnoi.ocr_tokens_per_file(files)

    assert result[0]["text"] == "CĂN CƯỚC"
    assert result[0]["tokens"] == [
        {"text": "CĂN", "bbox": [0.1, 0.2, 0.3, 0.4], "confidence": 0.98, "page": 0}
    ]


@pytest.mark.asyncio
async def test_attachment_classification_ocr_uses_only_tiengnoi(monkeypatch):
    captured = {}
    files = [{"name": "tai-lieu.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QUFB"}]

    async def fake_tiengnoi(items, max_tokens=None):
        captured["files"] = items
        captured["max_tokens"] = max_tokens
        return [{"name": "tai-lieu.pdf", "type": "application/pdf", "text": "TỜ KHAI"}]

    monkeypatch.setattr(attach_classify, "trim_files_for_classify", lambda items, _pages: items)
    monkeypatch.setattr(attach_classify.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)

    result = await attach_classify._ocr_trimmed(files)

    assert captured["files"] == files
    assert captured["max_tokens"] == settings.ocr_tiengnoi_max_tokens
    assert result[0]["provider"] == "tiengnoi"
    assert result[0]["text"] == "TỜ KHAI"


@pytest.mark.asyncio
async def test_attachment_classification_does_not_fallback_when_tiengnoi_fails(monkeypatch):
    files = [{"name": "tai-lieu.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QUFB"}]

    async def failed_tiengnoi(items, max_tokens=None):
        raise RuntimeError("timeout")

    monkeypatch.setattr(attach_classify, "trim_files_for_classify", lambda items, _pages: items)
    monkeypatch.setattr(attach_classify.ocr_tiengnoi, "ocr_per_file", failed_tiengnoi)

    result = await attach_classify._ocr_trimmed(files)

    assert result == [
        {
            "name": "tai-lieu.pdf",
            "type": "application/pdf",
            "text": "",
            "error": "OCR Tiếng Nói: timeout",
            "provider": "tiengnoi",
        }
    ]
