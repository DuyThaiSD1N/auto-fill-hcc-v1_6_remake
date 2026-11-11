"""Compact schema cho "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (mã TTHC 1.013818).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm dựng trong Python (mapper.py). Tên ô lấy từ eForm thật "GIẤY ĐĂNG KÝ THAM
DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG" Mẫu TP-TSCC-10 (tokhaidientu.moj.gov.vn, crawl 11/11/2026):
  KyKiemTra / KinhGui; *C / NO_* / SoDienThoai / Email = người đề nghị (cổng đổ sẵn theo tài khoản VNeID);
  ToChucTapSu / CongChungVienHuongDan / NgayBatDauTapSu / NgayKetThucTapSu = quá trình tập sự;
  SoQuyetDinhCongNhan / NgayQuyetDinhCongNhan / SoTuPhapCongNhan = quyết định công nhận hoàn thành tập sự;
  DaTungThamDuKyKiemTra; LamTai / Ngay / Thang / Nam / NguoiDeNghiKy = nơi, ngày làm giấy và người ký.
"""

FIELDS: list[dict] = [
    {"name": "KyKiemTra", "desc": "Dòng trong ngoặc dưới tiêu đề Giấy đăng ký '(Kỳ kiểm tra kết quả tập sự hành nghề "
        "công chứng ...)': CHỈ chép phần sau chữ 'công chứng', vd 'lần thứ sáu', 'năm 2026'. Không có thì bỏ."},
    {"name": "KinhGui", "desc": "Dòng 'Kính gửi' của Giấy đăng ký, chép nguyên văn (thường 'Bộ Tư pháp')."},

    # Người đề nghị — CCCD > Giấy đăng ký > Quyết định công nhận.
    {"name": "Ndn_HoTen", "desc": "Họ tên NGƯỜI TẬP SỰ đăng ký dự kiểm tra (dòng 'Tôi tên là' của Giấy đăng ký, người "
        "được công nhận ở Điều 1 Quyết định). KHÔNG lấy công chứng viên hướng dẫn hay người ký quyết định."},
    {"name": "Ndn_GioiTinh", "desc": '"Nam" hoặc "Nữ". Quyết định ghi "ông" → Nam, "bà" → Nữ.'},
    {"name": "Ndn_NgaySinh", "desc": "Ngày sinh dd/mm/yyyy (CCCD > Giấy đăng ký > Quyết định)."},
    {"name": "Ndn_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân CHỈ khi giấy ghi rõ một loại: 'Thẻ căn cước', 'Căn cước "
        "công dân', 'Chứng minh nhân dân', 'Hộ chiếu'. Dòng in sẵn của mẫu 'Số thẻ căn cước công dân/Số thẻ căn "
        "cước/Số định danh cá nhân' KHÔNG phải loại giấy tờ → bỏ."},
    {"name": "Ndn_SoDinhDanh", "desc": "Số CCCD/căn cước/số định danh cá nhân, chỉ chữ số."},
    {"name": "Ndn_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân dd/mm/yyyy. Không lấy ngày hết hạn."},
    {"name": "Ndn_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân, chép như giấy (vd 'Cục Cảnh sát quản lý hành chính về "
        "trật tự xã hội', 'Bộ Công an'). KHÔNG chép phần hướng dẫn in nghiêng '(đối với thẻ căn cước công dân/...)'."},
    {"name": "Ndn_NoiOHienTai", "desc": "Nơi ở hiện tại trên Giấy đăng ký, object {quocGia,tinh,xa,chiTietDuoiXa}; "
        "chiTietDuoiXa là số nhà/đường/tổ/thôn chép đúng giấy. Không có Giấy đăng ký thì lấy nơi cư trú trên CCCD."},
    {"name": "Ndn_DienThoai", "desc": "Số điện thoại trên Giấy đăng ký, chỉ chữ số."},
    {"name": "Ndn_Email", "desc": "Email trên Giấy đăng ký; dòng chấm trống thì bỏ."},

    # Quá trình tập sự.
    {"name": "TapSu_ToChuc", "desc": "Phần sau 'Tôi đã hoàn thành thời gian và nghĩa vụ của người tập sự tại:' chép "
        "NGUYÊN VĂN, giữ cả địa chỉ tổ chức (vd 'Văn phòng công chứng A - Địa chỉ: Số 1 đường B, phường C, tỉnh D')."},
    {"name": "TapSu_CongChungVien", "desc": "Phần sau 'Công chứng viên hướng dẫn tập sự:' chép NGUYÊN VĂN, giữ cả số "
        "thẻ công chứng viên (vd 'Công chứng viên Lê Văn A; Thẻ công chứng viên số 01/CCV tháng 01/2020')."},
    {"name": "TapSu_TuNgay", "desc": "Thời gian tập sự 'từ ngày' dd/mm/yyyy."},
    {"name": "TapSu_DenNgay", "desc": "Thời gian tập sự 'đến ngày' dd/mm/yyyy."},
    {"name": "TapSu_SoThang", "desc": "Số tháng tập sự ghi trên Giấy đăng ký, chỉ chữ số (vd '12')."},

    # Quyết định công nhận hoàn thành tập sự — hai nguồn để đối chiếu.
    {"name": "QD_CongNhan", "desc": "Đọc trên chính QUYẾT ĐỊNH công nhận hoàn thành tập sự hành nghề công chứng: "
        "object {so (số quyết định ở góc trái, vd '12/QĐ-STP'; số viết tay đọc không chắc thì để rỗng), ngay "
        "(ngày ký dd/mm/yyyy ở dòng địa danh, ngày), tinh (tỉnh/thành phố của Sở Tư pháp ban hành, vd 'Khánh Hòa')}. "
        "KHÔNG lấy số/ngày của dấu chứng thực bản sao. Không có Quyết định thì bỏ."},
    {"name": "DK_QuyetDinh", "desc": "Dòng 'Đã được công nhận hoàn thành tập sự theo quyết định số: ... ngày ... của Sở "
        "Tư pháp ...' trên GIẤY ĐĂNG KÝ: object {so, ngay (dd/mm/yyyy), tinh (chỉ tên tỉnh/thành phố)}."},
    {"name": "DaTungThamDu", "desc": "Phần sau 'Đã từng tham dự kỳ kiểm tra kết quả tập sự hành nghề công chứng:' chép "
        "NGUYÊN VĂN (vd 'Chưa tham dự kỳ kiểm tra kết quả tập sự hành nghề công chứng nào', 'Kỳ kiểm tra năm 2025')."},

    {"name": "LamDon_NoiNgay", "desc": "Dòng địa danh, ngày cuối Giấy đăng ký (có thể viết tay), object {diaDanh, ngay "
        "(dd/mm/yyyy)}; vd 'Hà Nội, ngày 5 tháng 3 năm 2026' → {diaDanh:'Hà Nội', ngay:'05/03/2026'}. Phần nào không "
        "đọc được thì để rỗng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Ndn_NgaySinh", "Ndn_NgayCap", "TapSu_TuNgay", "TapSu_DenNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["Ndn_NoiOHienTai"] = "x-select-area"

# Loại control đúng eForm. Tỉnh/xã nơi ở là HAI x-select rời (xã phụ thuộc tỉnh); chi tiết là NO_SoNhaToDanPhoC.
UI_COMP_BY_NAME = {
    "KyKiemTra": "x-input",
    "KinhGui": "x-input",
    "HoVaTenC": "x-input",
    "GioiTinhC": "x-select",
    "NgaySinhC": "x-date",
    "LoaiGiayToDinhDanhC": "x-select",
    "SoDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "NO_SoNhaToDanPhoC": "x-input",
    "NO_TinhThanhC": "x-select",
    "NO_PhuongXaC": "x-select",
    "SoDienThoai": "x-input",
    "Email": "x-input",
    "ToChucTapSu": "x-input",
    "CongChungVienHuongDan": "x-input",
    "NgayBatDauTapSu": "x-date",
    "NgayKetThucTapSu": "x-date",
    "SoQuyetDinhCongNhan": "x-input",
    "NgayQuyetDinhCongNhan": "x-date",
    "SoTuPhapCongNhan": "x-select",
    "DaTungThamDuKyKiemTra": "x-input",
    "LamTai": "x-select",
    "Ngay": "x-input",
    "Thang": "x-input",
    "Nam": "x-input",
    "NguoiDeNghiKy": "x-input",
}

# Option dropdown "LamTai" của eForm này là danh mục CŨ, khác danh mục tỉnh của NO_TinhThanhC / SoTuPhapCongNhan
# (vd "Tỉnh Bắc Ninh", "Tỉnh Thành phố Huế"). Extension khớp lỏng không nối được "Thành phố Bắc Ninh" ↔ "Tỉnh Bắc Ninh"
# nên mapper chọn đúng chữ option ở đây.
LAM_TAI_OPTIONS = (
    "Thành phố Quảng Ninh", "Thành phố Hà Nội", "Tỉnh Cao Bằng", "Tỉnh Tuyên Quang", "Tỉnh Điện Biên",
    "Tỉnh Lai Châu", "Tỉnh Sơn La", "Tỉnh Lào Cai", "Tỉnh Thái Nguyên", "Tỉnh Lạng Sơn", "Tỉnh Bắc Ninh",
    "Tỉnh Phú Thọ", "Thành phố Hải Phòng", "Tỉnh Hưng Yên", "Tỉnh Ninh Bình", "Tỉnh Thanh Hóa", "Tỉnh Nghệ An",
    "Tỉnh Hà Tĩnh", "Tỉnh Quảng Trị", "Tỉnh Thành phố Huế", "Thành phố Đà Nẵng", "Tỉnh Quảng Ngãi", "Tỉnh Gia Lai",
    "Tỉnh Khánh Hòa", "Tỉnh Đắk Lắk", "Tỉnh Lâm Đồng", "Thành phố Đồng Nai", "Thành phố Hồ Chí Minh",
    "Tỉnh Tây Ninh", "Tỉnh Đồng Tháp", "Tỉnh Vĩnh Long", "Tỉnh An Giang", "Tỉnh Thành phố Cần Thơ", "Tỉnh Cà Mau",
)
