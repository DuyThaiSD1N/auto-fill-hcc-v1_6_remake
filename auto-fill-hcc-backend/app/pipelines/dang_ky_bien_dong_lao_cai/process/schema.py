"""Compact schema cho thủ tục 1.115671 — Lào Cai.

"Đăng ký biến động đối với trường hợp thay đổi quyền sử dụng đất… theo thỏa thuận của các thành viên hộ gia
đình hoặc của vợ và chồng; quyền sử dụng đất xây dựng công trình trên mặt đất phục vụ công trình ngầm; bán tài
sản, điều chuyển, chuyển nhượng quyền sử dụng đất là tài sản công; nhận quyền sử dụng đất theo kết quả giải
quyết tranh chấp, khiếu nại, tố cáo, bản án/quyết định của Tòa án, phán quyết của Trọng tài thương mại; nhận
quyền sử dụng đất do xử lý tài sản thế chấp".

Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — bước 2 dùng CÙNG bộ ô CongDan_* (người nộp) +
ChuHoSo_* (chủ hồ sơ) với 1.115667/1.115668/1.115651/1.115694, mapping theo
"mapping_dang-ky-bien-dong_1.115671_LaoCai_MTTQ.xlsx" (sheet "Mapping B2 - Người nộp").

Khác các thủ tục anh em ở ĐỐI TƯỢNG NỘP HỒ SƠ: cổng có 4 lựa chọn (CN/DN/CQ/TC) và hồ sơ điển hình của thủ tục
này là TỔ CHỨC CHÍNH TRỊ - XÃ HỘI / CƠ QUAN NHÀ NƯỚC (điều chuyển trụ sở là tài sản công) chứ không phải doanh
nghiệp — chọn nhầm "Doanh nghiệp" là cổng đòi mã số thuế mà hồ sơ dạng này không có.

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
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ "
            "được nhắc trong đơn/biên bản): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,"
            "NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD/CMND trong Đơn đăng ký biến động, giấy ủy quyền, biên bản bàn "
            "giao, hợp đồng, bản án (người đại diện, người làm đơn, bên nhận, bên chuyển, bên ủy quyền, bên "
            "được ủy quyền), mỗi người một object: " + _PERSON_DESC
            + " Đơn mục 1.d thường ghi liền một dòng kiểu 'CCCD số 010087000653 cấp ngày 13/4/2021 tại Cục "
              "trưởng cục cảnh sát quản lý hành chính về trật tự xã hội' → tách ra SoDinhDanh/NgayCap/NoiCap."
        ),
    },
    # ---- Chủ hồ sơ = người/tổ chức đứng tên mục 1.a của Đơn = bên ĐỨNG TÊN SAU BIẾN ĐỘNG. ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Chủ hồ sơ (mục 1.a của Đơn đăng ký biến động — bên nhận quyền/đứng tên sau biến động) thuộc loại "
             "nào, trả ĐÚNG một trong bốn chuỗi: 'Cá nhân' | 'Doanh nghiệp' | 'Cơ quan nhà nước' | 'Tổ chức "
             "khác'. Công ty, doanh nghiệp, hợp tác xã, ngân hàng → 'Doanh nghiệp'. Ủy ban nhân dân, sở, ban, "
             "ngành, đơn vị sự nghiệp công lập → 'Cơ quan nhà nước'. Mặt trận Tổ quốc, hội, đoàn thể, tổ chức "
             "chính trị - xã hội, tổ chức tôn giáo, cộng đồng dân cư → 'Tổ chức khác'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức/cơ quan: tên đầy đủ ở Đơn mục 1.a, hoặc bên TIẾP NHẬN trên biên bản "
             "bàn giao tài sản công, hoặc bên nhận trên hợp đồng, hoặc 'Tên công ty viết bằng tiếng Việt' trên "
             "GCN đăng ký doanh nghiệp CỦA CHÍNH tổ chức đó. KHÔNG lấy tên bên bàn giao/bên chuyển nhượng, tên "
             "cơ quan ra quyết định, tên Tòa án, tên tổ chức tín dụng."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức đó (10 hoặc 13 số, "
             "liền chữ số). Không có thì bỏ field, KHÔNG lấy mã số của bên kia."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng tên đầu ở Đơn mục 1.a hoặc bên nhận quyền trên "
             "văn bản thỏa thuận/hợp đồng/bản án. Hai vợ chồng cùng đứng tên → người đứng tên đầu tiên. Người "
             "đại diện ký thay cho tổ chức KHÔNG phải chủ hồ sơ."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân trên giấy tờ. Chỉ có 'Sinh năm 1970' thì trả '1970', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân ghi ở Đơn mục 1.d hoặc trên văn bản thỏa thuận/hợp đồng; liền "
             "chữ số. Không lấy số của vợ/chồng đứng tên thứ hai, không lấy số của người đại diện đi nộp."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ cá nhân ghi trên Đơn/hợp đồng, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD chủ hồ sơ cá nhân ghi trên Đơn/hợp đồng. 'Cục trưởng cục cảnh sát quản lý hành "
             "chính về trật tự xã hội' là CHỨC DANH người ký, tên cơ quan cần trả là 'Cục Cảnh sát quản lý "
             "hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ của chủ hồ sơ ghi ở mục 1.e) của ĐƠN ĐĂNG KÝ BIẾN ĐỘNG — với hồ sơ đổi tên/đổi địa chỉ "
             "thì đây là địa chỉ MỚI SAU biến động, " + _AREA_DESC
             + " KHÔNG lấy địa chỉ thửa đất, KHÔNG lấy địa chỉ cũ ghi trên Giấy chứng nhận."},
    {"name": "ChuHoSo_DiaChiCanCu",
     "desc": "Địa chỉ/trụ sở của chủ hồ sơ ghi trên văn bản căn cứ (biên bản bàn giao tài sản công, văn bản "
             "thỏa thuận, hợp đồng, bản án, quyết định), " + _AREA_DESC
             + " KHÔNG lấy địa chỉ bên bàn giao/bên chuyển, KHÔNG lấy địa chỉ thửa đất."},
    {"name": "ChuHoSo_DiaChiDkdn",
     "desc": "Địa chỉ trụ sở chính trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ, " + _AREA_DESC},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn đăng ký biến động; liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn nếu có; bỏ trống/chấm chấm thì bỏ field."},
    {"name": "CanCu_DienThoai",
     "desc": "Số điện thoại của chủ hồ sơ ghi trên văn bản căn cứ (biên bản bàn giao, hợp đồng); liền chữ số."},
    {"name": "Dkdn_DienThoai", "desc": "Điện thoại trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ."},
    {"name": "Dkdn_Email", "desc": "Thư điện tử trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiCanCu", "ChuHoSo_DiaChiDkdn"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp. Họ tên/Số căn cước do tài khoản định danh điền sẵn (readonly) → KHÔNG phát lại (sửa
    # "Họ và tên" là cổng xoá trắng Di động + CCCD). Nhân thân còn lại chỉ lấy từ giấy tờ CỦA CHÍNH người nộp.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # mặc định cổng "0" = Nữ → phải sửa theo thẻ
    "CongDan_danTocCongDan": "dom-select",       # JS cổng không tự đổ dân tộc
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    # Phần II — chủ hồ sơ. Đối tượng là DRIVER: đổi CN/DN/CQ/TC mới hiện nhóm ô tương ứng → phát TRƯỚC.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",     # "" / CN / DN / CQ / TC
    "ChuHoSo_tenChuHoSo": "dom-input",           # chỉ hiện khi CN
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",   # chỉ hiện khi DN/CQ/TC
    "ChuHoSo_maSoThueChuHoSo": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",      # mặc định Lào Cai → phải đổi theo địa chỉ thật
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
