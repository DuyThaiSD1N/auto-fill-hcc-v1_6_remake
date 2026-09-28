"""Bản mã hoá HAI CHIỀU của mật khẩu tài khoản (Fernet, khoá ở env PASSWORD_VAULT_KEY).

`password_hash` (bcrypt) vẫn là thứ DUY NHẤT dùng để đăng nhập. `password_enc` chỉ để admin xem
lại / xuất danh sách — bcrypt một chiều nên tài khoản tạo trước khi có trường này không thể
khôi phục mật khẩu, chỉ đặt lại hoặc nạp lại từ danh sách đã biết.

Mọi chỗ ĐẶT mật khẩu phải đi qua `password_fields` để hai trường luôn khớp nhau: đổi hash mà
giữ `password_enc` cũ là trang quản trị hiện một mật khẩu đã sai.
"""
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.core.security import hash_password

logger = logging.getLogger(__name__)


def _fernet() -> Fernet | None:
    key = (settings.password_vault_key or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError):
        # Khoá sai định dạng: coi như tắt thay vì làm hỏng tạo/đổi mật khẩu; UI sẽ hiện
        # "chưa lưu mật khẩu" nên vẫn nhìn thấy được.
        logger.error("PASSWORD_VAULT_KEY không phải khoá Fernet hợp lệ — bỏ qua lưu mật khẩu.")
        return None


def enabled() -> bool:
    return _fernet() is not None


def encrypt(password: str) -> str | None:
    fernet = _fernet()
    if fernet is None:
        return None
    return fernet.encrypt(password.encode("utf-8")).decode("ascii")


def decrypt(token: str | None) -> str | None:
    """None khi không có bản lưu, chưa cấu hình khoá, hoặc khoá đã đổi (token không giải được)."""
    if not token:
        return None
    fernet = _fernet()
    if fernet is None:
        return None
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def enc_fields(password: str) -> tuple[dict, dict]:
    """($set, $unset) cho riêng `password_enc` — dùng khi hash đã có sẵn (băm ở thread riêng)."""
    token = encrypt(password)
    if token is None:
        return {}, {"password_enc": ""}
    return {"password_enc": token}, {}


def password_fields(password: str) -> tuple[dict, dict]:
    """($set, $unset) để ghi một mật khẩu mới. bcrypt ~170ms, chạy đồng bộ."""
    set_fields, unset_fields = enc_fields(password)
    return {"password_hash": hash_password(password), **set_fields}, unset_fields
