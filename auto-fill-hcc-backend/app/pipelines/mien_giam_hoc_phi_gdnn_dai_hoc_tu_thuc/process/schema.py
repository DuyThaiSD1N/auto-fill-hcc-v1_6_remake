"""Compact schema cho "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã 1.014335, cổng DVC Bộ
GD&ĐT dvc.moet.gov.vn, Form.io). Field-key theo Mapping_Mien_giam_hoc_phi_GDNN_BoGDDT.xlsx, TẤT CẢ PHẲNG data[...].

HAI người, TÁCH RIÊNG:
- SinhVien_* : HỌC SINH, SINH VIÊN được miễn giảm = CHỦ HỒ SƠ. Nguồn: Đơn PL IV, Giấy xác nhận của trường (mẫu
  Phụ lục V hoặc mẫu riêng), CCCD, Giấy khai sinh, Bằng tốt nghiệp. SinhVien_HoTen là NEO.
- NguoiNop_* : NGƯỜI NỘP khi KHÔNG phải sinh viên (thường là cha/mẹ) — từ CCCD mang tên khác sinh viên hoặc
  Giấy tiếp nhận hồ sơ. Sinh viên tự nộp → bỏ trống.

Cấu trúc form:
- Phần I   Người nộp: data[chonDoiTuong]/[fullname]/[identityNumber]/[birthday] KHOÁ (cổng đổ từ tài khoản) → không
  điền. Ô sửa được: gender, identityDate, idIssuePlace, email, province, district, address, phoneNumber.
  Nút data[isOwnerDossier] KHÔNG đụng tới (giống cap_ban_sao_van_bang_so_goc cùng cổng).
- Phần II  data[ChuHS] = "Cá nhân" + data[owner...] = sinh viên.
- Phần III panel Đơn PL IV: data[province2] (Tỉnh xử lý — option KHÔNG có tiền tố "Tỉnh"), data[d] (ngày viết
  đơn), data[KinhGui], data[TenChaMe], data[Lop], data[Khoa1] (Khóa), data[DoiTuong], data[Khoa2] (Khoa),
  Nơi sinh data[TinhThanhPho]/[QuanHuyen]/[SoNhaDuong], Nơi thường trú data[TinhThanhPho1]/[QuanHuyen1]/
  [SoNhaDuong1].
"""

# Giấy tờ của thủ tục đều 1-2 trang (Bằng tốt nghiệp 2 trang). Bước đính kèm cắt CÙNG số trang để trúng cache OCR.
OCR_MAX_PAGES = 4

# Địa chỉ trên CCCD/Giấy khai sinh thường là địa danh CŨ 3 cấp → giữ cấp huyện ở khoá "huyen" để mapper quy đổi.
_AREA_DESC = ("object {quocGia,tinh,huyen,xa,diaChi,fullText}. tinh=tỉnh/thành phố; huyen=quận/huyện/thị xã/thành "
              "phố thuộc tỉnh NẾU giấy ghi (địa danh cũ — giữ nguyên để quy đổi); xa=phường/xã/thị trấn; diaChi=số "
              "nhà/đường/thôn/tổ dân phố hoặc tên cơ sở (bệnh viện, trạm y tế); fullText=nguyên văn dòng địa chỉ. "
              "Chép đúng địa danh trên giấy, KHÔNG tự đổi sang tên sau sáp nhập.")

FIELDS: list[dict] = [
    # A. HỌC SINH, SINH VIÊN (chủ hồ sơ).
    {"name": "SinhVien_HoTen", "desc": "Họ tên HỌC SINH, SINH VIÊN được miễn, giảm học phí — Đơn PL IV 'Họ và tên', "
        "Giấy xác nhận 'Xác nhận anh/chị'/'xác nhận sinh viên', CCCD, Giấy khai sinh. ĐÂY LÀ NEO. KHÔNG lấy tên "
        "cha/mẹ hay người nộp hồ sơ."},
    {"name": "SinhVien_NgaySinh", "desc": "Ngày sinh sinh viên, dd/mm/yyyy (CCCD / Giấy khai sinh / Đơn / Giấy xác nhận)."},
    {"name": "SinhVien_GioiTinh", "desc": 'Giới tính sinh viên: "Nam"/"Nữ" (CCCD / Giấy khai sinh / Bằng tốt nghiệp).'},
    {"name": "SinhVien_SoDinhDanh", "desc": "Số CCCD 12 chữ số của sinh viên (CCCD 'Số / No.'; Đơn/Giấy xác nhận hay "
        "ghi có dấu chấm '06.8306…' → chỉ lấy chữ số). Lệch nhau → LẤY THEO CCCD."},
    {"name": "SinhVien_NgayCap", "desc": "Ngày cấp CCCD sinh viên (mặt sau 'Ngày, tháng, năm / Date, month, year'), "
        "dd/mm/yyyy. KHÔNG lấy ngày chứng thực bản sao."},
    {"name": "SinhVien_NoiCap", "desc": "Nơi cấp CCCD sinh viên theo chức danh người ký mặt sau (vd 'Cục Cảnh sát "
        "quản lý hành chính về trật tự xã hội'). KHÔNG lấy văn phòng công chứng/UBND chứng thực bản sao."},
    {"name": "SinhVien_QuocTich", "desc": 'Quốc tịch sinh viên (CCCD/Giấy khai sinh). Mặc định "Việt Nam".'},
    {"name": "SinhVien_DienThoai", "desc": "Số điện thoại CỦA SINH VIÊN nếu giấy tờ ghi rõ. Chỉ chữ số."},
    {"name": "SinhVien_Email", "desc": "Email sinh viên nếu giấy tờ ghi rõ."},
    {"name": "SinhVien_ThuongTru", "desc": "Nơi thường trú HIỆN NAY của sinh viên theo Đơn PL IV 'Nơi thường trú (ghi "
        "đầy đủ)' hoặc Giấy xác nhận của trường 'Hộ khẩu thường trú', " + _AREA_DESC},
    {"name": "SinhVien_ThuongTruCCCD", "desc": "Nơi thường trú IN TRÊN CCCD của sinh viên ('Nơi thường trú / Place of "
        "residence'), " + _AREA_DESC},
    {"name": "SinhVien_NoiSinh", "desc": "NƠI SINH của sinh viên, " + _AREA_DESC + " ƯU TIÊN Giấy khai sinh 'Nơi "
        "sinh' (vd 'Bệnh viện Đa khoa, tỉnh X' → diaChi='Bệnh viện Đa khoa', tinh='X'), rồi Bằng tốt nghiệp, rồi "
        "Đơn PL IV. KHÔNG lấy 'Quê quán' của CCCD/Giấy khai sinh."},

    # B. Đơn đề nghị Phụ lục IV + Giấy xác nhận của trường.
    {"name": "Don_KinhGui", "desc": "Cơ sở giáo dục ở dòng 'Kính gửi' của Đơn PL IV (vd 'Trường Cao đẳng Mẫu')."},
    {"name": "Truong_Ten", "desc": "Tên trường/cơ sở giáo dục nơi sinh viên đang học — Giấy xác nhận ('Trường: …', "
        "'Trường … xác nhận sinh viên') hoặc Dự toán PL VI ('Tên cơ sở giáo dục nghề nghiệp')."},
    {"name": "Don_Lop", "desc": "Lớp (Đơn PL IV / Giấy xác nhận 'Lớp'), chép nguyên văn."},
    {"name": "Don_NienKhoa", "desc": "KHÓA HỌC dạng năm (Đơn PL IV 'Khóa' / Giấy xác nhận 'Khóa'/'Khóa học'), vd "
        "'2024 - 2027'. KHÔNG nhầm với 'Khoa' (tên khoa) hay 'Khóa thi' trên Bằng tốt nghiệp."},
    {"name": "Don_Khoa", "desc": "KHOA (đơn vị đào tạo) — Đơn PL IV / Giấy xác nhận 'Khoa', vd 'Dược'."},
    {"name": "Don_HoTenChaMe", "desc": "Đơn PL IV 'Họ tên cha/mẹ học sinh, sinh viên' — chép nguyên văn."},
    {"name": "Don_DoiTuong", "desc": "Đơn PL IV dòng 'Thuộc đối tượng:' — chép NGUYÊN VĂN cả câu."},
    {"name": "GiayXacNhan_DoiTuong", "desc": "Giấy xác nhận của trường dòng 'Thuộc đối tượng:' — chép NGUYÊN VĂN."},
    {"name": "Don_NgayLam", "desc": "Ngày viết Đơn PL IV ('…, ngày … tháng … năm …' cuối đơn), dd/mm/yyyy. Đơn "
        "không ghi đủ ngày → bỏ."},

    # C. Giấy khai sinh — cha/mẹ (dự phòng ô 'Họ tên cha/mẹ' + nhận ra người nộp là cha hay mẹ).
    {"name": "KhaiSinh_HoTenCha", "desc": "Giấy khai sinh 'Họ, chữ đệm, tên người cha'."},
    {"name": "KhaiSinh_HoTenMe", "desc": "Giấy khai sinh 'Họ, chữ đệm, tên người mẹ'."},

    # D. NGƯỜI NỘP khi KHÔNG phải sinh viên.
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ khi KHÔNG phải sinh viên — CCCD mang tên KHÁC sinh "
        "viên, hoặc Giấy tiếp nhận hồ sơ 'Cá nhân/Tổ chức/Doanh nghiệp'. Sinh viên tự nộp → bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/số định danh NGƯỜI NỘP (CCCD người nộp / Giấy tiếp nhận 'Số định "
        "danh cá nhân'). Chỉ chữ số."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP theo CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD NGƯỜI NỘP (như SinhVien_NoiCap)."},
    {"name": "NguoiNop_ThuongTru", "desc": "Nơi thường trú NGƯỜI NỘP (CCCD người nộp / Giấy tiếp nhận 'Địa chỉ'), "
        + _AREA_DESC},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP (Giấy tiếp nhận 'Số điện thoại'). Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("SinhVien_NgaySinh", "SinhVien_NgayCap", "Don_NgayLam", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("SinhVien_ThuongTru", "SinhVien_ThuongTruCCCD", "SinhVien_NoiSinh", "NguoiNop_ThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP (fullname/identityNumber/birthday/chonDoiTuong khoá — không điền) -----
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-select",
    "data[email]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",

    # ----- Phần II: CHỦ HỒ SƠ = sinh viên -----
    "data[ChuHS]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerBirthday]": "dom-date",
    "data[ownerIdentityAgency22]": "dom-select",
    "data[ownerNation]": "dom-select",
    "data[ownerEmail]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[tenHoSo]": "dom-input",  # "Ghi chú"

    # ----- Phần III: Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV) -----
    "data[province2]": "dom-select",  # Tỉnh/thành phố xử lý — option không tiền tố ("Lâm Đồng")
    "data[d]": "dom-date",            # Ngày viết đơn
    "data[KinhGui]": "dom-input",
    "data[TenChaMe]": "dom-input",
    "data[Lop]": "dom-input",
    "data[Khoa1]": "dom-input",       # Khóa (niên khóa)
    "data[DoiTuong]": "dom-input",
    "data[Khoa2]": "dom-input",       # Khoa
    "data[TinhThanhPho]": "dom-select",   # Nơi sinh — Tỉnh
    "data[QuanHuyen]": "dom-select",      # Nơi sinh — Phường/Xã
    "data[SoNhaDuong]": "dom-input",      # Nơi sinh — Số nhà, đường
    "data[TinhThanhPho1]": "dom-select",  # Nơi thường trú — Tỉnh
    "data[QuanHuyen1]": "dom-select",     # Nơi thường trú — Phường/Xã
    "data[SoNhaDuong1]": "dom-input",     # Nơi thường trú — Số nhà, đường
}
