"""Cấp cơ quan tiếp nhận (UBND xã hay Sở) cho thủ tục DVCQG mà cả hai cấp cùng nhận hồ sơ.

Thủ tục khai ``agencyLevelByAccount = {"xa": {...}, "so": {...}}`` — ở ke_khai_links.json (Auto Fill) và registry
trợ lý (handfree). Mỗi nhánh là chính các trường chọn cơ quan sẵn có của kênh đó (selectSo / submitCardIncludes,
agencyProvinceOnly / agencySoFirst / agencyCardIncludes), gộp đè lên cấu hình thủ tục theo cấp tính ở đây.

Luật: tài khoản Hành chính công tỉnh luôn nộp Sở; tài khoản khác có xã đang chọn thì nộp UBND xã đó, chưa có xã thì
nộp Sở (cổng không tìm được UBND xã khi chỉ có tỉnh). Auto Fill giữ bản JS của đúng luật này (popup.js
``agencyLevelFor``) vì xã do cán bộ chọn tay trên popup BE không biết.
"""

LEVEL_KEY = "agencyLevelByAccount"


def agency_level(role: object, ward: object) -> str:
    if str(role or "").strip() == "province" or not str(ward or "").strip():
        return "so"
    return "xa"


def with_agency_level(item: dict, role: object, ward: object) -> dict:
    """Cấu hình thủ tục đã gộp nhánh theo cấp; thủ tục không khai ``agencyLevelByAccount`` giữ nguyên."""
    branches = item.get(LEVEL_KEY)
    if not isinstance(branches, dict):
        return item
    return {**item, **(branches.get(agency_level(role, ward)) or {})}
