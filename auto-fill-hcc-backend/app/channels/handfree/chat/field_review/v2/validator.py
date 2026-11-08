"""Kiểm giá trị agent chuyên môn trả về — CHỈ kiểm, không tự quyết giá trị.

Đạt → giá trị ghi lên ô (với ô danh sách: đổi số thứ tự agent chọn thành đúng chữ của dòng). Không đạt → câu báo lỗi cụ
thể để agent chuyên môn đọc lại câu nói lần nữa; vẫn không đạt thì trợ lý hỏi lại công dân.
"""
import re
from dataclasses import dataclass
from datetime import date

from app.channels.handfree.chat.field_review import agent as v1
from app.channels.handfree.chat.intents import fold

_EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$")
_WEBSITE = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:/\S*)?$")
_MAX_VALUE = 300
# Ô ngày đã xảy ra (ngày sinh, ngày cấp, ngày đăng ký…) không thể ở tương lai.
_PAST_DATE_WORDS = ("sinh", "cap", "dang ky", "ket hon", "chet")


@dataclass
class Checked:
    value: str = ""
    extra: dict | None = None   # quantity / other_text cho ô bản sao, ô "Khác"
    shown: str = ""             # chữ hiển thị / đọc lại
    error: str = ""             # rỗng = đạt
    match: bool = False         # ô danh sách chưa mở: còn phải khớp với danh sách thật lúc điền


def module_of(field: dict) -> str:
    """Loại ô → mô-đun luật của agent chuyên môn (chỉ chọn luật để nạp, không đụng giá trị)."""
    label = fold(field.get("label") or "")
    if field.get("options"):
        return "lua_chon"
    if field.get("kind") == "select":
        return "lua_chon_nhap"
    if field.get("kind") == "date":
        return "ngay"
    if field.get("kind") == "number":
        return "so"
    if "email" in label or "thu dien tu" in label:
        return "email"
    if "website" in label or "trang thong tin" in label or "trang web" in label:
        return "website"
    if v1.id_lengths(field) or "quyen so" in label or "fax" in label:
        return "chu_so"
    if "noi cap" in label or "co quan cap" in label:
        return "co_quan_cap"
    if re.search(r"\bho\b.*\bten\b", label):
        return "ho_ten"
    if label.startswith("so ") or label.startswith("so:") or " so hieu" in label:
        return "so_hieu"
    if any(w in label for w in ("dia chi", "noi sinh", "noi cu tru", "que quan", "noi cap", "co quan", "noi o",
                                "thuong tru", "tam tru")):
        return "dia_chi"
    if any(w in label for w in ("noi dung", "ly do", "muc dich", "ghi chu", "de nghi")):
        return "cau_tu_do"
    return "chu"


_NUM_DIGITS = {"khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "lam": 5, "sau": 6, "bay": 7,
               "tam": 8, "chin": 9}
_NUM_WORDS = {*_NUM_DIGITS, "muoi", "tram", "nghin", "ngan", "linh", "le"}


def _read_number(tokens: list[str]) -> int | None:
    """Số tiếng Việt đọc theo hàng ("hai nghìn linh tư") hoặc từng chữ số ("hai không hai lăm")."""
    if not tokens:
        return None
    if not any(t in {"muoi", "tram", "nghin", "ngan", "linh", "le"} for t in tokens):
        return int("".join(str(_NUM_DIGITS[t]) for t in tokens))
    total, group, num = 0, 0, None
    for t in tokens:
        if t in {"nghin", "ngan"}:
            total += (group + (num if num is not None else 1)) * 1000
            group, num = 0, None
        elif t == "tram":
            group += (num if num is not None else 1) * 100
            num = None
        elif t == "muoi":
            num = num * 10 if num else 10
        elif t in {"linh", "le"}:
            num = None
        elif num is None:
            num = _NUM_DIGITS[t]
        elif num >= 10 and num % 10 == 0:
            num += _NUM_DIGITS[t]
        else:
            return None  # trộn đọc từng chữ số với đọc theo hàng: không đọc chắc được
    return total + group + (num or 0)


def spoken_years(text: str) -> set[int]:
    """Các năm công dân nói sau chữ "năm" ("năm hai nghìn linh tư", "năm 2004"). Dùng làm BẰNG CHỨNG khi kiểm giá trị
    agent trả, không dùng để tự điền."""
    tokens = re.findall(r"\d+|[^\W\d_]+", fold(text))
    years = set()
    for i, tok in enumerate(tokens):
        if tok != "nam":
            continue
        rest = tokens[i + 1:]
        if rest and rest[0].isdigit():
            if len(rest[0]) == 4:
                years.add(int(rest[0]))
            continue
        words = []
        for t in rest:
            if t not in _NUM_WORDS:
                break
            words.append(t)
        value = _read_number(words)
        if value and 1900 <= value <= 2100:
            years.add(value)
    return years


def spoken_date_digits(text: str) -> str:
    """Dãy ĐÚNG 8 chữ số công dân đọc liền từng con ("không ba không năm hai không không ba" → 03052003) — cả ngày nói
    liền không chữ "tháng". Chỉ nhận khi câu có đúng một dãy như vậy; dãy có hàng chục ("mười") thì bỏ. Là BẰNG CHỨNG
    để kiểm giá trị agent trả, không dùng để tự điền."""
    runs, run, broken = [], [], False
    for token in [*re.findall(r"\d+|[^\W\d_]+", fold(text)), ""]:
        if token in v1._DIGIT_WORDS or token.isdigit():
            run.append(v1._DIGIT_WORDS.get(token, token))
            continue
        if token in v1._NUMBER_WORDS:
            broken = True
            continue
        if run and not broken:
            runs.append("".join(run))
        run, broken = [], False
    eight = [r for r in runs if len(r) == 8]
    return eight[0] if len(eight) == 1 else ""


def _date_error(value: str, field: dict, text: str = "") -> str:
    year = int(value[-4:])
    if year < 1900:
        return f"năm {year} quá xa, có thể đọc sai năm"
    heard = spoken_years(text)
    if heard and year not in heard:
        said = ", ".join(str(y) for y in sorted(heard))
        return f'năm {year} không khớp năm công dân nói sau chữ "năm" trong câu (đọc ra {said})'
    digits = spoken_date_digits(text)
    if digits and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value) and value.replace("/", "") != digits:
        heard = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
        if v1._valid_date(heard, False, False):
            return f"{value} khác dãy chữ số công dân đọc liền ({' '.join(digits)} → {heard})"
    label = fold(field.get("label") or "")
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value)
    if m and any(w in label for w in _PAST_DATE_WORDS):
        if date(int(m.group(3)), int(m.group(2)), int(m.group(1))) > date.today():
            return f"{value} nằm ở tương lai, ô này phải là ngày đã qua"
    elif year > date.today().year + 5:
        return f"năm {year} quá xa trong tương lai"
    return ""


def evidence_error(field: dict, text: str) -> str:
    """Agent báo "thieu" / "mo_ho" mà câu nói có đủ dãy chữ số đọc từng con cho ô (số định danh 12 số, ngày 8 chữ số)
    → câu báo kèm bằng chứng để agent đọc lại; không có bằng chứng thì "" (để agent hỏi lại công dân)."""
    lengths = v1.id_lengths(field)
    if lengths:
        spoken = v1.spoken_digits(text)
        if v1._digits_ok(spoken, lengths):
            return (f"câu nói có ĐỦ dãy {len(spoken)} chữ số đọc từng con: {' '.join(spoken)} — đếm lại từng tiếng, "
                    f"trả đủ dãy đó")
        return ""
    if module_of(field) == "ngay":
        digits = spoken_date_digits(text)
        heard = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}" if digits else ""
        if heard and v1._valid_date(heard, False, False):
            return f"câu nói có đủ ngày đọc liền 8 chữ số: {' '.join(digits)} → {heard}"
    return ""


def check(field: dict, result: dict, text: str) -> Checked:
    """result: một phần tử "o" agent chuyên môn trả (đã có ket_qua == "gia_tri")."""
    raw = str(result.get("gia_tri") or "").strip()[:_MAX_VALUE]
    options = list(field.get("options") or [])
    if options:
        try:
            n = int(str(result.get("lua_chon") or 0).strip())
        except ValueError:
            n = 0
        picked = options[n - 1] if 1 <= n <= len(options) else ""
        if not picked and raw:
            # Agent ghi tên thay số thứ tự: chỉ nhận khi trùng đúng một dòng (bỏ dấu / hoa thường).
            same = [o for o in options if fold(o) == fold(raw)]
            picked = same[0] if len(same) == 1 else ""
        if not picked:
            return Checked(error=f'lựa chọn "{raw or n}" không có trong danh sách của ô')
        extra, shown = {}, picked
        if field.get("copy_choice"):
            qty = re.sub(r"\D", "", str(result.get("so_luong") or ""))
            if qty:
                extra["quantity"] = qty
                shown = f"{picked}, {qty} bản"
        other = field.get("other") or {}
        if other.get("option") == picked:
            text_other = re.sub(r"\s+", " ", str(result.get("khac") or "")).strip()
            if not text_other:
                return Checked(error=f'chọn "{picked}" thì phải có chữ ghi kèm trong khoá "khac"')
            extra["other"] = text_other
            shown = f"{picked}: {text_other}"
        return Checked(value=picked, extra=extra or None, shown=shown)
    if not raw:
        return Checked(error="giá trị rỗng")
    module = module_of(field)
    if module == "lua_chon_nhap":
        # Chưa có danh sách để kiểm: giữ tên lựa chọn công dân nói, lúc điền mở ô ra khớp với danh sách thật.
        return Checked(value=raw, shown=raw, match=True)
    if module == "ngay":
        value = v1._valid_date(raw, bool(field.get("year_only")), bool(field.get("partial_date")))
        if not value:
            return Checked(error=f'"{raw}" không phải ngày hợp lệ theo dạng của ô')
        error = _date_error(value, field, text)
        return Checked(error=error) if error else Checked(value=value, shown=value)
    if module == "so":
        value = raw.replace(",", ".")
        if not re.fullmatch(r"\d+(?:\.\d+)?", value):
            return Checked(error=f'"{raw}" không phải con số')
        return Checked(value=value, shown=value)
    if module == "email":
        value = re.sub(r"\s+", "", raw).lower()
        if not _EMAIL.match(value):
            return Checked(error=f'"{raw}" không đúng dạng địa chỉ thư điện tử')
        return Checked(value=value, shown=value)
    if module == "website":
        value = re.sub(r"^https?://", "", re.sub(r"\s+", "", raw).lower())
        if not _WEBSITE.match(value):
            return Checked(error=f'"{raw}" không đúng dạng tên miền')
        return Checked(value=value, shown=value)
    lengths = v1.id_lengths(field)
    if lengths:
        # Model đôi khi chép cả phần ghi chú của khoá nháp ("0 0 1 … (12 số)") vào giá trị → bỏ ghi chú trong ngoặc
        # trước khi đếm chữ số; chỉ dọn định dạng, không đoán giá trị.
        raw = re.sub(r"\([^)]*\)", "", raw)
        digits = re.sub(r"\D", "", raw)
        code = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
        if 9 in lengths and v1._PASSPORT.match(code) and not code.isdigit():
            return Checked(value=code, shown=code)
        spoken = v1.spoken_digits(text)
        if not v1._digits_ok(digits, lengths):
            need = " hoặc ".join(str(n) for n in lengths)
            heard = (f"; công dân đọc từng chữ số: {' '.join(spoken)} ({len(spoken)} số)"
                     if v1._digits_ok(spoken, lengths) else "")
            return Checked(error=f"dãy số có {len(digits)} chữ số, ô này cần {need} chữ số{heard}")
        if v1.phone_format_wrong(digits, lengths):
            return Checked(error="số điện thoại di động phải 10 số, bắt đầu bằng 0")
        # Đối chiếu với dãy chữ số công dân đọc từng con (nếu đọc từng con): lệch thì nhờ agent đọc lại, không tự thay.
        if v1._digits_ok(spoken, lengths) and spoken != digits:
            return Checked(error=f"dãy số trả về ({digits}) khác dãy công dân đọc từng chữ số ({spoken})")
        return Checked(value=digits, shown=digits)
    return Checked(value=raw, shown=raw)
