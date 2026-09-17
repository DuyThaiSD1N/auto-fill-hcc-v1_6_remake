"""Compact schema cho thủ tục 1.115651 — Lào Cai.

"Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời hạn sử dụng đất;
điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp quy định tại khoản 1 Điều 175 Luật Đất đai".

Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — CÙNG form bước 2 với 1.115667/1.115668
(fieldset CongDan_* người nộp + ChuHoSo_* chủ hồ sơ). Mapping theo
"mapping-1.115651-chuyen-muc-dich-su-dung-dat-LaoCai.xlsx". Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên Đơn (thủ tục
khai maDoiTuongNop = TO_CHUC nhưng cá nhân vẫn nộp được).

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
            "nhắc trong đơn/giấy ủy quyền): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. "
            "NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD trong đơn/giấy ủy quyền/GCN đăng ký doanh nghiệp (người làm đơn, "
            "người đại diện theo pháp luật, bên ủy quyền, bên được ủy quyền), mỗi người một object: " + _PERSON_DESC
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên Đơn (Mẫu 02/03/17/18). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Người sử dụng đất đứng tên Đơn là 'Cá nhân' hay 'Tổ chức' (công ty, doanh nghiệp, đơn vị)."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi người sử dụng đất là tổ chức: tên tổ chức, ưu tiên 'Tên công ty viết bằng tiếng Việt' trên GCN "
             "đăng ký doanh nghiệp, rồi tên trên Đơn, rồi tên chủ sử dụng đất trên bản đồ/GCN quyền sử dụng đất. "
             "Không lấy tên các thửa giáp ranh, đơn vị đo đạc, cơ quan ký duyệt."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi người sử dụng đất là tổ chức: mã số doanh nghiệp/mã số thuế (10 hoặc 13 số, liền chữ số)."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi người sử dụng đất là cá nhân: họ tên người sử dụng đất đứng tên Đơn/GCN. Người đại diện theo "
             "pháp luật của công ty KHÔNG phải chủ hồ sơ cá nhân."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân. Chỉ có 'Sinh năm 1970' thì trả '1970', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân trên Đơn/GCN; liền chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ cá nhân ghi trên Đơn, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD chủ hồ sơ cá nhân ghi trên Đơn. 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát quản lý hành "
             "chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDkdn",
     "desc": "Địa chỉ TRỤ SỞ CHÍNH trên GCN đăng ký doanh nghiệp của người sử dụng đất, " + _AREA_DESC},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ của người sử dụng đất (nơi cư trú/trụ sở) ghi trên ĐƠN, " + _AREA_DESC
             + " KHÔNG lấy vị trí khu đất xin chuyển mục đích."},
    {"name": "ThuaDat_DiaChi",
     "desc": "Vị trí KHU ĐẤT/thửa đất ghi trên Đơn, bản đồ/mảnh đo đạc hoặc GCN quyền sử dụng đất, " + _AREA_DESC
             + " Địa danh cũ trước sáp nhập (vd 'T. YÊN BÁI - HUYỆN YÊN BÌNH / XÃ PHÚ THỊNH', 'THÔN 3, KHU CÔNG NGHIỆP "
             "PHÍA NAM') → tinh='Yên Bái', huyen='Yên Bình', xa='Phú Thịnh', diaChi='Thôn 3, Khu công nghiệp phía Nam'."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn; liền chữ số."},
    {"name": "Don_Email", "desc": "Thư điện tử ghi trên Đơn nếu có; bỏ trống/chấm chấm thì bỏ field."},
    {"name": "Dkdn_DienThoai", "desc": "Điện thoại trụ sở trên GCN đăng ký doanh nghiệp của người sử dụng đất."},
    {"name": "Dkdn_Email", "desc": "Thư điện tử trên GCN đăng ký doanh nghiệp của người sử dụng đất."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDkdn", "ChuHoSo_DiaChiDon", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp. Họ tên/Số căn cước/địa chỉ do tài khoản định danh điền sẵn → KHÔNG phát lại (sửa
    # "Họ và tên" là cổng xoá trắng Di động + CCCD). Nhân thân còn lại chỉ lấy từ giấy tờ CỦA CHÍNH người nộp.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # mặc định cổng "0" = Nữ → sửa theo thẻ
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    # Phần II — chủ hồ sơ. Đối tượng là DRIVER: đổi CN/DN mới hiện nhóm ô tương ứng → phát TRƯỚC.
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
    "ChuHoSo_maTinhThanhCHS": "dom-select",      # mặc định Lào Cai
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
