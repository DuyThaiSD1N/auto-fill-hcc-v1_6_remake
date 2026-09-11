"""Hồ sơ scan GỘP nhiều giấy tờ vào MỘT file — vai cha phải đọc được từ đúng trang CCCD của cha.

Ca thật req_ce69adef5dd5: cả tập 22 trang nằm trong một PDF. Bản cam đoan ở trang 1 cũng có dòng
"Họ tên Cha:", đứng trước tờ khai ở trang 3, nên khối cha bị chốt theo bản cam đoan rồi hút luôn
số CCCD của CON ghi ở mục "Các giấy tờ cá nhân của tôi". Vai cha vì thế bị coi là trùng con và bị
xoá trắng, biểu mẫu không điền được gì cho cha.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason

_HO_SO = """───── Trang 1/6 ─────
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
BẢN CAM ĐOAN
Tên tôi là: Họ và tên: Tống Ngọc Quang
Họ và tên: Tống Ngọc Quang ............... Ngày, tháng, năm sinh..22/02/1983
Họ tên Cha: Tống Ngọc Phương ..................... Ngày, tháng, năm sinh..1949
Họ tên Mẹ................ngô Thị Dũng ....................... Ngày, tháng, năm sinh..1955.
Các giấy tờ cá nhân của tôi:
1............CCCD : 024083017609

───── Trang 2/6 ─────
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Họ, chữ đệm, tên người yêu cầu: Tống Ngọc Quang
Ngày, tháng, năm sinh: 22/02/1983
Giấy tờ tùy thân: (3) CCCD: 024083017609
Quan hệ với người được khai sinh: Bản Thân
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: Tống Ngọc Quang
Ngày, tháng, năm sinh: 22/02/1983
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Họ, chữ đệm, tên người mẹ: Ngô Thị Dung
Năm sinh: (5) 1955 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Giấy tờ tùy thân: (3) CCCD: 027155007164
Họ, chữ đệm, tên người cha: Tống Ngọc Phong
Năm sinh: (5) 1949 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Giấy tờ tùy thân: (3) CCCD: 024049204086
Đã đăng ký khai sinh tại: (6) UBND Phường Trần Phú

───── Trang 3/6 ─────
CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 024083017609
Họ và tên / Full name: TỐNG NGỌC QUANG
Ngày sinh / Date of birth: 22/02/1983
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Ngày, tháng, năm / Date, month, year: 12/05/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI

───── Trang 4/6 ─────
CĂN CƯỚC CÔNG DÂN
Số / No.: 027155007164
Họ và tên / Full name: NGÔ THỊ DUNG
Ngày sinh / Date of birth: 11/07/1955
Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam
Ngày, tháng, năm / Date, month, year: 10/05/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI

───── Trang 5/6 ─────
CĂN CƯỚC CÔNG DÂN
Số / No.: 024049004086
Họ và tên / Full name: TÓNG NGỌC PHÓNG
Ngày sinh / Date of birth: 15/06/1949
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Ngày, tháng, năm / Date, month, year: 10/05/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI

───── Trang 6/6 ─────
Trang trắng
"""


def _documents() -> list[dict]:
    return [{"name": "ho-so.pdf", "text": _HO_SO}]


def _context() -> str:
    return reason._render_context("", None, _documents())


def test_vai_cha_lay_theo_to_khai_chu_khong_theo_ban_cam_doan():
    roles = reason._declaration_roles(_documents())

    assert roles["cha"]["name"] == "Tống Ngọc Phong"
    # Số ở mục "Các giấy tờ cá nhân của tôi" là của CON, không được chảy sang vai cha.
    assert roles["cha"]["id"] != "024083017609"


def test_moi_trang_giay_to_duoc_doc_thanh_mot_nhan_than_rieng():
    cards = [
        person
        for unit in reason._identity_units(_documents())
        if (person := reason._person_from_document(unit)) and person.get("is_identity")
    ]

    assert [card["id"] for card in cards] == [
        "024083017609",
        "027155007164",
        "024049004086",
    ]


def test_khoi_cha_giu_duoc_nhan_than_va_lay_giay_to_theo_cccd():
    cha = reason._section(_context(), "cha")

    assert reason._role_name(cha) == "Tống Ngọc Phong"
    # Tờ khai viết tay ghi 024049204086; số đúng là số in trên thẻ.
    assert reason._labeled_value(cha, "Số CCCD/CMND") == "024049004086"
    assert reason._labeled_value(cha, "Ngày cấp") == "10/05/2021"
    assert reason._labeled_value(cha, "Nơi cấp") == (
        "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    )
    assert reason._labeled_value(cha, "Giới tính") == "Nam"


def test_agent_bo_sot_vai_cha_thi_python_dung_lai_tu_cccd():
    context = _context()
    fields = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "Tống Ngọc Quang"},
        {"name": "Subject_BirthDate", "comp": "x-date", "value": "22/02/1983"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "Ngô Thị Dung"},
        {"name": "Mother_IdNumber", "comp": "x-input", "value": "027155007164"},
        {"name": "Mother_Gender", "comp": "x-input", "value": "Nữ"},
    ]

    ui = {
        field["name"]: field["value"]
        for field in mapper.enrich(
            reason.sanitize_extracted_fields(fields, context),
            {"_reasoning_context": context},
        )
    }

    assert ui["HoTenChaKS"] == "TỐNG NGỌC PHONG"
    assert ui["SoDinhDanhCha"] == "024049004086"
    assert ui["NgayCapDDCha"] == "10/05/2021"
    assert ui["NoiCapDDCha"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert ui["NamSinhChaKS"] == "1949"
