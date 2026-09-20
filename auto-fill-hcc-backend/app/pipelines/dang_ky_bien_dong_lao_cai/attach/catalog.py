"""Catalog thành phần hồ sơ 1.115671 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng chia 5 NHÓM theo đúng 5 trường hợp trong tên thủ tục; nhóm chọn theo VĂN BẢN CĂN CỨ có trong hồ sơ:
  (1) Thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng  → 6 dòng.
  (2) QSDĐ xây dựng công trình trên mặt đất phục vụ công trình ngầm   → 6 dòng.
  (3) Bán tài sản, điều chuyển, chuyển nhượng QSDĐ là tài sản công    → 6 dòng (có "Hợp đồng mua bán tài sản
      công", KHÔNG có dòng "Mảnh trích đo").
  (4) Kết quả giải quyết tranh chấp / bản án / quyết định thi hành án / phán quyết Trọng tài → 6 dòng.
  (5) Xử lý tài sản thế chấp, kể cả xử lý nợ xấu của tổ chức tín dụng → 6 dòng.
Bên dưới còn khối "Thông tin khác" với danh sách "Giấy tờ khác" (tên tự nhập + tệp).

KHÁC 1.115651/1.115667: nhóm (1) KHÔNG có dòng tiêu đề riêng — cổng chỉ in tiêu đề từ "(2)" trở đi, 6 dòng của
nhóm (1) nằm ngay sau dòng tiêu đề CỘT của bảng. Vì vậy sectionHeader của nhóm (1) trỏ vào chính dòng tiêu đề
cột ("Tên giấy tờ"): FE lấy các dòng NẰM SAU nó cho tới tiêu đề nhóm kế tiếp, tức đúng 6 dòng của nhóm (1).

FE khoanh vùng dòng theo tiêu đề nhóm (sectionHeader) rồi khớp từ khóa đã fold (slotKeywords); từ khóa chọn sao
cho trong CÙNG nhóm chỉ khớp đúng một dòng — các dòng "Đơn", "Giấy chứng nhận đã cấp", "Bản vẽ tách thửa",
"Mảnh trích đo", "Văn bản về việc đại diện" lặp y hệt ở cả 5 nhóm nên chỉ có khoanh vùng mới phân biệt được.
slotKey theo DÒNG để nhiều tệp cùng dòng được FE gom vào một lần chọn tệp (hồ sơ thật hay có 3-4 file cùng đính
vào dòng "Giấy chứng nhận đã cấp" hoặc dòng văn bản căn cứ). Giấy tờ không có dòng trong nhóm → "Giấy tờ khác".
"""

GROUP_1 = "1"
GROUP_2 = "2"
GROUP_3 = "3"
GROUP_4 = "4"
GROUP_5 = "5"

GROUPS = (GROUP_1, GROUP_2, GROUP_3, GROUP_4, GROUP_5)

SECTION_HEADERS = {
    # Nhóm (1) không có dòng tiêu đề → neo vào dòng tiêu đề cột của bảng (xem docstring).
    GROUP_1: "ten giay to",
    GROUP_2: "(2) doi voi truong hop thay doi quyen su dung dat xay dung cong trinh tren mat dat",
    GROUP_3: "(3) doi voi truong hop ban tai san, dieu chuyen, chuyen nhuong quyen su dung dat la tai san cong",
    GROUP_4: "(4) doi voi truong hop nhan quyen su dung dat, quyen so huu tai san gan lien voi dat theo ket qua "
             "giai quyet tranh chap",
    GROUP_5: "(5) doi voi truong hop nhan quyen su dung dat, quyen so huu tai san gan lien voi dat do xu ly tai "
             "san the chap",
}

# (nhóm, vị trí) → (từ khóa dòng đã fold, tên dòng rút gọn).
# Từ khóa phải KHÔNG khớp chính dòng tiêu đề của nhóm (FE quét từ dòng SAU tiêu đề nên an toàn) và không khớp
# dòng khác trong cùng nhóm.
_ROW_DON = (["don dang ky bien dong dat dai"], "Đơn đăng ký biến động đất đai (Mẫu số 24)")
_ROW_GCN = (["giay chung nhan da cap"], "Giấy chứng nhận đã cấp")
_ROW_BAN_VE = (["ban ve tach thua dat"], "Bản vẽ tách thửa, hợp thửa (Mẫu số 28)")
_ROW_TRICH_DO = (["manh trich do ban do dia chinh"], "Mảnh trích đo bản đồ địa chính")
_ROW_DAI_DIEN = (["van ban ve viec dai dien"], "Văn bản về việc đại diện")

ROWS: dict[tuple[str, int], tuple[list[str], str]] = {
    (GROUP_1, 1): _ROW_DON,
    (GROUP_1, 2): _ROW_GCN,
    (GROUP_1, 3): (["van ban thoa thuan ve viec thay doi quyen su dung dat"],
                   "Văn bản thỏa thuận của thành viên hộ gia đình/vợ chồng"),
    (GROUP_1, 4): _ROW_BAN_VE,
    (GROUP_1, 5): _ROW_TRICH_DO,
    (GROUP_1, 6): _ROW_DAI_DIEN,
    (GROUP_2, 1): _ROW_DON,
    (GROUP_2, 2): _ROW_GCN,
    (GROUP_2, 3): (["van ban ve viec cho phep thay doi quyen su dung dat"],
                   "Văn bản cho phép thay đổi QSDĐ xây dựng công trình trên mặt đất"),
    (GROUP_2, 4): _ROW_BAN_VE,
    (GROUP_2, 5): _ROW_TRICH_DO,
    (GROUP_2, 6): _ROW_DAI_DIEN,
    (GROUP_3, 1): _ROW_DON,
    (GROUP_3, 2): _ROW_GCN,
    # Từ khóa cố ý KHÔNG có dấu phẩy: tiêu đề nhóm (3) cũng có cụm "bán tài sản, điều chuyển", chỉ cụm mở đầu
    # "văn bản cho phép bán tài sản" mới tách được dòng khỏi tiêu đề.
    (GROUP_3, 3): (["van ban cho phep ban tai san"],
                   "Văn bản cho phép bán tài sản, điều chuyển, chuyển nhượng QSDĐ"),
    (GROUP_3, 4): (["hop dong mua ban tai san cong"], "Hợp đồng mua bán tài sản công"),
    (GROUP_3, 5): _ROW_BAN_VE,
    # Nhóm (3) không có dòng "Mảnh trích đo" — vị trí 6 là "Văn bản về việc đại diện".
    (GROUP_3, 6): _ROW_DAI_DIEN,
    (GROUP_4, 1): _ROW_DON,
    (GROUP_4, 2): _ROW_GCN,
    (GROUP_4, 3): (["bien ban hoa giai thanh"], "Bản án/quyết định/biên bản hòa giải thành"),
    (GROUP_4, 4): _ROW_BAN_VE,
    (GROUP_4, 5): _ROW_TRICH_DO,
    (GROUP_4, 6): _ROW_DAI_DIEN,
    (GROUP_5, 1): _ROW_DON,
    (GROUP_5, 2): _ROW_GCN,
    (GROUP_5, 3): (["hop dong the chap quyen su dung dat"], "Hợp đồng xử lý tài sản thế chấp"),
    (GROUP_5, 4): _ROW_BAN_VE,
    (GROUP_5, 5): _ROW_TRICH_DO,
    (GROUP_5, 6): _ROW_DAI_DIEN,
}

# Nhãn văn bản CĂN CỨ → nhóm hồ sơ. Đây là thứ duy nhất phân biệt được 5 nhóm: Đơn/GCN/bản vẽ/trích đo/ủy quyền
# có mặt ở mọi nhóm nên không nói lên gì.
CAN_CU_GROUP = {
    "vb_thoa_thuan_ho_gia_dinh": GROUP_1,
    "vb_cho_phep_cong_trinh_ngam": GROUP_2,
    "vb_cho_phep_tai_san_cong": GROUP_3,
    "hop_dong_mua_ban_tai_san_cong": GROUP_3,
    "vb_giai_quyet_tranh_chap": GROUP_4,
    "hop_dong_xu_ly_the_chap": GROUP_5,
}

# label → {nhóm: vị trí dòng}; nhóm không có dòng cho nhãn → "Giấy tờ khác".
ROUTES: dict[str, dict[str, int]] = {
    "don_dang_ky": {GROUP_1: 1, GROUP_2: 1, GROUP_3: 1, GROUP_4: 1, GROUP_5: 1},
    "gcn": {GROUP_1: 2, GROUP_2: 2, GROUP_3: 2, GROUP_4: 2, GROUP_5: 2},
    # Quyết định giao đất/cấp GCN là căn cứ của chính Giấy chứng nhận đã cấp (Đơn mục 3 liệt kê chung một gạch
    # đầu dòng với số vào sổ cấp GCN) → đính cùng dòng "Giấy chứng nhận đã cấp".
    "qd_giao_dat_cap_gcn": {GROUP_1: 2, GROUP_2: 2, GROUP_3: 2, GROUP_4: 2, GROUP_5: 2},
    "vb_thoa_thuan_ho_gia_dinh": {GROUP_1: 3},
    "vb_cho_phep_cong_trinh_ngam": {GROUP_2: 3},
    "vb_cho_phep_tai_san_cong": {GROUP_3: 3},
    "hop_dong_mua_ban_tai_san_cong": {GROUP_3: 4},
    "vb_giai_quyet_tranh_chap": {GROUP_4: 3},
    "hop_dong_xu_ly_the_chap": {GROUP_5: 3},
    "ban_ve_tach_hop_thua": {GROUP_1: 4, GROUP_2: 4, GROUP_3: 5, GROUP_4: 4, GROUP_5: 4},
    "manh_trich_do": {GROUP_1: 5, GROUP_2: 5, GROUP_4: 5, GROUP_5: 5},
    "vb_dai_dien": {GROUP_1: 6, GROUP_2: 6, GROUP_3: 6, GROUP_4: 6, GROUP_5: 6},
    # GCN đăng ký doanh nghiệp/quyết định thành lập là giấy chứng minh tư cách người đại diện → cùng dòng đó.
    "vb_tu_cach_phap_nhan": {GROUP_1: 6, GROUP_2: 6, GROUP_3: 6, GROUP_4: 6, GROUP_5: 6},
}

# (label, tên hiển thị mặc định, mô tả cho LLM)
LABELS: list[tuple[str, str, str]] = [
    ("don_dang_ky", "Đơn đăng ký biến động đất đai",
     "ĐƠN đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24) — có mục 'Nội dung biến động'"),
    ("gcn", "Giấy chứng nhận quyền sử dụng đất",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất/quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ/sổ hồng) có số "
     "phát hành, số vào sổ, thửa đất, tờ bản đồ, sơ đồ thửa đất — KHÔNG phải GCN đăng ký doanh nghiệp"),
    ("qd_giao_dat_cap_gcn", "Quyết định giao đất, cấp Giấy chứng nhận",
     "QUYẾT ĐỊNH của UBND về GIAO ĐẤT/cho thuê đất/cấp Giấy chứng nhận — chính là căn cứ cấp Giấy chứng nhận "
     "đang có trong hồ sơ (cùng số vào sổ, cùng thửa đất)"),
    ("vb_thoa_thuan_ho_gia_dinh", "Văn bản thỏa thuận của hộ gia đình, vợ chồng",
     "VĂN BẢN THỎA THUẬN về việc thay đổi quyền sử dụng đất, quyền sở hữu tài sản giữa CÁC THÀNH VIÊN HỘ GIA "
     "ĐÌNH hoặc giữa VỢ VÀ CHỒNG (kèm giấy chứng nhận kết hôn/ly hôn nếu có trong cùng file)"),
    ("vb_cho_phep_cong_trinh_ngam", "Văn bản cho phép thay đổi QSDĐ công trình ngầm",
     "VĂN BẢN của cơ quan, người có thẩm quyền CHO PHÉP thay đổi quyền sử dụng đất xây dựng CÔNG TRÌNH TRÊN MẶT "
     "ĐẤT phục vụ vận hành, khai thác CÔNG TRÌNH NGẦM, quyền sở hữu công trình ngầm"),
    ("vb_cho_phep_tai_san_cong", "Văn bản cho phép điều chuyển tài sản công",
     "VĂN BẢN/QUYẾT ĐỊNH của cơ quan có thẩm quyền cho phép BÁN TÀI SẢN, ĐIỀU CHUYỂN, chuyển nhượng quyền sử "
     "dụng đất là TÀI SẢN CÔNG; kể cả thông báo phương án sắp xếp/bố trí lại trụ sở, BIÊN BẢN BÀN GIAO TIẾP "
     "NHẬN TÀI SẢN CÔNG, quyết định/quy định về tổ chức bộ máy làm căn cứ tiếp nhận trụ sở"),
    ("hop_dong_mua_ban_tai_san_cong", "Hợp đồng mua bán tài sản công",
     "HỢP ĐỒNG MUA BÁN tài sản công là quyền sử dụng đất, tài sản gắn liền với đất (trường hợp BÁN tài sản, "
     "chuyển nhượng quyền sử dụng đất là tài sản công)"),
    ("vb_giai_quyet_tranh_chap", "Bản án, quyết định giải quyết tranh chấp",
     "BIÊN BẢN HÒA GIẢI THÀNH, văn bản công nhận kết quả hòa giải; QUYẾT ĐỊNH giải quyết TRANH CHẤP, KHIẾU NẠI, "
     "TỐ CÁO về đất đai; BẢN ÁN/quyết định của TÒA ÁN; quyết định THI HÀNH ÁN; phán quyết của TRỌNG TÀI THƯƠNG MẠI"),
    ("hop_dong_xu_ly_the_chap", "Hợp đồng xử lý tài sản thế chấp",
     "HỢP ĐỒNG THẾ CHẤP quyền sử dụng đất; hợp đồng chuyển nhượng/chuyển giao quyền sử dụng đất do XỬ LÝ TÀI "
     "SẢN THẾ CHẤP, xử lý nợ xấu của tổ chức tín dụng; hợp đồng MUA BÁN TÀI SẢN ĐẤU GIÁ quyền sử dụng đất; văn "
     "bản xác nhận kết quả thi hành án của cơ quan thi hành án dân sự"),
    ("ban_ve_tach_hop_thua", "Bản vẽ tách thửa, hợp thửa",
     "Bản vẽ TÁCH THỬA đất, HỢP THỬA đất (Mẫu số 28)"),
    ("manh_trich_do", "Mảnh trích đo bản đồ địa chính",
     "MẢNH TRÍCH ĐO bản đồ địa chính thửa đất / phiếu đo đạc xác định lại kích thước, diện tích thửa đất"),
    ("vb_dai_dien", "Giấy ủy quyền",
     "GIẤY ỦY QUYỀN/hợp đồng ủy quyền/văn bản cử người đại diện đi làm thủ tục đăng ký đất đai"),
    ("vb_tu_cach_phap_nhan", "Giấy tờ về tư cách pháp nhân",
     "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP (mã số doanh nghiệp, người đại diện theo pháp luật) hoặc quyết "
     "định/quy định về chức năng, nhiệm vụ, tổ chức bộ máy xác lập tư cách pháp nhân của tổ chức làm hồ sơ"),
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu kèm theo", "Giấy tờ khác (hóa đơn, tờ khai thuế, biên lai…) hoặc không xác định được loại"),
]

# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED_LABELS = {"cccd"}

_DISPLAY = {label: name for label, name, _ in LABELS}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_for(label: str, group: str) -> tuple[str, int] | None:
    position = ROUTES.get(label, {}).get(group)
    return (group, position) if position else None


def slot(row: tuple[str, int]) -> dict:
    group, position = row
    keywords, name = ROWS[row]
    return {
        "slotKey": f"lc_115671_{group}_{position}",
        "slotName": f"({group})-{position}. {name}",
        "sectionHeader": SECTION_HEADERS[group],
        "slotKeywords": list(keywords),
    }


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in LABELS)
