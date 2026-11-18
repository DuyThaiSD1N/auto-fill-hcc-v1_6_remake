"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (form Form.io cổng Bộ Y tế) cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, dinh_danh, review

_OWNER_CHECK = "data[isOwnerDossierCheck]"
_DINH_DANH = dinh_danh.INSPECTOR.key
_DIA_CHI = dia_chi.INSPECTOR.key
_BLOCKS = (
    (_DINH_DANH, ("data[fullname]", "data[identityNumber]", "data[birthday]", "data[gender]")),
    (_DINH_DANH, ("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerBirthday]", "data[ownerGender]")),
    (_DIA_CHI, ("data[province]", "data[district]", "data[address]")),
    (_DIA_CHI, ("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]")),
)
# Ô xã đi kèm ô tỉnh: đổi tỉnh thì cổng xoá danh sách xã đã chọn.
_FOLLOWS = {"data[district]": "data[province]", "data[ownerDistrict]": "data[ownerProvince]"}


def _ui(values: dict, options: dict) -> list[dict]:
    fields, _ = mapper.enrich([{"name": name, "value": value} for name, value in values.items()], options)
    normalize_ui_dates(fields)
    return fields


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension; ``options``:
    options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    after = _ui(verdict.values, options)
    then = {f.get("name"): f.get("value") for f in after}
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
    unchanged = {f.get("name"): f.get("value") for f in _ui(values, options)}
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    # Đợt 2 KHÔNG đổi ô "Người nộp là chủ hồ sơ" (cổng chép / xoá khối chủ hồ sơ khi đổi). Phán quyết làm ô này đổi (vai
    # người nộp đổi theo) thì form đang theo trạng thái cũ → không vá gì.
    if first.get(_OWNER_CHECK) != then.get(_OWNER_CHECK):
        return out
    by: dict[str, str] = {}
    for inspector, cluster in _BLOCKS:
        by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    for ward, province in _FOLLOWS.items():
        if province in by:
            by.setdefault(ward, by[province])
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by, follows=_FOLLOWS)]
    return out
