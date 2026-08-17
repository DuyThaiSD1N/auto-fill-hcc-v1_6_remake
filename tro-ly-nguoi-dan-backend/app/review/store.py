"""Lưu/đọc dữ liệu rà soát (sources + ảnh baked) theo request_id.

Dùng dir PHẲNG {storage_dir}/review/{request_id}/ để endpoint review (chỉ có request_id,
không có ngày) tra được ngay. Ảnh luôn baked JPEG (đã bake EXIF ở bước process) nên
Vision-token và ảnh phục vụ FE dùng chung 1 hệ toạ độ.
"""
import json
import os

from app.config import settings

_MIME = "image/jpeg"


def _dir(request_id: str) -> str:
    return os.path.join(settings.storage_dir, "review", request_id)


def save_review(request_id: str, sources: dict, images: list[dict]) -> None:
    """sources: {"fields": {...}}. images: [{"index": int, "bytes": bytes}] (đã baked JPEG)."""
    d = _dir(request_id)
    os.makedirs(d, exist_ok=True)
    for img in images:
        idx = int(img["index"])
        with open(os.path.join(d, f"{idx}.jpg"), "wb") as fh:
            fh.write(img["bytes"])
    with open(os.path.join(d, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(sources, fh, ensure_ascii=False)


def load_sources(request_id: str) -> dict | None:
    path = os.path.join(_dir(request_id), "sources.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return None


def load_image(request_id: str, index: int) -> tuple[bytes, str] | None:
    path = os.path.join(_dir(request_id), f"{int(index)}.jpg")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            return fh.read(), _MIME
    except Exception:  # noqa: BLE001
        return None
