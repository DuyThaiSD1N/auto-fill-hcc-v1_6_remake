"""Regression phân vai chủ hồ sơ/người có công/người nộp cho Mẫu 11 và 12."""

from app.pipelines.giai_quyet_che_do_khang_chien.process import mapper
from app.pipelines.giai_quyet_che_do_khang_chien.process.runner import (
    _deceased_subject_section,
    _owner_recipient_section,
    _requester_context,
)
from app.pipelines.giai_quyet_che_do_khang_chien.process.schema import ALLOWED


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(compact, {"formContext": form_context or {}})
    mapped = {(field["name"], field.get("occurrence")): field["value"] for field in fields}
    return fields, mapped, warnings


_M12 = {
    # Chủ hồ sơ = cá nhân nhận mai táng phí tại Mục 2.
    "ChuHoSo_HoTen": "TRẦN VĂN B",
    "ChuHoSo_NgaySinh": "31/12/1950",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": "036050000002",
    "ChuHoSo_NgayCap": "16/12/2021",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_QueQuan": {
        "quocGia": "Việt Nam",
        "tinh": "Nam Định",
        "xa": "Thị trấn Liễu Đề",
        "diaChi": "",
    },
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Ninh Bình",
        "xa": "Nghĩa Hưng",
        "diaChi": "Thôn Đông Thọ",
    },
    "ChuHoSo_DienThoai": "0340000002",
    "ChuHoSo_MoiQuanHe": "là con",
    # Người có công đã chết tại Mục 1 là vai trò nghiệp vụ riêng.
    "NguoiCoCong_HoTen": "NGUYỄN VĂN A",
    "NguoiCoCong_NgaySinh": "09/03/1923",
    "NguoiCoCong_GioiTinh": "Nam",
    "NguoiCoCong_SoDinhDanh": "036020000001",
    "NguoiCoCong_NgayCap": "09/07/2021",
    "NguoiCoCong_NoiCap": "Cục CS QLHC về TTXH",
    "NguoiCoCong_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Ninh Bình",
        "xa": "Nghĩa Hưng",
        "diaChi": "Thôn Đông Thọ",
    },
    "NguoiCoCong_QueQuan": {
        "quocGia": "Việt Nam",
        "tinh": "Nam Định",
        "xa": "Liễu Đề",
        "diaChi": "",
    },
    "NguoiCoCong_NgayMat": "09/08/2026",
    "HDKC_CheDo": "Đề nghị giải quyết chế độ ưu đãi khi người có công từ trần",
    "HoSoDinhKem": [{"tenGiayTo": "Bản khai Mẫu số 12", "loaiBan": "Bản chính"}],
}


def test_schema_separates_owner_requester_and_deceased_subject():
    assert "ChuHoSo_HoTen" in ALLOWED
    assert "NguoiNop_HoTen" in ALLOWED
    assert "NguoiCoCong_HoTen" in ALLOWED
    assert "NguoiCoCong_NgayMat" in ALLOWED
    assert "DaiDienThanNhan_HoTen" not in ALLOWED
    assert "Nguoi_HoTen" not in ALLOWED


def test_m12_deceased_is_detail_subject_but_funeral_recipient_is_owner():
    fields, mapped, warnings = _run(
        _M12,
        {"applicantFullname": "VŨ VĂN C", "applicantIdentityNumber": "040200000003"},
    )

    assert fields[0]["name"] == "data[isOwnerDossierCheck]"
    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "TRẦN VĂN B"
    assert mapped[("data[ownerBirthday]", None)] == "31/12/1950"
    assert mapped[("data[ownerIdentityNumber]", None)] == "036050000002"
    assert mapped[("data[ownerPhoneNumber]", None)] == "0340000002"

    assert mapped[("data[fullname]", 1)] == "NGUYỄN VĂN A"
    assert mapped[("data[birthday]", 1)] == "09/03/1923"
    assert mapped[("data[identityNumber]", 1)] == "036020000001"

    assert mapped[("data[fullname1]", None)] == "TRẦN VĂN B"
    assert mapped[("data[identityNumber1]", None)] == "036050000002"
    assert mapped[("data[phoneNumber]", 1)] == "0340000002"
    assert mapped[("data[moiQH]", None)] == "là con"
    assert mapped[("data[ngayMat]", None)] == "09/08/2026"
    assert "không điền phần người nộp" in warnings[0]


def test_shared_remap_fills_old_origin_for_subject_and_owner():
    _, mapped, _ = _run(_M12)

    assert mapped[("data[province]", 1)] == "Tỉnh Ninh Bình"
    assert mapped[("data[district]", 1)] == "Xã Nghĩa Hưng"
    assert mapped[("data[province1]", None)] == "Tỉnh Ninh Bình"
    assert mapped[("data[district1]", None)] == "Xã Nghĩa Hưng"
    assert mapped[("data[province2]", None)] == "Tỉnh Ninh Bình"


def test_funeral_recipient_self_submission_ticks_and_fills_both_top_blocks():
    _, mapped, warnings = _run(
        _M12,
        {"applicantFullname": "TRẦN VĂN B", "applicantIdentityNumber": "036050000002"},
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "TRẦN VĂN B"
    assert mapped[("data[birthday]", 0)] == "31/12/1950"
    assert mapped[("data[ownerFullname]", None)] == "TRẦN VĂN B"
    assert mapped[("data[fullname]", 1)] == "NGUYỄN VĂN A"
    assert not warnings


def test_verified_distinct_requester_preserves_funeral_recipient_owner():
    values = {
        **_M12,
        "NguoiNop_HoTen": "VŨ VĂN C",
        "NguoiNop_NgaySinh": "26/04/2003",
        "NguoiNop_SoDinhDanh": "040200000003",
    }
    _, mapped, warnings = _run(
        values,
        {"applicantFullname": "VŨ VĂN C", "applicantIdentityNumber": "040200000003"},
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert mapped[("data[fullname]", 0)] == "VŨ VĂN C"
    assert mapped[("data[ownerFullname]", None)] == "TRẦN VĂN B"
    assert mapped[("data[fullname]", 1)] == "NGUYỄN VĂN A"
    assert not warnings


def test_name_match_with_identity_mismatch_does_not_verify_requester():
    values = {**_M12, "NguoiNop_HoTen": "VŨ VĂN C", "NguoiNop_SoDinhDanh": "999999999999"}
    _, mapped, warnings = _run(
        values,
        {"applicantFullname": "VŨ VĂN C", "applicantIdentityNumber": "040200000003"},
    )

    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "TRẦN VĂN B"
    assert warnings


def test_missing_ui_anchor_does_not_assume_self_submission():
    _, mapped, warnings = _run(_M12)

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "TRẦN VĂN B"
    assert mapped[("data[fullname]", 1)] == "NGUYỄN VĂN A"
    assert not warnings


def test_m11_living_person_is_owner_and_detail_subject_without_mortuary_block():
    values = {
        "ChuHoSo_HoTen": "LÊ VĂN D",
        "ChuHoSo_NgaySinh": "12/03/1950",
        "ChuHoSo_SoDinhDanh": "042050000004",
        "ChuHoSo_NoiCuTru": {"tinh": "Lâm Đồng", "xa": "Phường Lâm Viên", "diaChi": "136 Mê Linh"},
        "ChuHoSo_QueQuan": {"tinh": "Hà Tĩnh", "xa": "Kỳ Khang", "diaChi": ""},
        "HDKC_CheDo": "Trợ cấp một lần đối với người hoạt động kháng chiến giải phóng dân tộc",
    }
    _, mapped, warnings = _run(values)

    assert mapped[("data[ownerFullname]", None)] == "LÊ VĂN D"
    assert mapped[("data[fullname]", 1)] == "LÊ VĂN D"
    assert ("data[fullname1]", None) not in mapped
    assert ("data[ngayMat]", None) not in mapped
    assert not warnings


async def test_runner_scopes_m12_and_matches_recipient_as_owner():
    ocr = """Mẫu số 12
1. Họ và tên người có công từ trần: Nguyễn Văn A
Ngày tháng năm sinh: 09/03/1923
Số định danh cá nhân: 036020000001
2. Người hoặc tổ chức nhận mai táng phí:
Họ và tên: Trần Văn B
Ngày sinh: 31/12/1950
CCCD: 036050000002
3. Họ và tên người nhận trợ cấp một lần: Trần Văn B
4. Thân nhân người có công
"""

    assert "Nguyễn Văn A" in _deceased_subject_section(ocr)
    assert "Trần Văn B" not in _deceased_subject_section(ocr)
    assert "Trần Văn B" in _owner_recipient_section(ocr)
    assert "Nguyễn Văn A" not in _owner_recipient_section(ocr)

    no_match = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {"applicantFullname": "Vũ Văn C", "applicantIdentityNumber": "040200000003"}},
    )
    assert 'result="no_document_match"' in no_match

    owner_match = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {"applicantFullname": "Trần Văn B", "applicantIdentityNumber": "036050000002"}},
    )
    assert 'result="owner_match"' in owner_match
    assert "<owner_recipient_ocr" in owner_match
    assert "<deceased_subject_ocr" in owner_match

    deceased_is_not_owner = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "036020000001"}},
    )
    assert 'result="no_document_match"' in deceased_is_not_owner
