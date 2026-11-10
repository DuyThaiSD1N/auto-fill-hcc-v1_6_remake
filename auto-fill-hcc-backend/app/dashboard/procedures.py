"""Danh mục thủ tục của Trợ lý người dân (handfree) cho trang thống kê.

Phạm vi theo tỉnh của tài khoản, cùng luật mà trợ lý dùng để hiện thủ tục (`provinceOnly` + bảng
"Hoàn thiện phần mềm" theo tỉnh `is_ready_in_province`):
  - admin toàn hệ thống → mọi thủ tục, kèm danh sách tỉnh có thủ tục riêng để lọc;
  - tài khoản còn lại   → thủ tục dùng chung + thủ tục riêng của tỉnh mình, bỏ thủ tục tỉnh mình chưa hoàn thiện.
Khác trợ lý ở một chỗ: tài khoản không xác định được tỉnh chỉ thấy thủ tục dùng chung — đây là
trang tra cứu, hiện thủ tục riêng của tỉnh khác chỉ gây hiểu nhầm là đơn vị mình dùng được.

Chỉ trả tên, mã TTHC và tỉnh áp dụng; không trả cấu hình nội bộ (detect, requiredDocs, wizard...).
"""
import re

from app.channels.handfree.procedure_registry import is_ready_in_province, public_list
from app.locations.catalog import find_province, province_by_slug
from app.reports.integration import fold

# Mã TTHC nằm trong URL kê khai hoặc điều kiện nhận diện ("maThuTuc=1.004772", "#/ke-khai/2.000987").
_TTHC_CODE = re.compile(r"(?<![\d.])([123]\.\d{6})(?!\d)")


def _codes(proc: dict) -> list[str]:
    sources = [proc.get("keKhaiUrl")]
    for value in (proc.get("detect") or {}).values():
        sources.extend(value if isinstance(value, list) else [value])
    codes: list[str] = []
    for source in sources:
        for match in _TTHC_CODE.finditer(str(source or "")):
            if match.group(1) not in codes:
                codes.append(match.group(1))
    return codes


def _province_name(slug: str) -> str:
    province = province_by_slug(slug)
    return province["name"] if province else slug


def account_province_slug(scope: dict) -> str:
    province = find_province(str(scope.get("province") or ""))
    return province["slug"] if province else ""


def catalog(scope: dict) -> dict:
    """Danh mục cho phạm vi đã phân giải (app/dashboard/scope.py)."""
    see_all = scope["scopeKind"] == "all"
    slug = "" if see_all else account_province_slug(scope)
    items: list[dict] = []
    counts: dict[str, int] = {}
    for proc in public_list():
        only = sorted(proc.get("provinceOnly") or [])
        if only and not see_all and slug not in only:
            continue
        if not see_all and not is_ready_in_province(proc, slug):
            continue
        for item_slug in only:
            counts[item_slug] = counts.get(item_slug, 0) + 1
        items.append({
            "key": proc["key"],
            "label": proc.get("label") or proc["key"],
            "shortLabel": proc.get("shortLabel") or None,
            "codes": _codes(proc),
            "provinces": [{"slug": s, "name": _province_name(s)} for s in only],
        })
    provinces = sorted(
        ({"slug": s, "name": _province_name(s), "count": n} for s, n in counts.items()),
        key=lambda p: fold(p["name"]),
    )
    return {
        "scopeKind": scope["scopeKind"],
        "province": {"slug": slug, "name": _province_name(slug)} if slug else None,
        "items": items,
        # Admin: các tỉnh có thủ tục riêng (ô lọc). Tài khoản khác: chỉ tỉnh của mình nếu có thủ tục riêng.
        "provinces": provinces,
    }
