"""Xác thực truy cập một phiên tải giấy tờ.

Extension dùng Bearer JWT và chỉ được đọc/sửa phiên do chính tài khoản quầy tạo.
Điện thoại không có JWT nên URL QR trao một capability token HMAC chỉ có hiệu lực
cho đúng ``sid``. Token nằm trong URL fragment để không lọt vào access log/referrer.
"""
import hashlib
import hmac

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.db.mongo import get_db
from app.upload_session import store

_bearer = HTTPBearer(auto_error=False)
_CAPABILITY_HEADER = "x-upload-token"


def _secret() -> bytes:
    value = settings.upload_capability_secret or settings.jwt_refresh_secret
    if not value or value in {"change_me", "change_me_too"} or len(value) < 32:
        raise RuntimeError(
            "Cần cấu hình UPLOAD_CAPABILITY_SECRET hoặc JWT_REFRESH_SECRET an toàn."
        )
    # Có domain separation ngay cả khi deployment tạm dùng JWT refresh làm root key.
    return hmac.new(
        value.encode("utf-8"),
        b"tlnd-capability-root:v1",
        hashlib.sha256,
    ).digest()


def create_upload_capability(sid: str) -> str:
    """Token 256-bit có scope đúng một session; vòng đời thực theo TTL của session."""
    message = f"tlnd-upload-session:v1:{sid}".encode("utf-8")
    return hmac.new(_secret(), message, hashlib.sha256).hexdigest()


def verify_upload_capability(sid: str, token: str | None) -> bool:
    if not sid or not token:
        return False
    try:
        expected = create_upload_capability(sid)
    except RuntimeError:
        # Deployment thiếu secret phải fail closed; request nặc danh không được biến thành 500
        # chỉ vì gửi một header capability giả.
        return False
    return hmac.compare_digest(expected, str(token))


async def _owner_user_id(sess: dict) -> str:
    owner = str(sess.get("owner_user_id") or "").strip()
    if owner:
        return owner
    # Tương thích các phiên đang sống từ trước khi thêm owner_user_id. Conversation đã
    # có auth_user vì endpoint chat vốn bắt Bearer, nên vẫn kiểm tra được đúng chủ phiên.
    conversation_id = str(sess.get("conversation_id") or "").strip()
    if not conversation_id:
        return ""
    conv = await get_db().conversations.find_one(
        {"_id": conversation_id}, {"auth_user.id": 1}
    )
    return str(((conv or {}).get("auth_user") or {}).get("id") or "").strip()


async def require_upload_session_access(
    sid: str,
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Cho phép capability hợp lệ hoặc Bearer của đúng tài khoản sở hữu session."""
    capability = request.headers.get(_CAPABILITY_HEADER)
    if verify_upload_capability(sid, capability):
        sess = await store.get(sid)
        if not sess:
            raise AppError("UPLOAD_SESSION_NOT_FOUND", "Phiên không tồn tại hoặc đã hết hạn", 404)
        return sess

    # Không kiểm tra sự tồn tại của sid trước xác thực để client nặc danh không dò phiên.
    user = await require_auth(creds)
    sess = await store.get(sid)
    if not sess:
        raise AppError("UPLOAD_SESSION_NOT_FOUND", "Phiên không tồn tại hoặc đã hết hạn", 404)
    owner_id = await _owner_user_id(sess)
    if not owner_id or owner_id != str(user.get("id") or ""):
        raise AppError("UPLOAD_SESSION_FORBIDDEN", "Tài khoản không có quyền truy cập phiên này", 403)
    return sess


def upload_session_experience(sess: dict) -> str:
    """Đọc channel đã lưu và nhận diện các session Handfree thuộc compatibility window."""
    actual = str(sess.get("experience") or "").strip()
    if not actual:
        # Compatibility window cho document Handfree đang sống từ DB cũ. Auto Fill cũ chỉ
        # có user_id + files; Handfree có checklist/procedure/conversation nên phân biệt được
        # tất định mà không cần đoán theo URL request.
        actual = "handfree" if (
            sess.get("conversation_id")
            or sess.get("procedure_key")
            or sess.get("required_docs") is not None
        ) else "autofill"
    return actual


def ensure_upload_session_experience(sess: dict, expected: str) -> dict:
    """Không cho route Auto và Handfree đọc nhầm cùng một document session."""
    actual = upload_session_experience(sess)
    if actual != expected:
        raise AppError(
            "UPLOAD_SESSION_EXPERIENCE_MISMATCH",
            "Phiên giấy tờ không thuộc giao diện này",
            409,
        )
    return sess
