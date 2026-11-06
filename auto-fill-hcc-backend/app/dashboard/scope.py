"""Phân giải PHẠM VI đơn vị cho bảng thống kê — khóa hoàn toàn theo token, không nhận từ client.

Ba mức phạm vi:
  - unit     : phường/xã tự xem CHÍNH mình (role commune / tài khoản có tỉnh+xã).
  - province : tài khoản Tỉnh (role province_admin) xem MỌI phường/xã cùng tỉnh.
  - all      : admin xem toàn hệ thống (hoặc admin có tỉnh → bó về đúng tỉnh đó). Admin toàn hệ
               thống được lọc thêm một tỉnh (narrow_to_province) — chỉ thu hẹp, không mở rộng.

Đơn vị = một tài khoản có `xa` (mỗi phường/xã một tài khoản xử lý hồ sơ). Khớp tỉnh bằng
province_name đã chuẩn hóa + fold dấu để chịu "Thành phố Đà Nẵng" ↔ "Đà Nẵng".
"""
from app.core.errors import AppError
from app.db.mongo import get_db
from app.reports.integration import fold, province_name
from app.users.roles import (
    NOT_DELETED,
    OFFICIAL_ACCOUNT_ROLES,
    PROVINCE_ADMIN_ROLE,
    normalized_role,
)

_UNIT_PROJECTION = {"name": 1, "username": 1, "xa": 1, "tinh": 1, "role": 1, "access_disabled": 1}


def _unit_of(user: dict) -> dict:
    return {
        "unitId": str(user.get("_id") or user.get("id")),
        "name": user.get("name") or user.get("username"),
        "xa": (user.get("xa") or "").strip() or None,
        "tinh": (user.get("tinh") or "").strip() or None,
        "role": normalized_role(user.get("role")),
        "accessDisabled": user.get("access_disabled") is True,
    }


async def _units_matching(province: str | None) -> list[dict]:
    """Đơn vị = tài khoản nghiệp vụ HCC xã/tỉnh (role commune/province). Truyền tỉnh → lọc đúng tỉnh.

    Dùng role thay vì "có xã" vì tài khoản HCC tỉnh có thể không gán xã nhưng vẫn là một đơn vị.
    """
    target = fold(province_name(province)) if province else None
    rows = await get_db().users.find(
        {**NOT_DELETED, "role": {"$in": list(OFFICIAL_ACCOUNT_ROLES)}}, _UNIT_PROJECTION
    ).to_list(5000)
    units: list[dict] = []
    for row in rows:
        # Tài khoản TẠM KHÓA vẫn là một đơn vị: công việc đã làm xong tháng trước không có lý
        # do biến mất khỏi báo cáo chỉ vì hôm nay khóa tài khoản để bảo trì. Bảng hiện nhãn
        # "Tạm khóa" và vẫn cộng vào tổng — ẩn đi thì tổng của tỉnh không khớp tổng các dòng.
        # (Khóa vẫn chặn ĐĂNG NHẬP như cũ, ở ensure_account_available.)
        if target is not None and fold(province_name(row.get("tinh"))) != target:
            continue
        units.append(_unit_of(row))
    units.sort(key=lambda unit: (unit.get("xa") or "", unit.get("name") or ""))
    return units


async def resolve_dashboard_scope(user: dict) -> dict:
    """Trả về phạm vi + danh sách đơn vị được phép xem cho tài khoản trong token."""
    role = normalized_role(user.get("role"))
    self_tinh = (user.get("tinh") or "").strip()
    self_unit = _unit_of(user)

    if role == PROVINCE_ADMIN_ROLE or (role == "admin" and self_tinh):
        units = await _units_matching(self_tinh)
        return {
            "role": role,
            "scopeKind": "province",
            "province": province_name(self_tinh) or self_tinh or None,
            "canViewUnits": True,
            "self": self_unit,
            "units": units,
        }
    if role == "admin":
        units = await _units_matching(None)
        return {
            "role": role,
            "scopeKind": "all",
            "province": None,
            "canViewUnits": True,
            "self": self_unit,
            "units": units,
        }
    # Phường/xã: chỉ chính mình.
    return {
        "role": role,
        "scopeKind": "unit",
        "province": province_name(self_tinh) or self_tinh or None,
        "canViewUnits": False,
        "self": self_unit,
        "units": [self_unit],
    }


def province_options(units: list[dict]) -> list[dict]:
    """Các tỉnh có đơn vị trong phạm vi (dựng ô chọn tỉnh). Gộp theo tên đã fold dấu."""
    groups: dict[str, dict] = {}
    for unit in units:
        name = province_name(unit.get("tinh"))
        if not name:
            continue
        group = groups.setdefault(fold(name), {"name": name, "unitCount": 0})
        group["unitCount"] += 1
    return sorted(groups.values(), key=lambda g: fold(g["name"]))


def narrow_to_province(scope: dict, province: str | None) -> dict:
    """Bó phạm vi admin toàn hệ thống về một tỉnh. Phạm vi xã/tỉnh đã khóa theo token → bỏ qua tham số."""
    if not province or province == "all" or scope["scopeKind"] != "all":
        return scope
    target = fold(province_name(province))
    units = [u for u in scope["units"] if fold(province_name(u.get("tinh"))) == target]
    if not units:
        raise AppError("PROVINCE_OUT_OF_SCOPE", "Tỉnh không có đơn vị nào trong phạm vi tài khoản.", 403)
    return {**scope, "province": province_name(units[0]["tinh"]), "units": units}
