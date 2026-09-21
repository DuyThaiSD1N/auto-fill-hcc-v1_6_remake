"""Catalog thành phần hồ sơ 1.115688 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng PHẲNG, không chia nhóm (không có dòng "a) Đối với trường hợp…"), gồm các dòng cố định của thủ tục đăng
ký đất đai, cấp Giấy chứng nhận LẦN ĐẦU. Bên dưới bảng là khối "Thành phần hồ sơ khác nếu có" với danh sách
"Giấy tờ khác" (chọn "Mới" → gõ tên → chọn tệp). Giấy tờ không có dòng riêng đi hết xuống đó.

VÌ SAO VẪN KHAI sectionHeader DÙ BẢNG KHÔNG CÓ NHÓM: content.js chỉ dùng slotKeywords do BE gửi khi item có
sectionHeader; không có thì nó tra bảng FIXED_SLOT_KEYWORDS cứng trong extension và thủ tục mới sẽ không khớp
được dòng nào (phải phát hành lại extension). Neo vào chính DÒNG TIÊU ĐỀ CỘT của bảng ("Tên giấy tờ") — FE lấy
mọi dòng NẰM SAU nó, tức toàn bộ dòng của bảng. Cùng cách làm với 1.115687.

KHỚP THEO TỪ KHÓA, KHÔNG THEO SỐ THỨ TỰ: cổng render danh sách dòng khác nhau giữa các biến thể (ảnh hướng dẫn
hồ sơ cá nhân HS03 có dòng "Điều 137…" / "nhận thừa kế" / "Báo cáo rà soát Mẫu 21d"; ảnh cổng thật của hồ sơ
tổ chức HS01 lại có thêm dòng "Quyết định vị trí đóng quân…"). Vị trí trong ROWS chỉ để sinh slotKey và nhãn
hiển thị; dòng nào không render trên trang thì FE báo "không tìm thấy ô đính kèm" đúng cho tệp đó, chứ không
đính nhầm sang dòng khác.

tickRow=True: mỗi dòng có ô checkbox ở cột "#" phải tích thì cổng mới nhận tệp (iCheck — FE click lớp phủ).
slotKey theo DÒNG để nhiều tệp cùng dòng được FE gom vào một lần chọn tệp (Đơn M15 + Mẫu 15a/15b quét rời).
"""

ROW_DON = 1
ROW_GIAY_TO_QSDD = 2
ROW_THUA_KE = 3
ROW_TRICH_LUC = 4
ROW_BAO_CAO_RA_SOAT = 5
ROW_THIET_KE = 6
ROW_NGHIA_VU_TAI_CHINH = 7
ROW_QUOC_PHONG = 8

# Cổng chỉ in tiêu đề cột, không có dòng "(1) Đối với trường hợp…" → neo vùng quét vào tiêu đề cột.
SECTION_HEADER = "ten giay to"

# vị trí dòng → (từ khóa dòng đã fold, tên dòng rút gọn)
ROWS: dict[int, tuple[list[str], str]] = {
    ROW_DON: (["don dang ky dat dai"],
              "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15/21)"),
    # Dòng "Hồ sơ thiết kế…" cũng nhắc "Điều 149 Luật Đất đai" nhưng KHÔNG có "Điều 137".
    ROW_GIAY_TO_QSDD: (["dieu 137"],
                       "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, "
                       "khoản 4, khoản 5 Điều 149 Luật Đất đai"),
    ROW_THUA_KE: (["nhan thua ke quyen su dung dat"],
                  "Giấy tờ về việc nhận thừa kế quyền sử dụng đất (người gốc Việt Nam định cư ở nước ngoài)"),
    ROW_TRICH_LUC: (["trich luc ban do dia chinh"],
                    "Sơ đồ hoặc bản trích lục bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính thửa đất"),
    # Cổng in dòng này HAI LẦN (dòng trùng). FE lấy ô còn trống ĐẦU TIÊN khớp từ khóa → dòng trên; dòng dưới
    # để trống, đúng như ảnh hướng dẫn ghi "DÒNG TRÙNG – không đính kèm lại".
    ROW_BAO_CAO_RA_SOAT: (["bao cao ket qua ra soat hien trang"],
                          "Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu số 15d/21d) — tổ chức"),
    ROW_THIET_KE: (["ho so thiet ke xay dung cong trinh"],
                   "Hồ sơ thiết kế xây dựng công trình đã được thẩm định/nghiệm thu"),
    ROW_NGHIA_VU_TAI_CHINH: (["chung tu thuc hien nghia vu tai chinh"],
                             "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ miễn giảm nghĩa vụ tài chính"),
    ROW_QUOC_PHONG: (["vi tri dong quan"],
                     "Quyết định vị trí đóng quân/văn bản giao cơ sở nhà đất quốc phòng, an ninh"),
}

# label → vị trí dòng; label không có ở đây → "Giấy tờ khác".
ROUTES: dict[str, int] = {
    "don_dang_ky": ROW_DON,
    # Mẫu 15a/15b là PHỤ LỤC của Đơn → cùng dòng với Đơn (slotKey theo dòng nên FE gom một lần bơm tệp).
    "danh_sach_kem_don": ROW_DON,
    "giay_to_quyen_su_dung_dat": ROW_GIAY_TO_QSDD,
    "giay_to_thua_ke": ROW_THUA_KE,
    "trich_luc": ROW_TRICH_LUC,
    "bao_cao_ra_soat": ROW_BAO_CAO_RA_SOAT,
    "ho_so_thiet_ke": ROW_THIET_KE,
    "chung_tu_tai_chinh": ROW_NGHIA_VU_TAI_CHINH,
    "qd_quoc_phong": ROW_QUOC_PHONG,
}

# (label, tên hiển thị mặc định, mô tả cho LLM)
LABELS: list[tuple[str, str, str]] = [
    ("don_dang_ky", "Đơn đăng ký đất đai, tài sản gắn liền với đất",
     "ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT (Mẫu số 15 hoặc Mẫu số 21) — có 'Kính gửi: Ủy ban nhân "
     "dân…', mục '1. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất', '2. Thửa đất đăng ký', "
     "'4. Đề nghị của người sử dụng đất', ký 'Người sử dụng đất kê khai'. Bản quét gộp cả Đơn lẫn các danh "
     "sách Mẫu 15a/15b hay báo cáo kèm theo vẫn là 'don_dang_ky' vì Đơn là giấy tờ chính"),
    ("danh_sach_kem_don", "Danh sách kèm theo Đơn đăng ký (Mẫu 15a/15b)",
     "DANH SÁCH quét RIÊNG, không kèm Đơn: 'DANH SÁCH NHỮNG NGƯỜI SỬ DỤNG CHUNG THỬA ĐẤT, SỞ HỮU CHUNG TÀI "
     "SẢN' (Mẫu số 15a) hoặc 'DANH SÁCH CÁC THỬA ĐẤT' (Mẫu số 15b) — bảng nhiều dòng, ghi 'Kèm theo đơn đăng "
     "ký đất đai, tài sản gắn liền với đất'"),
    ("giay_to_quyen_su_dung_dat", "Giấy tờ về quyền sử dụng đất",
     "GIẤY TỜ CŨ VỀ QUYỀN SỬ DỤNG ĐẤT của hộ gia đình, cá nhân theo Điều 137 Luật Đất đai: giấy tờ do chế độ "
     "cũ cấp, giấy giao đất/cấp đất cho HỘ GIA ĐÌNH - CÁ NHÂN, sổ mục kê, giấy tờ mua bán/tặng cho/thừa kế "
     "nhà đất lập trước 01/7/2004, giấy phép xây dựng, văn bản nghiệm thu công trình, giấy tờ chứng minh "
     "quyền sở hữu nhà ở/công trình xây dựng"),
    ("giay_to_thua_ke", "Giấy tờ về việc nhận thừa kế quyền sử dụng đất",
     "VĂN BẢN THỪA KẾ quyền sử dụng đất theo pháp luật dân sự: di chúc, văn bản khai nhận/thỏa thuận phân "
     "chia di sản thừa kế, văn bản từ chối nhận di sản — thường có công chứng, chứng thực"),
    ("trich_luc", "Trích lục bản đồ địa chính thửa đất",
     "SƠ ĐỒ/TRÍCH LỤC BẢN ĐỒ ĐỊA CHÍNH/MẢNH TRÍCH ĐO ĐỊA CHÍNH thửa đất, bản đồ ranh giới - mốc giới sử dụng "
     "đất, phiếu đo đạc chỉnh lý: có sơ đồ thửa, bảng tọa độ đỉnh thửa VN-2000, số hiệu thửa đất, số tờ bản "
     "đồ, diện tích, tỷ lệ bản đồ, dấu của đơn vị đo đạc"),
    ("bao_cao_ra_soat", "Báo cáo kết quả rà soát hiện trạng sử dụng đất",
     "BÁO CÁO KẾT QUẢ RÀ SOÁT HIỆN TRẠNG SỬ DỤNG ĐẤT của tổ chức, tổ chức tôn giáo (Mẫu số 15d/21d) — số "
     "hiệu dạng '…/BC-…', có mục 'I. HIỆN TRẠNG QUẢN LÝ, SỬ DỤNG ĐẤT', 'III. NGUỒN GỐC SỬ DỤNG ĐẤT', "
     "'V. KIẾN NGHỊ'"),
    ("ho_so_thiet_ke", "Hồ sơ thiết kế xây dựng công trình",
     "HỒ SƠ THIẾT KẾ XÂY DỰNG công trình đã được cơ quan chuyên môn thẩm định, hoặc văn bản chấp thuận kết "
     "quả nghiệm thu hoàn thành hạng mục công trình"),
    ("chung_tu_tai_chinh", "Chứng từ thực hiện nghĩa vụ tài chính",
     "BIÊN LAI, phiếu thu, giấy nộp tiền vào ngân sách, thông báo nộp tiền sử dụng đất, tờ khai lệ phí trước "
     "bạ, tờ khai thuế sử dụng đất phi nông nghiệp, giấy tờ miễn/giảm nghĩa vụ tài chính"),
    ("qd_quoc_phong", "Quyết định vị trí đóng quân, giao cơ sở nhà đất quốc phòng - an ninh",
     "QUYẾT ĐỊNH VỊ TRÍ ĐÓNG QUÂN hoặc văn bản giao cơ sở nhà đất, địa điểm công trình quốc phòng, an ninh "
     "cho đơn vị quân đội, đơn vị công an"),
    ("qd_phuong_an_su_dung_dat", "Quyết định phê duyệt phương án sử dụng đất",
     "QUYẾT ĐỊNH của UBND tỉnh/huyện PHÊ DUYỆT PHƯƠNG ÁN SỬ DỤNG ĐẤT của tổ chức, quyết định giao đất/cho "
     "thuê đất cho TỔ CHỨC, quyết định phê duyệt dự án — số hiệu dạng '…/QĐ-UBND'"),
    ("qd_thanh_lap_to_chuc", "Giấy tờ về tư cách pháp nhân",
     "QUYẾT ĐỊNH THÀNH LẬP tổ chức/đơn vị sự nghiệp, quyết định quy định chức năng nhiệm vụ, GIẤY CHỨNG NHẬN "
     "ĐĂNG KÝ DOANH NGHIỆP, giấy tờ công nhận tổ chức tôn giáo — giấy tờ xác lập tư cách pháp nhân của chủ "
     "hồ sơ"),
    ("don_de_nghi_xac_nhan", "Đơn đề nghị xác nhận các thành viên có chung quyền sử dụng đất",
     "ĐƠN ĐỀ NGHỊ XÁC NHẬN các thành viên hộ gia đình có chung quyền sử dụng đất, văn bản thỏa thuận cử "
     "người đại diện đứng tên Giấy chứng nhận, bản cam đoan về nguồn gốc đất, giấy xác nhận của UBND xã về "
     "nguồn gốc/không tranh chấp"),
    ("van_ban_dai_dien", "Giấy ủy quyền",
     "GIẤY UỶ QUYỀN/HỢP ĐỒNG UỶ QUYỀN hoặc văn bản cử người đại diện đi nộp hồ sơ — có 'Bên uỷ quyền (Bên "
     "A)', 'Bên nhận uỷ quyền (Bên B)' hoặc 'tôi uỷ quyền cho ông/bà…'"),
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu kèm theo", "Giấy tờ khác hoặc không xác định được loại"),
]

# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED_LABELS = {"cccd"}

# Giấy tờ hay bị QUÉT GỘP vào tệp Đơn đăng ký (hồ sơ mẫu HS01, HS03 đều một tệp cho cả bộ): không có tệp
# riêng mà có tệp "chủ" thì cảnh báo, để cán bộ biết dòng đó trống vì nằm chung tệp chứ không phải trợ lý bỏ
# sót. label -> (label chủ, mô tả).
MERGED_HINTS: dict[str, tuple[str, str]] = {
    "trich_luc": ("don_dang_ky", "Trích lục/mảnh trích đo bản đồ địa chính thửa đất"),
    "bao_cao_ra_soat": ("don_dang_ky", "Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu 15d/21d)"),
    "danh_sach_kem_don": ("don_dang_ky", "Danh sách Mẫu 15a/15b kèm theo Đơn"),
}

_DISPLAY = {label: name for label, name, _ in LABELS}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_for(label: str) -> int | None:
    return ROUTES.get(label)


def slot(position: int) -> dict:
    keywords, name = ROWS[position]
    return {
        "slotKey": f"lc_115688_{position}",
        "slotName": f"{position}. {name}",
        "sectionHeader": SECTION_HEADER,
        "slotKeywords": list(keywords),
    }


def row_name(position: int) -> str:
    return ROWS[position][1]


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in LABELS)
