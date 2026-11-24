"""Bảng thành phần hồ sơ cổng Bắc Ninh 1.115462 (xác nhận tiếp tục sử dụng đất nông nghiệp), theo mapping + ảnh ánh
xạ đính kèm ngày 24/11/2026: 2 thành phần, mỗi thành phần có hai dòng con Bản chính (số lượng 1) / Bản sao (số lượng 0,
không đính). FE (attachBacNinhByPlan) khớp thành phần theo MÃ TP-H05 in ở dòng tiêu đề, tick ô chọn rồi gán tệp vào
dòng ``slotKey``.

Giấy ủy quyền (kèm lời chứng chứng thực, cùng một giấy), CCCD, giấy khác → "File đính kèm khác" (bắt buộc khi đã tích
"người được ủy quyền").
"""

# (nhãn, mã TP-H05 | None = File đính kèm khác, dòng, mô tả cho LLM)
CATALOG: list[tuple[str, str | None, str, str]] = [
    ("don_09", "TP-H05.000053", "banChinh",
     "Đơn xin xác nhận (lại) thời hạn / tiếp tục sử dụng đất nông nghiệp (Mẫu số 09), GỒM CẢ trang \"II- XÁC NHẬN "
     "CỦA ỦY BAN NHÂN DÂN CẤP XÃ\" đi kèm."),
    ("gcn", "TP-H05.000040", "banChinh",
     "Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã cấp, gồm mọi trang: "
     "bìa, trang chứng nhận / bảng liệt kê thửa, sơ đồ thửa, 'Những thay đổi sau khi cấp'."),
    # --- không có dòng riêng → "File đính kèm khác" ---
    ("uy_quyen", None, "banChinh",
     "Giấy ủy quyền / hợp đồng ủy quyền / văn bản ủy quyền, GỒM CẢ trang lời chứng chứng thực chữ ký đi kèm."),
    ("cccd", None, "banChinh", "Căn cước công dân / CMND / thẻ căn cước / hộ chiếu."),
    ("khac", None, "banChinh", "Giấy tờ khác hoặc không xác định được loại."),
]

LABELS = [label for label, _, _, _ in CATALOG]
_BY_LABEL = {label: (code, slot) for label, code, slot, _ in CATALOG}

_DISPLAY = {
    "don_09": "Đơn xin xác nhận tiếp tục sử dụng đất nông nghiệp",
    "gcn": "Giấy chứng nhận đã cấp",
    "uy_quyen": "Giấy ủy quyền",
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
