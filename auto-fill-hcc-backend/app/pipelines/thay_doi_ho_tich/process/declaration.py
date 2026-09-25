"""Trích khối NGƯỜI YÊU CẦU trên Tờ khai thay đổi/cải chính/bổ sung hộ tịch bằng Python thuần.

Tờ khai thay đổi hộ tịch là biểu mẫu chuẩn, nhãn cố định, nên khối người yêu cầu đọc được
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
# "Đề nghị cơ quan đăng ký..." — mọi nhãn trùng tên phía sau đều thuộc người được thay đổi.
_REQUESTER_START = r"ho\s*,?\s*chu\s*dem\s*,?\s*ten\s*nguoi\s*yeu\s*cau"
_REQUESTER_END = r"de\s*nghi\s*co\s*quan\s*dang\s*ky\s*viec"

# Nhãn trong khối, dò trên text đã bỏ dấu. Giá trị của một nhãn kéo dài tới nhãn kế tiếp,
# vì OCR thường trả tờ khai thành một đoạn dài không xuống dòng.
_LABELS: tuple[tuple[str, str], ...] = (
    ("hoTen", _REQUESTER_START),
    ("ngaySinh", r"ngay\s*,?\s*thang\s*,?\s*nam\s*sinh"),
    ("noiCuTru", r"noi\s*(?:cu\s*tru|thuong\s*tru|dang\s*ky\s*thuong\s*tru)"),
    ("giayTo", r"(?:so\s*)?giay\s*to\s*tuy\s*than"),
    ("noiCap", r"noi\s*cap"),
)

# Khối NGƯỜI ĐƯỢC thay đổi/cải chính: mở bằng "cho người có tên dưới đây", đóng ở dòng khai
# sự kiện hộ tịch gốc ("Đã đăng ký ...") hoặc mục "Nội dung:"/"Lý do:". Mọi nhãn trùng tên nằm
# TRƯỚC câu mở đều thuộc người yêu cầu (mục I) nên không lọt vào khối này.
_SUBJECT_START = r"cho\s*nguoi\s*co\s*ten\s*duoi\s*day"
_SUBJECT_END = r"da\s*(?:duoc\s*)?dang\s*ky|noi\s*dung\s*:|ly\s*do\s*:"

_SUBJECT_LABELS: tuple[tuple[str, str], ...] = (
    ("hoTen", r"ho\s*,?\s*chu\s*dem\s*,?\s*ten"),
    ("ngaySinh", r"ngay\s*,?\s*thang\s*,?\s*nam\s*sinh"),
    ("gioiTinh", r"gioi\s*tinh"),
    ("danToc", r"dan\s*toc"),
    ("quocTich", r"quoc\s*tich"),
    ("noiCuTru", r"noi\s*(?:cu\s*tru|thuong\s*tru|dang\s*ky\s*thuong\s*tru)"),
    ("giayTo", r"(?:so\s*)?giay\s*to\s*tuy\s*than"),
    ("ngayCap", r"ngay\s*cap"),
    ("noiCap", r"noi\s*cap"),
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


def _block(text: str, start_pattern: str, end_pattern: str) -> tuple[str, str]:
    """Cắt một khối của tờ khai; trả (text gốc, text đã bỏ dấu) cùng độ dài."""
    folded = _fold(text)
    start = re.search(start_pattern, folded)
    if not start:
        return "", ""
    end = re.search(end_pattern, folded[start.end():])
    stop = start.end() + end.start() if end else len(folded)
    return text[start.start():stop], folded[start.start():stop]


def _labeled_values(block: str, folded_block: str, labels=_LABELS) -> dict[str, str]:
    """Giá trị của mỗi nhãn = đoạn từ hết nhãn đó tới đầu nhãn kế tiếp theo VỊ TRÍ."""
    hits: list[tuple[int, int, str]] = []
    for key, pattern in labels:
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
    # Cổng gộp thẻ Căn cước mới và CCCD cũ về một option "Căn cước công dân".
    if "cccd" in folded or "can cuoc" in folded or "cc" == folded.strip():
        return "Căn cước công dân"
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


def _gender(value: str) -> str:
    folded = _fold(_clean(value))
    if re.search(r"\bnu\b", folded):
        return "Nữ"
    if re.search(r"\bnam\b", folded):
        return "Nam"
    return ""


def _birth_date(value: str) -> str:
    """Ngày sinh dd/mm/yyyy; tờ khai cũ nhiều khi chỉ ghi năm."""
    match = _ANY_DATE_RE.search(_fold(value))
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{day:02d}/{month:02d}/{year}"
    year_only = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", str(value or ""))
    return year_only.group(1) if year_only else ""


def _name_key(value) -> str:
    return re.sub(r"\s+", " ", _fold(str(value or ""))).strip()


def subject_fields(ocr_text: str) -> dict:
    """Đọc khối NGƯỜI ĐƯỢC thay đổi/cải chính của tờ khai -> dict ChuThe_* (bỏ ô trống)."""
    block, folded_block = _block(ocr_text or "", _SUBJECT_START, _SUBJECT_END)
    if not block:
        return {}

    values = _labeled_values(block, folded_block, _SUBJECT_LABELS)
    id_line = values.get("giayTo", "")
    out = {
        "ChuThe_HoTen": values.get("hoTen", ""),
        "ChuThe_NgaySinh": _birth_date(values.get("ngaySinh", "")),
        "ChuThe_GioiTinh": _gender(values.get("gioiTinh", "")),
        # Dân tộc chỉ nhận khi tờ khai ghi rõ; ô để trống tuyệt đối không suy đoán.
        "ChuThe_DanToc": _clean(values.get("danToc", "")),
        "ChuThe_QuocTich": _clean(values.get("quocTich", "")),
        "ChuThe_SoDinhDanh": _identity_number(id_line),
        "ChuThe_NgayCapGiayTo": _issue_date(values.get("ngayCap", ""), values.get("noiCap", ""), id_line),
        "ChuThe_NoiCapGiayTo": _issuer(values.get("noiCap", "")),
        "ChuThe_NoiCuTru": _area(values.get("noiCuTru", "")),
    }
    return {name: value for name, value in out.items() if value}


def _same_subject(agent: dict, subject: dict) -> bool:
    """Nhóm ChuThe_* của agent có đúng là người mà tờ khai nêu đích danh hay không."""
    decl_id = re.sub(r"\D", "", str(subject.get("ChuThe_SoDinhDanh") or ""))
    agent_id = re.sub(r"\D", "", str(agent.get("ChuThe_SoDinhDanh") or ""))
    if decl_id and agent_id:
        return decl_id == agent_id
    decl_name = _name_key(subject.get("ChuThe_HoTen"))
    agent_name = _name_key(agent.get("ChuThe_HoTen"))
    if decl_name and agent_name:
        return decl_name == agent_name
    # Không đủ bằng chứng để kết luận khác người → giữ nguyên agent, chỉ bù ô thiếu.
    return True


def _apply_subject(fields: list[dict], subject: dict, comp_by_name: dict[str, str]) -> list[dict]:
    """Tờ khai nêu ĐÍCH DANH người được thay đổi/cải chính ở khối "cho người có tên dưới đây".

    Hồ sơ thường kèm cả giấy khai sinh/kết hôn/khai tử của NGƯỜI KHÁC (con, cha, mẹ...) làm giấy
    tờ chứng minh, và agent hay lấy nhầm chủ thể của giấy đó vào ChuThe_*. Khác người thì THAY
    TOÀN BỘ nhóm ChuThe_* bằng khối tờ khai; cùng người thì chỉ bù các ô agent bỏ sót.
    """
    if not subject.get("ChuThe_HoTen"):
        return fields

    agent = {
        field.get("name"): field.get("value")
        for field in fields
        if field.get("value") not in (None, "", {}, [])
    }
    kept = fields if _same_subject(agent, subject) else [
        field for field in fields
        if not str(field.get("name") or "").startswith("ChuThe_")
    ]
    present = {
        field.get("name")
        for field in kept
        if field.get("value") not in (None, "", {}, [])
    }
    return kept + [
        {"name": name, "comp": comp_by_name.get(name, "x-input"), "value": value}
        for name, value in subject.items()
        if name not in present
    ]


def requester_fields(ocr_text: str) -> dict:
    """Đọc khối người yêu cầu của tờ khai -> dict NguoiYeuCau_* (bỏ ô trống)."""
    block, folded_block = _block(ocr_text or "", _REQUESTER_START, _REQUESTER_END)
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
    }
    return {name: value for name, value in out.items() if value}


def fill_missing(fields: list[dict], ocr_text: str, comp_by_name: dict[str, str]) -> list[dict]:
    """Bù field người yêu cầu agent bỏ sót và chốt lại chủ thể theo khối tờ khai."""
    fields = _apply_subject(fields, subject_fields(ocr_text), comp_by_name)
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
