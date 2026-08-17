"""Đổi (tinh, xa) trên tài khoản cán bộ → conv.location — auto-chọn nơi làm thủ tục.

Tài khoản tạo từ trang quản trị lưu tên đầy đủ chuẩn danh mục ("Tỉnh Lai Châu",
"Phường Tân Phong"); tài khoản cũ nhập tay có thể là tên trần ("Lai Châu",
"Tân Phong") → khớp mềm thêm một nhịp. Không khớp được tỉnh → None (giữ hành vi
mặc định); tỉnh khớp mà xã không khớp → ward rỗng, card bắt chọn xã tay.
"""
import re

from app.locations.router import PROVINCES, _WARDS

_WARD_TYPE = re.compile(r"^(Phường|Xã|Đặc khu)\s+", re.IGNORECASE)


def location_for(tinh: str | None, xa: str | None) -> dict | None:
    tinh = (tinh or "").strip()
    xa = (xa or "").strip()
    if not tinh:
        return None
    prov = next((p for p in PROVINCES if p["text"] == tinh), None) or next(
        (p for p in PROVINCES if p["name"] == tinh), None
    )
    if not prov:
        return None
    ward = ""
    if xa:
        communes = _WARDS[prov["slug"]]["communes"]
        if xa in communes:
            ward = xa
        else:
            ward = next((w for w in communes if _WARD_TYPE.sub("", w) == xa), "")
    return {"province": prov["text"], "province_slug": prov["slug"], "ward": ward}
