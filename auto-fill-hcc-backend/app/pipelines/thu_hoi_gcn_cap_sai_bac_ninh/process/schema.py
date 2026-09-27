"""Compact schema cho "[Bắc Ninh] Thu hồi GCN cấp sai & cấp lại" (maThuTuc 1.115447).

Cổng đã thay form sang ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT (eformId 2896): người sử dụng
đất + thửa đất + tài sản + đề nghị a/b/c/d + giấy tờ nộp kèm. Nguồn: CCCD chủ hồ sơ, GCN QSDĐ (tên
chủ sử dụng dạng "Hộ ông…"), Biên bản họp gia đình (= văn bản kiến nghị, thường ghi đủ thông tin
thửa đất của GCN xin thu hồi).
"""

FIELDS: list[dict] = [
    {"name": "Cccd_HoTen",
     "desc": "Họ tên người kiến nghị/chủ hồ sơ, vd \"Nguyễn Văn A\". ƯU TIÊN nguồn có DẤU CHUẨN: "
             "CCCD > Biên bản họp gia đình. KHÔNG lấy tên từ GCN/sổ đỏ cũ (OCR hay sai dấu)."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD của chủ hồ sơ (từ CCCD hoặc dòng CCCD số trên đơn/biên bản)."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự '
             'xã hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an". Bỏ nếu không có.'},
    {"name": "TenChuSuDungDat",
     "desc": 'Tên chủ sử dụng đất cho ô "a) Họ và tên", dạng "Hộ ông …"/"Hộ bà …" (vd "Hộ ông Nguyễn Văn A"). '
             'ƯU TIÊN lấy từ Biên bản họp gia đình (cụm "chủ sử dụng đất, hộ ông/bà: …") hoặc CCCD — '
             'nguồn có DẤU CHUẨN. KHÔNG lấy tên từ GCN/sổ đỏ cũ nếu OCR sai dấu. '
             "Nếu không rõ ông/bà thì bỏ tiền tố, chỉ trả họ tên chuẩn."},
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn (dòng "Kính gửi:" hoặc "đề nghị UBND …" trong biên bản), vd "UBND phường X".'},
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ thường trú của chủ hồ sơ — CHUỖI MỘT DÒNG, giữ đủ tổ/thôn + phường/xã + tỉnh. KHÔNG object."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại (thường không có trên giấy tờ → bỏ). Chỉ chữ số."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử nếu giấy tờ có ghi. Thường không có → bỏ."},

    # Thửa đất của GCN xin thu hồi (mục 2 của đơn).
    {"name": "Dat_ThuaSo", "desc": 'Số thửa đất, vd "385". Chỉ số thửa, không kèm chữ.'},
    {"name": "Dat_ToBanDo", "desc": 'Số tờ bản đồ, vd "2".'},
    {"name": "Dat_DiaChi",
     "desc": "Địa chỉ thửa đất — CHUỖI MỘT DÒNG, giữ đủ thôn/tổ + phường/xã + tỉnh. Nếu tài liệu ghi cả địa "
             'danh cũ và "(Nay là …)" thì lấy ĐỊA DANH MỚI sau "Nay là". KHÔNG object.'},
    {"name": "Dat_DienTich", "desc": 'Diện tích thửa đất, vd "168,0 m²".'},
    {"name": "Dat_SuDungChung", "desc": 'Diện tích "sử dụng chung" nếu tài liệu ghi rõ. Bỏ nếu không ghi.'},
    {"name": "Dat_SuDungRieng", "desc": 'Diện tích "sử dụng riêng" nếu tài liệu ghi rõ. Bỏ nếu không ghi.'},
    {"name": "Dat_MucDich", "desc": 'Mục đích sử dụng đất như tài liệu ghi, vd "Ao", "Đất ở".'},
    {"name": "Dat_TuThoiDiem", "desc": 'Thời điểm bắt đầu sử dụng đất nếu tài liệu ghi rõ. Bỏ nếu không có.'},
    {"name": "Dat_ThoiHan", "desc": 'Thời hạn sử dụng đất, vd "Lâu dài".'},
    {"name": "Dat_NguonGoc", "desc": "Nguồn gốc sử dụng đất nếu tài liệu ghi rõ, NGUYÊN VĂN. Bỏ nếu không có."},
    {"name": "Gcn_SoPhatHanh",
     "desc": 'Số phát hành (số seri) của GCN xin thu hồi, vd "K 708004" (dòng "Số sổ …"/"Số K…"). KHÔNG lấy '
             'số vào sổ cấp GCN ("Số …QSDĐ/…").'},
    {"name": "Don_VanBanKienNghi",
     "desc": 'Tên loại văn bản kiến nghị thu hồi nộp kèm, theo tiêu đề tài liệu, vd "Biên bản họp gia đình". '
             "Bỏ nếu không có văn bản kiến nghị."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn (element_*) — khớp CLASS eform-element-<Key>, name = KEY (crawl DOM 27/09/2026) ----
# Form cũ khớp NHÃN "a) Tên" nên trượt khi cổng đổi sang "a) Họ và tên (2)".
K_KINHGUI = "KinhGui"
K_TEN = "AHoVaTen2"
K_GIAYTO = "BGiayToNhanThanphapNhan3"
K_DIACHI = "CDiaChi4"
K_DIENTHOAI = "DDienThoaiLienHeNeuCo"
K_EMAIL = "HopThuDienTuNeuCo"
K_THUA = "AThuaDatSo"
K_TOBANDO = "22ToBanDoSo"
K_DAT_DIACHI = "BDiaChi5"
K_DIENTICH = "CDienTich6"
K_SD_CHUNG = "SuDungChung"
K_SD_RIENG = "SuDungRieng"
K_MUCDICH = "DSuDungVaoMucDich7"
K_TUTHOIDIEM = "TuThoiDiem"
K_THOIHAN = "DThoiHanDeNghiDuocSuDungDat8"
K_NGUONGOC = "ENguonGocSuDungDat9"
K_DENGHI_KHAC = "DDeNghiKhacNeuCo"
# Mục giấy tờ nộp kèm: class chỉ là "1"/"2" (nhãn "(1)"/"(2)").
K_KEM1 = "1"
K_KEM2 = "2"

# ---- Người nhận (khớp NAME) ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

# ---- Checkbox "Đề nghị a/b" (eform-element-boolean) — tick theo NHÃN ----
L_DENGHI = "__DeNghiAB__"  # name ảo; FE dùng comp bn-radio + value = danh sách nhãn cần tick

UI_COMP_BY_NAME = {
    K_KINHGUI: "bn-input", K_TEN: "bn-input", K_GIAYTO: "bn-input", K_DIACHI: "bn-input",
    K_DIENTHOAI: "bn-input", K_EMAIL: "bn-input",
    K_THUA: "bn-input", K_TOBANDO: "bn-input", K_DAT_DIACHI: "bn-input", K_DIENTICH: "bn-input",
    K_SD_CHUNG: "bn-input", K_SD_RIENG: "bn-input", K_MUCDICH: "bn-input", K_TUTHOIDIEM: "bn-input",
    K_THOIHAN: "bn-input", K_NGUONGOC: "bn-input", K_DENGHI_KHAC: "bn-input",
    K_KEM1: "bn-input", K_KEM2: "bn-input",
    N_HOTEN: "bn-input", N_CCCD: "bn-input", N_SDT: "bn-input", N_DIACHI: "bn-input",
    L_DENGHI: "bn-radio",
}
