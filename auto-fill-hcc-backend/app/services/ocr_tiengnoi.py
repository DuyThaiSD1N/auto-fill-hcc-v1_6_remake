"""OCR Tiếng Nói vintern-v12 — POST /v1/ocr, batch nhiều tệp trong một request.

Gửi nhiều file trong 1 request multipart; server tự tách trang PDF, tự xoay ảnh và OCR
song song, trả results[] KHỚP THỨ TỰ files gửi lên. Keyless: để trống
`ocr_tiengnoi_api_key` = không gửi Bearer.

Đây là adapter OCR duy nhất của backend. `max_tokens` ngắn dùng cho phân loại; giới hạn dài
dùng cho fill và lập kế hoạch đính kèm.
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
    payload = m.group(3)
    payload += "=" * (-len(payload) % 4)
    raw = base64.b64decode(payload)
    return (f.get("name") or "file", raw, mime)


async def _post(
    decoded: list[tuple[str, bytes, str]],
    max_tokens: int | None = None,
) -> dict:
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


def _tokens(res: dict) -> list[dict]:
    out: list[dict] = []
    groups = [(None, res.get("tokens") or [])]
    groups.extend(
        (page.get("page"), page.get("tokens") or [])
        for page in (res.get("pages") or [])
        if isinstance(page, dict)
    )
    for page_no, tokens in groups:
        for token in tokens:
            if not isinstance(token, dict):
                continue
            item = {
                "text": token.get("text") or "",
                "bbox": token.get("bbox") or [0, 0, 0, 0],
                "confidence": token.get("confidence", 0),
            }
            if token.get("page") is not None:
                item["page"] = token.get("page")
            elif page_no is not None:
                item["page"] = page_no
            out.append(item)
    return out


async def _ocr_per_file(
    files: list[dict],
    max_tokens: int | None = None,
    *,
    include_tokens: bool = False,
) -> list[dict]:
    """Batch TẤT CẢ file trong 1 request → [{name, type, text, error?}] khớp thứ tự input.

    max_tokens: None → dùng ocr_tiengnoi_max_tokens (classify, ngắn). Fill truyền giá trị cao hơn.
    """
    out = [{"name": f.get("name"), "type": f.get("type"), "text": ""} for f in files]
    if not files:
        return out
    decoded = [_decode(f) for f in files]
    data = await _post(decoded, max_tokens)
    results = data.get("results") or []
    for i, o in enumerate(out):
        if i < len(results):
            res = results[i] or {}
            o["text"] = res.get("text") or ""
            if include_tokens:
                o["tokens"] = _tokens(res)
            if res.get("ok") is False and res.get("error"):
                o["error"] = str(res.get("error"))
        else:
            o["error"] = "thiếu kết quả từ OCR tiengnoi"
    return out


async def ocr_per_file(files: list[dict], max_tokens: int | None = None) -> list[dict]:
    return await _ocr_per_file(files, max_tokens)


async def ocr_tokens_per_file(files: list[dict], max_tokens: int | None = None) -> list[dict]:
    """OCR phục vụ rà soát; tận dụng token nếu response có, nếu không trả `tokens=[]`."""
    out = await _ocr_per_file(files, max_tokens, include_tokens=True)
    for item in out:
        item.setdefault("tokens", [])
    return out
