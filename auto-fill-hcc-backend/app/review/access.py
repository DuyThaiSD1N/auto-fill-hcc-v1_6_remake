"""Capability HMAC có hạn dùng cho dữ liệu rà soát bbox.

Ảnh được tải bằng ``<img>`` nên trình duyệt không gắn Bearer header. Process response trả
capability cho đúng ``request_id``; token khác request hoặc hết hạn đều bị từ chối.
"""
import hashlib
import hmac
import time

from app.config import settings


def _secret() -> bytes:
    root = settings.upload_capability_secret or settings.jwt_refresh_secret
    if not root or root in {"change_me", "change_me_too"} or len(root) < 32:
        raise RuntimeError(
            "Cần cấu hình UPLOAD_CAPABILITY_SECRET hoặc JWT_REFRESH_SECRET an toàn."
        )
    return hmac.new(root.encode("utf-8"), b"tlnd-capability-root:v1", hashlib.sha256).digest()


def create_review_capability(request_id: str) -> str:
    expires_at = int(time.time()) + settings.review_capability_ttl_seconds
    message = f"tlnd-review:v1:{request_id}:{expires_at}".encode("utf-8")
    signature = hmac.new(_secret(), message, hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"


def verify_review_capability(request_id: str, token: str | None) -> bool:
    if not request_id or not token:
        return False
    try:
        expires_raw, signature = str(token).split(".", 1)
        expires_at = int(expires_raw)
    except (TypeError, ValueError):
        return False
    if expires_at < int(time.time()):
        return False
    message = f"tlnd-review:v1:{request_id}:{expires_at}".encode("utf-8")
    try:
        expected = hmac.new(_secret(), message, hashlib.sha256).hexdigest()
    except RuntimeError:
        # Token giả trên endpoint public phải bị coi là không hợp lệ, không làm API trả 500.
        return False
    return hmac.compare_digest(expected, signature)
