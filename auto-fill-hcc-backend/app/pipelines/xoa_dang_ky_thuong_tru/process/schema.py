"""Compact schema cho "Xóa đăng ký thường trú" (1.003197, Cổng DVC Bộ Công an).

Link kê khai là trang thủ tục Cổng DVC Bộ Công an (tthc?matt=26348) → "Nộp hồ sơ" → trang kê khai
dang-ky-thuong-tru.html?TT=THUONGTRU_02 — CÙNG trang và CÙNG bộ id với Đăng ký thường trú (cboRECEIVE_ADDR_CITY_ID,
txtFULLNAME, txtBIRTH_DATE, cboGENDER_ID, bảng tblNguoi_CUNGTD…), cổng khoá Thủ tục theo TT= (mapping 24/11/2026). Khối
chủ hộ (txtHH_HEAD_FULLNAME…) JS chèn khi Thủ tục ≠ THUONGTRU_01, bắt buộc với Xóa ĐKTT.

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, CCCD). Ô form dựng ở mapper.py. Không điền: Thủ tục (khoá), radio
Khai hộ / tự khai (cổng chọn theo tài khoản), khối Nơi đề nghị (ẩn với Xóa ĐKTT, cổng xoá trắng), khối CT02 (ẩn), khối
VNeID xin ý kiến (ẩn), nhận thông báo / kết quả (mặc định của cổng), ô cam kết chkRULE (người dân tự tích).
Đính kèm ở attach/ (bảng #tblGiayToDinhKem cùng trang, nạp theo Trường hợp).
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú: dòng "Kính gửi (1)" Tờ khai CT01; Kính gửi không ghi tỉnh '
                'thì tỉnh của nơi thường trú ghi ở mục 10 CT01 / CCCD người đề nghị. Chỉ tên đơn vị hành chính, bỏ chữ '
                '"Công an". Không có nguồn nào → để trống, KHÔNG đoán.',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú (dòng "Kính gửi (1)" CT01). Giữ tiền tố '
                'Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    {
        "name": "TruongHop",
        "desc": (
            'Trường hợp xóa đăng ký thường trú, chọn ĐÚNG MỘT nhãn: "Cả hộ do không còn chỗ ở hợp pháp", "Nhân khẩu do '
            'không còn chỗ ở hợp pháp", "Cả hộ do vắng mặt trên 12 tháng", "Nhân khẩu do vắng mặt trên 12 tháng", "Cả '
            'hộ do định cư nước ngoài", "Nhân khẩu do định cư nước ngoài". Căn cứ LÝ DO XÓA ở mục 10 CT01; "Cả hộ" khi '
            'giấy ghi xóa cho cả hộ, còn lại là "Nhân khẩu". Mục 10 không nêu lý do xóa → để trống.'
        ),
    },
    # Người đề nghị xóa đăng ký thường trú = người kê khai mục 1–6 CT01, đối chiếu CCCD.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị (mục 1 CT01)."},
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị (mục 4 CT01)."},
    {"name": "NguoiDeNghi_SoDienThoai", "desc": "Số điện thoại liên hệ (mục 5 CT01)."},
    {"name": "NguoiDeNghi_Email", "desc": "Email (mục 6 CT01)."},
    # Chủ hộ — mục 7–9 CT01.
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

CONTENT_ID = "txtCHANGED_CONTENT_NOTE"

# Ô trên form (id = name), thứ tự là thứ tự điền: Cơ quan (Tỉnh → Xã; cổng nạp Thủ tục + khối chủ hộ) → Trường hợp
# (đổi là cổng tự sinh Nội dung đề nghị, nạp bảng giấy tờ, đổi danh mục quan hệ) → người đề nghị (Định dạng ngày TRƯỚC ô
# ngày sinh) → Nội dung đề nghị (SAU Trường hợp để ghi đè câu cổng tự sinh) → chủ hộ → bảng thành viên.
UI_COMP_BY_NAME = {
    "cboORG": "bca-agency",
    "cboBPROC_CASE_CODE": "dom-select",
    "cboFORMAT_DATE": "dom-select",
    "txtBIRTH_DATE": "dom-date",
    "txtFULLNAME": "dom-input",
    "cboGENDER_ID": "dom-select",
    "txtID_CARD_NUMBER": "dom-input",
    "txtPHONE_NUMBER": "dom-input",
    "txtEMAIL": "dom-input",
    CONTENT_ID: "dom-input",
    "txtHH_HEAD_FULLNAME": "dom-input",
    "cboRELATIONSHIP_WITH_HHHEAD_ID": "dom-select",
    "txtID_CARD_NUMBER_HHEAD": "dom-input",
    "tblNguoi_CUNGTD": "bca-rows",
}

# Nhãn option "Trường hợp" (cboBPROC_CASE_CODE) theo ảnh ánh xạ đính kèm của user 24/11/2026 (mapping chưa chép được
# danh mục: cổng nạp qua API sau khi chọn cơ quan; extension khớp lỏng theo chữ). Mã TT-XOA-xx khác (chết, mất tích…)
# chưa có ảnh → không chọn hộ.
CASE_NO_HOME_HH = "Cả hộ do không còn chỗ ở hợp pháp"
CASE_NO_HOME = "Nhân khẩu do không còn chỗ ở hợp pháp"
CASE_ABSENT_HH = "Cả hộ do vắng mặt trên 12 tháng"
CASE_ABSENT = "Nhân khẩu do vắng mặt trên 12 tháng"
CASE_ABROAD_HH = "Cả hộ do định cư nước ngoài"
CASE_ABROAD = "Nhân khẩu do định cư nước ngoài"
CASES = (CASE_NO_HOME_HH, CASE_NO_HOME, CASE_ABSENT_HH, CASE_ABSENT, CASE_ABROAD_HH, CASE_ABROAD)

HOUSEHOLD_HEAD = "Chủ hộ"
