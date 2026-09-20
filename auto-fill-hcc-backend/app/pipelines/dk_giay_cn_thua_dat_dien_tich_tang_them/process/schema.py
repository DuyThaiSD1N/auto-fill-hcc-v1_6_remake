"""Compact schema cho thủ tục 1.115694 — Lào Cai.

"Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích tăng thêm do thay đổi ranh giới so với
Giấy chứng nhận đã cấp đối với trường hợp thửa đất gốc đã có Giấy chứng nhận, phần diện tích đất tăng
thêm do nhận chuyển quyền sử dụng một phần thửa đất đã được cấp Giấy chứng nhận".

Cổng dichvucong.laocai.gov.vn (iGate VNPT / Nth.FormBuilder, maCoQuan=STNMT_LCI) — bước 2 "Thông tin
người nộp / Thông tin chủ hồ sơ" dùng CÙNG bộ ô `CongDan_*` + `ChuHoSo_*` với 1.115667/1.115668, nên
engine dom-* của extension khớp ô theo thuộc tính `name`. Mapping theo
"Mapping_DVC_LaoCai_Buoc2_TranThiMinhHue.xlsx" (34 ô bước 2, đã đối chiếu cả hai biến thể DOM cá
nhân/tổ chức).

⚠ HAI Ô KHÔNG BAO GIỜ PHÁT: `CongDan_tenCongDan` và `CongDan_soCmnd` là readonly, cổng tự điền từ tài
khoản định danh đã đăng nhập; script của cổng còn XOÁ TRẮNG "Di động" + "Số Căn cước" khi họ tên bị
sửa khác tài khoản. Vì vậy chúng không có trong UI_COMP_BY_NAME (xem mapper).

⚠ Bước 3 "Thành phần hồ sơ" / eForm kê khai CHƯA có DOM (sheet "Cảnh báo trường ẩn" của file mapping
ghi rõ wizard chưa mở tới bước này), nên thủ tục khai `hasAttachmentStep: False` và các dữ kiện nghiệp
vụ (thửa đất, GCN đã cấp, diện tích tăng thêm) CHỈ trích để lưu trace — cố ý KHÔNG khai trong
UI_COMP_BY_NAME để mapper không phát ô không tồn tại.

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
    # ---- NGƯỜI ĐƯỢC ỦY QUYỀN: điểm neo, trích ĐẦU TIÊN. Hồ sơ dạng này rất hay nộp qua người được ủy
    # quyền, mà khối "Thông tin người nộp" của cổng là của CHÍNH người đi nộp, không phải chủ hồ sơ.
    {
        "name": "NguoiDuocUyQuyen",
        "desc": (
            "TRÍCH ĐẦU TIÊN. CHỈ điền khi hồ sơ có MỘT FILE RIÊNG tiêu đề 'GIẤY ỦY QUYỀN'/'HỢP ĐỒNG ỦY "
            "QUYỀN'/'VĂN BẢN ỦY QUYỀN'/'VĂN BẢN VỀ VIỆC ĐẠI DIỆN' có dòng 'ủy quyền cho' kèm số CCCD của "
            "bên B. Chép người đứng NGAY SAU 'ủy quyền cho' (bên B) vào object: {\"hoTen\", \"ngaySinh\" "
            "(dd/mm/yyyy), \"gioiTinh\" ('Nam'/'Nữ'), \"danToc\", \"soDinhDanh\", \"ngayCapCccd\" "
            "(dd/mm/yyyy), \"noiCapCccd\", \"dienThoai\", \"email\", \"thuongTru\": " + _AREA_DESC + "}. "
            "BỎ TRỐNG object nếu: không có file ủy quyền (chữ 'Giấy ủy quyền' chỉ được LIỆT KÊ trong mục "
            "giấy tờ nộp kèm của Đơn thì KHÔNG tính); hoặc chỉ có CCCD rời; hoặc người kia chỉ ĐỒNG KÝ "
            "đơn / ĐỒNG SỞ HỮU (vd vợ/chồng) — họ KHÔNG phải người được ủy quyền. Đừng bịa."
        ),
    },
    {
        "name": "DanhSachCccd",
        "desc": (
            "BẮT BUỘC trả một object cho MỖI ảnh/bản sao CCCD/CMND/thẻ Căn cước THẬT có trong hồ sơ "
            "(không lấy người chỉ được NHẮC TỚI trong hợp đồng/đơn): "
            "[{HoTen,SoDinhDanh,NgaySinh,GioiTinh,DanToc,NgayCap,NoiCap,NoiCuTru}]. NgaySinh/NgayCap "
            "dd/mm/yyyy. NoiCuTru = nơi thường trú in trên thẻ, " + _AREA_DESC
        ),
    },
    {
        "name": "NguoiTrongGiayTo",
        "desc": (
            "Mọi CÁ NHÂN được ghi KÈM SỐ CCCD trong đơn/hợp đồng/giấy ủy quyền/tờ khai thuế (bên nhận, "
            "bên chuyển quyền, đồng sở hữu, người đại diện), mỗi người một object: " + _PERSON_DESC
        ),
    },

    # ---- CHỦ HỒ SƠ = người sử dụng đất thửa GỐC, đồng thời là BÊN NHẬN chuyển quyền phần diện tích
    # tăng thêm, đứng tên mục 1 (I.1) Đơn đăng ký biến động đất đai.
    {
        "name": "ChuHoSo_LoaiDoiTuong",
        "desc": "Chủ hồ sơ (người đứng tên Đơn đăng ký biến động mục 1, bên NHẬN chuyển quyền phần diện "
                "tích tăng thêm) là 'Cá nhân' hay 'Tổ chức'.",
    },
    {
        "name": "ChuHoSo_HoTen",
        "desc": "CHỈ khi chủ hồ sơ là cá nhân: họ tên người đứng tên ĐẦU TIÊN ở mục 1 Đơn đăng ký biến "
                "động, cũng là bên nhận trên hợp đồng chuyển quyền phần diện tích tăng thêm. Hai vợ chồng "
                "cùng nhận → lấy người đứng tên đầu tiên; người còn lại đưa vào NguoiTrongGiayTo.",
    },
    {"name": "ChuHoSo_XungHo", "desc": "Xưng hô đứng ngay trước tên chủ hồ sơ cá nhân: 'Ông' hoặc 'Bà'."},
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh chủ hồ sơ cá nhân, dd/mm/yyyy. Giấy chỉ ghi 'Sinh năm 1969' thì trả '1969', "
                "KHÔNG tự thêm ngày/tháng.",
    },
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính chủ hồ sơ cá nhân: 'Nam' hoặc 'Nữ'."},
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc chủ hồ sơ cá nhân nếu giấy tờ ghi rõ (vd 'Kinh'). CCCD KHÔNG in dân tộc — thường "
                "chỉ có ở giấy tờ hộ tịch (giấy chứng nhận kết hôn, giấy khai sinh). Không có thì bỏ field.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND của chủ hồ sơ cá nhân, liền chữ số. Một người có CẢ số căn cước 12 số LẪN "
                "số CMND 9 số (CMND cũ hay in trên giấy tờ hộ tịch/GCN cấp trước đây) → LUÔN chọn số 12 số.",
    },
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/CMND của chủ hồ sơ cá nhân, dd/mm/yyyy."},
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD/CMND của chủ hồ sơ cá nhân. 'Cục CSQLHC về TTXH' → 'Cục Cảnh sát quản lý "
                "hành chính về trật tự xã hội'; thẻ Căn cước mẫu mới ghi 'BỘ CÔNG AN' → 'Bộ Công an'.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "CHỈ khi chủ hồ sơ là TỔ CHỨC: tên tổ chức đứng tên Đơn / bên NHẬN (bên mua) trên hợp "
                "đồng / tên trên GCN đăng ký doanh nghiệp CỦA CHÍNH tổ chức đó. TUYỆT ĐỐI không lấy tên "
                "bên CHUYỂN QUYỀN (bên bán, chủ đầu tư dự án), không lấy tên cơ quan cấp giấy.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "CHỈ khi chủ hồ sơ là TỔ CHỨC: mã số doanh nghiệp/mã số thuế của CHÍNH tổ chức đó (10 "
                "hoặc 13 số, liền chữ số). Không lấy MST bên bán/bên chuyển quyền.",
    },
    {
        "name": "ChuHoSo_DiaChiDon",
        "desc": "Địa chỉ của chủ hồ sơ ghi ở mục 1 ĐƠN ĐĂNG KÝ BIẾN ĐỘNG (hoặc tờ khai lệ phí trước bạ / "
                "tờ khai thuế sử dụng đất phi nông nghiệp), " + _AREA_DESC + " KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "ChuHoSo_DiaChiHopDong",
        "desc": "Địa chỉ (nơi thường trú, hoặc trụ sở chính nếu là tổ chức) của BÊN NHẬN trên hợp đồng/văn "
                "bản chuyển quyền phần diện tích tăng thêm, " + _AREA_DESC + " KHÔNG lấy địa chỉ bên "
                "bán/bên chuyển quyền, KHÔNG lấy địa chỉ thửa đất.",
    },
    {
        "name": "ChuHoSo_DiaChiDkdn",
        "desc": "Địa chỉ trụ sở chính trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ (không phải của bên "
                "chuyển quyền), " + _AREA_DESC,
    },
    {"name": "Don_DienThoai",
     "desc": "Số điện thoại liên hệ của chủ hồ sơ ghi ở mục 1 Đơn đăng ký biến động (hoặc tờ khai thuế); "
             "liền chữ số."},
    {"name": "Don_Email",
     "desc": "Hộp thư điện tử ở mục 1 Đơn đăng ký biến động nếu có ghi; đơn bỏ trống/chấm chấm thì bỏ field."},
    {"name": "HopDong_DienThoai",
     "desc": "Số điện thoại liên hệ của BÊN NHẬN ghi trên hợp đồng/biên bản bàn giao; liền chữ số."},
    {"name": "HopDong_Email", "desc": "Email của BÊN NHẬN ghi trên hợp đồng/biên bản bàn giao."},
    {"name": "Dkdn_DienThoai", "desc": "Điện thoại trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ."},
    {"name": "Dkdn_Email", "desc": "Thư điện tử trụ sở trên GCN đăng ký doanh nghiệp CỦA CHỦ HỒ SƠ."},

    # ---- NGHIỆP VỤ: bước 2 KHÔNG có ô để điền (xem docstring). Trích để lưu trace cho cán bộ đối
    # chiếu và để dùng lại khi bước 3 / eForm kê khai có DOM.
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung biến động người dân đề nghị, chép NGUYÊN VĂN mục 'Nội dung biến động' của Đơn "
                "đăng ký biến động. Không tóm tắt thành câu khác nghĩa, không lấy tiêu đề thủ tục trên cổng.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "Địa chỉ THỬA ĐẤT (thửa gốc đã có Giấy chứng nhận), " + _AREA_DESC + " Lấy ở mục 'Thửa "
                "đất' của Đơn / trên GCN / mảnh trích đo. ĐÂY KHÔNG PHẢI nơi ở của người — tuyệt đối "
                "không gán trùng địa chỉ chủ hồ sơ.",
    },
    {"name": "ThuaDat_So",
     "desc": "Thửa đất số (thửa gốc), lấy từ Đơn / GCN / mảnh trích đo bản đồ địa chính."},
    {
        "name": "ThuaDat_ToBanDo",
        "desc": "Tờ bản đồ số của thửa gốc. GCN cũ và bản đồ đo đạc mới có thể ghi SỐ TỜ KHÁC NHAU (do đo "
                "đạc lại) — lấy theo mảnh trích đo/chỉnh lý MỚI NHẤT.",
    },
    {
        "name": "DienTich_TangThem",
        "desc": "Phần diện tích TĂNG THÊM kèm đơn vị (vd '163,8 m2'), CHỈ khi giấy tờ ghi SẴN con số đó "
                "(mục nội dung biến động của Đơn, hoặc bảng thống kê trên mảnh trích đo). TUYỆT ĐỐI không "
                "tự lấy diện tích hiện trạng trừ diện tích theo GCN để suy ra.",
    },
    {
        "name": "Gcn_SoPhatHanh",
        "desc": "Số phát hành/số hiệu Giấy chứng nhận ĐÃ CẤP cho thửa gốc, in ở góc trang bìa, thường 2 "
                "chữ cái + số (vd 'AA 06583358'). KHÔNG lấy 'Số vào sổ cấp GCN' vào field này.",
    },
    {"name": "Gcn_SoVaoSo",
     "desc": "Số vào sổ cấp Giấy chứng nhận (dạng 'CN00…', 'VP …', 'H00…') của GCN đã cấp."},
    {
        "name": "Gcn_NgayCap",
        "desc": "Ngày ký/cấp Giấy chứng nhận đã cấp (gần chữ ký + con dấu cơ quan cấp), dd/mm/yyyy. KHÔNG "
                "lấy ngày đăng ký biến động ở mục 'Những thay đổi sau khi cấp Giấy chứng nhận'.",
    },
    {
        "name": "Gcn_DonViCap",
        "desc": "Cơ quan KÝ CẤP Giấy chứng nhận đã cấp (vd 'Văn phòng đăng ký đất đai tỉnh …', 'UBND "
                "Thành phố …'). 'TM. ỦY BAN NHÂN DÂN ...' → 'UBND ...'.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgayCap", "Gcn_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChiDon", "ChuHoSo_DiaChiHopDong", "ChuHoSo_DiaChiDkdn", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- Ô UI THẬT ở bước 2 (thuộc tính `name`, Nth.FormBuilder). <select> native → dom-select, còn lại
# (kể cả datetime-picker) → dom-input. Danh sách bám đúng 34 dòng của file mapping; các ô CỐ Ý không khai:
#   CongDan_tenCongDan / CongDan_soCmnd : readonly, cổng điền từ tài khoản định danh — sửa họ tên là
#                                         cổng xoá trắng Di động + Số Căn cước.
#   CongDan_maDMDiaChi                  : input ẩn (display:none), chưa xác định được nhãn.
#   chkbox_nguoinoplachuhs              : checkbox "Người nộp là chủ hồ sơ" — mapper luôn phát ĐỦ khối
#                                         chủ hồ sơ nên không cần bấm; tự bấm còn rủi ro cổng xoá dữ liệu.
#   code-dkdn                           : ô tra cứu doanh nghiệp, không phải dữ liệu hồ sơ.
UI_COMP_BY_NAME = {
    # Phần I — Thông tin người nộp (CHÍNH NGƯỜI ĐI NỘP: chủ hồ sơ tự nộp, hoặc người được ủy quyền).
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",    # option Nữ(0)/Nam(1), không có "chưa chọn" → mặc định Nữ.
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",        # (*) cấp 1/3
    "CongDan_maPhuongXa": "dom-select",         # (*) cấp 2/3, nạp sau khi chọn tỉnh
    "CongDan_diaChi": "dom-input",              # (*) cấp 3/3
    "CongDan_diDong": "dom-input",              # (*)
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Phần II — Thông tin chủ hồ sơ. "Đối tượng nộp hồ sơ" là DRIVER: đổi CN/DN mới hiện nhóm ô tương
    # ứng (file mapping, sheet "Cảnh báo trường ẩn") → mapper phát ô này TRƯỚC.
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
