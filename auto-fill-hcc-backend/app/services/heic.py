"""Ảnh HEIC/HEIF (mặc định của camera iPhone) → JPG.

Cổng DVC từ chối HEIC ("Vui lòng chọn tệp đúng định dạng!") và Chrome không tự giải mã được, nên đổi ngay
lúc tệp vào hệ thống: mọi bước sau (OCR, đính kèm) chỉ thấy JPG.
"""
from __future__ import annotations

import io
import logging
import os

from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover — thiếu thư viện thì is_heic vẫn chạy, to_jpeg ném lỗi để nơi gọi giữ tệp gốc
    pillow_heif = None

# "ftyp" + brand ở byte 4–12: heic/heix/hevc/hevx (HEVC), mif1/msf1 (HEIF chung), heim/heis.
_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}
_HEIC_TYPES = {"image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
_JPEG_QUALITY = 90

logger = logging.getLogger(__name__)


def is_heic(data: bytes | None, name: str = "", content_type: str = "") -> bool:
    """Nhận theo BYTE ĐẦU tệp; thiếu bytes thì theo đuôi tệp/MIME (điện thoại hay gửi MIME rỗng hoặc sai)."""
    if data and len(data) >= 12:
        return data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS
    return (content_type or "").lower() in _HEIC_TYPES or os.path.splitext(name or "")[1].lower() in (".heic", ".heif")


def to_jpeg(data: bytes) -> bytes:
    """HEIC → JPG, xoay đúng chiều theo EXIF (ảnh chụp dọc lưu ngang kèm cờ xoay)."""
    if pillow_heif is None:
        raise RuntimeError("Thiếu thư viện pillow-heif")
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=_JPEG_QUALITY)
    return out.getvalue()


def jpeg_name(name: str) -> str:
    base = os.path.splitext(name or "")[0] or "anh"
    return f"{base}.jpg"


def convert_file_if_heic(path, name: str, content_type: str, size: int) -> tuple[str, str, int]:
    """Tệp đã lưu ở ``path`` là HEIC thì ghi đè bằng JPG tại chỗ → (tên, MIME, cỡ) mới; không phải HEIC hoặc
    đổi lỗi thì trả nguyên — giữ tệp gốc còn hơn mất tệp (cổng báo lỗi định dạng thì cán bộ vẫn thấy)."""
    with open(path, "rb") as fh:
        head = fh.read(16)
    if not is_heic(head, name, content_type):
        return name, content_type, size
    try:
        with open(path, "rb") as fh:
            jpeg = to_jpeg(fh.read())
    except Exception:  # noqa: BLE001
        logger.warning("Không đổi được HEIC sang JPG: %s", name, exc_info=True)
        return name, content_type, size
    with open(path, "wb") as fh:
        fh.write(jpeg)
    logger.info("Đổi HEIC → JPG: %s (%d → %d byte)", name, size, len(jpeg))
    return jpeg_name(name), "image/jpeg", len(jpeg)
