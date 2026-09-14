"""Trích khối NGƯỜI YÊU CẦU và khối NGƯỜI MẤT trên Tờ khai đăng ký khai tử bằng Python thuần.

Tờ khai đăng ký khai tử là biểu mẫu chuẩn, nhãn cố định, nên cả hai khối đọc được tất định
mà không cần LLM. Module này tồn tại vì agent trích xuất liên tục dồn dữ kiện của tờ khai vào
Cccd_* và bỏ trống NguoiYeuCau_*, khiến biểu mẫu bị điền bằng dữ liệu VNeID của tài khoản đăng
nhập thay vì người đứng đơn; và tương tự, hay bỏ sót nguyên khối người mất (ngày/giờ chết,
nguyên nhân chết, dân tộc, nơi cư trú cuối cùng) khiến mục II của biểu mẫu trống.

Kết quả ở đây chỉ BÙ các field mà agent bỏ sót; agent trả giá trị nào thì giá trị đó vẫn được giữ.
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

# Khối NGƯỜI MẤT: từ câu "Đề nghị cơ quan đăng ký khai tử..." tới lời cam đoan cuối tờ khai.
_DECEASED_START = _REQUESTER_END
_DECEASED_END = r"toi\s*cam\s*doan|lam\s*tai\s*[:,]|de\s*nghi\s*cap\s*ban\s*sao|nguoi\s*yeu\s*cau\s*\("
_DECEASED_BLOCK_MAX = 1200

# Nhãn khối người mất theo mẫu TP/HT-2020-TKKT. "soGiayBaoTu" chỉ dùng để CHẶN ĐUÔI cho
# nguyên nhân chết, không xuất field (Gbt_* có luồng kiểm chứng riêng ở runner).
_DECEASED_LABELS: tuple[tuple[str, str], ...] = (
    ("hoTen", r"ho\s*,?\s*chu\s*dem\s*,?\s*ten"),
    ("ngaySinh", r"ngay\s*,?\s*thang\s*,?\s*nam\s*sinh"),
    ("gioiTinh", r"gioi\s*tinh"),
    ("danToc", r"dan\s*toc"),
    ("quocTich", r"quoc\s*tich"),
    ("noiCuTru", r"noi\s*cu\s*tru(?:\s*cuoi\s*cung)?"),
    ("giayTo", r"giay\s*to\s*tuy\s*than"),
    ("noiCap", r"noi\s*cap"),
    ("thoiDiemChet", r"(?:da\s*)?chet\s*vao\s*luc|tu\s*vong\s*(?:vao\s*)?luc"),
    ("noiChet", r"noi\s*chet|noi\s*tu\s*vong"),
    ("nguyenNhanChet", r"nguyen\s*nhan\s*chet|nguyen\s*nhan\s*tu\s*vong"),
    ("soGiayBaoTu", r"so\s*giay\s*bao\s*tu"),
)

# "10 giờ 30 phút" / "10 giờ" — giờ phải đứng trước phút, tránh bắt nhầm số nhà.
_DEATH_CLOCK_RE = re.compile(r"(?<!\d)(\d{1,2})\s*gio(?:\s*(\d{1,2})\s*phut)?")
# "ngày 18 tháng 7 năm 2026"
_DEATH_DATE_TEXT_RE = re.compile(r"ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})")
_YEAR_RE = re.compile(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)")

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


def _block(text: str, start_pattern: str, end_pattern: str, skip_start: bool = False) -> tuple[str, str]:
    """Cắt đúng một khối của tờ khai; trả (text gốc, text đã bỏ dấu) cùng độ dài."""
    folded = _fold(text)
    start = re.search(start_pattern, folded)
    if not start:
        return "", ""
    begin = start.end() if skip_start else start.start()
    end = re.search(end_pattern, folded[begin:])
    stop = begin + (end.start() if end else len(folded) - begin)
    return text[begin:stop], folded[begin:stop]


def _requester_block(text: str) -> tuple[str, str]:
    """Cắt đúng khối người yêu cầu; trả (text gốc, text đã bỏ dấu) cùng độ dài."""
    return _block(text, _REQUESTER_START, _REQUESTER_END)


def _deceased_block(text: str) -> tuple[str, str]:
    """Cắt đúng khối người mất (sau câu "Đề nghị cơ quan đăng ký khai tử...").

    ocr_text là text GỘP mọi tài liệu, nên khi tờ khai thiếu lời cam đoan cuối trang khối
    này có thể chạy lan sang CCCD/giấy báo tử phía sau. Mục II của mẫu chỉ dài vài trăm ký
    tự, nên cắt cứng để không kéo nhãn của tài liệu khác vào.
    """
    block, folded = _block(text, _DECEASED_START, _DECEASED_END, skip_start=True)
    return block[:_DECEASED_BLOCK_MAX], folded[:_DECEASED_BLOCK_MAX]


def _labeled_values(
    block: str,
    folded_block: str,
    labels: tuple[tuple[str, str], ...] = _LABELS,
) -> dict[str, str]:
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


def _short_word(value: str, limit: int = 30) -> str:
    """Giá trị một-cụm-từ (dân tộc, quốc tịch): OCR dính cả câu thì bỏ, không đoán."""
    text = _clean(value)
    if not text or len(text) > limit or re.search(r"\d", text):
        return ""
    return text


def _gender(value: str) -> str:
    """Giới tính chỉ nhận khi ô ngắn và có đúng từ Nam/Nữ — "Việt Nam" cũng chứa "nam"."""
    text = _clean(value)
    if not text or len(text) > 20:
        return ""
    folded = _fold(text)
    if re.search(r"\bnu\b", folded):
        return "Nữ"
    if re.search(r"\bnam\b", folded):
        return "Nam"
    return ""


def _birth_date(value: str) -> str:
    """Ngày sinh: đủ dd/mm/yyyy thì trả đủ, chỉ có năm thì trả yyyy."""
    folded = _fold(value)
    match = _ANY_DATE_RE.search(folded)
    if match:
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{day:02d}/{month:02d}/{year}"
    year_match = _YEAR_RE.search(folded)
    return year_match.group(1) if year_match else ""


def _death_moment(value: str) -> tuple[str, str]:
    """"10 giờ 30 phút, ngày 18 tháng 7 năm 2026" -> ("18/07/2026", "10:30")."""
    folded = _fold(value)
    date = ""
    text_match = _DEATH_DATE_TEXT_RE.search(folded)
    numeric_match = _ANY_DATE_RE.search(folded)
    match = text_match or numeric_match
    if match:
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if 1 <= day <= 31 and 1 <= month <= 12:
            date = f"{day:02d}/{month:02d}/{year}"

    time = ""
    clock = _DEATH_CLOCK_RE.search(folded)
    if clock:
        hour = int(clock.group(1))
        minute = int(clock.group(2) or 0)
        if hour <= 23 and minute <= 59:
            time = f"{hour:02d}:{minute:02d}"
    return date, time


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


def deceased_fields(ocr_text: str) -> dict:
    """Đọc khối người mất của tờ khai -> dict NguoiMat_* (bỏ ô trống).

    Mục II của tờ khai là biểu mẫu cố định nên đọc tất định được; đây là lưới an toàn cho
    các ô agent hay bỏ sót (ngày/giờ chết, nguyên nhân chết, dân tộc, nơi cư trú cuối cùng).
    """
    block, folded_block = _deceased_block(ocr_text or "")
    if not block:
        return {}

    values = _labeled_values(block, folded_block, _DECEASED_LABELS)
    id_line = values.get("giayTo", "")
    issuer_line = values.get("noiCap", "")
    ngay_mat, gio_mat = _death_moment(values.get("thoiDiemChet", ""))

    out = {
        "NguoiMat_HoTen": values.get("hoTen", ""),
        "NguoiMat_NgaySinh": _birth_date(values.get("ngaySinh", "")),
        "NguoiMat_GioiTinh": _gender(values.get("gioiTinh", "")),
        "NguoiMat_DanToc": _short_word(values.get("danToc", "")),
        "NguoiMat_QuocTich": _short_word(values.get("quocTich", "")),
        "NguoiMat_SoDinhDanh": _identity_number(id_line),
        "NguoiMat_NgayCapGiayTo": _issue_date(issuer_line, id_line),
        "NguoiMat_NoiCapGiayTo": _issuer(issuer_line),
        "NguoiMat_NoiCuTruCuoiCung": _area(values.get("noiCuTru", "")),
        "NguoiMat_NgayMat": ngay_mat,
        "NguoiMat_GioMat": gio_mat,
        "NguoiMat_NoiChet": _area(values.get("noiChet", "")),
        "NguoiMat_NguyenNhanMat": _clean(values.get("nguyenNhanChet", "")),
    }
    return {name: value for name, value in out.items() if value}


# ---------------------------------------------------------------------------------------------
# ẢNH THẺ CCCD/CĂN CƯỚC: chỉ đọc 4 ô họ tên, số, ngày cấp, nơi cấp.
# ---------------------------------------------------------------------------------------------
_CARD_ID_LABEL = r"^\s*so(?:\s*dinh\s*danh\s*ca\s*nhan)?\s*/\s*(?:no\b|personal\s*identification\s*number)"
_CARD_NAME_LABEL = r"^\s*ho\s*,?\s*(?:va|chu\s*dem\s*va)\s*ten(?:\s*khai\s*sinh)?\s*/\s*full\s*name"
_CARD_ISSUE_LABEL = r"^\s*ngay\s*,?\s*thang\s*,?\s*nam(?:\s*cap)?\s*/\s*(?:date\s*,?\s*month\s*,?\s*year|date\s*of\s*issue)"
# Dòng MRZ mặt sau: IDVNM + 9 số seri + 1 số kiểm tra + 12 số định danh.
_CARD_MRZ_RE = re.compile(r"IDVNM\d{9}[\dA-Z<](\d{12})")
_CARD_LABEL_TAIL = r"^[\s:/.]*"


def _card_value(lines: list[str], index: int, label_pattern: str) -> str:
    """Giá trị của nhãn: phần sau nhãn trên cùng dòng, trống thì lấy dòng kế tiếp."""
    folded = _fold(lines[index])
    match = re.search(label_pattern, folded)
    tail = re.sub(_CARD_LABEL_TAIL, "", lines[index][match.end():]).strip() if match else ""
    if tail:
        return tail
    return lines[index + 1].strip() if index + 1 < len(lines) else ""


def _card_issuer(text: str) -> str:
    folded = _fold(text)
    # CCCD cũ ký "CỤC TRƯỞNG CỤC CẢNH SÁT..." (con dấu có thể in thêm BỘ CÔNG AN); thẻ Căn cước mới
    # chỉ ghi "BỘ CÔNG AN".
    if re.search(r"cuc\s*canh\s*sat", folded):
        return "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    if re.search(r"bo\s*cong\s*an|ministry\s*of\s*public\s*security", folded):
        return "Bộ Công an"
    return ""


def identity_cards(ocr_text: str) -> dict[str, dict]:
    """Họ tên/số/ngày cấp/nơi cấp của mọi thẻ đọc được trong OCR, gom theo số định danh 12 chữ số.

    Mặt trước cho số + họ tên. Mặt sau cho ngày cấp + nơi cấp và được ghép về đúng thẻ bằng số
    định danh trong dòng MRZ, không dựa vào thứ tự file (một PDF hay chứa nhiều mặt trước rồi mới
    tới các mặt sau).
    """
    cards: dict[str, dict] = {}
    lines = str(ocr_text or "").splitlines()
    front_id = ""
    back_date = ""
    back_text: list[str] = []
    for index, line in enumerate(lines):
        folded = _fold(line)
        if re.search(_CARD_ID_LABEL, folded):
            digits = re.sub(r"\D", "", _card_value(lines, index, _CARD_ID_LABEL))
            front_id = digits if len(digits) == 12 else ""
            if front_id:
                cards.setdefault(front_id, {"SoDinhDanh": front_id})
            continue
        if front_id and re.search(_CARD_NAME_LABEL, folded):
            name = re.sub(r"\s+", " ", _card_value(lines, index, _CARD_NAME_LABEL)).strip(" .:")
            if name and not re.search(r"\d", name):
                cards[front_id].setdefault("HoTen", name)
            front_id = ""
            continue
        if re.search(_CARD_ISSUE_LABEL, folded):
            back_date = _issue_date(_card_value(lines, index, _CARD_ISSUE_LABEL))
            back_text = []
            continue
        mrz = _CARD_MRZ_RE.search(line.replace(" ", ""))
        if mrz:
            card = cards.setdefault(mrz.group(1), {"SoDinhDanh": mrz.group(1)})
            if back_date:
                card.setdefault("NgayCap", back_date)
                # Nơi cấp nằm giữa dòng ngày cấp và MRZ của CHÍNH mặt sau này.
                issuer = _card_issuer("\n".join(back_text))
                if issuer:
                    card.setdefault("NoiCap", issuer)
            back_date, back_text = "", []
            continue
        back_text.append(line)
    return cards


_CARD_ROLE_FIELDS = {
    # vai -> (field số trên tờ khai, {ô trên thẻ -> field ghi đè})
    "requester": ("NguoiYeuCau_SoDinhDanh", {
        "HoTen": "NguoiYeuCau_HoTen",
        "SoDinhDanh": "NguoiYeuCau_SoDinhDanh",
        "NgayCap": "NguoiYeuCau_NgayCap",
        "NoiCap": "NguoiYeuCau_NoiCap",
    }),
    "deceased": ("NguoiMat_SoDinhDanh", {
        "HoTen": "NguoiMat_HoTen",
        "SoDinhDanh": "NguoiMat_SoDinhDanh",
        "NgayCap": "NguoiMat_NgayCapGiayTo",
        "NoiCap": "NguoiMat_NoiCapGiayTo",
    }),
}
_REQUESTER_CARD_GROUP = {
    "HoTen": "Cccd_HoTen",
    "SoDinhDanh": "Cccd_SoDinhDanh",
    "NgayCap": "Cccd_NgayCap",
    "NoiCap": "Cccd_NoiCap",
}


def prefer_identity_cards(fields: list[dict], ocr_text: str, comp_by_name: dict[str, str]) -> list[dict]:
    """Số giấy tờ trên tờ khai KHỚP số in trên ảnh thẻ → cùng một người: họ tên, số, ngày cấp, nơi cấp
    lấy theo THẺ (bản in), không theo chữ viết tay trên tờ khai. Áp dụng cho người yêu cầu và người mất.

    Chạy tất định trên OCR vì agent không đáng tin ở điểm này: có thẻ in "ĐÀO THỊ TĨNH" cùng số với
    tờ khai mà agent vẫn điền "ĐÀO THỊ TÍNH" theo tờ khai.
    """
    from app.pipelines.khai_tu.process.mapper import _same_id

    cards = identity_cards(ocr_text)
    if not cards:
        return fields
    values = {field.get("name"): field.get("value") for field in fields}

    def matching_card(number) -> dict | None:
        hits = [card for card_id, card in cards.items() if _same_id(card_id, number)]
        return hits[0] if len(hits) == 1 else None

    matched = {role: matching_card(values.get(id_field)) for role, (id_field, _) in _CARD_ROLE_FIELDS.items()}
    if matched["requester"] is not None and matched["requester"] is matched["deceased"]:
        return fields  # một thẻ không thể vừa là người yêu cầu vừa là người mất — không đoán

    updates: dict[str, object] = {}
    for role, (_, mapping) in _CARD_ROLE_FIELDS.items():
        card = matched[role]
        if not card:
            continue
        for key, name in mapping.items():
            if card.get(key):
                updates[name] = card[key]
        # Nhóm Cccd_* là thẻ agent đọc; cùng thẻ này thì cũng chép bản đọc tất định cho khớp.
        if _same_id(card["SoDinhDanh"], values.get("Cccd_SoDinhDanh")):
            for key, name in _REQUESTER_CARD_GROUP.items():
                if card.get(key):
                    updates[name] = card[key]

    if not updates:
        return fields
    out = [
        {**field, "value": updates.pop(field.get("name"))} if field.get("name") in updates else field
        for field in fields
    ]
    out.extend(
        {"name": name, "comp": comp_by_name.get(name, "x-input"), "value": value}
        for name, value in updates.items()
    )
    return out


def fill_missing(fields: list[dict], ocr_text: str, comp_by_name: dict[str, str]) -> list[dict]:
    """Bù các field tờ khai mà agent bỏ sót; KHÔNG ghi đè giá trị agent đã trả.

    Riêng 4 ô họ tên/số/ngày cấp/nơi cấp: vai nào có số trên tờ khai khớp số một ảnh thẻ thì ghi đè
    theo thẻ (xem prefer_identity_cards).
    """
    present = {
        field.get("name")
        for field in fields
        if field.get("value") not in (None, "", {}, [])
    }
    backfill = {**requester_fields(ocr_text), **deceased_fields(ocr_text)}
    extra = [
        {"name": name, "comp": comp_by_name.get(name, "x-input"), "value": value}
        for name, value in backfill.items()
        if name not in present
    ]
    return prefer_identity_cards(fields + extra, ocr_text, comp_by_name)
