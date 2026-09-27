"""Compact schema cho "[Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót" (maThuTuc 1.115446).

LLM chỉ trả FACT nguồn từ CCCD người yêu cầu + Đơn đăng ký biến động (Mẫu số 18).
UI field điền vào e-form Bắc Ninh được `mapper.enrich` suy ra tất định.

Cổng đã thay form (eformId 2858): nhãn đổi từ "a) Tên"/"c) Địa chỉ"/"2. Nội dung biến động" sang
"- Tên(2)"/"- Địa chỉ"/"II. Nội dung biến động(3)" nên khớp NHÃN cũ trượt gần hết thân đơn. Ô đơn
giờ khớp theo CLASS eform-element-<Key> (cùng bộ key với dinh_chinh_gcn_da_cap_bac_ninh); khối
người nhận kết quả khớp theo NAME.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ (người sử dụng đất đứng đơn).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người nộp hồ sơ (người đứng đơn) — lấy từ CCCD hoặc dòng 'Tên' của Đơn."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người đứng đơn; có thể đọc từ MRZ mặt sau hoặc dòng 'CCCD số'/'Căn cước số' trong Đơn."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi '
             '"BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng 'c) Địa chỉ'/'- Địa "
             "chỉ' của Đơn Mẫu 18. PHẢI giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh "
             '(vd "Thôn X, xã Y, tỉnh Bắc Ninh"). KHÔNG trả object, KHÔNG bỏ phường/xã.'},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 '
             '(vd "UBND xã Y, tỉnh Bắc Ninh"). Bỏ ký hiệu chú thích "(1)" ở cuối.'},
    {"name": "Don_Ten",
     "desc": 'NGUYÊN VĂN dòng "a) Tên"/"- Tên" của Đơn nếu đơn ghi thêm thông tin ngoài họ tên (vd "Ông '
             'NGUYỄN VĂN A, sinh năm 1980 (là người đại diện ...)"). Đơn chỉ ghi họ tên → bỏ.'},
    {"name": "Don_GiayToNhanThan",
     "desc": 'NGUYÊN VĂN dòng "b) Giấy tờ nhân thân/pháp nhân"/"- Giấy tờ nhân thân/pháp nhân" của Đơn '
             '(vd "Căn cước số 001090001234"). Dòng trống/chỉ có "...." → bỏ.'},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế người đứng đơn nếu Đơn ghi. Chỉ chữ số. Trống/\"....\" → bỏ."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 nếu có. Chỉ chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn nếu có. Trống/\"....\" → bỏ."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Nội dung biến động/đính chính ghi ở mục "2."/"II. Nội dung biến động" của Đơn Mẫu số 18, '
             'NGUYÊN VĂN (vd "Đính chính mục đích sử dụng đất"). Không tự bịa.'},
    {"name": "Don_MienGiam",
     "desc": 'Mục "III. Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính" của Đơn, NGUYÊN VĂN. '
             "Trống → bỏ."},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ nộp kèm THỨ HAI trong danh sách giấy tờ liên quan của Đơn (dòng ngay sau "(1) Giấy '
             'chứng nhận đã cấp…"), bất kể đơn đánh số (2) hay (4). Vd "CCCD bản photo". Bỏ nếu không có.'},
    {"name": "Don_GiayTo3",
     "desc": "Giấy tờ nộp kèm THỨ BA trong danh sách đó (dòng tiếp theo sau Don_GiayTo2). Nếu còn nhiều dòng "
             'nữa thì GHÉP các dòng còn lại, ngăn "; ". Bỏ nếu không có.'},
    # Mục cam kết/thông tin khác của Mẫu 18 mới — chỉ điền khi đơn GHI RÕ.
    {"name": "Don_ThanhVienHo",
     "desc": 'Dòng "(1) Thành viên hộ gia đình" của Đơn, NGUYÊN VĂN. Trống/"...." → bỏ.'},
    {"name": "Don_TranhChap",
     "desc": 'Dòng "(2) Tình trạng tranh chấp đất đai" của Đơn, NGUYÊN VĂN (vd "Không có tranh chấp"). '
             "Trống → bỏ, KHÔNG tự suy."},
    {"name": "Don_RanhGioi",
     "desc": 'Dòng "(3) Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận" của Đơn, NGUYÊN '
             "VĂN. Trống → bỏ, KHÔNG suy luận."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn Mẫu 18 (element_*) — khớp CLASS eform-element-<Key>, name = KEY (crawl 27/09/2026) ----
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
