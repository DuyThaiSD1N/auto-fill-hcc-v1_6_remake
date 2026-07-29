from typing import Literal

from pydantic import BaseModel, field_validator

# "commune"/"province" (Hành chính công xã/tỉnh): hành xử như "user" (không vào panel, chỉ dùng
# extension), chỉ khác nhãn phân loại. Mọi cổng quyền check == "admin" nên coi là non-admin.
Role = Literal["admin", "user", "commune", "province"]


class UserManaged(BaseModel):
    """Đại diện tài khoản trả về cho trang quản lý (không kèm mật khẩu)."""
    id: str
    username: str
    name: str | None = None
    xa: str | None = None
    tinh: str | None = None
    role: Role = "user"
    created_at: str | None = None
    last_login_at: str | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    name: str | None = None
    xa: str | None = None
    tinh: str | None = None
    role: Role = "user"

    @field_validator("username")
    @classmethod
    def _username_ok(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if len(v) < 3:
            raise ValueError("Tên đăng nhập phải >= 3 ký tự")
        return v

    @field_validator("password")
    @classmethod
    def _password_ok(cls, v: str) -> str:
        if len(v or "") < 8:
            raise ValueError("Mật khẩu phải >= 8 ký tự")
        return v


class UserUpdate(BaseModel):
    """Sửa tài khoản. Trường nào gửi lên (khác None) thì cập nhật; password để đổi mật khẩu."""
    name: str | None = None
    xa: str | None = None
    tinh: str | None = None
    role: Role | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def _password_ok(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if len(v) < 8:
            raise ValueError("Mật khẩu phải >= 8 ký tự")
        return v
