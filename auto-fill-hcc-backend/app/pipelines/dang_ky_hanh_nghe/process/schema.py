"""Compact schema cho "Đăng ký hành nghề" (mã 1.012275 — Sở Y tế, Form.io trên Cổng DVC quốc gia).

Form bước kê khai có hai khối nhân thân giống thủ tục thú y:
  Phần I  "THÔNG TIN NGƯỜI NỘP HỒ SƠ" → data[fullname…]: cổng tự đổ TÀI KHOẢN ĐANG ĐĂNG NHẬP. KHÔNG động vào.
  Phần II "THÔNG TIN CHỦ HỒ SƠ"       → data[owner…]: CƠ SỞ KHÁM BỆNH, CHỮA BỆNH + người đại diện của cơ sở.
Ô tích "Người nộp hồ sơ là chủ hồ sơ" (data[isOwnerDossierCheck]) khoá Phần II; bỏ tích thì mới điền được.

Nhóm field:
- CoSo_*         : cơ sở khám bệnh, chữa bệnh — đọc ở Danh sách đăng ký hành nghề (Mẫu 01 PL II NĐ 96/2023).
- NguoiDaiDien_* : nhân thân người đại diện / người chịu trách nhiệm chuyên môn — đọc ở CCCD của họ.
- NguoiNop_*     : chỗ để LLM "đỗ" nhân thân người nộp thay, KHÔNG đổ ra form.
"""

_DS_SRC = "Danh sách đăng ký hành nghề (Mẫu 01 Phụ lục II NĐ 96/2023/NĐ-CP)"
_CCCD_SRC = "CCCD / thẻ Căn cước của NGƯỜI ĐẠI DIỆN (người chịu trách nhiệm chuyên môn) của cơ sở"

# --- Cơ sở khám bệnh, chữa bệnh ---
FIELDS: list[dict] = [
    {"name": "CoSo_Ten", "desc": f"Tên CƠ SỞ KHÁM BỆNH, CHỮA BỆNH — mục 1 của {_DS_SRC} (vd 'Trạm Y tế xã "
        "Mường Than', 'Trung tâm Y tế huyện Nậm Nhùn'). Chép nguyên văn, KHÔNG kèm số thứ tự/nhãn mục."},
    {"name": "CoSo_DiaChi", "desc": f"ĐỊA CHỈ cơ sở khám bệnh, chữa bệnh — mục 2 của {_DS_SRC}, object "
        "{quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/thôn/bản/tổ (KHÔNG "
        "kèm phường/xã/tỉnh). Tên cơ sở dạng 'Trạm Y tế xã X' mà mục địa chỉ chỉ ghi tỉnh → xa='Xã X'."},
    {"name": "CoSo_NguoiChiuTrachNhiem", "desc": f"Họ tên NGƯỜI CHỊU TRÁCH NHIỆM CHUYÊN MÔN / người đứng đầu "
        f"cơ sở ghi ở {_DS_SRC} (dòng 'Người chịu trách nhiệm chuyên môn' hoặc người ký cuối danh sách). "
        "Danh sách không ghi thì bỏ trống."},
    {"name": "CoSo_CacCoSoKhac", "desc": "Hồ sơ có NHIỀU danh sách của CÁC CƠ SỞ KHÁC NHAU: liệt kê tên các "
        "cơ sở CÒN LẠI (ngoài CoSo_Ten), ngăn cách bằng ';'. Chỉ một cơ sở → bỏ trống."},
]

# --- Người đại diện của cơ sở (Phần II: ngày sinh, giới tính, CCCD) ---
FIELDS += [
    {"name": "NguoiDaiDien_HoTen", "desc": f"Họ và tên NGƯỜI ĐẠI DIỆN của cơ sở, lấy từ {_CCCD_SRC}. Ghi IN HOA."},
    {"name": "NguoiDaiDien_NgaySinh", "desc": f"Ngày sinh NGƯỜI ĐẠI DIỆN, dd/mm/yyyy — {_CCCD_SRC}."},
    {"name": "NguoiDaiDien_GioiTinh", "desc": f'Giới tính NGƯỜI ĐẠI DIỆN: "Nam" hoặc "Nữ", đọc ở {_CCCD_SRC}. '
        "KHÔNG suy từ họ tên."},
    {"name": "NguoiDaiDien_SoDinhDanh", "desc": f"Số CCCD/căn cước/định danh NGƯỜI ĐẠI DIỆN — {_CCCD_SRC}. Chỉ "
        "chữ số, ưu tiên số 12 chữ số. Hồ sơ KHÔNG có CCCD của người đại diện thì BỎ TRỐNG — tuyệt đối "
        "không lấy số của người nộp thay."},
    {"name": "NguoiDaiDien_NgayCapCCCD", "desc": f"Ngày cấp CCCD NGƯỜI ĐẠI DIỆN (mặt sau thẻ), dd/mm/yyyy — "
        f"{_CCCD_SRC}."},
    {"name": "NguoiDaiDien_NoiCapCCCD", "desc": "Nơi cấp CCCD NGƯỜI ĐẠI DIỆN. Mặt sau CCCD ghi \"CỤC TRƯỞNG CỤC "
        'CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã '
        'hội"; thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    # Hai field dưới CHỈ để tách vai, mapper KHÔNG đổ ra form.
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP THAY — CHỈ điền khi hồ sơ có CCCD RIÊNG của người "
        "nộp và người đó KHÁC người đại diện của cơ sở. Không có → bỏ trống."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh NGƯỜI NỘP THAY, chỉ chữ số. Không có → bỏ trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["CoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiDaiDien_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDaiDien_NgayCapCCCD"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*, tên theo bảng mapping nghiệp vụ.
UI_COMP_BY_NAME = {
    # --- Phần I "THÔNG TIN NGƯỜI NỘP HỒ SƠ" = TÀI KHOẢN ĐANG ĐĂNG NHẬP ---
    # KHÔNG có ô nhân thân nào của Phần I: cổng đã đổ sẵn tài khoản VNeID, ghi vào là ghi đè người khác.
    # Ô tích "Người nộp hồ sơ là chủ hồ sơ" không phải dữ liệu nhân thân — bỏ tích để MỞ KHOÁ Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # --- Phần II "THÔNG TIN CHỦ HỒ SƠ" = CƠ SỞ KHÁM BỆNH, CHỮA BỆNH ---
    "data[ownerFullname]": "dom-input",        # tên cơ sở (hoặc người chịu trách nhiệm chuyên môn).
    "data[ownerBirthday]": "dom-date",         # CCCD người đại diện.
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",       # địa chỉ cơ sở — Tỉnh/Thành phố.
    "data[ownerDistrict]": "dom-select",       # địa chỉ cơ sở — Phường/Xã.
    "data[ownerAddress]": "dom-input",         # địa chỉ cơ sở — chi tiết.
    "data[ownerNation]": "dom-select",         # "Quốc gia", mặc định Việt Nam.
    # data[ownerPhoneNumber] / ownerEmail / ownerFax / ghiChu: không có trong giấy tờ → cán bộ tự nhập.
}
