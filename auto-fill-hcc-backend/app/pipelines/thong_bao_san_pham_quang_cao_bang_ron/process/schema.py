"""Compact schema cho "Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn"
(mã 1.004650) — cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn`, nền tảng liz, form và bảng thành phần hồ sơ
CHUNG một trang `/nop-ho-so`. LLM chỉ trả FACT nguồn; mapper phát ô UI theo (section = `.group-header`,
name = `<mat-label>`) cho engine `fill-liz.js`.

Khối "Thông tin người nộp hồ sơ" KHÔNG điền: cổng đã đổ sẵn từ tài khoản định danh.
Khối "Thông tin người ủy quyền" = DOANH NGHIỆP thông báo quảng cáo (cá nhân đại diện đi nộp thay cho
doanh nghiệp); phải TÍCH ô "Thông tin người ủy quyền" thì cổng mới ghi nhận khối này.
"""

_GCN = "Giấy chứng nhận đăng ký doanh nghiệp/kinh doanh"
_TB = "Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (Mẫu số 01)"

FIELDS: list[dict] = [
    # ---- DOANH NGHIỆP thông báo quảng cáo (bên ủy quyền) ----
    {"name": "DoanhNghiep_Ten", "desc": f"Tên doanh nghiệp: 'Tên công ty viết bằng tiếng Việt' trên {_GCN}; "
        f"không có GCN thì lấy '1. Tên tổ chức' trên {_TB}. Chép nguyên văn."},
    {"name": "DoanhNghiep_MaSo", "desc": f"Mã số doanh nghiệp trên {_GCN} (hoặc 'Giấy chứng nhận đăng ký kinh "
        f"doanh số' trên {_TB}). Chép đúng chữ số đọc được, KHÔNG bù số bị che/thiếu."},
    {"name": "DoanhNghiep_NgayCap", "desc": f"Ngày 'Đăng ký lần đầu' trên {_GCN}, dd/mm/yyyy. Chỉ có tháng/năm "
        "hoặc năm thì bỏ field."},
    {"name": "DoanhNghiep_NoiCap", "desc": f"Cơ quan cấp {_GCN} — tiêu đề góc trái trên giấy thường in HAI dòng "
        "(cơ quan cấp trên, rồi phòng): GHÉP cả hai thành 'Phòng Đăng ký kinh doanh - Sở … tỉnh …', không bỏ "
        f"dòng nào. Không có GCN thì lấy cụm 'do … cấp' trên {_TB}."},
    {"name": "DoanhNghiep_DienThoai", "desc": f"Điện thoại trụ sở chính trên {_GCN} (hoặc dòng 'Điện thoại' của "
        f"mục 1 trên {_TB}). Chỉ chữ số; KHÔNG lấy số điện thoại của người chịu trách nhiệm."},
    {"name": "DoanhNghiep_Email", "desc": f"Thư điện tử trụ sở chính trên {_GCN}, nếu có."},
    {"name": "DoanhNghiep_TruSo", "desc": f"Địa chỉ trụ sở chính trên {_GCN} (hoặc 'Địa chỉ' mục 1 trên {_TB}), "
        "object {tinh,xa,diaChi}: tinh='Tỉnh/Thành phố …', xa='Xã/Phường …', diaChi=số nhà/thôn/đường "
        "(KHÔNG kèm xã/tỉnh). KHÔNG lấy địa chỉ thường trú của người chịu trách nhiệm."},

    # ---- Nội dung tờ khai Mẫu 01 ----
    {"name": "ThongBao_NoiDung", "desc": f"Mục '2. Nội dung trên bảng quảng cáo, băng rôn' trên {_TB}, chép "
        "nguyên văn (kể cả tên/địa chỉ địa điểm kinh doanh ghi kèm ngay dưới)."},
    {"name": "ThongBao_DiaDiem", "desc": f"Mục '3. Địa điểm thực hiện' trên {_TB}, chép nguyên văn."},
    {"name": "ThongBao_TuNgay", "desc": f"Ngày BẮT ĐẦU ở mục '4. Thời gian thực hiện: Từ ngày …' trên {_TB}, "
        "dd/mm/yyyy. Tờ khai để trống ngày/tháng thì BỎ field — KHÔNG lấy thời gian khuyến mại hay ngày "
        "ghi trên ma-két."},
    {"name": "ThongBao_DenNgay", "desc": f"Ngày KẾT THÚC ở mục '4. Thời gian thực hiện: … đến ngày …' trên "
        f"{_TB}, dd/mm/yyyy. Để trống thì BỎ field (cùng quy tắc với ThongBao_TuNgay)."},
    {"name": "ThongBao_SoLuong", "desc": f"Mục '5. Số lượng' trên {_TB}, chép ĐỦ mọi dòng (loại băng-rôn, địa "
        "bàn, số tấm, kích thước), các dòng ngăn cách bằng xuống dòng."},
    {"name": "ThongBao_PhuongAnThaoDo", "desc": f"Mục '6. Phương án tháo dỡ' trên {_TB}, chép nguyên văn."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DoanhNghiep_NgayCap", "ThongBao_TuNgay", "ThongBao_DenNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["DoanhNghiep_TruSo"] = "x-select-area"

# group-header thật trong DOM.
S_UQ = "Thông tin người ủy quyền"
S_TB = "THÔNG BÁO SẢN PHẨM QUẢNG CÁO TRÊN BẢNG QUẢNG CÁO, BĂNG - RÔN"

# Nhãn ô tích bật khối ủy quyền (liz-checkbox, trùng chữ với group-header của khối).
UY_QUYEN_CHECKBOX = "Thông tin người ủy quyền"

# (section, <mat-label>, comp) chép đúng DOM. Bỏ "Ngày sinh" của khối ủy quyền: bên ủy quyền là tổ chức.
UI_FIELDS: list[tuple[str, str, str]] = [
    (S_UQ, "Tên người / Tên đơn vị ủy quyền", "liz-input"),
    (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", "liz-input"),
    (S_UQ, "Ngày cấp", "liz-date"),
    (S_UQ, "Nơi cấp", "liz-input"),
    (S_UQ, "Số điện thoại", "liz-input"),
    (S_UQ, "Email", "liz-input"),
    (S_UQ, "Địa chỉ hành chính", "liz-select"),
    (S_UQ, "Địa chỉ chi tiết", "liz-input"),

    (S_TB, "Số GPKD", "liz-input"),
    (S_TB, "Nơi cấp GPKD", "liz-input"),
    (S_TB, "Nội dung trên bảng quảng cáo, băng-rôn", "liz-input"),
    (S_TB, "Địa điểm thực hiện", "liz-input"),
    (S_TB, "Từ ngày thực hiện", "liz-date"),
    (S_TB, "Đến ngày thực hiện", "liz-date"),
    (S_TB, "Số lượng", "liz-input"),
    (S_TB, "Phương án tháo dỡ (nếu có)", "liz-input"),
]

COMP_BY_UI = {(s, l): c for s, l, c in UI_FIELDS}
