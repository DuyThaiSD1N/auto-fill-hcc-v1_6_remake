"""Compact schema cho thủ tục "Thăm viếng mộ liệt sĩ" (Giấy giới thiệu Mẫu 42 / Đơn Mẫu 31).

LLM trả FACT NGUỒN đọc từ giấy tờ (Giấy giới thiệu + CCCD + Bằng TQGC/trích lục hồ sơ liệt sĩ).
Mapper map sang field Form.io data[...]. Tên field lấy CHUẨN từ fill thăm viếng.html (không tin xlsx).
Field lặp Phần 1 ↔ Phần 4 dùng occurrence.
"""

FIELDS: list[dict] = [
    # I. Người khai / người được giới thiệu — Giấy giới thiệu + CCCD.
    {"name": "ToKhai_HoTen", "desc": "Họ tên người được giới thiệu, dòng 'Ông (bà)' Giấy giới thiệu."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người khai, dd/mm/yyyy (thường lấy CCCD)."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người khai: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_SoDinhDanh", "desc": "Số CCCD/CMND người khai."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người khai, dd/mm/yyyy."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD/CMND người khai (vd 'Cục Cảnh sát QLHC về TTXH – Bộ Công an')."},
    {
        "name": "ToKhai_NoiThuongTru",
        "desc": (
            "Nơi thường trú người khai, object {quocGia,tinh,xa,diaChi}, dòng 'thường trú tại' Giấy giới thiệu "
            "(ưu tiên tờ khai; CCCD bổ sung khi thiếu)."
        ),
    },
    {"name": "ToKhai_DienThoai", "desc": "Số điện thoại người khai nếu có."},
    {"name": "ToKhai_LoaiGiayTo", "desc": 'Loại giấy tờ định danh của người khai: "CCCD"/"CMND"/"Hộ chiếu". Mặc định CCCD.'},
    {
        "name": "ToKhai_QuanHeVoiLietSi",
        "desc": "Quan hệ của người khai với liệt sĩ, dòng 'Mối quan hệ với liệt sĩ' (vd 'Cháu ruột', 'Con đẻ').",
    },

    # II. Liệt sĩ — Giấy giới thiệu (tên) + Bằng TQGC / trích lục hồ sơ liệt sĩ (chi tiết).
    {"name": "LietSi_HoTen", "desc": "Họ tên liệt sĩ cần thăm viếng (dòng '... thăm viếng phần mộ liệt sĩ ...')."},
    {"name": "LietSi_QueQuan", "desc": "Quê quán liệt sĩ, object {quocGia,tinh,xa,diaChi}, theo Bằng TQGC/trích lục. Bỏ nếu không có."},
    {"name": "LietSi_CoQuanDonVi", "desc": "Cơ quan, đơn vị khi hy sinh, theo trích lục hồ sơ liệt sĩ. Bỏ nếu không có."},
    {"name": "LietSi_CapBac", "desc": "Cấp bậc, chức vụ khi hy sinh, theo trích lục. Bỏ nếu không có."},
    {"name": "LietSi_NgayHySinh", "desc": "Ngày hy sinh, dd/mm/yyyy, theo Bằng TQGC/trích lục. Bỏ nếu không có."},
    {"name": "LietSi_NoiHySinh", "desc": "Nơi liệt sĩ đã hy sinh, theo trích lục/giấy xác nhận Mẫu 44. Bỏ nếu không có."},
    {"name": "LietSi_SoBang", "desc": 'Số Bằng "Tổ quốc ghi công", theo Bằng TQGC. Bỏ nếu không có.'},

    # III. Người cùng đi thăm viếng — bảng lặp (Giấy giới thiệu + CCCD người đi cùng).
    {
        "name": "ToKhai_NguoiCungDi",
        "desc": (
            "Danh sách người cùng đi thăm viếng trong Giấy giới thiệu. Mỗi item: "
            "{hoTen, ngaySinh, soGiayTo, ngayCap, noiCap, moiQuanHe}. ngaySinh/ngayCap dd/mm/yyyy. "
            "moiQuanHe là quan hệ của người đi cùng với liệt sĩ. Giữ đúng thứ tự, bỏ item trống. "
            "KHÔNG đưa chính người khai (người được giới thiệu ở mục đầu) vào danh sách này."
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
for _name in ("ToKhai_NgaySinh", "ToKhai_NgayCap", "LietSi_NgayHySinh", "Person1_NgaySinh", "Person1_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ToKhai_NoiThuongTru", "LietSi_QueQuan", "Person1_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_NguoiCungDi"] = "x-array"

# UI Form.io fields (data[...]). Tên lấy chuẩn từ fill thăm viếng.html.
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

    # Phần 4 — chi tiết mẫu khai (occurrence 1 cho fullname/birthday/gender/identityNumber/identityDate/phoneNumber).
    "data[province3]": "dom-select",    # Thường trú người khai — tỉnh.
    "data[village3]": "dom-select",     # Thường trú — phường/xã.
    "data[address3]": "dom-input",      # Thường trú — số nhà/đường.
    "data[LoaiGiayTo]": "dom-select",   # Chọn loại giấy tờ.
    "data[identityAgency]": "dom-select",  # Nơi cấp CMND/CCCD.
    "data[qheLSi]": "dom-input",        # Quan hệ với liệt sĩ.

    # Thông tin liệt sĩ.
    "data[fullname1]": "dom-input",
    "data[province4]": "dom-select",    # Quê quán liệt sĩ — tỉnh.
    "data[village4]": "dom-select",
    "data[address4]": "dom-input",
    "data[Coquandonvihisinh]": "dom-input",
    "data[CapBacChucVuKhiHiSinh]": "dom-input",
    "data[ngayHiSinh]": "dom-date",
    "data[noiHiSinh]": "dom-input",
    "data[soBang]": "dom-input",
}

# Phần III-A — bảng người cùng đi (datagrid 'dataGrid2').
# Cột thật: textField2=Họ tên, NgayThangNamSinh=Ngày sinh, SoCCCMND=Số CCCD, asd=Ngày cấp,
# asd1=Nơi cấp, QuanHeVoiLietSiDiCung=Quan hệ với liệt sĩ.
for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[dataGrid2][{_i}][textField2]": "dom-input",
        f"data[dataGrid2][{_i}][NgayThangNamSinh]": "dom-date",
        f"data[dataGrid2][{_i}][SoCCCMND]": "dom-input",
        f"data[dataGrid2][{_i}][asd]": "dom-input",
        f"data[dataGrid2][{_i}][asd1]": "dom-input",
        f"data[dataGrid2][{_i}][QuanHeVoiLietSiDiCung]": "dom-input",
    })
