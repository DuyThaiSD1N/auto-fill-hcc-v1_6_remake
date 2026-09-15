import pytest

from app.config import settings
from app.services import ocr, ocr_tiengnoi


@pytest.mark.asyncio
async def test_fill_ocr_always_uses_tiengnoi(monkeypatch):
    captured = {}

    async def fake_tiengnoi(files, max_tokens=None):
        captured["files"] = files
        captured["max_tokens"] = max_tokens
        return [{"name": "a.pdf", "text": "nội dung"}]

    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "a.pdf"}])

    assert captured["max_tokens"] == settings.ocr_tiengnoi_fill_max_tokens
    assert result[0]["provider"] == "tiengnoi"
    assert ocr.resolved_label() == "tiengnoi"


@pytest.mark.asyncio
async def test_classify_ocr_uses_short_tiengnoi_limit_when_cache_is_off(monkeypatch):
    """Cache tắt: phân loại không dùng lại được nên vẫn chạy trần token ngắn cho nhanh."""
    captured = {}

    async def fake_tiengnoi(files, max_tokens=None):
        captured["max_tokens"] = max_tokens
        return [{"name": "a.jpg", "text": "căn cước"}]

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "a.jpg"}], classify=True)

    assert captured["max_tokens"] == settings.ocr_tiengnoi_max_tokens
    assert result[0]["provider"] == "tiengnoi"


@pytest.mark.asyncio
async def test_classify_ocr_uses_fill_limit_when_cache_is_on(monkeypatch):
    """Cache bật: phân loại và trích xuất DÙNG CHUNG một lượt OCR nên phải chạy trần đầy đủ.

    Chạy trần ngắn rồi cache lại là bẫy: text bị cắt giữa chừng, lượt trích xuất dùng vào sẽ
    mất chữ ở những trang cuối mà không ai biết.
    """
    captured = {}

    async def fake_tiengnoi(files, max_tokens=None):
        captured["max_tokens"] = max_tokens
        return [{"name": "a.jpg", "text": "căn cước"}]

    monkeypatch.setattr(settings, "ocr_cache_enabled", True)
    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "a.jpg"}], classify=True)

    assert captured["max_tokens"] == settings.ocr_tiengnoi_fill_max_tokens
    assert result[0]["provider"] == "tiengnoi"


@pytest.mark.asyncio
async def test_review_tokens_do_not_use_another_provider(monkeypatch):
    async def fake_tokens(files, max_tokens=None):
        return [{"name": "a.jpg", "text": "A", "tokens": []}]

    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_tokens_per_file", fake_tokens)
    result = await ocr.ocr_tokens_per_file([{"name": "a.jpg"}])

    assert result == [{"name": "a.jpg", "text": "A", "tokens": [], "provider": "tiengnoi"}]


@pytest.mark.asyncio
async def test_tiengnoi_failure_returns_per_file_errors_without_fallback(monkeypatch):
    async def failed_tiengnoi(files, max_tokens=None):
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(ocr.ocr_tiengnoi, "ocr_per_file", failed_tiengnoi)
    result = await ocr.ocr_per_file([{"name": "a.jpg"}, {"name": "b.pdf"}])

    assert [item["name"] for item in result] == ["a.jpg", "b.pdf"]
    assert all(item["provider"] == "tiengnoi" for item in result)
    assert all(item["text"] == "" and "service unavailable" in item["error"] for item in result)


@pytest.mark.asyncio
async def test_tiengnoi_doc_file_tu_path_va_dong_handle_sau_khi_gui(monkeypatch, tmp_path):
    path = tmp_path / "upload_sessions" / "HS-TEST" / "hoso.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"noi-dung-pdf")
    captured = {}
    monkeypatch.setattr(ocr_tiengnoi.settings, "storage_dir", str(tmp_path))

    async def fake_post(decoded, max_tokens=None, *, include_tokens=False):
        name, source, mime = decoded[0]
        captured.update(name=name, source=source, mime=mime, content=source.read())
        return {"results": [{"ok": True, "text": "NỘI DUNG"}]}

    monkeypatch.setattr(ocr_tiengnoi, "_post", fake_post)
    result = await ocr_tiengnoi.ocr_per_file([{
        "name": "hoso.pdf",
        "type": "application/pdf",
        "path": str(path),
    }])

    assert result[0]["text"] == "NỘI DUNG"
    assert captured["content"] == b"noi-dung-pdf"
    assert not isinstance(captured["source"], bytes)
    assert captured["source"].closed is True


@pytest.mark.asyncio
async def test_tiengnoi_tu_choi_path_ngoai_kho_upload(monkeypatch, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    monkeypatch.setattr(ocr_tiengnoi.settings, "storage_dir", str(tmp_path / "storage"))

    with pytest.raises(ValueError, match="ngoài kho upload-session"):
        await ocr_tiengnoi.ocr_per_file([{
            "name": "secret.txt",
            "type": "text/plain",
            "path": str(outside),
        }])


@pytest.mark.asyncio
async def test_tiengnoi_van_ho_tro_data_url_cu(monkeypatch):
    captured = {}

    async def fake_post(decoded, max_tokens=None, *, include_tokens=False):
        captured["decoded"] = decoded
        return {"results": [{"ok": True, "text": "A"}]}

    monkeypatch.setattr(ocr_tiengnoi, "_post", fake_post)
    result = await ocr_tiengnoi.ocr_per_file([{
        "name": "a.txt",
        "type": "text/plain",
        "dataUrl": "data:text/plain;base64,QUJD",
    }])

    assert result[0]["text"] == "A"
    assert captured["decoded"] == [("a.txt", b"ABC", "text/plain")]
