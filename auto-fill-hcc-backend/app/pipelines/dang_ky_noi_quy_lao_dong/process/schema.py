"""Compact schema cho "Đăng ký nội quy lao động của doanh nghiệp" (mã 2.001955) — cổng DVCQG (Form.io).

Hồ sơ mẫu: Văn bản (công văn) đề nghị đăng ký nội quy lao động kính gửi Sở Nội vụ + Quyết định ban hành Nội quy lao
động + toàn văn Nội quy lao động + Biên bản hội nghị đối thoại / văn bản góp ý của tổ chức đại diện người lao động +
Giấy ủy quyền (khi người đi nộp không phải người đại diện theo pháp luật) + CCCD (nếu có).

BA vai:
- DoanhNghiep_* : CHỦ HỒ SƠ = doanh nghiệp đăng ký nội quy (luôn là tổ chức) — tên, mã số, trụ sở, điện thoại.
- DaiDien_*     : người đại diện theo pháp luật của doanh nghiệp (người ký công văn / Bên A Giấy ủy quyền) → nhân
                  thân Phần II (họ tên, CCCD... của chủ hồ sơ là tổ chức).
- NguoiNop_*    : NGƯỜI NỘP = tài khoản đăng nhập (thường là Bên B Giấy ủy quyền). Họ tên, ngày sinh, số định danh
                  cổng tự đổ (ô khoá) → chỉ lấy giới tính, ngày cấp, nơi cấp, nơi cư trú, SĐT.
"""

FIELDS: list[dict] = [
    {"name": "DoanhNghiep_Ten", "desc": "Tên ĐẦY ĐỦ của doanh nghiệp đăng ký nội quy (tiêu đề công văn / quyết định, "
        "phần căn cứ Giấy ủy quyền, Giấy chứng nhận ĐKDN), viết IN HOA như văn bản ghi. KHÔNG lấy tên công ty mẹ / "
        "tổng công ty in dòng trên tên đơn vị, KHÔNG lấy tên viết tắt."},
    {"name": "DoanhNghiep_MaSo", "desc": "Mã số doanh nghiệp / mã số thuế (10 hoặc 13 chữ số, có thể có '-'). Nguồn: "
        "công văn 'Mã số doanh nghiệp', Giấy chứng nhận ĐKDN, căn cứ Giấy ủy quyền."},
    {"name": "DoanhNghiep_DiaChi", "desc": "Địa chỉ TRỤ SỞ CHÍNH của doanh nghiệp (công văn 'Địa chỉ' / Giấy ủy quyền "
        "'Trụ sở tại'), object {quocGia,tinh,xa,diaChi}. diaChi = số nhà, đường (KHÔNG kèm phường/tỉnh). KHÔNG lấy "
        "địa chỉ cư trú của cá nhân."},
    {"name": "DoanhNghiep_DienThoai", "desc": "Số điện thoại của DOANH NGHIỆP (công văn 'Điện thoại', 'ĐT'). Ghi "
        "nhiều số thì chép đủ, ngăn bằng ' / '."},
    {"name": "DoanhNghiep_Email", "desc": "Email của doanh nghiệp nếu văn bản ghi."},
    {"name": "DoanhNghiep_Fax", "desc": "Số fax của doanh nghiệp nếu văn bản ghi."},
    {"name": "DaiDien_HoTen", "desc": "Họ tên NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của doanh nghiệp: công văn 'Người đại "
        "diện theo pháp luật', Giấy ủy quyền 'Bên ủy quyền (Bên A)', người ký công văn / quyết định (Giám đốc, Tổng "
        "giám đốc, Chủ tịch). Viết hoa chữ cái đầu mỗi từ."},
    {"name": "DaiDien_SoDinhDanh", "desc": "Số CCCD/căn cước của NGƯỜI ĐẠI DIỆN (Bên A Giấy ủy quyền 'CCCD số' → thẻ "
        "CCCD của chính người này). Chỉ chữ số."},
    {"name": "DaiDien_NgayCap", "desc": "Ngày cấp CCCD của người đại diện, dd/mm/yyyy (Bên A Giấy ủy quyền 'Ngày cấp' "
        "→ thẻ CCCD)."},
    {"name": "DaiDien_NoiCap", "desc": "Nơi cấp CCCD của người đại diện, chép đúng (Bên A Giấy ủy quyền 'Nơi cấp' → "
        "thẻ CCCD)."},
    {"name": "DaiDien_NgaySinh", "desc": "Ngày sinh của người đại diện, dd/mm/yyyy — CHỈ khi giấy tờ ghi rõ (thẻ CCCD, "
        "Giấy ủy quyền). KHÔNG suy ra từ số CCCD."},
    {"name": "DaiDien_GioiTinh", "desc": 'Giới tính của người đại diện: "Nam"/"Nữ" — chỉ khi giấy tờ ghi rõ hoặc có '
        'danh xưng "Ông"/"Bà" đứng trước tên.'},
    {"name": "NguoiNop_HoTen", "desc": "Họ tên NGƯỜI NỘP (xem nguoi_nop_context): thường là Bên được ủy quyền (Bên B) "
        "trong Giấy ủy quyền, hoặc thẻ CCCD khớp tài khoản."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD của người nộp (Bên B Giấy ủy quyền 'CCCD số' / thẻ CCCD). Chỉ chữ "
        "số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy (Bên B Giấy ủy quyền / thẻ CCCD). KHÔNG "
        "lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD người nộp, chép đúng (Bên B Giấy ủy quyền / thẻ CCCD)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam"/"Nữ" (thẻ CCCD, hoặc danh xưng "Ông"/"Bà" trước '
        'tên Bên B).'},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú / nơi cư trú của NGƯỜI NỘP (thẻ CCCD, hoặc 'Địa chỉ' của Bên B "
        "trong Giấy ủy quyền), object {quocGia,tinh,xa,diaChi}. KHÔNG lấy địa chỉ trụ sở doanh nghiệp."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của CHÍNH người nộp nếu giấy tờ ghi cạnh tên người đó (Bên B "
        "Giấy ủy quyền, 'Người liên hệ: ..., ĐT ...'). KHÔNG lấy số điện thoại của doanh nghiệp."},
    {"name": "QuyetDinh_So", "desc": "Số hiệu Quyết định ban hành Nội quy lao động (vd '12/QĐ-ABC')."},
    {"name": "QuyetDinh_Ngay", "desc": "Ngày ban hành Quyết định ban hành Nội quy lao động, dd/mm/yyyy."},
    {"name": "DanhMucHoSo", "desc": "Mảng giấy tờ CÓ trong bộ hồ sơ tải lên, mỗi phần tử một chuỗi 'Tên giấy tờ – Số: "
        "..., ngày ...' (bỏ phần số/ngày nếu giấy không ghi). Thứ tự: Văn bản đề nghị đăng ký nội quy lao động → "
        "Quyết định ban hành Nội quy lao động → Nội quy lao động → Biên bản đối thoại / văn bản góp ý của tổ chức đại "
        "diện người lao động → văn bản quy định về kỷ luật lao động, trách nhiệm vật chất → Giấy ủy quyền. KHÔNG liệt "
        "kê CCCD."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DaiDien_NgayCap", "DaiDien_NgaySinh", "NguoiNop_NgayCap", "QuyetDinh_Ngay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("DoanhNghiep_DiaChi", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["DanhMucHoSo"] = "x-array"

# Option "Đối tượng nộp hồ sơ" của chủ hồ sơ — đúng chữ trên HTML thật.
CHON_TO_CHUC = "Tổ chức/Doanh nghiệp"

# ---- UI Form.io fields (data[...]) — field-key theo Mapping_DangKy_NoiQuyLaoDong_BoNoiVu.xlsx.
# data[fullname], data[birthday], data[identityNumber], data[chonDoiTuong] (Phần I) cổng khoá theo tài khoản → KHÔNG
# phát. data[email], data[fax] không có nguồn → bỏ. Thứ tự khai báo = thứ tự điền: data[chonDoiTuong1] phải chọn
# TRƯỚC thì ô tên tổ chức / mã số thuế chủ hồ sơ mới hiện.
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp (ô không khoá).
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ = doanh nghiệp.
    "data[chonDoiTuong1]": "dom-select",
    "data[ownerOrganizationFullname]": "dom-input",
    "data[ownerTaxCode]": "dom-input",
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
}

# Datagrid "Hồ sơ kèm theo gồm" — mỗi giấy tờ một dòng (FE tự bấm "Thêm dòng").
MAX_HO_SO_ROWS = 15
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
