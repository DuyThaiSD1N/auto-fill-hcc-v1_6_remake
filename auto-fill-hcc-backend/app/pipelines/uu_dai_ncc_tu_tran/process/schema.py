"""Compact schema cho thủ tục "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần".

Nguồn: Bản khai Mẫu số 12 (chính) + CCCD + trích lục khai tử + biên bản họp GĐ + danh sách đề nghị.
ĐẶC THÙ: occurrence 0 = NGƯỜI KHAI/nhận trợ cấp (còn sống), occurrence 1 = NGƯỜI CÓ CÔNG TỪ TRẦN
(2 người KHÁC nhau, không như các thủ tục người có công khác). Mục 2 (mai táng phí) là field nạp động
(không có trong HTML tĩnh) nên KHÔNG điền. Tên field lấy CHUẨN từ e-form.html.
"""

FIELDS: list[dict] = [
    # === Người khai / người nhận trợ cấp một lần (còn sống) — Bản khai Mẫu 12 + CCCD ===
    {"name": "ToKhai_HoTen", "desc": "Họ tên người khai/người nhận trợ cấp một lần (còn sống)."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người khai, dd/mm/yyyy."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người khai: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_SoDinhDanh", "desc": "Số CCCD/CMND người khai."},
    {"name": "ToKhai_NgayCap", "desc": "Ngày cấp CCCD/CMND người khai, dd/mm/yyyy."},
    {"name": "ToKhai_NoiCap", "desc": "Nơi cấp CCCD/CMND người khai."},
    {"name": "ToKhai_QueQuan", "desc": "Quê quán người khai, object {quocGia,tinh,xa,diaChi}."},
    {"name": "ToKhai_NoiThuongTru", "desc": "Nơi thường trú người khai, object {quocGia,tinh,xa,diaChi}."},
    {"name": "ToKhai_DienThoai", "desc": "Số điện thoại người khai."},
    {"name": "ToKhai_LoaiGiayTo", "desc": 'Loại giấy tờ định danh người khai: "Căn cước công dân"/"CMND"/"Hộ chiếu". Mặc định "Căn cước công dân".'},
    {"name": "ToKhai_MoiQuanHeVoiTuTran", "desc": "Quan hệ của người khai với người có công từ trần (vd 'Con đẻ')."},

    # === Người có công TỪ TRẦN — Bản khai Mẫu 12 mục 1 + trích lục khai tử ===
    {"name": "TuTran_HoTen", "desc": "Họ tên người có công đã từ trần (Mục 1 bản khai)."},
    {"name": "TuTran_NgaySinh", "desc": "Ngày sinh người từ trần, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "TuTran_GioiTinh", "desc": 'Giới tính người từ trần: "Nam" hoặc "Nữ".'},
    {"name": "TuTran_QueQuan", "desc": "Quê quán người từ trần, object {quocGia,tinh,xa,diaChi}."},
    {"name": "TuTran_NoiThuongTru", "desc": "Nơi thường trú người từ trần, object {quocGia,tinh,xa,diaChi}."},
    {"name": "TuTran_DoiTuong", "desc": "Thuộc đối tượng người có công (vd 'Vợ liệt sĩ (Nguyễn Văn Giá)'), Mục 1."},
    {"name": "TuTran_SoQDHuongTroCap", "desc": "Quyết định hưởng trợ cấp số, Mục 1. Bỏ nếu trống."},
    {"name": "TuTran_NgayQDHuongTroCap", "desc": "Ngày Quyết định hưởng trợ cấp, dd/mm/yyyy. Bỏ nếu trống."},
    {"name": "TuTran_NoiCapQD", "desc": "Cơ quan ra Quyết định hưởng trợ cấp. Bỏ nếu trống."},
    {"name": "TuTran_TiLeTonThuong", "desc": "Tỷ lệ tổn thương cơ thể (nếu có). Bỏ nếu trống."},
    {"name": "TuTran_NgayTuTran", "desc": "Ngày từ trần/ngày chết, dd/mm/yyyy (trích lục khai tử)."},
    {"name": "TuTran_SoGiayBaoTu", "desc": "Số giấy báo tử/trích lục khai tử (vd '576/2026/TLKT-BS')."},
    {"name": "TuTran_NgayCapBaoTu", "desc": "Ngày cấp/ngày ký giấy báo tử/trích lục khai tử, dd/mm/yyyy."},
    {"name": "TuTran_NoiCapBaoTu", "desc": "Nơi cấp/nơi đăng ký khai tử (vd 'UBND phường Song Liễu')."},
    {"name": "TuTran_MucTroCap", "desc": "Mức trợ cấp, phụ cấp hằng tháng/trợ cấp một lần (vd '2.789.000'). Bỏ nếu trống."},
    {"name": "TuTran_TroCapDaNhanDenHet", "desc": "Trợ cấp/phụ cấp hằng tháng đã nhận đến hết tháng nào (vd 'Tháng 04/2026'). Bỏ nếu trống."},

    # === Cá nhân nhận mai táng phí (Mục 2a) — SECTION RIÊNG, có thể KHÁC người khai ===
    {"name": "MaiTang_HoTen", "desc": "Họ tên cá nhân nhận mai táng phí, Mục 2a bản khai. Bỏ nếu Mục 2a trống/là tổ chức."},
    {"name": "MaiTang_NgaySinh", "desc": "Ngày sinh cá nhân nhận mai táng phí, dd/mm/yyyy, Mục 2a."},
    {"name": "MaiTang_GioiTinh", "desc": 'Giới tính cá nhân nhận mai táng phí: "Nam"/"Nữ", Mục 2a.'},
    {"name": "MaiTang_SoDinhDanh", "desc": "Số CCCD/CMND cá nhân nhận mai táng phí, Mục 2a."},
    {"name": "MaiTang_NgayCap", "desc": "Ngày cấp CCCD/CMND cá nhân nhận mai táng phí, dd/mm/yyyy, Mục 2a."},
    {"name": "MaiTang_NoiCap", "desc": "Nơi cấp CCCD/CMND cá nhân nhận mai táng phí, Mục 2a."},
    {"name": "MaiTang_LoaiGiayTo", "desc": 'Loại giấy tờ cá nhân nhận mai táng phí: "Căn cước công dân"/"CMND"/"Hộ chiếu".'},
    {"name": "MaiTang_QueQuan", "desc": "Quê quán cá nhân nhận mai táng phí, object {quocGia,tinh,xa,diaChi}, Mục 2a."},
    {"name": "MaiTang_NoiThuongTru", "desc": "Nơi thường trú cá nhân nhận mai táng phí, object {quocGia,tinh,xa,diaChi}, Mục 2a."},
    {"name": "MaiTang_DienThoai", "desc": "Số điện thoại cá nhân nhận mai táng phí, Mục 2a."},
    {"name": "MaiTang_MoiQuanHe", "desc": "Quan hệ của cá nhân nhận mai táng phí với người có công từ trần, Mục 2a."},

    # === Danh sách thân nhân (Mục 4a) ===
    {
        "name": "ToKhai_ThanNhan",
        "desc": (
            "Danh sách thân nhân trong bản khai/biên bản họp gia đình. Mỗi item: "
            "{hoTen, namSinh, noiThuongTru, quanHe, ngheNghiep, hoanCanh}. namSinh chỉ là NĂM. "
            "quanHe là quan hệ với người có công. Giữ đúng thứ tự, bỏ item trống."
        ),
    },

    # === Con NCC từ đủ 18 tuổi đi học/khuyết tật (Mục 4b) — thường trống ===
    {
        "name": "ToKhai_ConNCC",
        "desc": (
            "Danh sách con người có công từ đủ 18 tuổi còn đi học/bị khuyết tật (Mục 4b). Mỗi item: "
            "{hoTen, namSinh, thoiDiemKhuyetTat, thoiDiemKetThucPhoThong, tenCoSoGiaoDuc, thoiGianBatDauHoc}. "
            "Bỏ field nếu bản khai không có mục này."
        ),
    },

    # === CCCD người khai ===
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
    "ToKhai_NgaySinh", "ToKhai_NgayCap", "Person1_NgaySinh", "Person1_NgayCap",
    "TuTran_NgaySinh", "TuTran_NgayTuTran", "TuTran_NgayCapBaoTu", "TuTran_NgayQDHuongTroCap",
    "MaiTang_NgaySinh", "MaiTang_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "ToKhai_QueQuan", "ToKhai_NoiThuongTru", "TuTran_QueQuan", "TuTran_NoiThuongTru", "Person1_NoiCuTru",
    "MaiTang_QueQuan", "MaiTang_NoiThuongTru",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_ThanNhan"] = "x-array"
COMPACT_COMP_BY_NAME["ToKhai_ConNCC"] = "x-array"

# UI Form.io fields (data[...]). Tên lấy chuẩn từ e-form.html.
UI_COMP_BY_NAME = {
    # Phần 1 — người nộp (occ 0 = người khai còn sống).
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

    # Phần 2 — chủ hồ sơ.
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

    # Mục 1 — Người có công TỪ TRẦN (occ 1 cho fullname/birthday/gender/province/address).
    # Quê quán = province(occ1)/village/address(occ1); Nơi thường trú = province1/village1/address1.
    "data[village]": "dom-select",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[address1]": "dom-input",
    "data[doiTuong]": "dom-input",
    "data[SoQDTH]": "dom-input",
    "data[ncNgayCap]": "dom-date",
    "data[noiCap]": "dom-input",
    "data[TiLeTonThuong]": "dom-input",
    "data[NgayTuTran]": "dom-date",
    "data[SoGiayBaoTu]": "dom-input",
    "data[ncNgayCap1]": "dom-date",
    "data[noiCap1]": "dom-input",
    "data[MucTroCap]": "dom-input",
    "data[TroCapPhuCap]": "dom-date",

    # Mục 2 — Loại nhận mai táng phí (bắt buộc) + panel động "Cá nhân nhận mai táng phí"
    # (hiện sau khi chọn loaiNhan="Cá nhân"; các field "1"-suffix, = người khai/người nhận).
    "data[loaiNhan]": "dom-select",
    "data[fullname1]": "dom-input",
    "data[birthday1]": "dom-date",
    "data[nnLoaiGiayTo1]": "dom-select",
    "data[gender1]": "dom-select",
    "data[identityNumber1]": "dom-input",
    "data[identityDate1]": "dom-date",
    "data[identityAgency1]": "dom-select",
    "data[province2]": "dom-select",   # Quê quán tỉnh (mai táng cá nhân).
    "data[village2]": "dom-select",
    "data[address2]": "dom-input",
    "data[province3]": "dom-select",   # Thường trú tỉnh (mai táng cá nhân).
    "data[village3]": "dom-select",
    "data[address3]": "dom-input",
    "data[moiQH]": "dom-input",         # Mối quan hệ (mai táng cá nhân).
    # data[phoneNumber] (Điện thoại mai táng) reuse tên Phần 1 → dùng occurrence 1 (xem mapper).

    # Mục 3 — Người nhận trợ cấp một lần (= người khai).
    "data[fullname2]": "dom-input",
    "data[phoneNumber2]": "dom-input",
    "data[birthday2]": "dom-date",
    "data[nnLoaiGiayTo2]": "dom-select",
    "data[gender2]": "dom-select",
    "data[identityNumber2]": "dom-input",
    "data[identityDate2]": "dom-date",
    "data[identityAgency2]": "dom-select",
    "data[province5]": "dom-select",   # Quê quán tỉnh.
    "data[village5]": "dom-select",
    "data[address5]": "dom-input",
    "data[province6]": "dom-select",   # Thường trú tỉnh.
    "data[village6]": "dom-select",
    "data[address6]": "dom-input",
    "data[moiQH1]": "dom-input",
}

# Mục 4a — Danh sách thân nhân (datagrid 'dataGrid').
# Cột: textField=Họ tên, textField1=Năm sinh, textField2=Nơi thường trú, textField3=Quan hệ,
# textField4=Nghề nghiệp, textField5=Hoàn cảnh hiện tại.
for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[dataGrid][{_i}][textField]": "dom-input",
        f"data[dataGrid][{_i}][textField1]": "dom-input",
        f"data[dataGrid][{_i}][textField2]": "dom-input",
        f"data[dataGrid][{_i}][textField3]": "dom-input",
        f"data[dataGrid][{_i}][textField4]": "dom-input",
        f"data[dataGrid][{_i}][textField5]": "dom-input",
    })

# Mục 4b — Con NCC từ 18 tuổi đi học/khuyết tật (datagrid 'dataGrid1').
# Cột: textField=Họ tên, textField1=Năm sinh, textField2=Thời điểm bị khuyết tật,
# textField3=Thời điểm kết thúc phổ thông, textField4=Tên cơ sở giáo dục, textField5=Thời gian bắt đầu học.
for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[dataGrid1][{_i}][textField]": "dom-input",
        f"data[dataGrid1][{_i}][textField1]": "dom-input",
        f"data[dataGrid1][{_i}][textField2]": "dom-input",
        f"data[dataGrid1][{_i}][textField3]": "dom-input",
        f"data[dataGrid1][{_i}][textField4]": "dom-input",
        f"data[dataGrid1][{_i}][textField5]": "dom-input",
    })
