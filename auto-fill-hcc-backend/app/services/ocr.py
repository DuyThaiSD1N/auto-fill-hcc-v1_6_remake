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


async def ocr_per_file(files: list[dict], *, classify: bool = False) -> list[dict]:
    """OCR từng file, có cache hash và giữ giới hạn token riêng cho lúc phân loại.

    Upload-session truyền file bằng ``path`` nên không có dataUrl để tính cache key; trường
    hợp đó đi thẳng OCR nhưng vẫn không đọc toàn bộ file vào RAM.
    """
    from app.services import ocr_cache

    if not settings.ocr_cache_enabled or not files:
        return await _run_uncached(files, classify=classify)

    keys = [ocr_cache.content_key((item or {}).get("dataUrl") or "") for item in files]
    cached = await ocr_cache.get_many([key for key in keys if key])
    cached = {
        key: value
        for key, value in cached.items()
        if value.get("provider") == "tiengnoi"
        and _has_meaningful_ocr_text(value.get("text"))
    }

    miss_files = [item for item, key in zip(files, keys) if not key or key not in cached]
    fresh = (
        await _run_uncached(miss_files, classify=classify)
        if miss_files
        else []
    )

    results: list[dict] = []
    fresh_iter = iter(fresh)
    to_cache: list[tuple[str, str, str | None]] = []
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
            to_cache.append((key, result["text"], "tiengnoi"))

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
