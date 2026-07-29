"""Compact schema cho thủ tục "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ" (Đơn Mẫu 26/06).

LLM chỉ trả FACT NGUỒN đọc từ giấy tờ (Đơn Mẫu 26 + CCCD + hồ sơ liệt sĩ + Bằng TQGC).
Mapper map sang field Form.io data[...] của cổng dichvucongbnv.moha.gov.vn. Tên field lấy CHUẨN
từ e-form.html (KHÔNG theo file xlsx vì field-key ở đó sai). Field lặp Phần 1 ↔ Phần 4 dùng occurrence.
"""

FIELDS: list[dict] = [
    # I. Người khai / người nộp — Đơn Mẫu 26 mục đầu + CCCD.
    {"name": "ToKhai_HoTen", "desc": "Họ tên người khai/người nộp, đầu Đơn Mẫu 26."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người khai, dd/mm/yyyy, Đơn Mẫu 26."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người khai: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_SoDinhDanh", "desc": "Số CCCD/CMND người khai, Đơn Mẫu 26."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người khai, dd/mm/yyyy."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD/CMND người khai (vd 'Cục Cảnh sát QLHC về TTXH')."},
    {
        "name": "ToKhai_QueQuan",
        "desc": (
            "Quê quán người khai, object {quocGia,tinh,xa,diaChi}, lấy dòng 'Quê quán' Đơn Mẫu 26 "
            "(ưu tiên tờ khai; không lấy quê quán trên CCCD vì có thể ghi đơn vị hành chính cũ)."
        ),
    },
    {
        "name": "ToKhai_NoiThuongTru",
        "desc": "Nơi thường trú người khai, object {quocGia,tinh,xa,diaChi}, dòng 'Nơi thường trú' Đơn Mẫu 26.",
    },
    {"name": "ToKhai_DienThoai", "desc": "Số điện thoại người khai (số đầu tiên nếu có nhiều), Đơn Mẫu 26."},
    {
        "name": "ToKhai_QuanHeVoiLietSi",
        "desc": "Quan hệ của người khai với liệt sĩ, dòng 'Thuộc diện người có công' (vd 'Con đẻ', 'Vợ').",
    },

    # II. Liệt sĩ — Đơn Mẫu 26 + Hồ sơ liệt sĩ gốc + Bằng Tổ quốc ghi công.
    {"name": "LietSi_HoTen", "desc": "Họ tên liệt sĩ được đề nghị sửa đổi hồ sơ (vd trong 'hồ sơ liệt sĩ ...')."},
    {"name": "LietSi_QueQuan", "desc": "Quê quán liệt sĩ, object {quocGia,tinh,xa,diaChi}, theo hồ sơ liệt sĩ. Bỏ nếu không có."},
    {"name": "LietSi_NgayHySinh", "desc": "Ngày hy sinh, dd/mm/yyyy, theo hồ sơ liệt sĩ/Bằng TQGC. Bỏ nếu không có."},
    {"name": "LietSi_CoQuanDonVi", "desc": "Cơ quan, đơn vị khi hy sinh, theo hồ sơ liệt sĩ. Bỏ nếu không có."},
    {"name": "LietSi_CapBac", "desc": "Cấp bậc, chức vụ khi hy sinh, theo hồ sơ liệt sĩ. Bỏ nếu không có."},
    {"name": "LietSi_SoBang", "desc": 'Bằng "Tổ quốc ghi công" số, theo Bằng TQGC. Bỏ nếu không có.'},
    {"name": "LietSi_SoQuyetDinh", "desc": "Quyết định cấp Bằng số, theo Bằng TQGC. Bỏ nếu không có."},
    {"name": "LietSi_NgayQuyetDinh", "desc": "Ngày ký Quyết định cấp Bằng, dd/mm/yyyy, theo Bằng TQGC. Bỏ nếu không có."},

    # III. Thân nhân đề nghị bổ sung — bảng lặp (Đơn Mẫu 26 + bản sao CM quan hệ).
    {
        "name": "ToKhai_ThanNhan",
        "desc": (
            "Danh sách thành viên đề nghị sửa đổi/bổ sung trong Đơn Mẫu 26. Mỗi item: "
            "{hoTen, ngaySinh, soGiayTo, moiQuanHe, noiThuongTru, hoanCanh}. "
            "ngaySinh LẤY DÒNG 'Thông tin đề nghị sửa đổi, bổ sung: ... sinh ngày dd/mm/yyyy' "
            "(KHÔNG lấy dòng 'đang ghi trong hồ sơ'). moiQuanHe từ chú thích trong ngoặc (vợ/con đẻ...). "
            "soGiayTo lấy từ bản sao chứng minh quan hệ nếu có. Giữ đúng thứ tự, bỏ item trống."
        ),
    },

    # CCCD người khai (bản sao) — bổ sung/đối chiếu định danh, cư trú.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND người khai nếu có file định danh."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND trên thẻ căn cước."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh trên CCCD, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính trên CCCD: "Nam" hoặc "Nữ".'},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy. Không lấy ngày sinh/ngày hết hạn."},
    {"name": "Person1_NoiCap", "desc": "Nơi cấp CCCD (cơ quan cấp mặt sau)."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ToKhai_NgaySinh",
    "ToKhai_NgayCap",
    "LietSi_NgayHySinh",
    "LietSi_NgayQuyetDinh",
    "Person1_NgaySinh",
    "Person1_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_QueQuan", "ToKhai_NoiThuongTru", "LietSi_QueQuan", "Person1_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_ThanNhan"] = "x-array"

# UI Form.io fields (data[...]). Tên lấy chuẩn từ e-form.html.
UI_COMP_BY_NAME = {
    # Phần 1 — Thông tin người nộp hồ sơ (occurrence 0 của field dùng chung).
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần 2 — Thông tin chủ hồ sơ.
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

    # Phần 3 — khai báo hồ sơ đính kèm.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Phần 4 — chi tiết mẫu khai người khai (occurrence 1 cho field dùng chung).
    "data[identityAgency]": "dom-select",   # Nơi cấp CMND/CCCD.
    "data[QuanHe]": "dom-input",            # Quan hệ với liệt sĩ.
    # Quê quán người khai = province/district/address (occ 1) — sau labelQueQuan trên DOM.
    # Nơi thường trú người khai = province1/district1/address1 — sau labelThuongTru.
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",

    # Thông tin liệt sĩ.
    "data[fullname1]": "dom-input",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
    "data[address2]": "dom-input",
    "data[NgayHiSinh]": "dom-date",         # Ngày hy sinh.
    "data[CoQuanDonVi]": "dom-input",
    "data[ChucVu]": "dom-input",
    "data[so]": "dom-input",                # Bằng số.
    "data[QD]": "dom-input",                # Quyết định số.
    "data[ngaycap]": "dom-date",            # Ngày ký QĐ Bằng TQGC (tên field DOM là 'ngaycap').
}

# Phần 4.2 — bảng thân nhân đề nghị bổ sung (datagrid 'dataGrid').
# Cột thật (theo header + thứ tự input trên DOM): textField1=Họ tên, NgayHiSinh1=Ngày sinh,
# textField2=Số CCCD/CMND/GKS, textField3=Mối quan hệ, textField6=Nơi thường trú, textField5=Hoàn cảnh.
for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[dataGrid][{_i}][textField1]": "dom-input",
        f"data[dataGrid][{_i}][NgayHiSinh1]": "dom-date",
        f"data[dataGrid][{_i}][textField2]": "dom-input",
        f"data[dataGrid][{_i}][textField3]": "dom-input",
        f"data[dataGrid][{_i}][textField6]": "dom-input",
        f"data[dataGrid][{_i}][textField5]": "dom-input",
    })
