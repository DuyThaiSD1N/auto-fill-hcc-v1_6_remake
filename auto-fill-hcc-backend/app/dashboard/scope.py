"""Phân giải PHẠM VI đơn vị cho bảng thống kê — khóa hoàn toàn theo token, không nhận từ client.

Ba mức phạm vi:
  - unit     : phường/xã tự xem CHÍNH mình (role commune / tài khoản có tỉnh+xã).
  - province : tài khoản Tỉnh (role province_admin) xem MỌI phường/xã cùng tỉnh.
  - all      : admin xem toàn hệ thống (hoặc admin có tỉnh → bó về đúng tỉnh đó).

Đơn vị = một tài khoản có `xa` (mỗi phường/xã một tài khoản xử lý hồ sơ). Khớp tỉnh bằng
province_name đã chuẩn hóa + fold dấu để chịu "Thành phố Đà Nẵng" ↔ "Đà Nẵng".
"""
from app.db.mongo import get_db
from app.reports.integration import fold, province_name
from app.users.roles import OFFICIAL_ACCOUNT_ROLES, PROVINCE_ADMIN_ROLE, normalized_role

_UNIT_PROJECTION = {"name": 1, "username": 1, "xa": 1, "tinh": 1, "role": 1, "access_disabled": 1}


def _unit_of(user: dict) -> dict:
    return {
        "unitId": str(user.get("_id") or user.get("id")),
        "name": user.get("name") or user.get("username"),
        "xa": (user.get("xa") or "").strip() or None,
        "tinh": (user.get("tinh") or "").strip() or None,
        "role": normalized_role(user.get("role")),
    }


async def _units_matching(province: str | None) -> list[dict]:
    """Đơn vị = tài khoản nghiệp vụ HCC xã/tỉnh (role commune/province). Truyền tỉnh → lọc đúng tỉnh.

    Dùng role thay vì "có xã" vì tài khoản HCC tỉnh có thể không gán xã nhưng vẫn là một đơn vị.
    """
    target = fold(province_name(province)) if province else None
    rows = await get_db().users.find(
        {"role": {"$in": list(OFFICIAL_ACCOUNT_ROLES)}}, _UNIT_PROJECTION
    ).to_list(5000)
    units: list[dict] = []
    for row in rows:
        if row.get("access_disabled"):
            continue
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
