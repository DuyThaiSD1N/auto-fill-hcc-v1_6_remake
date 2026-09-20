"""Compact schema cho thủ tục 1.115677 — Lào Cai: "Xác nhận tiếp tục sử dụng đất nông nghiệp".

Cổng dichvucong.laocai.gov.vn (iGate VNPT / Nth.FormBuilder, form jQuery — field-key = thuộc tính
`name`, KHÔNG phải Angular/Form.io). Bước 2 "Thông tin người nộp / Thông tin chủ hồ sơ" dùng CÙNG bộ ô
`CongDan_*` + `ChuHoSo_*` với 1.115667/1.115668/1.115694, nên engine dom-* của extension khớp ô theo
thuộc tính `name`. Mapping theo "Mapping_XN_thoi_han_SDD_nong_nghiep_LaoCai.xlsx" (34 ô bước 2, bóc
tách từ cả hai biến thể DOM Cá nhân/Tổ chức).

⚠ HAI Ô KHÔNG BAO GIỜ PHÁT: `CongDan_tenCongDan` và `CongDan_soCmnd` là readonly, cổng tự điền từ tài
khoản định danh đã đăng nhập; script của cổng còn XOÁ TRẮNG "Di động" + "Số Căn cước" khi họ tên bị
sửa khác tài khoản. Vì vậy chúng không có trong UI_COMP_BY_NAME (xem mapper).

⚠ Bước 3 "Thành phần hồ sơ" CHỈ có ảnh chụp màn hình, chưa có DOM; khối "Biểu mẫu giấy tờ" (e-form kê
khai mục 3.1–3.8 của Đơn 39) đang thu gọn/chưa render (sheet "Cảnh báo trường ẩn"). Vì vậy các dữ kiện
nghiệp vụ (thửa đất, diện tích, thời hạn, GCN đã cấp) CHỈ trích để lưu trace — cố ý KHÔNG khai trong
UI_COMP_BY_NAME để mapper không phát ô không tồn tại. Ô "Về việc" (*) do cổng điền sẵn tên thủ tục —
KHÔNG ghi đè.

LLM chỉ trả FACT nguồn; `mapper.enrich` chọn nguồn theo ma trận ưu tiên rồi sinh field UI.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa chỉ hiện hành chỉ còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "số nhà/đường/tổ/thôn."
)
_PERSON_DESC = (
    "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,NgayCap,NoiCap,DienThoai,Email}]; SoDinhDanh liền chữ số; "
    "NgaySinh/NgayCap dd/mm/yyyy (giấy chỉ ghi năm thì trả đúng năm); GioiTinh suy từ xưng hô gắn "
    "TRỰC TIẾP với chính người đó (Ông→Nam, Bà→Nữ)."
)

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐƯỢC ỦY QUYỀN: điểm neo, trích ĐẦU TIÊN. Hiếm ở thủ tục này nhưng vẫn có; phải tách
    # khỏi "Người làm đơn" (vợ/chồng ký thay vẫn là ĐỒNG NGƯỜI SỬ DỤNG ĐẤT, không phải người được ủy
    # quyền) để mapper không gán nhầm nhân thân vào khối người nộp.
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "TRÍCH ĐẦU TIÊN. CHỈ điền khi hồ sơ có MỘT FILE RIÊNG tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY "
            "QUYỀN'/'VĂN BẢN ỦY QUYỀN'/'VĂN BẢN VỀ VIỆC ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số CCCD của "
            "bên B. Chép người đứng NGAY SAU 'ủy quyền cho' (bên B) vào object: {\"hoTen\", \"ngaySinh\" "
            "(dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", \"ngayCapCccd\" "
            "(dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", \"thuongTru\": " + _AREA_DESC + "}. "
            "BỎ TRỐNG object nếu: không có file ủy quyền; hoặc chỉ có CCCD rời; hoặc người kia chỉ là "
            "VỢ/CHỒNG cùng sử dụng đất đứng ở mục 1 Đơn Mẫu số 39, KỂ CẢ khi chính họ ký ở mục 'Người "
            "làm đơn' — họ KHÔNG phải người được ủy quyền. Đừng bịa."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ "
            "(không lấy người chỉ được NHẮC TỚI trong đơn hay Giấy chứng nhận): "
            "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap "
            "dd/mm/yyyy. NoiCuTru = nơi thường trú in trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi KÈM SỐ CCCD/CMND trong đơn/Giấy chứng nhận/giấy ủy quyền (người sử "
            "dụng đất, vợ/chồng, người làm đơn, người đại diện), mỗi người một object: " + _PERSON_DESC
        ),
    },
    # ---- MỤC 1 ĐƠN MẪU SỐ 39: cả hộ cùng sử dụng đất dùng CHUNG một địa chỉ liên hệ ở mục 2. Mapper
    # dùng danh sách này để biết người đang đi nộp có phải đồng người sử dụng đất hay không (vd chồng
    # đứng tên đầu, vợ ký đơn và đi nộp) → mới được dùng địa chỉ/liên hệ của Đơn cho khối người nộp.
    {
        "name": "Don_NguoiSuDungDat",
        "desc": (
            "TẤT CẢ người được liệt kê ở mục 1 'Người sử dụng đất' của Đơn Mẫu số 39, THEO ĐÚNG THỨ TỰ "
            "trên đơn, kể cả dòng 'Và vợ bà …' / 'Và chồng ông …': " + _PERSON_DESC + " Đây là những "
            "người CÙNG sử dụng thửa đất và CÙNG dùng địa chỉ liên hệ ở mục 2 của đơn."
        ),
    },
    {
        "name": "Don_NguoiLamDon",
        "desc": "Họ tên người ký ở mục 'Người làm đơn' cuối Đơn Mẫu số 39. Có thể là vợ/chồng của người "
                "đứng tên đầu mục 1 — chép nguyên văn, KHÔNG suy ra đây là chủ hồ sơ.",
    },

    # ---- CHỦ HỒ SƠ = người sử dụng đất đứng tên ĐẦU TIÊN ở mục 1 Đơn Mẫu số 39.
    {
        "name": "ChuHoSo_LoaiDoiTuong",
        "desc": "Chủ hồ sơ (người sử dụng đất đứng tên ĐẦU TIÊN ở mục 1 Đơn Mẫu số 39) là 'Cá nhân' hay "
                "'Tổ chức'. Hộ gia đình / 'Hộ ông …' vẫn tính là 'Cá nhân'.",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người sử dụng đất đứng tên ĐẦU TIÊN ở mục 1 Đơn "
                "Mẫu số 39. Hai vợ chồng cùng sử dụng đất → lấy người đứng tên đầu; người còn lại đưa "
                "vào Don_NguoiSuDungDat và NguoiTrongGiayTo.",
    },
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô đứng ngay trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh chủ hồ sơ cá nhân, dd/mm/yyyy. Giấy chỉ ghi 'Sinh năm 1971' thì trả '1971', "
                "KHÔNG tự thêm ngày/tháng. Đơn Mẫu số 39 KHÔNG có ô ngày sinh — chỉ CCCD mới có.",
    },
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính chủ hồ sơ cá nhân: 'Nam' hoặc 'Nữ'."},
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc chủ hồ sơ cá nhân nếu giấy tờ ghi rõ (vd 'Kinh'). CCCD KHÔNG in dân tộc trên mặt "
                "thẻ — thường chỉ có ở giấy tờ hộ tịch. Không có thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân, liền chữ số. Một người có CẢ số căn cước 12 số LẪN "
                "số CMND 9 số (mục 'Những thay đổi sau khi cấp Giấy chứng nhận' hay in số CMND 9 số cũ) "
                "→ LUÔN chọn số 12 số.",
    },
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/CMND của chủ hồ sơ cá nhân, dd/mm/yyyy."},
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/CMND của chủ hồ sơ cá nhân. 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát quản lý "
                "hành chính về trật tự xã hội'; thẻ Căn cước mẫu mới ghi 'BỘ CÔNG AN' → 'Bộ Công an'.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "CHỈ khi chủ hồ sơ là TỔ CHỨC: tên tổ chức đứng tên người sử dụng đất ở mục 1 Đơn Mẫu số "
                "39. TUYỆT ĐỐI không lấy tên cơ quan nhận đơn ('Kính gửi: Văn phòng đăng ký đất đai …'), "
                "không lấy tên cơ quan cấp Giấy chứng nhận.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "CHỈ khi chủ hồ sơ là TỔ CHỨC: mã số doanh nghiệp/mã số thuế của CHÍNH tổ chức đó (10 "
                "hoặc 13 số, liền chữ số).",
    },
    {
        "name": "ChuHoSo_DiaChiDon",
        "desc": "Địa chỉ ghi ở mục 2 'Địa chỉ liên hệ' của Đơn Mẫu số 39, " + _AREA_DESC + " ĐÂY LÀ NƠI "
                "CƯ TRÚ — TUYỆT ĐỐI không lấy mục '3.7. Địa điểm thửa đất/khu đất' (đó là vị trí đất).",
    },
    {
        "name": "ChuHoSo_DiaChiToChuc",
        "desc": "CHỈ khi chủ hồ sơ là TỔ CHỨC: địa chỉ trụ sở chính của tổ chức đó ghi trên Giấy chứng "
                "nhận đăng ký doanh nghiệp hoặc tiêu đề/con dấu văn bản, " + _AREA_DESC,
    },
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại ghi ở mục 2 'Địa chỉ liên hệ (điện thoại, email...)' của Đơn Mẫu số 39; liền "
             "chữ số. Đơn bỏ trống/chấm chấm thì bỏ field, KHÔNG bịa."},
    {"name": "Don_Email",
     "desc": "Hộp thư điện tử ghi ở mục 2 của Đơn Mẫu số 39 nếu có; đơn bỏ trống thì bỏ field."},
    {"name": "ToChuc_DienThoai", "desc": "Điện thoại của tổ chức chủ hồ sơ (chỉ khi chủ hồ sơ là tổ chức)."},
    {"name": "ToChuc_Email", "desc": "Thư điện tử của tổ chức chủ hồ sơ (chỉ khi chủ hồ sơ là tổ chức)."},

    # ---- NGHIỆP VỤ: bước 2 KHÔNG có ô để điền (xem docstring). Trích để lưu trace cho cán bộ đối
    # chiếu và để dùng lại khi khối "Biểu mẫu giấy tờ" (e-form Mẫu 39) ở bước 3 có DOM.
    {
        "name": "Don_KinhGui",
        "desc": "Cơ quan nhận đơn ghi ở dòng 'Kính gửi:' của Đơn Mẫu số 39 (vd 'Văn phòng đăng ký đất đai "
                "tỉnh Lào Cai').",
    },
    {"name": "Don_NgayLap",
     "desc": "Ngày lập Đơn Mẫu số 39 ghi ở dòng '……, ngày … tháng … năm …' phía trên tiêu đề, dd/mm/yyyy."},
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Chép NGUYÊN VĂN mục 4 'Nội dung đề nghị xác nhận lại thời hạn sử dụng đất' của Đơn Mẫu "
                "số 39 (vd 'đến ngày 15 tháng 11 năm 2063'). Không tóm tắt thành câu khác nghĩa, không "
                "lấy tiêu đề thủ tục trên cổng.",
    },
    {
        "name": "ThuaDat_So",
        "desc": "Mục 3.1 'Thửa đất số' của Đơn Mẫu số 39. Đơn có thể kê NHIỀU thửa — chép nguyên cả dãy, "
                "giữ dấu phân cách (vd '289; 435; 438; 285; 441; 370; 257; 55').",
    },
    {
        "name": "ThuaDat_ToBanDo",
        "desc": "Mục 3.2 'Tờ bản đồ số' của Đơn Mẫu số 39, chép nguyên cả dãy (vd '10; 11 và 20').",
    },
    {
        "name": "ThuaDat_DienTich",
        "desc": "Mục 3.3 'Diện tích đất (m2)' của Đơn Mẫu số 39, chép nguyên văn kể cả phần diện tích ghi "
                "theo từng thửa (vd 'thửa 289 (135,8 m2); thửa 435 (442,0 m2); …').",
    },
    {
        "name": "ThuaDat_MucDichSuDung",
        "desc": "Mục 3.4 'Mục đích sử dụng đất' của Đơn Mẫu số 39, chép nguyên văn (vd 'đất trồng lúa "
                "(thửa 289; 435; …); đất nuôi trồng thủy sản (thửa 55)').",
    },
    {
        "name": "ThuaDat_ThoiHanSuDung",
        "desc": "Mục 3.5 'Thời hạn sử dụng đất' ĐANG ghi trên Giấy chứng nhận đã cấp (vd '2013') — là thời "
                "hạn CŨ cần xác nhận lại, KHÔNG phải thời hạn đề nghị ở mục 4.",
    },
    {
        "name": "ThuaDat_TaiSanGanLien",
        "desc": "Mục 3.6 'Tài sản gắn liền với đất hiện có' của Đơn Mẫu số 39; đơn để trống/chấm chấm thì "
                "bỏ field.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "Mục 3.7 'Địa điểm thửa đất/khu đất' của Đơn Mẫu số 39, " + _AREA_DESC + " ĐÂY KHÔNG PHẢI "
                "nơi ở của người — tuyệt đối không gán trùng địa chỉ liên hệ ở mục 2.",
    },
    {
        "name": "Gcn_SoPhatHanh",
        "desc": "Mục 3.8 'Số phát hành' của Giấy chứng nhận đã cấp (in ở góc trang bìa, thường 1–2 chữ cái "
                "+ số, vd 'E 007548'). KHÔNG lấy 'Số vào sổ cấp GCN' vào field này.",
    },
    {"name": "Gcn_SoVaoSo",
     "desc": "Mục 3.8 'Số vào sổ' cấp Giấy chứng nhận (vd '000085', 'CN00…', 'H00…')."},
    {
        "name": "Gcn_NgayCap",
        "desc": "Mục 3.8 'Ngày cấp' Giấy chứng nhận đã cấp, dd/mm/yyyy. KHÔNG lấy ngày đăng ký biến động ở "
                "mục 'Những thay đổi sau khi cấp Giấy chứng nhận', không lấy ngày lập mảnh trích đo.",
    },
    {
        "name": "Gcn_DonViCap",
        "desc": "Cơ quan KÝ CẤP Giấy chứng nhận đã cấp (vd 'UBND huyện Trấn Yên', 'Văn phòng đăng ký đất "
                "đai tỉnh …'). 'TM. ỦY BAN NHÂN DÂN ...' → 'UBND ...'.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap", "Gcn_NgayCap", "Don_NgayLap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiToChuc", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- Ô UI THẬT ở bước 2 (thuộc tính `name`, Nth.FormBuilder). <select> native → dom-select, còn lại
# (kể cả datetime-picker) → dom-input. Danh sách bám đúng 34 dòng của file mapping; các ô CỐ Ý không khai:
#   CongDan_tenCongDan / CongDan_soCmnd : readonly, cổng điền từ tài khoản định danh — sửa họ tên là
#                                         cổng xoá trắng Di động + Số Căn cước.
#   CongDan_maDMDiaChi                  : input ẩn (display:none), label rỗng, chưa xác định được nhãn.
#   chkbox_nguoinoplachuhs              : checkbox "Người nộp là chủ hồ sơ" — mapper luôn phát ĐỦ khối
#                                         chủ hồ sơ nên không cần bấm; tự bấm còn rủi ro cổng xoá dữ liệu.
#   code-dkdn                           : ô tra cứu doanh nghiệp, không phải dữ liệu hồ sơ.
#   local_file / local_file_xuly / AN_FORM_CHS / tokenCsrf : input hidden hệ thống tự sinh.
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp (CHÍNH NGƯỜI ĐI NỘP: người sử dụng đất tự nộp, vợ/chồng cùng sử dụng
    # đất nộp thay, hoặc người được ủy quyền).
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",    # option Nữ(0)/Nam(1), không có "chưa chọn" → mặc định Nữ.
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",        # (*) cấp 1/3, 34 option tỉnh
    "CongDan_maPhuongXa": "dom-select",         # (*) cấp 2/3, nạp sau khi chọn tỉnh
    "CongDan_diaChi": "dom-input",              # (*) cấp 3/3
    "CongDan_diDong": "dom-input",              # (*)
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Phần II — Thông tin chủ hồ sơ. "Đối tượng nộp hồ sơ" là DRIVER: đổi CN/DN mới hiện nhóm ô tương
    # ứng (file mapping, sheet "Cảnh báo trường ẩn" mục 2) → mapper phát ô này TRƯỚC.
    "ChuHoSo_maDoiTuongNopHS": "dom-select",    # (*) "" / CN / DN / CQ / TC
    "ChuHoSo_tenChuHoSo": "dom-input",          # (*) khi CN
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",  # (*) khi DN/CQ/TC
    "ChuHoSo_maSoThueChuHoSo": "dom-input",     # (*) khi DN/CQ/TC
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",       # (*) khi CN
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",     # mặc định cổng là Lào Cai → phải đổi theo địa chỉ thật
    "ChuHoSo_maPhuongXaCHS": "dom-select",      # nạp AJAX sau khi chọn tỉnh
    "ChuHoSo_diaChiChuHoSo": "dom-input",
}

UI_ALIASES: dict[str, list[str]] = {}
