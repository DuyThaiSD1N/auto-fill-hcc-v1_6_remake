"""Compact schema cho thủ tục 2.002862 — Hỗ trợ chi phí mai táng người dân tộc thiểu số Lai Châu.

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là đúng bộ ô
``CongDan_*`` của eForm Lai Châu (file mapping "HS MAI TÁNG NQ 53"); ô bắt buộc (*): Họ và tên, Ngày Sinh,
Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã/Thị trấn, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Hồ sơ có BA người: người chết (Tờ khai mục I, Biên bản mục III, trích lục), người đi khai tử (chỉ trên
trích lục) và người khai = người đứng ra tổ chức mai táng = NGƯỜI NỘP. Mọi field dưới đây là của người
nộp, trừ ``NguoiChet_HoTen`` chỉ dùng để chặn trường hợp đọc nhầm thẻ CCCD của người chết.

Cố ý KHÔNG phát (không có nguồn trên giấy tờ, bịa là sai): Fax, Website, Email, Số/Ngày/Nơi cấp GCN/GP
(không lấy số Giấy chứng nhận hộ nghèo), "Địa chỉ chi tiết" nước ngoài (readonly) và ô ẩn maDMDiaChi.
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của NGƯỜI NỘP — nguồn ưu tiên 1 cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên thẻ CCCD/CMND/Căn cước của người nộp (người đứng ra mai táng)."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND trên thẻ; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên thẻ: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc",
     "desc": "Dân tộc IN TRÊN THẺ. Thẻ Căn cước mẫu mới (tiêu đề \"CĂN CƯỚC\") không in dân tộc → bỏ field."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp thẻ, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp thẻ. Thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an"; OCR thấy "CỤC TRƯỞNG CỤC CẢNH '
             'SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú/thường trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}. Nguồn CUỐI CÙNG cho "
             "địa chỉ: bản scan thẻ hay mất dấu và thẻ cũ còn ghi tỉnh/huyện trước sáp nhập."},

    # Tờ khai đề nghị Mẫu số 01 mục II (thiếu Tờ khai thì Biên bản Mẫu số 02 mục I.2).
    {"name": "ToKhai_HoTen",
     "desc": "Họ tên người đứng ra tổ chức mai táng: Tờ khai Mẫu số 01 mục II.2.a \"Họ và tên (Chủ hộ hoặc "
             "người đại diện)\" hoặc II.1.b người đại diện cơ quan; không có Tờ khai thì Biên bản Mẫu số 02 "
             "mục I.2. KHÔNG lấy họ tên người chết (mục I Tờ khai/mục III Biên bản)."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh của người đứng ra mai táng (Tờ khai mục II.2.a/Biên bản I.2), dd/mm/yyyy."},
    {"name": "ToKhai_SoCccd", "desc": "Số CCCD của người đứng ra mai táng (Tờ khai mục II.2.a/Biên bản I.2)."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD của người đứng ra mai táng (Tờ khai mục II.2.a/Biên bản I.2), dd/mm/yyyy."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD của người đứng ra mai táng (Tờ khai mục II.2.a/Biên bản I.2)."},
    {"name": "ToKhai_ThuongTru",
     "desc": "Nơi THƯỜNG TRÚ của người đứng ra mai táng (Tờ khai mục II.2.b \"Thường trú\" hoặc Biên bản I.2), "
             "object {quocGia,tinh,xa,chiTietDuoiXa}. Dòng viết liền \"<bản/thôn>, <xã/phường>, <tỉnh>\": cụm "
             "cuối = tinh, cụm trước = xa, phần còn lại = chiTietDuoiXa. KHÔNG lấy nơi thường trú của người chết."},
    {"name": "ToKhai_NoiO",
     "desc": "\"Nơi ở\" của người đứng ra mai táng (Tờ khai mục II.2.b), object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "NguoiNop_DienThoai",
     "desc": "Số điện thoại của người đứng ra mai táng: Biên bản Mẫu số 02 mục I.2 \"Số điện thoại\" (hoặc Tờ "
             "khai nếu có). KHÔNG lấy số điện thoại đại diện thôn/bản, số tài khoản ngân hàng hay số CCCD."},
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC đứng ra mai táng (Tờ khai mục II.1.a / Biên bản mục I.1.a). Mục này thường để "
             "chấm chấm khi hộ gia đình, cá nhân đứng ra → BỎ FIELD; không lấy tên hộ gia đình/người dân."},

    # Giấy chứng nhận hộ nghèo, hộ cận nghèo — nguồn dân tộc của người nộp khi thẻ mới không in dân tộc.
    {"name": "HoNgheo_ChuHo", "desc": "Họ tên ở dòng \"Hộ gia đình ông/bà: ...\" của Giấy chứng nhận hộ nghèo, hộ cận nghèo."},
    {"name": "HoNgheo_DanToc",
     "desc": "Dân tộc ghi NGAY SAU tên chủ hộ trên dòng \"Hộ gia đình ông/bà: ... Dân tộc: ...\". KHÔNG lấy cột "
             "dân tộc trong bảng danh sách thành viên."},

    # Người chết — chỉ để chặn đọc nhầm thẻ CCCD của người chết thành của người nộp.
    {"name": "NguoiChet_HoTen",
     "desc": "Họ tên NGƯỜI CHẾT (Trích lục khai tử \"Họ, chữ đệm, tên\", Tờ khai mục I.1, Biên bản mục III)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "ToKhai_NgaySinh", "ToKhai_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "ToKhai_ThuongTru", "ToKhai_NoiO"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô bước 2 theo file mapping (name = field-key của Nth FormBuilder): <select> -> dom-select, <input> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*) — cổng tự chuyển IN HOA.
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức — chỉ khi tổ chức đứng ra mai táng.
    "CongDan_ngaySinhCongDan": "dom-input",       # Ngày Sinh (*) dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",      # Giới tính (*) — mặc định "Nữ" nên luôn phải chọn lại.
    "CongDan_danTocCongDan": "dom-select",        # Dân tộc (*) — selectpicker 498 option.
    "CongDan_soCmnd": "dom-input",                # Số CMND/CCCD (*)
    "CongDan_ngayCapCmnd": "dom-input",           # Ngày cấp CMND/CCCD
    "CongDan_noiCapCmnd": "dom-input",            # Nơi cấp CMND/CCCD
    # Địa chỉ 2 cấp tỉnh → xã: phát maTinhThanh TRƯỚC (danh mục xã nạp theo tỉnh).
    "CongDan_maTinhThanh": "dom-select",          # Tỉnh/Thành phố (*)
    "CongDan_maPhuongXa": "dom-select",           # Phường/Xã/Thị trấn (*)
    "CongDan_diaChi": "dom-input",                # Số nhà/Đường/Tổ/Ấp/Thôn/Xóm (*)
    "CongDan_diDong": "dom-input",                # Di động — nhập liền không khoảng trắng.
    "CongDan_maTinhCapCMND": "dom-select",        # Nơi cấp CMND (CA Tỉnh) — chỉ CMND do công an tỉnh cấp.
    "CongDan_maDMQuocGia": "dom-select",          # Quốc gia
    "CongDan_soCCCD": "dom-input",                # Số CCCD (trùng Số CMND/CCCD)
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi đầy đủ)
}

UI_ALIASES = {"CongDan_soCCCD": ["soCCCD"]}
