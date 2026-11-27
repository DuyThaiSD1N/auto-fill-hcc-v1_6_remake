"""Compact schema cho "Giải quyết chế độ mai táng phí đối với cựu chiến binh" (2.002307) — cổng Bộ Nội vụ (Form.io).

Hồ sơ: Bản khai Mẫu số 01 Thông tư 21/2026/TT-BNV (nguồn chính) + bản sao trích lục khai tử / giấy chứng tử + giấy xác
nhận là cựu chiến binh (khoản 7 Điều 2 NĐ 150/2006/NĐ-CP) + có thể có CCCD người nhận trợ cấp.

Ba người:
- ChuHoSo_* : CÁ NHÂN NHẬN TRỢ CẤP MAI TÁNG (Mục 2a Bản khai, còn sống) = chủ hồ sơ = "người nhận mai táng phí".
- CCB_*     : CỰU CHIẾN BINH ĐÃ CHẾT (Mục 1 Bản khai, trích lục khai tử, giấy xác nhận cựu chiến binh).
- NguoiNop_*: người nộp = tài khoản đăng nhập, chỉ khi khác chủ hồ sơ và có CCCD khớp tài khoản.
"""

_AREA = ("object {quocGia,tinh,huyen,xa,chiTietDuoiXa}; huyen = quận/huyện CŨ nếu giấy có ghi (để đổi sang xã mới), "
         "chiTietDuoiXa = số nhà / thôn / xóm / tổ")

FIELDS: list[dict] = [
    # --- Cá nhân nhận trợ cấp mai táng (chủ hồ sơ) ---
    {"name": "ChuHoSo_HoTen", "desc": "Họ và tên cá nhân nhận trợ cấp mai táng ở Mục 2a Bản khai (đối chiếu CCCD đúng "
        "người). KHÔNG lấy cựu chiến binh đã chết, KHÔNG lấy cán bộ ký xác nhận."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh người nhận trợ cấp, dd/mm/yyyy. Ưu tiên CCCD đúng người, rồi Mục 2a."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính người nhận trợ cấp: "Nam" hoặc "Nữ" (CCCD, ô "Nam/Nữ" Mục 2a).'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh / CCCD người nhận trợ cấp (CCCD, Mục 2a), chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD người nhận trợ cấp, dd/mm/yyyy: mặt sau CCCD; không có CCCD thì lấy "
        "\"cấp ngày\" ở dòng giấy tờ tùy thân của người đi khai tử trên trích lục khai tử NẾU đó cùng là người này."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD người nhận trợ cấp (chức danh người ký mặt sau CCCD, hoặc \"do … cấp\" "
        "trên trích lục khai tử khi cùng người). \"Cục trưởng Cục Cảnh sát QLHC về TTXH\" → \"Cục Cảnh sát quản lý hành "
        "chính về trật tự xã hội\"."},
    {"name": "ChuHoSo_QueQuan", "desc": f"Quê quán người nhận trợ cấp trên CCCD, {_AREA}."},
    {"name": "ChuHoSo_NoiThuongTru", "desc": f"Nơi thường trú người nhận trợ cấp trên CCCD, {_AREA}."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại ở Mục 2a Bản khai, chỉ chữ số."},
    {"name": "ChuHoSo_QuanHe", "desc": "Quan hệ của người nhận trợ cấp với cựu chiến binh, NGẮN GỌN (vd \"Cháu nội\", \"Con "
        "đẻ\", \"Vợ\"): dòng \"Là (ghi rõ mối quan hệ) với cựu chiến binh\" Mục 2a, rồi \"Quan hệ với người chết\" trên "
        "trích lục khai tử. Bỏ phần giải thích trong ngoặc."},
    {"name": "ToChucNhan_Ten", "desc": "Tên tổ chức nhận trợ cấp ở Mục 2b — CHỈ khi Mục 2b thực sự ghi một tổ chức (bỏ nếu "
        "trống / \"Không áp dụng\")."},

    # --- Người nộp thay ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp — CHỈ trả theo nguoi_nop_context (thẻ CCCD khớp tài khoản)."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD người nộp, từ đúng thẻ khớp tài khoản."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy, từ đúng thẻ khớp tài khoản."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp "Nam"/"Nữ", từ đúng thẻ khớp tài khoản.'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD người nộp."},
    {"name": "NguoiNop_NoiCuTru", "desc": f"Nơi thường trú người nộp trên thẻ khớp tài khoản, {_AREA}."},

    # --- Cựu chiến binh đã chết ---
    {"name": "CCB_HoTen", "desc": "Họ và tên cựu chiến binh đã chết (Mục 1 Bản khai, trích lục khai tử, giấy xác nhận CCB)."},
    {"name": "CCB_NgaySinh", "desc": "Ngày sinh cựu chiến binh, dd/mm/yyyy (Mục 1 Bản khai → trích lục → giấy xác nhận)."},
    {"name": "CCB_GioiTinh", "desc": 'Giới tính cựu chiến binh "Nam"/"Nữ" (trích lục khai tử, giấy xác nhận CCB).'},
    {"name": "CCB_SoDinhDanh", "desc": "Số định danh cá nhân của cựu chiến binh, chỉ chữ số."},
    {"name": "CCB_QueQuan", "desc": f"Quê quán / nguyên quán cựu chiến binh (giấy xác nhận CCB \"Quê quán\"), {_AREA}. Ghi "
        "đúng địa danh CŨ như giấy kèm huyen; giấy có \"(nay là …)\" thì vẫn lấy địa danh cũ, hệ thống tự đổi."},
    {"name": "CCB_NoiThuongTru", "desc": f"Nơi cư trú cuối cùng / thường trú trước khi chết của cựu chiến binh (trích lục "
        f"\"Nơi cư trú cuối cùng\" → giấy xác nhận \"Nơi thường trú trước khi chết\" → xác nhận UBND), {_AREA}."},
    {"name": "CCB_DoiTuong", "desc": "Diện đối tượng: \"Cựu chiến binh\" kèm tóm tắt ngắn trong ngoặc từ giấy xác nhận (kháng "
        "chiến tham gia, năm nhập ngũ, năm phục viên/xuất ngũ), vd \"Cựu chiến binh (kháng chiến chống Mỹ, nhập ngũ 1971, "
        "phục viên 1976)\"."},
    {"name": "CCB_NgayChet", "desc": "Ngày chết / từ trần, dd/mm/yyyy — ưu tiên \"Đã chết vào lúc\" trên trích lục khai tử."},
    {"name": "CCB_LoaiGiayChungTu", "desc": '"Trích lục khai tử" / "Giấy chứng tử" / "Giấy báo tử" — loại giấy báo tử trong hồ sơ.'},
    {"name": "CCB_SoGiayChungTu", "desc": "Số của trích lục khai tử / giấy chứng tử ở góc trái (vd \"152/TLKT\"), KHÔNG phải số "
        "chứng thực bản sao."},
    {"name": "CCB_NgayCapGiayChungTu", "desc": "Ngày ký trích lục khai tử / giấy chứng tử (dòng địa danh, ngày tháng năm góc "
        "phải), dd/mm/yyyy. KHÔNG lấy ngày chứng thực bản sao, KHÔNG lấy ngày chết."},
    {"name": "CCB_NoiCapGiayChungTu", "desc": "Cơ quan cấp trích lục / giấy chứng tử (tên cơ quan góc trái, vd \"Ủy ban nhân "
        "dân xã X, tỉnh Y\"), viết đầy đủ \"Ủy ban nhân dân\" thay \"UBND\"."},

    {"name": "HoSoDinhKem", "desc": "Danh sách thành phần hồ sơ THỰC CÓ, mỗi item {tenGiayTo, loaiBan}; tenGiayTo kèm số, "
        "ngày, cơ quan nếu đọc được (vd \"Bản sao chứng thực Trích lục khai tử số 152/TLKT ngày 10/11/2026 của UBND xã "
        "X\"); bản chứng thực / photo ghi \"Bản sao\". Không liệt kê CCCD."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap", "CCB_NgaySinh",
              "CCB_NgayChet", "CCB_NgayCapGiayChungTu"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_QueQuan", "ChuHoSo_NoiThuongTru", "NguoiNop_NoiCuTru", "CCB_QueQuan", "CCB_NoiThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["HoSoDinhKem"] = "x-array"

UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp. data[fullname]/[birthday]/[gender] trùng key khối người có công từ trần, data[province]/
    # [district]/[address] trùng key khối trú quán người nhận mai táng phí → khối Người nộp luôn occurrence 0.
    "data[isOwnerDossierCheck]": "dom-checkbox",
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
    # Phần II — chủ hồ sơ = cá nhân nhận trợ cấp mai táng.
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
    "data[ghiChu]": "dom-input",
    # Phần III — người có công từ trần = cựu chiến binh (fullname/birthday/gender occurrence 1).
    "data[province2]": "dom-select",   # Nguyên quán.
    "data[district2]": "dom-select",
    "data[address2]": "dom-input",
    "data[province3]": "dom-select",   # Trú quán.
    "data[district3]": "dom-select",
    "data[address3]": "dom-input",
    "data[ttncc_DoiTuong]": "dom-input",
    "data[ttncc_NgayTuTran]": "dom-date",
    "data[ttncc_GiayChungTu]": "dom-input",
    "data[ttncc_NgayCap]": "dom-date",
    "data[ttncc_CoQuanCap]": "dom-input",
    # Phần IV — người nhận mai táng phí (= chủ hồ sơ). Trú quán dùng lại data[province]/[district]/[address] occ 1.
    "data[fullname1]": "dom-input",
    "data[birthday1]": "dom-date",
    "data[gender1]": "dom-select",
    "data[province1]": "dom-select",   # Nguyên quán.
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[ttnn_QuanHe]": "dom-input",
}

# Datagrid "Hồ sơ kèm theo gồm" (FE tự bấm "Thêm dòng" theo chỉ số lớn nhất).
MAX_HO_SO_ROWS = 8
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
