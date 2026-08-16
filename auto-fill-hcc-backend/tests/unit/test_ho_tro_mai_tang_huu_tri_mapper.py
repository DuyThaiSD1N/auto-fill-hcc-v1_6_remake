"""Regression cho hai vai trò của mai táng người hưởng hưu trí xã hội."""

from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process import mapper
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.runner import (
    _death_declarant_section,
    _owner_section,
    _requester_context,
)
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.schema import ALLOWED


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(
        compact,
        {"formContext": form_context or {}},
    )
    return {field["name"]: field["value"] for field in fields}, warnings


_DANG_VAN_LAM = {
    "ChuHoSo_HoTen": "ĐẶNG VĂN LÂM",
    "ChuHoSo_NgaySinh": "03/03/1980",
    "ChuHoSo_SoDinhDanh": "068080000292",
    "ChuHoSo_NgayCap": "08/07/2022",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "diaChi": "Thạnh Nghĩa",
    },
    "ChuHoSo_DienThoai": "0974814031",
}


def test_schema_only_exposes_owner_and_requester_roles():
    assert "ChuHoSo_HoTen" in ALLOWED
    assert "NguoiNop_HoTen" in ALLOWED
    assert not any(name.startswith(("Person", "ToKhai_")) for name in ALLOWED)


def test_owner_matching_ui_ticks_checkbox_and_emits_owner_birthday():
    fields, warnings = _run(
        _DANG_VAN_LAM,
        {
            "applicantFullname": "ĐẶNG VĂN LÂM",
            "applicantIdentityNumber": "068080000292",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is True
    assert fields["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert fields["data[birthday]"] == "03/03/1980"
    assert fields["data[identityNumber]"] == "068080000292"
    assert fields["data[phoneNumber]"] == "0974814031"
    assert fields["data[ownerBirthday]"] == "03/03/1980"
    assert "data[gender]" not in fields
    assert "data[ownerFullname]" not in fields
    assert not warnings


def test_mismatching_ui_keeps_owner_and_does_not_promote_deceased():
    fields, warnings = _run(
        _DANG_VAN_LAM,
        {
            "applicantFullname": "VŨ ĐÌNH THIẾT",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "ĐẶNG VĂN LÂM"
    assert fields["data[ownerIdentityNumber]"] == "068080000292"
    assert "ĐẶNG VĂN LONG" not in fields.values()
    assert "không điền phần người nộp" in warnings[0]


def test_both_ui_anchors_must_match_same_person():
    fields, warnings = _run(
        _DANG_VAN_LAM,
        {
            "applicantFullname": "ĐẶNG VĂN LÂM",
            "applicantIdentityNumber": "999999999999",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "ĐẶNG VĂN LÂM"
    assert warnings


def test_distinct_verified_requester_fills_both_roles():
    values = {
        **_DANG_VAN_LAM,
        "NguoiNop_HoTen": "VŨ ĐÌNH THIẾT",
        "NguoiNop_NgaySinh": "26/04/2003",
        "NguoiNop_SoDinhDanh": "040203015844",
    }
    fields, warnings = _run(
        values,
        {
            "applicantFullname": "VŨ ĐÌNH THIẾT",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert fields["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert fields["data[ownerFullname]"] == "ĐẶNG VĂN LÂM"
    assert not warnings


async def test_context_isolates_owner_and_death_declarant_from_deceased():
    form_04 = """I. THÔNG TIN NGƯỜI CHẾT ĐƯỢC MAI TÁNG
Họ và tên: ĐẶNG VĂN LONG
II. THÔNG TIN CƠ QUAN, TỔ CHỨC, HỘ GIA ĐÌNH, CÁ NHÂN ĐỨNG RA MAI TÁNG
2. Trường hợp hộ gia đình, cá nhân đứng ra mai táng
a) Họ và tên (Chủ hộ hoặc người đại diện): ĐẶNG VĂN LÂM
Ngày, tháng, năm sinh: 03/03/1980
Giấy CCCD số: 068080000292 cấp ngày: 08/07/2022
Số điện thoại: 0974814031
Tôi xin cam đoan những lời khai trên là đúng.
"""
    death_extract = """TRÍCH LỤC KHAI TỬ
Họ, chữ đệm, tên: ĐẶNG VĂN LONG
Số định danh cá nhân: 068049000055
Họ, chữ đệm, tên người đi khai tử: ĐẶNG VĂN LÂM
Giấy tờ tùy thân: Thẻ căn cước công dân số 068080000292, cấp ngày 08/07/2022
NGƯỜI KÝ TRÍCH LỤC
"""

    assert "ĐẶNG VĂN LONG" not in _owner_section(form_04)
    declarant = _death_declarant_section(death_extract)
    assert "ĐẶNG VĂN LÂM" in declarant
    assert "ĐẶNG VĂN LONG" not in declarant
    assert "068049000055" not in declarant

    context = await _requester_context(
        [
            {"name": "to-khai.jpg", "text": form_04},
            {"name": "trich-luc.jpg", "text": death_extract},
        ],
        {"formContext": {
            "applicantFullname": "ĐẶNG VĂN LÂM",
            "applicantIdentityNumber": "068080000292",
        }},
    )

    assert 'result="owner_match"' in context
    assert "owner_support_ocr" in context
    assert "068049000055" not in context
    assert "ĐẶNG VĂN LONG" not in context
