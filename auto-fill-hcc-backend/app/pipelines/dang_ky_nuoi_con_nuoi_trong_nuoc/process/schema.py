"""Compact schema for "Đăng ký việc nuôi con nuôi trong nước" (mã TTHC 2.001263).

LLM chỉ trả dữ kiện nguồn; ô UI của eForm được dựng trong Python (mapper.py). Tên ô lấy từ mẫu eForm
thật của cổng tokhaidientu.moj.gov.vn (mẫu "NCNV5", id 2081, iframe /e-form/75a52d24-…):
  C   = người yêu cầu (mục I);
  CN  = con nuôi (mục II);
  M   = mẹ nuôi, Cha = cha nuôi (mục III/IV, nằm TRONG khối x-select-area VoChongNhanNuoi khi vợ chồng
        cùng nhận, hoặc MeNuoi/ChaNuoi khi người đơn thân nhận);
  gd* = gia đình nơi trẻ đang sống (khối hienSongTai_OngBa).
"""

FIELDS: list[dict] = [
    # Cha nuôi / mẹ nuôi — phần "Người nhận con nuôi" cột Ông/Bà trên đơn.
    {"name": "AdoptiveFather_FullName", "desc": "Họ tên cha nuôi (cột Ông trong phần khai về người nhận con nuôi)."},
    {"name": "AdoptiveFather_BirthDate", "desc": "Ngày sinh cha nuôi, dd/mm/yyyy."},
    {"name": "AdoptiveFather_Ethnicity", "desc": "Dân tộc cha nuôi nếu giấy tờ ghi."},
    {"name": "AdoptiveFather_Nationality", "desc": "Quốc tịch cha nuôi."},
    {"name": "AdoptiveFather_IdNumber", "desc": "Số CCCD/căn cước/số định danh cha nuôi (12 chữ số)."},
    {"name": "AdoptiveFather_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân cha nuôi, dd/mm/yyyy."},
    {"name": "AdoptiveFather_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân cha nuôi."},
    {"name": "AdoptiveFather_Residence", "desc": "Nơi cư trú cha nuôi, object {quocGia,tinh,xa,diaChi}; ưu tiên đơn."},
    {"name": "AdoptiveFather_Phone", "desc": "Số điện thoại cha nuôi nếu đơn ghi."},
    {"name": "AdoptiveFather_Relation", "desc": 'Cha nuôi là: "Chú, cậu, bác ruột", "Cha dượng" hoặc "Khác" — chỉ trả khi giấy tờ thể hiện.'},

    {"name": "AdoptiveMother_FullName", "desc": "Họ tên mẹ nuôi (cột Bà trong phần khai về người nhận con nuôi)."},
    {"name": "AdoptiveMother_BirthDate", "desc": "Ngày sinh mẹ nuôi, dd/mm/yyyy."},
    {"name": "AdoptiveMother_Ethnicity", "desc": "Dân tộc mẹ nuôi nếu giấy tờ ghi."},
    {"name": "AdoptiveMother_Nationality", "desc": "Quốc tịch mẹ nuôi."},
    {"name": "AdoptiveMother_IdNumber", "desc": "Số CCCD/căn cước/số định danh mẹ nuôi (12 chữ số)."},
    {"name": "AdoptiveMother_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân mẹ nuôi, dd/mm/yyyy."},
    {"name": "AdoptiveMother_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân mẹ nuôi."},
    {"name": "AdoptiveMother_Residence", "desc": "Nơi cư trú mẹ nuôi, object {quocGia,tinh,xa,diaChi}; ưu tiên đơn."},
    {"name": "AdoptiveMother_Phone", "desc": "Số điện thoại mẹ nuôi nếu đơn ghi."},
    {"name": "AdoptiveMother_Relation", "desc": 'Mẹ nuôi là: "Cô, dì, bác ruột", "Mẹ kế" hoặc "Khác" — chỉ trả khi giấy tờ thể hiện.'},

    # Người được nhận làm con nuôi.
    {"name": "Child_FullName", "desc": "Họ tên người được nhận làm con nuôi."},
    {"name": "Child_BirthDate", "desc": "Ngày sinh con nuôi, dd/mm/yyyy."},
    {"name": "Child_Gender", "desc": 'Giới tính con nuôi: "Nam" hoặc "Nữ".'},
    {"name": "Child_Ethnicity", "desc": "Dân tộc con nuôi (giấy khai sinh)."},
    {"name": "Child_Nationality", "desc": "Quốc tịch con nuôi."},
    {"name": "Child_IdNumber", "desc": "Số định danh cá nhân của con nuôi."},
    {"name": "Child_IdIssueDate", "desc": "Ngày cấp thẻ CCCD/căn cước của con nuôi, dd/mm/yyyy — CHỈ khi trẻ có thẻ."},
    {"name": "Child_IdIssuePlace", "desc": "Nơi cấp thẻ CCCD/căn cước của con nuôi — CHỈ khi trẻ có thẻ."},
    {"name": "Child_BirthPlace", "desc": "Nơi sinh con nuôi, object {quocGia,tinh,xa,diaChi}; diaChi là tên cơ sở y tế/thôn."},
    {"name": "Child_Residence", "desc": "Nơi cư trú con nuôi, object {quocGia,tinh,xa,diaChi}; ưu tiên đơn."},
    {"name": "Child_Category", "desc": "Mục 'Thuộc đối tượng' của con nuôi đúng như đơn ghi/tích."},

    # Nơi trẻ hiện đang sống.
    {"name": "LivingWith_Type", "desc": '"Gia đình" nếu đơn ghi đang sống tại gia đình ông/bà; "Cơ sở nuôi dưỡng" nếu ở cơ sở nuôi dưỡng.'},
    {"name": "LivingWith_FullName", "desc": "Họ tên ông/bà nơi trẻ đang sống, chép đúng đơn."},
    {"name": "LivingWith_Gender", "desc": 'Giới tính ông/bà nơi trẻ đang sống khi chỉ có MỘT người: "Nam" hoặc "Nữ".'},
    {"name": "LivingWith_Phone", "desc": "Điện thoại liên lạc của gia đình nơi trẻ đang sống."},
    {"name": "LivingWith_Email", "desc": "Email liên lạc của gia đình nơi trẻ đang sống nếu đơn ghi."},
    {"name": "LivingWith_Residence", "desc": "Nơi cư trú gia đình nơi trẻ đang sống, object {quocGia,tinh,xa,diaChi}."},
    {"name": "LivingWith_FacilityName", "desc": "Tên cơ sở nuôi dưỡng nếu trẻ đang sống tại cơ sở nuôi dưỡng."},

    # V. Nơi đăng ký việc nuôi con nuôi.
    {"name": "Registration_Agency", "desc": "Cơ quan ở dòng 'Kính gửi' của đơn, chép nguyên văn (vd 'Ủy ban nhân dân phường X, tỉnh Y')."},

    # Bản sao.
    {"name": "CopyRequest_WantsCopy", "desc": '"Có" nếu đơn đề nghị cấp bản sao, "Không" nếu tích không.'},
    {"name": "CopyRequest_Quantity", "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "AdoptiveFather_BirthDate",
    "AdoptiveFather_IdIssueDate",
    "AdoptiveMother_BirthDate",
    "AdoptiveMother_IdIssueDate",
    "Child_BirthDate",
    "Child_IdIssueDate",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "AdoptiveFather_Residence",
    "AdoptiveMother_Residence",
    "Child_BirthPlace",
    "Child_Residence",
    "LivingWith_Residence",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô con nằm trong x-select-area (thông tin cha/mẹ nuôi, gia đình nơi trẻ sống): ô chữ không có x-input
# bọc → "raw" (input trần theo name); dropdown/ngày/ô tích con giữ đúng loại control của mẫu.
UI_COMP_BY_NAME = {
    # I. Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "TT_SoNhaToDanPhoC": "x-input",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",

    # II. Con nuôi.
    "HoVaTenCN": "x-input",
    "NgaySinhCN": "x-date",
    "GioiTinhCN": "x-select",
    "DanTocCN": "x-select",
    "QuocTichCN": "x-select",
    "SoDinhDanhCN": "x-input",
    "LoaiGiayToDinhDanhCN": "x-select",
    "SoGiayToTuyThanCN": "x-input",
    "NgayCapDDCN": "x-date",
    "NoiCapDDCN": "x-input",
    "LoaiCuTruCN": "x-select",
    "NoiCuTruCN": "x-radio",
    "NoiCuTruCN_TrongNuoc": "x-select-area",
    "NoiSinhCN": "x-radio",
    "NoiSinhCN_TrongNuoc": "x-select-area",
    "ncDoiTuong": "x-select-default",

    # Trường hợp nhận nuôi.
    "truongHopNhanNuoi": "x-radio",
    "ChonNguoiDonThanNhanNuoi": "x-radio",

    # III. Mẹ nuôi.
    "HoVaTenM": "raw",
    "NgaySinhM": "raw",
    "DanTocM": "x-select",
    "QuocTichM": "x-select",
    "SoDinhDanhM": "raw",
    "LoaiGiayToDinhDanhM": "x-select",
    "SoGiayToDinhDanhM": "raw",
    "NgayCapDDM": "x-date",
    "NoiCapDDM": "raw",
    "LoaiCuTruM": "x-select",
    "MeDoiTuong": "x-select-default",
    "SoDienThoaiM": "raw",
    "DiaChiM": "raw",
    "NoiCuTruM_QuocGia": "x-select",
    "NoiCuTruM": "x-radio",
    "NoiCuTruM_TrongNuoc": "x-select-area",

    # IV. Cha nuôi.
    "HoVaTenCha": "raw",
    "NgaySinhCha": "raw",
    "DanTocCha": "x-select",
    "QuocTichCha": "x-select",
    "SoDinhDanhCha": "raw",
    "LoaiGiayToDinhDanhCha": "x-select",
    "SoGiayToDinhDanhCha": "raw",
    "NgayCapDDCha": "x-date",
    "NoiCapDDCha": "raw",
    "LoaiCuTruCha": "x-select",
    "ChaDoiTuong": "x-select-default",
    "SoDienThoaiCha": "raw",
    "DiaChiCha": "raw",
    "NoiCuTruCha_QuocGia": "x-select",
    "NoiCuTruCha": "x-radio",
    "NoiCuTruCha_TrongNuoc": "x-select-area",

    # Nơi trẻ đang sống.
    "hienSongTai": "x-radio",
    "gdHoTen": "raw",
    "gdGioiTinh": "x-select",
    "gdEmail": "raw",
    "gdDienthoai": "raw",
    "gdLoaiCuTru": "x-select",
    "gdNoiCuTru": "x-radio",
    "gdNoiCuTru_TrongNuoc": "x-select-area",
    "tenCoSoNuoiDuong": "raw",

    # V. Đăng ký nuôi con nuôi. Tên ô mượn từ mẫu nhận cha, mẹ, con (TenCQDKNhanChaMe).
    "TenCQDKNhanChaMe": "x-input",
    "TenQuocGiaDK": "x-select",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}
