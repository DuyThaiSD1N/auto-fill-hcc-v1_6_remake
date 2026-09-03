"""Ghi ``UploadFile`` xuống file tạm theo chunk cho cả Auto Fill và Handfree.

Không gọi ``await upload.read()`` vì cách đó giữ nguyên cả tệp trong RAM. Hai channel
dùng chung helper này để quota theo tệp/phiên có cùng ý nghĩa và cùng cách dọn file lỗi.
"""
from pathlib import Path

from app.upload_session import store

UPLOAD_CHUNK_BYTES = 1024 * 1024


class FileLimitExceeded(Exception):
    pass


class SessionLimitExceeded(Exception):
    pass


def copy_upload_to_staging(
    source,
    staged_path: Path,
    max_file_bytes: int,
    max_session_bytes: int,
) -> int:
    """Copy stream theo chunk và xóa file tạm nếu request vượt quota hoặc bị lỗi."""
    size = 0
    created = False
    try:
        source.seek(0)
        with staged_path.open("xb") as target:
            created = True
            while True:
                chunk = source.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_file_bytes:
                    raise FileLimitExceeded
                if size > max_session_bytes:
                    raise SessionLimitExceeded
                target.write(chunk)
        return size
    except Exception:
        # Không xóa nếu open("xb") thất bại vì trùng path; file đó có thể thuộc request khác.
        if created:
            store.delete_staged_file(staged_path)
        raise
