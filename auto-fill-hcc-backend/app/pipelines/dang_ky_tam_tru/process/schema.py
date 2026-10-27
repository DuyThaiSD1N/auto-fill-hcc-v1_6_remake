"""Compact schema cho "Đăng ký tạm trú" (Cổng DVC Bộ Công an, dichvucong.dancuquocgia.gov.vn).

LLM chỉ trả DỮ KIỆN đọc từ giấy tờ (CCCD, Tờ khai CT01, hợp đồng thuê/mượn/ở nhờ, GCN quyền sử dụng
đất). Ô của form (id = name trên trang: txtFULLNAME, txtDOB, cboGENDER_CODE…) dựng trong mapper.py.

Khối "Cơ quan thực hiện" (cboRECEIVE_ADDR_*) trợ lý đã chọn với công dân trước khi nhận giấy tờ, và cổng
tự chép sang "Nơi đề nghị đăng ký tạm trú" (cboSUGGEST_*, bị khoá) → pipeline KHÔNG điền các ô đó.
"""

FIELDS: list[dict] = [
    # Người đề nghị đăng ký tạm trú — nguồn ưu tiên: CCCD → Tờ khai CT01 → hợp đồng thuê.
    {"name": "NguoiDangKy_HoTen", "desc": "Họ, chữ đệm và tên khai sinh của người đăng ký tạm trú."},
    {
        "name": "NguoiDangKy_NgaySinh",
        "desc": "Ngày sinh của người đăng ký: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.",
    },
    {"name": "NguoiDangKy_GioiTinh", "desc": 'Giới tính của người đăng ký: "Nam" hoặc "Nữ".'},
    {"name": "NguoiDangKy_SoDinhDanh", "desc": "Số định danh cá nhân (12 chữ số) của người đăng ký."},
    {"name": "NguoiDangKy_SoDienThoai", "desc": "Số điện thoại liên hệ của người đăng ký (Tờ khai CT01 mục 5)."},
    {"name": "NguoiDangKy_Email", "desc": "Email của người đăng ký (Tờ khai CT01 mục 6)."},
    # Nơi đề nghị đăng ký tạm trú.
    {
        "name": "NoiTamTru_DiaChiChiTiet",
        "desc": "Phần địa chỉ DƯỚI cấp xã của nơi đề nghị đăng ký tạm trú: số nhà, ngách, ngõ, đường, "
                "tổ dân phố, thôn, xóm. KHÔNG kèm tên xã/phường, quận/huyện, tỉnh/thành phố.",
    },
    {"name": "NoiTamTru_Xa", "desc": "Xã/phường/đặc khu của nơi đề nghị đăng ký tạm trú (địa giới mới nếu giấy ghi cả hai)."},
    {"name": "NoiTamTru_Tinh", "desc": "Tỉnh/thành phố của nơi đề nghị đăng ký tạm trú."},
    {
        "name": "NoiDungDeNghi",
        "desc": "Nội dung đề nghị: nguyên văn mục 10 Tờ khai CT01 (nơi đề nghị, chỗ ở hợp pháp…). Không có "
                "CT01 thì tóm tắt theo hợp đồng thuê/giấy chứng nhận: đăng ký tạm trú tại địa chỉ nào, chỗ ở "
                "hợp pháp do thuê/mượn/ở nhờ của ai.",
    },
    {"name": "ThoiHan_DenNgay", "desc": "Thời hạn tạm trú đề nghị ĐẾN NGÀY, dd/mm/yyyy."},
    {
        "name": "ChuHo_QuanHe",
        "desc": 'Mối quan hệ của người đăng ký với chủ hộ (Tờ khai CT01 mục 8), vd "Chủ hộ", "Con", "Vợ".',
    },
    # Chủ sở hữu chỗ ở hợp pháp (người cần xin ý kiến qua VNeID) — nguồn: CT01 ô "Ý kiến của chủ sở hữu chỗ ở hợp
    # pháp" (8) → hợp đồng phần BÊN CHO THUÊ / bên cho mượn, cho ở nhờ → GCN mục I (người sử dụng đất, chủ sở hữu).
    {"name": "ChuSoHuu_HoTen", "desc": "Họ tên chủ sở hữu chỗ ở hợp pháp (người cho thuê/cho mượn/cho ở nhờ)."},
    {
        "name": "ChuSoHuu_SoDinhDanh",
        "desc": 'Số định danh cá nhân 12 chữ số của chủ sở hữu chỗ ở (GCN/hợp đồng có thể ghi nhãn "CMND số").',
    },
    {
        "name": "ChuSoHuu_NgaySinh",
        "desc": "Ngày sinh của chủ sở hữu chỗ ở: dd/mm/yyyy; giấy chỉ ghi năm sinh (vd GCN \"Năm sinh: 1975\") thì yyyy.",
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDangKy_NgaySinh", "ThoiHan_DenNgay", "ChuSoHuu_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"

# Ô trên form (id = name). Thứ tự ở đây là thứ tự điền: "Định dạng" ngày sinh trước ô ngày sinh.
UI_COMP_BY_NAME = {
    "txtFULLNAME": "dom-input",
    "cboDATE_FORMAT": "dom-select",
    "txtDOB": "dom-date",
    "cboGENDER_CODE": "dom-select",
    "txtIDENTIFIER_NUMBER": "dom-input",
    "txtPHONE_NUMBER": "dom-input",
    "txtEMAIL": "dom-input",
    "txtSUGGEST_ADDRESS": "dom-input",
    "cboHH_PERSON_RELATIONSHIP_CODE": "dom-select",
    "txtCHANGED_NOTE": "dom-input",
    "txtTEMP_RESIDENT_TO": "dom-date",
    # Khối "Thông tin xác nhận tờ khai thông tin cư trú bản điện tử" — dòng 0 của "Danh sách người cần xin ý kiến".
    "txtFULLNAME0": "dom-input",
    "txtCITIZENNUMBER0": "dom-input",
    "txtDOB0": "dom-date",
    "cboROLESID0": "dom-select",
}

# Vai trò của người cần xin ý kiến (cboROLESID0) khi đó là chủ sở hữu chỗ ở — nhãn option đúng như trên cổng.
ROLE_OWNER = "Chủ sở hữu chỗ ở hợp pháp"

# Nhãn option của ô "Định dạng" (cboDATE_FORMAT) đúng như trên cổng.
DATE_FORMAT_FULL = "Ngày tháng năm"
DATE_FORMAT_MONTH = "Tháng năm"
DATE_FORMAT_YEAR = "Năm"

# Ô "Quan hệ với chủ hộ tạm trú" (select2, 77 lựa chọn). Form mặc định "Đăng ký tạm trú lập hộ mới" → người đăng
# ký đứng làm chủ hộ tạm trú của chính mình.
HOUSEHOLD_HEAD = "Chủ hộ"
