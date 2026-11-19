"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (form Form.io cổng Bộ GD&ĐT) cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dinh_danh, review

_OWNER_CHECK = "data[isOwnerDossier]"
_DINH_DANH = dinh_danh.INSPECTOR.key
_PHIEU = (_DINH_DANH, ("data[ToiTen]", "data[Sodinhdanh]", "data[sinhNam]", "data[nguoidenghi]"))
# Sửa họ tên chủ văn bằng có thể làm căn cước khớp tên → mapper định tuyến lại người nộp / chủ hồ sơ theo căn cước đó.
_NGUOI = (
    (_DINH_DANH, ("data[fullname]", "data[identityNumber]", "data[gender]", "data[birthday]", "data[identityDate]",
                  "data[idIssuePlace]", "data[province]", "data[district]", "data[address]", "data[phoneNumber]")),
    (_DINH_DANH, ("data[ownerFullname]", "data[ownerGender]", "data[ownerIdentityNumber]", "data[ownerBirthday]",
                  "data[ownerIdentityDate]", "data[ownerIdentityAgency22]", "data[ownerPhoneNumber]",
                  "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[lienhe]")),
)
# Ô xã đi kèm ô tỉnh: đổi tỉnh thì cổng xoá danh sách xã đã chọn.
_FOLLOWS = {"data[district]": "data[province]", "data[ownerDistrict]": "data[ownerProvince]"}
_LAYOUT = (_OWNER_CHECK, "data[ChuHS]")


def _ui(values: dict, options: dict, ocr_text: str) -> list[dict]:
    fields, _ = mapper.enrich([{"name": name, "value": value} for name, value in values.items()], options,
                              ocr_text=ocr_text)
    normalize_ui_dates(fields)
    # Ô "xoá giá trị VNeID tự đổ" chỉ dành cho lượt đầu: bản vá chỉ ghi, không xoá.
    return [field for field in fields if not field.get("clear")]


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict,
                ocr_text: str = "") -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension; ``options``,
    ``ocr_text``: đầu vào mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options, ocr_text)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    after = _ui(verdict.values, options, ocr_text)
    then = {f.get("name"): f.get("value") for f in after}
    unchanged = {f.get("name"): f.get("value") for f in _ui(values, options, ocr_text)}
    if any(then.get(name) != unchanged.get(name) for name in _LAYOUT):
        return out
    blocks = [_PHIEU]
    # Đã tích "Người nộp là chủ hồ sơ": cổng chép Phần I xuống và khoá khối chủ hồ sơ → không ghi lại hai khối người.
    if not then.get(_OWNER_CHECK):
        blocks += _NGUOI
    by: dict[str, str] = {}
    for inspector, cluster in blocks:
        by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    for ward, province in _FOLLOWS.items():
        if province in by:
            by.setdefault(ward, by[province])
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]}
                     for field in ban_va.diff(base_fields, after, by, follows=_FOLLOWS)]
    return out
