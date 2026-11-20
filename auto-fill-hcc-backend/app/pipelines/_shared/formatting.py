"""Helper dùng chung cho mapping OCR → fields."""
import difflib
import re
import unicodedata

Field = dict  # { "name": str, "comp": str, "value": str | dict }


def parse_address(addr: str | None) -> dict:
    """Tách "Khu 2, Hoàng Cương, Thanh Ba, Phú Thọ" → { tinh, diaChi }.

    - tinh  = cụm CUỐI (sau dấu phẩy cuối).
    - diaChi = CHỈ đơn vị nhỏ nhất (số nhà/khu/xóm/thôn/bản) = cụm ĐẦU; KHÔNG kèm xã/huyện/tỉnh
      (vì xã/phường đã có dropdown riêng trong x-select-area).
    """
    if not addr:
        return {}
    parts = [s.strip() for s in str(addr).split(",") if s.strip()]
    if not parts:
        return {}
    if len(parts) == 1:
        return {"diaChi": parts[0]}
    return {"tinh": parts[-1], "diaChi": parts[0]}


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFC", (s or "").strip().lower())


def same_name(a: str | None, b: str | None) -> bool:
    na, nb = re.sub(r"\s+", " ", _norm(a)), re.sub(r"\s+", " ", _norm(b))
    return bool(na) and bool(nb) and na == nb


def upper_person_name(value) -> str:
    """Ô "Họ, chữ đệm, tên" trên eForm hộ tịch: luôn VIẾT HOA — "ĐINH THỊ CHIÊN".

    Nguồn trả về đủ kiểu (tờ khai ghi "Đinh thi chiến", CCCD ghi "Đinh Thị Chiên") nên ép tại
    mapper thay vì trông chờ OCR/LLM trả đúng. Cũng bỏ gạch nối kiểu giấy hộ tịch cũ
    ("Nguyễn-Văn-An") và gom khoảng trắng thừa. str.upper() của Python xử lý đúng dấu tiếng Việt.

    Trả "" khi rỗng — mọi add() của mapper đều bỏ qua "" y như None, nên không sinh field rác.
    """
    text = str(value or "").strip()
    text = re.sub(r"\s*[-‐‑–—]+\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


# ── Email đọc từ giấy (OCR/LLM) → địa chỉ đúng khuôn để điền ô Email (cổng Bộ Công an validate chặt) ──
# Chạy thật 19/11/2026 (thị thực 1.001194): "lethihoa,0615@example.com" — OCR đọc dấu chấm thành dấu phẩy. Hay gặp thêm:
# "gmail,com", "gmail .com", "gmailcom", "@ gmail.com", nhãn "Email:" dính trước, chữ có dấu, dấu chấm thừa ở đầu/cuối.
_EMAIL_LABEL_RE = re.compile(r"^(?:e-?mail|thu dien tu|dia chi thu dien tu|dia chi email)\s*[:：\-]?\s*")
_EMAIL_FINAL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._%+-]*[a-z0-9_])?@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
                             r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$")
# Nhà cung cấp phổ biến: tên miền đọc lệch / mất dấu chấm → sửa về đúng tên ("gmai.com", "gmail.con", "gmailcom").
_EMAIL_PROVIDERS = ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com")
_EMAIL_BAD_TLDS = {"", "com", "con", "co", "cm", "om", "comm", "corn", "c0m"}


def _fold_email_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower().strip()


def _email_domain(domain: str) -> str:
    domain = re.sub(r"[,;:]", ".", domain)
    domain = re.sub(r"[^a-z0-9.-]", "", domain)
    domain = re.sub(r"\.{2,}", ".", domain).strip(".-")
    head, _, tld = domain.partition(".")
    for provider in _EMAIL_PROVIDERS:
        name = provider.split(".")[0]
        # "gmailcom" (mất dấu chấm) / "gmai.com" / "gmail.con" → gmail.com; "yahoo.com.vn" giữ nguyên (tld "com.vn").
        # Cùng chữ đầu: "mail.com", "ymail.com" là nhà cung cấp thật, không kéo về gmail.
        near = head == name or (head[:1] == name[:1] and difflib.SequenceMatcher(None, head, name).ratio() >= 0.8)
        if domain in (name, name + "com") or (near and tld in _EMAIL_BAD_TLDS):
            return provider
    return domain


def clean_email(value) -> str | None:
    """Email đọc từ giấy → "ten.ho@gmail.com" đúng khuôn, None khi không ra được email hợp lệ.

    Bỏ nhãn "Email:", dấu cách, dấu tiếng Việt; dấu phẩy / chấm phẩy / hai chấm (OCR đọc lệch dấu chấm) → dấu chấm; bỏ ký
    tự lạ; gộp ".." và bỏ dấu chấm đầu/cuối phần tên; sửa tên miền nhà cung cấp phổ biến đọc lệch ("gmail,com",
    "gmailcom", "gmai.com" → "gmail.com")."""
    text = _fold_email_text(value)
    if not text:
        return None
    text = re.sub(r"\s*(?:\(at\)|\[at\])\s*", "@", text)
    text = _EMAIL_LABEL_RE.sub("", text)
    text = re.sub(r"\s+", "", text).strip(".,;:")
    if text.count("@") != 1:
        return None
    local, domain = text.split("@")
    local = re.sub(r"[,;:]", ".", local)
    local = re.sub(r"[^a-z0-9._%+-]", "", local)
    local = re.sub(r"\.{2,}", ".", local).strip(".")
    email = f"{local}@{_email_domain(domain)}"
    return email if _EMAIL_FINAL_RE.match(email) else None


def keep_portal_values(fields: list[dict], names) -> list[dict]:
    """Gắn cờ ``keepPortalValue`` cho các ô của CHỦ TÀI KHOẢN VNeID mà cổng DVC Bộ Công an có thể đổ sẵn (SĐT, email người
    kê khai / người đề nghị / người bảo lãnh…). Extension (Auto Fill + trợ lý) thấy ô đang có giá trị không do chính nó
    ghi thì giữ nguyên, ô trống vẫn điền theo giấy (user 20/11/2026: SĐT / email Phần I cấp lại căn cước bị thay bằng của
    người trên giấy). Sửa tại chỗ và trả lại chính ``fields``."""
    names = set(names)
    for field in fields:
        if field.get("name") in names:
            field["keepPortalValue"] = True
    return fields


def normalize_date(d: str | None) -> str:
    """"22/4/2021" → "22/04/2021" (zero-pad ngày & tháng)."""
    if not d:
        return ""
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(d))
    if not m:
        return str(d)
    return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"


# Comp của ô ngày do extension điền qua ba ô con day/month/year → CHỈ hiểu dd/mm/yyyy.
# "raw" nằm ngoài danh sách: đó là input trần backend gửi đúng dạng cổng đang chờ, siết vào là hỏng.
_UI_DATE_COMPS = ("x-date", "x-date-text")

# Agent trả ngày đủ kiểu tùy giấy tờ: "5/3/2024", "16-12-2024", "22.11.2024", "2024-12-16".
_UI_DATE_DMY = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$")
_UI_DATE_ISO = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$")


def normalize_ui_date(value):
    """Mọi biến thể ngày → "dd/mm/yyyy"; không nhận ra dạng ngày thì GIỮ NGUYÊN.

    Giữ nguyên là bắt buộc: ô "Năm sinh" cha/mẹ chỉ có năm ("1968"), giấy tờ cũ hay ghi
    "Không rõ" — đoán bừa thành ngày đầy đủ là bịa dữ liệu.
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    m = _UI_DATE_DMY.match(text)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
    else:
        m = _UI_DATE_ISO.match(text)
        if not m:
            return value
        year, month, day = m.group(1), m.group(2), m.group(3)
    return f"{day.zfill(2)}/{month.zfill(2)}/{year}"


def normalize_ui_dates(fields):
    """Siết mọi ô ngày của một danh sách field UI về dd/mm/yyyy (sửa TẠI CHỖ, trả lại chính nó).

    Chốt chặn CHUNG cho mọi thủ tục: mỗi pipeline chuẩn hóa một kiểu, nhiều pipeline không làm gì
    cả. Extension gặp dạng lạ là bỏ qua ô đó, mà ô ngày trượt lượt điền đầu thì không được thử
    lại — ra đúng triệu chứng "lúc điền được, lúc không".
    """
    if not isinstance(fields, list):
        return fields
    for field in fields:
        if not isinstance(field, dict) or field.get("comp") not in _UI_DATE_COMPS:
            continue
        field["value"] = normalize_ui_date(field.get("value"))
    return fields


def parse_death_time(time: str | None) -> dict:
    """"HH:mm" hoặc "06 giờ 38 phút" → { hour, minute } (2 chữ số)."""
    if not time:
        return {}
    s = str(time).strip()
    m1 = re.match(r"^(\d{1,2})\s*:\s*(\d{1,2})", s)
    if m1:
        return {"hour": m1.group(1).zfill(2), "minute": m1.group(2).zfill(2)}
    m2 = re.search(r"(\d{1,2})\s*giờ\s*(\d{1,2})", s, re.IGNORECASE)
    if m2:
        return {"hour": m2.group(1).zfill(2), "minute": m2.group(2).zfill(2)}
    return {}


def area_value(tinh: str | None, dia_chi: str | None, quoc_gia: str = "Việt Nam") -> dict:
    return {"quocGia": quoc_gia, "tinh": tinh or "", "diaChi": dia_chi or ""}


def _fold_street(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


_HOUSE_NUMBER_RE = re.compile(r"^\s*(?:số\s+|so\s+)?([0-9]+[a-z]?(?:/[0-9a-z]+)*)[\s,]+(.+)$", re.IGNORECASE)
_STREET_SIMILARITY_MIN = 0.7


def _split_house_number(address) -> tuple[str, str] | None:
    match = _HOUSE_NUMBER_RE.match(str(address or ""))
    if not match:
        return None
    return match.group(1).lower(), match.group(2).strip(" ,")


def prefer_printed_street(area, card_area):
    """Địa chỉ viết tay trên tờ khai hay bị OCR đọc sai tên đường ("Nguyễn Thị Minh Khai" →
    "Nguyễn Thế Oan Khai"). Thẻ căn cước CỦA CHÍNH NGƯỜI ĐÓ in cùng địa chỉ → lấy tên đường in.

    Chỉ thay khi chắc là CÙNG một địa chỉ: cùng số nhà, cùng tỉnh, tên đường giống nhau ≥ 70%.
    Giữ nguyên tỉnh/xã của tờ khai (thẻ cũ còn in đơn vị hành chính trước sáp nhập, vd "P1").
    """
    if not isinstance(area, dict) or not isinstance(card_area, dict):
        return area
    declared = _split_house_number(area.get("diaChi"))
    printed = _split_house_number(card_area.get("diaChi"))
    if not declared or not printed or declared[0] != printed[0]:
        return area
    card_tinh = _fold_street(card_area.get("tinh")).replace("tinh ", "").replace("thanh pho ", "")
    area_tinh = _fold_street(area.get("tinh")).replace("tinh ", "").replace("thanh pho ", "")
    if card_tinh and area_tinh and card_tinh != area_tinh:
        return area
    if declared[1] == printed[1]:
        return area
    ratio = difflib.SequenceMatcher(None, _fold_street(declared[1]), _fold_street(printed[1])).ratio()
    if ratio < _STREET_SIMILARITY_MIN:
        return area
    return {**area, "diaChi": f"{declared[0]} {printed[1]}"}
