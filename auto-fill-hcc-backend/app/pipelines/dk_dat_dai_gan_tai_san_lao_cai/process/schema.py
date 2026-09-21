"""Compact schema cho thủ tục 1.115688 — Lào Cai.

"Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn
liền với đất LẦN ĐẦU đối với tổ chức đang sử dụng đất".

Cổng dichvucong.laocai.gov.vn (Nth.FormBuilder — iGate VNPT, jQuery/Bootstrap) — bước 2 "Thông tin người nộp"
dùng CÙNG bộ ô CongDan_* (người nộp) + ChuHoSo_* (chủ hồ sơ) với 1.115651/1.115667/1.115668/1.115671/1.115687,
mapping theo "Mapping_1.115688_DangKyDatDai_LanDau_LaoCai.xlsx" (sheet "1. Tổ chức (HS01-HS02)" và
"2. Cá nhân (HS03)").

KHÁC 1.115687 ở hai chỗ:
  1. Tỉnh/Phường-Xã của khối NGƯỜI NỘP được cổng đổ sẵn theo tài khoản; chỉ "Số nhà/Đường/Tổ/Thôn" và "Di
     động" là bắt buộc (*) mà để trống. Trợ lý vẫn phát cả ba ô địa chỉ — nhưng CHỈ khi đọc được giấy tờ của
     CHÍNH người đang đăng nhập — để bộ ba tỉnh/xã/số nhà là một địa chỉ nhất quán, không chắp vá nửa tài
     khoản nửa giấy tờ.
  2. Di động/Email của khối người nộp có nguồn thật (Đơn Mẫu 15 mục "Điện thoại liên hệ"/"Hộp thư điện tử"),
     nhưng số đó là của NGƯỜI SỬ DỤNG ĐẤT. Chỉ dùng lại cho khối người nộp khi người đăng nhập CHÍNH LÀ chủ
     hồ sơ (khớp số định danh) — nộp thay thì để cán bộ gõ.

KHÔNG phát ô "Người nộp là chủ hồ sơ" (chkbox_nguoinoplachuhs): tích ô đó gọi nguoiNopLaChuHoSo() để cổng ÉP
"Đối tượng nộp hồ sơ" = Cá nhân rồi CHÉP toàn bộ khối người nộp sang khối chủ hồ sơ — sai hẳn với hồ sơ tổ
chức (HS01, HS02) và sai người với hồ sơ nộp thay. Khối chủ hồ sơ đã được điền thẳng từ giấy tờ.

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
            "được nhắc trong đơn/danh sách/giấy ủy quyền): [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,"
            "NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap dd/mm/yyyy. NoiCuTru = nơi thường trú trên thẻ, "
            + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi kèm số CCCD/CMND trong Đơn đăng ký đất đai (Mẫu số 15/21), Danh sách người "
            "sử dụng chung thửa đất (Mẫu 15a), Đơn đề nghị xác nhận thành viên có chung quyền sử dụng đất, "
            "Giấy ủy quyền (cả bên ủy quyền lẫn bên nhận ủy quyền) — mỗi người một object: " + _PERSON_DESC
            + " Đơn Mẫu 15 ghi liền nhau 'a) Họ và tên: … sinh ngày …', 'b) Giấy tờ nhân thân: CCCD số … cấp "
              "ngày … do … cấp', 'd) Địa chỉ: …' → tách ra HoTen/NgaySinh/SoDinhDanh/NgayCap/NoiCap/NoiCuTru "
              "của cùng một người. Mẫu 15a là BẢNG: mỗi dòng là một người đồng sử dụng đất."
        ),
    },
    # ---- Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên mục 1 của Đơn Mẫu 15 (cá nhân hoặc tổ chức). ----
    {"name": "ChuHoSo_LoaiDoiTuong",
     "desc": "Chủ hồ sơ (người sử dụng đất đứng tên mục 1 Đơn đăng ký) thuộc loại nào, trả ĐÚNG một trong "
             "bốn chuỗi: 'Cá nhân' | 'Doanh nghiệp' | 'Cơ quan nhà nước' | 'Tổ chức khác'. Hộ gia đình, cá "
             "nhân, vợ chồng, nhiều người cùng sử dụng đất → 'Cá nhân'. Công ty, doanh nghiệp, hợp tác xã, "
             "ngân hàng → 'Doanh nghiệp'. Ủy ban nhân dân, sở, ban, ngành, ban quản lý, đơn vị sự nghiệp "
             "công lập → 'Cơ quan nhà nước'. Giáo xứ, nhà thờ, chùa, tổ chức tôn giáo, Mặt trận Tổ quốc, "
             "hội, đoàn thể, cộng đồng dân cư → 'Tổ chức khác'."},
    {"name": "ChuHoSo_TenToChuc",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: tên đầy đủ của tổ chức đang sử dụng đất. Thứ tự ưu tiên nguồn: "
             "(1) giấy tờ pháp nhân (Quyết định thành lập — lấy tên MỚI sau sáp nhập, không lấy tên cũ trong "
             "quyết định phê duyệt phương án sử dụng đất), (2) Trích lục bản đồ địa chính mục 'Tên người sử "
             "dụng đất, người quản lý đất', (3) Đơn Mẫu 15 mục 1a. KHÔNG lấy tên cơ quan NHẬN đơn ở dòng "
             "'Kính gửi', KHÔNG lấy cơ quan cấp trên, KHÔNG lấy tên trên con dấu nếu khác tên pháp nhân, "
             "KHÔNG lấy tên đơn vị đo đạc trên trích lục."},
    {"name": "ChuHoSo_MaSoThue",
     "desc": "CHỈ khi chủ hồ sơ là tổ chức: mã số doanh nghiệp/mã số thuế của chính tổ chức đó ghi ở Đơn Mẫu "
             "15 mục 'Mã số thuế' (10 hoặc 13 số, liền chữ số). Không có thì bỏ field."},
    {"name": "ChuHoSo_HoTen",
     "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người sử dụng đất ở Đơn Mẫu 15 mục '1. a) Họ và tên' (bỏ "
             "chữ ÔNG/BÀ đứng trước). Nhiều người cùng sử dụng đất thì lấy người đứng ĐẦU mục 1a — form chỉ "
             "nhận một chủ hồ sơ, những người còn lại kê ở Mẫu 15a. KHÔNG lấy người được ủy quyền đi nộp, "
             "KHÔNG lấy cán bộ địa chính hay người ký xác nhận của UBND."},
    {"name": "ChuHoSo_NgaySinh",
     "desc": "Ngày sinh chủ hồ sơ cá nhân ghi trên Đơn Mẫu 15/Mẫu 15a/Đơn đề nghị xác nhận, dd/mm/yyyy. Chỉ "
             "có 'Năm sinh 1989' thì trả '1989', không bịa ngày. Các giấy tờ ghi LỆCH nhau thì lấy theo Đơn "
             "Mẫu 15."},
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân ghi ở Đơn Mẫu 15 mục '1. b) Giấy tờ nhân thân' hoặc Mẫu 15a "
             "cột 'Số'; liền chữ số (Đơn hay ghi cách nhóm 4 số '0100 8900 1379' → trả '010089001379'). "
             "KHÔNG lấy mã số thuế của tổ chức, số quyết định, số thửa đất, số tờ bản đồ, số vào sổ cấp Giấy "
             "chứng nhận, diện tích."},
    {"name": "ChuHoSo_NgayCap",
     "desc": "Ngày cấp CCCD của chủ hồ sơ cá nhân ghi trên Đơn Mẫu 15/Mẫu 15a, dd/mm/yyyy."},
    {"name": "ChuHoSo_NoiCap",
     "desc": "Cơ quan cấp CCCD của chủ hồ sơ cá nhân. Viết tắt 'Cục cảnh sát QLHC về TTXH' → trả 'Cục Cảnh "
             "sát quản lý hành chính về trật tự xã hội'."},
    {"name": "ChuHoSo_DiaChiDon",
     "desc": "Địa chỉ của CHỦ HỒ SƠ ghi trên ĐƠN Mẫu 15 (mục 'c) Địa chỉ' với tổ chức — là trụ sở; mục "
             "'d) Địa chỉ' với cá nhân — là nơi thường trú), " + _AREA_DESC
             + " KHÔNG lấy 'Địa chỉ thửa đất' ở mục 2, KHÔNG lấy địa chỉ của người được ủy quyền đi nộp."},
    {"name": "ChuHoSo_DiaChiUyQuyen",
     "desc": "Địa chỉ liên hệ của BÊN ỦY QUYỀN (bên A — chính là chủ hồ sơ khi hồ sơ nộp thay) trên Giấy ủy "
             "quyền, " + _AREA_DESC + " KHÔNG lấy địa chỉ của bên nhận ủy quyền."},
    {"name": "ChuHoSo_DiaChiDanhSach",
     "desc": "Địa chỉ của chủ hồ sơ ghi ở Danh sách Mẫu 15a cột 'Địa chỉ' hoặc ở Đơn đề nghị xác nhận thành "
             "viên có chung quyền sử dụng đất ('Địa chỉ thường trú'), " + _AREA_DESC
             + " Chỉ lấy dòng của CHÍNH người đứng tên mục 1a Đơn Mẫu 15."},
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 15 ('Điện thoại liên hệ (nếu có)'); liền chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn Mẫu 15 nếu có; bỏ trống/chấm chấm thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuHoSo_NgayCap"] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiUyQuyen", "ChuHoSo_DiaChiDanhSach"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô UI thật ở bước 2 (name = <tiền tố><key>, Nth.FormBuilder). <select> native → dom-select, còn lại → dom-input.
UI_COMP_BY_NAME = {
    # Phần I — người nộp (tài khoản đang đăng nhập). Họ tên + Số Căn cước readonly, cổng tự đổ từ tài khoản
    # định danh (khoaThongTinKhongChoPhepSua) → KHÔNG phát lại.
    "CongDan_tenCoQuanToChuc": "dom-input",      # người nộp đại diện tổ chức chủ hồ sơ
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",     # option 0 = Nữ (mặc định), 1 = Nam
    "CongDan_danTocCongDan": "dom-select",       # 500 option + "-- Chưa chọn --", cổng không tự đổ
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",
    "CongDan_maPhuongXa": "dom-select",          # nạp AJAX sau khi chọn tỉnh (bindBy #maTinhThanh)
    "CongDan_diaChi": "dom-input",               # BẮT BUỘC (*) và cổng để TRỐNG
    "CongDan_diDong": "dom-input",               # BẮT BUỘC (*) và cổng để TRỐNG
    "CongDan_email": "dom-input",
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
    "ChuHoSo_maPhuongXaCHS": "dom-select",       # nạp AJAX sau khi chọn tỉnh (bindBy #maTinhThanhCHS)
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
