"""Trích khối NGƯỜI YÊU CẦU trên Tờ khai đăng ký khai tử bằng Python thuần.

Tờ khai đăng ký khai tử là biểu mẫu chuẩn, nhãn cố định, nên khối người yêu cầu đọc được
tất định mà không cần LLM. Module này tồn tại vì agent trích xuất liên tục dồn dữ kiện của
tờ khai vào Cccd_* và bỏ trống NguoiYeuCau_*, khiến biểu mẫu bị điền bằng dữ liệu VNeID của
tài khoản đăng nhập thay vì người đứng đơn.

Kết quả ở đây chỉ BÙ các field NguoiYeuCau_* mà agent bỏ sót; agent trả giá trị nào thì
giá trị đó vẫn được giữ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer

# Nhãn mở/đóng khối người yêu cầu. Khối này nằm giữa nhãn họ tên người yêu cầu và câu
# "Đề nghị cơ quan đăng ký khai tử..." — mọi nhãn trùng tên phía sau đều thuộc người chết.
_REQUESTER_START = r"ho\s*,?\s*chu\s*dem\s*,?\s*ten\s*(?:nguoi\s*yeu\s*cau|nguoi\s*di\s*khai)"
_REQUESTER_END = r"de\s*nghi\s*co\s*quan\s*dang\s*ky\s*khai\s*tu"

# Nhãn trong khối, dò trên text đã bỏ dấu. Giá trị của một nhãn kéo dài tới nhãn kế tiếp,
# vì OCR thường trả tờ khai thành một đoạn dài không xuống dòng.
_LABELS: tuple[tuple[str, str], ...] = (
    ("hoTen", _REQUESTER_START),
    ("ngaySinh", r"ngay\s*,?\s*thang\s*,?\s*nam\s*sinh"),
    ("noiCuTru", r"noi\s*(?:cu\s*tru|thuong\s*tru|dang\s*ky\s*thuong\s*tru)"),
    ("giayTo", r"giay\s*to\s*tuy\s*than"),
    ("noiCap", r"noi\s*cap"),
    ("quanHe", r"quan\s*he\s*voi\s*nguoi\s*(?:da\s*chet|chet|duoc\s*khai\s*tu)"),
)

# Số định danh: CMND 9 số, CCCD/Căn cước 12 số. OCR có thể chèn khoảng trắng/dấu chấm.
_ID_NUMBER_RE = re.compile(r"(?<!\d)(\d[\d.\s]{7,16}\d)(?!\d)")
_ISSUE_DATE_RE = re.compile(r"cap\s*(?:ngay|vao\s*ngay)?\s*:?\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})")
_ANY_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})(?!\d)")
# Ô để trống trên bản in: toàn dấu chấm/gạch/nhiễu, không phải giá trị thật.
_BLANK_RE = re.compile(r"^[\s.\-_…·•/\\(),:;]*$")
_AREA_PREFIX_RE = re.compile(r"^(xa|phuong|thi\s*tran|tt)\b")


def _fold(text: str) -> str:
    """Bỏ dấu NHƯNG GIỮ NGUYÊN vị trí từng ký tự, để span regex khớp ngược về text gốc."""
    out: list[str] = []
    for char in text:
        if char in "Đđ":
            out.append("d")
            continue
        decomposed = unicodedata.normalize("NFD", char)
        base = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        out.append((base[0] if base else char).lower())
    return "".join(out)


def _clean(value: str) -> str:
    """Bỏ chú thích mẫu "(1)".."(5)", dấu hai chấm thừa và khoảng trắng OCR."""
    text = re.sub(r"^\s*[:\-]\s*", "", str(value or ""))
    text = re.sub(r"\(\s*\d\s*\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,;:-")
    return "" if _BLANK_RE.match(text) else text.strip()


def _requester_block(text: str) -> tuple[str, str]:
    """Cắt đúng khối người yêu cầu; trả (text gốc, text đã bỏ dấu) cùng độ dài."""
    folded = _fold(text)
    start = re.search(_REQUESTER_START, folded)
    if not start:
        return "", ""
    end = re.search(_REQUESTER_END, folded[start.start():])
    stop = start.start() + (end.start() if end else len(folded) - start.start())
    return text[start.start():stop], folded[start.start():stop]


def _labeled_values(block: str, folded_block: str) -> dict[str, str]:
    """Giá trị của mỗi nhãn = đoạn từ hết nhãn đó tới đầu nhãn kế tiếp theo VỊ TRÍ."""
    hits: list[tuple[int, int, str]] = []
    for key, pattern in _LABELS:
        match = re.search(pattern, folded_block)
        if match:
            hits.append((match.start(), match.end(), key))
    hits.sort()

    values: dict[str, str] = {}
    for index, (_, label_end, key) in enumerate(hits):
        next_start = hits[index + 1][0] if index + 1 < len(hits) else len(block)
        values[key] = _clean(block[label_end:next_start])
    return values


def _identity_number(value: str) -> str:
    """Số giấy tờ dài nhất hợp lệ trong dòng; OCR hay dính khoảng trắng giữa các cụm số."""
    candidates = [
        re.sub(r"\D", "", match.group(1))
        for match in _ID_NUMBER_RE.finditer(value)
    ]
    valid = [digits for digits in candidates if len(digits) in (9, 12)]
    return valid[0] if valid else ""


def _document_type(value: str) -> str:
    """Loại giấy tờ theo đúng chữ tờ khai gọi, khớp option dropdown của cổng."""
    folded = _fold(value)
    if "chung minh" in folded or "cmnd" in folded or "cmtnd" in folded:
        return "Chứng minh nhân dân"
    if "ho chieu" in folded or "passport" in folded:
        return "Hộ chiếu"
    if "cccd" in folded or "can cuoc cong dan" in folded:
        return "Thẻ căn cước công dân"
    if "can cuoc" in folded or "cc" == folded.strip():
        return "Thẻ Căn cước"
    return ""


def _issue_date(*values: str) -> str:
    """Ngày cấp: ưu tiên cụm đi sau chữ "cấp", không có mới lấy ngày đầu tiên của dòng nơi cấp."""
    for value in values:
        folded = _fold(value)
        match = _ISSUE_DATE_RE.search(folded) or _ANY_DATE_RE.search(folded)
        if match:
            day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{day:02d}/{month:02d}/{year}"
    return ""


def _issuer(value: str) -> str:
    """Tên cơ quan cấp: bỏ đuôi "cấp ngày ..." và chức danh, rồi chuẩn hóa như CCCD."""
    folded = _fold(value)
    match = re.search(r"\bcap\s*(?:ngay|vao\s*ngay)\b", folded)
    text = value[:match.start()] if match else value
    text = _ANY_DATE_RE.sub(" ", text)
    text = _clean(text)
    return normalize_issuer(text) if text else ""


def _area(value: str) -> dict | None:
    """Tách "chi tiết - xã - (huyện) - tỉnh" thành object địa giới 2 cấp.

    Chỉ nhận xã khi có tiền tố loại đơn vị hoặc chuỗi đủ dài để suy vị trí, tránh
    biến một địa chỉ 2 cụm mơ hồ thành xã sai.
    """
    parts = [_clean(part) for part in re.split(r"\s*[-–—,]\s*|\s+thuoc\s+", value)]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None

    province = parts[-1]
    rest = parts[:-1]

    commune_index = next(
        (i for i, part in enumerate(rest) if _AREA_PREFIX_RE.match(_fold(part))),
        None,
    )
    if commune_index is None and len(rest) >= 2:
        # "[chi tiết], xã, huyện, tỉnh": cụm sát tỉnh là huyện, cụm trước nó là xã.
        commune_index = len(rest) - 2
    if commune_index is None:
        return None

    commune = re.sub(
        r"^(xã|phường|thị trấn|tt\.?)\s+", "", rest[commune_index], flags=re.IGNORECASE
    ).strip()
    detail = " ".join(rest[:commune_index]).strip()
    if not commune:
        return None
    return remap_area({
        "quocGia": "Việt Nam",
        "tinh": province,
        "xa": commune,
        "diaChi": detail,
    })


def requester_fields(ocr_text: str) -> dict:
    """Đọc khối người yêu cầu của tờ khai -> dict NguoiYeuCau_*/ToKhai_* (bỏ ô trống)."""
    block, folded_block = _requester_block(ocr_text or "")
    if not block:
        return {}

    values = _labeled_values(block, folded_block)
    id_line = values.get("giayTo", "")
    issuer_line = values.get("noiCap", "")

    out = {
        "NguoiYeuCau_HoTen": values.get("hoTen", ""),
        "NguoiYeuCau_SoDinhDanh": _identity_number(id_line),
        "NguoiYeuCau_LoaiGiayTo": _document_type(id_line),
        "NguoiYeuCau_NgayCap": _issue_date(issuer_line, id_line),
        "NguoiYeuCau_NoiCap": _issuer(issuer_line),
        "NguoiYeuCau_NoiCuTru": _area(values.get("noiCuTru", "")),
        "ToKhai_QuanHeNguoiYeuCau": values.get("quanHe", ""),
    }
    return {name: value for name, value in out.items() if value}


def fill_missing(fields: list[dict], ocr_text: str, comp_by_name: dict[str, str]) -> list[dict]:
    """Bù các field người yêu cầu mà agent bỏ sót; KHÔNG ghi đè giá trị agent đã trả."""
    present = {
        field.get("name")
        for field in fields
        if field.get("value") not in (None, "", {}, [])
    }
    extra = [
        {"name": name, "comp": comp_by_name.get(name, "x-input"), "value": value}
        for name, value in requester_fields(ocr_text).items()
        if name not in present
    ]
    return fields + extra
