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


def _run_mode(values: dict, mode: str = "owner_as_submitter"):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(compact, {"submitterMode": mode})
    return {field["name"]: field["value"] for field in fields}, warnings


_NGUOI_MAT = {
    "NguoiMat_HoTen": "TRẦN THỊ HOA",
    "NguoiMat_NgaySinh": "05/06/1940",
    "NguoiMat_GioiTinh": "Nữ",
    "NguoiMat_SoDinhDanh": "068140000123",
    "NguoiMat_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Đơn Dương", "diaChi": "Thạnh Nghĩa"},
}


def test_owner_mode_lay_nguoi_mat_lam_chu_ho_so():
    """Bật "Lấy người nộp theo tờ khai" → chủ hồ sơ = người mất, người nộp = người đề nghị, không tick tự nộp."""
    got, warnings = _run_mode({**_DANG_VAN_LAM, **_NGUOI_MAT})
    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert got["data[identityNumber]"] == "068080000292"
    assert got["data[ownerFullname]"] == "TRẦN THỊ HOA"
    assert got["data[ownerIdentityNumber]"] == "068140000123"
    assert got["data[ownerBirthday]"] == "05/06/1940"
    assert got["data[ownerGender]"] == "Nữ"
    assert not warnings


def test_owner_mode_bo_qua_nguoi_nop_phu_va_mo_neo_ui():
    """Toggle bật vẫn KHÔNG so mỏ neo UI: người đề nghị trên tờ khai là người nộp, NguoiNop lỡ trích bị bỏ."""
    values = {**_DANG_VAN_LAM, **_NGUOI_MAT, "NguoiNop_HoTen": "Phan Mỹ Dung", "NguoiNop_SoDinhDanh": "024193003267"}
    compact = [{"name": k, "value": v} for k, v in values.items()]
    fields, _ = mapper.enrich(compact, {
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "Người Khác", "applicantIdentityNumber": "999999999999"},
    })
    got = {f["name"]: f["value"] for f in fields}
    assert got["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert got["data[ownerFullname]"] == "TRẦN THỊ HOA"
    assert "Phan Mỹ Dung" not in str(list(got.values()))


def test_owner_mode_khong_doc_duoc_nguoi_mat_thi_canh_bao():
    got, warnings = _run_mode(_DANG_VAN_LAM)
    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[fullname]"] == "ĐẶNG VĂN LÂM"
    assert "data[ownerFullname]" not in got
    assert any("người chết" in w for w in warnings)


def test_tat_toggle_giu_logic_cu_khong_lay_nguoi_mat():
    got, _ = _run({**_DANG_VAN_LAM, **_NGUOI_MAT}, {"applicantFullname": "ĐẶNG VĂN LÂM", "applicantIdentityNumber": "068080000292"})
    assert got["data[isOwnerDossierCheck]"] is True
    assert "TRẦN THỊ HOA" not in str(list(got.values()))


def test_toggle_bat_thi_runner_trich_them_nguoi_mat():
    assert mapper.is_deceased_owner({"submitterMode": "owner_as_submitter"})
    assert mapper.is_deceased_owner({mapper.DECEASED_AS_OWNER_OPTION: True})
    assert not mapper.is_deceased_owner({})
    assert not mapper.is_deceased_owner({"submitterMode": "anchor"})


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


def test_nghia_hung_account_sets_clear_email_flag_only_for_this_procedure():
    """Cờ xoá email do server đặt theo tài khoản; client tự gửi cờ cho xã khác bị gỡ."""
    nghia_hung = {"tinh": "Tỉnh Ninh Bình", "xa": "Xã Nghĩa Hưng"}
    other = {"tinh": "Tỉnh Ninh Bình", "xa": "Xã Nghĩa Hưng Đông"}
    key = mapper.PROCEDURE_KEY
    assert mapper.with_account_process_options({}, nghia_hung, key)[mapper.CLEAR_EMAIL_OPTION] is True
    assert mapper.CLEAR_EMAIL_OPTION not in mapper.with_account_process_options(
        {mapper.CLEAR_EMAIL_OPTION: True}, other, key
    )
    assert mapper.CLEAR_EMAIL_OPTION not in mapper.with_account_process_options({}, nghia_hung, "ho-tro-mai-tang")


def test_binh_chuong_account_sets_deceased_as_owner_flag_only_for_this_procedure():
    """Xã Bình Chương (Quảng Ngãi) lấy người chết làm chủ hồ sơ như Cam Đường; xã khác bị gỡ cờ."""
    binh_chuong = {"tinh": "Tỉnh Quảng Ngãi", "xa": "Xã Bình Chương"}
    key = mapper.PROCEDURE_KEY
    assert mapper.with_account_process_options({}, binh_chuong, key)[mapper.DECEASED_AS_OWNER_OPTION] is True
    for other in ({"tinh": "Tỉnh Quảng Ngãi", "xa": "Xã Bình Châu"}, {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Bình Chương"}):
        assert mapper.DECEASED_AS_OWNER_OPTION not in mapper.with_account_process_options(
            {mapper.DECEASED_AS_OWNER_OPTION: True}, other, key
        )
    assert mapper.DECEASED_AS_OWNER_OPTION not in mapper.with_account_process_options({}, binh_chuong, "ho-tro-mai-tang")


def test_clear_email_flag_emits_clear_after_requester_block():
    compact = [{"name": k, "value": v} for k, v in _DANG_VAN_LAM.items()]
    fields, _ = mapper.enrich(compact, {"submitterMode": "owner_as_submitter", mapper.CLEAR_EMAIL_OPTION: True})
    email = [f for f in fields if f["name"] == "data[email]"]
    assert email == [{"name": "data[email]", "comp": "dom-input", "value": "", "clear": True}]
    assert fields[-1]["name"] == "data[email]"
    got = {f["name"]: f["value"] for f in fields}
    assert got["data[fullname]"] == "ĐẶNG VĂN LÂM"          # các ô khác vẫn điền như thường


def test_without_flag_email_untouched():
    got, _ = _run_mode(_DANG_VAN_LAM)
    assert "data[email]" not in got
