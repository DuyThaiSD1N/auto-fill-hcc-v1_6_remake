"""Một tệp chỉ được OCR MỘT lần cho cả phân loại lẫn trích xuất.

Trước đây upload-session truyền tệp bằng ``path`` (không dựng dataUrl để khỏi nạp cả file vào
RAM) nên lượt OCR lúc nhận tệp không có khóa cache. Lượt trích xuất sau đó gửi dataUrl của ĐÚNG
tệp ấy lại thành cache miss → OCR lần hai, và lần hai rơi trọn vào khoảng chờ sau khi cán bộ bấm
"đủ giấy tờ" — đúng khúc người dùng cảm nhận được là chậm.
"""
import base64

import pytest

from app.config import settings
from app.services import ocr, ocr_cache


def _fake_store(monkeypatch):
    """Cache trong RAM thay Mongo; trả luôn danh sách lượt OCR thật đã chạy."""
    store: dict[str, dict] = {}
    ocr_calls: list[list[dict]] = []

    async def fake_get_many(keys):
        return {k: store[k] for k in keys if k in store}

    def fake_put_many_bg(items):
        for key, text, provider, max_tokens in items:
            store[key] = {"text": text, "provider": provider, "max_tokens": max_tokens}

    async def fake_uncached(files, **kwargs):
        ocr_calls.append(list(files))
        return [
            {"name": f.get("name"), "type": f.get("type"),
             "text": "CĂN CƯỚC CÔNG DÂN\nSố: 001…", "provider": "tiengnoi"}
            for f in files
        ]

    monkeypatch.setattr(settings, "ocr_cache_enabled", True)
    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    monkeypatch.setattr(ocr_cache, "put_many_bg", fake_put_many_bg)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    return store, ocr_calls


@pytest.mark.asyncio
async def test_upload_ocr_by_path_is_reused_by_extraction_by_dataurl(tmp_path, monkeypatch):
    store, ocr_calls = _fake_store(monkeypatch)
    raw = b"%PDF-1.4 noi dung giay to"
    path = tmp_path / "cccd.pdf"
    path.write_bytes(raw)

    # 1) Lúc điện thoại gửi lên: upload-session OCR theo `path` để phân loại.
    upload = await ocr.ocr_per_file(
        [{"name": "cccd.pdf", "type": "application/pdf", "path": str(path)}],
        classify=True,
    )
    assert upload[0]["text"].startswith("CĂN CƯỚC")
    assert len(ocr_calls) == 1, "lượt đầu phải OCR thật"
    assert store, "lượt OCR lúc nhận tệp PHẢI được ghi cache"

    # 2) Sau khi bấm "đủ giấy tờ": pipeline dựng dataUrl từ CHÍNH tệp đó rồi trích xuất.
    data_url = f"data:application/pdf;base64,{base64.b64encode(raw).decode()}"
    extract = await ocr.ocr_per_file([{"name": "cccd.pdf", "type": "application/pdf",
                                       "dataUrl": data_url}])

    assert extract[0]["_cached"] is True, "trích xuất phải dùng lại OCR của lượt nhận tệp"
    assert extract[0]["text"] == upload[0]["text"]
    assert len(ocr_calls) == 1, "không được OCR lần hai cho cùng một tệp"


@pytest.mark.asyncio
async def test_path_and_dataurl_of_same_bytes_give_the_same_key(tmp_path):
    raw = b"anh giay khai sinh"
    path = tmp_path / "ks.jpg"
    path.write_bytes(raw)
    data_url = f"data:image/jpeg;base64,{base64.b64encode(raw).decode()}"

    assert ocr_cache.content_key_from_path(str(path)) == ocr_cache.content_key(data_url)


@pytest.mark.asyncio
async def test_missing_file_does_not_break_ocr(monkeypatch):
    """Không băm được đường dẫn thì chỉ mất cache, tuyệt đối không được hỏng lượt OCR."""
    _store, ocr_calls = _fake_store(monkeypatch)
    out = await ocr.ocr_per_file([{"name": "x.jpg", "path": "/khong/ton/tai.jpg"}])
    assert out[0]["text"].startswith("CĂN CƯỚC")
    assert len(ocr_calls) == 1


@pytest.mark.asyncio
async def test_cache_written_at_low_token_cap_is_not_reused(tmp_path, monkeypatch):
    """Bản ghi OCR ở trần token THẤP có thể bị cắt giữa chừng → trích xuất phải OCR lại.

    Nếu tin bừa, hồ sơ nhiều trang sẽ mất chữ ở những trang cuối mà không ai biết.
    """
    store, ocr_calls = _fake_store(monkeypatch)
    raw = b"ho so nhieu trang"
    path = tmp_path / "hoso.pdf"
    path.write_bytes(raw)
    key = ocr_cache.content_key_from_path(str(path))
    store[key] = {"text": "trang 1…", "provider": "tiengnoi",
                  "max_tokens": settings.ocr_tiengnoi_max_tokens}

    out = await ocr.ocr_per_file([{"name": "hoso.pdf", "path": str(path)}])

    assert len(ocr_calls) == 1, "text cắt ở trần thấp không được dùng cho trích xuất"
    assert out[0].get("_cached") is not True
    assert store[key]["max_tokens"] == settings.ocr_tiengnoi_fill_max_tokens, "ghi đè bằng bản đầy đủ"
