"""Unit tests cho mapper hai vai trò của thủ tục hỗ trợ mai táng."""

from app.pipelines.ho_tro_mai_tang.process import mapper
from app.pipelines.ho_tro_mai_tang.process.runner import _owner_section, _requester_context


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(
        compact,
        {"formContext": form_context or {}},
    )
    return {field["name"]: field["value"] for field in fields}, warnings


_KA_TUI = {
    "ChuHoSo_HoTen": "KA TUI",
    "ChuHoSo_NgaySinh": "01/01/1975",
    "ChuHoSo_SoDinhDanh": "068175007976",
    "ChuHoSo_NgayCap": "27/12/2002",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "diaChi": "Kambutte",
    },
    "ChuHoSo_DienThoai": "0378877127",
}


def test_owner_matching_ui_is_requester_and_ticks_checkbox():
    fields, warnings = _run(
        _KA_TUI,
        {
            "applicantFullname": "KA TUI",
            "applicantIdentityNumber": "068175007976",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is True
    assert fields["data[fullname]"] == "KA TUI"
    assert fields["data[birthday]"] == "01/01/1975"
    assert fields["data[identityNumber]"] == "068175007976"
    assert fields["data[identityDate]"] == "27/12/2002"
    assert fields["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert fields["data[province]"] == "Lâm Đồng"
    assert fields["data[district]"] == "Đơn Dương"
    assert fields["data[address]"] == "Kambutte"
    assert fields["data[phoneNumber]"] == "0378877127"
    assert fields["data[ownerBirthday]"] == "01/01/1975"
    assert "data[ownerFullname]" not in fields
    assert not warnings


def test_missing_requester_context_still_returns_owner_normally():
    fields, warnings = _run(_KA_TUI)

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "KA TUI"
    assert fields["data[ownerBirthday]"] == "01/01/1975"
    assert fields["data[ownerIdentityNumber]"] == "068175007976"
    assert fields["data[ownerPhoneNumber]"] == "0378877127"
    assert fields["data[ownerNation]"] == "Việt Nam"
    assert not warnings


def test_mismatching_ui_keeps_owner_and_does_not_fill_requester():
    fields, warnings = _run(
        _KA_TUI,
        {
            "applicantFullname": "HA YONG",
            "applicantIdentityNumber": "012345678901",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "KA TUI"
    assert "không điền phần người nộp" in warnings[0]


def test_both_ui_anchors_must_match_owner():
    fields, warnings = _run(
        _KA_TUI,
        {
            "applicantFullname": "KA TUI",
            "applicantIdentityNumber": "999999999999",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in fields
    assert fields["data[ownerFullname]"] == "KA TUI"
    assert warnings


def test_distinct_verified_requester_fills_both_roles():
    values = {
        **_KA_TUI,
        "NguoiNop_HoTen": "TRẦN THỊ THANH THẢO",
        "NguoiNop_NgaySinh": "17/06/1992",
        "NguoiNop_GioiTinh": "Nữ",
        "NguoiNop_SoDinhDanh": "036192014693",
        "NguoiNop_NgayCap": "17/06/2023",
        "NguoiNop_NoiCap": "Bộ Công an",
        "NguoiNop_NoiCuTru": {
            "tinh": "Ninh Bình",
            "xa": "Gia Thắng",
            "diaChi": "Xóm 2",
        },
    }
    fields, warnings = _run(
        values,
        {
            "applicantFullname": "TRẦN THỊ THANH THẢO",
            "applicantIdentityNumber": "036192014693",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is False
    assert fields["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert fields["data[identityNumber]"] == "036192014693"
    assert fields["data[ownerFullname]"] == "KA TUI"
    assert fields["data[ownerIdentityNumber]"] == "068175007976"
    assert not warnings


def test_same_person_returned_in_both_groups_is_not_duplicated():
    values = {
        **_KA_TUI,
        "NguoiNop_HoTen": "KA TUI",
        "NguoiNop_SoDinhDanh": "068175007976",
    }
    fields, warnings = _run(
        values,
        {
            "applicantFullname": "KA TUI",
            "applicantIdentityNumber": "068175007976",
        },
    )

    assert fields["data[isOwnerDossierCheck]"] is True
    assert fields["data[fullname]"] == "KA TUI"
    assert fields["data[ownerBirthday]"] == "01/01/1975"
    assert "data[ownerFullname]" not in fields
    assert not warnings


async def test_current_form_04_owner_block_matches_ui_requester_context():
    ocr = """I. THÔNG TIN NGƯỜI CHẾT ĐƯỢC MAI TÁNG
Họ và tên: KA NANG
II. THÔNG TIN CƠ QUAN, TỔ CHỨC, HỘ GIA ĐÌNH, CÁ NHÂN ĐỨNG RA MAI TÁNG
2. Trường hợp hộ gia đình, cá nhân đứng ra mai táng
a) Họ và tên (Chủ hộ hoặc người đại diện): KA TUI
Ngày, tháng, năm sinh: 01/01/1975
Giấy CCCD số: 068175007976 cấp ngày: 27/12/2002
b) Hộ khẩu thường trú: Kambutte, xã Đơn Dương, Lâm Đồng
Tôi xin cam đoan những lời khai trên là đúng.
"""

    assert "KA TUI" in _owner_section(ocr)
    assert "KA NANG" not in _owner_section(ocr)

    context = await _requester_context(
        [{"name": "image.jpg", "text": ocr}],
        {"formContext": {
            "applicantFullname": "KA TUI",
            "applicantIdentityNumber": "068175007976",
        }},
    )

    assert 'result="owner_match"' in context
    assert "Đây là tự nộp" in context
