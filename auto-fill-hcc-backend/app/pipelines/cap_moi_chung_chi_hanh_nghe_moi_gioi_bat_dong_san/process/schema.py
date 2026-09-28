"""Compact schema cho "Cấp mới chứng chỉ hành nghề môi giới bất động sản" (mã 1.012906) — cổng Sở Xây dựng
(Form.io, engine fillFormStandard dom-*).

Hồ sơ thường gồm: Đơn đăng ký dự thi sát hạch có dán ảnh 4x6 (Phụ lục XXI NĐ 96/2024/NĐ-CP) — hoặc người dân nộp
nhầm Đơn xin cấp lại CCHN — + CCCD / thẻ căn cước + bằng tốt nghiệp THPT trở lên + Giấy chứng nhận hoàn thành khóa
đào tạo, bồi dưỡng kiến thức hành nghề môi giới BĐS + ảnh 4x6.

BA vai:
- NguoiDeNghi_* : NGƯỜI ĐỀ NGHỊ cấp chứng chỉ (người đứng tên đơn) → toàn bộ Đơn đăng ký dự thi.
- NguoiNop_*    : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ → chỉ lấy giới tính,
                  ngày cấp, nơi cấp, địa chỉ từ CCCD KHỚP tài khoản (nộp thay).
- ToChuc_*      : TỔ CHỨC nộp hồ sơ (chỉ khi có GCN ĐKDN / giấy giới thiệu của tổ chức) → panel Thông tin doanh
                  nghiệp (Chọn đối tượng = Tổ chức).
"""

_NGUON = "CCCD / thẻ căn cước → Đơn đăng ký dự thi (hoặc Đơn xin cấp lại) của NGƯỜI ĐỀ NGHỊ"

# --- Người đề nghị cấp chứng chỉ (người đứng tên đơn) ---
FIELDS: list[dict] = [
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ và tên NGƯỜI ĐỀ NGHỊ cấp chứng chỉ (người đứng tên đơn, dán ảnh trên "
        f"đơn). Nguồn: {_NGUON} mục 1 'Họ và tên'. Ghi IN HOA như CCCD."},
    {"name": "NguoiDeNghi_NgaySinh", "desc": "Ngày sinh người đề nghị, dd/mm/yyyy (CCCD → Đơn mục 'Ngày, tháng, năm "
        "sinh')."},
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đề nghị: "Nam"/"Nữ", đọc ở CCCD (Giới tính / Sex, MRZ '
        "M/F). KHÔNG suy từ họ tên."},
    {"name": "NguoiDeNghi_NoiSinh", "desc": "Nơi sinh của người đề nghị, CHÉP NGUYÊN VĂN từ CCCD của CHÍNH người "
        "này: CCCD mẫu 2021 lấy dòng 'Quê quán / Place of origin'; thẻ Căn cước mẫu mới lấy 'Nơi đăng ký khai sinh'. "
        "Không có CCCD thì lấy mục 'Nơi sinh' của đơn / Giấy khai sinh. Form chỉ cần tỉnh/thành phố (mapper tự tách)."},
    {"name": "NguoiDeNghi_QuocTich", "desc": "Quốc tịch người đề nghị (CCCD 'Quốc tịch / Nationality', vd 'Việt "
        "Nam')."},
    {"name": "NguoiDeNghi_LoaiGiayTo", "desc": 'Loại giấy tờ tùy thân CÓ trong hồ sơ: "CCCD" khi tiêu đề thẻ là '
        '"CĂN CƯỚC CÔNG DÂN"; "Thẻ căn cước" khi tiêu đề chỉ là "CĂN CƯỚC" (mẫu từ 01/7/2024); "CMND" khi là Giấy '
        'chứng minh nhân dân (9 số); "Hộ chiếu" khi là hộ chiếu. Chỉ có đơn thì theo số: 12 số → "CCCD".'},
    {"name": "NguoiDeNghi_SoGiayTo", "desc": "Số CCCD / thẻ căn cước / CMND / hộ chiếu của người đề nghị (CCCD mặt "
        "trước / MRZ → Đơn mục 'Số CMND/CCCD/Thẻ căn cước'). Chỉ chữ số (hộ chiếu giữ chữ cái)."},
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người đề nghị, dd/mm/yyyy (mặt sau CCCD "
        "'Ngày, tháng, năm' → Đơn 'Cấp ngày'). KHÔNG lấy ngày hết hạn 'Có giá trị đến'."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của người đề nghị: CCCD gắn chip in chức "
        "danh 'CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI' → 'Cục Cảnh sát quản lý hành chính về "
        "trật tự xã hội'; thẻ Căn cước mới 'BỘ CÔNG AN' → 'Bộ Công an'. Đơn viết tắt thì chuẩn hóa tên đầy đủ."},
    {"name": "NguoiDeNghi_DiaChiThuongTru", "desc": "Nơi thường trú của người đề nghị, CHÉP NGUYÊN VĂN một chuỗi "
        "(CCCD 'Nơi thường trú / Place of residence' → Đơn 'Đăng ký thường trú tại' / 'Địa chỉ thường trú'). Gộp các "
        "dòng của thẻ thành một chuỗi, ngăn cách bằng dấu phẩy."},
    {"name": "NguoiDeNghi_ThuongTru", "desc": "Nơi thường trú của người đề nghị dạng object {quocGia,tinh,xa,diaChi}"
        " để chọn trên form (chỉ có đơn vị hành chính MỚI, 34 tỉnh, không cấp huyện). Đơn ghi phường/xã MỚI thì "
        "lấy tinh/xa theo Đơn, còn không theo CCCD. diaChi = số nhà, đường, tổ/thôn (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Số điện thoại của người đề nghị (Đơn mục 'Điện thoại' / 'Điện thoại "
        "liên hệ'). Chỉ chữ số."},
    {"name": "NguoiDeNghi_Email", "desc": "Email của người đề nghị nếu đơn ghi. Không có thì bỏ."},
    {"name": "NguoiDeNghi_DonViCongTac", "desc": "Đơn vị công tác ghi trên đơn (vd 'Công ty TNHH Nhà Đất An Phú'). "
        "Không có thì bỏ."},
    {"name": "NguoiDeNghi_VanBang", "desc": "Mảng các văn bằng, chứng chỉ của người đề nghị, mỗi phần tử một chuỗi "
        "'Tên văn bằng – nơi cấp, năm cấp' (vd 'Bằng tốt nghiệp THPT – Trường THPT Lê Lợi, 2008'). Nguồn: Đơn mục "
        "'Văn bằng, chứng chỉ đã được cấp' → bản sao bằng tốt nghiệp THPT/trung cấp/cao đẳng/đại học CÓ trong hồ sơ "
        "→ Giấy chứng nhận hoàn thành khóa học môi giới BĐS. KHÔNG liệt kê CCCD. Không có thì bỏ."},
]

# --- Đơn ---
FIELDS += [
    {"name": "Don_Loai", "desc": 'Loại đơn trong hồ sơ: "dang_ky_du_thi" (ĐƠN ĐĂNG KÝ DỰ THI SÁT HẠCH / đơn đề nghị '
        'cấp chứng chỉ hành nghề môi giới BĐS), "cap_lai" (ĐƠN XIN / ĐỀ NGHỊ CẤP LẠI chứng chỉ), "khac" (đơn khác). '
        "Không có đơn thì bỏ."},
    {"name": "Don_KinhGui", "desc": "Nơi nhận đơn — dòng 'Kính gửi:' (vd 'Sở Xây dựng thành phố Đà Nẵng'). Chép "
        "nguyên văn, bỏ chữ 'Kính gửi:'."},
    {"name": "Don_DiaDanh", "desc": "Địa danh nơi làm đơn ở dòng '……, ngày … tháng … năm …' cuối đơn (vd 'Đà "
        "Nẵng'). Chỉ lấy tên địa danh."},
    {"name": "Don_NguoiLamDon", "desc": "Họ tên người làm đơn ký ở cuối đơn ('Người làm đơn' / 'Người đề nghị' — "
        "ký, ghi rõ họ tên)."},
    {"name": "Don_CamKet", "desc": '"Có" khi đơn có lời cam kết / cam đoan ("Tôi cam kết ..." / "Tôi cam đoan mọi '
        'thông tin ... đúng sự thật"), không có thì bỏ.'},
]

# --- Người nộp = tài khoản đăng nhập (chỉ từ thẻ CCCD của CHÍNH họ) ---
FIELDS += [
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (xem nguoi_nop_context) — không có "
        "thẻ đó thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh 12 số trên CHÍNH thẻ CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp, dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép đúng như in trên thẻ."},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú trên thẻ CCCD người nộp, object {quocGia,tinh,xa,diaChi}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP nếu hồ sơ ghi cạnh đúng tên người đó (vd "
        "giấy giới thiệu 'Người liên hệ: ..., ĐT ...'). Không có thì bỏ."},
]

# --- Tổ chức nộp hồ sơ (panel Thông tin doanh nghiệp) ---
_TO_CHUC_SRC = ("CHỈ lấy từ giấy tờ CỦA TỔ CHỨC có trong hồ sơ (Giấy chứng nhận đăng ký doanh nghiệp, giấy giới "
                "thiệu / văn bản đề nghị của tổ chức). KHÔNG lấy từ mục 'Đơn vị công tác' của đơn cá nhân")
FIELDS += [
    {"name": "ToChuc_Ten", "desc": f"Tên doanh nghiệp / tổ chức nộp hồ sơ. {_TO_CHUC_SRC}."},
    {"name": "ToChuc_MaSoThue", "desc": f"Mã số doanh nghiệp / mã số thuế của tổ chức, chỉ chữ số. {_TO_CHUC_SRC}."},
    {"name": "ToChuc_DienThoai", "desc": f"Số điện thoại của tổ chức. {_TO_CHUC_SRC}."},
    {"name": "ToChuc_DiaChi", "desc": "Địa chỉ trụ sở chính của tổ chức, object {quocGia,tinh,xa,diaChi}. "
        f"{_TO_CHUC_SRC}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiDeNghi_ThuongTru", "NguoiNop_DiaChi", "ToChuc_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiDeNghi_VanBang"] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.012906, sheet Cá nhân + Tổ chức).
# Phần I: data[fullname], data[birthday], data[identityNumber] cổng đổ từ tài khoản → KHÔNG phát. data[tenHoSo]
# (nhãn "Ghi chú"), data[AuthorityApplicantPhoneNumber] hồ sơ không có nguồn → bỏ. Các ô ẩn (data[note],
# data[photoFile], data[attachedDocuments] ...) và data[dateTime] (disabled, cổng tự điền ngày nộp) → bỏ.
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp hồ sơ.
    "data[chonDoiTuong]": "dom-select",         # Cá nhân / Tổ chức — chỉ đổi khi hồ sơ có giấy tờ của tổ chức.
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",       # Nơi cấp — danh mục tải qua API.
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",             # "Phường/xã".
    "data[address]": "dom-input",
    # Phần I-b — thông tin doanh nghiệp (panel thongTinDoanhNghiep, chỉ hiện khi Tổ chức).
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    # Phần II — Đơn đăng ký dự thi sát hạch (panel brokerExamRegistrationForm).
    "data[TinTTTe1]": "dom-select",             # "Tại" — tỉnh/TP nơi làm đơn.
    "data[recipient]": "dom-input",             # Kính gửi.
    "data[fullName]": "dom-input",              # ⚠ chữ N hoa — KHÁC data[fullname] của Phần I.
    "data[birthday]": "dom-date",               # ⚠ TRÙNG key Phần I → mapper gắn DON_SCOPE.
    "data[provincenoisinh]": "dom-select",      # Nơi sinh (bắt buộc) — chỉ cấp tỉnh.
    "data[nationality]": "dom-input",
    "data[idType]": "dom-select",
    "data[idNumber]": "dom-input",
    "data[CapNGay]": "dom-date",
    "data[idIssuePlace]": "dom-input",          # "Tại" (nơi cấp) — nhập tự do.
    "data[permanentAddress]": "dom-input",      # Một chuỗi đầy đủ.
    "data[contactPhone]": "dom-input",
    "data[educationCertificates]": "dom-input",  # textarea.
    "data[commitment]": "dom-checkbox",
    "data[KyGhiRoHoTen]": "dom-input",
}

# Đơn là form Form.io RIÊNG nhưng dùng lại key data[birthday] của Phần I (ngày sinh TÀI KHOẢN đăng nhập). Dò cả
# trang thì trúng ô Phần I trước → giới hạn vùng dò trong panel đơn; panel đó bọc cả trang thì leo ngược từ ô neo
# data[provincenoisinh] (chỉ có trong đơn), vẫn không tách được thì BỎ ô — thà trống còn hơn ghi đè Phần I.
DON_SCOPE = ".formio-component-brokerExamRegistrationForm"
DON_SCOPE_NEAR = "data[provincenoisinh]"
NGUOI_NOP_MARKERS = ("data[chonDoiTuong]", "data[identityAgency]")
DON_SCOPED_FIELDS = frozenset({"data[birthday]"})

# Nhãn option ô "Loại giấy tờ" (data[idType]) chép đúng chữ trên form.
ID_TYPE_LABELS = {
    "cmnd": "CMND (Chứng minh nhân dân)",
    "cccd": "CCCD (Căn cước công dân)",
    "the_can_cuoc": "Thẻ căn cước",
    "ho_chieu": "Hộ chiếu",
}
