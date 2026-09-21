"""Compact schema cho thủ tục 1.115679 — Lào Cai, nộp tại PHƯỜNG/XÃ.

"Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời hạn sử dụng đất;
điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp quy định tại Khoản 1 Điều 175 Luật Đất đai
năm 2024".

KHÁC 1.115651 (cùng TÊN nhưng là bản nộp ở SỞ): 1.115679 nhận hồ sơ ở UBND phường/xã, hồ sơ mẫu là hộ gia
đình - cá nhân chuyển đất trồng cây lâu năm sang đất ở, và bảng "Thành phần hồ sơ" bước 3 chia nhóm bằng CHỮ
CÁI "a) b) c) d)" chứ không phải "(1)…(4)". Hai thủ tục vì thế có hai pipeline riêng.

Cổng dichvucong.laocai.gov.vn (Nth.FormBuilder — iGate VNPT, jQuery/Bootstrap): bước 2 dùng CÙNG bộ ô
CongDan_* (người nộp) + ChuHoSo_* (chủ hồ sơ) với 1.115651/1.115667/1.115668/1.115671/1.115687/1.115688.
Mapping theo "Mapping_CMDSDD_1.115679_LaoCai_CaNhan_ToChuc.xlsx" (2 sheet: biến thể Cá nhân và biến thể Tổ
chức của ô "Đối tượng nộp hồ sơ").

BA ĐIỂM RIÊNG CỦA BIỂU MẪU NÀY (sheet "Bắt buộc điền"):
  1. Khối NGƯỜI NỘP có SÁU ô bắt buộc (*) mà cổng chỉ đổ "theo tài khoản": Giới tính, Dân tộc, Tỉnh/Thành phố,
     Phường/Xã, Số nhà/Đường/Tổ và Di động. Trợ lý điền lại cả cụm địa chỉ — nhưng CHỈ khi đọc được giấy tờ
     của CHÍNH người đang đăng nhập — để ba ô tỉnh/xã/số nhà là một địa chỉ nhất quán.
  2. Ô "Giới tính" KHÔNG có option trống: cổng luôn hiển thị "Nữ" ⇒ hồ sơ của nam giới mà không phát lại ô này
     là nộp sai giới tính mà nhìn vào form vẫn thấy "đã chọn" (sheet "Cảnh báo & đối chiếu", mục 11).
  3. Ô "Phường/Xã" của khối người nộp đang nạp sẵn danh sách xã của TỈNH THEO TÀI KHOẢN (ảnh chụp: 104 xã của
     Hưng Yên) ⇒ phải phát Tỉnh TRƯỚC để cổng nạp lại danh sách rồi mới phát Xã.

KHÔNG phát ô "Người nộp là chủ hồ sơ" (chkbox_nguoinoplachuhs): tích ô đó là cổng ÉP "Đối tượng nộp hồ sơ" =
Cá nhân rồi CHÉP khối người nộp đè lên khối chủ hồ sơ — sai người với hồ sơ nộp thay theo Giấy uỷ quyền (hồ sơ
mẫu HS1: ông Đào Văn Tuấn nộp thay ông Hoàng Trung Thành - bà Trần Thị Thương).

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
            "được nhắc trong đơn/giấy uỷ quyền/giấy chứng nhận): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,"
            "NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, "
            + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD/CMND trong Đơn đề nghị (Mẫu số 02/03/17), Giấy uỷ quyền (CẢ bên "
            "uỷ quyền lẫn bên được uỷ quyền), Giấy chứng nhận quyền sử dụng đất, Phiếu chuyển thông tin — mỗi "
            "người một object: " + _PERSON_DESC
            + " Đơn Mẫu số 02 ghi liền mạch 'HOÀNG TRUNG THÀNH Sinh: 1985, CC số: 0150 8500 7662 cấp ngày: "
              "10/6/2025 Nơi cấp: Bộ Công An. Vợ: TRẦN THỊ THƯƠNG Sinh năm: 1989, CCCD số: …' → tách thành "
              "HAI người, mỗi người đủ HoTen/NgaySinh/SoDinhDanh/NgayCap/NoiCap."
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên mục 1 của Đơn (Mẫu số 02/03/17). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Chủ hồ sơ (người sử dụng đất đứng tên mục 1 của Đơn) thuộc loại nào, trả ĐÚNG một trong bốn "
             "chuỗi: 'Cá nhân' | 'Doanh nghiệp' | 'Cơ quan nhà nước' | 'Tổ chức khác'. Hộ gia đình, cá nhân, "
             "hai vợ chồng cùng đứng tên → 'Cá nhân'. Công ty, doanh nghiệp, hợp tác xã, ngân hàng → 'Doanh "
             "nghiệp'. Uỷ ban nhân dân, sở, ban, ngành, ban quản lý, đơn vị sự nghiệp công lập → 'Cơ quan nhà "
             "nước'. Giáo xứ, nhà thờ, chùa, tổ chức tôn giáo, Mặt trận Tổ quốc, hội, đoàn thể, cộng đồng dân "
             "cư → 'Tổ chức khác'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: tên đầy đủ của tổ chức đang sử dụng đất — ưu tiên 'Tên công ty "
             "viết bằng tiếng Việt' trên Giấy chứng nhận đăng ký doanh nghiệp/Quyết định thành lập, rồi tên "
             "ở mục 1 của Đơn, rồi tên người sử dụng đất trên Giấy chứng nhận quyền sử dụng đất. KHÔNG lấy "
             "cơ quan ở dòng 'Kính gửi', cơ quan ra quyết định, đơn vị đo đạc, văn phòng công chứng."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức đó (10 hoặc 13 "
             "số, liền chữ số). Mã số thuế CÁ NHÂN trên Phiếu chuyển thông tin/Giấy nộp tiền KHÔNG dùng — "
             "biến thể Cá nhân của cổng ẩn hẳn ô này."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đề nghị ở mục '1. Người đề nghị chuyển mục đích sử "
             "dụng đất' của Đơn (bỏ chữ ÔNG/BÀ đứng trước). Hai vợ chồng cùng đứng tên thì lấy NGƯỜI ĐỨNG "
             "ĐẦU mục 1 — form chỉ có một ô họ tên, người còn lại đã nằm trong Đơn và Giấy chứng nhận đính "
             "kèm. KHÔNG lấy người được uỷ quyền đi nộp, KHÔNG lấy công chứng viên, cán bộ địa chính, người "
             "ký quyết định."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân ghi trên Đơn/Giấy uỷ quyền/Giấy chứng nhận, dd/mm/yyyy. Đơn và "
             "Giấy uỷ quyền của thủ tục này thường CHỈ ghi 'Sinh: 1985' → trả '1985', KHÔNG tự thêm "
             "ngày/tháng."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân ghi ở mục 1 của Đơn ('CC số: …' / 'CCCD số: …') hoặc trên "
             "Giấy uỷ quyền; liền chữ số (giấy tờ hay ghi cách nhóm 4 số '0150 8500 7662' → trả "
             "'015085007662'). Giấy chứng nhận cấp trước 2021 ghi CMND 9 số CŨ — chỉ dùng khi không có nguồn "
             "nào khác. KHÔNG lấy mã số thuế, số quyết định, số công chứng, số vào sổ cấp GCN, số thửa đất, "
             "số tờ bản đồ, diện tích."},
    {"name": "ChuHoSo_NgayCap",
     "desc": "Ngày cấp CCCD của chủ hồ sơ cá nhân ghi trên Đơn hoặc Giấy uỷ quyền, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD của chủ hồ sơ cá nhân. Viết tắt/viết sai 'Cục cảnh sát và QLHC về TTXH' → trả "
             "'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; 'Bộ công an' → 'Bộ Công an'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ của CHỦ HỒ SƠ ghi ở mục '2. Địa chỉ/trụ sở chính' của Đơn, " + _AREA_DESC
             + " KHÔNG lấy 'Địa điểm thửa đất/khu đất' ở mục 4, KHÔNG lấy địa chỉ người được uỷ quyền đi nộp."},
    {"name": "ChuHoSo_DiaChiUyQuyen",
     "desc": "Nơi thường trú của BÊN UỶ QUYỀN (chính là chủ hồ sơ khi hồ sơ nộp thay) trên Giấy uỷ quyền, "
             + _AREA_DESC + " KHÔNG lấy nơi thường trú của bên được uỷ quyền."},
    {"name": "ChuHoSo_DiaChiGcn",
     "desc": "Địa chỉ thường trú của người sử dụng đất in trên Giấy chứng nhận quyền sử dụng đất hoặc ghi ở "
             "Phiếu chuyển thông tin/hồ sơ đo đạc, " + _AREA_DESC
             + " Đây là nguồn BÙ cuối cùng vì Giấy chứng nhận cũ thường còn địa danh trước sáp nhập."},
    {"name": "ThuaDat_DiaChi",
     "desc": "Vị trí THỬA ĐẤT/khu đất xin chuyển mục đích ghi ở mục 4 của Đơn, trên Giấy chứng nhận hoặc "
             "phiếu đo đạc, " + _AREA_DESC + " KHÔNG trộn với địa chỉ nơi ở của chủ hồ sơ."},
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại ở mục '3. Thông tin liên hệ (điện thoại, fax, email...)' của Đơn; liền chữ số. "
             "Số viết tay trên Phiếu chuyển thông tin/Thông báo thuế cũ (2015) chỉ là nguồn bù."},
    {"name": "Don_Email", "desc": "Thư điện tử ghi ở mục 3 của Đơn nếu có; bỏ trống/chấm chấm thì bỏ field."},
    {"name": "PhieuChuyen_DienThoai",
     "desc": "Số điện thoại liên hệ ghi trên Phiếu chuyển thông tin để xác định nghĩa vụ tài chính về đất "
             "đai hoặc Thông báo nộp tiền sử dụng đất; liền chữ số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiUyQuyen", "ChuHoSo_DiaChiGcn", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp (tài khoản đang đăng nhập). "Họ và tên" + "Số Căn cước" readonly, cổng tự đổ từ tài
    # khoản định danh → KHÔNG phát lại.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # (*) — option 0 = Nữ (cổng luôn hiện sẵn), 1 = Nam
    "CongDan_danTocCongDan": "dom-select",       # (*) — 500 option + "-- Chưa chọn --", cổng không tự đổ
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",         # (*)
    "CongDan_maPhuongXa": "dom-select",          # (*) — nạp AJAX sau khi chọn tỉnh
    "CongDan_diaChi": "dom-input",               # (*)
    "CongDan_diDong": "dom-input",               # (*)
    "CongDan_email": "dom-input",
    # Phần II — chủ hồ sơ. Đối tượng là DRIVER: đổi CN/DN/CQ/TC mới hiện nhóm ô tương ứng → phát TRƯỚC.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",     # (*) — "" / CN / DN / CQ / TC
    "ChuHoSo_tenChuHoSo": "dom-input",           # chỉ hiện khi CN
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",   # chỉ hiện khi DN/CQ/TC
    "ChuHoSo_maSoThueChuHoSo": "dom-input",      # chỉ hiện khi DN/CQ/TC
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
