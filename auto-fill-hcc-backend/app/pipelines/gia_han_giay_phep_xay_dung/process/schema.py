"""Compact schema cho "Gia hạn giấy phép xây dựng" (mã 1.013227, cổng Bộ Xây dựng dvc.moc.gov.vn, Form.io).

CÙNG khối người nộp / tổ chức người nộp / chủ hộ-chủ đầu tư với dieu_chinh_giay_phep_xay_dung, NHƯNG tờ
đơn gia hạn dùng bộ field-key KHÁC (theo mapping-gia-han-GPXD-Bo-Xay-dung.xlsx):
- Kính gửi: data[recipient].
- Địa điểm xây dựng: data[lotNumber] (Lô đất số), data[landArea] (chỉ số + dấu chấm), data[locationAt]
  (Tại — thửa đất), data[street] (đường), data[province] LẦN 2 + data[phuongxaaa] (Tỉnh/Phường của lô đất).
- GPXD đã cấp: data[existingPermitNumber] / data[NgayCap] / data[existingPermitAuthority] /
  data[existingPermitContent].
- Nội dung đề nghị: data[requestType] = "Gia hạn Giấy phép xây dựng" mở ô data[extensionReason].
- data[estimatedCompletionMonths] (số tháng), data[commitment] (cam kết), data[tinhthanhqwaasa] (Tỉnh nơi
  làm đơn), data[KyGhiRoHoTen] (ký, ghi rõ họ tên).
"""

# Đơn 1 trang + CCCD 2 mặt / GPXD 3 trang / GCN 3 trang (mục IV chuyển nhượng ở trang 3) → 4 trang đầu đủ.
# Bước đính kèm cắt CÙNG số trang để trúng cache OCR của bước điền.
OCR_MAX_PAGES = 4

FIELDS: list[dict] = [
    # A. NGƯỜI NỘP HỒ SƠ. Form chỉ có MỘT ô người nộp; đơn đứng tên hai vợ chồng → người đứng ĐẦU (người
    # ký/nộp), người còn lại chỉ ghi ở tên chủ hộ.
    {"name": "Applicant_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ. Có Giấy ủy quyền → bên được ủy quyền. Không "
        "có → người ĐỨNG ĐẦU trong mục 'Tên chủ đầu tư (Chủ hộ)' của Đơn (đơn ghi 2 người thì lấy người thứ "
        "nhất), chỉ MỘT người."},
    {"name": "Applicant_NgaySinh", "desc": "Ngày sinh người nộp theo CCCD, dd/mm/yyyy. Không trả chỉ năm sinh vào field này."},
    {"name": "Applicant_NamSinh", "desc": "Năm sinh người nộp nếu chỉ đọc được năm (vd GCN QSDĐ ghi 'Sinh năm')."},
    {"name": "Applicant_GioiTinh", "desc": 'Giới tính người nộp theo CCCD: "Nam" hoặc "Nữ".'},
    {"name": "Applicant_SoDinhDanh", "desc": "Số CCCD 12 số của NGƯỜI NỘP. Lệch giữa CCCD và GPXD/Đơn → LẤY "
        "THEO CCCD. Không lấy số CMND cũ 9 số khi đã có CCCD."},
    {"name": "Applicant_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP (mặt sau CCCD), dd/mm/yyyy."},
    {"name": "Applicant_NoiCap", "desc": "Nơi cấp CCCD của NGƯỜI NỘP (mặt sau, vd 'Cục Cảnh sát quản lý hành "
        "chính về trật tự xã hội')."},
    {"name": "Applicant_DienThoai", "desc": "Số điện thoại người nộp (dòng 'Số điện thoại' trên Đơn)."},
    {"name": "Applicant_Email", "desc": "Email người nộp nếu giấy tờ ghi rõ."},
    {"name": "Applicant_NoiCuTru", "desc": "Nơi THƯỜNG TRÚ của NGƯỜI NỘP theo CCCD (hoặc 'Địa chỉ' của người "
        "đó trên GPXD), object {quocGia,tinh,xa,chiTietDuoiXa,fullText}. KHÔNG lấy địa chỉ lô đất xây dựng."},

    # B. Kính gửi + CHỦ ĐẦU TƯ/CHỦ HỘ.
    {"name": "Don_KinhGui", "desc": "Cơ quan 'Kính gửi' trên Đơn (thường là cơ quan đã cấp GPXD), vd "
        "'UBND phường Mẫu'."},
    {"name": "ChuDauTu_Loai", "desc": '"Chủ hộ" nếu chủ đầu tư là cá nhân/hộ gia đình; "Chủ đầu tư" nếu tổ chức.'},
    {"name": "ChuHo_HoTen", "desc": "Tên CHỦ HỘ/CHỦ ĐẦU TƯ cá nhân đứng tên công trình — mục 'Tên chủ đầu tư "
        "(Chủ hộ)' trên Đơn / 'Cấp cho' trên GPXD. Hai vợ chồng thì ghi ĐỦ cả hai, nối ' - ' (vd 'Trần Văn "
        "Bình - Lê Thị Hoa')."},
    {"name": "ChuHo_SoDinhDanh", "desc": "Số CCCD của chủ hộ. Hai người → ghi CẢ HAI số theo đúng thứ tự tên, "
        "nối ' - '. Lệch giữa CCCD và GPXD → LẤY THEO CCCD."},
    {"name": "ChuHo_DienThoai", "desc": "Số điện thoại chủ hộ/chủ đầu tư (dòng 'Số điện thoại' trên Đơn)."},
    {"name": "ChuDauTu_TenToChuc", "desc": "Tên tổ chức chủ đầu tư nếu chủ đầu tư là tổ chức/doanh nghiệp."},
    {"name": "ChuDauTu_NguoiDaiDien", "desc": "Người đại diện của tổ chức chủ đầu tư (mục 'Người đại diện' trên Đơn)."},
    {"name": "ChuDauTu_ChucVu", "desc": "Chức vụ người đại diện chủ đầu tư (mục 'Chức vụ' trên Đơn)."},
    {"name": "ChuDauTu_MaSoDoanhNghiep", "desc": "Mã số doanh nghiệp của tổ chức CHỦ ĐẦU TƯ (10 chữ số)."},

    # C. Tổ chức NGƯỜI NỘP (chỉ khi chủ đầu tư là tổ chức tự đứng nộp).
    {"name": "ToChucNop_Ten", "desc": "Tên doanh nghiệp NGƯỜI NỘP (chỉ khi CHỦ ĐẦU TƯ là tổ chức tự đứng nộp)."},
    {"name": "ToChucNop_MaSoThue", "desc": "Mã số doanh nghiệp/Mã số thuế của tổ chức người nộp (10 chữ số)."},
    {"name": "ToChucNop_DiaChi", "desc": "Địa chỉ trụ sở tổ chức người nộp, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "ToChucNop_DienThoai", "desc": "Số điện thoại của tổ chức người nộp."},

    # D. Địa điểm xây dựng (mục 2 của Đơn).
    {"name": "Dat_DiaDiemXayDung", "desc": "TỈNH và PHƯỜNG/XÃ của LÔ ĐẤT xây dựng (mục 2 Đơn: 'phường (xã)', "
        "'tỉnh, thành phố'; hoặc vị trí xây dựng trên GPXD), object {quocGia,tinh,xa,chiTietDuoiXa,fullText}. Ưu tiên "
        "tên phường/xã HIỆN HÀNH (GPXD/Đơn mới) thay cho tên cũ trên GCN. KHÁC nơi cư trú người nộp."},
    {"name": "Dat_LoDatSo", "desc": "Giá trị dòng 'Lô đất số' trên Đơn (thường ghi số phát hành GCN QSDĐ, vd "
        "'AB 123456'). Đơn để trống thì lấy số phát hành GCN QSDĐ."},
    {"name": "Dat_ThuaDatSo", "desc": "Thửa đất số (vd '120 (gốc 45)'), lấy trên Đơn/GPXD/GCN."},
    {"name": "Dat_ToBanDoSo", "desc": "Tờ bản đồ số (vd '7 (12b)')."},
    {"name": "Dat_DienTich", "desc": "Diện tích lô đất, m2, chỉ trả số (vd 150,5 → 150.5)."},
    {"name": "Dat_DuongPho", "desc": "Tên đường/phố của lô đất nếu có THẬT. Đơn ghi tờ bản đồ vào ô 'đường' "
        "thì KHÔNG trả ở đây (đã có Dat_ToBanDoSo)."},

    # E. Giấy phép xây dựng đã được cấp (mục 3 của Đơn + chính GPXD).
    {"name": "GPXD_So", "desc": "Số Giấy phép xây dựng đã cấp (vd '15/GPXD'), lấy trên GPXD hoặc mục 3 Đơn."},
    {"name": "GPXD_NgayCap", "desc": "Ngày cấp GPXD, dd/mm/yyyy (dòng '…, ngày … tháng … năm …' đầu GPXD)."},
    {"name": "GPXD_CoQuanCap", "desc": "Cơ quan đã cấp GPXD (vd 'UBND phường Mẫu')."},
    {"name": "GPXD_NoiDung", "desc": "Nội dung Giấy phép đã cấp — dòng 'Nội dung Giấy phép' ở mục 3 Đơn (cấp "
        "công trình, diện tích xây dựng tầng 1, tổng diện tích sàn…); bổ sung thông số chính ở mục 2 GPXD (loại/"
        "cấp công trình, số tầng, chiều cao) nếu đọc được. Giữ nguyên số liệu, không bịa."},

    # F. Nội dung đề nghị gia hạn + thời gian hoàn thành.
    {"name": "GiaHan_LyDo", "desc": "Lý do đề nghị gia hạn — NGUYÊN VĂN mục 4 Đơn ('Nội dung đề nghị điều chỉnh "
        "… (hoặc lý do đề nghị gia hạn/cấp lại)'), vd 'Gia hạn giấy phép'. Không bịa."},
    {"name": "CongTrinh_ThoiGianDuKienHoanThanh", "desc": "Mục 5 Đơn: dự kiến thời gian hoàn thành công trình "
        "theo thiết kế điều chỉnh/gia hạn, số THÁNG (vd '12')."},
    {"name": "Don_NguoiKy", "desc": "Họ tên ghi dưới chữ ký 'NGƯỜI LÀM ĐƠN/ĐẠI DIỆN CHỦ ĐẦU TƯ'. Nhiều người ký "
        "→ nối ' - '."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Applicant_NgaySinh", "Applicant_NgayCap", "GPXD_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Applicant_NoiCuTru", "Dat_DiaDiemXayDung", "ToChucNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Giá trị option "Loại đề nghị" của thủ tục này (value=extension trên cổng).
REQUEST_TYPE_GIA_HAN = "Gia hạn Giấy phép xây dựng"

UI_COMP_BY_NAME = {
    # Người nộp hồ sơ.
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # Tổ chức người nộp (chỉ khi chọn 'Tổ chức').
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",

    # Đầu đơn + chủ đầu tư / chủ hộ.
    "data[recipient]": "dom-input",
    "data[loaiHinhChuDauTu]": "dom-radio",
    "data[tenChuHo]": "dom-input",
    "data[soDinhDanhChuHo]": "dom-input",
    "data[soDienThoaiChuHo]": "dom-input",
    "data[tenChuDauTu]": "dom-input",
    "data[nguoiDaiDien]": "dom-input",
    "data[chucVu]": "dom-input",
    "data[maSoDoanhNghiepCDT]": "dom-input",
    "data[soDinhDanhNguoiDaiDien]": "dom-input",
    "data[soDienThoaiNguoiDaiDien]": "dom-input",

    # Địa điểm xây dựng (Tỉnh lô đất = data[province] lần 2).
    "data[lotNumber]": "dom-input",
    "data[landArea]": "dom-input",
    "data[locationAt]": "dom-input",
    "data[street]": "dom-input",
    "data[phuongxaaa]": "dom-select",

    # GPXD đã cấp.
    "data[existingPermitNumber]": "dom-input",
    "data[NgayCap]": "dom-date",
    "data[existingPermitAuthority]": "dom-input",
    "data[existingPermitContent]": "dom-input",

    # Nội dung đề nghị + hoàn thành + cam kết + ký đơn.
    "data[requestType]": "dom-select",
    "data[extensionReason]": "dom-input",
    "data[estimatedCompletionMonths]": "dom-input",
    "data[commitment]": "dom-checkbox",
    "data[tinhthanhqwaasa]": "dom-select",
    "data[KyGhiRoHoTen]": "dom-input",
}
