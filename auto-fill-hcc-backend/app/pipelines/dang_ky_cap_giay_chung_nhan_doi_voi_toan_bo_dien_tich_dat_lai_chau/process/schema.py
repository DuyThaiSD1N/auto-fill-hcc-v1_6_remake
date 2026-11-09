"""Compact schema cho thủ tục 1.115590 — Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng (Lai Châu).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ; ô UI ``CongDan_*`` do mapper dựng. Bước 2 của cổng là đúng bộ ô
``CongDan_*`` của eForm Lai Châu (file mapping "Mapping_1.115590_LaiChau_Buoc2_NguoiNop"); ô bắt buộc (*): Họ và
tên, Ngày Sinh, Giới tính, Dân tộc, Số CMND/CCCD, Tỉnh/Thành phố, Phường/Xã/Thị trấn, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.

Hồ sơ mẫu KHÔNG có thẻ CCCD: nhân thân ghép từ Đơn đăng ký biến động Mẫu số 16 (họ tên, năm sinh, số CCCD, địa
chỉ, mã số thuế, điện thoại), Giấy ủy quyền (ngày sinh đầy đủ, ngày/nơi cấp CCCD, thường trú của BÊN ỦY QUYỀN) và
Giấy chứng nhận đã cấp (danh xưng Ông/Bà, trang "Những thay đổi sau khi cấp" ghi số CCCD + thường trú mới). Giấy
ủy quyền có HAI người: chỉ lấy bên ủy quyền (= người sử dụng đất), không lấy người được ủy quyền.

Cố ý KHÔNG phát (theo file mapping: để trống hoặc không có nguồn): Fax, Website, Số/Ngày/Nơi cấp GCN/GP (dành cho
tổ chức — KHÔNG nhập số phát hành Giấy chứng nhận QSDĐ), "Địa chỉ chi tiết" nước ngoài (readonly) và ô ẩn
maDMDiaChi. Dân tộc chỉ phát khi thẻ CCCD có in (Đơn, GCN, Giấy ủy quyền đều không ghi).
"""

FIELDS: list[dict] = [
    # Thẻ CCCD/CMND/Căn cước của người sử dụng đất (nếu hồ sơ có) — nguồn ưu tiên 1 cho nhân thân.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên thẻ CCCD/CMND/Căn cước."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND trên thẻ; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên thẻ, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên thẻ: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_DanToc", "desc": "Dân tộc IN TRÊN THẺ. Thẻ Căn cước mẫu mới không in dân tộc → bỏ field."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp thẻ, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp thẻ. Thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an"; OCR thấy "CỤC TRƯỞNG CỤC CẢNH '
             'SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi cư trú/thường trú IN TRÊN THẺ, object {quocGia,tinh,xa,chiTietDuoiXa}. Thẻ cũ hay còn ghi "
             "tỉnh/huyện trước sáp nhập."},

    # Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16) mục I — nguồn chính.
    {"name": "Don_HoTen",
     "desc": "Họ tên người sử dụng đất ở mục I \"Tên\" của Đơn đăng ký biến động (Mẫu số 16), bỏ phần \"Năm "
             "sinh ...\" viết liền phía sau."},
    {"name": "Don_SoGiayTo",
     "desc": "Số giấy tờ nhân thân ở mục I \"Giấy tờ nhân thân/pháp nhân\" của Đơn (thường \"CCCD: <12 số>\"); "
             "chỉ trả chữ số."},
    {"name": "Don_DiaChi",
     "desc": "Mục I \"Địa chỉ\" của người sử dụng đất trên Đơn, object {quocGia,tinh,xa,chiTietDuoiXa}. Dòng viết "
             "liền \"<tổ/thôn/bản>, <xã/phường>, <tỉnh>\": cụm cuối = tinh, cụm trước = xa (thêm \"Xã\"/\"Phường\" "
             "nếu đơn viết trống), phần còn lại = chiTietDuoiXa giữ nguyên chữ (kể cả \"TDP:\"). KHÔNG lấy địa chỉ "
             "thửa đất."},
    {"name": "Don_MaSoThue",
     "desc": "Mục I \"Mã số thuế (nếu có)\" trên Đơn; bỏ dấu chấm/khoảng trắng, giữ chữ số. Đơn bỏ trống → bỏ field."},
    {"name": "Don_DienThoai",
     "desc": "Mục I \"Điện thoại liên hệ (nếu có)\" trên Đơn; bỏ dấu chấm/khoảng trắng, giữ chữ số."},
    {"name": "Don_Email", "desc": "Mục I \"Hộp thư điện tử (nếu có)\" trên Đơn. Thường để trống → bỏ field."},
    {"name": "ToChuc_Ten",
     "desc": "Tên CƠ QUAN/TỔ CHỨC ở mục I \"Tên\" của Đơn, CHỈ khi người sử dụng đất là tổ chức. Cá nhân, hộ gia "
             "đình → BỎ FIELD; không lấy họ tên người dân."},

    # Giấy ủy quyền (hay scan chung file với Đơn) — chỉ phần BÊN ỦY QUYỀN ("Tôi: ...").
    {"name": "UyQuyen_HoTen",
     "desc": "Họ tên BÊN ỦY QUYỀN (dòng \"Tôi: ...\" đầu Giấy ủy quyền). KHÔNG lấy người được ủy quyền (sau câu "
             "\"Bằng giấy này tôi ủy quyền cho\") hay công chứng viên."},
    {"name": "UyQuyen_NgaySinh", "desc": "\"Sinh ngày\" của BÊN ỦY QUYỀN, dd/mm/yyyy."},
    {"name": "UyQuyen_SoCccd", "desc": "Số căn cước công dân của BÊN ỦY QUYỀN; chỉ trả chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp căn cước của BÊN ỦY QUYỀN (\"cấp ngày ...\"), dd/mm/yyyy."},
    {"name": "UyQuyen_NoiCap", "desc": "Nơi cấp căn cước của BÊN ỦY QUYỀN (\"tại ...\"), chép nguyên chữ."},
    {"name": "UyQuyen_ThuongTru",
     "desc": "\"Địa chỉ thường trú tại\" của BÊN ỦY QUYỀN, CHUỖI chép nguyên văn (kể cả tên huyện/thị xã cũ)."},

    # Giấy chứng nhận đã cấp (bản gốc).
    {"name": "Gcn_HoTen", "desc": "Họ tên người sử dụng đất ở mục I của Giấy chứng nhận, bỏ danh xưng Ông/Bà."},
    {"name": "Gcn_SoCccdMoi",
     "desc": "Số CCCD MỚI ở trang \"Những thay đổi sau khi cấp giấy chứng nhận\" (câu \"thay đổi giấy CMND từ số "
             "... thành CCCD số ...\"): lấy số SAU chữ \"thành\". KHÔNG lấy \"Số CMND\" cũ ở mục I."},
    {"name": "Gcn_NgayCapCccd", "desc": "Ngày cấp CCCD mới ghi ở trang thay đổi của GCN, dd/mm/yyyy."},
    {"name": "Gcn_NoiCapCccd", "desc": "Nơi cấp CCCD mới ghi ở trang thay đổi của GCN, chép nguyên chữ."},
    {"name": "Gcn_ThuongTruMoi",
     "desc": "Địa chỉ thường trú MỚI ở trang thay đổi của GCN (câu \"Đổi địa chỉ thường trú từ ... thành ...\": lấy "
             "phần SAU chữ \"thành\"), CHUỖI nguyên văn. Không lấy địa chỉ thường trú cũ ở mục I."},

    # Giới tính suy từ danh xưng khi hồ sơ không có thẻ.
    {"name": "NguoiSdd_GioiTinh",
     "desc": "Giới tính người sử dụng đất suy từ danh xưng đứng trước tên họ: \"Bà\" → \"Nữ\", \"Ông\" → \"Nam\" "
             "(mục I Giấy chứng nhận, mục 3 Phiếu đo đạc/Mảnh trích đo, Lời chứng của công chứng viên). Không có "
             "danh xưng → bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "UyQuyen_NgaySinh", "UyQuyen_NgayCap", "Gcn_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Don_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô bước 2 theo file mapping (field-key Nth FormBuilder): <select> -> dom-select, <input> -> dom-input.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",            # Họ và tên (*) — cổng tự chuyển IN HOA.
    "CongDan_tenCoQuanToChuc": "dom-input",       # Tên cơ quan/tổ chức — chỉ khi người SDĐ là tổ chức.
    "CongDan_maSoThueNguoiNop": "dom-input",      # MSDN/MST — mục "Mã số thuế" của Đơn, nhập liền.
    "CongDan_ngaySinhCongDan": "dom-input",       # Ngày Sinh (*) dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",      # Giới tính (*) — mặc định "Nữ" nên luôn phải chọn lại.
    "CongDan_danTocCongDan": "dom-select",        # Dân tộc (*) — selectpicker; hồ sơ thường không có nguồn.
    "CongDan_soCmnd": "dom-input",                # Số CMND/CCCD (*)
    "CongDan_ngayCapCmnd": "dom-input",           # Ngày cấp CMND/CCCD
    "CongDan_noiCapCmnd": "dom-input",            # Nơi cấp CMND/CCCD
    # Địa chỉ 2 cấp tỉnh → xã: phát maTinhThanh TRƯỚC (danh mục xã nạp theo tỉnh).
    "CongDan_maTinhThanh": "dom-select",          # Tỉnh/Thành phố (*)
    "CongDan_maPhuongXa": "dom-select",           # Phường/Xã/Thị trấn (*)
    "CongDan_diaChi": "dom-input",                # Số nhà/Đường/Tổ/Ấp/Thôn/Xóm (*)
    "CongDan_diDong": "dom-input",                # Di động — nhập liền.
    "CongDan_maTinhCapCMND": "dom-select",        # Nơi cấp CMND (CA Tỉnh) — chỉ CMND do công an tỉnh cấp.
    "CongDan_maDMQuocGia": "dom-select",          # Quốc gia
    "CongDan_email": "dom-input",                 # Email
    "CongDan_soCCCD": "dom-input",                # Số CCCD (trùng Số CMND/CCCD)
    "CongDan_noiOHienTai": "dom-input",           # Nơi ở hiện tại (chuỗi đầy đủ)
    "CongDan_diaChiThuongTru": "dom-input",       # Địa chỉ thường trú (chuỗi đầy đủ)
}

UI_ALIASES = {"CongDan_soCCCD": ["soCCCD"]}
