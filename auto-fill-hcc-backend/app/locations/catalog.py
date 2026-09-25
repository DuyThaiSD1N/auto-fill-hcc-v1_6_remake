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
        province = {"text": text, "slug": slug, "name": _modern_tone(item["name"])}
        communes = [_modern_tone(ward["full_name"]) for ward in item["wards"]]
        provinces.append(province)
        wards_by_slug[slug] = {"slug": slug, "province": text, "communes": communes}
    return provinces, wards_by_slug


PROVINCES, WARDS_BY_SLUG = _load()

# Tên Phường/Xã mà khối "Chọn cơ quan thực hiện" của Cổng DVC quốc gia (dichvucong.gov.vn) đang
# liệt kê, khi cổng CHƯA cập nhật theo danh mục hiện hành. Hai extension gõ đúng chuỗi này vào ô
# tìm kiếm của cổng, lệch tiền tố Xã/Phường là không ra option nào và ô xã bị bỏ trống.
# CHỈ dùng cho bước chọn cơ quan: WARDS_BY_SLUG giữ tên hiện hành vì biểu mẫu kê khai
# (area_remap) và tài khoản (canonical_location) vẫn cần "Phường ...". Cổng cập nhật rồi thì xóa dòng.
_PORTAL_AGENCY_WARDS: dict[str, dict[str, str]] = {
    "bacninh": {"Phường Hiệp Hòa": "Xã Hiệp Hòa"},
}


def portal_agency_ward(province: str | None, ward: str | None) -> str:
    """Tên xã để chọn ở khối "Chọn cơ quan thực hiện" của cổng; không có ngoại lệ thì giữ nguyên.

    `province` nhận slug ("bacninh"), tên đầy đủ hoặc tên trần như các chỗ khác trong module.
    """
    ward_text = (ward or "").strip()
    if not ward_text:
        return ward_text
    province_text = (province or "").strip()
    found = province_by_slug(province_text) or _find_province(province_text)
    if not found:
        return ward_text
    aliases = _PORTAL_AGENCY_WARDS.get(found["slug"], {})
    ward_folded = _fold(ward_text)
    return next(
        (portal for current, portal in aliases.items() if _fold(current) == ward_folded),
        ward_text,
    )


def portal_agency_wards_by_slug() -> dict[str, dict]:
    """WARDS_BY_SLUG với tên xã theo khối chọn cơ quan của cổng — cho danh mục trả extension."""
    result: dict[str, dict] = {}
    for slug, data in WARDS_BY_SLUG.items():
        aliases = _PORTAL_AGENCY_WARDS.get(slug)
        if not aliases:
            result[slug] = data
            continue
        result[slug] = {**data, "communes": [aliases.get(ward, ward) for ward in data["communes"]]}
    return result


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


def ward_name_matches(tinh: str | None, ward_name: str | None) -> tuple[str | None, list[str]]:
    """Tra xã theo TÊN trong đúng tỉnh → (tên tỉnh chuẩn, các xã khớp với tên đầy đủ).

    File nhập tài khoản hàng loạt chỉ ghi tên trần ("Bồng Lai"); tài khoản phải lưu tên đầy đủ
    của danh mục ("Phường Bồng Lai"). Ghi sẵn tên đầy đủ thì khớp chính xác trước. Trả NHIỀU kết
    quả khi một tỉnh có hai đơn vị trùng tên trần (Phường X / Xã X): người gọi phải báo, KHÔNG được
    tự chọn một bên. Tỉnh không có trong danh mục → (None, []).
    """
    province = _find_province((tinh or "").strip())
    if not province:
        return None, []
    raw = " ".join((ward_name or "").split())
    if not raw:
        return province["text"], []
    communes = WARDS_BY_SLUG[province["slug"]]["communes"]
    bare = lambda ward: _WARD_TYPE.sub("", ward)  # noqa: E731

    # So CÓ DẤU trước: bỏ dấu thì "Văn Lang"/"Văn Lăng" (hai xã khác nhau cùng tỉnh) thành một,
    # file ghi đúng dấu vẫn bị báo trùng oan. Chuẩn vị trí dấu (Hoà→Hòa) như danh mục đã làm.
    # Chỉ khi có dấu không ra gì mới lùi về so bỏ dấu (file gõ thiếu dấu).
    toned = lambda value: _modern_tone(unicodedata.normalize("NFC", value)).casefold()  # noqa: E731
    for key in (toned, _fold):
        wanted = key(raw)
        for candidate in (lambda ward: ward, bare):
            found = [ward for ward in communes if key(candidate(ward)) == wanted]
            if found:
                return province["text"], found
    return province["text"], []


def province_name_variants(value: str) -> list[str]:
    """Mọi cách ghi tên một tỉnh đang có thể nằm trong DB, để lọc bằng $in thay vì $regex.

    Tài khoản cũ lưu tên trần ("Đà Nẵng"), bản mới lưu tên đầy đủ ("Thành phố Đà Nẵng"). So
    chuỗi thẳng thì sót một nửa; fold dấu thì Mongo không fold hộ được. Liệt kê sẵn là cách
    duy nhất vừa đúng vừa còn dùng được index trên `tinh`.

    Tỉnh không có trong danh mục (dữ liệu rác) → trả chính chuỗi đó, lọc ra đúng nó.
    """
    text = (value or "").strip()
    if not text:
        return []
    province = _find_province(text)
    if not province:
        return [text]
    return sorted({text, province["text"], province["name"]})


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
