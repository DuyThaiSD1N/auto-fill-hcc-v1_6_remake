"""Compact schema cho thủ tục "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ" (Đơn Mẫu 18).

LLM trả FACT NGUỒN đọc từ giấy tờ (Đơn Mẫu 18 + CCCD + Bằng TQGC + văn bản ủy quyền + trích lục khai tử).
Mapper map sang field Form.io data[...]. Tên field lấy CHUẨN từ e-form.html (không tin xlsx).
Field lặp Phần 1 ↔ Phần 4 dùng occurrence.
"""

FIELDS: list[dict] = [
    # I. Người đề nghị (đứng ra thờ cúng) — Đơn Mẫu 18 + CCCD.
    {"name": "ToKhai_HoTen", "desc": "Họ tên người đề nghị/người nộp, Đơn Mẫu 18."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người đề nghị, dd/mm/yyyy, Đơn Mẫu 18."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_SoDinhDanh", "desc": "Số CCCD/CMND người đề nghị."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người đề nghị, dd/mm/yyyy."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD/CMND người đề nghị (vd 'Cục Cảnh sát QLHC về TTXH')."},
    {
        "name": "ToKhai_QueQuan",
        "desc": (
            "Quê quán người đề nghị, object {quocGia,tinh,xa,diaChi}, dòng 'Quê quán' Đơn Mẫu 18 "
            "(ưu tiên tờ khai; không lấy quê quán trên CCCD vì có thể ghi đơn vị hành chính cũ)."
        ),
    },
    {
        "name": "ToKhai_NoiThuongTru",
        "desc": "Nơi thường trú người đề nghị, object {quocGia,tinh,xa,diaChi}, dòng 'Nơi thường trú' Đơn Mẫu 18.",
    },
    {"name": "ToKhai_DienThoai", "desc": "Số điện thoại người đề nghị, Đơn Mẫu 18."},
    {"name": "ToKhai_MoiQuanHeVoiLietSi", "desc": "Mối quan hệ của người đề nghị với liệt sĩ (vd 'Anh ruột')."},
    {
        "name": "ToKhai_LietSiThoCung",
        "desc": "Họ tên liệt sĩ được thờ cúng/được ủy quyền thờ cúng (Đơn Mẫu 18/văn bản ủy quyền).",
    },

    # I-b. Liệt sĩ + Bằng Tổ quốc ghi công — Đơn Mẫu 18 + Bằng TQGC.
    {
        "name": "LietSi_QueQuan",
        "desc": "Quê quán/nguyên quán liệt sĩ, TRẢ CHUỖI ĐỊA CHỈ ĐẦY ĐỦ (không tách cấp), theo Đơn Mẫu 18/Bằng TQGC.",
    },
    {"name": "LietSi_SoBang", "desc": 'Số Bằng "Tổ quốc ghi công" (vd "7L-496x"), theo Bằng TQGC. Bỏ nếu không có.'},
    {"name": "LietSi_SoQuyetDinh", "desc": "Quyết định cấp Bằng số (vd '1455/TTg'), theo Bằng TQGC. Bỏ nếu không có."},
    {"name": "LietSi_NgayQuyetDinh", "desc": "Ngày ký Quyết định/ngày cấp Bằng, dd/mm/yyyy, theo Bằng TQGC. Bỏ nếu không có."},

    # II. Thân nhân liệt sĩ — bảng lặp (Đơn Mẫu 18 + trích lục khai tử).
    {
        "name": "ToKhai_ThanNhan",
        "desc": (
            "Danh sách thân nhân liệt sĩ trong Đơn Mẫu 18. Mỗi item: "
            "{hoTen, namSinh, namMat, noiThuongTru, moiQuanHe}. "
            "namSinh/namMat chỉ là NĂM (vd '1931', '2026'); namMat lấy từ trích lục khai tử nếu có. "
            "moiQuanHe là quan hệ của thân nhân với liệt sĩ (Bố đẻ/Mẹ đẻ...). Giữ đúng thứ tự, bỏ item trống."
        ),
    },

    # CCCD người đề nghị — bổ sung/đối chiếu định danh, cư trú.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND người đề nghị nếu có file định danh."},
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
for _name in ("ToKhai_NgaySinh", "ToKhai_NgayCap", "LietSi_NgayQuyetDinh", "Person1_NgaySinh", "Person1_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_QueQuan", "ToKhai_NoiThuongTru", "Person1_NoiCuTru"):
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

    # Phần 2 — Thông tin chủ hồ sơ (owner KHÔNG có ngày cấp trên form này).
    "data[chonDoiTuong1]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerNation]": "dom-select",

    # Phần 3 — khai báo hồ sơ đính kèm.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Phần 4 — chi tiết mẫu khai người đề nghị (occurrence 1 cho field dùng chung).
    "data[identityAgency]": "dom-select",   # Nơi cấp.
    "data[MqhVls1]": "dom-input",           # Mối quan hệ với liệt sĩ.
    "data[UqTcLs]": "dom-input",            # Được ủy quyền thờ cúng liệt sĩ (họ tên liệt sĩ).
    # Quê quán người khai = province/village/address (occ 1) — sau nhãn "Quê quán:".
    "data[village]": "dom-select",
    # Nơi thường trú người khai = province1/village1/address1 — sau nhãn "thường trú:".
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[address1]": "dom-input",

    # Thông tin liệt sĩ + Bằng TQGC.
    "data[address2]": "dom-input",          # Quê quán liệt sĩ (1 ô text tự do).
    "data[SoBtqGc]": "dom-input",           # Số bằng.
    "data[SoQd]": "dom-input",              # Quyết định số.
    "data[NgayQd]": "dom-date",             # Ngày cấp bằng.
}

# Phần 4.2 — bảng thân nhân liệt sĩ (datagrid 'DataGrid').
# Cột thật: Ht=Họ tên, Ns=Năm sinh, Nm=Năm mất, Ntt=Nơi thường trú, MqhVls=Mối quan hệ với liệt sĩ.
for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[DataGrid][{_i}][Ht]": "dom-input",
        f"data[DataGrid][{_i}][Ns]": "dom-input",
        f"data[DataGrid][{_i}][Nm]": "dom-input",
        f"data[DataGrid][{_i}][Ntt]": "dom-input",
        f"data[DataGrid][{_i}][MqhVls]": "dom-input",
    })
