"""Đọc và chuẩn hóa danh mục địa giới hành chính Việt Nam sau sáp nhập 2025.

Danh mục được đóng gói cùng backend để production không phụ thuộc đường dẫn của repo
tham khảo. Dữ liệu chỉ được đọc một lần khi process khởi động.
"""
import json
import re
import unicodedata
from pathlib import Path

from app.core.errors import AppError

_DATA_FILE = Path(__file__).parent / "data" / "vn_provinces_wards.json"

# File nguồn còn một số cách đặt dấu kiểu cũ, trong khi option trên cổng DVC dùng kiểu mới.
# Chỉ đổi ở cuối âm tiết để không làm hỏng các tên đúng như "Hoàng" hoặc "Quỳnh".
_TONE_O = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
}
_TONE_U = {"uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy"}
_RE_TONE_O = re.compile("(" + "|".join(_TONE_O) + r")(?!\w)")
_RE_TONE_U = re.compile("(?<![qQ])(" + "|".join(_TONE_U) + r")(?!\w)")
_WARD_TYPE = re.compile(r"^(Phường|Xã|Đặc khu)\s+", re.IGNORECASE)

# Tên HIỂN THỊ khác tên trong danh mục. Chỉ đổi nhãn đọc cho cán bộ ("label"); "text" vẫn là tên
# đúng như option trên cổng DVC nên mọi chỗ khớp/điền hộ (chọn cơ quan thực hiện, lưu tài khoản)
# không bị lệch. Đổi thẳng "text" là trợ lý không tìm ra option "Tỉnh Bắc Ninh" trên cổng nữa.
_DISPLAY_LABEL = {"Tỉnh Bắc Ninh": "Thành phố Bắc Ninh"}


def _modern_tone(value: str) -> str:
    value = _RE_TONE_O.sub(lambda match: _TONE_O[match.group(1)], value)
    return _RE_TONE_U.sub(lambda match: _TONE_U[match.group(1)], value)


def _fold(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ).casefold().strip()


def _load() -> tuple[list[dict], dict[str, dict]]:
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    provinces: list[dict] = []
    wards_by_slug: dict[str, dict] = {}
    for item in raw["provinces"]:
        slug = item["code_name"].replace("_", "")
        text = _modern_tone(item["full_name"])
        province = {
            "text": text,
            "slug": slug,
            "name": _modern_tone(item["name"]),
            "label": _DISPLAY_LABEL.get(text, text),
        }
        communes = [_modern_tone(ward["full_name"]) for ward in item["wards"]]
        provinces.append(province)
        wards_by_slug[slug] = {"slug": slug, "province": text, "communes": communes}
    return provinces, wards_by_slug


PROVINCES, WARDS_BY_SLUG = _load()


def province_by_slug(slug: str) -> dict | None:
    return next((province for province in PROVINCES if province["slug"] == slug), None)


def _find_province(value: str) -> dict | None:
    folded = _fold(value)
    return next(
        (
            province
            for province in PROVINCES
            if folded in {_fold(province["text"]), _fold(province["name"])}
        ),
        None,
    )


def canonical_location(
    tinh: str | None,
    xa: str | None,
) -> tuple[str | None, str | None]:
    """Kiểm tra quan hệ tỉnh-xã và trả tên đầy đủ chuẩn để lưu tài khoản.

    Giá trị rỗng giữ nguyên kiểu None/chuỗi rỗng để không làm thay đổi contract update
    hiện tại. Tên trần của dữ liệu cũ ("Bắc Ninh", "Song Liễu") vẫn được nhận diện.
    """
    province_input = (tinh or "").strip()
    ward_input = (xa or "").strip()
    if not province_input:
        if ward_input:
            raise AppError(
                "INVALID_LOCATION",
                "Vui lòng chọn tỉnh/thành trước khi chọn xã/phường.",
                422,
            )
        return (None if tinh is None else "", None if xa is None else "")

    province = _find_province(province_input)
    if not province:
        raise AppError(
            "INVALID_PROVINCE",
            f"Tỉnh/thành '{province_input}' không nằm trong danh mục hiện hành.",
            422,
        )

    if not ward_input:
        return province["text"], None if xa is None else ""

    communes = WARDS_BY_SLUG[province["slug"]]["communes"]
    ward_folded = _fold(ward_input)
    exact = next((ward for ward in communes if _fold(ward) == ward_folded), None)
    if exact:
        return province["text"], exact

    # Tài khoản cũ có thể lưu tên trần, không có tiền tố Phường/Xã/Đặc khu. Chỉ nhận
    # khi có đúng một kết quả để không tự chọn nhầm hai đơn vị trùng tên trong cùng tỉnh.
    legacy_matches = [
        ward
        for ward in communes
        if _fold(_WARD_TYPE.sub("", ward)) == ward_folded
    ]
    if len(legacy_matches) == 1:
        return province["text"], legacy_matches[0]

    raise AppError(
        "INVALID_LOCATION",
        f"'{ward_input}' không thuộc {province['text']} hoặc không còn trong danh mục hiện hành.",
        422,
    )
