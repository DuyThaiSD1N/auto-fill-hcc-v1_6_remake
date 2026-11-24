"""Compact schema cho "Xác nhận thông tin về cư trú" (1.010041, Cổng DVC Bộ Công an).

Trang kê khai là dang-ky-thuong-tru.html?TT=THUONGTRU_09 — CÙNG trang và CÙNG bộ id với Đăng ký thường trú
(txtFULLNAME, txtHH_HEAD_FULLNAME, bảng tblNguoi_CUNGTD…), cổng khoá Thủ tục theo TT= và chỉ đổi danh sách Trường hợp:
"Cấp cho NK thường trú trên địa bàn quản lý" / "… khác địa bàn quản lý" (mapping 16/11/2026) — chọn theo nơi thường
trú của người đề nghị so với cơ quan tiếp nhận.

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, giấy ủy quyền, CCCD, trang bìa). Ô form dựng ở mapper.py. Không
điền: Thủ tục (khoá), radio Khai hộ / người khai là người xác nhận (cổng chọn sẵn theo tài khoản), khối CT02 và "Nơi đề
nghị đăng ký thường trú" (ẩn), "Danh sách người cần xin ý kiến" (gõ vào đó cổng đổi nút nộp thành gửi xác nhận qua
VNeID), nhận thông báo, địa chỉ nhận kết quả qua bưu chính, ô cam kết (người dân tự tích). Đính kèm ở attach/.
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú: dòng "Kính gửi (1)" Tờ khai CT01, cơ quan nêu trong giấy ủy '
                'quyền hoặc "Cơ quan tiếp nhận" trên bìa hồ sơ. Chỉ tên đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú (cùng nguồn với CoQuan_Tinh). Giữ tiền tố '
                'Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    # Người đề nghị xác nhận = người kê khai mục 1–6 CT01 (bên ủy quyền), KHÔNG phải người nộp thay.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị (mục 1 CT01)."},
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị (mục 4 CT01)."},
    {
        "name": "NguoiDeNghi_SoDienThoai",
        "desc": "Số điện thoại liên hệ của người đề nghị (mục 5 CT01; không có thì số của bên ủy quyền trong giấy ủy "
                "quyền). KHÔNG lấy số của người được ủy quyền.",
    },
    {"name": "NguoiDeNghi_Email", "desc": "Email của người đề nghị (mục 6 CT01)."},
    {
        "name": "NoiThuongTru_Tinh",
        "desc": "Tỉnh/thành phố nơi thường trú của người đề nghị: theo mục 10 CT01, nơi thường trú của bên ủy quyền "
                "trong giấy ủy quyền hoặc nơi cư trú trên thẻ căn cước CỦA CHÍNH người đề nghị; không có thì nơi "
                "thường trú của chủ hộ (cùng hộ). Không có giấy nào ghi → để trống.",
    },
    {"name": "NoiThuongTru_Xa", "desc": "Xã/phường/đặc khu nơi thường trú của người đề nghị (cùng nguồn), giữ tiền tố."},
    # Chủ hộ — mục 7–9 CT01.
    {"name": "ChuHo_HoTen", "desc": "Họ, chữ đệm và tên chủ hộ (mục 7 CT01)."},
    {
        "name": "ChuHo_QuanHe",
        "desc": 'Mối quan hệ của NGƯỜI ĐỀ NGHỊ với chủ hộ (mục 8 CT01), chép đúng chữ trên giấy (vd "Con", "Vợ", '
                '"Chủ hộ").',
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
    {
        "name": "HinhThucNhanKetQua",
        "desc": 'Hình thức nhận kết quả nếu giấy ghi (bìa hồ sơ, giấy ủy quyền): chép đúng chữ trên giấy, vd "Bản giấy, '
                'nhận trực tiếp", "qua bưu chính", "nhận trên cổng dịch vụ công". Không giấy nào ghi → để trống.',
    },
    {
        "name": "SoLuongPhieu",
        "desc": "Số lượng phiếu / bản xác nhận thông tin về cư trú đề nghị cấp, chỉ khi giấy ghi rõ. Không ghi → trống.",
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ThanhVien"] = "x-array"

# Ô trên form (id = name), thứ tự là thứ tự điền: Cơ quan (Tỉnh → Xã) → cổng nạp Trường hợp; Trường hợp (đổi là cổng
# xoá khối người đề nghị); Định dạng ngày TRƯỚC ô ngày sinh (đổi định dạng xoá ô ngày); Hình thức nhận kết quả TRƯỚC
# Số lượng phiếu (ô số lượng nằm trong khối cổng mở theo hình thức).
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
    "txtHH_HEAD_FULLNAME": "dom-input",
    "cboRELATIONSHIP_WITH_HHHEAD_ID": "dom-select",
    "txtID_CARD_NUMBER_HHEAD": "dom-input",
    "tblNguoi_CUNGTD": "bca-rows",
    "txtCHANGED_CONTENT_NOTE": "dom-input",
    "cboTYPE_GET_RESULT": "dom-select",
    "txtNUMBER_OF_RESULT": "dom-input",
}

# Nhãn option "Trường hợp" (cboBPROC_CASE_CODE) đúng như trên cổng.
CASE_IN_AREA = "Cấp cho NK thường trú trên địa bàn quản lý"
CASE_OUT_AREA = "Cấp cho NK thường trú khác địa bàn quản lý"

# Nhãn option "Hình thức nhận kết quả" (cboTYPE_GET_RESULT).
RESULT_DIRECT = "Nhận trực tiếp"
RESULT_POST = "Qua đường bưu chính"
RESULT_PORTAL = "Nhận qua cổng thông tin"
