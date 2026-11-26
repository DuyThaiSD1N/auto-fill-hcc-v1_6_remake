"""Compact schema cho "[Bắc Ninh] Xác nhận tiếp tục sử dụng đất nông nghiệp" (1.115462).

LLM chỉ trả FACT nguồn từ Đơn Mẫu 09 (kèm II. Xác nhận của UBND cấp xã), Giấy chứng nhận đã cấp, Giấy ủy quyền + lời
chứng chứng thực, CCCD. UI field điền vào e-form Bắc Ninh do ``mapper`` suy ra tất định.

Ô đơn khớp NAME ``element_<id>`` của eform 2869 (mapping 24/11/2026, cột "formcontrolname / field-key" — FE thêm tiền
tố portlet ``_org_bn_hoso_noptructuyen_``); khối người nhận kết quả và khối ủy quyền khớp NAME cố định của cổng.
"""

FIELDS: list[dict] = [
    # Đầu Đơn Mẫu 09.
    {"name": "Don_NoiKhai",
     "desc": 'Địa danh ở dòng ngày tháng đầu Đơn Mẫu 09 ("Văn Môn, ngày 09 tháng 11 năm 2026" → "Văn Môn"). Chỉ '
             "địa danh, không kèm ngày."},
    {"name": "Don_NgayKhai", "desc": "Ngày ghi ở dòng ngày tháng đầu Đơn Mẫu 09, dd/mm/yyyy."},
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan ghi sau "Kính gửi:" đầu Đơn Mẫu 09 (vd "Văn phòng đăng ký đất đai liên phường, xã Yên Phong"), '
             "nguyên văn."},
    {"name": "Don_NguoiSuDungDat",
     "desc": 'Họ tên ở mục "1. Người sử dụng đất" của Đơn, bỏ danh xưng "ông/bà". Viết hoa chữ đầu mỗi từ.'},
    {"name": "Don_GioiTinh",
     "desc": '"Nam" nếu mục "1. Người sử dụng đất" ghi danh xưng "ông", "Nữ" nếu ghi "bà". Không có danh xưng → bỏ.'},
    {"name": "Don_DiaChiLienHe",
     "desc": 'CHUỖI MỘT DÒNG chép NGUYÊN VĂN mục "2. Địa chỉ liên hệ (điện thoại, email...)" của Đơn, GIỮ cả phần '
             '"điện thoại: …", email nếu có. KHÔNG trả object.'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại ghi trong mục 2 của Đơn. Chỉ chữ số."},

    # Mục 3 — thửa đất. Nhiều thửa → MỘT chuỗi mỗi field, cùng thứ tự, ngăn bằng ", ".
    {"name": "Don_ThuaSo",
     "desc": 'Các "Thửa đất số" ở mục 3.1 của Đơn, theo đúng thứ tự dòng, ngăn bằng ", " (vd "59, 156, 43").'},
    {"name": "Don_ToBanDo",
     "desc": 'Các "Tờ bản đồ số" ở mục 3.1, CÙNG thứ tự với Don_ThuaSo, ngăn bằng ", " (vd "XV, XV, XVI"). Giữ số La '
             "Mã như trên giấy."},
    {"name": "Don_DienTich",
     "desc": 'Các "Diện tích (m2)" ở mục 3.1, CÙNG thứ tự với Don_ThuaSo, ngăn bằng ", " (vd "312, 336, 192").'},
    {"name": "Don_MucDich", "desc": 'Mục "Mục đích sử dụng đất" của Đơn, nguyên văn (vd "Canh tác").'},
    {"name": "Don_ThoiHan", "desc": 'Mục "Thời hạn sử dụng đất" của Đơn, nguyên văn (vd "tháng 10/2013").'},
    {"name": "Don_TaiSan", "desc": 'Mục "Tài sản gắn liền với đất hiện có" của Đơn, nguyên văn (vd "Không").'},
    {"name": "Don_DiaDiem",
     "desc": 'Mục "Địa điểm thửa đất/khu đất (tại xã..., tỉnh...)" của Đơn, NGUYÊN VĂN kể cả phần "(nay là …)".'},
    {"name": "Gcn_SoPhatHanh",
     "desc": 'Số phát hành Giấy chứng nhận đã cấp (mục 3.8 của Đơn "Số phát hành: N 859384", hoặc số in trên bìa GCN '
             '"Số N 859384"). Chép đúng chữ cái + số.'},
    {"name": "Gcn_SoVaoSo",
     "desc": 'Số vào sổ cấp Giấy chứng nhận đã cấp (mục 3.8 của Đơn, hoặc dòng "Vào sổ cấp giấy chứng nhận … Số" trên '
             "GCN). Ưu tiên cách viết ở Đơn. Chép đúng ký tự."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp Giấy chứng nhận đã cấp (mục 3.8 của Đơn hoặc ngày ký trên GCN), "
        "dd/mm/yyyy."},

    # Mục 4 — nội dung đề nghị.
    {"name": "Don_NoiDungDeNghi",
     "desc": 'Phần CHỮ ghi sau "4. Nội dung đề nghị xác nhận lại thời hạn sử dụng đất:" (trước "đến ngày"). Chỉ có '
             "dấu chấm → bỏ."},
    {"name": "Don_DenNgay", "desc": 'Số ngày viết ở chỗ "đến ngày …" của mục 4. Chỉ dấu chấm → bỏ.'},
    {"name": "Don_DenThang", "desc": 'Số tháng viết ở chỗ "tháng …" của mục 4 (thường viết tay). Chỉ dấu chấm → bỏ.'},
    {"name": "Don_DenNam", "desc": 'Năm viết ở chỗ "năm …" của mục 4 (thường viết tay, 4 chữ số). Chỉ dấu chấm → bỏ.'},

    # II. Xác nhận của UBND cấp xã (trang 2 của Đơn).
    {"name": "Xn_NoiDung",
     "desc": 'TOÀN BỘ nội dung xác nhận ở phần "II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ" (các đoạn dưới dòng hướng dẫn '
             'in nghiêng), nguyên văn, không cắt. KHÔNG lấy dòng hướng dẫn "(Nội dung xác nhận về tình trạng …)".'},
    {"name": "Xn_NgayXacNhan", "desc": 'Ngày ký phần xác nhận của UBND cấp xã ("Ngày 10 tháng 11 năm 2026"), '
        "dd/mm/yyyy."},

    # Chủ hồ sơ — cho khối người nhận kết quả.
    {"name": "ChuHoSo_SoDinhDanh",
     "desc": "Số CCCD/định danh của người sử dụng đất đứng Đơn (= BÊN ỦY QUYỀN của Giấy ủy quyền), lấy từ CCCD, "
             "Giấy ủy quyền hoặc lời chứng chứng thực. Chỉ chữ số. KHÔNG lấy số của bên được ủy quyền."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Don_NgayKhai", "Gcn_NgayCap", "Xn_NgayXacNhan"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"

# ---- purpose="authorized_person": khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*) ----
# Tài khoản đang nộp là người ĐƯỢC ủy quyền; khối này hỏi NGƯỜI ỦY QUYỀN = CHỦ HỒ SƠ = người sử dụng đất đứng Đơn.
FIELDS_UYQUYEN: list[dict] = [
    {"name": "ChuHoSo_HoTen",
     "desc": 'Họ tên CHỦ HỒ SƠ = "I. BÊN ỦY QUYỀN" của Giấy ủy quyền = người sử dụng đất đứng Đơn Mẫu 09. Chỉ họ tên, '
             "không kèm Ông/Bà. TUYỆT ĐỐI KHÔNG lấy BÊN ĐƯỢC ỦY QUYỀN."},
    {"name": "ChuHoSo_GioiTinh", "desc": '"Nam"/"Nữ" của chủ hồ sơ: theo CCCD, hoặc danh xưng "ông"/"bà" đứng trước '
        "tên ở Đơn / Giấy chứng nhận. Không rõ → bỏ."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh của chủ hồ sơ (CCCD, dòng 'Số CC/hộ chiếu số' của bên ủy "
        "quyền, lời chứng chứng thực). Chỉ chữ số."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy (CCCD hoặc dòng 'Năm sinh' của bên ủy quyền "
        "nếu ghi đủ ngày). Chỉ có năm → bỏ."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ hồ sơ, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "ChuHoSo_NoiCap",
     "desc": 'Nơi cấp CCCD của chủ hồ sơ ("Cục cảnh sát…" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ '
             'căn cước mới / "Bộ Công an" → "Bộ Công an"). Bỏ nếu không có.'},
    {"name": "ChuHoSo_ThuongTru",
     "desc": "Nơi thường trú của chủ hồ sơ, object {quocGia,tinh,xa,chiTietDuoiXa} theo TÊN HÀNH CHÍNH HIỆN HÀNH: "
             "tinh=tỉnh/thành, xa=phường/xã, chiTietDuoiXa=thôn/tổ dân phố/số nhà."},
    {"name": "ChuHoSo_DienThoai", "desc": "SĐT chủ hồ sơ (mục 2 Địa chỉ liên hệ của Đơn, hoặc dòng Điện thoại của bên "
        "ủy quyền). Chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email chủ hồ sơ nếu giấy tờ ghi rõ; thường không có → bỏ."},
]
ALLOWED_UYQUYEN = {f["name"] for f in FIELDS_UYQUYEN}
COMPACT_COMP_UYQUYEN = {name: "x-input" for name in ALLOWED_UYQUYEN}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap"):
    COMPACT_COMP_UYQUYEN[_name] = "x-date"
COMPACT_COMP_UYQUYEN["ChuHoSo_ThuongTru"] = "x-select-area"

# ---- UI thân đơn Mẫu 09 — NAME element_<id> của eform 2869 (mapping 24/11/2026) ----
E_NOI_KHAI = "element_77320"        # Nơi khai hồ sơ (cổng điền sẵn "Bắc Ninh")
E_NGAY_KHAI = "element_77321"       # Ngày khai hồ sơ (datepicker, cổng điền sẵn ngày hôm nay)
E_KINH_GUI = "element_77323"
E_DIA_CHI = "element_77325"         # 2. Địa chỉ liên hệ (điện thoại, email...)
E_THUA_SO = "element_77327"         # 3.1 Thửa đất số
E_TO_BAN_DO = "element_77328"       # 3.2 Tờ bản đồ số
E_DIEN_TICH = "element_77329"       # 3.3 Diện tích đất (m2)
E_MUC_DICH = "element_77330"        # 3.4
E_THOI_HAN = "element_77331"        # 3.5
E_TAI_SAN = "element_77332"         # 3.6
E_DIA_DIEM = "element_77333"        # 3.7
E_SO_PHAT_HANH = "element_77335"    # 3.8 Số phát hành
E_SO_VAO_SO = "element_77336"
E_NGAY_CAP_GCN = "element_77337"
E_NOI_DUNG = "element_77338"        # 4. Nội dung đề nghị
E_DEN_NGAY = "element_77339"
E_DEN_THANG = "element_77340"
E_DEN_NAM = "element_77341"
E_XN_NOI_DUNG = "element_77344"     # II. Xác nhận của UBND cấp xã (input 1 dòng)
E_XN_NGAY = "element_77347"         # Ngày xác nhận (datepicker)
# Không phát: element_77346 "Nơi xác nhận" (giấy không ghi địa danh, cổng điền sẵn "Bắc Ninh"). Mục "1. Người sử dụng
# đất" trên eform chỉ là nhãn, không có ô — họ tên chủ hồ sơ đi vào khối ủy quyền / người nhận kết quả.

# ---- Người nhận kết quả tại nhà (khớp NAME; khối chỉ hiện khi chọn VNPOST) = chủ hồ sơ ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

UI_COMP_BY_NAME = {
    name: "bn-input"
    for name in (
        E_NOI_KHAI, E_NGAY_KHAI, E_KINH_GUI, E_DIA_CHI, E_THUA_SO, E_TO_BAN_DO, E_DIEN_TICH, E_MUC_DICH, E_THOI_HAN,
        E_TAI_SAN, E_DIA_DIEM, E_SO_PHAT_HANH, E_SO_VAO_SO, E_NGAY_CAP_GCN, E_NOI_DUNG, E_DEN_NGAY, E_DEN_THANG,
        E_DEN_NAM, E_XN_NOI_DUNG, E_XN_NGAY, N_HOTEN, N_CCCD, N_SDT, N_DIACHI,
    )
}

# Loại "Người ủy quyền là:" — chủ hồ sơ từ đủ 60 tuổi chọn "Người cao tuổi" (theo mapping); không thì loại mặc định
# của registry ("Cá nhân khác là Công dân Việt Nam").
SUBJECT_NGUOI_CAO_TUOI = "Người cao tuổi"
TUOI_CAO_TUOI = 60
