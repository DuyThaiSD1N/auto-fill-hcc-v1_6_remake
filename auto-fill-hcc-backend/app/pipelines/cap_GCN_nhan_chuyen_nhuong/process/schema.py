"""Compact schema cho thủ tục 1.115667 — Lào Cai.

"Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho người nhận
chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất động sản".

Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI). Mapping theo file
"mapping-1.115667-cap-GCN-nhan-chuyen-nhuong-du-an-BDS.xlsx" (sheet 1 = trường, sheet 2 = nguồn ưu tiên).
CHỈ có DOM của BƯỚC 2 "Thông tin người nộp" (2 fieldset CongDan_* và ChuHoSo_*); bước 3 (eForm Mẫu số 24,
thửa đất, tài sản) và bước 4–5 chưa có DOM nên chưa map.

LLM chỉ trích dữ kiện nguồn; Python chọn nguồn theo cột "Nguồn ưu tiên" và sinh field UI.
"""

_AREA_DESC = "object {quocGia,tinh,xa,diaChi}; địa chỉ 2 cấp (xã/phường → tỉnh), diaChi là số nhà/tổ/thôn."

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI CCCD/CMND/thẻ Căn cước đã upload, không bỏ thẻ nào: "
            "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. Mỗi object chỉ chứa "
            "dữ liệu của ĐÚNG một thẻ. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, "
            + _AREA_DESC
        ),
    },
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "CHỈ điền khi hồ sơ có văn bản riêng tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY QUYỀN'/'VĂN BẢN "
            "VỀ VIỆC ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số định danh của bên B. Chép người đứng NGAY "
            "SAU 'ủy quyền cho' vào object: {\"hoTen\", \"ngaySinh\" (dd/mm/yyyy), \"gioiTinh\" "
            "('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", \"ngayCapCccd\" (dd/mm/yyyy), \"noiCapCccd\", "
            "\"dienThoai\", \"thuongTru\": " + _AREA_DESC + "}. Không có văn bản ủy quyền thì BỎ TRỐNG "
            "— người đại diện theo pháp luật của chủ đầu tư KHÔNG phải người được ủy quyền."
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "MỌI cá nhân được ghi KÈM SỐ ĐỊNH DANH/CCCD/CMND trong bất kỳ giấy tờ nào của hồ sơ (người "
            "ký đơn, bên nhận chuyển nhượng và vợ/chồng cùng đứng tên, người được ủy quyền), mỗi người "
            "một object: [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,DienThoai,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm). NoiCuTru " + _AREA_DESC
            + " Người nào thiếu mục nào thì bỏ mục đó, KHÔNG bịa. Đây chỉ là DANH SÁCH ỨNG VIÊN — không "
            "tự quyết ai là người đi nộp."
        ),
    },
    # ---- Chủ hồ sơ = BÊN NHẬN chuyển nhượng (bên B), người đứng tên Đơn đăng ký biến động. ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Bên nhận chuyển nhượng là 'Cá nhân' hay 'Tổ chức'. Chỉ trả 'Tổ chức' khi bên NHẬN là công ty/"
             "tổ chức; bên CHUYỂN NHƯỢNG là công ty thì KHÔNG liên quan."},
    {"name": "ChuHoSo_HoTen",
     "desc": "Họ tên người nhận chuyển nhượng đứng tên đầu trên Đơn đăng ký biến động (mục 1.a Tên) hoặc "
             "HĐ chuyển nhượng mục BÊN NHẬN CHUYỂN NHƯỢNG (bên B). Hai vợ chồng cùng nhận → lấy người "
             "đứng tên đầu tiên trên Đơn."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh của chủ hồ sơ ghi trên giấy tờ đất đai. Giấy chỉ ghi 'Sinh năm 1957' thì trả đúng "
             "'1957' — TUYỆT ĐỐI không tự thêm ngày/tháng."},
    {"name": "ChuHoSo_XungHo",
     "desc": "Cách xưng hô trước tên chủ hồ sơ trên HĐ chuyển nhượng/Đơn/Biên bản: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ ghi trên Đơn (1.b Giấy tờ nhân thân) hoặc HĐ chuyển nhượng bên B. "
             "Trả liền chữ số, bỏ dấu chấm/khoảng trắng. KHÔNG lấy số của vợ/chồng đứng tên thứ hai."},
    {"name": "ChuHoSo_NgayCap",
     "desc": "Ngày cấp CCCD của chủ hồ sơ ghi trên HĐ chuyển nhượng (bên B) hoặc Biên bản, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD của chủ hồ sơ ghi trên HĐ chuyển nhượng (bên B) hoặc Biên bản. 'Cục CSQLHC về "
             "TTXH' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ chủ hồ sơ tại mục 1.c) Địa chỉ của ĐƠN ĐĂNG KÝ BIẾN ĐỘNG, " + _AREA_DESC
             + " KHÔNG lấy địa chỉ thửa đất ở mục 2/3 của đơn."},
    {"name": "ChuHoSo_DiaChiHopDong",
     "desc": "Nơi thường trú của BÊN NHẬN chuyển nhượng (bên B) trên HĐ chuyển nhượng, " + _AREA_DESC
             + " KHÔNG lấy trụ sở công ty bên chuyển nhượng."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi bên NHẬN chuyển nhượng là tổ chức: tên tổ chức nhận chuyển nhượng. Bên nhận là cá nhân "
             "thì BỎ FIELD. TUYỆT ĐỐI không lấy tên công ty bên chuyển nhượng/chủ đầu tư."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi bên NHẬN là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức nhận chuyển "
             "nhượng. Không lấy MST của bên chuyển nhượng."},
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại tại mục 1.d) Điện thoại liên hệ trên Đơn đăng ký biến động; trả liền chữ số."},
    {"name": "Don_Email",
     "desc": "Hộp thư điện tử tại mục 1.d) trên Đơn nếu có ghi; trống thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap",):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiHopDong"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key> do Nth.FormBuilder dựng từ XML). <select> native → dom-select,
# còn lại (kể cả ô ngày bootstrap-datetimepicker DD/MM/YYYY) → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp. Ở chế độ THEO TÀI KHOẢN (mặc định) mapper KHÔNG phát lại Họ tên/Số căn cước/
    # địa chỉ/Di động: cổng đã điền sẵn đúng người từ tài khoản định danh, mà sửa "Họ và tên" thì cổng
    # xoá trắng Di động + CCCD. Chế độ THEO TỜ KHAI phát cả khối vì người nộp là người KHÁC — để nửa
    # khối của tài khoản nửa của người trong hồ sơ là sai người khi cổng xác thực với CSDLQG dân cư.
    "CongDan_tenCongDan": "dom-input",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # mặc định cổng "0" = Nữ → phải sửa theo thẻ
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_maTinhThanh": "dom-select",
    "CongDan_maPhuongXa": "dom-select",          # nạp AJAX sau khi chọn tỉnh
    "CongDan_diaChi": "dom-input",
    # Phần II — chủ hồ sơ. Đối tượng là DRIVER: đổi nhánh CN/DN mới hiện nhóm ô tương ứng → phát TRƯỚC.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",     # "" / CN / DN / CQ / TC
    "ChuHoSo_tenChuHoSo": "dom-input",           # (*) khi CN
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",     # 0 = Nữ, 1 = Nam
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",        # (*) khi CN
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",   # (*) khi DN/CQ/TC
    "ChuHoSo_maSoThueChuHoSo": "dom-input",      # (*) khi DN/CQ/TC
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
