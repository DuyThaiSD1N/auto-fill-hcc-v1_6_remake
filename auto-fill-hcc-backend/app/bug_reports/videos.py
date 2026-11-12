"""Video đính kèm báo lỗi: tải lên TỪNG PHẦN vào phiên tạm, lúc gửi lỗi mới gắn vào lỗi.

Video tới 200 MB vượt giới hạn một request ở nginx (110 MB) và Cloudflare (100 MB), nên trình
duyệt cắt thành phần ≤ CHUNK_BYTES gửi lần lượt; gửi lỗi chỉ kèm mã phiên. Ghi thẳng xuống đĩa
từng phần nên backend không giữ cả video trong RAM.

Phiên là thư mục trên đĩa (không cần Mongo): {STORAGE_DIR}/bug_reports/_uploads/{upload_id}/
  meta.json — chủ phiên + dung lượng khai báo;  data — nội dung đã nhận.
Gắn vào lỗi = chuyển `data` sang {STORAGE_DIR}/bug_reports/{report_id}/video.{ext}, cạnh ảnh.
Phiên bỏ dở quá UPLOAD_TTL_SECONDS bị dọn mỗi lần mở phiên mới.
"""
import json
import os
import re
import secrets
import shutil
import time

from app.config import settings
from app.core.errors import AppError

MAX_BYTES = 200 * 1024 * 1024
CHUNK_BYTES = 8 * 1024 * 1024
UPLOAD_TTL_SECONDS = 24 * 3600

_UPLOAD_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_TOO_LARGE = "Video tối đa 200 MB. Hãy quay video ngắn hơn hoặc chọn video có dung lượng nhỏ hơn."
_EXPIRED = "Phiên tải video đã hết hạn. Hãy chọn lại video rồi gửi."


def _uploads_root() -> str:
    return os.path.join(settings.storage_dir, "bug_reports", "_uploads")


def _upload_dir(upload_id: str) -> str:
    if not _UPLOAD_ID.match(upload_id or ""):
        raise AppError("BUG_VIDEO_UPLOAD_NOT_FOUND", _EXPIRED, 404)
    return os.path.join(_uploads_root(), upload_id)


def _sweep() -> None:
    root = _uploads_root()
    if not os.path.isdir(root):
        return
    cutoff = time.time() - UPLOAD_TTL_SECONDS
    for name in os.listdir(root):
        path = os.path.join(root, name)
        try:
            if os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue


def start(user_id: str, size: int) -> dict:
    if size <= 0:
        raise AppError("BUG_VIDEO_EMPTY", "Video rỗng, hãy chọn lại video.", 400)
    if size > MAX_BYTES:
        raise AppError("BUG_VIDEO_TOO_LARGE", _TOO_LARGE, 413)
    _sweep()
    upload_id = secrets.token_urlsafe(18)
    path = os.path.join(_uploads_root(), upload_id)
    os.makedirs(path)
    with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"user_id": user_id, "size": size}, fh)
    open(os.path.join(path, "data"), "wb").close()
    return {"uploadId": upload_id, "chunkSize": CHUNK_BYTES, "maxBytes": MAX_BYTES}


def _meta(upload_id: str, user_id: str) -> tuple[str, dict]:
    path = _upload_dir(upload_id)
    try:
        with open(os.path.join(path, "meta.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        meta = None
    # Không phân biệt "không có" với "của người khác" để khỏi dò được phiên của tài khoản khác.
    if not meta or meta.get("user_id") != user_id:
        raise AppError("BUG_VIDEO_UPLOAD_NOT_FOUND", _EXPIRED, 404)
    return path, meta


def append(upload_id: str, user_id: str, offset: int, chunk: bytes) -> int:
    """Ghi một phần tại `offset`; trả số byte đã nhận.

    Gửi lại đúng offset cũ (mạng rớt sau khi máy chủ đã ghi) thì ghi đè, không nhân đôi dữ liệu.
    """
    path, meta = _meta(upload_id, user_id)
    if not chunk or len(chunk) > CHUNK_BYTES:
        raise AppError("BUG_VIDEO_CHUNK_INVALID", "Phần video gửi lên không hợp lệ, hãy gửi lại.", 400)
    data = os.path.join(path, "data")
    received = os.path.getsize(data)
    if offset > received:
        raise AppError("BUG_VIDEO_CHUNK_GAP", "Thiếu một phần video, hãy gửi lại.", 409)
    if offset + len(chunk) > int(meta["size"]):
        raise AppError("BUG_VIDEO_TOO_LARGE", _TOO_LARGE, 413)
    with open(data, "r+b") as fh:
        fh.truncate(offset)
        fh.seek(offset)
        fh.write(chunk)
    return offset + len(chunk)


def inspect(head: bytes) -> tuple[str, str]:
    """Định dạng theo nội dung tệp, không tin tên/content-type trình duyệt gửi lên."""
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return ("mov", "video/quicktime") if head[8:12] == b"qt  " else ("mp4", "video/mp4")
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm", "video/webm"
    raise AppError("BUG_VIDEO_INVALID", "Tệp đính kèm không phải video MP4, MOV hoặc WebM.", 400)


def claim(upload_id: str, user_id: str) -> dict:
    """Kiểm phiên đã nhận đủ + đúng định dạng video, TRƯỚC khi cấp mã lỗi."""
    path, meta = _meta(upload_id, user_id)
    data = os.path.join(path, "data")
    size = os.path.getsize(data)
    if size != int(meta["size"]):
        raise AppError("BUG_VIDEO_INCOMPLETE", "Video chưa tải lên xong, hãy gửi lại.", 400)
    with open(data, "rb") as fh:
        ext, media_type = inspect(fh.read(16))
    return {"dir": path, "ext": ext, "type": media_type, "size": size}


def attach(claimed: dict, report_id: str) -> dict:
    """Chuyển video của phiên vào thư mục lỗi; trả metadata ghi vào Mongo."""
    rel_dir = os.path.join("bug_reports", report_id)
    abs_dir = os.path.join(settings.storage_dir, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    name = f"video.{claimed['ext']}"
    os.replace(os.path.join(claimed["dir"], "data"), os.path.join(abs_dir, name))
    shutil.rmtree(claimed["dir"], ignore_errors=True)
    return {"path": os.path.join(rel_dir, name), "type": claimed["type"], "size": claimed["size"]}
