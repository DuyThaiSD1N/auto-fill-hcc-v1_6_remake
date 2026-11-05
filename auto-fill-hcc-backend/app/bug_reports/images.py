"""Ảnh đính kèm báo lỗi: kiểm định dạng thật rồi ghi xuống đĩa.

Cấu trúc: {STORAGE_DIR}/bug_reports/{report_id}/{idx}.{ext}. Ảnh chỉ đọc qua API có đăng nhập
(router), không phục vụ tĩnh — ảnh chụp màn hình cổng DVC có thể dính thông tin công dân.
"""
import io
import os
import shutil

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.core.errors import AppError

MAX_BYTES = 3 * 1024 * 1024

# Định dạng theo nội dung tệp (Pillow), không tin content-type/tên tệp trình duyệt gửi lên.
_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


def inspect(raw: bytes) -> tuple[str, str]:
    """Trả (đuôi tệp, media type); ném AppError nếu không phải ảnh hợp lệ."""
    if not raw:
        raise AppError("BUG_IMAGE_EMPTY", "Có ảnh rỗng, hãy chọn lại ảnh.", 400)
    if len(raw) > MAX_BYTES:
        raise AppError("BUG_IMAGE_TOO_LARGE", "Mỗi ảnh tối đa 3 MB.", 413)
    try:
        with Image.open(io.BytesIO(raw)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise AppError("BUG_IMAGE_INVALID", "Tệp đính kèm không phải ảnh JPG, PNG hoặc WebP.", 400) from exc
    if fmt not in _FORMATS:
        raise AppError("BUG_IMAGE_INVALID", "Tệp đính kèm không phải ảnh JPG, PNG hoặc WebP.", 400)
    return _FORMATS[fmt]


def _report_dir(report_id: str) -> tuple[str, str]:
    rel = os.path.join("bug_reports", report_id)
    return rel, os.path.join(settings.storage_dir, rel)


def save_all(report_id: str, images: list[tuple[bytes, str, str]]) -> list[dict]:
    """images: [(bytes, đuôi, media type)] đã qua `inspect`. Trả metadata để ghi vào Mongo."""
    if not images:
        return []
    rel_dir, abs_dir = _report_dir(report_id)
    os.makedirs(abs_dir, exist_ok=True)
    saved = []
    for idx, (raw, ext, media_type) in enumerate(images):
        name = f"{idx:02d}.{ext}"
        with open(os.path.join(abs_dir, name), "wb") as fh:
            fh.write(raw)
        saved.append({"path": os.path.join(rel_dir, name), "type": media_type, "size": len(raw)})
    return saved


def remove_all(report_id: str) -> None:
    """Dọn ảnh khi ghi Mongo thất bại — không để ảnh mồ côi không thuộc lỗi nào."""
    shutil.rmtree(_report_dir(report_id)[1], ignore_errors=True)


def absolute_path(rel_path: str) -> str:
    root = os.path.realpath(settings.storage_dir)
    path = os.path.realpath(os.path.join(root, rel_path))
    if not path.startswith(root + os.sep):
        raise AppError("BUG_IMAGE_NOT_FOUND", "Không tìm thấy ảnh.", 404)
    return path
