"""Lưu file/ảnh của mỗi request xuống disk.

Cấu trúc: {STORAGE_DIR}/{YYYY-MM-DD}/{request_id}/{idx}_{tên-an-toàn}
Trả về metadata (name, type, role, size, path tương đối) để ghi vào Mongo.
"""
import base64
import hashlib
import os
import re
from datetime import datetime

from app.config import settings


def _safe_name(name: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "file")[:120]


def _decode_data_url(data_url: str) -> bytes:
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def save_request_files(request_id: str, created_at: datetime, files) -> list[dict]:
    """files: list FileItem (name, type, dataUrl, role). Ghi từng file, trả metadata."""
    rel_dir = os.path.join(created_at.strftime("%Y-%m-%d"), request_id)
    abs_dir = os.path.join(settings.storage_dir, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    saved: list[dict] = []
    for idx, f in enumerate(files):
        try:
            raw = _decode_data_url(f.dataUrl)
        except Exception:  # noqa: BLE001 — file hỏng vẫn ghi metadata, không chặn request
            saved.append({"name": f.name, "type": f.type, "role": f.role,
                          "size": 0, "path": None, "sha256": None,
                          "error": "decode_failed"})
            continue
        fname = f"{idx:02d}_{_safe_name(f.name)}"
        with open(os.path.join(abs_dir, fname), "wb") as fh:
            fh.write(raw)
        saved.append({"name": f.name, "type": f.type, "role": f.role,
                      "size": len(raw), "path": os.path.join(rel_dir, fname),
                      # Tính đúng một lần trong lúc bytes đã có sẵn; thống kê không phải đọc
                      # lại file trên đĩa hay tin vào tên file có thể trùng/đổi tên.
                      "sha256": hashlib.sha256(raw).hexdigest()})
    return saved
