"""Compact schema for ATTP certificate reissue.

The LLM returns source facts only. The mapper derives Form.io fields and keeps
portal account fields untouched when the uploaded documents do not prove them.
"""

FIELDS: list[dict] = [
    # Người nộp/người đại diện nếu có CCCD hoặc giấy ủy quyền.
    {"name": "Applicant_HoTen", "desc": "Họ tên người nộp/đại diện nếu tài liệu ghi rõ."},
    {"name": "Applicant_SoDinhDanh", "desc": "Số CCCD/CMND/định danh của người nộp/đại diện."},
    {"name": "Applicant_NgaySinh", "desc": "Ngày sinh người nộp/đại diện, dd/mm/yyyy."},
    {"name": "Applicant_NgayCap", "desc": "Ngày cấp giấy tờ định danh người nộp/đại diện, dd/mm/yyyy."},
    {"name": "Applicant_NoiCap", "desc": "Nơi cấp giấy tờ định danh người nộp/đại diện."},
    {"name": "Applicant_NoiCuTru", "desc": "Nơi thường trú/cư trú của người nộp/đại diện, object {quocGia,tinh,xa,diaChi,fullText}."},
    {"name": "Applicant_DienThoai", "desc": "Số điện thoại người nộp/đại diện nếu giấy tờ ghi rõ."},
    {"name": "Applicant_Email", "desc": "Email người nộp/đại diện nếu giấy tờ ghi rõ."},

    # Giấy ủy quyền, nếu người nộp thay đại diện/chủ cơ sở.
    {"name": "UyQuyen_BenUyQuyen_HoTen", "desc": "Họ tên bên ủy quyền trong Giấy ủy quyền."},
    {"name": "UyQuyen_BenUyQuyen_SoDinhDanh", "desc": "Số CCCD/CMND/hộ chiếu của bên ủy quyền."},
    {"name": "UyQuyen_BenUyQuyen_NgayCap", "desc": "Ngày cấp giấy tờ định danh bên ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_BenUyQuyen_NoiCap", "desc": "Nơi cấp giấy tờ định danh bên ủy quyền."},
    {"name": "UyQuyen_BenUyQuyen_ChucDanh", "desc": "Chức danh/vai trò của bên ủy quyền."},
    {"name": "UyQuyen_BenDuocUyQuyen_HoTen", "desc": "Họ tên bên được ủy quyền/người có thể đi nộp hồ sơ."},
    {"name": "UyQuyen_BenDuocUyQuyen_SoDinhDanh", "desc": "Số CCCD/CMND của bên được ủy quyền."},
    {"name": "UyQuyen_BenDuocUyQuyen_NgayCap", "desc": "Ngày cấp giấy tờ định danh bên được ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_BenDuocUyQuyen_NoiCap", "desc": "Nơi cấp giấy tờ định danh bên được ủy quyền."},
    {"name": "UyQuyen_BenDuocUyQuyen_ChucVu", "desc": "Chức vụ/chức danh của bên được ủy quyền."},

    # Đơn đề nghị cấp lại.
    {"name": "DonCapLai_DiaDanh", "desc": "Địa danh lập đơn, ví dụ Lai Châu."},
    {"name": "DonCapLai_NgayDon", "desc": "Ngày lập/nộp đơn, dd/mm/yyyy."},
    {"name": "DonCapLai_KinhGui", "desc": "Cơ quan kính gửi trong đơn đề nghị cấp lại."},
    {"name": "DonCapLai_TenCoSo", "desc": "Tên cơ sở sản xuất/kinh doanh trong đơn đề nghị cấp lại."},
    {"name": "DonCapLai_DiaChiCoSo", "desc": "Địa chỉ cơ sở trong đơn đề nghị cấp lại, có thể trả chuỗi đầy đủ hoặc object địa chỉ."},
    {"name": "DonCapLai_GCNCuSo", "desc": "Số Giấy chứng nhận đủ điều kiện ATTP cũ được nêu trong đơn."},
    {"name": "DonCapLai_NgayCapGCNCu", "desc": "Ngày cấp GCN cũ được nêu trong đơn, dd/mm/yyyy."},
    {"name": "DonCapLai_LyDoCapLai", "desc": "Lý do xin cấp lại Giấy chứng nhận."},
    {"name": "DonCapLai_NguoiKy", "desc": "Họ tên người ký đơn/đại diện cơ sở ở cuối đơn."},
    {"name": "DonCapLai_NoiDungYeuCau", "desc": "Nội dung yêu cầu giải quyết nếu đơn ghi rõ; thường là đề nghị cấp lại GCN ATTP."},

    # Thông tin cơ sở/chủ hồ sơ từ các tài liệu hỗ trợ.
    {"name": "CoSo_TenCoSo", "desc": "Tên cơ sở/chủ hồ sơ từ GCN ĐK địa điểm KD, ĐKDN, GCN ATTP cũ hoặc bản thuyết minh."},
    {"name": "CoSo_MaSoThue", "desc": "Mã số doanh nghiệp/MST/mã địa điểm kinh doanh/mã chi nhánh của cơ sở."},
    {"name": "CoSo_DienThoai", "desc": "Điện thoại cơ sở/chủ hồ sơ, có thể là số bàn hoặc di động."},
    {"name": "CoSo_DiaChi", "desc": "Địa chỉ cơ sở/chủ hồ sơ, chuỗi đầy đủ."},

    # GCN ATTP đã cấp trước đó.
    {"name": "GCNCu_SoCap", "desc": "Số cấp trên GCN ATTP cũ, ví dụ 05/2022/GCNATTP-SCT."},
    {"name": "GCNCu_NgayCap", "desc": "Ngày cấp trên GCN ATTP cũ, dd/mm/yyyy."},
    {"name": "GCNCu_TenCoSo", "desc": "Tên cơ sở hoặc tên doanh nghiệp trên GCN ATTP cũ."},
    {"name": "GCNCu_DiaChiCoSo", "desc": "Địa chỉ kinh doanh/cơ sở trên GCN ATTP cũ."},
    {"name": "GCNCu_DienThoai", "desc": "Điện thoại trên GCN ATTP cũ."},
    {"name": "GCNCu_ChuCoSoHoTen", "desc": "Họ tên chủ cơ sở/người đại diện trên GCN ATTP cũ."},
    {"name": "GCNCu_SoDinhDanhChuCoSo", "desc": "Số định danh/CCCD/hộ chiếu của chủ cơ sở trên GCN ATTP cũ nếu có."},

    # Bản thuyết minh CSVC.
    {"name": "ThuyetMinh_DaiDienCoSo", "desc": "Đại diện cơ sở trong bản thuyết minh."},
    {"name": "ThuyetMinh_DiaChiVanPhong", "desc": "Địa chỉ văn phòng trong bản thuyết minh."},
    {"name": "ThuyetMinh_DiaChiCoSo", "desc": "Địa chỉ cơ sở kinh doanh trong bản thuyết minh."},
    {"name": "ThuyetMinh_DienThoai", "desc": "Điện thoại trong bản thuyết minh."},

    # Giấy đăng ký kinh doanh/địa điểm/chi nhánh nếu hồ sơ có.
    {"name": "DangKy_TenDonVi", "desc": "Tên doanh nghiệp/chi nhánh/địa điểm kinh doanh trên giấy đăng ký."},
    {"name": "DangKy_MaSo", "desc": "Mã số doanh nghiệp/MST/mã chi nhánh/mã địa điểm kinh doanh trên giấy đăng ký."},
    {"name": "DangKy_DiaChi", "desc": "Địa chỉ trụ sở/địa điểm kinh doanh trên giấy đăng ký."},
    {"name": "DangKy_DienThoai", "desc": "Điện thoại trên giấy đăng ký nếu có."},
    {"name": "DangKy_NguoiDaiDien", "desc": "Người đại diện/người đứng đầu trên giấy đăng ký nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Applicant_NgaySinh",
    "Applicant_NgayCap",
    "UyQuyen_BenUyQuyen_NgayCap",
    "UyQuyen_BenDuocUyQuyen_NgayCap",
    "DonCapLai_NgayDon",
    "DonCapLai_NgayCapGCNCu",
    "GCNCu_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Applicant_NoiCuTru",):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Account/requester fields.
    "data[fullname]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[taxCode]": "dom-input",
    "data[email]": "dom-input",
    "data[district]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[birthday]": "dom-date",
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",

    # Dossier owner/facility fields.
    "data[isOwnerDossier]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownertaxCode]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",

    # Reissue application fields.
    "data[tinhThanhPhoNopDon]": "dom-select",
    "data[ngayNopDon]": "dom-date",
    "data[kinhGui]": "dom-input",
    "data[TenCoSoSanXuatKinhDoanh]": "dom-input",
    "data[GCNCuSo]": "dom-input",
    "data[NgayCapGCNCu]": "dom-date",
    "data[LyDoCapLaiGCN]": "dom-input",
    "data[KyTen]": "dom-input",
}

