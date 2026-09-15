"""Facade OCR duy nhất của backend: dịch vụ batch Tiếng Nói.

Mọi pipeline gọi module này để dùng chung cache theo nội dung file và không thể tự chọn
provider/fallback khác. Tiếng Nói tự tách trang PDF, xoay ảnh và OCR nhiều tệp multipart.
"""
import re

from app.config import settings
from app.services import ocr_tiengnoi

_PAGE_SEPARATOR_RE = re.compile(
    r"(?im)^[\s\u2500-\u257f-]*(?:trang|page)\s+\d+\s*/\s*\d+[\s\u2500-\u257f-]*$"
)


def _has_meaningful_ocr_text(value: str | None) -> bool:
    """Header phân trang do OCR tự sinh không được xem là nội dung tài liệu."""
    without_page_headers = _PAGE_SEPARATOR_RE.sub("", str(value or ""))
    return bool(without_page_headers.strip())


def resolved_label() -> str:
    return "tiengnoi"


def _error_results(files: list[dict], exc: Exception) -> list[dict]:
    """Giữ lỗi theo từng tệp để sự cố batch không làm API vỡ shape response."""
    return [
        {
            "name": item.get("name"),
            "type": item.get("type"),
            "text": "",
            "error": f"OCR Tiếng Nói: {exc}",
            "provider": "tiengnoi",
        }
        for item in files
    ]


async def _ocr_per_file_uncached(
    files: list[dict],
    *,
    classify: bool = False,
) -> list[dict]:
    max_tokens = (
        settings.ocr_tiengnoi_max_tokens
        if classify
        else settings.ocr_tiengnoi_fill_max_tokens
    )
    try:
        results = await ocr_tiengnoi.ocr_per_file(
            files, max_tokens=max_tokens
        )
    except Exception as exc:  # noqa: BLE001 — trả lỗi per-file, không fallback provider khác
        return _error_results(files, exc)

    for item in results:
        item["provider"] = "tiengnoi"
        if not item.get("error") and not _has_meaningful_ocr_text(item.get("text")):
            item["error"] = "OCR Tiếng Nói không đọc được nội dung"
    return results


async def _run_uncached(files: list[dict], *, classify: bool) -> list[dict]:
    """Giữ tương thích với các adapter/mock cũ khi chạy OCR điền biểu mẫu.

    ``classify`` chỉ là contract mới của upload-session. Không truyền keyword này ở luồng
    mặc định để các adapter nội bộ cũ vẫn dùng được đúng chữ ký một tham số.
    """
    if classify:
        return await _ocr_per_file_uncached(files, classify=True)
    return await _ocr_per_file_uncached(files)


def _cache_key(item: dict):
    """Khóa cache của MỘT file, dù nó đến bằng dataUrl (pipeline) hay path (upload-session).

    Hai đường phải ra CÙNG một khóa: có vậy lượt OCR lúc nhận tệp mới dùng lại được cho lượt
    trích xuất sau khi cán bộ bấm "đủ giấy tờ" — trước đây upload-session không có khóa nên mỗi
    tệp bị OCR hai lần, và lượt thứ hai rơi đúng vào khoảng chờ mà cán bộ cảm nhận được.
    """
    from app.services import ocr_cache

    data_url = (item or {}).get("dataUrl") or ""
    if data_url:
        return ocr_cache.content_key(data_url)
    return ocr_cache.content_key_from_path((item or {}).get("path") or "")


async def ocr_per_file(files: list[dict], *, classify: bool = False) -> list[dict]:
    """OCR từng file, có cache theo hash nội dung.

    Khi cache bật, phân loại và trích xuất DÙNG CHUNG một lượt OCR ở trần token của trích xuất:
    text cắt ở trần phân loại (thấp hơn) không đủ dày cho trích xuất nên cache nó là bẫy — lượt
    sau vẫn phải OCR lại mà lại tưởng là đã có. ``classify`` chỉ còn tác dụng khi cache tắt.
    """
    from app.services import ocr_cache

    if not settings.ocr_cache_enabled or not files:
        return await _run_uncached(files, classify=classify)

    need_tokens = settings.ocr_tiengnoi_fill_max_tokens
    keys = [_cache_key(item) for item in files]
    cached = await ocr_cache.get_many([key for key in keys if key])
    cached = {
        key: value
        for key, value in cached.items()
        if value.get("provider") == "tiengnoi"
        and _has_meaningful_ocr_text(value.get("text"))
        # Bản ghi cũ chưa có max_tokens đều do luồng fill ghi (chỉ upload-session dùng trần
        # phân loại, mà đường đó trước đây không ghi cache được) → coi như đã đủ dày.
        and (value.get("max_tokens") or need_tokens) >= need_tokens
    }

    miss_files = [item for item, key in zip(files, keys) if not key or key not in cached]
    fresh = (
        await _run_uncached(miss_files, classify=False)
        if miss_files
        else []
    )

    results: list[dict] = []
    fresh_iter = iter(fresh)
    to_cache: list[tuple[str, str, str | None, int | None]] = []
    for item, key in zip(files, keys):
        if key and key in cached:
            results.append({
                "name": (item or {}).get("name"),
                "type": (item or {}).get("type"),
                "text": cached[key]["text"],
                "provider": "tiengnoi",
                "_cached": True,
            })
            continue

        result = next(fresh_iter)
        results.append(result)
        if key and not result.get("error") and _has_meaningful_ocr_text(result.get("text")):
            to_cache.append((key, result["text"], "tiengnoi", need_tokens))

    ocr_cache.put_many_bg(to_cache)
    return results


async def ocr_tokens_per_file(files: list[dict]) -> list[dict]:
    """OCR token/bbox cho màn rà soát, vẫn chỉ gọi dịch vụ Tiếng Nói."""
    try:
        results = await ocr_tiengnoi.ocr_tokens_per_file(
            files, max_tokens=settings.ocr_tiengnoi_fill_max_tokens
        )
    except Exception as exc:  # noqa: BLE001 — review best-effort, không fallback
        results = _error_results(files, exc)
        for item in results:
            item["tokens"] = []
    for item in results:
        item["provider"] = "tiengnoi"
    return results
