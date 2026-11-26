"""Compact schema cho "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061) — cổng Bộ Xây dựng
(Form.io, engine fillFormStandard dom-*).

Hồ sơ: Đơn đề nghị cấp phép thi công (mẫu Đơn_TT1.013061) + hồ sơ khoảng cách tới dải phân cách giữa + báo cáo thẩm
tra / tính toán khả năng chịu lực cầu + thuyết minh, bản vẽ biện pháp tổ chức thi công, bảo đảm giao thông, hoàn trả +
bản vẽ thiết kế thi công; có thể kèm CCCD. Theo mapping 1.013061, thứ tự nguồn: CCCD → Đơn đề nghị → giấy tờ chuyên
ngành (chủ đầu tư ghi ở bìa / khung tên bản vẽ); riêng địa chỉ: Đơn (địa danh mới) trước CCCD (địa danh cũ).

BA vai:
- NguoiDeNghi_* : người đứng đơn (chủ đầu tư cá nhân; tổ chức thì người đại diện ký đơn).
- NguoiNop_*    : NGƯỜI NỘP = tài khoản đăng nhập, chỉ từ CCCD KHỚP tài khoản (nộp thay).
- ToChuc_*      : TỔ CHỨC đề nghị cấp phép → "Chọn đối tượng" = Tổ chức + panel thongTinDoanhNghiep.
"""

_NGUON = ("CCCD của người đứng đơn → Đơn đề nghị (góc trái tiêu đề, thân đơn 'Ông/Bà … đề nghị', khung ký NGƯỜI ĐỀ "
          "NGHỊ) → bìa / thuyết minh / khung tên bản vẽ mục 'Chủ đầu tư'")

FIELDS: list[dict] = [
    {"name": "NguoiDeNghi_LoaiDoiTuong", "desc": '"Cá nhân" khi người đứng đơn là cá nhân (góc trái tiêu đề Đơn ghi '
        '"CÁ NHÂN ĐỀ NGHỊ CẤP PHÉP" + họ tên, chủ đầu tư là "Ông/Bà ..."); "Tổ chức" khi đơn đứng tên doanh nghiệp, '
        "cơ quan, tổ chức (góc trái ghi tên tổ chức, có số văn bản, đóng dấu)."},
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ và tên CÁ NHÂN đứng đơn đề nghị cấp phép (chủ đầu tư). Tổ chức đứng đơn "
        f"thì lấy người đại diện ký đơn. Nguồn: {_NGUON}. Ghi như CCCD."},
    {"name": "NguoiDeNghi_NgaySinh", "desc": "Ngày sinh người đứng đơn, dd/mm/yyyy (CCCD → thuyết minh thiết kế "
        "'Chủ đầu tư: Ông ..., sinh ngày ...')."},
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính người đứng đơn: "Nam"/"Nữ" theo CCCD (Giới tính / Sex, MRZ '
        "M/F). Không có CCCD thì bỏ — KHÔNG suy từ họ tên hay chữ 'Ông/Bà'."},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số CCCD / số định danh cá nhân 12 số của người đứng đơn (CCCD → Đơn "
        "dòng 'Mã số định danh VNeID của cơ quan, tổ chức, cá nhân đề nghị cấp' → 'CCCD số' ở thuyết minh / báo cáo "
        "thẩm tra). Chỉ chữ số. Tổ chức đứng đơn thì số đó là của tổ chức → ghi vào ToChuc_MaSoThue, ô này bỏ."},
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD người đứng đơn, dd/mm/yyyy (mặt sau CCCD 'Ngày, tháng, "
        "năm'). KHÔNG lấy ngày hết hạn 'Có giá trị đến'. Không có CCCD thì bỏ."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Cơ quan cấp CCCD người đứng đơn: CCCD gắn chip in 'CỤC TRƯỞNG CỤC CẢNH SÁT "
        "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; thẻ Căn cước "
        "mới 'BỘ CÔNG AN' → 'Bộ Công an'. Không có CCCD thì bỏ."},
    {"name": "NguoiDeNghi_DiaChi", "desc": "Địa chỉ liên hệ / thường trú của người đứng đơn dạng object "
        "{quocGia,tinh,xa,chiTietDuoiXa} (chỉ đơn vị hành chính MỚI: 34 tỉnh, không cấp huyện). ƯU TIÊN dòng 'Địa chỉ "
        "liên hệ' của Đơn (địa danh mới) → 'địa chỉ' chủ đầu tư ở thuyết minh / báo cáo thẩm tra → CCCD 'Nơi thường "
        "trú' (CCCD cũ ghi xã/huyện trước sáp nhập). chiTietDuoiXa = thôn/xóm, số nhà, đường (KHÔNG kèm xã/tỉnh). "
        "KHÔNG lấy địa điểm xây dựng công trình (Km, Quốc lộ) làm địa chỉ."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Số điện thoại người đứng đơn (Đơn '+ Số điện thoại' → thuyết minh "
        "'điện thoại' của chủ đầu tư → biển thông tin công trình 'Chủ đầu tư: ... – ĐT ...'). KHÔNG lấy số của chỉ "
        "huy trưởng, cán bộ ATGT, đơn vị tư vấn."},
    {"name": "NguoiDeNghi_Email", "desc": "Email người đứng đơn (Đơn 'Email:'). Không có thì bỏ."},
    {"name": "Don_KinhGui", "desc": "Cơ quan nhận đơn — dòng 'Kính gửi:' của Đơn (vd 'Khu Quản lý đường bộ I – Cục "
        "Đường bộ Việt Nam'). Bỏ chữ 'Kính gửi:'."},
    {"name": "Don_NhanKetQua", "desc": 'Phương thức nhận kết quả được đánh dấu X / ☒ trong Đơn: "truc_tiep", '
        '"truc_tuyen" hoặc "buu_chinh". Không đánh dấu ô nào thì bỏ.'},
]

# --- Người nộp = tài khoản đăng nhập (chỉ từ thẻ CCCD của CHÍNH họ) ---
FIELDS += [
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (xem nguoi_nop_context) — không có "
        "thẻ đó thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh 12 số trên CHÍNH thẻ CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp, dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép đúng như in trên thẻ."},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú trên thẻ CCCD người nộp, object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP nếu hồ sơ ghi cạnh đúng tên người đó (vd giấy "
        "ủy quyền). Không có thì bỏ."},
]

# --- Tổ chức đứng đơn (panel Thông tin doanh nghiệp) ---
_TO_CHUC_SRC = ("CHỈ khi người đứng đơn là TỔ CHỨC (doanh nghiệp, cơ quan): lấy từ Đơn (góc trái, dòng liên hệ, mã "
                "số định danh / mã số thuế) hoặc Giấy chứng nhận đăng ký doanh nghiệp. Đơn vị tư vấn thiết kế, đơn "
                "vị thẩm tra, nhà thầu thi công KHÔNG phải tổ chức đứng đơn")
FIELDS += [
    {"name": "ToChuc_Ten", "desc": f"Tên doanh nghiệp / tổ chức đứng đơn. {_TO_CHUC_SRC}."},
    {"name": "ToChuc_MaSoThue", "desc": f"Mã số doanh nghiệp / mã số thuế / mã định danh của tổ chức, chỉ chữ số. "
        f"{_TO_CHUC_SRC}."},
    {"name": "ToChuc_DienThoai", "desc": f"Số điện thoại của tổ chức. {_TO_CHUC_SRC}."},
    {"name": "ToChuc_DiaChi", "desc": "Địa chỉ trụ sở của tổ chức, object {quocGia,tinh,xa,chiTietDuoiXa}. "
        f"{_TO_CHUC_SRC}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiDeNghi_DiaChi", "NguoiNop_DiaChi", "ToChuc_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — field-key theo mapping 1.013061 (DOM cá nhân + DOM tổ chức).
# Bỏ: data[tenHoSo] (nhãn "Ghi chú", mapping ghi "CẦN XÁC NHẬN"), data[AuthorityApplicantPhoneNumber] (chỉ khi nộp
# theo ủy quyền, hồ sơ không có nguồn), 3 ô ẩn data[note] / data[noidungyeucaugiaiquyet] / data[ownerFullname].
# Bước 3 receivingKind (mat-select Angular) + bước 4 cam kết / captcha → cổng / người dùng lo, KHÔNG điền.
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp hồ sơ.
    "data[chonDoiTuong]": "dom-select",         # Cá nhân / Tổ chức — đổi TRƯỚC để mở panel doanh nghiệp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",       # Nơi cấp — danh mục tải qua API.
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",             # "Phường/xã".
    "data[address]": "dom-input",
    # Phần II — panel thongTinDoanhNghiep (chỉ hiện khi Tổ chức).
    "data[organization]": "dom-input",
    "data[nation1]": "dom-select",
    "data[address1]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[province1]": "dom-select",
    "data[organizationPhoneNumber]": "dom-input",
    "data[district1]": "dom-select",
    # Khối "Thông tin chi tiết" (mapping KHÔNG có, người dùng gửi ảnh DOM 24/11): panel "Thông tin Tổ chức, cá nhân"
    # là container Form.io key "container" — ĐÃ THẤY data[container][province] + component phoneNumber trong
    # container. Các ô còn lại CHƯA thấy key → khai tên theo khuôn Phần I (container nhân bản nhóm địa chỉ) kèm
    # aliases; ô không có trên trang thì extension báo notFound, không ghi nhầm ô khác.
    "data[container][organization]": "dom-input",  # "Tên tổ chức hoặc cơ quan cấp trên" — người đề nghị.
    "data[container][province]": "dom-select",
    "data[container][district]": "dom-select",       # "Phường/xã" — cascade theo Tỉnh/TP của container.
    "data[container][address]": "dom-input",
    "data[container][phoneNumber]": "dom-input",
    # "Tại" (select tỉnh, bắt buộc) + "(Ký tên và đóng dấu)" — key CHƯA thấy, thử theo các form cùng cổng.
    "data[TinTTTe]": "dom-select",
    "data[kyTen]": "dom-input",
}

# Tên dự phòng extension thử lần lượt (fieldCandidates) khi tên chính không có trên trang.
UI_ALIASES: dict[str, list[str]] = {
    "data[container][organization]": ["data[container][tenToChuc]", "data[container][tenToChucCaNhan]",
                                      "data[container][fullname]", "data[container][hoTen]"],
    "data[container][district]": ["data[container][ward]", "data[container][phuongXa]"],
    "data[container][address]": ["data[container][diaChi]", "data[container][diaChiChiTiet]"],
    "data[TinTTTe]": ["data[TinTTTe1]", "data[panel][TinTTTe]", "data[container][TinTTTe]"],
    "data[kyTen]": ["data[KyGhiRoHoTen]", "data[panel][kyTen]", "data[container][kyTen]"],
}
