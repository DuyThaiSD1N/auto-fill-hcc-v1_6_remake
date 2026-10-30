"""OCR Tiếng Nói vintern-v12 — POST /v1/ocr, batch nhiều tệp trong một request.

Gửi nhiều file trong 1 request multipart; server tự tách trang PDF, tự xoay ảnh và OCR
song song, trả results[] KHỚP THỨ TỰ files gửi lên. Keyless: để trống
`ocr_tiengnoi_api_key` = không gửi Bearer.

Đây là adapter OCR duy nhất của backend. `max_tokens` ngắn dùng cho phân loại; giới hạn dài
dùng cho fill và lập kế hoạch đính kèm.
"""
import asyncio
import base64
from contextlib import ExitStack
import logging
from pathlib import Path
import re
from typing import BinaryIO

import fitz
import httpx

from app.config import settings
from app.monitor import recorder as mon

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
            async with mon.span("ocr.server", target=tag, attempt=idx + 1):
                data = await _post_once(
                    decoded, max_tokens, include_tokens=include_tokens,
                    base_url=base_url, api_key=api_key,
                )
            if tag != "primary":
                mon.flag("ocr_fallback")
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


# Gateway OCR song song theo trang nhưng có trần mỗi request → hồ sơ nhiều trang gửi một request
# phải xếp hàng. Chia nhóm tệp liền nhau gửi song song: đo trên OCR prod, 4 nhóm nhanh ~1,7 lần,
# chữ OCR không lệch hơn gửi lại một lần; 8 nhóm không nhanh thêm đáng kể mà chiếm gấp đôi chỗ của
# người dùng khác. Hồ sơ ít trang lợi chưa tới 1 giây → vẫn một request.
_MAX_GROUPS = 4
_GROUP_MIN_PAGES = 9
# Một PDF nhiều trang cũng xếp hàng trong trần song song của một request → cắt thành vài PDF con gửi
# song song rồi ghép lại đúng khuôn "Trang i/N" của gateway. Đo trên OCR prod (18 PDF thật 6–97 trang):
# 6–15 trang nhanh 1,6–2,1 lần khi cắt phần 2–4 trang; 16–40 trang tốt nhất 4 trang/phần (~2,3 lần);
# trên 40 trang phần to hơn, khoảng 8 phần là đủ (~2,8 lần) — cắt quá nhiều phần lại chậm. Chữ OCR không
# lệch hơn gửi lại nguyên tệp. Dưới 6 trang không đáng cắt.
_SPLIT_MIN_PAGES = 6
_MAX_PARTS = 8
_PAGE_HEADER = "───── Trang {page}/{total} ─────"


def _page_count(f: dict, data: bytes | BinaryIO) -> int:
    """Số trang để chia nhóm; ảnh và tệp không mở được tính 1."""
    try:
        if isinstance(data, (bytes, bytearray)):
            if bytes(data[:5]) != b"%PDF-":
                return 1
            document = fitz.open(stream=data, filetype="pdf")
        else:
            document = fitz.open(str(f.get("path")))
        try:
            return max(1, document.page_count)
        finally:
            document.close()
    except Exception:  # noqa: BLE001 - chỉ để chia nhóm, sai thì gửi như ảnh một trang
        return 1


def _page_groups(pages: list[int], max_groups: int = _MAX_GROUPS) -> list[list[int]]:
    """Nhóm chỉ số tệp LIỀN NHAU, cân theo số trang (không tách tệp)."""
    count = min(max_groups, len(pages))
    if count < 2 or sum(pages) < _GROUP_MIN_PAGES:
        return [list(range(len(pages)))]
    target = sum(pages) / count
    groups: list[list[int]] = []
    current: list[int] = []
    filled = 0
    for index, page in enumerate(pages):
        if current and filled + page / 2 > target and len(groups) < count - 1:
            groups.append(current)
            current, filled = [], 0
        current.append(index)
        filled += page
    return groups + [current]


def _cut_pdf(raw: bytes, first: int, last: int) -> bytes:
    source = fitz.open(stream=raw, filetype="pdf")
    part = fitz.open()
    try:
        part.insert_pdf(source, from_page=first, to_page=last)
        return part.tobytes(garbage=1)
    finally:
        part.close()
        source.close()


def _split_units(
    decoded: list[tuple[str, bytes | BinaryIO, str]], pages: list[int],
) -> list[tuple[int, int, tuple[str, bytes | BinaryIO, str]]]:
    """(chỉ số tệp, số trang, input gửi OCR); PDF đủ lớn cắt thành các phần trang liền nhau."""
    units = []
    for index, ((name, data, mime), count) in enumerate(zip(decoded, pages)):
        if count < _SPLIT_MIN_PAGES:
            units.append((index, count, (name, data, mime)))
            continue
        raw = data if isinstance(data, (bytes, bytearray)) else data.read()
        size = max(-(-count // _MAX_PARTS), min(4, -(-count // 4)))
        for first in range(0, count, size):
            last = min(count, first + size) - 1
            units.append((index, last - first + 1, (name, _cut_pdf(bytes(raw), first, last), "application/pdf")))
    return units


def _merge_parts(parts: list[tuple[int, dict | None]]) -> dict | None:
    """Ghép kết quả các phần của MỘT tệp như gateway trả cho cả tệp (đánh lại số trang toàn tệp)."""
    if len(parts) == 1:
        return parts[0][1]
    pages: list[dict] = []
    for count, res in parts:
        got = (res or {}).get("pages") if isinstance((res or {}).get("pages"), list) else None
        if res is None or got is None:
            got = [{"ok": False, "text": ""}] * count
        pages.extend(got)
    total = len(pages)
    pages = [{**page, "index": i} for i, page in enumerate(pages)]
    return {
        "ok": all(page.get("ok") is not False for page in pages),
        "num_pages": total,
        "pages": pages,
        "text": "\n\n".join(
            f"{_PAGE_HEADER.format(page=i + 1, total=total)}\n{page.get('text') or ''}" for i, page in enumerate(pages)
        ),
        "error": next((res.get("error") for _c, res in parts if res and res.get("error")), None),
    }


async def _post_groups(
    decoded: list[tuple[str, bytes | BinaryIO, str]],
    groups: list[list[int]],
    max_tokens: int | None,
    *,
    include_tokens: bool,
) -> list[dict | None]:
    """Kết quả theo đúng thứ tự tệp; tệp OCR báo lỗi (thường một trang vLLM lỗi) gửi lại riêng một lần."""
    datas = await asyncio.gather(*(
        _post([decoded[i] for i in group], max_tokens, include_tokens=include_tokens)
        for group in groups
    ))
    results: list[dict | None] = [None] * len(decoded)
    for group, data in zip(groups, datas):
        for index, res in zip(group, data.get("results") or []):
            results[index] = res
    failed = [i for i, res in enumerate(results) if res is None or res.get("ok") is False]
    if failed and len(failed) < len(results):
        mon.flag("ocr_retry")
        _rewind([decoded[i] for i in failed])
        try:
            data = await _post([decoded[i] for i in failed], max_tokens, include_tokens=include_tokens)
        except Exception as e:  # noqa: BLE001 - giữ kết quả lần đầu
            logger.warning("OCR gửi lại %d tệp lỗi: %r", len(failed), e)
            return results
        for index, res in zip(failed, data.get("results") or []):
            if res and res.get("ok") is not False:
                results[index] = res
    return results


async def _ocr_per_file(
    files: list[dict],
    max_tokens: int | None = None,
    *,
    include_tokens: bool = False,
) -> list[dict]:
    """OCR các file (một request, hoặc vài nhóm song song khi nhiều trang) → [{name, type, text, error?}]
    khớp thứ tự input.

    max_tokens: None → dùng ocr_tiengnoi_max_tokens (classify, ngắn). Fill truyền giá trị cao hơn.
    """
    out = [{"name": f.get("name"), "type": f.get("type"), "text": ""} for f in files]
    if not files:
        return out
    with ExitStack() as stack:
        with mon.span("pre.decode", files=len(files)) as dec:
            decoded = [_open_input(f, stack) for f in files]
            dec.attrs["bytes"] = sum(len(d) for _n, d, _m in decoded if isinstance(d, (bytes, bytearray)))
            pages = [_page_count(f, d) for f, (_n, d, _m) in zip(files, decoded)]
            units = await asyncio.to_thread(_split_units, decoded, pages)
            # Có tệp bị cắt thì mỗi phần cần request riêng mới song song được → nới trần số request.
            groups = _page_groups([count for _i, count, _d in units], _MAX_PARTS if len(units) > len(files) else _MAX_GROUPS)
            dec.attrs["parts"] = len(units)
            dec.attrs["groups"] = len(groups)
        unit_results = await _post_groups([d for _i, _c, d in units], groups, max_tokens, include_tokens=include_tokens)
        results = [
            _merge_parts([(count, res) for (index, count, _d), res in zip(units, unit_results) if index == file_index])
            for file_index in range(len(files))
        ]
    with mon.span("ocr.split", files=len(files)) as split:
        pages: list[int | None] = []
        for i, o in enumerate(out):
            if results[i] is not None:
                res = results[i] or {}
                o["text"] = res.get("text") or ""
                if include_tokens:
                    o["tokens"] = _tokens(res)
                if res.get("ok") is False and res.get("error"):
                    o["error"] = str(res.get("error"))
                page_list = res.get("pages")
                pages.append(len(page_list) if isinstance(page_list, list) else res.get("page_count"))
            else:
                o["error"] = "thiếu kết quả từ OCR tiengnoi"
                pages.append(None)
        split.attrs["pages"] = pages
    return out


async def ocr_per_file(files: list[dict], max_tokens: int | None = None) -> list[dict]:
    return await _ocr_per_file(files, max_tokens)


async def ocr_tokens_per_file(files: list[dict], max_tokens: int | None = None) -> list[dict]:
    """OCR phục vụ rà soát; tận dụng token nếu response có, nếu không trả `tokens=[]`."""
    out = await _ocr_per_file(files, max_tokens, include_tokens=True)
    for item in out:
        item.setdefault("tokens", [])
    return out
