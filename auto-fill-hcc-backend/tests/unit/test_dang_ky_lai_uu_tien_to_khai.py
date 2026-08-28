"""Đăng ký lại khai sinh: TỜ KHAI là nguồn số 1, CCCD/trích lục chỉ bù field còn trống.

Ca thật đã hỏng: hồ sơ chỉ có tờ khai + trích lục khai tử của cha. Agent phân vai trả rỗng nên
<con>/<me>/<cha> đều "Không xác định", sanitize xoá sạch Subject_*/Mother_*/Father_* và cổng chỉ
điền được mỗi khối người yêu cầu.
"""

import re

from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason


_TO_KHAI = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Kính gửi: Ủy Ban Nhân Dân phường Xuân Trường - Đà Lạt
Họ, chữ đệm, tên người yêu cầu: Nguyễn Tấn Khang
Ngày, tháng, năm sinh: 02-09-1974
Nơi cư trú: (2) TDP phát chi, phường Xuân Trường - Đà Lạt - Lâm Đồng
Giấy tờ tùy thân: (3) CCCD số 052071012960 cấp ngày 26-05-2022 Tại Cục Cảnh sát - QLHC về TTXH
Quan hệ với người được khai sinh: Tự khai
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: Nguyễn Tấn Khang
Ngày, tháng, năm sinh: 02-09-1974 ghi bằng chữ: ngày hai tháng chín năm một chín bảy tư
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi sinh: (4) Thôn Long Mỹ xã Ân Rảo - Tỉnh Gia Lai
Quê quán: T.P Đà Nẵng
Họ, chữ đệm, tên người mẹ: Trương Thị Nhỏ
Năm sinh: (5) 01-01-1944 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Nơi cư trú: (2) TDP phát chi, phường Xuân Trường - Đà Lạt - Lâm Đồng
Giấy tờ tùy thân: (3) CCCD số 049144001890 cấp ngày 5/4/2022 Tại Cục cảnh sát
Họ, chữ đệm, tên người cha: Nguyễn Văn Câu
Năm sinh: (5) 15-07-1945 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Nơi cư trú: (2) Đã chết
Giấy tờ tùy thân: (3)
Đã đăng ký khai sinh tại: (6) xã Ân Rảo - Tỉnh Gia Lai
Tôi cam đoan những nội dung khai trên đây là đúng sự thật.
"""

_TRICH_LUC_KHAI_TU = """TRÍCH LỤC KHAI TỬ
Số: 17/TLKT
Họ, chữ đệm, tên: NGUYỄN VĂN CẦU
Ngày, tháng, năm sinh: 15/07/1945
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Số định danh cá nhân: 022045000555
Đã chết vào lúc 09 giờ 30 phút, ngày 05 tháng 12 năm 2023
Họ, chữ đệm, tên người đi khai tử: Nguyễn Tấn Khang
"""

_DOCUMENTS = [
    {"name": "khai-tu.jpg", "text": _TRICH_LUC_KHAI_TU},
    {"name": "to-khai.pdf", "text": _TO_KHAI},
]


def _label(context: str, tag: str, label: str) -> str:
    section = re.search(rf"<{tag}>(.*?)</{tag}>", context, re.S)
    if not section:
        return ""
    found = re.search(rf"^{label}:\s*(.*)$", section.group(1), re.M)
    return found.group(1).strip() if found else ""


def test_to_khai_chot_vai_khi_agent_phan_vai_tra_rong():
    context = reason._render_context("", {}, _DOCUMENTS)

    assert _label(context, "con", "Họ tên") == "Nguyễn Tấn Khang"
    assert _label(context, "me", "Họ tên") == "Trương Thị Nhỏ"
    assert _label(context, "cha", "Họ tên") == "Nguyễn Văn Câu"
    # "Nơi cư trú: Đã chết" trên tờ khai là cách biểu mẫu ghi cha/mẹ đã mất.
    assert _label(context, "cha", "Trạng thái") == "đã chết"
    # Dòng "Quan hệ với người được khai sinh: Tự khai" thắng mọi suy luận khác.
    assert _label(context, "quan_he_nguoi_yeu_cau", "Kết luận") == "bản thân"
    assert _label(context, "nguoi_yeu_cau", "Họ tên") == "Nguyễn Tấn Khang"


def test_cccd_chi_bu_field_to_khai_bo_trong():
    context = reason._render_context("", {}, _DOCUMENTS)

    # Tờ khai bỏ trống giấy tờ tùy thân của cha → lấy bù từ trích lục khai tử của CHÍNH ông ấy.
    assert _label(context, "cha", "Số CCCD/CMND") == "022045000555"
    # Mẹ có số trên tờ khai thì giữ nguyên số của tờ khai.
    assert _label(context, "me", "Số CCCD/CMND") == "049144001890"


def test_to_khai_thang_khi_agent_gan_nham_nguoi_vao_vai_cha():
    raw = """<cha>
Họ tên: NGUYỄN TẤN KHANG
Số CCCD/CMND: 052071012960
Ngày sinh: 02/09/1974
Giới tính: Nam
Trạng thái: còn sống
Nguồn: to-khai.pdf
Căn cứ phân vai: Suy từ CCCD.
</cha>"""

    context = reason._render_context(raw, {}, _DOCUMENTS)

    assert _label(context, "cha", "Họ tên") == "Nguyễn Văn Câu"


def test_khoi_con_cha_me_khong_con_bi_xoa_sach_sau_sanitize():
    context = reason._render_context("", {}, _DOCUMENTS)
    fields = [
        {"name": "Subject_FullName", "value": "Nguyễn Tấn Khang"},
        {"name": "Subject_BirthDate", "value": "02/09/1974"},
        {"name": "Subject_Gender", "value": "Nam"},
        {"name": "Mother_FullName", "value": "Trương Thị Nhỏ"},
        {"name": "Mother_IdNumber", "value": "049144001890"},
        {"name": "Mother_Gender", "value": "Nữ"},
        {"name": "Mother_BirthDateOrYear", "value": "01/01/1944"},
        {"name": "Father_FullName", "value": "NGUYỄN VĂN CẦU"},
        {"name": "Father_IdNumber", "value": "022045000555"},
        {"name": "Father_Gender", "value": "Nam"},
        {"name": "Father_BirthDateOrYear", "value": "15/07/1945"},
        {"name": "Father_ResidenceDomestic", "value": {"quocGia": "", "tinh": "", "xa": "", "diaChi": "Đã chết"}},
    ]

    kept = {field["name"] for field in reason.sanitize_extracted_fields(fields, context)}
    assert "Subject_FullName" in kept
    assert "Mother_FullName" in kept
    assert "Father_FullName" in kept

    ui = {field["name"]: field["value"] for field in mapper.enrich(
        reason.sanitize_extracted_fields(fields, context), {"_reasoning_context": context}
    )}
    assert ui["HoTenKS"] == "Nguyễn Tấn Khang"
    assert ui["HoTenMeKS"] == "Trương Thị Nhỏ"
    assert ui["HoTenChaKS"] == "NGUYỄN VĂN CẦU"
    # Cha đã mất → tick "Khác" rồi ghi chữ vào ô nhập tự do.
    assert ui["ChaNoiCuTru"] == "Khác"
    assert ui["ChaNoiCuTru_NuocNgoai"] == "Đã chết"


def test_khong_co_to_khai_thi_khong_dung_bo_doc_to_khai():
    only_death = [{"name": "khai-tu.jpg", "text": _TRICH_LUC_KHAI_TU}]

    context = reason._render_context("", {}, only_death)

    # Người trên trích lục khai tử không được tự động thành con/cha/mẹ.
    assert _label(context, "con", "Họ tên") in ("", "Không xác định")
    assert _label(context, "cha", "Họ tên") in ("", "Không xác định")


def test_ocr_rung_chu_nguoi_yeu_cau_thi_khong_nham_thanh_con():
    # OCR hay đọc thiếu "người yêu cầu" ở nhãn đầu tờ khai; khi đó nhãn trần "Họ, chữ đệm, tên:"
    # đứng TRƯỚC dòng "Đề nghị ... cho người có tên dưới đây" vẫn là người yêu cầu, không phải con.
    text = _TO_KHAI.replace("Họ, chữ đệm, tên người yêu cầu:", "Họ, chữ đệm, tên:")
    text = text.replace(
        "Họ, chữ đệm, tên: Nguyễn Tấn Khang\nNgày, tháng, năm sinh: 02-09-1974 ghi bằng chữ",
        "Họ, chữ đệm, tên: Nguyễn Tấn Khương\nNgày, tháng, năm sinh: 02-09-1974 ghi bằng chữ",
    )

    context = reason._render_context("", {}, [{"name": "to-khai.pdf", "text": text}])

    assert _label(context, "con", "Họ tên") == "Nguyễn Tấn Khương"
