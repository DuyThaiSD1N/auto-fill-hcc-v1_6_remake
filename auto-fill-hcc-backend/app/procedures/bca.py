"""Thủ tục Bộ Công an — tài khoản Hành chính công Bộ Công an (role "bca") chỉ thấy, tìm và mở các thủ tục này.

Nhận diện theo cấu hình sẵn có của thủ tục, không giữ danh sách tay: thủ tục chạy trên cổng Bộ Công an /
Cổng dịch vụ công quản lý cư trú (`bcaPortal`, `requiresCapability` supportsBca*, URL nhận diện hoặc link kê
khai thuộc hai cổng đó). Thủ tục Bộ Công an thêm sau theo đúng cách cấu hình là tự vào nhóm.
"""
from functools import lru_cache

from app.users.roles import is_bca_role

_BCA_HOSTS = ("bocongan.gov.vn", "dancuquocgia.gov.vn")


def _looks_bca(entry: dict) -> bool:
    if entry.get("bcaPortal"):
        return True
    caps = entry.get("requiresCapability") or []
    if isinstance(caps, str):
        caps = [caps]
    if any(str(c).startswith("supportsBca") for c in caps):
        return True
    detect = entry.get("detect") or {}
    urls = [*(detect.get("urlScope") or []), *(detect.get("urlIncludes") or []), str(entry.get("keKhaiUrl") or "")]
    return any(host in str(url) for url in urls for host in _BCA_HOSTS)


@lru_cache(maxsize=1)
def bca_keys() -> frozenset[str]:
    # Import muộn: registry handfree nạp registry core, module này được cả hai phía dùng.
    from app.channels.handfree.procedure_registry import public_list as handfree_list
    from app.procedures.registry import PROCEDURES

    return frozenset(str(p["key"]) for p in [*handfree_list(), *PROCEDURES] if _looks_bca(p))


def is_bca_procedure(key: str | None) -> bool:
    return str(key or "") in bca_keys()


def allowed_for_role(key: str | None, role: object) -> bool:
    """Tài khoản Bộ Công an chỉ làm thủ tục Bộ Công an; tài khoản khác không đổi gì."""
    return not is_bca_role(role) or is_bca_procedure(key)


def for_role(items: list[dict], role: object) -> list[dict]:
    """Lọc danh sách thủ tục / link kê khai (mỗi phần tử có `key`) theo role tài khoản."""
    if not is_bca_role(role):
        return items
    return [item for item in items if is_bca_procedure(item.get("key"))]
