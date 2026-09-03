"""Đổi tỉnh/xã của tài khoản thành location chuẩn cho hội thoại Handfree."""
import re
import unicodedata

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG

_WARD_TYPE = re.compile(r"^(Phường|Xã|Đặc khu)\s+", re.IGNORECASE)


def _fold(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ).casefold().strip()


def location_for(tinh: str | None, xa: str | None) -> dict | None:
    province_value = (tinh or "").strip()
    ward_value = (xa or "").strip()
    if not province_value:
        return None

    folded_province = _fold(province_value)
    province = next(
        (
            item
            for item in PROVINCES
            if folded_province in {_fold(item["text"]), _fold(item["name"])}
        ),
        None,
    )
    if not province:
        return None

    ward = ""
    if ward_value:
        communes = WARDS_BY_SLUG[province["slug"]]["communes"]
        folded_ward = _fold(ward_value)
        ward = next((item for item in communes if _fold(item) == folded_ward), "")
        if not ward:
            legacy = [
                item
                for item in communes
                if _fold(_WARD_TYPE.sub("", item)) == folded_ward
            ]
            if len(legacy) == 1:
                ward = legacy[0]

    return {
        "province": province["text"],
        "province_slug": province["slug"],
        "ward": ward,
    }
