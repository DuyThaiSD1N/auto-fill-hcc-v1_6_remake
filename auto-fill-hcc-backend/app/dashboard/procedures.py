"""Danh mục thủ tục Trợ lý hỗ trợ cho trang thống kê — gộp hai kênh: Auto Fill (extension panel, danh mục lõi)
và Trợ lý người dân (handfree). Mọi thủ tục handfree đều có ở Auto Fill; một số chỉ có ở Auto Fill.

Thủ tục áp dụng cho một tỉnh = thủ tục dùng chung + thủ tục riêng của tỉnh đó (`provinceOnly`, cùng luật Auto Fill
hiện thủ tục). Trên Trợ lý người dân, tỉnh trong bảng "Hoàn thiện phần mềm" chỉ chạy thủ tục đã hoàn thiện
(`is_ready_in_province`) → mỗi thủ tục kèm danh sách tỉnh mà kênh handfree chưa chạy (`handfreeOff`), web ghi
kênh đúng cho tỉnh đang xem.
  - admin toàn hệ thống → mọi thủ tục, kèm mọi tỉnh đã có đơn vị (và tỉnh có thủ tục riêng) để lọc;
  - tài khoản còn lại   → thủ tục áp dụng cho tỉnh mình. Không xác định được tỉnh → chỉ thủ tục dùng chung
    (trang tra cứu: hiện thủ tục riêng tỉnh khác dễ hiểu nhầm là đơn vị mình dùng được).

Chỉ trả tên, mã TTHC, tỉnh áp dụng, kênh và Trợ lý điền/đính kèm; không trả cấu hình nội bộ (detect, wizard...).
"""
import re

from app.channels.handfree.procedure_registry import is_visible_in_province, public_list
from app.procedures.bca import allowed_for_role
from app.locations.catalog import find_province, province_by_slug
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import public_list as core_public_list
from app.reports.integration import fold

# Mã TTHC lấy từ nguồn ĐẦU TIÊN có mã: trường `code` → URL kê khai ("#/ke-khai/2.000987") → link kê khai cùng key
# ở ke_khai_links → điều kiện nhận diện ("maThuTuc=1.004772"). Nhận diện để cuối vì có thể liệt kê thêm mã của
# biến thể chỉ dùng để bắt trang (vd liên thông khai sinh bắt cả 2.000986) — không phải mã của thủ tục.
_TTHC_CODE = re.compile(r"(?<![\d.])([123]\.\d{6})(?!\d)")
_LINK_CODES: dict[str, list[str]] = {}
for _link in KE_KHAI_LINKS:
    if _link.get("key") and _link.get("code"):
        _LINK_CODES.setdefault(str(_link["key"]), []).append(str(_link["code"]))


def _codes(proc: dict) -> list[str]:
    detect: list = []
    for value in (proc.get("detect") or {}).values():
        detect.extend(value if isinstance(value, list) else [value])
    groups = [[proc.get("code")], [proc.get("keKhaiUrl")], _LINK_CODES.get(str(proc.get("key") or ""), []), detect]
    for sources in groups:
        codes: list[str] = []
        for source in sources:
            for match in _TTHC_CODE.finditer(str(source or "")):
                if match.group(1) not in codes:
                    codes.append(match.group(1))
        if codes:
            return codes
    return []


def _support(proc: dict) -> str:
    """Trợ lý làm gì trên cổng: `attach` chỉ đính kèm (không có tờ khai), `fill_attach` điền tờ khai + đính kèm,
    `fill` chỉ điền (cổng không có bước đính kèm, vd nhóm căn cước/cư trú của BCA)."""
    if proc.get("mode") == "attach":
        return "attach"
    return "fill_attach" if proc.get("hasAttachmentStep") else "fill"


def _province_name(slug: str) -> str:
    province = province_by_slug(slug)
    return province["name"] if province else slug


def account_province_slug(scope: dict) -> str:
    province = find_province(str(scope.get("province") or ""))
    return province["slug"] if province else ""


def _deployed_slugs(scope: dict) -> set[str]:
    """Tỉnh đã triển khai = tỉnh có đơn vị trong phạm vi (nhóm Bộ Công an không phải tỉnh → bỏ)."""
    slugs = set()
    for unit in scope.get("units") or []:
        province = find_province(str(unit.get("tinh") or ""))
        if province:
            slugs.add(province["slug"])
    return slugs


def catalog(scope: dict) -> dict:
    """Danh mục cho phạm vi đã phân giải (app/dashboard/scope.py)."""
    see_all = scope["scopeKind"] == "all"
    slug = "" if see_all else account_province_slug(scope)
    role = (scope.get("self") or {}).get("role") or scope.get("role")
    handfree = {p["key"]: p for p in public_list()}
    core = {p["key"]: p for p in core_public_list()}
    # Thứ tự: thủ tục có cả hai kênh theo thứ tự danh mục trợ lý, rồi thủ tục chỉ Auto Fill theo danh mục lõi.
    keys = [*handfree, *(k for k in core if k not in handfree)]
    deployed = _deployed_slugs(scope) if see_all else ({slug} if slug else set())
    items: list[dict] = []
    counts: dict[str, int] = {}
    for key in keys:
        hf, af = handfree.get(key), core.get(key)
        proc = hf or af
        # Tài khoản Bộ Công an: danh mục chỉ gồm thủ tục Bộ Công an, đúng như trợ lý hiện cho tài khoản này.
        if not see_all and not allowed_for_role(key, role):
            continue
        # Mỗi kênh tự giới hạn tỉnh: Auto Fill suy từ cổng/tiền tố tên (procedure_province_slugs), trợ lý theo
        # `provinceOnly` + bảng hoàn thiện. Kênh nào giới hạn tỉnh là thủ tục riêng của tỉnh đó (cổng / nghiệp vụ
        # của tỉnh); thủ tục áp dụng cho tỉnh khi ÍT NHẤT một kênh chạy ở tỉnh đó.
        af_only = procedure_province_slugs(af) if af else []
        hf_only = sorted((hf or {}).get("provinceOnly") or [])
        only = sorted(set(af_only) | set(hf_only))
        if not see_all:
            af_ok = af is not None and (not af_only or slug in af_only)
            hf_ok = hf is not None and is_visible_in_province(hf, slug)
            if not (af_ok or hf_ok) or (only and slug not in only):
                continue
        for item_slug in only:
            counts[item_slug] = counts.get(item_slug, 0) + 1
        items.append({
            "key": key,
            "label": proc.get("label") or key,
            "shortLabel": proc.get("shortLabel") or None,
            "codes": _codes(proc),
            "support": _support(proc),
            "provinces": [{"slug": s, "name": _province_name(s)} for s in only],
            # Kênh theo tỉnh (web tự ghép): Auto Fill chạy ở mọi tỉnh khi `autofillProvinces` rỗng, ngược lại chỉ
            # các tỉnh đó; Trợ lý người dân chạy ở mọi tỉnh áp dụng trừ `handfreeOff` (chưa hoàn thiện / khoá tỉnh).
            "autofill": af is not None,
            "autofillProvinces": af_only,
            "handfree": hf is not None,
            "handfreeOff": sorted(
                s for s in deployed
                if hf is not None and (not only or s in only) and not is_visible_in_province(hf, s)
            ),
        })
    provinces = sorted(
        ({"slug": s, "name": _province_name(s), "count": counts.get(s, 0)} for s in (deployed | set(counts)) if see_all),
        key=lambda p: fold(p["name"]),
    )
    return {
        "scopeKind": scope["scopeKind"],
        "province": {"slug": slug, "name": _province_name(slug)} if slug else None,
        "items": items,
        # Admin: mọi tỉnh đã có đơn vị + tỉnh có thủ tục riêng (ô lọc), `count` = số thủ tục riêng của tỉnh.
        "provinces": provinces if see_all else (
            [{"slug": slug, "name": _province_name(slug), "count": counts.get(slug, 0)}] if slug and counts.get(slug) else []
        ),
    }
