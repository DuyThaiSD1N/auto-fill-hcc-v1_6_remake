"""Catalog thành phần hồ sơ 1.115679 (Lào Cai — phường/xã) — bảng "Thành phần hồ sơ" bước 3.

Bảng in MỘT LẦN toàn bộ dòng của cả bốn trường hợp, chia nhóm bằng dòng tiêu đề CHỮ CÁI (khác 1.115651 dùng
"(1)…(4)"):
  a) Hồ sơ đề nghị chuyển mục đích sử dụng đất gồm:        — Đơn Mẫu số 02 + dòng "khoản 21 Điều 3…"
  b) Hồ sơ đề nghị chuyển hình thức sử dụng đất gồm:       — Đơn Mẫu số 03 + GCN + quyết định
  c) Hồ sơ đề nghị gia hạn sử dụng đất … gồm:              — Đơn Mẫu số 17 + GCN + quyết định + VB gia hạn
  d) Hồ sơ đề nghị điều chỉnh thời hạn … dự án đầu tư gồm: — VB thay đổi thời hạn + GCN + quyết định
Dưới bảng là khối "Thông tin khác" với ô "Về việc" (*), "Ghi chú" và danh sách "Giấy tờ khác" (chọn "Mới" →
gõ tên → chọn tệp). Giấy tờ không có dòng riêng đi hết xuống đó.

ĐÍNH VÀO DÒNG NÀO — theo ẢNH ÁNH XẠ ĐÍNH KÈM của hồ sơ mẫu (bộ phận một cửa hướng dẫn):
  Đơn Mẫu số 02            → dòng "Đơn theo Mẫu số 02…" của nhóm a)
  Giấy chứng nhận QSDĐ     → dòng "Một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, …" ở
                             CUỐI BẢNG (nhóm d), KHÔNG phải dòng "khoản 21 Điều 3…" của nhóm a)
  Quyết định giao đất/…    → dòng "Quyết định giao đất, cho thuê đất, …" ở CUỐI BẢNG (nhóm d)
Ảnh hướng dẫn ghi rõ mỗi giấy tờ chỉ tải ở MỘT dòng; lần nộp trước có cán bộ tải GCN vào dòng nhóm a) nên nếu
nơi tiếp nhận yêu cầu khác thì sửa ROUTES ở đây, không sửa rải rác nơi khác.

VÌ SAO PHẢI KHAI sectionHeader: content.js chỉ dùng slotKeywords do BE gửi khi item có sectionHeader; không
có thì nó tra bảng FIXED_SLOT_KEYWORDS cứng trong extension và thủ tục mới không khớp được dòng nào (phải
phát hành lại extension). Hai mức neo:
  HEADER_BANG  = dòng TIÊU ĐỀ CỘT ("Tên giấy tờ") → FE quét TOÀN BỘ dòng của bảng. Dùng cho các dòng có từ
                 khóa duy nhất trong cả bảng (Đơn Mẫu 02/03/17, văn bản gia hạn dự án).
  HEADER_NHOM_D = dòng tiêu đề nhóm d) → FE chỉ quét các dòng SAU nó, tức ba dòng cuối bảng. Bắt buộc cho
                 GCN và quyết định giao đất: cả bốn nhóm đều có một dòng "giấy chứng nhận" và một dòng
                 "quyết định giao đất…" gần như trùng câu chữ, khoanh vùng theo nhóm mới chắc đúng dòng.
                 Nhóm d) là nhóm CUỐI nên không cần content.js biết tiêu đề nhóm dạng "a)…d)" để cắt vùng.

tickRow=True: mỗi dòng có checkbox ở cột "#" phải tích thì cổng mới nhận tệp (iCheck — FE click lớp phủ).
slotKey theo DÒNG để nhiều tệp cùng dòng được FE gom vào một lần chọn tệp.
"""

ROW_DON_02 = 1
ROW_DON_03 = 2
ROW_DON_17 = 3
ROW_VB_GIA_HAN = 4
ROW_VB_THAY_DOI = 5
ROW_GCN = 6
ROW_QUYET_DINH = 7

# Cổng in tiêu đề cột "# | Tên giấy tờ | Số bản (*) | Tệp tin | Mẫu đơn | Ký số tệp tin".
HEADER_BANG = "ten giay to"
HEADER_NHOM_D = "d) ho so de nghi dieu chinh thoi han su dung dat cua du an dau tu"

# vị trí dòng → (từ khóa dòng đã fold, tiêu đề neo vùng, tên dòng rút gọn)
ROWS: dict[int, tuple[list[str], str, str]] = {
    ROW_DON_02: (["don theo mau so 02"], HEADER_BANG,
                 "Đơn theo Mẫu số 02 (chuyển mục đích sử dụng đất)"),
    ROW_DON_03: (["don theo mau so 03"], HEADER_BANG,
                 "Đơn theo Mẫu số 03 (chuyển hình thức sử dụng đất)"),
    ROW_DON_17: (["don theo mau so 17"], HEADER_BANG,
                 "Đơn theo Mẫu số 17 (gia hạn sử dụng đất)"),
    # Nhóm c) là chỗ duy nhất nói "cho phép GIA HẠN thời hạn hoạt động"; nhóm d) nói "THAY ĐỔI".
    ROW_VB_GIA_HAN: (["cho phep gia han thoi han hoat dong"], HEADER_BANG,
                     "Văn bản cho phép gia hạn thời hạn hoạt động của dự án đầu tư"),
    ROW_VB_THAY_DOI: (["thay doi thoi han hoat dong"], HEADER_NHOM_D,
                      "Văn bản cho phép thay đổi thời hạn hoạt động của dự án đầu tư"),
    # Trong vùng nhóm d) chỉ có ĐÚNG MỘT dòng "Một trong các giấy chứng nhận…" và MỘT dòng "Quyết định giao
    # đất…" nên từ khóa để ngắn cho chắc, không phụ thuộc dấu phẩy của cổng.
    ROW_GCN: (["mot trong cac giay chung nhan"], HEADER_NHOM_D,
              "Một trong các giấy chứng nhận (GCN quyền sử dụng đất, quyền sở hữu nhà ở…)"),
    ROW_QUYET_DINH: (["quyet dinh giao dat"], HEADER_NHOM_D,
                     "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất"),
}

# label → vị trí dòng; label không có ở đây → "Giấy tờ khác".
ROUTES: dict[str, int] = {
    "don_mau_02": ROW_DON_02,
    "don_mau_03": ROW_DON_03,
    "don_mau_17": ROW_DON_17,
    "vb_gia_han_du_an": ROW_VB_GIA_HAN,
    "vb_thay_doi_thoi_han_du_an": ROW_VB_THAY_DOI,
    "gcn": ROW_GCN,
    "quyet_dinh_giao_dat": ROW_QUYET_DINH,
}

# (label, tên hiển thị mặc định, mô tả cho LLM)
LABELS: list[tuple[str, str, str]] = [
    ("don_mau_02", "Đơn đề nghị chuyển mục đích sử dụng đất",
     "ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT — tiêu đề ghi 'Mẫu số 02', có mục '1. Người đề nghị chuyển mục "
     "đích sử dụng đất', '4. Thông tin thửa đất/khu đất', '5. Nội dung đề nghị chuyển mục đích sử dụng đất', "
     "ký 'Người làm đơn'"),
    ("don_mau_03", "Đơn đề nghị chuyển hình thức sử dụng đất",
     "ĐƠN ĐỀ NGHỊ CHUYỂN HÌNH THỨC SỬ DỤNG ĐẤT (Mẫu số 03) — vd từ thuê đất trả tiền hằng năm sang trả tiền "
     "một lần cho cả thời gian thuê"),
    ("don_mau_17", "Đơn đề nghị gia hạn sử dụng đất",
     "ĐƠN ĐỀ NGHỊ GIA HẠN SỬ DỤNG ĐẤT khi hết thời hạn sử dụng đất (Mẫu số 17)"),
    ("gcn", "Giấy chứng nhận quyền sử dụng đất",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất / quyền sở hữu nhà ở và tài sản khác gắn liền với đất (sổ đỏ, sổ "
     "hồng) — trang bìa in 'GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT', có 'I. Người sử dụng đất', 'II. Thửa đất, "
     "nhà ở…', số phát hành dạng 'CM 832513', 'Số vào sổ cấp GCN'; hoặc giấy tờ về quyền sử dụng đất theo "
     "Điều 137 Luật Đất đai. KHÔNG phải Giấy chứng nhận ĐĂNG KÝ DOANH NGHIỆP"),
    ("quyet_dinh_giao_dat", "Quyết định cho phép chuyển mục đích sử dụng đất",
     "QUYẾT ĐỊNH của UBND về việc GIAO ĐẤT, CHO THUÊ ĐẤT hoặc CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT và quyết "
     "định ĐIỀU CHỈNH các quyết định đó — số hiệu dạng '…/QĐ-UBND', có 'Điều 1. Cho phép chuyển mục đích sử "
     "dụng đất…', thường kèm danh sách các hộ và bản đồ"),
    ("vb_gia_han_du_an", "Văn bản cho phép gia hạn thời hạn hoạt động của dự án đầu tư",
     "Văn bản của cơ quan có thẩm quyền cho phép GIA HẠN thời gian hoạt động của dự án đầu tư, hoặc giấy tờ "
     "thể hiện thời hạn hoạt động dự án (quyết định chủ trương đầu tư, giấy chứng nhận đăng ký đầu tư)"),
    ("vb_thay_doi_thoi_han_du_an", "Văn bản cho phép thay đổi thời hạn hoạt động của dự án đầu tư",
     "Văn bản của cơ quan có thẩm quyền cho phép THAY ĐỔI (điều chỉnh) thời hạn hoạt động của dự án đầu tư "
     "theo pháp luật về đầu tư"),
    ("ho_so_nghia_vu_tai_chinh", "Hồ sơ nghĩa vụ tài chính về đất đai",
     "PHIẾU CHUYỂN THÔNG TIN để xác định nghĩa vụ tài chính về đất đai, THÔNG BÁO NỘP TIỀN SỬ DỤNG ĐẤT, "
     "THÔNG BÁO NỘP LỆ PHÍ TRƯỚC BẠ nhà đất, GIẤY NỘP TIỀN VÀO NGÂN SÁCH NHÀ NƯỚC, biên lai, chứng từ "
     "miễn/giảm nghĩa vụ tài chính — số hiệu dạng '…/TB-CCT', '…/TB', 'Mẫu số C1-02/NS'"),
    ("ho_so_do_dac", "Hồ sơ đo đạc thửa đất",
     "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT, PHIẾU XÁC NHẬN KẾT QUẢ ĐO ĐẠC HIỆN TRẠNG THỬA ĐẤT, biên bản kiểm tra "
     "chất lượng sản phẩm đo đạc, phiếu ghi ý kiến kiểm tra, sơ đồ/trích lục bản đồ địa chính, sơ đồ lô đất "
     "— có sơ đồ thửa, bảng toạ độ đỉnh thửa VN-2000, số thửa, số tờ bản đồ, diện tích"),
    ("vb_uy_quyen", "Giấy uỷ quyền",
     "GIẤY UỶ QUYỀN/HỢP ĐỒNG UỶ QUYỀN hoặc văn bản cử người đi nộp hồ sơ — có 'Bên uỷ quyền', 'Bên được uỷ "
     "quyền', 'LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN', số công chứng dạng '488/2026/CCGD'"),
    ("gcn_dkdn", "Giấy chứng nhận đăng ký doanh nghiệp",
     "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP, quyết định thành lập tổ chức, giấy tờ xác lập tư cách pháp nhân "
     "của chủ hồ sơ"),
    ("tb_ket_qua_tthc", "Thông báo kết quả giải quyết thủ tục hành chính",
     "THÔNG BÁO KẾT QUẢ GIẢI QUYẾT THỦ TỤC HÀNH CHÍNH, thông báo trả hồ sơ/rút hồ sơ, phiếu hẹn trả kết quả "
     "của Bộ phận Một cửa"),
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu kèm theo", "Giấy tờ khác hoặc không xác định được loại"),
]

# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED_LABELS = {"cccd"}

# Đơn nào cũng chỉ có MỘT dòng trong bảng; thiếu hẳn đơn thì cổng không nhận hồ sơ.
DON_LABELS = ("don_mau_02", "don_mau_03", "don_mau_17")

_DISPLAY = {label: name for label, name, _ in LABELS}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_for(label: str) -> int | None:
    return ROUTES.get(label)


def slot(position: int) -> dict:
    keywords, header, name = ROWS[position]
    return {
        "slotKey": f"lc_115679_{position}",
        "slotName": f"{position}. {name}",
        "sectionHeader": header,
        "slotKeywords": list(keywords),
    }


def row_name(position: int) -> str:
    return ROWS[position][2]


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in LABELS)
