"""Compact schema cho "[Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất" (1.115465).

LLM chỉ trả FACT nguồn từ CCCD + Đơn đăng ký biến động (Mẫu số 18) + Đơn trình báo mất / Bản cam kết. UI field điền
vào e-form Bắc Ninh do `mapper.enrich` suy ra tất định.

Ô đơn khớp CLASS eform-element-<Key> (mapping DOM 10/11/2026, cùng bộ khoá đính chính GCN Bắc Ninh); ô người nhận và
khối ủy quyền khớp NAME (id DOM _org_bn_hoso_noptructuyen_<name>).
"""

FIELDS: list[dict] = [
    # CCCD người đứng đơn (người sử dụng đất bị mất GCN).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người đứng Đơn Mẫu 18 (người sử dụng đất bị mất Giấy chứng nhận) — lấy "
        "từ CCCD hoặc dòng '- Tên' của Đơn. Ghi như trên Giấy chứng nhận / bên nhận chuyển quyền."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD của người đứng đơn; đọc mặt trước, MRZ mặt sau, hoặc dòng "
        "'Giấy tờ nhân thân' / 'CCCD số' trong Đơn. Chỉ chữ số (bỏ dấu chấm viết tay)."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã '
             'hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng '- Địa chỉ' mục I của Đơn Mẫu 18. "
             "PHẢI giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object, KHÔNG bỏ phường/xã."},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 (vd "Chi nhánh Văn phòng đăng ký đất đai ..."). '
             'Bỏ ký hiệu chú thích "(1)".'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 (dòng 'Điện thoại liên hệ'). Chỉ chữ "
        "số; không lấy số điện thoại bàn."},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế ghi trên Đơn (dòng 'Mã số thuế (nếu có)'). Chỉ chữ số. Đơn để trống → "
        "bỏ, KHÔNG tự lấy số CCCD."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn (dòng 'Hộp thư điện tử (nếu có)'). Trống → bỏ."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Mục "II. Nội dung biến động" của Đơn Mẫu 18, NGUYÊN VĂN, giữ các gạch đầu dòng và xuống dòng (vd "- Cấp '
             'lại giấy chứng nhận do bị mất"). CHỈ lấy từ Đơn, không lấy từ Đơn trình báo / Bản cam kết. Trống → bỏ.'},
    {"name": "Don_MienGiam",
     "desc": 'Mục "III. Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính" của Đơn, NGUYÊN VĂN. Trống → bỏ.'},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ nộp kèm "(2) ..." ở mục IV của Đơn. Bỏ nếu trống. KHÔNG lấy dòng in sẵn "(1) Giấy chứng nhận đã '
             'cấp".'},
    {"name": "Don_GiayTo3", "desc": 'Giấy tờ nộp kèm "(3) ..." ở mục IV của Đơn. Bỏ nếu trống.'},
    {"name": "Don_ThanhVienHo",
     "desc": 'Mục V "(1) Thành viên hộ gia đình" của Đơn, NGUYÊN VĂN. Trống → bỏ.'},
    {"name": "Don_TranhChap",
     "desc": 'Mục V "(2) Tình trạng tranh chấp đất đai" của Đơn, NGUYÊN VĂN. Trống → bỏ, KHÔNG tự suy "không tranh '
             'chấp" từ Bản cam kết.'},
    {"name": "Don_RanhGioi",
     "desc": 'Mục V "(3) Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận" của Đơn, NGUYÊN VĂN. Trống → '
             "bỏ."},

    # Giấy chứng nhận bị mất — hướng dẫn (3) Mẫu 18 yêu cầu ghi kèm vào Nội dung biến động.
    {"name": "Gcn_SoVaoSo",
     "desc": 'Số vào sổ cấp Giấy chứng nhận BỊ MẤT (dạng "CS01234/T05/Q02", "CH 00123"...) — đọc ở Đơn, Đơn trình báo '
             "mất giấy chứng nhận hoặc Bản cam kết. Chép đúng ký tự. Không có → bỏ."},
    {"name": "Gcn_SoPhatHanh",
     "desc": 'Số phát hành (số seri) của Giấy chứng nhận BỊ MẤT (dạng "CĐ 123456", "BX 654321"...) — đọc ở Đơn, Đơn '
             "trình báo mất hoặc Bản cam kết. Chép đúng chữ cái + số. Không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- purpose="authorized_person": khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*) ----
# Tài khoản đang nộp là người ĐƯỢC ủy quyền (người nộp thay); khối này hỏi NGƯỜI ỦY QUYỀN = CHỦ HỒ SƠ = người đứng
# Đơn Mẫu 18. Loại đối tượng mặc định "Cá nhân khác là Công dân Việt Nam" (cổng có cả "Người cao tuổi", cùng bộ ô).
FIELDS_UYQUYEN: list[dict] = [
    {"name": "ChuHoSo_HoTen",
     "desc": 'Họ tên CHỦ HỒ SƠ = người đứng Đơn Mẫu 18 (người sử dụng đất bị mất GCN); có Giấy ủy quyền thì là BÊN ỦY '
             'QUYỀN (bên A). Chỉ họ tên, không kèm Ông/Bà, năm sinh. TUYỆT ĐỐI KHÔNG lấy bên ĐƯỢC ủy quyền (bên B).'},
    {"name": "ChuHoSo_GioiTinh", "desc": '"Nam"/"Nữ" của chủ hồ sơ, CHỈ khi giấy tờ ghi rõ (CCCD, giấy xác nhận tình '
             'trạng hôn nhân) hoặc ghi "Ông"/"Bà" riêng (không phải "Ông, bà:" in sẵn). Không rõ → bỏ.'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh của chủ hồ sơ, chỉ chữ số."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy (CCCD / giấy xác nhận). Chỉ có năm → bỏ."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ hồ sơ, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "ChuHoSo_NoiCap",
     "desc": 'Nơi cấp CCCD của chủ hồ sơ ("Cục Cảnh sát QLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã '
             'hội"; thẻ căn cước mới "BỘ CÔNG AN" → "Bộ Công an"). Bỏ nếu không có.'},
    {"name": "ChuHoSo_ThuongTru",
     "desc": "Nơi ở hiện tại của chủ hồ sơ, object {quocGia,tinh,xa,chiTietDuoiXa} theo TÊN HÀNH CHÍNH HIỆN HÀNH: "
             "tinh=tỉnh/thành, xa=phường/xã, chiTietDuoiXa=thôn/tổ dân phố/số nhà. Giấy tờ ghi địa giới cũ kèm 'nay "
             "thuộc/nay là …' thì lấy phần 'nay'."},
    {"name": "ChuHoSo_DienThoai", "desc": "SĐT chủ hồ sơ (dòng Điện thoại liên hệ của Đơn). Chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email chủ hồ sơ nếu giấy tờ ghi rõ; thường không có → bỏ."},
]
ALLOWED_UYQUYEN = {f["name"] for f in FIELDS_UYQUYEN}
COMPACT_COMP_UYQUYEN = {name: "x-input" for name in ALLOWED_UYQUYEN}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap"):
    COMPACT_COMP_UYQUYEN[_name] = "x-date"
COMPACT_COMP_UYQUYEN["ChuHoSo_ThuongTru"] = "x-select-area"

# ---- UI thân đơn Mẫu 18 — khớp CLASS eform-element-<Key>, name = KEY ----
K_KINHGUI = "KinhGui"
K_TEN = "Ten2"
K_GIAYTO = "GiayToNhanThanphapNhan"
K_DIACHI = "DiaChi"
K_MST = "MaSoThueNeuCo"
K_DIENTHOAI = "DienThoaiLienHeNeuCo"
K_EMAIL = "HopThuDienTuNeuCo"
K_NOIDUNG = "IINoiDungBienDong3"
K_MIENGIAM = "IIIThongTinVeDoiTuongDuocMienGiamNghiaVuTaiChinhVe"
# Mục IV giấy tờ nộp kèm: class chỉ là "2"/"3" (nhãn "(2)"/"(3)"); dòng (1) là nhãn tĩnh, không có ô.
K_GIAYTO2 = "2"
K_GIAYTO3 = "3"
K_THANHVIENHO = "1ThanhVienHoGiaDinh5"
K_TRANHCHAP = "2TinhTrangTranhChapDatDai"
K_RANHGIOI = "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha"
# Không phát: NoiKhaiHoSo/NgayKhaiHoSo (cổng điền sẵn, class trùng với ô của phần UBND xác nhận) và
# HienTrangSuDungDatSuDungOnDinh (phần UBND cấp xã xác nhận, chỉ cho chuyển mục đích).

# ---- Người nhận kết quả (khớp NAME) ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

# comp: bn-input (input text), bn-textarea (ô nhiều dòng). FE điền theo CLASS/NAME.
UI_COMP_BY_NAME = {
    K_KINHGUI: "bn-input",
    K_TEN: "bn-input",
    K_GIAYTO: "bn-input",
    K_DIACHI: "bn-input",
    K_MST: "bn-input",
    K_DIENTHOAI: "bn-input",
    K_EMAIL: "bn-input",
    K_NOIDUNG: "bn-textarea",
    K_MIENGIAM: "bn-input",
    K_GIAYTO2: "bn-input",
    K_GIAYTO3: "bn-input",
    K_THANHVIENHO: "bn-input",
    K_TRANHCHAP: "bn-input",
    K_RANHGIOI: "bn-input",
    N_HOTEN: "bn-input",
    N_CCCD: "bn-input",
    N_SDT: "bn-input",
    N_DIACHI: "bn-input",
}
