"""Provider OCR mới — llm.tiengnoi.vn/ocr, POST /v1/ocr (model vintern-v5).

Khác raw/vintern: BATCH nhiều file trong 1 request (multipart), server tự tách trang PDF +
tự xoay ảnh + OCR song song, trả results[] KHỚP THỨ TỰ files gửi lên. Keyless: để trống
`ocr_tiengnoi_api_key` = không gửi Bearer.

Public interface `ocr_per_file(files)` trùng ocr_raw để cắm vào attach_classify (path đính kèm).
DÙNG CHO PHÂN LOẠI ĐÍNH KÈM — không dùng cho fill (điểm yếu số dài ~74%).
"""
import base64
import re

import httpx

from app.config import settings

_DATA_URL_RE = re.compile(r"^data:([^;,]*)(;base64)?,(.*)$", re.DOTALL)


def _decode(f: dict) -> tuple[str, bytes, str]:
    """(filename, bytes, mime) từ file dict {name,type,dataUrl}."""
    du = f.get("dataUrl") or ""
    m = _DATA_URL_RE.match(du)
    if not m:
        raise ValueError(f"dataUrl không hợp lệ cho {f.get('name')}")
    mime = m.group(1) or f.get("type") or "application/octet-stream"
    raw = base64.b64decode(m.group(3))
    return (f.get("name") or "file", raw, mime)


async def _post(decoded: list[tuple[str, bytes, str]], max_tokens: int | None = None) -> dict:
    headers = {}
    if settings.ocr_tiengnoi_api_key:
        headers["Authorization"] = f"Bearer {settings.ocr_tiengnoi_api_key}"
    parts = [("files", (name, data, mime)) for (name, data, mime) in decoded]
    mt = settings.ocr_tiengnoi_max_tokens if max_tokens is None else max_tokens
    timeout = httpx.Timeout(settings.ocr_tiengnoi_timeout_ms / 1000)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr",
            files=parts,
            data={"max_tokens": str(mt)},
            headers=headers,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"OCR tiengnoi HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


async def ocr_per_file(files: list[dict], max_tokens: int | None = None) -> list[dict]:
    """Batch TẤT CẢ file trong 1 request → [{name, type, text, error?}] khớp thứ tự input.

    max_tokens: None → dùng ocr_tiengnoi_max_tokens (classify, ngắn). Fill truyền giá trị cao hơn.
    """
    out = [{"name": f.get("name"), "type": f.get("type"), "text": ""} for f in files]
    if not files:
        return out
    decoded = [_decode(f) for f in files]  # lỗi decode → ném ra, attach_classify fallback raw
    data = await _post(decoded, max_tokens)
    results = data.get("results") or []
    for i, o in enumerate(out):
        if i < len(results):
            res = results[i] or {}
            o["text"] = res.get("text") or ""
            if res.get("ok") is False and res.get("error"):
                o["error"] = str(res.get("error"))
        else:
            o["error"] = "thiếu kết quả từ OCR tiengnoi"
    return out
