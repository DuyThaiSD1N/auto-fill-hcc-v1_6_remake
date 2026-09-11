"""Compact schema cho "Cấp lại Chứng chỉ hành nghề thú y" (mã 1.005319 — Sở Nông nghiệp và Môi trường,
Form.io trên Cổng DVC quốc gia).

Form bước kê khai có ĐỦ hai khối nhân thân giống #97/#101 rồi mới tới tờ đơn:
  Phần I  "THÔNG TIN NGƯỜI NỘP HỒ SƠ" → data[fullname…]: cổng tự đổ nhân thân TÀI KHOẢN ĐANG ĐĂNG NHẬP,
          ô số căn cước còn bị khoá. Người trong hồ sơ KHÔNG thuộc khối này — ghi đè vào đây là ghép
          họ tên người này với giấy tờ tùy thân người kia.
  Phần II "THÔNG TIN CHỦ HỒ SƠ"       → data[owner…]: đây mới là NGƯỜI ĐỀ NGHỊ cấp lại chứng chỉ.
  Panel phuLuc1 (tờ đơn)              → "Kính gửi" + "Nội dung đơn đăng ký".
Ô tích "Người nộp hồ sơ là chủ hồ sơ" (data[isOwnerDossierCheck]) khoá Phần II; bỏ tích thì mới điền được.

Nhóm field:
- NguoiDeNghi_* : nhân thân người đứng đơn (nguồn duy nhất cho "Thông tin chung").
- NguoiNop_*    : chỗ để LLM "đỗ" nhân thân người nộp thay, KHÔNG đổ ra form — tránh lẫn vào người đứng đơn.
- Don_*         : nội dung Đơn đăng ký cấp lại (Mẫu 03.HNTY).
- CCHNCu_*      : Chứng chỉ hành nghề thú y ĐÃ CẤP (số đăng ký + ngày hết hiệu lực).
"""

_DENGHI_SRC = "CCCD / Đơn đăng ký cấp lại Chứng chỉ hành nghề thú y (Mẫu 03.HNTY) của NGƯỜI ĐỀ NGHỊ"

# --- Nhân thân người đứng đơn (form KHÔNG có ô giới tính / nơi cấp / email) ---
FIELDS: list[dict] = [
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ và tên NGƯỜI ĐỀ NGHỊ (người đứng tên Đơn 03.HNTY, người "
        f"được cấp lại chứng chỉ). Lấy từ {_DENGHI_SRC}, mục 'Tên tôi là'. Ghi IN HOA."},
    {"name": "NguoiDeNghi_NgaySinh", "desc": "Ngày sinh NGƯỜI ĐỀ NGHỊ, dd/mm/yyyy — CCCD hoặc Đơn "
        "03.HNTY (mục 'Ngày tháng năm sinh')."},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số CCCD/căn cước/định danh cá nhân NGƯỜI ĐỀ NGHỊ. Đọc "
        "CCCD (mặt trước/MRZ) hoặc Đơn 03.HNTY (mục 'Số CMND/CCCD'). Chỉ chữ số, ưu tiên số 12 chữ số. "
        "Đơn KHÔNG ghi và hồ sơ KHÔNG có CCCD của họ thì BỎ TRỐNG — tuyệt đối không lấy số của người "
        "nộp thay."},
    {"name": "NguoiDeNghi_NgayCapCCCD", "desc": "Ngày cấp CCCD/căn cước của NGƯỜI ĐỀ NGHỊ (mặt sau CCCD), "
        "dd/mm/yyyy. ⚠ 'Ngày cấp' đứng ngay sau dòng 'Bằng cấp chuyên môn' trong Đơn 03.HNTY là ngày cấp "
        "BẰNG, KHÔNG phải ngày cấp CCCD → gặp trường hợp đó thì BỎ TRỐNG field này."},
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính NGƯỜI ĐỀ NGHỊ: "Nam" hoặc "Nữ", đọc ở CCCD '
        "(Giới tính / Sex). Đơn 03.HNTY không có mục này; KHÔNG suy từ họ tên."},
    {"name": "NguoiDeNghi_NoiCapCCCD", "desc": "Nơi cấp giấy tờ tùy thân NGƯỜI ĐỀ NGHỊ. Mặt sau CCCD ghi "
        '"CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành '
        'chính về trật tự xã hội"; thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an"; CMND ~9 số lấy '
        '"Công an tỉnh/thành phố …" ghi trên giấy.'},
    {"name": "NguoiDeNghi_ThuongTru", "desc": "NƠI THƯỜNG TRÚ / nơi cư trú NGƯỜI ĐỀ NGHỊ, object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở CCCD (Nơi thường trú) / Đơn 03.HNTY (Địa chỉ thường trú). "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/khóm/ấp/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Số điện thoại DI ĐỘNG NGƯỜI ĐỀ NGHỊ. Chỉ chữ số; KHÔNG "
        "lấy số bàn. Đơn 03.HNTY có mục 'Số điện thoại liên hệ'."},
    # Hai field dưới CHỈ để tách vai, mapper KHÔNG đổ ra form.
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP THAY — CHỈ điền khi hồ sơ có CCCD RIÊNG của "
        "người nộp và người đó KHÁC người đứng đơn. Tự nộp → bỏ trống."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh NGƯỜI NỘP THAY, chỉ chữ số. Tự nộp → bỏ trống."},
]

# --- Nội dung Đơn đăng ký cấp lại Mẫu 03.HNTY ---
FIELDS += [
    {"name": "Don_KinhGui", "desc": "Nơi nhận đơn — mục 'Kính gửi' của Đơn 03.HNTY (vd 'Chi cục Chăn "
        "nuôi và Thú y tỉnh Lai Châu'). Chép nguyên văn, bỏ chữ 'Kính gửi:'."},
    {"name": "Don_LaNguoiNuocNgoai", "desc": "Người đứng đơn có phải NGƯỜI NƯỚC NGOÀI không: trả 'Có' "
        "CHỈ khi giấy tờ thể hiện rõ quốc tịch nước ngoài hoặc dùng hộ chiếu nước ngoài; công dân Việt "
        "Nam (có CCCD) → 'Không'."},
    {"name": "Don_BangCapChuyenMon", "desc": "Bằng cấp chuyên môn ghi ở Đơn 03.HNTY (vd 'Bác sĩ thú y', "
        "'Kỹ sư Chăn nuôi - Thú y'). CHỈ lấy tên bằng, KHÔNG kèm ngày cấp/nơi cấp bằng."},
    {"name": "Don_PhamViHanhNghe", "desc": "Phạm vi hành nghề được ĐÁNH DẤU (☑/x/✓) trong danh sách ở "
        "mục đề nghị của Đơn 03.HNTY, vd 'Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn'. "
        "Chép NGUYÊN VĂN, ĐẦY ĐỦ cả đuôi 'trên cạn' / 'thủy sản'; nhiều dòng được tích thì ngăn cách "
        "bằng dấu ';'. KHÔNG liệt kê dòng không được tích."},
    {"name": "Don_LyDoCapLai", "desc": "Lý do đề nghị CẤP LẠI ghi ở Đơn 03.HNTY (vd 'Chứng chỉ bị mất', "
        "'Chứng chỉ bị hư hỏng', 'Sai sót thông tin', 'Thay đổi thông tin cá nhân'). Đơn không ghi thì "
        "bỏ trống."},
    {"name": "Don_DiaDiem", "desc": "Địa danh nơi lập đơn — phần '……, ngày … tháng … năm …' của Đơn "
        "03.HNTY. Chỉ lấy tên địa danh (vd 'Lai Châu')."},
    {"name": "Don_NgayLamDon", "desc": "Ngày lập đơn ở dòng '……, ngày … tháng … năm …' của Đơn 03.HNTY, "
        "dd/mm/yyyy."},
    {"name": "Don_NguoiLamDon", "desc": "Họ tên NGƯỜI LÀM ĐƠN ký ở cuối Đơn 03.HNTY (ký, ghi rõ họ tên). "
        "Thường trùng NguoiDeNghi_HoTen."},
]

# --- Chứng chỉ hành nghề thú y ĐÃ CẤP (bản cũ) ---
FIELDS += [
    {"name": "CCHNCu_SoDangKy", "desc": "SỐ ĐĂNG KÝ (số hiệu) in trên Chứng chỉ hành nghề thú y ĐÃ CẤP "
        "trước đó, vd '123/CCHN-TY'. Ô trên form đã in sẵn đuôi '-CCHNTY' → chỉ lấy PHẦN SỐ đứng trước. "
        "Lấy ở bản chụp Chứng chỉ cũ; Đơn 03.HNTY cũng có thể ghi lại. KHÔNG lấy số của đơn."},
    {"name": "CCHNCu_NgayHetHan", "desc": "Ngày HẾT HIỆU LỰC của Chứng chỉ hành nghề thú y đã cấp — dòng "
        "'Chứng chỉ có giá trị đến ngày …' trên Chứng chỉ cũ, dd/mm/yyyy. KHÔNG nhầm với ngày cấp."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiDeNghi_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_NgayCapCCCD"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Don_NgayLamDon"] = "x-date"
COMPACT_COMP_BY_NAME["CCHNCu_NgayHetHan"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*, tên đọc từ DOM thật của panel phuLuc1. FE
# standardNameVariants tự thử cả "data[x]" lẫn "x" nên khớp được cả Form.io lẫn Angular reactive form.
UI_COMP_BY_NAME = {
    "data[kinhGui]": "dom-input",

    # --- Phần I "THÔNG TIN NGƯỜI NỘP HỒ SƠ" = TÀI KHOẢN ĐANG ĐĂNG NHẬP ---
    # KHÔNG có ô nào của Phần I ở đây: cổng đã đổ sẵn nhân thân tài khoản VNeID (ô số căn cước còn bị
    # khoá) nên mọi thao tác ghi vào khối này đều là ghi đè lên người khác — kể cả ô "Đối tượng nộp hồ
    # sơ" (thuộc tính của tài khoản, không phải của hồ sơ).

    # Ô tích "Người nộp hồ sơ là chủ hồ sơ": còn tích thì Phần II bị khoá. Không phải dữ liệu nhân thân
    # nên được phép chạm — bỏ tích chỉ để MỞ KHOÁ Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # --- Phần II "THÔNG TIN CHỦ HỒ SƠ" = NGƯỜI ĐỀ NGHỊ cấp lại chứng chỉ ---
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",       # "Tỉnh/Thành phố".
    "data[ownerDistrict]": "dom-select",       # "Phường/Xã".
    "data[ownerAddress]": "dom-input",         # "Địa chỉ chi tiết".
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerNation]": "dom-select",         # "Quốc gia".

    # --- Tờ đơn 03.HNTY, mục "Thông tin chung" = NGƯỜI ĐỨNG ĐƠN ---
    # ⚠ Bước tờ đơn là MỘT form Form.io RIÊNG nên field-key trùng khít Phần I ở bước trước
    # (data[fullname], data[birthday]…) dù là hai người khác nhau khi nộp thay. Mapper gắn kèm
    # DON_SCOPE để extension chỉ điền khi đang mở đúng bước tờ đơn.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",          # ô "Ngày cấp" cạnh số căn cước.
    "data[province]": "dom-select",            # "Tỉnh/Thành phố".
    "data[district]": "dom-select",            # "Phường xã".
    "data[address]": "dom-input",              # "Địa chỉ chi tiết".
    "data[phoneNumber]": "dom-input",
    "data[toiLaNguoiNuocNgoai]": "dom-checkbox",
    "data[bangCapChuyenMon]": "dom-input",

    # --- Nội dung đơn đăng ký ---
    # Selectboxes 12 phạm vi: MỌI option dùng chung name "data[deNghi][]", chỉ khác value (a, b, c…) và
    # nhãn. Value do Form.io sinh nên BE không đoán được → gửi kèm optionLabel để FE khớp theo NHÃN.
    "data[deNghi][]": "dom-checkbox",
    "data[soDK]": "dom-input",
    "data[ngayCC]": "dom-date",                # nhãn "Chứng chỉ có giá trị đến".
    "data[lyDo]": "dom-input",
    "data[diaDiem]": "dom-input",
    "data[thoiGian]": "dom-date",
    "data[nguoiLD]": "dom-input",
}

PHAM_VI_FIELD_KEY = "data[deNghi][]"

# Panel bọc toàn bộ tờ đơn 03.HNTY. Extension chỉ điền ô mang scope này khi trang đang mở có panel đó,
# nhờ vậy field-key trùng tên với Phần I (bước Thông tin chung) không bị điền nhầm sang bước kia.
DON_SCOPE = ".formio-component-phuLuc1"

# Ô neo của tờ đơn: field-key CHỈ có trong tờ đơn, nằm cùng khối "Thông tin chung" với các ô trùng tên.
# Khi DON_SCOPE trỏ vào panel bọc cả trang, extension leo ngược từ ô neo này để tìm đúng khối tờ đơn.
DON_SCOPE_NEAR = "data[bangCapChuyenMon]"

# Mốc nhận diện HAI khối nhân thân đứng TRƯỚC tờ đơn. Ô nào của tờ đơn mà vùng dò còn chứa một trong
# các mốc này thì vùng dò vẫn quá rộng → extension thu hẹp, không thu hẹp được thì BỎ ô.
# data[chonDoiTuong] + data[isOwnerDossierCheck]: Phần I người nộp. data[ownerFullname]: Phần II chủ hồ sơ.
NGUOI_NOP_MARKERS = (
    "data[chonDoiTuong]",
    "data[isOwnerDossierCheck]",
    "data[ownerFullname]",
)

# Ô của tờ đơn dùng CHUNG field-key với Phần I → bắt buộc kèm scope.
DON_SCOPED_FIELDS = frozenset({
    "data[fullname]",
    "data[birthday]",
    "data[identityNumber]",
    "data[identityDate]",
    "data[province]",
    "data[district]",
    "data[address]",
    "data[phoneNumber]",
})

# 12 nhãn option của mục "Đã được cấp Chứng chỉ hành nghề thú y", chép ĐÚNG chữ trên form (kể cả dấu
# chấm cuối) vì FE khớp checkbox theo chính nhãn này.
PHAM_VI_OPTIONS: list[str] = [
    "Tiêm phòng, chữa bệnh, tiểu phẫu (thiến, cắt đuôi) động vật, tư vấn các hoạt động liên quan đến lĩnh vực thú y.",
    "Khám bệnh, chẩn đoán bệnh, phẫu thuật động vật, xét nghiệm bệnh động vật.",
    "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn.",
    "Buôn bán thuốc thú y dùng trong thú y cho động vật thủy sản.",
    "Sản xuất thuốc thú y dùng trong thú y cho động vật trên cạn.",
    "Sản xuất thuốc thú y dùng trong thú y cho động vật thủy sản.",
    "Xuất khẩu, nhập khẩu thuốc thú y dùng trong thú y cho động vật trên cạn.",
    "Xuất khẩu, nhập khẩu thuốc thú y dùng trong thú y cho động vật thủy sản.",
    "Khảo nghiệm thuốc thú y dùng trong thú y cho động vật trên cạn.",
    "Khảo nghiệm thuốc thú y dùng trong thú y cho động vật thủy sản.",
    "Kiểm nghiệm thuốc thú y dùng trong thú y cho động vật trên cạn.",
    "Kiểm nghiệm thuốc thú y dùng trong thú y cho động vật thủy sản.",
]
