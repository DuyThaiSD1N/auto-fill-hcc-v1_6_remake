"""Compact schema cho "Xóa đăng ký tạm trú" (1.010028, Cổng DVC Bộ Công an).

Trang kê khai là dang-ky-tam-tru.html?TT=TAMTRU_06 — CÙNG trang và CÙNG bộ id với Đăng ký tạm trú (txtFULLNAME,
cboDATE_FORMAT, txtDOB, cboGENDER_CODE…), cổng khoá Thủ tục theo TT= và đổi danh sách Trường hợp (mapping
20/11/2026). Ô Tỉnh/Xã cơ quan có sẵn giá trị mặc định (Hà Nội / Ba Đình) nên PHẢI chọn đè, không dùng onlyIfEmpty.

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, CCCD). Ô form dựng ở mapper.py. Không điền: Thủ tục (khoá), radio
Khai hộ / tự khai (cổng chọn theo tài khoản), khối "Thông tin đề nghị đăng ký tạm trú" gồm cả Nội dung đề nghị
txtCHANGED_NOTE (ẩn với TAMTRU_06 — nội dung đề nghị chỉ dùng để chọn Trường hợp), khối người đại diện / thời hạn
(ẩn), khối VNeID xin ý kiến (ẩn), nhận thông báo / kết quả (mặc định của cổng), ô cam kết (người dân tự tích).
Đính kèm ở attach/ (bảng #tblGiayToDinhKem cùng trang, nạp theo Trường hợp).
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú: dòng "Kính gửi (1)" Tờ khai CT01. Chỉ tên đơn vị hành '
                'chính, bỏ chữ "Công an". Giấy chỉ ghi xã (vd "Công an xã A") → để trống, KHÔNG đoán tỉnh.',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú (dòng "Kính gửi (1)" CT01). Giữ tiền tố '
                'Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    {
        "name": "TruongHop",
        "desc": (
            'Trường hợp xóa đăng ký tạm trú, chọn ĐÚNG MỘT nhãn: "Nhân khẩu do không còn chỗ ở hợp pháp", "Cả hộ do '
            'không còn chỗ ở hợp pháp", "Nhân khẩu do vắng mặt từ 6 tháng trở lên", "Hộ do vắng mặt từ 6 tháng trở '
            'lên", "Nhân khẩu do đã đăng ký thường trú tại chính nơi tạm trú", "Hộ do đã đăng ký thường trú tại chính '
            'nơi tạm trú". Căn cứ lý do ở mục 10 CT01; "Hộ"/"Cả hộ" chỉ khi giấy ghi xóa cho cả hộ, còn lại là '
            '"Nhân khẩu". Không có căn cứ → để trống.'
        ),
    },
    # Người đề nghị xóa đăng ký tạm trú = người kê khai mục 1–6 CT01, đối chiếu CCCD.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị (mục 1 CT01)."},
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị (mục 4 CT01)."},
    {"name": "NguoiDeNghi_SoDienThoai", "desc": "Số điện thoại liên hệ (mục 5 CT01)."},
    {"name": "NguoiDeNghi_Email", "desc": "Email (mục 6 CT01)."},
    # Chủ hộ tạm trú — mục 7–9 CT01.
    {"name": "ChuHo_HoTen", "desc": "Họ, chữ đệm và tên chủ hộ (mục 7 CT01)."},
    {
        "name": "ChuHo_QuanHe",
        "desc": 'Mối quan hệ của NGƯỜI ĐỀ NGHỊ với chủ hộ (mục 8 CT01), chép đúng chữ trên giấy (vd "Chủ hộ", "Con").',
    },
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của chủ hộ (mục 9 CT01)."},
    {"name": "NoiDungDeNghi", "desc": 'Nội dung đề nghị: nguyên văn mục 10 CT01, bỏ chữ "Nội dung đề nghị" ở đầu.'},
    {
        "name": "ThanhVien",
        "desc": (
            "Những thành viên trong hộ gia đình cùng thay đổi (bảng mục 11 CT01), đúng thứ tự, KHÔNG gồm người đề "
            "nghị và chủ hộ. Mỗi item: {hoTen, ngaySinh, gioiTinh, soDinhDanh, quanHeVoiChuHo}. Bảng trống → []."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ThanhVien"] = "x-array"

# Cặp id Tỉnh → Xã của khối "Cơ quan thực hiện" trang tạm trú (khác trang thường trú *_ID).
AGENCY_FIELD = "cboRECEIVE_ORG"
AGENCY_CITY_ID = "cboRECEIVE_ADDR_CITY_CODE"
AGENCY_WARD_ID = "cboRECEIVE_ADDR_VILLAGE_CODE"
CASE_SELECT_ID = "cboBPROC_CASE_CODE"

# Ô trên form (id = name), thứ tự là thứ tự điền: Cơ quan → Trường hợp (đổi là cổng nạp lại bảng giấy tờ + danh mục
# quan hệ) → người đề nghị (Định dạng ngày TRƯỚC ô ngày sinh) → chủ hộ tạm trú → bảng thành viên.
UI_COMP_BY_NAME = {
    AGENCY_FIELD: "bca-agency",
    CASE_SELECT_ID: "dom-select",
    "txtFULLNAME": "dom-input",
    "cboDATE_FORMAT": "dom-select",
    "txtDOB": "dom-date",
    "cboGENDER_CODE": "dom-select",
    "txtIDENTIFIER_NUMBER": "dom-input",
    "txtPHONE_NUMBER": "dom-input",
    "txtEMAIL": "dom-input",
    "txtHH_PERSON_FULLNAME": "dom-input",
    "cboHH_PERSON_RELATIONSHIP_CODE": "dom-select",
    "txtHH_PERSON_IDENTIFIER_NUMBER": "dom-input",
    "listNormal": "bca-rows",
}

# Nhãn option "Trường hợp" (cboBPROC_CASE_CODE) đúng như trên cổng (sheet "Danh mục Option", mã TAT-XOA-13…18).
CASE_NO_HOME = "Nhân khẩu do không còn chỗ ở hợp pháp"
CASE_NO_HOME_HH = "Cả hộ do không còn chỗ ở hợp pháp"
CASE_ABSENT = "Nhân khẩu do vắng mặt từ 6 tháng trở lên"
CASE_ABSENT_HH = "Hộ do vắng mặt từ 6 tháng trở lên"
CASE_PERMANENT = "Nhân khẩu do đã đăng ký thường trú tại chính nơi tạm trú"
CASE_PERMANENT_HH = "Hộ do đã đăng ký thường trú tại chính nơi tạm trú"
CASES = (CASE_NO_HOME, CASE_NO_HOME_HH, CASE_ABSENT, CASE_ABSENT_HH, CASE_PERMANENT, CASE_PERMANENT_HH)

HOUSEHOLD_HEAD = "Chủ hộ"

# Bảng "Những thành viên trong hộ gia đình cùng thay đổi" (#listNormal): ô dòng n có id <tiền tố><n>, thêm dòng bằng
# nút "+" (add_CUNGTD). Khác trang thường trú: có thêm cột Định dạng ngày sinh (chọn TRƯỚC ô ngày).
MEMBER_ADD_SELECTOR = "#listNormal .add_CUNGTD, #listNormal #add_CUNGTD"
MEMBER_IDS = {
    "hoTen": ("txtFULLNAME_CUNGTD", "dom-input"),
    "dinhDang": ("cboDATE_FORMAT_CUNGTD", "dom-select"),
    "ngaySinh": ("txtDOB_CUNGTD", "dom-input"),
    "gioiTinh": ("cboGENDER_CUNGTD", "dom-select"),
    "soDinhDanh": ("txtIDENTIFIER_NOCARD_NUMBER_CUNGTD", "dom-input"),
    "quanHeVoiChuHo": ("cboRELATIONSHIP_CHUHO_CUNGTD", "dom-select"),
}
