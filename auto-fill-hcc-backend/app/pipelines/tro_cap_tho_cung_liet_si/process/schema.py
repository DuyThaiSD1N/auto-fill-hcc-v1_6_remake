"""Schema hai vai trò cho thủ tục trợ cấp thờ cúng liệt sĩ.

- ChuHoSo: người đề nghị/được ủy quyền thờ cúng liệt sĩ.
- NguoiNop: người thực sự nộp hồ sơ, chỉ khi tài liệu khớp mỏ neo UI.
- Các field ToKhai_/LietSi_ còn lại chỉ chứa dữ liệu nghiệp vụ của Mẫu 18.
"""

FIELDS: list[dict] = [
    # Chủ hồ sơ = người đề nghị/được ủy quyền thờ cúng.
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên chủ hồ sơ: người đề nghị tại mục 1 Mẫu 18 hoặc BÊN ĐƯỢC ỦY QUYỀN đúng nội dung thờ cúng liệt sĩ."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD đúng người, rồi giấy ủy quyền được chứng thực, sau cùng Mẫu 18; không đổi năm đơn lẻ thành 01/01/yyyy nếu có nguồn ngày đầy đủ."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ chỉ "Nam" hoặc "Nữ" khi giấy tờ của chính người đó ghi rõ; không suy từ tên hay quan hệ như "Con trai".'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND chủ hồ sơ; chỉ giữ chữ số. Ưu tiên CCCD đúng người hoặc giấy ủy quyền được chứng thực hơn số OCR mơ hồ trên Mẫu 18."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/CMND chủ hồ sơ, dd/mm/yyyy, lấy từ đúng giấy tờ của chủ hồ sơ."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD/CMND chủ hồ sơ từ đúng giấy tờ; không lấy cơ quan chứng thực/người ký."},
    {"name": "ChuHoSo_QueQuan", "desc": "Quê quán chủ hồ sơ, object {quocGia,tinh,xa,diaChi}, ưu tiên dòng Quê quán tại mục 1 Mẫu 18."},
    {"name": "ChuHoSo_NoiCuTru", "desc": "Nơi thường trú chủ hồ sơ, object {quocGia,tinh,xa,diaChi}. Ưu tiên Mẫu 18; giấy ủy quyền đúng người được bổ sung tỉnh/xã còn thiếu."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại chủ hồ sơ tại mục 1 Mẫu 18."},
    {"name": "ChuHoSo_QuocTich", "desc": "Quốc tịch chủ hồ sơ khi giấy tờ của đúng người ghi rõ."},

    # Người nộp chỉ được trích từ tài liệu đã khớp mỏ neo UI.
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp khác chủ hồ sơ, chỉ trả khi requester_context xác nhận tài liệu khớp UI."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy, lấy từ đúng tài liệu đã khớp UI."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp chỉ "Nam" hoặc "Nữ" khi đúng giấy tờ ghi rõ; không suy từ tên.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND người nộp; phải thuộc tài liệu đã khớp UI."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD/CMND người nộp, dd/mm/yyyy, từ đúng tài liệu đã khớp UI."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp giấy tờ người nộp từ đúng tài liệu đã khớp UI."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi cư trú người nộp, object {quocGia,tinh,xa,diaChi}, từ đúng tài liệu đã khớp UI."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp nếu tài liệu đúng người ghi rõ."},
    {"name": "NguoiNop_QuocTich", "desc": "Quốc tịch người nộp khi tài liệu đúng người ghi rõ."},

    # Dữ liệu nghiệp vụ Mẫu 18.
    {"name": "ToKhai_MoiQuanHeVoiLietSi", "desc": "Mối quan hệ của chủ hồ sơ với liệt sĩ, lấy tại mục 1 Mẫu 18."},
    {"name": "ToKhai_LietSiThoCung", "desc": "CHUỖI họ tên liệt sĩ mà chủ hồ sơ được ủy quyền/đề nghị thờ cúng. Có nhiều người thì nối bằng ' và '; tuyệt đối không trả array/list."},
    {"name": "LietSi_QueQuan", "desc": "Quê quán/nguyên quán liệt sĩ, trả chuỗi địa chỉ đầy đủ, không tách cấp."},
    {"name": "LietSi_SoBang", "desc": "Số Bằng Tổ quốc ghi công. Bỏ nếu không có nguồn phù hợp."},
    {"name": "LietSi_SoQuyetDinh", "desc": "Số quyết định cấp Bằng Tổ quốc ghi công. Bỏ nếu không có nguồn phù hợp."},
    {"name": "LietSi_NgayQuyetDinh", "desc": "Ngày ký quyết định/ngày cấp Bằng, dd/mm/yyyy. Bỏ nếu không có."},
    {
        "name": "ToKhai_ThanNhan",
        "desc": "Danh sách thân nhân trong bảng mục 2 Mẫu 18, mỗi item {hoTen,namSinh,namMat,noiThuongTru,moiQuanHe}; giữ thứ tự, bỏ dòng trống và gộp các dòng OCR trùng cùng người.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ChuHoSo_NgaySinh",
    "ChuHoSo_NgayCap",
    "NguoiNop_NgaySinh",
    "NguoiNop_NgayCap",
    "LietSi_NgayQuyetDinh",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "ChuHoSo_QueQuan",
    "ChuHoSo_NoiCuTru",
    "NguoiNop_NoiCuTru",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_ThanNhan"] = "x-array"

UI_COMP_BY_NAME = {
    # Người nộp hồ sơ.
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

    # Chủ hồ sơ.
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

    # Hồ sơ đính kèm.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Chi tiết Mẫu 18.
    "data[identityAgency]": "dom-select",
    "data[MqhVls1]": "dom-input",
    "data[UqTcLs]": "dom-input",
    "data[village]": "dom-select",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[address1]": "dom-input",
    "data[address2]": "dom-input",
    "data[SoBtqGc]": "dom-input",
    "data[SoQd]": "dom-input",
    "data[NgayQd]": "dom-date",
}

for _i in range(8):
    UI_COMP_BY_NAME.update({
        f"data[DataGrid][{_i}][Ht]": "dom-input",
        f"data[DataGrid][{_i}][Ns]": "dom-input",
        f"data[DataGrid][{_i}][Nm]": "dom-input",
        f"data[DataGrid][{_i}][Ntt]": "dom-input",
        f"data[DataGrid][{_i}][MqhVls]": "dom-input",
    })
