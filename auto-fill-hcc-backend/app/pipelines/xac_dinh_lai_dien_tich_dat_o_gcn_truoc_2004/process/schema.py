"""Compact schema cho "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận
trước ngày 01 tháng 7 năm 2004" (1.012817) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io).

Field-key data[...] Y HỆT dang_ky_dat_dai_lan_dau_da_nang (khối "Thông tin chung" 2 vai + panel "Địa chỉ
thửa đất/ địa chỉ xây dựng"). Nguồn theo "Mapping_XacDinhLaiDienTichDatO_DVC_DaNang.xlsx":
- Đơn đăng ký biến động đất đai (giấy là Mẫu số 25, cổng ghi Mẫu số 18): chủ hồ sơ (mục 1.a-e), nội dung
  biến động (mục 2), giấy tờ nộp kèm (mục 3).
- Bản mô tả ranh giới, mốc giới thửa đất (Phụ lục 11): người sử dụng đất + địa chỉ thửa.
- Công văn của Chi nhánh VPĐKĐĐ chuyển trả hồ sơ / Phiếu đo đạc chỉnh lý: số thửa, tờ bản đồ MỚI.
- Giấy chứng nhận đã cấp (trước 01/7/2004): thửa/tờ CŨ, chỉ dùng khi không có số liệu đo mới.
- CCCD (nếu có): nhân thân người nộp. Bộ hồ sơ mẫu KHÔNG kèm CCCD → ngày sinh/ngày cấp có thể thiếu.

Phần I: ChuHoSo_* = người đứng tên Đơn (người sử dụng đất); NguoiNop_* = người nộp (mặc định tự nộp).
Phần II: ThuaDat_* = thửa đất đề nghị xác định lại diện tích đất ở — KHÔNG phải địa chỉ của người.
"""

# --- Chủ hồ sơ (người đứng tên Đơn đăng ký biến động) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Cá nhân" nếu chủ hồ sơ là một người/hộ gia đình (gần như luôn '
        'vậy — thủ tục dành cho hộ gia đình, cá nhân); "Tổ chức" chỉ khi Đơn ghi tên công ty/cơ quan.'},
    {"name": "ChuHoSo_HoTen", "desc": "Họ và tên CHỦ HỒ SƠ, IN HOA — người đứng tên mục '1. Người sử dụng "
        "đất…' / 'a) Tên' của Đơn đăng ký biến động (cũng là 'Người viết đơn'). Đối chiếu CCCD, Bản mô tả "
        "ranh giới ('…tại thực địa của (ông, bà, đơn vị)'). ⚠ Giấy chứng nhận cấp trước 2004 có thể ghi tên "
        "chủ CŨ / 'Hộ ông …' — KHÔNG lấy theo GCN khi Đơn ghi khác. Nhiều người cùng sử dụng đất thì lấy "
        "người ĐỨNG ĐƠN, những người còn lại đưa vào NguoiCungSuDung."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN mục "
        "'c) Địa chỉ' của Đơn đăng ký biến động (người dân tự ghi, theo đơn vị hành chính hiện hành); thiếu "
        "mới lấy 'Nơi thường trú' trên CCCD. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/tổ/thôn "
        "(KHÔNG kèm phường/tỉnh). Viết tắt 'TP Đà Nẵng' → 'Thành phố Đà Nẵng'. KHÔNG lấy địa chỉ thửa đất."},
    {"name": "NguoiCungSuDung", "desc": "Danh sách họ tên NHỮNG NGƯỜI KHÁC cùng sử dụng thửa đất (ngoài chủ "
        "hồ sơ) nếu giấy tờ nêu rõ — vd công văn của cơ quan đăng ký đất đai kính gửi 'Ông A, bà B, ông "
        "C…'. Mảng chuỗi. KHÔNG kể người liền kề ký bản mô tả ranh giới, người chuyển nhượng/nhận tặng cho "
        "trước đây, cán bộ đo đạc. Không có thì bỏ."},
]

# --- Nội dung yêu cầu + ghi chú ---
FIELDS += [
    {"name": "NoiDungYeuCau", "desc": "Nội dung yêu cầu giải quyết — CHÉP NGUYÊN VĂN mục '2. Nội dung biến "
        "động' của Đơn đăng ký biến động (vd 'Xác định lại diện tích đất ở'). Chữ viết tay sai chính tả rõ "
        "ràng ('Xát định lại diện tít') thì sửa lại cho đúng tiếng Việt, KHÔNG thêm ý. Bỏ dấu chấm chấm "
        "(.....). Đơn trống mục này thì bỏ."},
    {"name": "VanBanCoQuan", "desc": "Văn bản của CƠ QUAN đăng ký đất đai liên quan tới hồ sơ (công văn "
        "chuyển trả/hướng dẫn nộp hồ sơ, thông báo…), ghi gọn MỘT câu dạng 'Công văn số {số/ký hiệu} ngày "
        "{dd/mm/yyyy} của {cơ quan ban hành}' (vd 'Công văn số 1234/CNKV-KTĐC ngày 15/3/2026 của Chi nhánh "
        "Văn phòng Đăng ký đất đai Khu vực II'). Không có văn bản nào như vậy thì bỏ."},
    {"name": "GiayToTrongHoSo", "desc": "Danh sách CÁC GIẤY TỜ đọc được trong hồ sơ, theo thứ tự xuất hiện, "
        "mỗi phần tử một câu ngắn có số/ngày nếu có: vd 'Đơn đăng ký biến động đất đai, tài sản gắn liền với "
        "đất (Mẫu số 25) ký ngày 05/3/2026', 'Bản mô tả ranh giới, mốc giới thửa đất lập ngày 10/01/2026', "
        "'Giấy chứng nhận quyền sử dụng đất số A 123456 cấp ngày 20/5/1998'. Bỏ trang trắng, KHÔNG liệt kê "
        "CCCD. Mảng chuỗi."},
]

# --- Phần II: thửa đất đề nghị xác định lại diện tích đất ở ---
FIELDS += [
    {"name": "ThuaDat_DiaChi", "desc": "Địa chỉ THỬA ĐẤT, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN văn bản "
        "của cơ quan đăng ký đất đai ('…đối với thửa đất tại địa chỉ…') và Đơn; Bản mô tả ranh giới ('đang "
        "sử dụng đất tại') dùng đối chiếu; GCN cũ ghi địa danh trước sáp nhập chỉ dùng khi không còn nguồn "
        "nào. Hai nguồn lệch nhau (vd tổ dân phố khác số) → theo nguồn khớp với Đơn. diaChi=tổ/thôn/số nhà, "
        "xa=phường/xã hiện hành, tinh='Tỉnh/Thành phố …'."},
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất. ƯU TIÊN số liệu ĐO ĐẠC MỚI (Phiếu đo đạc chỉnh lý, văn "
        "bản của cơ quan đăng ký đất đai 'hiện nay … đang sử dụng thửa đất số …'); thiếu mới lấy 'thửa đất "
        "số' trên GCN đã cấp. Nhiều thửa → liệt kê cách nhau dấu phẩy (vd '101, 102'). Chỉ số, không kèm "
        "chữ 'thửa đất số'."},
    {"name": "ThuaDat_SoTo", "desc": "Số tờ bản đồ, CÙNG nguồn với ThuaDat_SoThua (đo mới trước, GCN cũ "
        "sau). Các thửa cùng một tờ thì ghi số tờ MỘT lần. Chỉ số."},
]

# --- Người nộp hồ sơ ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Cá nhân" (đa số) hoặc "Tổ chức".'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ, IN HOA. Có văn bản ủy quyền/đại diện → "
        "người ĐƯỢC ủy quyền. Không có (tự nộp) → CHÍNH LÀ chủ hồ sơ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD hoặc văn bản ủy quyền. Chỉ "
        "có NĂM sinh (hoặc phải suy từ số định danh) thì BỎ, không tự bịa ngày/tháng."},
    {"name": "NguoiNop_GioiTinh", "desc": '"Nam"/"Nữ" — CCCD; hoặc danh xưng Ông/Bà gắn với ĐÚNG người nộp '
        '(vd công văn kính gửi "Ông …").'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân NGƯỜI NỘP — CCCD, hoặc mục 'b) Giấy "
        "tờ nhân thân' của Đơn ('CCCD 0xx…'). Chỉ chữ số, ưu tiên 12 số; CMND 9 số trên GCN cũ chỉ để đối "
        "chiếu."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế NGƯỜI NỘP — CHỈ khi là tổ chức. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD. Đơn Mẫu 25 "
        "không có ô này; không có CCCD thì bỏ."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP, ghi ĐẦY ĐỦ: CCCD gắn chip → "Cục Cảnh '
        'sát quản lý hành chính về trật tự xã hội"; thẻ căn cước mới → "Bộ Công an". Không có CCCD thì bỏ.'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Tự nộp → GIỐNG "
        "ChuHoSo_DiaChi. Người được ủy quyền → địa chỉ của chính người đó trên văn bản ủy quyền/CCCD; không "
        "có thì bỏ. KHÔNG lấy địa chỉ thửa đất."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại — mục 'e) Điện thoại liên hệ' của Đơn, hoặc dòng "
        "'Số ĐT liên hệ' trong công văn. Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email — mục 'Hộp thư điện tử' của Đơn nếu có ghi; thường trống → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ThuaDat_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key theo cột H của file mapping.
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",   # textarea.
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",            # Cá nhân/Tổ chức.
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",                # nhãn "Phường/Xã" (mô hình 2 cấp).
    "data[address]": "dom-input",
    # Panel "Địa chỉ thửa đất/ địa chỉ xây dựng".
    "data[diaChiThuaDat]": "dom-input",            # textarea.
    "data[SoToBanDo]": "dom-input",
    "data[SoThuaDat]": "dom-input",
    "data[province2]": "dom-select",
    "data[nation2]": "dom-select",
    "data[district2]": "dom-select",
}
