"""OCR Tiếng Nói vintern-v12 — POST /v1/ocr, batch nhiều tệp trong một request.

Gửi nhiều file trong 1 request multipart; server tự tách trang PDF, tự xoay ảnh và OCR
song song, trả results[] KHỚP THỨ TỰ files gửi lên. Keyless: để trống
`ocr_tiengnoi_api_key` = không gửi Bearer.

Đây là adapter OCR duy nhất của backend. `max_tokens` ngắn dùng cho phân loại; giới hạn dài
dùng cho fill và lập kế hoạch đính kèm.
"""
import base64
from contextlib import ExitStack
import logging
from pathlib import Path
import re
from typing import BinaryIO

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DATA_URL_RE = re.compile(r"^data:([^;,]*)(;base64)?,(.*)$", re.DOTALL)


def _decode_data_url(f: dict) -> tuple[str, bytes, str]:
    """Giải mã contract cũ ``{name,type,dataUrl}`` của process/attach."""
    du = f.get("dataUrl") or ""
    m = _DATA_URL_RE.match(du)
    if not m:
        raise ValueError(f"dataUrl không hợp lệ cho {f.get('name')}")
    mime = m.group(1) or f.get("type") or "application/octet-stream"
    payload = m.group(3)
    payload += "=" * (-len(payload) % 4)
    raw = base64.b64decode(payload)
    return (f.get("name") or "file", raw, mime)


def _open_input(f: dict, stack: ExitStack) -> tuple[str, bytes | BinaryIO, str]:
    """Mở nguồn OCR dạng path mà không đưa cả file upload-session vào RAM.

    Chỉ cho đọc file nằm dưới kho upload-session; path do client tự gửi hoặc path traversal
    đều bị chặn trước khi mở file. ``ExitStack`` giữ handle sống đến khi httpx gửi xong.
    """
    path = str(f.get("path") or "").strip()
    if not path:
        return _decode_data_url(f)
    storage_root = (Path(settings.storage_dir) / "upload_sessions").resolve()
    resolved_path = Path(path).resolve()
    if not resolved_path.is_relative_to(storage_root):
        raise ValueError("Đường dẫn OCR nằm ngoài kho upload-session.")
    handle = stack.enter_context(resolved_path.open("rb"))
    mime = f.get("type") or "application/octet-stream"
    return (f.get("name") or resolved_path.name or "file", handle, mime)


def _ocr_targets() -> list[tuple[str, str, str]]:
    """Endpoint OCR theo thứ tự ưu tiên: (base_url, api_key, tag). Fallback chỉ khi có cấu hình.

    Key backup trống → kế thừa key chính (server dự phòng thường dùng chung khóa xác thực).
    """
    targets = [(settings.ocr_tiengnoi_base_url, settings.ocr_tiengnoi_api_key, "primary")]
    if settings.fallback_ocr_tiengnoi_base_url:
        targets.append((
            settings.fallback_ocr_tiengnoi_base_url,
            settings.fallback_ocr_tiengnoi_api_key or settings.ocr_tiengnoi_api_key,
            "fallback",
        ))
    return targets


def _rewind(decoded: list[tuple[str, bytes | BinaryIO, str]]) -> None:
    """Đưa con trỏ file handle về 0 trước khi gửi lại sang server dự phòng.

    httpx đã đọc hết stream ở lần POST trước → không seek lại thì server backup nhận file RỖNG.
    ``bytes`` (đến từ dataUrl) không cần seek.
    """
    for _name, data, _mime in decoded:
        seek = getattr(data, "seek", None)
        if callable(seek):
            seek(0)


async def _post_once(
    decoded: list[tuple[str, bytes | BinaryIO, str]],
    max_tokens: int | None,
    *,
    include_tokens: bool,
    base_url: str,
    api_key: str,
) -> dict:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    parts = [("files", (name, data, mime)) for (name, data, mime) in decoded]
    mt = settings.ocr_tiengnoi_max_tokens if max_tokens is None else max_tokens
    timeout = httpx.Timeout(settings.ocr_tiengnoi_timeout_ms / 1000)
    form_data = {"max_tokens": str(mt)}
    if include_tokens:
        form_data["include_tokens"] = "true"
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            base_url.rstrip("/") + "/v1/ocr",
            files=parts,
            data=form_data,
            headers=headers,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"OCR tiengnoi HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


async def _post(
    decoded: list[tuple[str, bytes | BinaryIO, str]],
    max_tokens: int | None = None,
    *,
    include_tokens: bool = False,
) -> dict:
    """POST OCR với fallback: thử server chính, lỗi thì seek(0) rồi thử server dự phòng."""
    last_exc: Exception | None = None
    for idx, (base_url, api_key, tag) in enumerate(_ocr_targets()):
        if idx > 0:
            _rewind(decoded)
        try:
            data = await _post_once(
                decoded, max_tokens, include_tokens=include_tokens,
                base_url=base_url, api_key=api_key,
            )
            if tag != "primary":
                logger.warning("OCR %s [%s] OK sau khi server chính lỗi", tag, base_url)
            return data
        except Exception as e:  # noqa: BLE001
            last_exc = e
            logger.warning("OCR %s lỗi [%s]: %r", tag, type(e).__name__, e)
    raise last_exc if last_exc else RuntimeError("Không có endpoint OCR nào khả dụng")


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
    with ExitStack() as stack:
        decoded = [_open_input(f, stack) for f in files]
        data = await _post(decoded, max_tokens, include_tokens=include_tokens)
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
