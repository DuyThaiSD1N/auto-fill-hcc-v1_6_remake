"""Compact schema cho "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ đấu nối với hệ
thống điện quốc gia tại cấp điện áp hạ áp" (mã 1.115377) — cổng một cửa Bộ Công Thương (Form.io, cùng engine
thong_bao_sua_doi_ctkm), cơ quan tiếp nhận là UBND cấp xã.

Bước 1 gồm khối tài khoản + khối chủ hồ sơ (data[...]) và tờ khai Thông báo Mẫu 01 (Phụ lục III NĐ 243/2026/NĐ-CP)
nằm dưới container pn3 (data[pn3][...]). "Loại đối tượng" (data[pn3][loaiDoiTuong]) bật MỘT trong hai panel:
formCaNhan (key trần) hoặc formToChuc (key đuôi ...ToChuc). Key tờ khai không trùng khối tài khoản → không
cần occurrence.

Nguồn: Thông báo Mẫu 01 (nguồn chính) + Bản vẽ thiết kế lắp đặt (dự phòng thông số kỹ thuật, đối chiếu chủ đầu
tư) + CCCD người đứng tên (khối tài khoản, số định danh).
"""

_TB = "Thông báo phát triển nguồn điện mặt trời mái nhà (Mẫu 01)"
_BV = "Bản vẽ thiết kế lắp đặt / bản vẽ hoàn công hệ thống điện mặt trời"

FIELDS: list[dict] = [
    # --- CCCD / thẻ căn cước của người đứng tên Thông báo (hoặc người đại diện tổ chức) ---
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/thẻ căn cước có trong hồ sơ. IN HOA."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân in trên CÙNG thẻ đó. Chỉ chữ số."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh in trên CÙNG thẻ đó, dd/mm/yyyy."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp in ở mặt sau CÙNG thẻ đó, dd/mm/yyyy."},
    {"name": "Cccd_NoiCuTru", "desc": "Nơi thường trú / nơi cư trú in trên CÙNG thẻ đó, object "
        "{quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa chỉ phần số nhà/thôn/đường, KHÔNG kèm phường/xã/tỉnh."},

    # --- Đầu văn bản Thông báo ---
    {"name": "TB_DiaDanh", "desc": f"Địa danh ở đầu dòng '<địa danh>, ngày … tháng … năm …' của {_TB}, chép phần "
        "trước dấu phẩy (vd 'Hà Nội')."},
    {"name": "TB_NgayLap", "desc": f"Ngày ở dòng '<địa danh>, ngày … tháng … năm …' của {_TB}, dd/mm/yyyy."},
    {"name": "TB_KinhGui", "desc": f"Nơi nhận ở dòng 'Kính gửi:' của {_TB}, chép nguyên văn, bỏ chữ 'Kính gửi:'."},

    # --- I.1 Thông tin về tổ chức/cá nhân ---
    {"name": "TB_Ten", "desc": f"Dòng 'a) Tên:' mục I.1 của {_TB}, chép nguyên văn (họ tên cá nhân hoặc tên tổ "
        "chức/hộ kinh doanh)."},
    {"name": "TB_SoDinhDanh", "desc": "Dòng 'b) Số định danh cá nhân/CCCD (đối với cá nhân):'. Chỉ chữ số, không "
        "tự bù số."},
    {"name": "TB_MaSoDoanhNghiep", "desc": "Dòng 'Mã số doanh nghiệp (đối với tổ chức):'. Bỏ trống trên giấy thì "
        "bỏ field."},
    {"name": "TB_DiaChi", "desc": "Dòng 'c) Địa chỉ:' mục I.1, object {quocGia,tinh,xa,chiTietDuoiXa,fullText}. fullText "
        "= nguyên dòng; tinh='Tỉnh/Thành phố …'; xa=phường/xã/đặc khu; chiTietDuoiXa=số nhà/đường/thôn (KHÔNG kèm "
        "phường/xã/tỉnh)."},
    {"name": "TB_DienThoai", "desc": "Dòng 'd) Số điện thoại:'. Chỉ chữ số."},
    {"name": "TB_Email", "desc": "Dòng 'đ) Email (nếu có):'. Bỏ trống thì bỏ field."},
    {"name": "TB_MaKhachHang", "desc": "Dòng 'e) Mã số khách hàng sử dụng điện:', chép nguyên văn chữ và số (vd "
        "'PA01000000001'), bỏ khoảng trắng."},

    # --- I.2–I.6 ---
    {"name": "TB_ViTriLapDat", "desc": "Dòng '2. Vị trí lắp đặt:' (thường in sẵn 'Trên mái nhà')."},
    {"name": "TB_KetCau", "desc": "Dòng 'a) Kết cấu:' mục I.3 (vd 'Hệ khung, mái bê tông')."},
    {"name": "TB_ChieuCao", "desc": "Dòng 'b) Chiều cao công trình:', chép đúng số và đơn vị nếu có (vd '3.10')."},
    {"name": "TB_DienTichMai", "desc": "Dòng 'c) Diện tích mái:', chép đúng số và đơn vị nếu có."},
    {"name": "TB_CongSuatPV", "desc": "Dòng 'Tổng công suất tấm quang điện (kWp):' mục I.4, chỉ phần số viết vào."},
    {"name": "TB_LuuTru", "desc": "Dòng 'Tổng sản lượng điện lưu trữ tại hệ thống lưu trữ điện (nếu có, kWh):', "
        "chỉ phần số viết vào. Bỏ trống thì bỏ field."},
    {"name": "TB_Inverter", "desc": "Dòng 'Tổng công suất định mức của các bộ chuyển đổi nghịch lưu - inverter "
        "(kW):', chỉ phần số viết vào."},
    {"name": "TB_PhuongAn", "desc": "Mục 5 'Phương án xử lý sản lượng điện dư': ô nào được đánh dấu x. Trả '5.1' "
        "nếu đánh dấu ô 'Đồng ý bán sản lượng điện dư…', '5.2' nếu đánh dấu ô 'Không bán sản lượng điện dư…'. "
        "Không thấy dấu thì bỏ field."},
    {"name": "TB_ThoiGianDuKien", "desc": "Dòng '6. Thời gian dự kiến lắp đặt và thời gian hoàn thành:', chép "
        "nguyên văn (vd '09/2026')."},

    # --- II. Cam kết + chữ ký ---
    {"name": "TB_TenCamKet", "desc": "Tên viết vào câu 'Hộ …… cam kết thực hiện xây dựng, lắp đặt…' ở mục II."},
    {"name": "TB_NguoiKy", "desc": "Họ tên viết tay dưới chữ ký ở khối 'ĐẠI DIỆN … THÔNG BÁO (Ký, ghi rõ họ tên)'."},

    # --- Bản vẽ thiết kế (chỉ để dự phòng + đối chiếu) ---
    {"name": "BanVe_ChuDauTu", "desc": f"Tên ở mục 'Chủ đầu tư/INVESTOR' trên {_BV}. KHÔNG lấy tên đơn vị thiết "
        "kế/thi công."},
    {"name": "BanVe_CongSuatPV", "desc": f"Tổng công suất tấm PV (kWp) ghi trên {_BV} (vd dòng 'Tổng công suất PV "
        "= … kWp'). Chỉ phần số."},
    {"name": "BanVe_LuuTru", "desc": f"Dung lượng pin lưu trữ (kWh) ghi trên {_BV}. Chỉ phần số."},
    {"name": "BanVe_Inverter", "desc": f"Công suất inverter (kW) ghi trên {_BV}; nhiều inverter thì cộng tổng. "
        "Chỉ phần số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "TB_NgayLap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "TB_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

CA_NHAN = "Cá nhân"
TO_CHUC = "Tổ chức"

# OCR tối đa N trang đầu mỗi PDF (bước điền + đính kèm dùng CÙNG số → bước sau trúng cache OCR). Thông báo 3
# trang, thông số bản vẽ ở trang 1; hồ sơ thật hay kèm tệp gộp ~50 trang (C/O, CQ…) → OCR cả tệp quá 120s, cả
# lô OCR hỏng và extension báo "Không kết nối được máy chủ" (trần 100s).
OCR_MAX_PAGES = 4

# Selectboxes "5. Phương án xử lý sản lượng điện dư": value Form.io → nhãn nguyên văn trên cổng.
SURPLUS_OPTIONS = {
    "dongYBan": (
        "5.1. Đồng ý bán sản lượng điện dư vào lưới điện của bên mua và chịu trách nhiệm đầu tư, lắp đặt công tơ "
        "điện có đo xa và kết nối với hệ thống thu thập dữ liệu từ xa của đơn vị điện lực, bảo đảm thiết bị phù "
        "hợp với quy định của pháp luật."
    ),
    "khongBan": (
        "5.2. Không bán sản lượng điện dư vào lưới điện của bên mua và chịu trách nhiệm đối với việc kiểm định về "
        "an toàn điện, tuân thủ các quy trình, quy chuẩn quản lý vận hành công trình điện và các quy định về điều "
        "kiện kỹ thuật, nghiệm thu an toàn theo quy định."
    ),
}

# Field-key tờ khai theo panel: key logic → (Cá nhân, Tổ chức). Lấy từ DOM thật (sheet mapping 2 biến thể).
PANEL_KEYS: dict[str, tuple[str, str]] = {
    "kinhGui": ("data[pn3][kinhGui]", "data[pn3][kinhGuiToChuc]"),
    "ten": ("data[pn3][fullname]", "data[pn3][tenToChuc]"),
    "tinh": ("data[pn3][province]", "data[pn3][provinceToChuc]"),
    "xa": ("data[pn3][district1]", "data[pn3][districtToChuc]"),
    "diaChi": ("data[pn3][address]", "data[pn3][addressToChuc]"),
    "dienThoai": ("data[pn3][phonenlh]", "data[pn3][dienThoaiToChuc]"),
    "email": ("data[pn3][email]", "data[pn3][emailToChuc]"),
    "maKhachHang": ("data[pn3][maSoKhachHang]", "data[pn3][maSoKhachHangToChuc]"),
    "viTri": ("data[pn3][viTriLapDat]", "data[pn3][viTriLapDatToChuc]"),
    "ketCau": ("data[pn3][ketCauCongTrinh]", "data[pn3][ketCauCongTrinhToChuc]"),
    "chieuCao": ("data[pn3][chieuCaoCongTrinh]", "data[pn3][chieuCaoCongTrinhToChuc]"),
    "dienTichMai": ("data[pn3][dienTichMai]", "data[pn3][dienTichMaiToChuc]"),
    "congSuatPV": ("data[pn3][tongCongSuatPV]", "data[pn3][tongCongSuatPVToChuc]"),
    "luuTru": ("data[pn3][tongLuuTruDien]", "data[pn3][tongLuuTruDienToChuc]"),
    "inverter": ("data[pn3][tongCongSuatInverter]", "data[pn3][tongCongSuatInverterToChuc]"),
    "phuongAn": ("data[pn3][pa][]", "data[pn3][phuongAnXuLyDienDuToChuc][]"),
    "thoiGian": ("data[pn3][thoiGianDuKien]", "data[pn3][thoiGianDuKienToChuc]"),
    "camKet": ("data[pn3][tenChuHoCamKet]", "data[pn3][tenToChucCamKet]"),
    "nguoiKy": ("data[pn3][chuhoky]", "data[pn3][nguoiDaiDienToChucKy]"),
}

_PANEL_COMP = {
    "tinh": "dom-select",
    "xa": "dom-select",
    "phuongAn": "dom-checkbox",
}

UI_COMP_BY_NAME = {
    # --- Khối TÀI KHOẢN NỘP HỒ SƠ (cổng đổ theo VNeID) ---
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[birthday]": "dom-date",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # --- Khối CHỦ HỒ SƠ ---
    "data[isOwnerDossier]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownertaxCode]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    # --- Tờ khai: đầu đơn (chung hai panel) ---
    "data[pn3][tinhThanhPhoNopDon]": "dom-select",
    "data[pn3][ngayNopDon]": "dom-date",
    "data[pn3][loaiDoiTuong]": "dom-select",
}
for _logic, _keys in PANEL_KEYS.items():
    for _key in _keys:
        UI_COMP_BY_NAME[_key] = _PANEL_COMP.get(_logic, "dom-input")
