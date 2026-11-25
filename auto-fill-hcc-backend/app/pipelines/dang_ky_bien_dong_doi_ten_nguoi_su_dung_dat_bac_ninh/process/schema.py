"""Compact schema cho "[Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất" (1.115460).

LLM chỉ trả FACT nguồn từ CCCD + Đơn đăng ký biến động (Mẫu số 18 / Mẫu số 24, có thể hai người đồng sử dụng) +
Văn bản cam kết của các thành viên hộ gia đình. UI field điền vào e-form Bắc Ninh do `mapper.enrich` suy ra tất định
theo file mapping Excel 25/11/2026.

Ô đơn khớp CLASS eform-element-<Key> (crawl DOM 21/11/2026 — trùng bộ khoá Mẫu 18 của 1.115465); nơi / ngày khai, ô
người nhận và khối ủy quyền khớp NAME (id DOM _org_bn_hoso_noptructuyen_<name>).
"""

FIELDS: list[dict] = [
    # Người THỨ NHẤT đứng đơn = người sử dụng đất (mục "- Tên" Mẫu 18 / "1.1. Tên Ông/Bà" Mẫu 24), thông tin HIỆN TẠI.
    {"name": "Cccd_HoTen", "desc": "Họ và tên người THỨ NHẤT đứng Đơn (dòng '- Tên' Mẫu 18 / '1.1. Tên Ông/Bà' Mẫu 24) "
        "theo thông tin HIỆN TẠI — lấy từ CCCD của chính người đó hoặc từ Đơn. KHÔNG lấy tên cũ in trên Giấy chứng "
        "nhận nếu đã đổi tên. Không kèm Ông/Bà."},
    {"name": "Don_DanhXung", "desc": 'Danh xưng in/viết RIÊNG trước tên người thứ nhất trên Đơn ("Tên Ông:" → "Ông", '
        '"Tên Bà:" → "Bà"). Dòng in sẵn "Ông, bà" / không có → bỏ.'},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD HIỆN TẠI của người THỨ NHẤT đứng đơn; đọc CCCD (mặt trước, "
        "MRZ mặt sau) hoặc dòng 'Giấy tờ nhân thân/pháp nhân' của Đơn. KHÔNG lấy số CMND cũ in trên Giấy chứng nhận. "
        "Chỉ chữ số."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD của người thứ nhất (mặt sau CCCD, hoặc văn bản cam kết / lời chứng "
        "thực ghi rõ 'cấp ngày …' cho đúng người đó), dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD của người thứ nhất. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về '
             'trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người THỨ NHẤT đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng '- Địa chỉ' / '- Địa chỉ "
             "thường trú' của người đó trên Đơn. PHẢI giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object, "
             "KHÔNG bỏ phường/xã."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ của người thứ nhất trên Đơn (dòng 'Điện thoại liên hệ'). "
        "Chỉ chữ số; dòng chỉ có dấu chấm → bỏ."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử của người thứ nhất trên Đơn. Trống → bỏ."},

    # Người THỨ HAI đứng đơn (đồng sử dụng: mục "1.2. Tên Bà/Ông" Mẫu 24, hoặc dòng "- Tên" thứ hai). Không có → bỏ.
    {"name": "Don2_DanhXung", "desc": 'Danh xưng trước tên người THỨ HAI trên Đơn ("Tên Bà:" → "Bà", "Tên Ông:" → '
        '"Ông"). Đơn chỉ có một người → bỏ.'},
    {"name": "Don2_HoTen", "desc": "Họ và tên người THỨ HAI đứng Đơn (mục 1.2 Mẫu 24 / dòng '- Tên' thứ hai), không kèm "
        "Ông/Bà. Đơn chỉ có một người → bỏ."},
    {"name": "Don2_SoGiayTo", "desc": "Số CCCD/định danh của người THỨ HAI (dòng 'Giấy tờ nhân thân/pháp nhân' của người "
        "đó, hoặc CCCD của chính người đó). Chỉ chữ số."},
    {"name": "Don2_DiaChi", "desc": "Địa chỉ người THỨ HAI — CHUỖI MỘT DÒNG nguyên văn như Don_DiaChi (không trả "
        "object)."},
    {"name": "Don2_DienThoai", "desc": "Số điện thoại người THỨ HAI trên Đơn. Chỉ chữ số; chỉ có dấu chấm → bỏ."},
    {"name": "Don2_Email", "desc": "Hộp thư điện tử người THỨ HAI trên Đơn. Trống → bỏ."},

    # Đơn đăng ký biến động đất đai (Mẫu số 18 / Mẫu số 24) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn (vd "Văn phòng đăng ký đất đai tỉnh Bắc Ninh"). Bỏ ký '
             'hiệu chú thích "(1)".'},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế ghi trên Đơn (dòng 'Mã số thuế (nếu có)'). Chỉ chữ số. Đơn để trống → "
        "bỏ, KHÔNG tự lấy số CCCD."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Mục "Nội dung biến động" của Đơn ("II." Mẫu 18 / "2." Mẫu 24), NGUYÊN VĂN, giữ các gạch đầu dòng và xuống '
             'dòng (vd "- Thay đổi số CMND 125xxxxxx thành số CCCD 027xxxxxxxxx", "Thay đổi Hộ"). CHỈ lấy từ Đơn. '
             "Trống → bỏ."},
    {"name": "Don_MienGiam",
     "desc": 'Mục "III. Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính" của Đơn, NGUYÊN VĂN. Trống → bỏ.'},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ nộp kèm "(2) ..." ở mục giấy tờ nộp kèm của Đơn ("IV." Mẫu 18 / "3." Mẫu 24). Bỏ nếu trống. '
             'KHÔNG lấy dòng in sẵn "(1) Giấy chứng nhận đã cấp".'},
    {"name": "Don_GiayTo3", "desc": 'Giấy tờ nộp kèm "(3) ..." của Đơn. Bỏ nếu trống.'},
    {"name": "Don_ThanhVienHo",
     "desc": 'Mục V "(1) Thành viên hộ gia đình" của Đơn, NGUYÊN VĂN. Trống → bỏ.'},
    {"name": "Don_TranhChap",
     "desc": 'Mục V "(2) Tình trạng tranh chấp đất đai" của Đơn, NGUYÊN VĂN. Trống → bỏ.'},
    {"name": "Don_RanhGioi",
     "desc": 'Mục V "(3) Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận" của Đơn, NGUYÊN VĂN. Trống → '
             "bỏ."},
    {"name": "Don_NoiKhai", "desc": 'Địa danh trước ", ngày … tháng … năm …" ở chỗ ký của Đơn (trên chữ "Người viết '
        'đơn"). Chỉ có dấu chấm → bỏ.'},
    {"name": "Don_NgayKhai", "desc": 'Ngày ký Đơn ở dòng ", ngày … tháng … năm …" trên chữ "Người viết đơn", dd/mm/yyyy '
        "(số viết tay). Thiếu ngày / tháng / năm → bỏ."},

    # Văn bản cam kết / thỏa thuận của các thành viên hộ gia đình có chung quyền sử dụng đất (nộp kèm, có chứng thực).
    {"name": "Vbck_TieuDe",
     "desc": 'Tên văn bản cam kết / thỏa thuận / xác nhận của các thành viên hộ gia đình nộp kèm — ghép tiêu đề với dòng '
             'phụ đề ngay dưới (vd "VĂN BẢN CAM KẾT" + "Của các thành viên hộ gia đình có chung quyền sử dụng đất" → '
             '"Văn bản cam kết của các thành viên hộ gia đình có chung quyền sử dụng đất"). Không có văn bản → bỏ.'},
    {"name": "Vbck_ChungThuc",
     "desc": 'Lời chứng thực / công chứng của văn bản cam kết đó, gọn MỘT cụm: "chứng thực chữ ký[, điểm chỉ] ngày '
             'dd/mm/yyyy tại <tên cơ quan / văn phòng công chứng, tỉnh>". Không có → bỏ.'},
    {"name": "Vbck_ThanhVien",
     "desc": 'MẢNG các thành viên hộ gia đình liệt kê ở đầu văn bản cam kết, ĐÚNG thứ tự 1, 2, 3…: [{"danhXung":"Ông" | '
             '"Bà","hoTen":"…","ngaySinh":"dd/mm/yyyy","soDinhDanh":"chỉ chữ số","thuongTru":"chuỗi một dòng nguyên '
             'văn"}]. Thiếu thông tin nào thì bỏ khoá đó. Không có văn bản → bỏ.'},
    {"name": "Vbck_TranhChap",
     "desc": 'Câu cam kết về tranh chấp trong văn bản cam kết, NGUYÊN VĂN, bỏ gạch đầu dòng (vd "Không có bất cứ tranh '
             'chấp khiếu nại, khiếu kiện gì"). Không có → bỏ.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgayCap", "Don_NgayKhai"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"

# ---- purpose="authorized_person": khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*) ----
# Tài khoản đang nộp là người ĐƯỢC ủy quyền (người nộp thay); khối này hỏi NGƯỜI ỦY QUYỀN = CHỦ HỒ SƠ = người đứng
# Đơn Mẫu 18. Loại đối tượng mặc định "Cá nhân khác là Công dân Việt Nam".
FIELDS_UYQUYEN: list[dict] = [
    {"name": "ChuHoSo_HoTen",
     "desc": 'Họ tên CHỦ HỒ SƠ = người THỨ NHẤT đứng Đơn (dòng "- Tên" Mẫu 18 / "1.1. Tên Ông/Bà" Mẫu 24), theo tên '
             'HIỆN TẠI; có Giấy ủy quyền thì là '
             'BÊN ỦY QUYỀN (bên A). Chỉ họ tên, không kèm Ông/Bà, năm sinh. TUYỆT ĐỐI KHÔNG lấy bên ĐƯỢC ủy quyền (bên B).'},
    {"name": "ChuHoSo_GioiTinh", "desc": '"Nam"/"Nữ" của chủ hồ sơ, CHỈ khi giấy tờ ghi rõ (CCCD, giấy xác nhận thông '
             'tin cư trú) hoặc ghi "Ông"/"Bà" riêng (không phải "Ông, bà:" in sẵn). Không rõ → bỏ.'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh HIỆN TẠI của chủ hồ sơ, chỉ chữ số (không lấy CMND cũ "
        "in trên Giấy chứng nhận)."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy (CCCD / giấy xác nhận / văn bản cam kết ghi "
        "'Sinh ngày' cho đúng người đó). Chỉ có năm → bỏ."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ hồ sơ, dd/mm/yyyy (mặt sau CCCD, hoặc văn bản cam kết / "
        "lời chứng thực ghi 'cấp ngày …' cho đúng người đó). Bỏ nếu không có."},
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

# ---- UI thân đơn Mẫu 18 — khớp CLASS eform-element-<Key>, name = KEY (crawl 21/11/2026) ----
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
# Nơi / ngày khai của người viết đơn: class NoiKhaiHoSo / NgayKhaiHoSo TRÙNG ô phần UBND xác nhận → khớp NAME
# element_<id> của eform 2867 (mapping Excel 25/11/2026). Cổng điền sẵn "Bắc Ninh" + ngày hôm nay; chỉ phát khi Đơn ghi.
# Không phát: element_77279/77281/77282 (phần UBND cấp xã xác nhận).
E_NOI_KHAI = "element_77275"
E_NGAY_KHAI = "element_77276"

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
    E_NOI_KHAI: "bn-input",
    E_NGAY_KHAI: "bn-input",
    N_HOTEN: "bn-input",
    N_CCCD: "bn-input",
    N_SDT: "bn-input",
    N_DIACHI: "bn-input",
}

# Loại "Người ủy quyền là:" — chủ hồ sơ từ đủ 60 tuổi chọn "Người cao tuổi" (sheet "UQ - Người cao tuổi" của mapping);
# không thì loại mặc định của registry ("Cá nhân khác là Công dân Việt Nam").
SUBJECT_NGUOI_CAO_TUOI = "Người cao tuổi"
TUOI_CAO_TUOI = 60
