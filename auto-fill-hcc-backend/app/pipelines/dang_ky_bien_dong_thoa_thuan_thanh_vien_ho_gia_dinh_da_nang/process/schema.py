"""Compact schema cho "Đăng ký biến động đối với trường hợp thay đổi QSDĐ, QSH tài sản gắn liền với đất theo thỏa
thuận của các thành viên hộ gia đình hoặc của vợ và chồng; … tài sản công; … giải quyết tranh chấp, bản án, quyết
định thi hành án; … xử lý tài sản thế chấp" (1.013980) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io).
CÙNG cổng/engine với dang_ky_bien_dong_dat_dai_da_nang (1.013831), mapping theo
"Mapping_DK_bien_dong_dat_dai_*.xlsx".

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = bên ĐƯỢC ĐĂNG KÝ biến động (người được đứng tên theo thỏa thuận, bên mua tài sản
               đấu giá/tài sản công, bên được nhận QSDĐ theo bản án/quyết định…) — mục 1 Đơn đăng ký biến động.
               Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP = người trực tiếp nộp, thường là người được ỦY QUYỀN; tự nộp thì = chủ hồ sơ.
Phần II: THỬA ĐẤT biến động (địa chỉ/số tờ/số thửa MỚI NHẤT theo Giấy chứng nhận + trang biến động).
Bên chuyển quyền (người đứng tên cũ trên GCN, người phải thi hành án, bên bán) KHÔNG lên form.
"""

# --- Chủ hồ sơ (bên được đăng ký biến động) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan/đơn vị '
        '(tên có "Công ty", "Doanh nghiệp", "Hợp tác xã", "Ủy ban", "Trung tâm"…); "Cá nhân" nếu là một người.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ = người/tổ chức ĐƯỢC ĐĂNG KÝ biến động, ghi ở mục 1 Đơn đăng ký "
        "biến động 'Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất…' — a) Tên. Cá nhân: họ và tên IN HOA; "
        "tổ chức: tên đầy đủ. Đối chiếu: bên mua trúng đấu giá / bên B trên hợp đồng mua bán tài sản, người được "
        "giao tài sản trên quyết định thi hành án, người được đứng tên theo văn bản thỏa thuận/bản án. ⚠ KHÔNG lấy "
        "người đứng tên cũ trên Giấy chứng nhận gốc (bên chuyển quyền, người phải thi hành án)."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh CHỦ HỒ SƠ: tổ chức = mã số doanh nghiệp/mã số thuế (Đơn mục "
        "1b 'Giấy tờ nhân thân/pháp nhân', hợp đồng, tờ khai thuế của chính tổ chức đó); cá nhân = số CCCD. CHỈ chữ số."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ CHỦ HỒ SƠ (trụ sở tổ chức / thường trú cá nhân), object "
        "{quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên Đơn mục 1c 'Địa chỉ' (tên đơn vị hành chính MỚI). tinh='Tỉnh/Thành "
        "phố …', xa=phường/xã, chiTietDuoiXa=số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "NoiDungBienDong", "desc": "Mục '2. Nội dung biến động' của Đơn đăng ký biến động — CHÉP NGUYÊN VĂN cả "
        "câu (vd 'Nhận quyền sử dụng đất theo bản án số … và cấp đổi Giấy chứng nhận'). KHÔNG tự viết lại/bịa."},
    {"name": "DienThoaiLienHe", "desc": "Số điện thoại liên hệ của HỒ SƠ, theo thứ tự ưu tiên: Đơn mục 1 'Điện thoại "
        "liên hệ' → 'Số điện thoại liên hệ' trên Giấy tiếp nhận hồ sơ và hẹn trả kết quả → 'Điện thoại' trên Tờ khai "
        "lệ phí trước bạ của chính chủ hồ sơ. Chỉ chữ số. Không có thì bỏ."},
    {"name": "GhiChu", "desc": "CHỈ khi hồ sơ có ĐƠN CAM KẾT của chủ hồ sơ: ghi 'Theo Đơn cam kết ngày dd/mm/yyyy: "
        "<trích yếu V/v chép nguyên văn>'. Không có đơn cam kết thì BỎ."},
]

# --- Người nộp hồ sơ (người thao tác nộp; thường được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP (một CÁ NHÂN). Có Giấy/Hợp đồng ủy quyền → BÊN ĐƯỢC ỦY "
        "QUYỀN ('ủy quyền cho ông/bà …'). Chủ hồ sơ cá nhân tự nộp → = ChuHoSo_HoTen. Chủ hồ sơ tổ chức mà KHÔNG có "
        "ủy quyền kèm số CCCD người đi nộp → BỎ. IN HOA."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP dd/mm/yyyy — chỉ từ CCCD/giấy ủy quyền của chính người "
        "đó. Giấy tờ không ghi thì BỎ (không suy từ số CCCD)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP "Nam"/"Nữ" — CCCD, hoặc danh xưng Ông/Bà đứng trước '
        'tên người được ủy quyền. Không có thì bỏ.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân của CHÍNH NGƯỜI NỘP (cùng người với "
        "NguoiNop_HoTen), đọc ở CCCD hoặc giấy ủy quyền ('CCCD số …' của bên được ủy quyền). Chỉ chữ số. TUYỆT ĐỐI "
        "KHÔNG lấy CCCD người đại diện pháp luật/bên ủy quyền/bên bán."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP dd/mm/yyyy (CCCD mặt sau / giấy ủy quyền 'cấp "
        "ngày'). KHÔNG lấy ngày cấp CCCD của người khác hay ngày cấp giấy phép kinh doanh."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD của NGƯỜI NỘP, chép ĐÚNG như ghi trên CCCD/giấy ủy quyền (vd 'Cục "
        "Cảnh sát quản lý hành chính về trật tự xã hội', 'Bộ Công an'). Giấy tờ không ghi thì BỎ, không suy đoán."},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,chiTietDuoiXa} — CCCD "
        "(Nơi thường trú/Nơi cư trú) hoặc địa chỉ người được ủy quyền trên giấy ủy quyền. KHÔNG lấy địa chỉ trụ sở "
        "tổ chức hay địa chỉ thửa đất."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

# --- Phần II: thửa đất biến động ---
FIELDS += [
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT biến động, object {quocGia,tinh,xa,chiTietDuoiXa}. Lấy ĐỊA "
        "CHỈ MỚI NHẤT: Giấy chứng nhận mục 'Những thay đổi sau khi cấp Giấy chứng nhận' (vd 'tên phường thay đổi "
        "từ … thành …') được ưu tiên hơn địa chỉ gốc in trên GCN; sau đó Đơn cam kết, hợp đồng sửa đổi bổ sung, tờ "
        "khai lệ phí trước bạ. chiTietDuoiXa = đường/tổ/thôn (vd 'Quốc lộ 1A')."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ của thửa đất, số MỚI NHẤT (trang biến động của GCN 'thay đổi thành "
        "số thửa …, tờ bản đồ số …' ưu tiên hơn số gốc/ghi tay cũ; rồi hợp đồng sửa đổi bổ sung, tờ khai). Chỉ số."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất, số MỚI NHẤT (cùng nguồn và cùng thửa với ThuaDat_SoTo). Chỉ số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ThuaDat_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key lấy CHUẨN từ HTML thật (sheet Mapping).
UI_COMP_BY_NAME = {
    # Phần I — chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",       # "Chủ hồ sơ cũng là người nộp" — bỏ tích khi ủy quyền.
    # Phần I — người nộp.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",  # textarea — chép mục 2 Đơn.
    "data[chonDoiTuong]": "dom-select",           # Cá nhân/Tổ chức — theo loại CHỦ HỒ SƠ (mapping).
    "data[taxCode]": "dom-input",                 # Mã định danh tổ chức — chỉ hiện khi chọn "Tổ chức".
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # Phần II — thửa đất.
    "data[diaChiThuaDat]": "dom-input",           # textarea địa chỉ thửa đất.
    "data[SoToBanDo]": "dom-input",
    "data[SoThuaDat]": "dom-input",
    "data[nation2]": "dom-select",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
}
