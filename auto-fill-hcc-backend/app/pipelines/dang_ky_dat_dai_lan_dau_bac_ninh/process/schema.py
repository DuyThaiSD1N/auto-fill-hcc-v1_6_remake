"""Compact schema cho "[Bắc Ninh] Đăng ký đất đai, cấp GCN lần đầu" (Đơn Mẫu số 15).

LLM trả FACT nguồn từ Đơn Mẫu 15 (tờ khai) + CCCD người đề nghị. UI field điền vào e-form Bắc Ninh
được `mapper.enrich` suy ra:
  - Thân đơn (Phần II): ô `element_<id>` khớp theo NHÃN → name = CỐT NHÃN, comp bn-*.
  - Người nhận (Phần IV): field tên cố định `nhanTaiNha*` → name = ĐÚNG NAME.
  - Đề nghị a/b/c: radio → comp bn-radio, tick theo nhãn.
"""

FIELDS: list[dict] = [
    # CCCD + người đề nghị/sử dụng đất.
    {"name": "Cccd_HoTen", "desc": "Họ và tên người đề nghị/người sử dụng đất (CCCD hoặc mục 1 tờ khai)."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD người đề nghị."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật '
             'tự xã hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "Don_KinhGui", "desc": 'Nơi nhận ở dòng "Kính gửi:" của đơn (vd "UBND phường Song Liễu, tỉnh Bắc Ninh").'},
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ nơi cư trú người đề nghị (mục c) Địa chỉ của tờ khai) — CHUỖI MỘT DÒNG, giữ đủ "
             "tổ/thôn + phường/xã + tỉnh. KHÔNG trả object."},
    {"name": "Don_DienThoai", "desc": "Điện thoại liên hệ trên tờ khai (chỉ chữ số/định dạng như đơn)."},
    {"name": "Don_Email", "desc": 'Hộp thư điện tử trên tờ khai (mục 1.d). Bỏ nếu trống.'},
    {"name": "Don_NoiKhai", "desc": 'Địa danh nơi khai ở cuối đơn (vd "Song Liễu"). Bỏ nếu không có.'},

    # Thửa đất (mục 2 tờ khai).
    {"name": "Dat_ThuaSo", "desc": 'Số thửa đất (mục 2 "a) Thửa đất số"), chỉ phần số, vd "68".'},
    {"name": "Dat_ToBanDo", "desc": 'Số tờ bản đồ (mục "2.2. Tờ bản đồ số"), chỉ phần số, vd "3".'},
    {"name": "Dat_DiaChi",
     "desc": "Địa chỉ thửa đất (mục b) Địa chỉ (5)) — CHUỖI MỘT DÒNG, giữ đủ phường/xã, tỉnh. KHÔNG object."},
    {"name": "Dat_DienTich", "desc": 'Diện tích thửa đất (mục c), vd "152,0 m²".'},
    {"name": "Dat_SuDungChung", "desc": 'Diện tích/nội dung "Sử dụng chung" nếu có (vd "152,0 m²"). Bỏ nếu trống.'},
    {"name": "Dat_SuDungRieng", "desc": 'Diện tích/nội dung "Sử dụng riêng" nếu có (vd "0,0 m²"). Bỏ nếu trống.'},
    {"name": "Dat_MucDich", "desc": 'Mục đích sử dụng đất (mục d, vd "Đất ở").'},
    {"name": "Dat_TuThoiDiem", "desc": 'Sử dụng "từ thời điểm" (vd "27/03/2008"). Bỏ nếu trống.'},
    {"name": "Dat_ThoiHan", "desc": 'Thời hạn đề nghị được sử dụng đất (vd "Lâu dài").'},
    {"name": "Dat_NguonGoc",
     "desc": "Nguồn gốc sử dụng đất (mục e, chú thích (9)) — lấy TOÀN BỘ nội dung NGUYÊN VĂN từ sau "
             '"(9):" cho đến trước mục "g)", GỒM MỌI CÂU/ĐOẠN (nguồn gốc, phiếu thu, đồng chủ sử dụng, '
             "quá trình sử dụng, xây nhà...). KHÔNG rút gọn, KHÔNG cắt bớt."},

    # Nhà ở, công trình xây dựng (mục 3 tờ khai) — chỉ có khi người dân kê khai tài sản.
    {"name": "Nha_Loai", "desc": "a) Loại nhà ở, công trình xây dựng (11)."},
    {"name": "Nha_DienTichXayDung", "desc": 'b) Diện tích xây dựng (12), giữ đơn vị như đơn (vd "80,5 m²").'},
    {"name": "Nha_DienTichSan", "desc": "c) Diện tích sàn xây dựng/diện tích sử dụng (13), giữ đơn vị."},
    {"name": "Nha_SoHuuChung", "desc": "d) Sở hữu chung (14), giữ đơn vị."},
    {"name": "Nha_SoHuuRieng", "desc": "Sở hữu riêng (14), giữ đơn vị."},
    {"name": "Nha_SoTang", "desc": 'đ) Tổng số tầng, chỉ phần số (vd "3").'},
    {"name": "Nha_SoTangNoi", "desc": "Số tầng nổi, chỉ phần số."},
    {"name": "Nha_SoTangHam", "desc": "Số tầng hầm, chỉ phần số."},
    {"name": "Nha_NguonGoc", "desc": "e) Nguồn gốc nhà ở, công trình (15) (vd \"Tự xây dựng\")."},
    {"name": "Nha_NamHoanThanh", "desc": "g) Năm hoàn thành xây dựng (16)."},
    {"name": "Nha_ThoiHanSoHuu", "desc": "h) Thời hạn sở hữu đến (17)."},

    # Mục "5. Những giấy tờ nộp kèm theo" — danh sách giấy tờ đính kèm công dân tự liệt kê.
    {"name": "Don_KemTheo1", "desc": 'Giấy tờ nộp kèm số (1) ở mục 5 (vd "Mẫu số 15a. danh sách...").'},
    {"name": "Don_KemTheo2", "desc": 'Giấy tờ nộp kèm số (2) ở mục 5 (vd "02 Phiếu thu tiền (Bản photo)").'},
    {"name": "Don_KemTheo3", "desc": 'Giấy tờ nộp kèm số (3) ở mục 5 (vd "Căn cước công dân (Bản sao)").'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI: ô thân đơn (Phần II) — khớp theo NHÃN ----
L_KINHGUI = "Kính gửi"
L_HOTEN = "a) Họ và tên"
L_GIAYTO = "b) Giấy tờ nhân thân/pháp nhân"
L_DIACHI = "c) Địa chỉ"           # người đề nghị (title "c) Địa chỉ (4)")
L_DIENTHOAI = "d) Điện thoại liên hệ"
L_DAT_DIACHI = "b) Địa chỉ (5)"   # thửa đất
L_DAT_DIENTICH = "c) Diện tích"   # title "c) Diện tích (6)"
L_SD_CHUNG = "sử dụng chung"
L_SD_RIENG = "sử dụng riêng"
L_MUCDICH = "d) Sử dụng vào mục đích"
L_TUTHOIDIEM = "từ thời điểm"
L_THOIHAN = "d) Thời hạn đề nghị được sử dụng đất"
L_NGUONGOC = "e) Nguồn gốc sử dụng đất"
# Ô (1)(2) thực chất là mục "5. Những giấy tờ nộp kèm theo" (KHÔNG phải chú thích như xlsx ghi).
# Form 1.115443 chỉ còn 2 ô (bỏ "(3)") → mapper gộp giấy tờ (3) vào ô (2).
L_KT1 = "(1)"
L_KT2 = "(2)"
L_NOIKHAI = "Nơi khai hồ sơ"

# Ô mới của form 1.115443 — khớp theo CLASS eform-element-<Key> (nhãn "tờ bản đồ số" trùng ở mục g).
C_EMAIL = "HopThuDienTuNeuCo"
C_THUA_SO = "AThuaDatSo"
C_TO_BAN_DO = "22ToBanDoSo"
C_NHA_LOAI = "ALoaiNhaOCongTrinhXayDung11"
C_NHA_DT_XD = "BDienTichXayDung12"
C_NHA_DT_SAN = "CDienTichSanXayDungdienTichSuDung13"
C_NHA_SH_CHUNG = "DSoHuuChung14"
C_NHA_SH_RIENG = "SoHuuRieng14"
C_NHA_SO_TANG = "DSoTang"
C_NHA_TANG_NOI = "TangTrongDoSoTangNoi"
C_NHA_TANG_HAM = "TangSoTangHam"
C_NHA_NGUON_GOC = "ENguonGoc15"
C_NHA_NAM_HT = "GNamHoanThanhXayDung16"
C_NHA_THOI_HAN = "HThoiHanSoHuuDen17"

# ---- UI: người nhận kết quả (Phần IV) — khớp theo NAME ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

# ---- Radio "Đề nghị (a/b/c)" — tick theo nhãn ----
L_DENGHI = "__DeNghiABC__"  # name ảo; FE dùng comp bn-radio + value = danh sách nhãn cần tick

UI_COMP_BY_NAME = {
    L_KINHGUI: "bn-input", L_HOTEN: "bn-input", L_GIAYTO: "bn-input", L_DIACHI: "bn-input",
    L_DIENTHOAI: "bn-input", L_DAT_DIACHI: "bn-input", L_DAT_DIENTICH: "bn-input",
    L_SD_CHUNG: "bn-input", L_SD_RIENG: "bn-input", L_MUCDICH: "bn-input", L_TUTHOIDIEM: "bn-input",
    L_THOIHAN: "bn-input", L_NGUONGOC: "bn-input", L_KT1: "bn-input", L_KT2: "bn-input",
    L_NOIKHAI: "bn-input",
    C_EMAIL: "bn-input", C_THUA_SO: "bn-input", C_TO_BAN_DO: "bn-input",
    C_NHA_LOAI: "bn-input", C_NHA_DT_XD: "bn-input", C_NHA_DT_SAN: "bn-input",
    C_NHA_SH_CHUNG: "bn-input", C_NHA_SH_RIENG: "bn-input", C_NHA_SO_TANG: "bn-input",
    C_NHA_TANG_NOI: "bn-input", C_NHA_TANG_HAM: "bn-input", C_NHA_NGUON_GOC: "bn-input",
    C_NHA_NAM_HT: "bn-input", C_NHA_THOI_HAN: "bn-input",
    N_HOTEN: "bn-input", N_CCCD: "bn-input", N_SDT: "bn-input", N_DIACHI: "bn-input",
    L_DENGHI: "bn-radio",
}
