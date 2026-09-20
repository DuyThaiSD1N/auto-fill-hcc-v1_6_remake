"""Catalog thành phần hồ sơ 1.115687 (Lào Cai) — bảng "Thành phần hồ sơ" bước 3.

Bảng PHẲNG, không chia nhóm, chỉ đúng 2 dòng (ảnh hướng dẫn hồ sơ mẫu 2 — Đinh Thị Thoa):
  1. Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định của pháp luật đất đai (bản chính)
  2. Giấy chứng nhận đã cấp (bản gốc)
Bên dưới là khối "Thông tin khác": ô "Về việc (*)" cổng ĐIỀN SẴN, ô "Ghi chú", và danh sách "Giấy tờ khác"
(chọn "Mới" → gõ tên → chọn tệp). Giấy tờ không có dòng riêng đi hết xuống "Giấy tờ khác".

VÌ SAO VẪN KHAI sectionHeader DÙ BẢNG KHÔNG CÓ NHÓM: content.js chỉ dùng slotKeywords do BE gửi khi item có
sectionHeader; không có thì nó tra bảng FIXED_SLOT_KEYWORDS cứng trong extension và thủ tục mới sẽ không khớp
được dòng nào (phải phát hành lại extension). Neo vào chính DÒNG TIÊU ĐỀ CỘT của bảng ("Tên giấy tờ") — FE lấy
mọi dòng NẰM SAU nó, tức đúng 2 dòng của bảng. Cùng cách làm với nhóm (1) của 1.115671.

tickRow=True: mỗi dòng có ô checkbox ở cột "#" phải tích thì cổng mới nhận tệp (iCheck — FE click lớp phủ).
slotKey theo DÒNG để nhiều tệp cùng dòng được FE gom vào một lần chọn tệp (ảnh scan sổ đỏ thường 2 trang rời).
"""

ROW_KIEN_NGHI = 1
ROW_GCN = 2

# Cổng chỉ in tiêu đề cột, không có dòng "(1) Đối với trường hợp…" → neo vùng quét vào tiêu đề cột.
SECTION_HEADER = "ten giay to"

# vị trí dòng → (từ khóa dòng đã fold, tên dòng rút gọn)
ROWS: dict[int, tuple[list[str], str]] = {
    # "văn bản kiến nghị" chỉ có ở dòng 1; KHÔNG dùng "giay chung nhan" vì dòng 1 cũng nhắc "Giấy chứng nhận".
    ROW_KIEN_NGHI: (["van ban kien nghi"],
                    "Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định (bản chính)"),
    # Dòng 1 ghi "cấp Giấy chứng nhận KHÔNG ĐÚNG quy định" nên không chứa cụm "giấy chứng nhận đã cấp".
    ROW_GCN: (["giay chung nhan da cap"], "Giấy chứng nhận đã cấp (bản gốc)"),
}

# label → vị trí dòng; label không có ở đây → "Giấy tờ khác".
ROUTES: dict[str, int] = {
    "don_kien_nghi": ROW_KIEN_NGHI,
    "gcn": ROW_GCN,
}

# (label, tên hiển thị mặc định, mô tả cho LLM)
LABELS: list[tuple[str, str, str]] = [
    ("don_kien_nghi", "Đơn đề nghị thu hồi, hủy Giấy chứng nhận",
     "ĐƠN ĐỀ NGHỊ THU HỒI/HỦY Giấy chứng nhận quyền sử dụng đất, hoặc văn bản kiến nghị việc cấp Giấy chứng "
     "nhận không đúng quy định — do CHÍNH người sử dụng đất viết, có 'Kính gửi', 'Tôi tên là', phần trình bày "
     "sự việc, phần cam kết và chữ ký của chủ sử dụng đất"),
    ("gcn", "Giấy chứng nhận quyền sử dụng đất",
     "GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất (sổ đỏ/sổ hồng) — "
     "trang bìa có quốc huy và số phát hành, các trang trong có thửa đất số, tờ bản đồ, diện tích, sơ đồ thửa "
     "đất, dấu của UBND. KHÔNG phải GCN đăng ký doanh nghiệp"),
    ("vb_ra_soat", "Văn bản rà soát của Văn phòng đăng ký đất đai",
     "VĂN BẢN của Chi nhánh Văn phòng đăng ký đất đai, Phòng/Sở chuyên môn hoặc UBND xã về việc KIỂM TRA, RÀ "
     "SOÁT, xác minh việc cấp Giấy chứng nhận trùng thửa/không đúng quy định"),
    ("vb_dong_thuan", "Giấy tờ của người cùng đứng tên, đồng sử dụng đất",
     "Văn bản ĐỒNG Ý/cam kết của người cùng đứng tên trên Giấy chứng nhận, giấy chứng tử/giấy báo tử, giấy "
     "đăng ký kết hôn, giấy tờ chứng minh quan hệ nhân thân của người đồng sử dụng đất"),
    ("vb_dai_dien", "Giấy ủy quyền",
     "GIẤY ỦY QUYỀN/hợp đồng ủy quyền có công chứng, chứng thực hoặc văn bản cử người đại diện đi nộp hồ sơ "
     "— có 'Bên ủy quyền (Bên A)', 'Bên nhận ủy quyền (Bên B)', lời chứng của công chứng viên"),
    ("vb_tu_cach_phap_nhan", "Giấy tờ về tư cách pháp nhân",
     "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP (mã số doanh nghiệp, người đại diện theo pháp luật) hoặc quyết "
     "định thành lập, quy định chức năng nhiệm vụ xác lập tư cách pháp nhân của tổ chức đứng đơn"),
    ("cccd", "Căn cước công dân", "CCCD/CMND/thẻ căn cước/hộ chiếu của bất kỳ ai"),
    ("khac", "Tài liệu kèm theo",
     "Giấy tờ khác (quyết định giao đất, biên lai, tờ khai thuế, trích lục bản đồ…) hoặc không xác định được loại"),
]

# CCCD không phải thành phần hồ sơ của thủ tục → không đính kèm.
SKIPPED_LABELS = {"cccd"}

_DISPLAY = {label: name for label, name, _ in LABELS}


def is_valid(label: str) -> bool:
    return label in _DISPLAY


def row_for(label: str) -> int | None:
    return ROUTES.get(label)


def slot(position: int) -> dict:
    keywords, name = ROWS[position]
    return {
        "slotKey": f"lc_115687_{position}",
        "slotName": f"{position}. {name}",
        "sectionHeader": SECTION_HEADER,
        "slotKeywords": list(keywords),
    }


def display_name(label: str) -> str:
    return _DISPLAY.get(label, "Tài liệu kèm theo")


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, desc in LABELS)
