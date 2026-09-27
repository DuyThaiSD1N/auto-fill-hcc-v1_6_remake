"""Compact schema cho "[Bắc Ninh] Đính chính giấy chứng nhận đã cấp" (maThuTuc 1.115476).

LLM chỉ trả FACT nguồn từ CCCD người yêu cầu + Đơn đăng ký biến động (Mẫu số 18). UI field
điền vào e-form Bắc Ninh được `mapper.enrich` suy ra tất định.

Cấu trúc = ĐƠN Mẫu 18 + khối NGƯỜI NHẬN KẾT QUẢ (giống cap_doi_gcn_bac_ninh). Ô đơn khớp theo
CLASS eform-element-<Key>; ô người nhận khớp theo NAME.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ (người sử dụng đất đứng đơn = người nhận kết quả khi tự nộp).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người nộp hồ sơ (người sử dụng đất đứng đơn) — lấy từ CCCD "
        "hoặc dòng 'a) Tên'/'- Tên' của Đơn Mẫu 18. Ghi như trên Giấy chứng nhận đã cấp."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người đứng đơn; đọc mặt trước, MRZ mặt "
        "sau, hoặc dòng 'CCCD số' trong Đơn."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành '
             'chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng 'c) Địa chỉ'/'- Địa "
             "chỉ' của Đơn Mẫu 18. PHẢI giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh "
             '(vd "Bản Nậm Dòn, xã Nậm Hàng, tỉnh Lai Châu"). KHÔNG trả object, KHÔNG bỏ phường/xã.'},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 (vd "Chi nhánh VP ĐKĐĐ ..."). '
             'Bỏ ký hiệu chú thích "(1)" ở cuối.'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 (dòng 'Điện thoại liên hệ') "
        "nếu có. Chỉ chữ số; không lấy số điện thoại bàn."},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế người đứng đơn nếu Đơn ghi (dòng 'Mã số thuế (nếu có)'). "
        "Chỉ chữ số. Đơn để trống → bỏ, KHÔNG tự lấy số CCCD."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn (dòng 'Hộp thư điện tử (nếu có)'). Trống → bỏ."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Nội dung biến động ghi ở mục "2."/"II. Nội dung biến động" của Đơn Mẫu số 18, NGUYÊN VĂN — '
             'với thủ tục này thường là đính chính thông tin trên Giấy chứng nhận đã cấp (vd "Đính chính '
             'diện tích/số tờ, số thửa/họ tên..."). Chép đúng như trong đơn, không tự bịa.'},
    {"name": "Don_MienGiam",
     "desc": 'Mục "III. Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính" của Đơn, NGUYÊN VĂN. '
             "Đơn không có mục này hoặc để trống → bỏ."},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ nộp kèm (2) liệt kê ở mục giấy tờ liên quan của Đơn Mẫu 18 (dòng "(2) ..."). Bỏ nếu '
             "trống. KHÔNG lấy dòng (1) Giấy chứng nhận đã cấp (dòng in sẵn)."},
    {"name": "Don_GiayTo3",
     "desc": 'Giấy tờ nộp kèm (3) liệt kê ở mục giấy tờ liên quan của Đơn Mẫu 18 (dòng "(3) ..."). Bỏ nếu trống.'},
    # Mục "Thông tin khác" của Mẫu 18 mới — đơn bản cũ không có, chỉ điền khi đơn GHI RÕ.
    {"name": "Don_ThanhVienHo",
     "desc": 'Dòng "(1) Thành viên hộ gia đình" ở mục thông tin khác của Đơn, NGUYÊN VĂN. Không có → bỏ.'},
    {"name": "Don_TranhChap",
     "desc": 'Dòng "(2) Tình trạng tranh chấp đất đai" ở mục thông tin khác của Đơn, NGUYÊN VĂN. Không có → '
             "bỏ, KHÔNG tự suy \"không tranh chấp\"."},
    {"name": "Don_RanhGioi",
     "desc": 'Dòng "(3) Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận" của Đơn, NGUYÊN '
             "VĂN. Không có → bỏ, KHÔNG suy luận."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn Mẫu 18 (element_*) — khớp CLASS eform-element-<Key>, name = KEY ----
# Cổng đã thay form: nhãn đổi từ "a) Tên"/"c) Địa chỉ"/"2. Nội dung biến động" sang "- Tên(2)"/
# "- Địa chỉ"/"II. Nội dung biến động(3)" nên khớp NHÃN cũ trượt cả thân đơn. Class ngữ nghĩa
# (crawl DOM 27/09/2026, eformId 2883) ổn định hơn nhãn — cùng bộ key với dang_ky_bien_dong_dat_dai_bac_ninh.
K_KINHGUI = "KinhGui"
K_TEN = "Ten2"
K_GIAYTO = "GiayToNhanThanphapNhan"
K_DIACHI = "DiaChi"
K_MST = "MaSoThueNeuCo"
K_DIENTHOAI = "DienThoaiLienHeNeuCo"
K_EMAIL = "HopThuDienTuNeuCo"
K_NOIDUNG = "IINoiDungBienDong3"
K_MIENGIAM = "IIIThongTinVeDoiTuongDuocMienGiamNghiaVuTaiChinhVe"
# Mục giấy tờ nộp kèm: class chỉ là "2"/"3" (nhãn "(2)"/"(3)").
K_GIAYTO2 = "2"
K_GIAYTO3 = "3"
K_THANHVIENHO = "1ThanhVienHoGiaDinh5"
K_TRANHCHAP = "2TinhTrangTranhChapDatDai"
K_RANHGIOI = "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha"

# ---- Người nhận kết quả (khớp NAME — id DOM là _org_bn_hoso_noptructuyen_<name>) ----
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
