"""Compact schema cho thủ tục 1.115668 — Lào Cai.

"Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp chuyển đổi
quyền sử dụng đất nông nghiệp…; chuyển nhượng, thừa kế, tặng cho…; góp vốn…; cho thuê, cho thuê lại…;
chuyển nhượng quyền khai thác khoáng sản".

Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — CÙNG form bước 2 với 1.115667 (fieldset
CongDan_* người nộp + ChuHoSo_* chủ hồ sơ). Mapping theo "mapping-1.115668-dang-ky-bien-dong-dat-dai-LaoCai.xlsx".

LLM chỉ trích dữ kiện nguồn; Python chọn nguồn theo ma trận ưu tiên và sinh field UI.
"""

_AREA_DESC = "object {quocGia,tinh,xa,diaChi}; địa chỉ 2 cấp (xã/phường → tỉnh), diaChi là số nhà/đường/tổ/thôn."
_PERSON_DESC = (
    "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap}]; SoDinhDanh liền chữ số; NgaySinh/NgayCap dd/mm/yyyy "
    "(chỉ có năm thì trả đúng năm); GioiTinh suy từ xưng hô Ông→Nam, Bà→Nữ."
)

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ được "
            "nhắc trong hợp đồng): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong hợp đồng/giấy ủy quyền/đơn (bên nhận, bên chuyển, người đại "
            "diện, bên ủy quyền, bên được ủy quyền), mỗi người một object: " + _PERSON_DESC
        ),
    },
    # ---- Chủ hồ sơ = người đứng tên Đơn đăng ký biến động (bên NHẬN quyền sử dụng đất). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Chủ hồ sơ (người đứng tên Đơn mục 1.a, bên nhận chuyển quyền) là 'Cá nhân' hay 'Tổ chức'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: tên tổ chức ở Đơn mục 1.a / bên nhận (bên mua) trên hợp đồng / tên "
             "công ty trên GCN đăng ký doanh nghiệp CỦA CHÍNH tổ chức đó. Không lấy tên bên chuyển nhượng/bên bán."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức đó (10 hoặc 13 số, "
             "liền chữ số). Không lấy MST bên bán/bên chuyển nhượng."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng tên đầu trên Đơn mục 1.a hoặc bên nhận trên hợp "
             "đồng/văn bản thừa kế, tặng cho. Hai vợ chồng cùng nhận → người đứng tên đầu tiên."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân trên giấy tờ. Chỉ có 'Sinh năm 1970' thì trả '1970', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân trên Đơn (1.b) hoặc hợp đồng; liền chữ số. Không lấy số của "
             "vợ/chồng đứng tên thứ hai."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ cá nhân ghi trên hợp đồng/đơn, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD chủ hồ sơ cá nhân ghi trên hợp đồng/đơn. 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát "
             "quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiHopDong",
     "desc": "Địa chỉ của BÊN NHẬN trên hợp đồng/văn bản chuyển quyền (nơi thường trú, hoặc trụ sở chính nếu là "
             "tổ chức), " + _AREA_DESC + " KHÔNG lấy địa chỉ bên bán/bên chuyển, KHÔNG lấy địa chỉ thửa đất."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ tại mục 1.c) của ĐƠN ĐĂNG KÝ BIẾN ĐỘNG, " + _AREA_DESC + " KHÔNG lấy địa chỉ thửa đất."},
    {"name": "ChuHoSo_DiaChiDkdn",
     "desc": "Địa chỉ trụ sở chính trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ (không phải của bên bán), "
             + _AREA_DESC},
    {"name": "Don_DienThoai", "desc": "Số điện thoại mục 1.d) trên Đơn đăng ký biến động; liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử mục 1.d) trên Đơn nếu có ghi; bỏ trống/chấm chấm thì bỏ field."},
    {"name": "HopDong_DienThoai", "desc": "Số điện thoại của BÊN NHẬN (bên mua) ghi trên hợp đồng; liền chữ số."},
    {"name": "Dkdn_DienThoai",
     "desc": "Điện thoại trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ (không lấy của bên bán)."},
    {"name": "Dkdn_Email",
     "desc": "Thư điện tử trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ (không lấy của bên bán)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiHopDong", "ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiDkdn"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần II — người nộp. Họ tên/Số căn cước/địa chỉ do tài khoản định danh điền sẵn → KHÔNG phát lại (sửa
    # "Họ và tên" là cổng xoá trắng Di động + CCCD). Nhân thân còn lại chỉ lấy từ giấy tờ CỦA CHÍNH người nộp.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # mặc định cổng "0" = Nữ → sửa theo thẻ
    "CongDan_danTocCongDan": "dom-select",       # JS cổng không tự đổ dân tộc
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    # Phần III — chủ hồ sơ. Đối tượng là DRIVER: đổi CN/DN mới hiện nhóm ô tương ứng → phát TRƯỚC.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",     # "" / CN / DN / CQ / TC
    "ChuHoSo_tenChuHoSo": "dom-input",           # (*) khi CN
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",        # (*) khi CN
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",   # (*) khi DN/CQ/TC
    "ChuHoSo_maSoThueChuHoSo": "dom-input",      # (*) khi DN/CQ/TC
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",      # mặc định Lào Cai → phải đổi theo địa chỉ thật
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
