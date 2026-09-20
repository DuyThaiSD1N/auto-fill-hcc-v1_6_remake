"""Compact schema cho thủ tục 1.115687 — Lào Cai.

"Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do người sử dụng đất, chủ sở
hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi".

Cổng dichvucong.laocai.gov.vn (iGate VNPT) — bước 2 "Thông tin người nộp" dùng CÙNG bộ ô CongDan_* (người nộp) +
ChuHoSo_* (chủ hồ sơ) với 1.115651/1.115667/1.115668/1.115671, mapping theo
"mapping_thu_hoi_huy_GCN_laocai.xlsx" (sheet "HS1 - Trần Thị Tâm", "HS2 - Đinh Thị Thoa", "Tổ chức").

KHÁC các thủ tục anh em ở KHỐI NGƯỜI NỘP: mapping của thủ tục này ghi rõ Tỉnh/Thành phố, Phường/Xã và
Số nhà/Đường/Tổ/Thôn của người nộp là ô TRỐNG và BẮT BUỘC (*) — cổng không đổ sẵn từ tài khoản định danh, chỉ
Họ và tên + Số Căn cước mới readonly. Vì vậy ở đây có thêm ba ô địa chỉ của khối người nộp
(CongDan_maTinhThanh/maPhuongXa/diaChi), lấy từ giấy tờ CỦA CHÍNH người đang đăng nhập.

KHÔNG phát ô "Người nộp là chủ hồ sơ" (chkbox_nguoinoplachuhs): tích ô đó gọi nguoiNopLaChuHoSo() để cổng CHÉP
khối người nộp sang khối chủ hồ sơ. Hồ sơ mẫu 1 là nộp thay (ông Hợi nộp cho bà Tâm) nên chép là sai người; còn
hồ sơ tự nộp thì ta đã điền thẳng ChuHoSo_* từ giấy tờ, chép thêm chỉ tạo rủi ro cổng ghi đè sau lượt điền.

LLM chỉ trích dữ kiện nguồn; Python chọn nguồn theo ma trận ưu tiên và sinh field UI.
"""

_AREA_DESC = "object {quocGia,tinh,xa,diaChi}; địa chỉ 2 cấp (xã/phường → tỉnh), diaChi là số nhà/đường/tổ/thôn."
_PERSON_DESC = (
    "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap,NoiCuTru}]; SoDinhDanh liền chữ số; NgaySinh/NgayCap "
    "dd/mm/yyyy (chỉ có năm thì trả đúng năm); GioiTinh suy từ xưng hô Ông→Nam, Bà→Nữ; NoiCuTru là nơi thường "
    "trú/địa chỉ của CHÍNH người đó, " + _AREA_DESC
)

FIELDS: list[dict] = [
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ẢNH CCCD/CMND/thẻ Căn cước THẬT đã upload (không lấy người chỉ "
            "được nhắc trong đơn/giấy ủy quyền): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,"
            "NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD/CMND trong Đơn đề nghị thu hồi/hủy Giấy chứng nhận, Giấy ủy "
            "quyền (cả Bên ủy quyền, Bên nhận ủy quyền và người làm chứng) hoặc văn bản kèm theo, mỗi người "
            "một object: " + _PERSON_DESC
            + " Đơn thường ghi liền nhau 'Tôi tên là: … - Sinh ngày …', 'CC/CCCD số: … cấp ngày: …', 'Địa chỉ "
              "thường trú: …' → tách ra HoTen/NgaySinh/SoDinhDanh/NgayCap/NoiCuTru của cùng một người."
        ),
    },
    # ---- Chủ hồ sơ = người ĐỨNG ĐƠN đề nghị thu hồi/hủy GCN = người sử dụng đất phát hiện việc cấp sai. ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Chủ hồ sơ (người/tổ chức ĐỨNG ĐƠN đề nghị thu hồi, hủy Giấy chứng nhận) thuộc loại nào, trả ĐÚNG "
             "một trong bốn chuỗi: 'Cá nhân' | 'Doanh nghiệp' | 'Cơ quan nhà nước' | 'Tổ chức khác'. Hộ gia "
             "đình, cá nhân, vợ chồng → 'Cá nhân'. Công ty, doanh nghiệp, hợp tác xã, ngân hàng → 'Doanh "
             "nghiệp'. Ủy ban nhân dân, sở, ban, ngành, đơn vị sự nghiệp công lập → 'Cơ quan nhà nước'. Mặt "
             "trận Tổ quốc, hội, đoàn thể, tổ chức tôn giáo, cộng đồng dân cư → 'Tổ chức khác'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức/cơ quan: tên đầy đủ của tổ chức đứng đơn. KHÔNG lấy tên cơ quan "
             "NHẬN đơn ở dòng 'Kính gửi', KHÔNG lấy cơ quan đã cấp Giấy chứng nhận, KHÔNG lấy tên Văn phòng "
             "đăng ký đất đai hay Văn phòng công chứng."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức đó (10 hoặc 13 số, "
             "liền chữ số). Không có thì bỏ field."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng đơn ('Tôi tên là…', ký tên ở mục 'Chủ sử dụng "
             "đất'). KHÔNG lấy người được ủy quyền đi nộp (Bên B của Giấy ủy quyền), KHÔNG lấy người đang "
             "đứng tên trên Giấy chứng nhận bị đề nghị thu hồi nếu đó là người khác, KHÔNG lấy công chứng "
             "viên hay người làm chứng."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân ghi trên Đơn/Giấy ủy quyền, dd/mm/yyyy. Chỉ có 'Sinh năm 1950' thì "
             "trả '1950', không bịa ngày."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân ghi trên Đơn hoặc Giấy ủy quyền; liền chữ số. KHÔNG lấy số "
             "phát hành Giấy chứng nhận (vd BA 331193), số vào sổ cấp GCN (vd CH 00077), số quyết định, số "
             "thửa, số tờ bản đồ, số công chứng."},
    {"name": "ChuHoSo_NgayCap",
     "desc": "Ngày cấp CCCD của chủ hồ sơ cá nhân ghi trên Đơn/Giấy ủy quyền, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD của chủ hồ sơ cá nhân. 'Cục cảnh sát Quản lý hành chính về trật tự xã hội' → "
             "trả 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ THƯỜNG TRÚ của chủ hồ sơ ghi trên ĐƠN đề nghị thu hồi/hủy Giấy chứng nhận, " + _AREA_DESC
             + " KHÔNG lấy 'Địa chỉ thửa đất', KHÔNG lấy địa chỉ thường trú in trên Giấy chứng nhận (đó là "
               "địa danh cũ, thường đã sáp nhập), KHÔNG lấy địa chỉ Văn phòng công chứng."},
    {"name": "ChuHoSo_DiaChiUyQuyen",
     "desc": "Hộ khẩu thường trú của BÊN ỦY QUYỀN (Bên A) trên Giấy ủy quyền — chính là chủ hồ sơ khi hồ sơ "
             "nộp thay, " + _AREA_DESC + " KHÔNG lấy địa chỉ của Bên B hay của người làm chứng."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn đề nghị; liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn nếu có; bỏ trống/chấm chấm thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiUyQuyen"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp (tài khoản đang đăng nhập). Họ tên + Số Căn cước readonly, cổng tự đổ từ tài khoản
    # định danh → KHÔNG phát lại (sửa "Họ và tên" là cổng xoá trắng Di động + Số CCCD khi bấm Tiếp tục).
    # Di động/Email/Fax mapping ghi "Tự nhập" → không có nguồn trong hồ sơ, để cán bộ gõ.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # option 0 = Nữ, 1 = Nam
    "CongDan_danTocCongDan": "dom-select",       # 501 option, cổng không tự đổ
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",         # BẮT BUỘC (*) và cổng để TRỐNG — xem docstring
    "CongDan_maPhuongXa": "dom-select",          # nạp AJAX sau khi chọn tỉnh
    "CongDan_diaChi": "dom-input",
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
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
