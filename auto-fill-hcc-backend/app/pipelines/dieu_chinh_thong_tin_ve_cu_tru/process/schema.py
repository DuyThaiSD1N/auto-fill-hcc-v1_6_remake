"""Compact schema cho "Điều chỉnh thông tin về cư trú" (1.010039, Cổng DVC Bộ Công an).

Trang kê khai là dang-ky-thuong-tru.html?TT=THUONGTRU_08 — CÙNG trang và CÙNG bộ id với Đăng ký thường trú
(txtFULLNAME, txtHH_HEAD_FULLNAME, bảng tblNguoi_CUNGTD…), cổng chỉ đổi Thủ tục (khoá) + Trường hợp. Trường hợp hiện
có MỘT option "Thay đổi chủ hộ" (mapping 16/11/2026): người đề nghị là người được cử làm chủ hộ MỚI, khối chủ hộ
là chủ hộ HIỆN TẠI trong CSDL (chủ hộ cũ, thường đã chết).

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, văn bản thống nhất của các thành viên, trích lục khai tử, CCCD).
Ô form dựng ở mapper.py. Không điền: Thủ tục (cổng khoá theo TT= trên URL), khối "Nơi đề nghị đăng ký thường trú"
(ẩn ở thủ tục này), "Danh sách người cần xin ý kiến" (gõ vào đó cổng đổi nút nộp thành gửi xác nhận qua VNeID),
khối CT02, nhận thông báo / kết quả (mặc định của cổng), ô cam kết (người dân tự tích).
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú: dòng "Kính gửi (1)" Tờ khai CT01, "Kính gửi" văn bản '
                'thống nhất hoặc "Cơ quan tiếp nhận" trên bìa hồ sơ; không có thì tỉnh nơi thường trú của hộ. Chỉ tên '
                'đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú (cùng nguồn với CoQuan_Tinh). Giữ tiền tố '
                'Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    # Người đề nghị điều chỉnh = người kê khai mục 1–6 CT01 (người được cử làm chủ hộ mới), đối chiếu CCCD.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị (mục 1 CT01)."},
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị."},
    {"name": "NguoiDeNghi_SoDienThoai", "desc": "Số điện thoại liên hệ (mục 5 CT01)."},
    {"name": "NguoiDeNghi_Email", "desc": "Email (mục 6 CT01)."},
    # Chủ hộ HIỆN TẠI trong CSDL (chủ hộ cũ) — mục 7–9 CT01.
    {
        "name": "ChuHo_HoTen",
        "desc": "Họ, chữ đệm và tên chủ hộ ở mục 7 CT01 (chủ hộ hiện tại / chủ hộ cũ, KHÔNG phải người được cử làm "
                "chủ hộ mới). Không có CT01 → chủ hộ cũ ghi trong văn bản thống nhất của các thành viên.",
    },
    {
        "name": "ChuHo_QuanHe",
        "desc": 'Mối quan hệ của NGƯỜI ĐỀ NGHỊ với chủ hộ đó (mục 8 CT01), chép đúng chữ trên giấy (vd "Con", '
                '"Vợ"). Không có CT01 → cột quan hệ với chủ hộ cũ của người đề nghị trong văn bản thống nhất.',
    },
    {"name": "ChuHo_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của chủ hộ đó (mục 9 CT01)."},
    {"name": "NoiDungDeNghi", "desc": 'Nội dung đề nghị: nguyên văn mục 10 CT01, bỏ chữ "Nội dung đề nghị" ở đầu.'},
    {
        "name": "ThanhVien",
        "desc": (
            "Những thành viên trong hộ gia đình cùng thay đổi (bảng mục 11 CT01), đúng thứ tự, KHÔNG gồm người đề "
            "nghị ở mục 1 và chủ hộ cũ. Mỗi item: {hoTen, ngaySinh, gioiTinh, soDinhDanh, quanHeVoiChuHo} — "
            "quanHeVoiChuHo chép đúng cột quan hệ của bảng mục 11. Bảng trống / không có CT01 → []."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ThanhVien"] = "x-array"

# Ô trên form (id = name), thứ tự là thứ tự điền: Cơ quan (Tỉnh → Xã) → cổng nạp Trường hợp + bảng giấy tờ;
# Trường hợp (đổi là cổng xoá khối người đề nghị); Định dạng ngày TRƯỚC ô ngày sinh (đổi định dạng xoá ô ngày).
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
}

# Nhãn option "Trường hợp" (cboBPROC_CASE_CODE) đúng như trên cổng — hiện chỉ có một.
CASE_CHANGE_HEAD = "Thay đổi chủ hộ"
