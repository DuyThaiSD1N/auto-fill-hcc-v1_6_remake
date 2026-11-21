"""Bảng thành phần hồ sơ cổng Bắc Ninh 1.115460 (đổi tên / thay đổi thông tin người sử dụng đất), theo crawl DOM ngày
21/11/2026: 7 thành phần, mỗi thành phần có hai dòng con Bản chính / Bản sao. FE (attachBacNinhByPlan) khớp thành phần
theo MÃ TP-H05 in ở dòng tiêu đề, tick ô chọn rồi gán tệp vào dòng ``slotKey``.

Chưa có ảnh ánh xạ → mọi giấy vào dòng Bản chính (như 1.115465). Giấy không thuộc 7 thành phần (CCCD, giấy khác) →
"File đính kèm khác".
"""

# (nhãn, mã TP-H05 | None = File đính kèm khác, dòng, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("don_18", "TP-H05.000026", "banChinh",
     "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18), gồm cả trang cam đoan, phần xác nhận của "
     "UBND cấp xã, hướng dẫn kê khai, Bảng 18a."),
    ("giay_to_thay_doi", "TP-H05.000049", "banChinh",
     "Giấy tờ chứng minh việc đổi tên / thay đổi thông tin của người sử dụng đất: giấy xác nhận thông tin về cư trú, "
     "giấy xác nhận số chứng minh nhân dân cũ / thông báo số định danh cá nhân, quyết định cho phép thay đổi họ tên, "
     "trích lục thay đổi / cải chính hộ tịch."),
    ("gcn", "TP-H05.000040", "banChinh",
     "Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã cấp, gồm mọi trang: "
     "bìa, mục I–IV, sơ đồ thửa, 'Những thay đổi sau khi cấp', trang bổ sung giấy chứng nhận."),
    ("vb_cho_phep_doi_ten", "TP-H05.000050", "banChinh",
     "Văn bản của cơ quan có thẩm quyền cho phép / công nhận việc TỔ CHỨC, cộng đồng dân cư, người gốc Việt Nam định "
     "cư ở nước ngoài đổi tên hoặc thay đổi thông tin (quyết định đổi tên, giấy chứng nhận đăng ký doanh nghiệp mới)."),
    ("van_ban_dai_dien", "TP-H05.000046", "banChinh",
     "Văn bản về việc đại diện: giấy ủy quyền, hợp đồng ủy quyền, văn bản ủy quyền, giấy giới thiệu."),
    ("vb_thay_doi_quyen", "TP-H05.000051", "banChinh",
     "Văn bản về việc thay đổi quyền của người có quyền lợi liên quan: hợp đồng / thỏa thuận xác lập, thay đổi, chấm "
     "dứt quyền đối với thửa đất liền kề (lối đi, cấp thoát nước…), văn bản thay đổi hạn chế quyền sử dụng đất."),
    ("trich_do", "TP-H05.000045", "banChinh",
     "Mảnh trích đo bản đồ địa chính thửa đất, trích lục bản đồ địa chính, bản vẽ đo đạc xác định lại kích thước "
     "cạnh, diện tích thửa đất."),
    # --- không có dòng riêng → "File đính kèm khác" ---
    ("cccd", None, "banChinh", "Căn cước công dân / CMND / thẻ căn cước / hộ chiếu."),
    ("khac", None, "banChinh",
     "Giấy tờ khác (văn bản xác nhận sạt lở, giấy xác nhận tình trạng hôn nhân…) hoặc không xác định được loại."),
]

LABELS = [label for label, _, _, _ in CATALOG]
_BY_LABEL = {label: (code, slot) for label, code, slot, _ in CATALOG}

_DISPLAY = {
    "don_18": "Đơn đăng ký biến động Mẫu số 18",
    "giay_to_thay_doi": "Giấy tờ chứng minh thay đổi thông tin",
    "gcn": "Giấy chứng nhận đã cấp",
    "vb_cho_phep_doi_ten": "Văn bản cho phép đổi tên",
    "van_ban_dai_dien": "Văn bản ủy quyền",
    "vb_thay_doi_quyen": "Văn bản thay đổi quyền liên quan",
    "trich_do": "Mảnh trích đo bản đồ địa chính",
    "cccd": "Căn cước công dân",
    "khac": "Giấy tờ kèm theo hồ sơ",
}


def normalize(label) -> str:
    text = str(label or "").strip().lower()
    return text if text in _BY_LABEL else "khac"


def is_supplementary(label: str) -> bool:
    return _BY_LABEL.get(label, (None, ""))[0] is None


def resolve(label: str) -> tuple[str, str, str]:
    """Nhãn → (target, componentName = mã TP-H05 | "", slotKey)."""
    code, slot = _BY_LABEL.get(label, (None, "banChinh"))
    if not code:
        return "supplementary", "", "banChinh"
    return "existing", code, slot


def display_name(label: str) -> str:
    return _DISPLAY.get(label, _DISPLAY["khac"])


def llm_options() -> str:
    return "\n".join(f"- {label}: {desc}" for label, _, _, desc in CATALOG)
