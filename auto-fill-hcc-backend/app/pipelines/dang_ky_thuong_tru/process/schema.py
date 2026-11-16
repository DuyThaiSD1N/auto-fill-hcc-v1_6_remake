"""Compact schema cho "Đăng ký thường trú" (Cổng DVC Bộ Công an, dichvucong.dancuquocgia.gov.vn).

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, CCCD, giấy khai sinh / kết hôn chứng minh quan hệ, giấy tờ chỗ ở).
Ô của form (id = name trên trang: txtFULLNAME, cboFORMAT_DATE, txtBIRTH_DATE…) dựng trong mapper.py — bộ id KHÁC
trang Đăng ký tạm trú dù cùng cổng.

Không điền: "Thủ tục" (cổng tự chọn theo TT= trên URL rồi khoá), khối "Nơi đề nghị" Tỉnh/Xã (cổng chép từ Cơ quan
thực hiện), "Danh sách người cần xin ý kiến" (gõ vào đó cổng đổi nút "Nộp hồ sơ" thành gửi xác nhận qua VNeID),
khối CT02 (người định cư ở nước ngoài), nhận thông báo / kết quả (để mặc định của cổng).
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú ở dòng "Kính gửi (1)" Tờ khai CT01 (hoặc "Cơ quan tiếp '
                'nhận" trên bìa hồ sơ). Chỉ tên đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú ở dòng "Kính gửi (1)" Tờ khai CT01 (hoặc bìa hồ sơ). Giữ '
                'tiền tố Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    {
        "name": "TruongHop",
        "desc": 'Trường hợp đăng ký, chọn đúng một nhãn: "Đăng ký thường trú cả hộ" (cả hộ gia đình cùng chuyển đến '
                'đăng ký), "Đăng ký thường trú nhân khẩu" (một hoặc vài người đăng ký vào hộ / chỗ ở mới, không phải cả '
                'hộ), "Đăng ký thường trú lần đầu với trẻ em mới sinh, công dân chưa từng đăng ký thường trú". Căn cứ nội '
                'dung đề nghị mục 10 và bảng thành viên mục 11 CT01. Không có căn cứ → bỏ trống.',
    },
    {
        "name": "HinhThuc",
        "desc": 'Hình thức đăng ký: "vào hộ đã có" khi người đề nghị đăng ký vào hộ của một chủ hộ KHÁC (tờ khai ghi chủ '
                'hộ là người khác, nội dung "đăng ký thường trú vào hộ …"); "lập hộ mới" khi người đề nghị tự làm chủ hộ '
                '(mục 8 ghi "Chủ hộ" / nội dung "lập hộ mới"). Không có căn cứ → bỏ trống.',
    },
    # Người đề nghị đăng ký thường trú (người thay đổi chính) — mục 1–6 Tờ khai CT01, đối chiếu CCCD.
    {"name": "NguoiDangKy_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị đăng ký thường trú (mục 1 CT01)."},
    {
        "name": "NguoiDangKy_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDangKy_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDangKy_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị."},
    {"name": "NguoiDangKy_SoDienThoai", "desc": "Số điện thoại liên hệ (mục 5 CT01)."},
    {"name": "NguoiDangKy_Email", "desc": "Email (mục 6 CT01)."},
    # Chủ hộ — mục 7–9 CT01.
    {"name": "ChuHo_HoTen", "desc": "Họ, chữ đệm và tên chủ hộ (mục 7 CT01)."},
    {
        "name": "ChuHo_QuanHe",
        "desc": 'Mối quan hệ của NGƯỜI ĐỀ NGHỊ với chủ hộ (mục 8 CT01), chép đúng chữ trên giấy (vd "Vợ", "Con", '
                '"Chủ hộ").',
    },
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của chủ hộ (mục 9 CT01)."},
    # Nơi đề nghị đăng ký thường trú + nội dung — mục 10 CT01.
    {
        "name": "NoiDangKy_DiaChiChiTiet",
        "desc": "Phần địa chỉ DƯỚI cấp xã của nơi đề nghị đăng ký thường trú (số nhà, ngõ, đường, tổ dân phố, thôn, "
                "bản…), lấy trong nội dung đề nghị mục 10 CT01. KHÔNG kèm tên xã/phường, tỉnh/thành phố.",
    },
    {"name": "NoiDungDeNghi", "desc": 'Nội dung đề nghị: nguyên văn mục 10 CT01, bỏ chữ "Nội dung đề nghị" ở đầu.'},
    {
        "name": "ThanhVien",
        "desc": (
            "Những thành viên trong hộ gia đình cùng thay đổi (bảng mục 11 CT01), đúng thứ tự, KHÔNG gồm người đề "
            "nghị ở mục 1. Mỗi item: {hoTen, ngaySinh, gioiTinh, soDinhDanh, quanHeVoiChuHo}. Bảng trống → []."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ThanhVien"] = "x-array"

# Ô trên form (id = name). Thứ tự là thứ tự điền — cổng xoá dữ liệu khi đổi các ô trước:
#   Cơ quan (Tỉnh → Xã) → cổng nạp Thủ tục + Trường hợp + nhóm giấy tờ (extension chờ danh sách Trường hợp có option
#   — `readySelect` của ô cơ quan); Trường hợp; Hình thức (lập hộ mới / vào hộ đã có) mở khối
#   chủ hộ; đổi Trường hợp xoá khối người đề nghị; đổi Định dạng ngày xoá ô ngày sinh; gõ Địa chỉ nơi đề nghị thì cổng
#   ghi đè Nội dung đề nghị → Nội dung đứng SAU Địa chỉ.
UI_COMP_BY_NAME = {
    "cboORG": "bca-agency",
    "cboBPROC_CASE_CODE": "dom-select",
    "radIsHouseHold": "dom-radio",
    "cboFORMAT_DATE": "dom-select",
    "txtBIRTH_DATE": "dom-date",
    "txtFULLNAME": "dom-input",
    "cboGENDER_ID": "dom-select",
    "txtID_CARD_NUMBER": "dom-input",
    "txtPHONE_NUMBER": "dom-input",
    "txtEMAIL": "dom-input",
    "txtSUGGEST_DETAIL_ADDR": "dom-input",
    "txtCHANGED_CONTENT_NOTE": "dom-input",
    "txtHH_HEAD_FULLNAME": "dom-input",
    "cboRELATIONSHIP_WITH_HHHEAD_ID": "dom-select",
    "txtID_CARD_NUMBER_HHEAD": "dom-input",
    "tblNguoi_CUNGTD": "bca-rows",
}

# Cặp id Tỉnh → Xã của khối "Cơ quan thực hiện" trang thường trú (extension fillBcaAgencyField).
AGENCY_FIELD = "cboORG"
AGENCY_CITY_ID = "cboRECEIVE_ADDR_CITY_ID"
AGENCY_WARD_ID = "cboRECEIVE_ADDR_VILLAGE_ID"

# Nhãn option "Trường hợp" (cboBPROC_CASE_CODE) đúng như trên cổng (crawl 16/11/2026).
CASES = (
    "Đăng ký thường trú cả hộ",
    "Đăng ký thường trú nhân khẩu",
    "Đăng ký thường trú lần đầu với trẻ em mới sinh, công dân chưa từng đăng ký thường trú",
)
CASE_FIRST_TIME = CASES[2]
CASE_SELECT_ID = "cboBPROC_CASE_CODE"

# Nhãn radio "Hình thức" đúng như trên cổng (radio cùng value="on" → engine khớp theo nhãn).
HOUSEHOLD_NEW = "Đăng ký thường trú lập hộ mới"
HOUSEHOLD_EXISTING = "Đăng ký thường trú vào hộ đã có"

# Nhãn option ô "Định dạng" ngày sinh (cboFORMAT_DATE).
DATE_FORMAT_FULL = "Ngày tháng năm"
DATE_FORMAT_MONTH = "Tháng năm"
DATE_FORMAT_YEAR = "Năm"

# Bảng "Những thành viên trong hộ gia đình cùng thay đổi": ô dòng n có id <tiền tố><n>; thêm dòng bằng nút "thêm" ở
# dòng cuối.
MEMBER_ADD_SELECTOR = "#tblNguoi_CUNGTD a.add_CUNGTD"
MEMBER_IDS = {
    "hoTen": ("txtFULLNAME_CUNGTD", "dom-input"),
    "ngaySinh": ("txtDOB_CUNGTD", "dom-input"),
    "gioiTinh": ("cboGENDER_CUNGTD", "dom-select"),
    "soDinhDanh": ("txtIDENTIFIER_NOCARD_NUMBER_CUNGTD", "dom-input"),
    "quanHeVoiChuHo": ("cboRELATIONSHIP_CHUHO_CUNGTD", "dom-select"),
}
