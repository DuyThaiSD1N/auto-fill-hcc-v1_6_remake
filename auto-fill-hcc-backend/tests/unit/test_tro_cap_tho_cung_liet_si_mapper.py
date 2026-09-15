"""Regression hai vai trò cho trợ cấp thờ cúng liệt sĩ."""

from app.pipelines.tro_cap_tho_cung_liet_si.process import mapper
from app.pipelines.tro_cap_tho_cung_liet_si.process.runner import (
    _authorization_sections,
    _proposal_section,
    _requester_context,
)
from app.pipelines.tro_cap_tho_cung_liet_si.process.schema import ALLOWED


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(compact, {"formContext": form_context or {}})
    mapped = {
        (field["name"], field.get("occurrence")): field["value"]
        for field in fields
    }
    return fields, mapped, warnings


_OWNER = {
    "ChuHoSo_HoTen": "Vũ Đình Tuyến",
    "ChuHoSo_NgaySinh": "08/03/1962",
    "ChuHoSo_SoDinhDanh": "034062017797",
    "ChuHoSo_NgayCap": "09/05/2021",
    "ChuHoSo_NoiCap": "Cục CSQLHC về TTXH",
    "ChuHoSo_QueQuan": {
        "quocGia": "Việt Nam",
        "tinh": "Hưng Yên",
        "xa": "Long Hưng",
        "diaChi": "",
    },
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Lâm Viên",
        "diaChi": "2 Trương Văn Hoàn",
    },
    "ChuHoSo_DienThoai": "0982577867",
    "ToKhai_MoiQuanHeVoiLietSi": "Con trai",
    "ToKhai_LietSiThoCung": "Vũ Đình Soang",
    "ToKhai_ThanNhan": [
        {
            "hoTen": "Vũ Thị Duyên",
            "namSinh": "1965",
            "noiThuongTru": "8/5 Xô Viết Nghệ Tĩnh, Phường Lâm Viên",
            "moiQuanHe": "Con",
        }
    ],
}


def _run_owner_mode(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    opts = {"submitterMode": "owner_as_submitter"}
    if form_context is not None:
        opts["formContext"] = form_context
    fields, warnings = mapper.enrich(compact, opts)
    return {(f["name"], f.get("occurrence")): f["value"] for f in fields}, warnings


def test_owner_mode_submitter_is_owner_and_ticks():
    """Toggle owner_as_submitter, không mỏ neo UI → occ0 (người nộp) = chủ hồ sơ + tick; phần còn lại giữ nguyên."""
    mapped, _ = _run_owner_mode(_OWNER)
    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"          # người nộp = chủ hồ sơ
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"          # Mẫu 18 chi tiết (luôn owner)
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"  # khối chủ hồ sơ (luôn owner)
    assert mapped[("data[MqhVls1]", None)] == "Con trai"             # nghiệp vụ liệt sĩ vẫn điền
    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang"


def test_owner_mode_ignores_ui_anchor_no_warning():
    """Owner mode bỏ mỏ neo UI: dù form có người KHÁC vẫn owner=submitter, KHÔNG cảnh báo lệch người nộp."""
    mapped, warnings = _run_owner_mode(
        _OWNER, {"applicantFullname": "Người Khác", "applicantIdentityNumber": "999999999999"}
    )
    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"
    assert not any("người nộp" in w for w in warnings)


def test_schema_has_two_identity_roles_and_keeps_business_fields():
    assert "ChuHoSo_HoTen" in ALLOWED
    assert "NguoiNop_HoTen" in ALLOWED
    assert "ToKhai_MoiQuanHeVoiLietSi" in ALLOWED
    assert "ToKhai_ThanNhan" in ALLOWED
    assert not any(name.startswith("Person") for name in ALLOWED)
    assert "ToKhai_HoTen" not in ALLOWED


def test_mismatching_ui_fills_owner_and_detail_but_not_requester():
    fields, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert fields[0]["name"] == "data[isOwnerDossierCheck]"
    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[ownerBirthday]", None)] == "08/03/1962"
    assert mapped[("data[ownerIdentityNumber]", None)] == "034062017797"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert mapped[("data[ownerProvince]", None)] == "Tỉnh Lâm Đồng"
    assert mapped[("data[ownerDistrict]", None)] == "Phường Lâm Viên"
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"
    assert mapped[("data[birthday]", 1)] == "08/03/1962"
    assert mapped[("data[MqhVls1]", None)] == "Con trai"
    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang"
    assert ("data[ownerGender]", None) not in mapped
    assert ("data[gender]", 1) not in mapped
    assert "không điền phần người nộp" in warnings[0]


def test_owner_matching_ui_ticks_and_explicitly_fills_both_blocks():
    _, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "034062017797",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"
    assert mapped[("data[birthday]", 0)] == "08/03/1962"
    assert mapped[("data[identityDate]", 0)] == "09/05/2021"
    assert mapped[("data[ownerBirthday]", None)] == "08/03/1962"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert not warnings


def test_distinct_verified_requester_fills_both_roles():
    values = {
        **_OWNER,
        "NguoiNop_HoTen": "Vũ Đình Thiết",
        "NguoiNop_NgaySinh": "26/04/2003",
        "NguoiNop_SoDinhDanh": "040203015844",
    }
    _, mapped, warnings = _run(
        values,
        {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Thiết"
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"
    assert not warnings


def test_name_match_but_identity_mismatch_is_not_accepted():
    _, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "999999999999",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert warnings


def test_missing_ui_anchor_still_fills_owner_and_business_details():
    _, mapped, warnings = _run(_OWNER)

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[DataGrid][0][Ht]", None)] == "Vũ Thị Duyên"
    assert not warnings


def test_martyr_name_list_is_joined_and_duplicate_relatives_are_merged():
    values = {
        **_OWNER,
        "ToKhai_LietSiThoCung": ["Vũ Đình Soang", "Vũ Đình Hải"],
        "ToKhai_ThanNhan": [
            {
                "hoTen": "Vũ Đình Tuyên",
                "namSinh": "1962",
                "noiThuongTru": "Số 2 Trường Sơn Vân Hoàn",
                "moiQuanHe": "em trai",
            },
            {
                "hoTen": "VŨ ĐÌNH TUYÊN",
                "namSinh": "",
                "noiThuongTru": "phường Lâm Viên Đà Lạt",
                "moiQuanHe": "em trai",
            },
            {
                "hoTen": "Vũ Thị Duyên",
                "namSinh": "1965",
                "noiThuongTru": "8/5 Hồ Xuân Hương P. Lâm Viên Đà Lạt",
                "moiQuanHe": "em trai",
            },
            {"hoTen": "Vũ Thị Duyên", "namSinh": "1965"},
        ],
    }

    _, mapped, warnings = _run(values)

    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang và Vũ Đình Hải"
    assert mapped[("data[DataGrid][0][Ht]", None)] == "Vũ Đình Tuyên"
    assert mapped[("data[DataGrid][0][Ns]", None)] == "1962"
    assert mapped[("data[DataGrid][1][Ht]", None)] == "Vũ Thị Duyên"
    assert mapped[("data[DataGrid][1][Ns]", None)] == "1965"
    assert ("data[DataGrid][2][Ht]", None) not in mapped
    assert not warnings


async def test_runner_scopes_owner_and_rejects_unrelated_people_as_requester():
    ocr = """Mẫu số 18
1. Thông tin người đề nghị
Họ và tên: Vũ Đình Tuyên
Ngày tháng năm sinh: 1962
CCCD/CMND số 034062011797
Mối quan hệ với liệt sĩ: Con trai
2. Thông tin về thân nhân liệt sĩ
1 | Vũ Thị Duyên | 1965

BÊN ỦY QUYỀN:
Họ và tên: Vũ Thị Duyên
CC số: 034165017965
BÊN ĐƯỢC ỦY QUYỀN:
Họ và tên: Vũ Đình Tuyến Sinh năm: 08/03/1962
CCCD số: 034062017797 cấp ngày 09/05/2021
Địa chỉ: 2 Trương Văn Hoàn, Phường Lâm Viên, Lâm Đồng
NỘI DUNG ỦY QUYỀN:
Thờ cúng liệt sĩ Vũ Đình Soang
"""

    proposal = _proposal_section(ocr)
    assert "Vũ Đình Tuyên" in proposal
    assert "Vũ Thị Duyên" not in proposal
    authorization = _authorization_sections(ocr)[0]
    assert "Vũ Đình Tuyến" in authorization
    assert "Vũ Thị Duyên" not in authorization

    owner_context = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "034062017797",
        }},
    )
    assert 'result="owner_match"' in owner_context

    mismatch_context = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )
    assert 'result="no_document_match"' in mismatch_context
