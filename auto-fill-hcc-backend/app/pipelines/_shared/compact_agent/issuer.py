"""Suy cơ quan cấp CCCD/Căn cước khi OCR không đọc được nơi cấp.

Thẻ CĂN CƯỚC theo Luật Căn cước (cấp từ 01/7/2024) do BỘ CÔNG AN cấp;
CCCD gắn chip cũ (2021-2023) do Cục Cảnh sát QLHC về TTXH cấp.
Dùng chung cho tất cả pipeline agent_compact để không mặc định sai "Cục Cảnh sát..."
cho thẻ Căn cước mới.
"""
import re
import unicodedata

ISSUER_BO_CONG_AN = "Bộ Công an"
ISSUER_CUC = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

# Loại giấy tờ tùy thân KHỚP option dropdown công dịch vụ công.
DOC_THE_CAN_CUOC = "Thẻ Căn cước"          # thẻ Căn cước mới (Bộ Công an, từ 01/7/2024)
DOC_CCCD = "Thẻ căn cước công dân"          # CCCD gắn chip cũ (Cục Cảnh sát QLHC)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_issuer(place) -> str:
    """Chuẩn hóa nơi cấp CCCD/Căn cước về tên cơ quan gọn.

    Bỏ phần song ngữ tiếng Anh ("BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY" -> "Bộ Công an")
    và mọi biến thể hoa/thường/dấu. Không nhận ra thì trả nguyên văn (đã strip).
    """
    text = str(place or "").strip()
    if not text:
        return ""
    folded = _fold(text)
    compact = re.sub(r"[^a-z0-9]+", "", folded)
    # Cơ quan cấp CỤ THỂ (Cục Cảnh sát QLHC về TTXH) ưu tiên hơn tên bộ chủ quản: CCCD chip cũ và
    # giấy tờ người có công hay ghi "... cục cảnh sát QLHC về TTXH bộ công an" (có CẢ hai) → phải
    # trả Cục Cảnh sát. Thẻ Căn cước mới (Bộ Công an) KHÔNG in "cục cảnh sát" nên không lọt nhánh này.
    if (
        "cuc canh sat" in folded
        or "cuc truong cuc canh sat" in folded
        or ("cuc" in folded and "qlhc" in compact and "ttxh" in compact)
        or ("qlhc" in compact and "ttxh" in compact)
        or "cucsqlhc" in compact
        or "ccsqlhc" in compact
        # OCR/LLM hay đọc nhầm viết tắt "CCSQLHC" thành "CCSVLHC"/"CCSGLHC"... (Q↔V/G). Bắt chung chữ
        # ký: bắt đầu "ccs"/"cs" (Cục Cảnh Sát) + có "lhc" (quản lý hành chính) + "ttxh" (trật tự xã hội).
        or ("ccs" in compact and "lhc" in compact and "ttxh" in compact)
    ):
        return ISSUER_CUC
    if "bo cong an" in folded or "ministry of public security" in folded:
        return ISSUER_BO_CONG_AN
    return text


def default_issuer(ngay_cap) -> str:
    """Mặc định cơ quan cấp theo ngày cấp khi OCR không đọc được nơi cấp."""
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$", str(ngay_cap or ""))
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if (year, month, day) >= (2024, 7, 1):
            return ISSUER_BO_CONG_AN
    return ISSUER_CUC


def id_doc_type(loai_hint, issuer: str = "") -> str:
    """Loại giấy tờ tùy thân KHỚP option dropdown, phân biệt theo NƠI CẤP:
    Bộ Công an → "Thẻ Căn cước" (thẻ mới); Cục Cảnh sát → "Thẻ căn cước công dân" (CCCD cũ).

    CMND/Hộ chiếu/Thẻ thường trú/Giấy chứng nhận căn cước ưu tiên theo loai_hint (bất kể issuer).
    """
    norm = _fold(loai_hint)
    if "chung minh" in norm or "cmnd" in norm:
        return "Chứng minh nhân dân"
    if "ho chieu" in norm or "passport" in norm:
        return "Hộ chiếu"
    if "the thuong tru" in norm or "thuong tru" in norm:
        return "Thẻ thường trú"
    if "giay chung nhan can cuoc" in norm:
        return "Giấy chứng nhận căn cước"
    # Nhóm căn cước/CCCD: NƠI CẤP quyết định.
    iss = normalize_issuer(issuer) if issuer else ""
    if iss == ISSUER_BO_CONG_AN:
        return DOC_THE_CAN_CUOC
    if iss == ISSUER_CUC:
        return DOC_CCCD
    # Không suy được nơi cấp → dựa vào chữ trong loại (có "công dân" = CCCD cũ).
    if "cong dan" in norm:
        return DOC_CCCD
    if "can cuoc" in norm or "cccd" in norm:
        return DOC_THE_CAN_CUOC
    return str(loai_hint or "").strip()
