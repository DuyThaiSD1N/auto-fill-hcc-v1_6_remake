"""Compact schema "Cấp, cấp lại, chuyển đổi GCN khả năng chuyên môn, chứng chỉ chuyên môn" (1.003135).

Cổng Bộ Xây dựng dvc.moc.gov.vn — Form.io. MỘT chủ hồ sơ (người nộp = chính chủ, không ủy quyền).
LLM trả FACT nguồn (CCCD / GCNKNCM / Đơn đề nghị / Giấy khám sức khỏe [+ GCN ĐKDN/ĐKKD nếu là tổ chức/hộ KD]).
`mapper.enrich` suy ra tất định các ô Form.io data[...].

2 KHỐI:
- Khối A "Thông tin chung" (người nộp) — data[...] phẳng: fullname, birthday, gender, identityNumber,
  identityDate, identityAgency, AuthorityApplicantPhoneNumber, nation, province, district.
- Khối B "Cá nhân/Tổ chức đề nghị" — đổi theo data[chonDoiTuong]; ô đăng ký DN/hộ KD CHỈ điền khi hồ sơ
  CÓ giấy ĐKDN/ĐKKD (cá nhân thuần → chỉ tên + địa chỉ).
⚠ Phần II HTML ("Đề nghị công bố khu neo đậu") là biểu mẫu con NHÚNG SAI của cổng → TUYỆT ĐỐI không điền.
"""

FIELDS: list[dict] = [
    # === Người nộp = chủ hồ sơ (thuyền viên xin cấp/cấp lại/chuyển đổi GCNKNCM/CCCM) ===
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (chủ hồ sơ), IN HOA. Lấy ở CCCD (Họ và tên) / "
        "GCNKNCM (Họ và tên) / Đơn đề nghị ('Tên tôi là') / Giấy khám sức khỏe (Họ và tên)."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — từ CCCD / GCNKNCM / Đơn / Giấy "
        "khám sức khỏe. KHÔNG lấy giá trị nháp còn sót trên form."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ" (CCCD / Giấy khám sức khỏe).'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh/CCCD người nộp; ưu tiên CCCD, hoặc Đơn đề nghị / "
        "Giấy khám sức khỏe (Số CCCD/định danh). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy. CHỈ có nếu upload CCCD; "
        "Đơn/Giấy khám sức khỏe không ghi → bỏ trống."},
    {"name": "NguoiNop_NoiCapCccd",
     "desc": 'Nơi cấp CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát '
             'quản lý hành chính về trật tự xã hội"; thẻ Căn cước mới "BỘ CÔNG AN" → "Bộ Công an". Bỏ nếu '
             'không có ảnh CCCD.'},
    {"name": "NguoiNop_QuocTich", "desc": 'Quốc tịch người nộp (CCCD: Quốc tịch). Mặc định "Việt Nam".'},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi cư trú người nộp, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN địa danh MỚI ở Đơn đề nghị "
             "(2026, sau sáp nhập) hơn GCNKNCM cũ (2021). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số "
             "nhà/thôn/tổ (KHÔNG kèm xã/huyện/tỉnh)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp — Đơn đề nghị ('Điện thoại'). Chỉ chữ số."},

    # === Khối B: đối tượng đề nghị (cá nhân/tổ chức). Chỉ điền phần đăng ký khi có giấy ĐKDN/ĐKKD. ===
    {"name": "DoiTuong",
     "desc": 'Đối tượng đề nghị: "Tổ chức" NẾU hồ sơ có Giấy chứng nhận đăng ký doanh nghiệp/hợp tác xã đứng '
             'tên tổ chức; ngược lại "Cá nhân" (thuyền viên xin cấp cho bản thân). Mặc định "Cá nhân".'},
    {"name": "DoiTuong_Ten",
     "desc": "Tên đối tượng ĐỀ NGHỊ: nếu Tổ chức = tên tổ chức/doanh nghiệp; nếu Cá nhân = họ tên người đề "
             "nghị (thường trùng NguoiNop_HoTen). IN HOA nếu là tên riêng."},
    {"name": "DoiTuong_DiaChi", "desc": "Địa chỉ đối tượng đề nghị (trụ sở tổ chức, hoặc địa chỉ cá nhân) — "
        "CHUỖI một dòng. Cá nhân thường trùng nơi cư trú người nộp."},
    {"name": "DoiTuong_NguoiDaiDien", "desc": "Người đại diện theo pháp luật (chỉ khi có giấy ĐKDN/ĐKKD ghi rõ). "
        "Bỏ nếu không có."},
    {"name": "DoiTuong_SoDangKy", "desc": "Số đăng ký doanh nghiệp / hộ kinh doanh (mã số DN/ĐKKD). CHỈ khi hồ "
        "sơ CÓ giấy đăng ký. Bỏ nếu cá nhân thuần không có."},
    {"name": "DoiTuong_NgayCapDangKy", "desc": "Ngày cấp giấy đăng ký DN/hộ KD, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "DoiTuong_NoiCapDangKy", "desc": "Nơi cấp ('Cấp tại') giấy đăng ký DN/hộ KD (vd Phòng Đăng ký "
        "kinh doanh Sở KH&ĐT …). Bỏ nếu không có."},
    {"name": "DoiTuong_DienThoai", "desc": "Số điện thoại của tổ chức (chỉ khi là Tổ chức và giấy tờ ghi rõ). "
        "Bỏ nếu không có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NguoiNop_NgaySinh", "NguoiNop_NgayCapCccd", "DoiTuong_NgayCapDangKy"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fillFormStandard ----
UI_COMP_BY_NAME = {
    # Khối A — Thông tin chung (người nộp), phẳng.
    "data[chonDoiTuong]": "dom-select",   # Cá nhân / Tổ chức
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    # SĐT người nộp = ô "Số điện thoại" = data[phoneNumber]. ⚠ KHÔNG dùng data[AuthorityApplicantPhoneNumber]
    # (nhãn "Số điện thoại người được ủy quyền" — chỉ dành cho người ĐƯỢC ỦY QUYỀN, thủ tục này không có).
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",       # Tỉnh/TP (nơi cư trú)
    "data[district]": "dom-select",       # Phường/Xã (nơi cư trú)

    # Khối B — Cá nhân đề nghị (panel "Thông Tin Cá Nhân").
    "data[fullName]": "dom-input",          # Cá nhân đề nghị (họ tên)
    "data[nguoidaidiencanhan]": "dom-input",
    "data[dangkyhogiadinh]": "dom-input",   # Đăng ký DN (hộ gia đình)
    "data[captaicaNhan]": "dom-input",      # Cấp tại
    "data[ngayThangNamCN]": "dom-date",     # Ngày cấp
    "data[diachicanhan]": "dom-input",      # Địa chỉ

    # Khối B — Tổ chức đề nghị (panel "Thông Tin Tổ chức Doanh nghiệp").
    "data[ownerFullname]": "dom-input",     # Tổ chức đề nghị (tên)
    "data[nguoidaidiendoanhnghiep]": "dom-input",
    "data[dangkydoanhnghiep]": "dom-input", # Số ĐKDN
    "data[captaidoanhnghiep]": "dom-input", # Cấp tại
    "data[ngaythangnamdoanhnghiep]": "dom-date",
    "data[diaChitoChuc]": "dom-input",      # Địa chỉ
    "data[phoneNumberTC]": "dom-input",     # SĐT tổ chức
}
