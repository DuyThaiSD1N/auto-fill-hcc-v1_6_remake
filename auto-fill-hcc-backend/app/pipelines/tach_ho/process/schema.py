"""Compact schema cho "Tách hộ" (1.010038, Cổng DVC Bộ Công an).

Trang kê khai là dang-ky-thuong-tru.html?TT=THUONGTRU_05 — CÙNG trang và CÙNG bộ id với Đăng ký thường trú
(txtFULLNAME, txtSUGGEST_DETAIL_ADDR, bảng tblNguoi_CUNGTD…), cổng khoá Thủ tục theo TT= (mapping 20/11/2026).
Người đề nghị là người tách ra làm chủ hộ MỚI; khối chủ hộ không có trên form; bảng "cùng thay đổi" là các thành viên
tách theo, quan hệ tính với chủ hộ mới.

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (Tờ khai CT01, đơn xác nhận tách hộ, CCCD, giấy khai sinh, giấy chứng nhận kết
hôn, giấy tờ chỗ ở). Ô form dựng ở mapper.py. Không điền: Thủ tục (khoá), radio Khai hộ / người khai là người tách hộ
(cổng chọn sẵn theo tài khoản), Tỉnh/Xã nơi đề nghị (cổng khoá, chép từ Cơ quan thực hiện), khối CT02 (ẩn), "Danh
sách người cần xin ý kiến" (gõ vào đó cổng đổi nút nộp thành gửi xác nhận qua VNeID), các popup giấy tờ điện tử / BM01
/ BM02, nhận thông báo / kết quả (mặc định của cổng), ô cam kết (người dân tự tích). Thủ tục không đính kèm.
"""

FIELDS: list[dict] = [
    {
        "name": "CoQuan_Tinh",
        "desc": 'Tỉnh/thành phố của cơ quan đăng ký cư trú: dòng "Kính gửi (1)" Tờ khai CT01; không có thì tỉnh nơi '
                'thường trú / nơi tách hộ trong đơn xác nhận tách hộ. Chỉ tên đơn vị hành chính, bỏ chữ "Công an".',
    },
    {
        "name": "CoQuan_Xa",
        "desc": 'Xã/phường/đặc khu của cơ quan đăng ký cư trú (cùng nguồn với CoQuan_Tinh). Giữ tiền tố '
                'Xã/Phường/Đặc khu, bỏ chữ "Công an".',
    },
    # Người đề nghị tách hộ = người kê khai mục 1–6 CT01 / người làm đơn xác nhận tách hộ (chủ hộ mới), đối chiếu CCCD.
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đề nghị tách hộ (mục 1 CT01)."},
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số định danh cá nhân 12 chữ số của người đề nghị (mục 4 CT01)."},
    {"name": "NguoiDeNghi_SoDienThoai", "desc": "Số điện thoại liên hệ (mục 5 CT01)."},
    {"name": "NguoiDeNghi_Email", "desc": "Email (mục 6 CT01)."},
    {
        "name": "NoiTachHo_DiaChiChiTiet",
        "desc": "Phần địa chỉ DƯỚI cấp xã của nơi tách hộ / nơi đăng ký thường trú của hộ mới (số nhà, ngõ, đường, tổ "
                "dân phố, thôn, bản…): lấy trong nội dung đề nghị mục 10 CT01; không có thì \"Hộ khẩu thường trú\" / "
                "\"Nơi ở hiện tại\" của người làm đơn xác nhận tách hộ. KHÔNG kèm tên xã/phường, tỉnh/thành phố.",
    },
    {"name": "NoiDungDeNghi", "desc": 'Nội dung đề nghị: nguyên văn mục 10 CT01, bỏ chữ "Nội dung đề nghị" ở đầu.'},
    {
        "name": "ThanhVien",
        "desc": (
            "Những thành viên tách theo người đề nghị (bảng mục 11 CT01; không có CT01 thì bảng thành viên của đơn xác "
            "nhận tách hộ), đúng thứ tự, KHÔNG gồm người đề nghị. Mỗi item: {hoTen, ngaySinh, gioiTinh, soDinhDanh, "
            "quanHeVoiChuHo} — quanHeVoiChuHo là quan hệ với người đề nghị (chủ hộ mới), chép đúng chữ trên bảng. "
            "Bảng chỉ ghi năm sinh thì lấy ngày sinh đầy đủ từ CCCD / giấy khai sinh / giấy kết hôn của CHÍNH người "
            "đó. Bảng trống → []."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ThanhVien"] = "x-array"

# Ô trên form (id = name), thứ tự là thứ tự điền: Cơ quan (Tỉnh → Xã) → cổng nạp Trường hợp; Trường hợp (đổi là cổng
# xoá khối người đề nghị); Định dạng ngày TRƯỚC ô ngày sinh (đổi định dạng xoá ô ngày); gõ Địa chỉ nơi đề nghị thì cổng
# ghi đè Nội dung đề nghị → Nội dung đứng SAU Địa chỉ (như Đăng ký thường trú).
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
    "txtSUGGEST_DETAIL_ADDR": "dom-input",
    "txtCHANGED_CONTENT_NOTE": "dom-input",
    "tblNguoi_CUNGTD": "bca-rows",
}

# "Trường hợp" (cboBPROC_CASE_CODE): mapping 20/11/2026 chưa chép được danh mục (cổng nạp qua API sau khi chọn cơ
# quan). Extension khớp lỏng theo chữ (bestChoiceOption) → "Tách hộ" bắt nhãn đầy đủ chứa cụm này.
CASE_SPLIT = "Tách hộ"
