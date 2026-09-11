"""Hồ sơ thật: cụ Nguyễn Thị Thu Hà tự đăng ký lại khai sinh, em gái đăng nhập cổng nộp hộ.

Hai lỗi phải chặn:
1. Mục I giữ nguyên số/ngày/nơi cấp CCCD của tài khoản VNeID đang đăng nhập (người em) trong khi
   họ tên đã bị ghi đè thành người yêu cầu trên tờ khai → khối người yêu cầu là nửa người này
   nửa người kia.
2. Tờ khai viết tay để OCR đọc mục người được đăng ký lại thành "Nguyễn Thị Ha Hà" trong khi
   chính tờ khai đó (và 4 giấy tờ khác) ghi "Nguyễn Thị Thu Hà".
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason
from app.pipelines.khai_sinh_dang_ky_lai.process.schema import COMPACT_COMP_BY_NAME

_TO_KHAI = "\n".join([
    "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
    "Kính gửi: (1) UBND phường Xuân Trường – Đà Lạt",
    "Họ, chữ đệm, tên người yêu cầu: Nguyễn Thị Thu Hà",
    "Ngày, tháng, năm sinh: 11-12-1957",
    "Nơi cư trú: (2) tổ DP Trại Mát, Phường Xuân Trường – Đà Lạt, tỉnh Lâm Đồng",
    "Giấy tờ tùy thân: (3) CCCD số không có do Cục Cảnh sát QLHC về TTXH cấp ngày",
    "Quan hệ với người được khai sinh: tự Khai",
    "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:",
    "Họ, chữ đệm, tên: Nguyễn Thị Ha Hà",
    "Ngày, tháng, năm sinh: 11-12-1957",
    "Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam",
    "Nơi sinh: (4) Phường 11 Đà Lạt, Lâm Đồng",
    "Họ, chữ đệm, tên người mẹ: Nguyễn Thị Nguyệt",
    "Năm sinh: (5) 9-9-1941 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam",
    "Nơi cư trú: (2) tổ DP Trại Mát, Phường Xuân Trường – Đà Lạt, tỉnh Lâm Đồng",
    "Giấy tờ tùy thân: (3) CCCD Số 040141003442",
    "Họ, chữ đệm, tên người cha: Không có",
    "Đã đăng ký khai sinh tại: (6) Phường 11, Đà Lạt, tỉnh Lâm Đồng",
])

_CCCD_ME = "\n".join([
    "CĂN CƯỚC CÔNG DÂN",
    "Citizen Identity Card",
    "Số / No.: 040141003442",
    "Họ và tên / Full name: NGUYỄN THỊ NGUYỆT",
    "Ngày sinh / Date of birth: 09/09/1941",
    "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam",
    "Nơi thường trú / Place of residence 238 Tự Phước, Phường 11, Thành phố Đà Lạt, Lâm Đồng",
])

_CCCD_EM_GAI = "\n".join([
    "CĂN CƯỚC CÔNG DÂN",
    "Citizen Identity Card",
    "Số / No.: 068172005084",
    "Họ và tên / Full name: NGUYỄN THỊ MINH THƯ",
    "Ngày sinh / Date of birth: 05/02/1972",
    "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam",
    "Nơi thường trú / Place of residence: 238B/13 Tự Phước, Phường 11, TP Đà Lạt, Lâm Đồng",
])

_TUONG_TRINH = "\n".join([
    "BẢN TƯỜNG TRÌNH CÁ NHÂN",
    "Kính gửi: UBND Phường Xuân Trường – Đà Lạt",
    "Tôi tên: Nguyễn Thị Thu Hà Sinh ngày: 11/12/1957",
    "Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam",
])

_GIAY_UY_QUYEN = "\n".join([
    "GIẤY ỦY QUYỀN",
    "1. Tôi tên: Nguyễn Thị Thu Hà; sinh năm: 1957",
    "CCCD số: Không có",
    "Bằng giấy này chúng tôi ủy quyền cho em gái ruột của tôi là:",
    "Họ và tên: Nguyễn Thị Minh Thư; sinh năm: 1972",
    "CCCD số: 068172005084",
])

_DOCUMENTS = [
    {"name": "TK thu hà.pdf", "text": _TO_KHAI, "role": ""},
    {"name": "cccd nguyệt.pdf", "text": _CCCD_ME, "role": ""},
    {"name": "cccd thư.pdf", "text": _CCCD_EM_GAI, "role": ""},
    {"name": "Tt thu hà.pdf", "text": _TUONG_TRINH, "role": ""},
    {"name": "guq thu hà.pdf", "text": _GIAY_UY_QUYEN, "role": ""},
]

# Cổng đang đăng nhập bằng tài khoản người em được ủy quyền đi nộp hộ.
_OPTIONS = {
    "formContext": {
        "applicantFullname": "Nguyễn Thị Minh Thư",
        "applicantIdentityNumber": "068172005084",
    }
}


def _context() -> str:
    return reason._render_context("", _OPTIONS, _DOCUMENTS)


def _enrich(values: dict, context: str, options: dict | None = None) -> dict:
    fields = [
        {"name": name, "comp": COMPACT_COMP_BY_NAME.get(name, "x-input"), "value": value}
        for name, value in values.items()
    ]
    enriched = mapper.enrich(fields, {**(options or _OPTIONS), "_reasoning_context": context})
    return {field["name"]: field for field in enriched}


_EXTRACTED = {
    "Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
    "Requester_RelationToSubject": "Bản thân",
    "Requester_FullName": "Nguyễn Thị Thu Hà",
    "Requester_ResidenceDomestic": {
        "quocGia": "Việt Nam", "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Trường", "diaChi": "TDP Trại Mát",
    },
    "Subject_FullName": "Nguyễn Thị Ha Hà",
    "Subject_BirthDate": "11/12/1957",
    "Subject_Gender": "Nữ",
    "Mother_FullName": "Nguyễn Thị Nguyệt",
    "Mother_IdNumber": "040141003442",
}


def test_ten_nguoi_dang_ky_lai_lay_theo_ten_duoc_nhieu_giay_to_xac_nhan():
    context = _context()

    assert "Kết luận: bản thân" in context
    assert "Họ tên thống nhất: Nguyễn Thị Thu Hà" in context

    fields = _enrich(_EXTRACTED, context)
    assert fields["HoTenKS"]["value"] == "NGUYỄN THỊ THU HÀ"
    assert fields["HoVaTenC"]["value"] == "NGUYỄN THỊ THU HÀ"


def test_ten_chi_lech_mot_tieng_moi_duoc_gop():
    """Lệch nhiều hơn một tiếng là HAI cái tên khác nhau — không được tự ý gộp."""
    assert reason._self_name_consensus("Nguyễn Thị Thu Hà", "Trần Văn Bình", _DOCUMENTS) == ""
    assert reason._self_name_consensus("Nguyễn Thị Thu Hà", "Nguyễn Thị Thu Hà", _DOCUMENTS) == ""


def test_agent_tra_ten_da_thong_nhat_thi_khong_bi_xoa_khoi_con():
    """Tên trong <con> vẫn là dòng OCR hỏng; agent trả tên thật KHÔNG phải là người lạ."""
    context = _context()
    fields = [{"name": "Subject_FullName", "comp": "x-input", "value": "Nguyễn Thị Thu Hà"}]

    kept = {field["name"] for field in reason.sanitize_extracted_fields(fields, context)}
    assert "Subject_FullName" in kept


def test_xoa_giay_to_tuy_than_con_sot_cua_tai_khoan_vneid():
    fields = _enrich(_EXTRACTED, _context())

    for name in ("SoDinhDanhC", "SoGiayToDinhDanhC", "LoaiGiayToDinhDanhC", "NgayCapDDC", "NoiCapDDC"):
        assert fields[name]["value"] == "", name
        assert fields[name]["clear"] is True, name
    # Họ tên đọc được thì điền, không xóa.
    assert "clear" not in fields["HoVaTenC"]


def test_chinh_chu_dang_nhap_thi_giu_nguyen_du_lieu_cong_dien_san():
    """Người yêu cầu chính là tài khoản đang đăng nhập → ô trống là dữ liệu ĐÚNG của họ."""
    options = {
        "formContext": {
            "applicantFullname": "Nguyễn Thị Thu Hà",
            "applicantIdentityNumber": "",
        }
    }
    fields = _enrich(_EXTRACTED, _context(), options)

    for name in ("SoDinhDanhC", "NgayCapDDC", "NoiCapDDC"):
        assert name not in fields, name


def test_muc_cha_ghi_khong_co_thi_bo_han_vai_cha():
    """"Không có" là lời khai KHÔNG CÓ NGƯỜI, không phải một họ tên."""
    context = _context()

    assert "Họ tên: Không có" not in context
    kept = {
        field["name"]
        for field in reason.sanitize_extracted_fields(
            [{"name": "Father_FullName", "comp": "x-input", "value": "Không có"}], context
        )
    }
    # Vai mẹ có CCCD trong hồ sơ nên được dựng lại; vai cha thì phải mất sạch.
    assert not any(name.startswith("Father_") for name in kept)


def test_khong_doc_duoc_nhan_than_nguoi_yeu_cau_thi_khong_xoa_gi():
    """Chưa ghi đè ô nào thì khối cổng điền vẫn là MỘT người trọn vẹn — xóa là mất dữ liệu đúng."""
    fields = _enrich(
        {
            "Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
            "Requester_Relationship": "Cháu nội",
        },
        "",
    )

    assert not [name for name, field in fields.items() if field.get("clear")]
