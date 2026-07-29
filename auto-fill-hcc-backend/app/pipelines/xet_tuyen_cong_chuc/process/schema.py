"""Compact schema for "Xét tuyển công chức".

The LLM returns OCR-derived source facts from Phiếu đăng ký dự tuyển. Python
maps those facts to Form.io `data[...]` fields, including repeated datagrids.
"""

FIELDS: list[dict] = [
    {"name": "Phieu_ViTriViecLam", "desc": "Vị trí việc làm dự tuyển."},
    {"name": "Phieu_CoQuanDuTuyen", "desc": "Cơ quan, tổ chức, đơn vị dự tuyển."},

    # I. Thông tin cá nhân.
    {"name": "Phieu_HoTen", "desc": "Họ tên người đăng ký dự tuyển/chủ hồ sơ."},
    {"name": "Phieu_NgaySinh", "desc": "Ngày, tháng, năm sinh người dự tuyển, dd/mm/yyyy."},
    {"name": "Phieu_GioiTinh", "desc": 'Giới tính người dự tuyển: "Nam" hoặc "Nữ".'},
    {"name": "Phieu_SoDinhDanh", "desc": "Số CCCD/CMND/hộ chiếu người dự tuyển."},
    {"name": "Phieu_NgayCap", "desc": "Ngày cấp giấy tờ định danh, dd/mm/yyyy."},
    {"name": "Phieu_NoiCap", "desc": "Nơi cấp giấy tờ định danh."},
    {"name": "Phieu_TonGiao", "desc": "Tôn giáo."},
    {"name": "Phieu_DanToc", "desc": "Dân tộc."},
    {"name": "Phieu_DienThoai", "desc": "Số điện thoại di động/liên hệ."},
    {"name": "Phieu_Email", "desc": "Email liên hệ."},
    {"name": "Phieu_QueQuan", "desc": "Quê quán, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Phieu_NoiThuongTru", "desc": "Nơi thường trú, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Phieu_NoiOHienTai", "desc": "Nơi ở hiện tại, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Phieu_TinhTrangSucKhoe", "desc": "Tình trạng sức khỏe."},
    {"name": "Phieu_ChieuCao", "desc": "Chiều cao, đơn vị cm, chỉ trả số."},
    {"name": "Phieu_CanNang", "desc": "Cân nặng, đơn vị kg, chỉ trả số."},
    {"name": "Phieu_TrinhDoVanHoa", "desc": "Trình độ văn hóa, ví dụ 12/12."},
    {"name": "Phieu_TrinhDoChuyenMon", "desc": "Trình độ chuyên môn, ví dụ Đại học."},

    # II. Văn bằng, chứng chỉ.
    {
        "name": "Phieu_VanBangChungChi",
        "desc": (
            "Danh sách văn bằng/chứng chỉ. Mỗi item: {tenTruong,ngayCap,trinhDo,soHieu,"
            "chuyenNganh,nganh,hinhThuc,xepLoai}. Giữ đúng thứ tự trong phiếu."
        ),
    },

    # III. Quá trình công tác.
    {
        "name": "Phieu_QuaTrinhCongTac",
        "desc": "Danh sách quá trình công tác nếu có. Mỗi item: {thoiGian,coQuan}. Bỏ nếu phiếu để trống.",
    },

    # IV. Thông tin đăng ký dự tuyển.
    {"name": "Phieu_NgoaiNgu", "desc": "Ngoại ngữ đăng ký thi nếu có."},
    {"name": "Phieu_CoDoiTuongUuTien", "desc": 'Thuộc đối tượng ưu tiên: "Có" hoặc "Không".'},
    {"name": "Phieu_DoiTuongUuTien", "desc": "Nội dung đối tượng ưu tiên."},
    {"name": "Phieu_DiemUuTien", "desc": "Điểm ưu tiên, chỉ trả số."},
    {
        "name": "Phieu_ThuTuUuTien",
        "desc": "Danh sách thứ tự ưu tiên/nguyện vọng. Mỗi item: {tenCoQuan,nguyenVong}.",
    },
    {"name": "Phieu_NoiDungKhac", "desc": "Nội dung khác theo yêu cầu nếu có."},

    # Optional CCCD upload, if user also provides it.
    {"name": "Person1_HoTen", "desc": "Họ tên trên CCCD/CMND nếu có file định danh riêng."},
    {"name": "Person1_SoDinhDanh", "desc": "Số định danh/CCCD/CMND nếu có file định danh riêng."},
    {"name": "Person1_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Person1_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Person1_NgayCap", "desc": "Ngày cấp CCCD/CMND, dd/mm/yyyy."},
    {"name": "Person1_NoiCap", "desc": "Nơi cấp CCCD/CMND."},
    {"name": "Person1_NoiCuTru", "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Phieu_NgaySinh", "Phieu_NgayCap", "Person1_NgaySinh", "Person1_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Phieu_QueQuan", "Phieu_NoiThuongTru", "Phieu_NoiOHienTai", "Person1_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("Phieu_VanBangChungChi", "Phieu_QuaTrinhCongTac", "Phieu_ThuTuUuTien"):
    COMPACT_COMP_BY_NAME[_name] = "x-array"

UI_COMP_BY_NAME = {
    # Applicant/account holder.
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
    "data[email]": "dom-input",
    "data[fax]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Dossier owner.
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
    "data[ownerEmail]": "dom-input",
    "data[ownerFax]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",

    # Attached dossier declaration grid.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Detailed application form.
    "data[VtVlDt]": "dom-input",
    "data[CqTcDt]": "dom-input",
    "data[identityAgency]": "dom-input",
    "data[TonGiao]": "dom-input",
    "data[DanToc]": "dom-input",
    "data[email]": "dom-input",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
    "data[address2]": "dom-input",
    "data[TtSk]": "dom-input",
    "data[ChieuCao]": "dom-input",
    "data[CanNang]": "dom-input",
    "data[TdVh]": "dom-input",
    "data[TdCm]": "dom-input",
    "data[NgoaiNgu]": "dom-input",
    "data[CoKhong]": "dom-select",
    "data[DtUt]": "dom-input",
    "data[Dut]": "dom-input",
    "data[XacNhan]": "dom-checkbox",
    "data[NdYc]": "dom-input",
}

for _i in range(6):
    UI_COMP_BY_NAME.update({
        f"data[DataGrid][{_i}][TenTruong]": "dom-input",
        f"data[DataGrid][{_i}][NgayCap1]": "dom-date",
        f"data[DataGrid][{_i}][TdVh1]": "dom-input",
        f"data[DataGrid][{_i}][ShVbCc]": "dom-input",
        f"data[DataGrid][{_i}][CnDt]": "dom-input",
        f"data[DataGrid][{_i}][Ndt]": "dom-input",
        f"data[DataGrid][{_i}][HtDt]": "dom-input",
        f"data[DataGrid][{_i}][XhVbCc]": "dom-input",
    })

for _i in range(5):
    UI_COMP_BY_NAME.update({
        f"data[DataGrid1][{_i}][TnDn]": "dom-input",
        f"data[DataGrid1][{_i}][CqTcDv]": "dom-input",
        f"data[DataGrid2][{_i}][stt]": "dom-input",
        f"data[DataGrid2][{_i}][textField1]": "dom-input",
        f"data[DataGrid2][{_i}][textField2]": "dom-input",
    })
