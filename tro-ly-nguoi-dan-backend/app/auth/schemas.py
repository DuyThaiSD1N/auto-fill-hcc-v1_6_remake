from pydantic import BaseModel


class LoginReq(BaseModel):
    username: str
    password: str
    # FE trang quản lý gửi adminOnly=true để BE TỪ CHỐI cấp token cho tài khoản không phải
    # admin ngay tại login (không chỉ chặn ở UI). Extension login KHÔNG gửi cờ này (mặc định
    # false) nên tài khoản phường vẫn đăng nhập auto-fill bình thường.
    adminOnly: bool = False


class RefreshReq(BaseModel):
    refreshToken: str


class UserOut(BaseModel):
    id: str
    username: str
    name: str | None = None
    role: str = "user"
    xa: str | None = None
    tinh: str | None = None


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserOut | None = None
