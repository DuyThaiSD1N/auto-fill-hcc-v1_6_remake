"""Hồ sơ đăng ký lại khai sinh KHÔNG có tờ khai: ô tích (5) theo tài khoản VNeID, không theo agent.

Ca thật (3 CCCD của con/cha/mẹ, không tờ khai): agent vẫn trả Requester_RelationToSubject="Khác"
dù prompt bắt bỏ trống. Field rác đó từng đẩy cả ca sang nhánh "có tờ khai" nên chính chủ tự đi
làm cho mình bị tick "Khác", mục I cũng không được điền từ CCCD của chính họ.
"""
from app.pipelines.khai_sinh_dang_ky_lai.process import reason
from app.pipelines.khai_sinh_dang_ky_lai.process.mapper import enrich

SUBJECT = {
    "Subject_FullName": "NGUYỄN THỊ LUÂN",
    "Subject_BirthDate": "05/05/1979",
    "Subject_Gender": "Nữ",
    "Subject_IdNumber": "027190016206",
    "Subject_BirthDateFromId": "05/05/1979",
    "Subject_IdIssueDate": "29/03/2021",
    "Subject_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Subject_ResidenceDomestic": {
        "quocGia": "Việt Nam",
        "tinh": "Bắc Ninh",
        "xa": "Xuân Lâm",
        "diaChi": "Thôn Thuận Thành",
    },
    "Father_FullName": "NGUYỄN XUÂN MÃI",
    "Father_IdNumber": "027052006628",
    "Mother_FullName": "NGUYỄN THỊ CƯ",
    "Mother_IdNumber": "027149000630",
}


def _context(to_khai: str, ket_luan: str) -> str:
    return "\n".join([
        "<con>",
        f"Họ tên: {SUBJECT['Subject_FullName']}",
        f"Số CCCD/CMND: {SUBJECT['Subject_IdNumber']}",
        "</con>",
        "<quan_he_nguoi_yeu_cau>",
        f"Kết luận: {ket_luan}",
        "Căn cứ: test",
        "</quan_he_nguoi_yeu_cau>",
        "<to_khai_dang_ky_lai>",
        f"Có tờ khai đăng ký lại khai sinh: {to_khai}",
        "Nguồn: test",
        "</to_khai_dang_ky_lai>",
    ])


def _enrich(values, context="", applicant=("NGUYỄN THỊ LUÂN", "027190016206")):
    fields = [
        {"name": name, "comp": "x-input", "value": value}
        for name, value in values.items()
    ]
    options = {
        "_reasoning_context": context,
        "formContext": {
            "applicantFullname": applicant[0],
            "applicantIdentityNumber": applicant[1],
        },
    }
    return {field["name"]: field["value"] for field in enrich(fields, options)}


def test_khong_to_khai_thi_bo_qua_quan_he_agent_tu_suy():
    values = _enrich(
        {**SUBJECT, "Requester_RelationToSubject": "Khác"},
        _context("Không", "bản thân"),
    )

    assert values["QuanHe"] == "BanThan"
    # Mục I phải điền từ CCCD của chính người đó, không dừng lại ở dữ liệu cổng đổ sẵn.
    assert values["HoVaTenC"] == "NGUYỄN THỊ LUÂN"
    assert values["SoDinhDanhC"] == "027190016206"


def test_khong_to_khai_va_nguoi_nop_ho_thi_van_tick_khac():
    """Người đăng nhập không phải người được đăng ký lại → không suy được quan hệ."""
    values = _enrich(
        {**SUBJECT, "Requester_RelationToSubject": "Khác"},
        _context("Không", "khác"),
        applicant=("NGUYỄN VĂN AN", "027190099999"),
    )

    assert values["QuanHe"] == "Khac"
    assert "HoVaTenC" not in values


def test_co_to_khai_thi_van_lay_quan_he_ghi_tren_to_khai():
    values = _enrich(
        {
            **SUBJECT,
            "Requester_RelationToSubject": "Khác",
            "Requester_FullName": "NGUYỄN VĂN AN",
            "Requester_Relationship": "Cháu nội",
        },
        _context("Có", "khác"),
    )

    assert values["QuanHe"] == "Khac"
    assert values["HoVaTenC"] == "NGUYỄN VĂN AN"


def test_sanitize_xoa_requester_khi_ho_so_khong_co_to_khai():
    fields = [
        {"name": "Requester_RelationToSubject", "comp": "x-input", "value": "Khác"},
        {"name": "Subject_FullName", "comp": "x-input", "value": "NGUYỄN THỊ LUÂN"},
    ]

    kept = {
        field["name"]
        for field in reason.sanitize_extracted_fields(fields, _context("Không", "bản thân"))
    }

    assert "Requester_RelationToSubject" not in kept
    assert "Subject_FullName" in kept


def test_sanitize_giu_requester_khi_ho_so_co_to_khai():
    fields = [
        {"name": "Requester_RelationToSubject", "comp": "x-input", "value": "Khác"},
        {"name": "Subject_FullName", "comp": "x-input", "value": "NGUYỄN THỊ LUÂN"},
    ]

    kept = {
        field["name"]
        for field in reason.sanitize_extracted_fields(fields, _context("Có", "khác"))
    }

    assert "Requester_RelationToSubject" in kept
