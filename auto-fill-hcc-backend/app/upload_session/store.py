"""Phiên tải ảnh qua QR — metadata Mongo `upload_sessions` (TTL tự dọn), bytes ảnh
trên đĩa `{storage_dir}/upload_sessions/{sid}/{fid}`.

ĐƠN GIẢN, KHÔNG phân loại: file lưu PHẲNG {fid,name,type,size}. Session chỉ là CẦU NỐI —
extension kéo ảnh về danh sách file của popup rồi chạy /process như ảnh chọn tay.
"""
import secrets
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dir(sid: str) -> Path:
    p = Path(settings.storage_dir) / "upload_sessions" / sid
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_session(user_id: str) -> dict:
    # sid = mã bí mật (capability token): điện thoại KHÔNG đăng nhập, chỉ ai có sid mới gửi
    # được ảnh vào phiên. token_urlsafe(18) ≈ 24 ký tự — đủ dài để không đoán được.
    return {
        "_id": secrets.token_urlsafe(18),
        "user_id": user_id,
        # files: [{fid, name, type, size}] — PHẲNG, không doc_key/side/checklist.
        "files": [],
        "created_at": _now(),  # TTL index tự xoá phiên sau upload_session_ttl_minutes
        "updated_at": _now(),
    }


async def get(sid: str) -> dict | None:
    if not sid:
        return None
    return await get_db().upload_sessions.find_one({"_id": sid})


async def save(sess: dict) -> None:
    sess["updated_at"] = _now()
    await get_db().upload_sessions.replace_one({"_id": sess["_id"]}, sess, upsert=True)


def new_file_id(name: str) -> str:
    ext = (name.rsplit(".", 1)[-1] if "." in name else "jpg").lower()[:5]
    return f"f{secrets.token_hex(4)}.{ext}"


def save_file_bytes(sid: str, fid: str, data: bytes) -> None:
    (_dir(sid) / fid).write_bytes(data)


def read_file_bytes(sid: str, fid: str) -> bytes | None:
    p = _dir(sid) / fid
    return p.read_bytes() if p.exists() else None
