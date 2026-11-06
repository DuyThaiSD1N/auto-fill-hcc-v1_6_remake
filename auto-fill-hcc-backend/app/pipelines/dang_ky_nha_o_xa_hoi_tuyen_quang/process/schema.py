"""Compact schema cho "Tuyên Quang - Đăng ký mua, thuê mua, thuê nhà ở xã hội…" (1.014632) — cổng DVC Bộ Xây dựng
dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-*). Field-key lấy từ file mapping (sheet "Mapping NOXH - Bộ Xây
dựng"). Bộ hồ sơ thường là một PDF gộp: Mẫu số 02, Giấy chứng nhận, CCCD, CT07, giấy tờ hôn nhân, văn bản BHXH.

Hai form trên cùng bước 1:
- Form 1, key PHẲNG data[...]            : người nộp (= người kê khai).
- Form 2, key LỒNG data[panel_chung][...]: Giấy xác nhận về điều kiện nhà ở. Key lồng không trùng key phẳng nên không
  cần occurrence. Nơi cấp ở đây là ô chữ tự do, còn nơi cấp form 1 là ô chọn.

Không khai các ô ẩn của form (note, noidungyeucaugiaiquyet, ownerFullname, panel_chung.kinhGui): cổng không dựng ô ẩn nên
điền vào sẽ thành "không tìm thấy ô". Panel doanh nghiệp cũng bỏ: Mẫu 02 chỉ dành cho cá nhân.
"""

_PANEL = "data[panel_chung]"

FIELDS: list[dict] = [
    {"name": "NguoiKeKhai_HoTen", "desc": "Họ và tên NGƯỜI KÊ KHAI (mục 2 của Mẫu số 02/03, người đứng tên CCCD). IN HOA "
        "như CCCD."},
    {"name": "NguoiKeKhai_NgaySinh", "desc": "Ngày sinh người kê khai, dd/mm/yyyy — CCCD / Mẫu 02 mục 2 / CT07 mục 1."},
    {"name": "NguoiKeKhai_GioiTinh", "desc": 'Giới tính: "Nam"/"Nữ" — CCCD / CT07 mục 2.'},
    {"name": "NguoiKeKhai_SoDinhDanh", "desc": "Số CCCD/định danh người kê khai — CCCD / Mẫu 02 mục 3 / CT07. Chỉ chữ số."},
    {"name": "NguoiKeKhai_NgayCap", "desc": "Ngày cấp CCCD, dd/mm/yyyy — mặt sau CCCD / Mẫu 02 mục 3 'cấp ngày'."},
    {"name": "NguoiKeKhai_NoiCap", "desc": "Nơi cấp CCCD — Mẫu 02 mục 3 'tại' / chức danh người ký mặt sau CCCD."},
    {"name": "NguoiKeKhai_DienThoai", "desc": "Số điện thoại người kê khai — văn bản BHXH dòng '(Điện thoại liên hệ …)' "
        "hoặc giấy tờ khác có ghi. Chỉ chữ số."},
    {"name": "NguoiKeKhai_ThuongTru", "desc": "NƠI THƯỜNG TRÚ, object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên CT07 mục 8 "
        "→ Mẫu 02 mục 5 → văn bản BHXH; CCCD xếp CUỐI vì hay in địa chỉ cũ."},
    {"name": "NguoiKeKhai_NoiOHienTai", "desc": "NƠI Ở HIỆN TẠI, object {quocGia,tinh,xa,chiTietDuoiXa}. Mẫu 02 mục 4 / "
        "CT07 mục 10 / văn bản BHXH."},
    {"name": "NguoiKeKhai_DoiTuong", "desc": "Mẫu 02 mục 8 'Là đối tượng' — chép nguyên văn."},
    {"name": "NguoiKeKhai_QuanHeChuHo", "desc": "CT07 mục 12 'Quan hệ với chủ hộ' của người kê khai, chép nguyên văn "
        "(vd 'Mẹ đẻ', 'Chủ hộ'). Người kê khai đứng tên chủ hộ thì trả 'Chủ hộ'."},
    {"name": "VoChong_HoTen", "desc": "Mẫu 02 mục 6 'Họ và tên vợ/chồng'. Mục để trống thì BỎ, kể cả khi hồ sơ có giấy "
        "ly hôn."},
    {"name": "VoChong_SoDinhDanh", "desc": "Mẫu 02 mục 6 'Căn cước công dân số' của vợ/chồng. Trống thì BỎ."},
    {"name": "VoChong_NgayCap", "desc": "Mẫu 02 mục 6 'cấp ngày' của vợ/chồng, dd/mm/yyyy. Trống thì BỎ."},
    {"name": "VoChong_NoiCap", "desc": "Mẫu 02 mục 6 'tại' của vợ/chồng. Trống thì BỎ."},
    {"name": "DangKyKetHon_So", "desc": "Mẫu 02 mục 7 'Đăng ký kết hôn số'. Trống thì BỎ."},
    {"name": "Ho_ThanhVien", "desc": "MẢNG người trong bảng II của CT07 (cả dòng chủ hộ). Mỗi phần tử {hoTen, soDinhDanh, "
        "quanHeVoiChuHo}, chép nguyên văn cột 'Quan hệ với chủ hộ'. Tờ khai có mục thành viên riêng (Mẫu 03) thì lấy theo "
        "tờ khai và trả {hoTen, soDinhDanh, quanHeVoiNguoiKeKhai}."},
    {"name": "ToKhai_NoiKy", "desc": "Địa danh ở dòng ký cuối tờ khai ('Tuyên Quang, ngày … tháng … năm …')."},
    {"name": "ToKhai_NgayKy", "desc": "Ngày ký tờ khai, dd/mm/yyyy — dòng ký cuối tờ khai, ngày và tháng thường viết tay."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _date_field in ("NguoiKeKhai_NgaySinh", "NguoiKeKhai_NgayCap", "VoChong_NgayCap", "ToKhai_NgayKy"):
    COMPACT_COMP_BY_NAME[_date_field] = "x-date"
for _area_field in ("NguoiKeKhai_ThuongTru", "NguoiKeKhai_NoiOHienTai"):
    COMPACT_COMP_BY_NAME[_area_field] = "x-select-area"
COMPACT_COMP_BY_NAME["Ho_ThanhVien"] = "x-array"

UI_COMP_BY_NAME = {
    # ----- Form 1: người nộp -----
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
    # ----- Form 2: người kê khai -----
    f"{_PANEL}[fullName]": "dom-input",
    f"{_PANEL}[identityNumber]": "dom-input",
    f"{_PANEL}[identityDate]": "dom-date",
    f"{_PANEL}[identityAgency]": "dom-input",
    f"{_PANEL}[address]": "dom-input",      # Nơi ở hiện tại
    f"{_PANEL}[address1]": "dom-input",     # Đăng ký thường trú tại
    # ----- Form 2: vợ/chồng -----
    f"{_PANEL}[fullName2]": "dom-input",
    f"{_PANEL}[identityNumber1]": "dom-input",
    f"{_PANEL}[identityDate1]": "dom-date",
    f"{_PANEL}[identityAgency1]": "dom-input",
    f"{_PANEL}[dangKyKetHon]": "dom-input",
    # ----- Form 2: thành viên hộ gia đình (một ô cho nhiều người) -----
    f"{_PANEL}[thanhVien]": "dom-input",
    f"{_PANEL}[identityNumber2]": "dom-input",
    f"{_PANEL}[identityDate2]": "dom-date",
    f"{_PANEL}[identityAgency2]": "dom-input",
    # ----- Form 2: đối tượng + ký -----
    f"{_PANEL}[doiTuong]": "dom-input",
    f"{_PANEL}[TinTTTe]": "dom-select",     # "Tại"
    f"{_PANEL}[TDTTK]": "dom-date",         # "Ngày tháng năm"
    f"{_PANEL}[nguoiLamDon]": "dom-input",  # ô ký tên, nhãn ẩn
}
