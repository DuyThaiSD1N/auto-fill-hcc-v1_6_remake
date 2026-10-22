"""Compact schema cho "Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công ... và giấy chứng nhận thân nhân
liệt sĩ" (1.010814, Đơn đề nghị Mẫu số 25 Phụ lục I NĐ 131/2021/NĐ-CP).

LLM chỉ trả FACT NGUỒN đọc từ giấy tờ (Đơn M25 + CCCD + Giấy chứng nhận đã cấp). Mapper mới map sang field
Form.io `data[...]` theo Mapping_Cap_lai_GCN_than_nhan_liet_si_Bo_Noi_vu.xlsx. Phần III (mẫu khai Đơn M25) dùng
lại tên field của Phần I (fullname/birthday/gender/identityNumber/identityDate/phoneNumber/province/address)
nên điền bằng occurrence 1.
"""

FIELDS: list[dict] = [
    # Đơn đề nghị Mẫu số 25 — nguồn chính cho người làm đơn và nội dung đề nghị.
    {"name": "Don_HoTen", "desc": "Họ và tên người làm đơn, dòng 'Họ và tên' Đơn Mẫu 25."},
    {"name": "Don_NgaySinh", "desc": "Ngày tháng năm sinh người làm đơn, dd/mm/yyyy."},
    {"name": "Don_GioiTinh", "desc": 'Giới tính người làm đơn, dòng "Nam/Nữ": "Nam" hoặc "Nữ".'},
    {"name": "Don_SoDinhDanh", "desc": "Số CCCD/CMND người làm đơn, dòng 'CCCD/CMND số'."},
    {"name": "Don_NgayCap", "desc": "Ngày cấp CCCD/CMND trên Đơn, dd/mm/yyyy."},
    {"name": "Don_NoiCap", "desc": "Nơi cấp CCCD/CMND trên Đơn (vd 'Bộ Công an')."},
    {"name": "Don_QueQuan", "desc": "Quê quán người làm đơn, object {quocGia,tinh,xa,chiTietDuoiXa}, dòng 'Quê quán'."},
    {"name": "Don_NoiThuongTru", "desc": "Nơi thường trú người làm đơn, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại người làm đơn."},
    {
        "name": "Don_DienNguoiCoCong",
        "desc": (
            "Nguyên văn phần ghi sau 'Tôi là' (diện người có công, vd 'Thân nhân liệt sĩ (con của liệt sĩ "
            "Nguyễn Văn A)', 'Thương binh'). KHÔNG phải họ tên người làm đơn."
        ),
    },
    {"name": "Don_SoQuyetDinh", "desc": "Số quyết định hưởng trợ cấp, dòng 'Đã được hưởng trợ cấp theo quyết định số'."},
    {"name": "Don_NgayQuyetDinh", "desc": "Ngày của quyết định hưởng trợ cấp, dd/mm/yyyy."},
    {"name": "Don_CoQuanQuyetDinh", "desc": "Người/cơ quan ra quyết định hưởng trợ cấp (phần sau chữ 'của')."},
    {
        "name": "Don_LoaiGiayChungNhan",
        "desc": (
            "Loại giấy chứng nhận đề nghị cấp, chú thích (1)/(5) của Đơn, vd 'Giấy chứng nhận thân nhân liệt "
            "sĩ', 'Giấy chứng nhận thương binh'. Viết hoa chữ đầu 'Giấy chứng nhận ...'."
        ),
    },
    {
        "name": "Don_LoaiDeNghi",
        "desc": (
            'Loại đề nghị: "Cấp lại" (giấy bị mất/hư hỏng/rách nát), "Cấp bổ sung" (bổ sung/thay đổi '
            'thông tin) hoặc "Cấp lại và cấp bổ sung" nếu lý do nêu cả hai. Suy theo tiêu đề đã gạch/khoanh '
            "và mục Lý do."
        ),
    },
    {"name": "Don_LyDo", "desc": "Nguyên văn mục 'Lý do' (6) của Đơn."},
    # Giấy chứng nhận đã cấp (bản cũ bị mất/hư hỏng) — chỉ là nguồn dự phòng.
    {"name": "GCN_LoaiGiayChungNhan", "desc": "Tiêu đề giấy chứng nhận đã cấp, vd 'Giấy chứng nhận thân nhân liệt sĩ'."},
    {"name": "GCN_HoTen", "desc": "Họ và tên người được cấp ghi trên giấy chứng nhận đã cấp."},
    {"name": "GCN_QueQuan", "desc": "Quê quán ghi trên giấy chứng nhận đã cấp, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "GCN_SoQuyetDinh", "desc": "Số quyết định ghi trên giấy chứng nhận đã cấp ('Được cấp theo Quyết định số')."},
    {"name": "GCN_NgayQuyetDinh", "desc": "Ngày quyết định ghi trên giấy chứng nhận đã cấp, dd/mm/yyyy."},
    {"name": "GCN_CoQuanQuyetDinh", "desc": "Cơ quan ra quyết định ghi trên giấy chứng nhận đã cấp."},
    # CCCD người làm đơn.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/thẻ căn cước."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh cá nhân trên CCCD."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh trên CCCD, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính trên CCCD: "Nam" hoặc "Nữ".'},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD, dd/mm/yyyy. Không lấy ngày sinh/ngày hết hạn."},
    {"name": "Person1_NoiCap", "desc": "Cơ quan cấp CCCD (thẻ mẫu 2024 in 'BỘ CÔNG AN')."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi cư trú/thường trú trên CCCD, object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Don_NgaySinh",
    "Don_NgayCap",
    "Don_NgayQuyetDinh",
    "GCN_NgayQuyetDinh",
    "Person1_NgaySinh",
    "Person1_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Don_QueQuan", "Don_NoiThuongTru", "GCN_QueQuan", "Person1_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

MAX_HO_SO_ROWS = 4

UI_COMP_BY_NAME = {
    # Phần I — người nộp. fullname/birthday/identityNumber/chonDoiTuong cổng khoá theo tài khoản → không phát
    # ở occurrence 0 (mapper chỉ phát ở occurrence 1 cho Phần III).
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",   # Nhãn Phường/Xã.
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ (người được cấp bổ sung/cấp lại).
    "data[chonDoiTuong1]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerNation]": "dom-select",
    # Phần III — mẫu khai Đơn M25 (field dùng chung tên Phần I đi occurrence 1).
    "data[loaiDeNghi]": "dom-select",
    "data[loaiGiayChungNhan]": "dom-input",
    "data[identityAgency]": "dom-select",
    "data[province1]": "dom-select",  # Quê quán tỉnh.
    "data[village1]": "dom-select",   # Quê quán phường/xã.
    "data[address1]": "dom-input",    # Quê quán số nhà, đường.
    "data[village]": "dom-select",    # Thường trú phường/xã (tỉnh = data[province]#1).
    "data[dienNguoiCoCong]": "dom-input",
    "data[sqdTroCap]": "dom-input",
    "data[nqdTroCap]": "dom-date",
    "data[noiCap]": "dom-input",
    "data[lyDo]": "dom-input",
}
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
