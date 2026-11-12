"""Bảng thành phần hồ sơ eForm Bắc Ninh 1.011442 (Đăng ký thay đổi biện pháp bảo đảm), theo ảnh ánh xạ 12/11/2026.

Mỗi thành phần có hai dòng con Bản chính / Bản sao; FE (attachBacNinhByPlan) khớp thành phần theo MÃ KQ in ở dòng
tiêu đề, tick ô chọn rồi gán tệp vào đúng dòng ``slotKey``. Dòng nào đính vào đâu chép đúng ảnh ánh xạ:
Phiếu 02a → Bản chính (bản thứ hai → Bản sao), Giấy chứng nhận → Bản chính, các văn bản còn lại → Bản sao.
Giấy tờ không thuộc 12 thành phần (Hợp đồng thế chấp gốc, CCCD, GCN đăng ký doanh nghiệp…) → "File đính kèm khác".
KQ003708 (GCN theo điểm b khoản 1 Điều 18) không tự đính: GCN đã đính ở KQ003707, cán bộ tự đính khi thuộc trường hợp.
"""

# (nhãn, mã KQ | None = File đính kèm khác, dòng, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("phieu_02a", "KQ003703", "banChinh",
     "Phiếu yêu cầu đăng ký thay đổi nội dung biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất "
     "(Mẫu số 02a). Mỗi BẢN phiếu (bản thứ hai cùng nội dung) là một giấy riêng."),
    ("hd_sua_doi", "KQ003704", "banSao",
     "Văn bản / Hợp đồng SỬA ĐỔI, BỔ SUNG hợp đồng thế chấp (hợp đồng bảo đảm), kể cả Lời chứng của công chứng viên "
     "đi kèm ngay sau."),
    ("vb_chuyen_giao", "KQ003705", "banSao",
     "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ."),
    ("vb_can_cu_khac", "KQ003706", "banSao",
     "Văn bản khác chứng minh căn cứ đăng ký thay đổi: công văn, quyết định của ngân hàng/cơ quan về đổi tên, sáp "
     "nhập, chấm dứt hoạt động, sắp xếp mạng lưới, thay đổi địa điểm của bên nhận bảo đảm…"),
    ("gcn", "KQ003707", "banChinh",
     "Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản khác gắn liền với đất (bản gốc), gồm mọi "
     "trang: bìa, mục I–IV, sơ đồ thửa, 'Những thay đổi sau khi cấp', TRANG BỔ SUNG GIẤY CHỨNG NHẬN."),
    ("van_ban_dai_dien", "KQ003709", "banSao",
     "Văn bản về đại diện: Giấy giới thiệu, Giấy/Văn bản ủy quyền cử người đi nộp hồ sơ."),
    ("vb_giao_nhiem_vu", "KQ003710", "banSao",
     "Văn bản pháp nhân GIAO NHIỆM VỤ cho chi nhánh/phòng giao dịch thực hiện việc yêu cầu đăng ký."),
    ("giay_to_mien_phi", "KQ003711", "banSao",
     "Giấy tờ chứng minh thuộc đối tượng được miễn phí đăng ký (hợp đồng tín dụng ưu đãi, văn bản xác nhận…)."),
    ("giay_to_nhieu_chu_the", "KQ003712", "banSao",
     "Văn bản thể hiện một bên bảo đảm/bên nhận bảo đảm đại diện cho những người còn lại (khi một bên gồm nhiều người)."),
    ("vb_ben_nhan_moi", "KQ003713", "banSao",
     "Văn bản chứng minh Công ty quản lý tài sản của tổ chức tín dụng / chủ thể khác trở thành bên nhận bảo đảm mới."),
    ("danh_muc_01d", "KQ003714", "banSao",
     "Danh mục văn bản kê khai theo Mẫu số 01đ hoặc 02đ (thay đổi nhiều biện pháp bảo đảm cùng bên nhận)."),
    # --- không có dòng riêng → "File đính kèm khác" ---
    ("hop_dong_the_chap", None, "banChinh",
     "Hợp đồng thế chấp / hợp đồng bảo đảm GỐC (không phải văn bản sửa đổi, bổ sung), kể cả lời chứng đi kèm."),
    ("gcn_dkdn", None, "banChinh",
     "Giấy chứng nhận đăng ký doanh nghiệp / đăng ký hoạt động chi nhánh."),
    ("cccd", None, "banChinh", "Căn cước công dân / CMND / thẻ căn cước / hộ chiếu."),
    ("khac", None, "banChinh", "Giấy tờ khác hoặc không xác định được loại."),
]

LABELS = [label for label, _, _, _ in CATALOG]
_BY_LABEL = {label: (kq, slot) for label, kq, slot, _ in CATALOG}

_DISPLAY = {
    "phieu_02a": "Phiếu yêu cầu đăng ký thay đổi Mẫu 02a",
    "hd_sua_doi": "Hợp đồng sửa đổi, bổ sung hợp đồng bảo đảm",
    "vb_chuyen_giao": "Văn bản chuyển giao quyền đòi nợ",
    "vb_can_cu_khac": "Văn bản căn cứ đăng ký thay đổi",
    "gcn": "Giấy chứng nhận quyền sử dụng đất",
    "van_ban_dai_dien": "Giấy giới thiệu, văn bản ủy quyền",
    "vb_giao_nhiem_vu": "Văn bản giao nhiệm vụ cho chi nhánh",
    "giay_to_mien_phi": "Giấy tờ miễn phí đăng ký",
    "giay_to_nhieu_chu_the": "Văn bản đại diện nhiều chủ thể",
    "vb_ben_nhan_moi": "Văn bản bên nhận bảo đảm mới",
    "danh_muc_01d": "Danh mục văn bản Mẫu 01đ, 02đ",
    "hop_dong_the_chap": "Hợp đồng thế chấp",
    "gcn_dkdn": "Giấy chứng nhận đăng ký doanh nghiệp",
    "cccd": "Căn cước công dân",
    "khac": "Giấy tờ kèm theo hồ sơ",
}

PHIEU = "phieu_02a"


def is_valid(label: str) -> bool:
    return label in _BY_LABEL


def normalize(label) -> str:
    text = str(label or "").strip().lower()
    return text if text in _BY_LABEL else "khac"


def is_supplementary(label: str) -> bool:
    return _BY_LABEL.get(label, (None, ""))[0] is None


def resolve(label: str, copy_index: int = 0) -> tuple[str, str, str]:
    """Nhãn → (target, componentName = mã KQ | "", slotKey). Bản thứ hai trở đi của Phiếu 02a → dòng Bản sao."""
    kq, slot = _BY_LABEL.get(label, (None, "banChinh"))
    if not kq:
        return "supplementary", "", "banChinh"
    if label == PHIEU and copy_index > 0:
        slot = "banSao"
    return "existing", kq, slot


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
