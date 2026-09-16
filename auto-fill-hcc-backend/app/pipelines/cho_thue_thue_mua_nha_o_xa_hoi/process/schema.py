"""Compact schema cho "Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu tư
công" — cổng DVC Bộ Xây dựng dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-*). CÙNG cổng #76/#78/
#113. Nguồn: CCCD người nộp + Tờ đơn đăng ký thuê/thuê mua NOXH (bản viết tay/scan).

⚠ ĐẶC THÙ: field-key data[...] TRÙNG giữa Phần I (người nộp) và Phần III (người viết đơn) — mỗi key sau
xuất hiện 2× trong DOM: fullname, identityNumber, identityDate, identityAgency, province, district,
address. Phân biệt bằng OCCURRENCE (0 = Phần I, 1 = Phần III) trong mapper. Địa chỉ 2 phần KHÁC nghĩa:
- Phần I province/district/address (occ0) = NƠI THƯỜNG TRÚ (theo CCCD).
- Phần III province/district/address (occ1) = NƠI Ở HIỆN TẠI (mục 5 đơn).
- Phần III province1/district1/address1 (key riêng, 1×) = THƯỜNG TRÚ/TẠM TRÚ (mục 6 đơn / CCCD).

Cấu trúc form:
- Phần I    : NGƯỜI NỘP — fullname/birthday/gender/CCCD/thường trú + chonDoiTuong + nation.
- Phần I.1  : DOANH NGHIỆP (chỉ khi Tổ chức) — organization/taxCode/nation1 (địa chỉ DN hiếm gặp, bỏ).
- Phần II   : HÌNH THỨC — checkbox mua/thuemua/thue (đúng 1 ô theo tiêu đề đơn).
- Phần III  : NGƯỜI VIẾT ĐƠN — nhân thân (occ1) + job/workPlace/nơi ở hiện tại/thường trú/đối tượng.
- Phần III.1: THÀNH VIÊN GIA ĐÌNH — datagrid dtgrid1 (x-array).
- Phần III.2: thực trạng nhà ở (select) + cam đoan (checkbox).
- Phần III.3: nơi ký (select) + ngày ký (date) + họ tên người ký.

Mẫu = Bà Nguyễn Thị Thảo Nguyên (cá nhân, con liệt sĩ/thương binh), hình thức THUÊ.
"""

_MAX_TV = 8  # số dòng thành viên gia đình tối đa trên datagrid dtgrid1.

# --- Người nộp / người viết đơn (chính chủ) — nhân thân từ CCCD + Tờ đơn ---
FIELDS: list[dict] = [
    {"name": "ChonDoiTuong", "desc": '"Tổ chức" nếu hồ sơ nộp dưới danh nghĩa công ty/HTX/cơ quan (có GCN '
        'đăng ký doanh nghiệp); "Cá nhân" nếu một người tự đăng ký. Thuê NOXH hầu hết là CÁ NHÂN.'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI VIẾT ĐƠN (= người nộp, chính chủ đăng ký thuê). "
        "IN HOA như CCCD. Lấy ở CCCD / Tờ đơn (mục 'Họ và tên người viết đơn')."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh, dd/mm/yyyy — CCCD (ngày/tháng/năm đầy đủ). Tờ đơn "
        "thường chỉ ghi năm sinh → lấy ngày/tháng theo CCCD."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính: "Nam"/"Nữ" — CCCD. KHÔNG suy từ tên đệm.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân. CCCD / Tờ đơn (mục 'Căn cước công "
        "dân số'). Chỉ chữ số, ưu tiên 12 số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD, dd/mm/yyyy — CCCD / Tờ đơn (mục 'cấp ngày')."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD. CCCD gắn chip: "Cục Cảnh sát quản lý hành chính '
        'về trật tự xã hội". Thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại liên hệ NGƯỜI VIẾT ĐƠN — Tờ đơn (cuối đơn). "
        "Chỉ chữ số. CCCD không in số điện thoại."},
    {"name": "NguoiNop_NgheNghiep", "desc": "Nghề nghiệp người viết đơn — Tờ đơn mục 4 'Nghề nghiệp (nếu "
        "có)'. Bỏ nếu đơn để trống/không đọc được."},
    {"name": "NguoiNop_NoiLamViec", "desc": "Nơi làm việc người viết đơn — Tờ đơn (nếu có). Bỏ nếu không có."},
    {"name": "NguoiNop_ThuongTru", "desc": "NƠI THƯỜNG TRÚ (đăng ký thường trú), object {quocGia,tinh,xa,"
        "diaChi}. CCCD (Nơi thường trú) / Tờ đơn mục 6 'Đăng ký thường trú (hoặc tạm trú) tại'. tinh='Tỉnh/"
        "Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ (KHÔNG kèm phường/xã/tỉnh). Đơn để trống mục 6 "
        "và không có CCCD thì bỏ field — mapper lấy nơi ở hiện tại thay."},
    {"name": "NguoiNop_NoiOHienTai", "desc": "NƠI Ở HIỆN TẠI (KHÁC thường trú), object {quocGia,tinh,xa,"
        "diaChi}. Tờ đơn mục 5 'Nơi ở hiện tại'. Nếu đơn không tách riêng, để trống (mapper sẽ suy)."},
    {"name": "NguoiNop_ThuocDoiTuong", "desc": "Đối tượng chính sách được hưởng NOXH — Tờ đơn mục 7 'Thuộc "
        "đối tượng'. Vd 'Con liệt sĩ, thương binh', 'Người thu nhập thấp', 'Công nhân KCN'. Chép nguyên văn."},
    {"name": "Don_ThucTrangNhaO", "desc": "Thực trạng nhà ở của người viết đơn — Tờ đơn mục thực trạng. Vd "
        "'Chưa có nhà ở thuộc sở hữu của mình', 'Có nhà nhưng diện tích bình quân dưới 15m²/người'. "
        "Chép cụm mô tả ngắn để khớp lựa chọn trên form."},
]

# --- Hình thức đăng ký (Phần II) ---
FIELDS += [
    {"name": "Don_HinhThuc", "desc": 'Hình thức đăng ký người viết đơn chọn: "Mua" / "Thuê mua" / "Thuê". '
        'Suy từ TIÊU ĐỀ tờ đơn: "ĐƠN ĐĂNG KÝ THUÊ NHÀ Ở XÃ HỘI" → "Thuê"; "…THUÊ MUA…" → "Thuê mua"; '
        '"…MUA…" → "Mua".'},
]

# --- Ký (Phần III.3) ---
FIELDS += [
    {"name": "Don_NoiKy", "desc": "Nơi lập/ký đơn (dòng '…, ngày … tháng … năm …' cuối đơn) — tên tỉnh/"
        "thành phố, vd 'Đà Nẵng'. Dùng cho ô 'Tại' (nơi ký)."},
    {"name": "Don_NgayKy", "desc": "Ngày ký đơn, dd/mm/yyyy — dòng ký cuối Tờ đơn."},
]

# --- Thành viên gia đình (Phần III.1 — datagrid) ---
FIELDS += [
    {"name": "ThanhVienGiaDinh", "desc": "MẢNG các thành viên trong hộ gia đình (Tờ đơn mục 9). Mỗi phần "
        "tử: {hoTen, soCccd, ngayCap, noiCap, quanHe}. hoTen=họ tên thành viên; soCccd=số căn cước (bỏ nếu "
        "trống); ngayCap=ngày cấp CCCD dd/mm/yyyy (bỏ nếu trống); noiCap=nơi cấp (bỏ nếu trống); "
        "quanHe=mối quan hệ với người viết đơn (Vợ/Chồng/Con gái/Con trai/…). Trích ĐÚNG số dòng có trong đơn."},
]

# --- Doanh nghiệp (chỉ khi Tổ chức — hiếm) ---
FIELDS += [
    {"name": "DoanhNghiep_Ten", "desc": "Tên đầy đủ DOANH NGHIỆP/tổ chức (khi Tổ chức). GCN đăng ký doanh "
        "nghiệp/hộ kinh doanh. Bỏ nếu cá nhân."},
    {"name": "DoanhNghiep_MaSoThue", "desc": "Mã số doanh nghiệp / mã số thuế (GCN ĐKDN). Chỉ chữ số. Bỏ "
        "nếu cá nhân."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "Don_NgayKy"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
for _a in ("NguoiNop_ThuongTru", "NguoiNop_NoiOHienTai"):
    COMPACT_COMP_BY_NAME[_a] = "x-select-area"
COMPACT_COMP_BY_NAME["ThanhVienGiaDinh"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key CHUẨN từ HTML thật.
# Nhiều key TRÙNG giữa Phần I và Phần III → mapper gắn occurrence (0/1). UI_COMP_BY_NAME chỉ khai báo comp.
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP (occurrence 0 cho các key trùng) -----
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # ----- Phần I.1: DOANH NGHIỆP (khi Tổ chức) -----
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[nation1]": "dom-select",
    # ----- Phần II: HÌNH THỨC (checkbox) -----
    "data[mua]": "dom-checkbox",
    "data[thuemua]": "dom-checkbox",
    "data[thue]": "dom-checkbox",
    # ----- Phần III: NGƯỜI VIẾT ĐƠN (occurrence 1 cho các key trùng) -----
    "data[job]": "dom-input",
    "data[workPlace]": "dom-input",
    "data[thuocDoiTuong]": "dom-input",
    # Thường trú/tạm trú người viết đơn (key riêng, 1× trong DOM cá nhân).
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    # ----- Phần III.2: thực trạng + cam đoan -----
    "data[thucTrang]": "dom-select",
    "data[checkBox]": "dom-checkbox",
    # ----- Phần III.3: ký -----
    "data[TinTTTe]": "dom-select",   # nơi ký (Tỉnh/TP).
    "data[TDTTK]": "dom-date",       # ngày ký.
    "data[nguoiLamDon]": "dom-input",
}

# ----- Phần III.1: DATAGRID thành viên gia đình (data[dtgrid1][i][...]).
# ⚠ key namsanxuat = "Nơi cấp", namsanxuat1 = "Mối quan hệ" (đặt tên nhầm trên form, giữ nguyên theo DOM).
for _i in range(_MAX_TV):
    for _col in ("fullname1", "identityNumber1", "namsanxuat", "namsanxuat1"):
        UI_COMP_BY_NAME[f"data[dtgrid1][{_i}][{_col}]"] = "dom-input"
    # identityDate là ô NGÀY (flatpickr) → dom-date để FE dùng setDate + được reapplyStandardDatagridDates
    # điền lại (Form.io re-render datagrid xóa date dòng trước; xem fix FE).
    UI_COMP_BY_NAME[f"data[dtgrid1][{_i}][identityDate]"] = "dom-date"
