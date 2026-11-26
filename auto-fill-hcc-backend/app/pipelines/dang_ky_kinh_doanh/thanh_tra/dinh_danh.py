"""Thanh tra NHÂN THÂN hồ sơ đăng ký hộ kinh doanh — họ tên, số định danh, ngày sinh của chủ hộ và bên được ủy quyền.

Giấy đề nghị / giấy ủy quyền viết tay nên OCR hay lệch dấu họ tên, lệch một hai chữ số; thẻ căn cước in thì đọc chắc hơn,
và họ tên / số còn được ghi lại ở trang khác (giấy ủy quyền ghi lại chủ hộ). Bằng chứng do MÃ đếm trên các trang, không qua
một lượt LLM đọc lại cùng OCR:
- Họ tên: cách viết của A chỉ có trên trang giấy chính của người đó (giấy đề nghị với chủ hộ, giấy ủy quyền với bên được ủy
  quyền), còn trang giấy khác ghi MỘT cách viết chỉ lệch dấu ở nhiều trang hơn / ở ≥2 trang khác.
- Số định danh / ngày sinh: thẻ căn cước của chính người đó (trang thẻ có họ tên người đó) in số / ngày sinh lệch với A,
  còn số / ngày của A không có trên thẻ nào.
"""

import re
import unicodedata

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, alnum, fold, parse_date

from . import trang

# (khóa người, loại trang giấy chính, field họ tên, số, ngày sinh, tên người nói với toà)
PEOPLE = (
    ("chu_ho", "don", "ChuHo_HoTen", "ChuHo_SoDinhDanh", "ChuHo_NgaySinh", "chủ hộ"),
    ("uy_quyen", "tu_lap", "UyQuyen_NguoiDuocUyQuyen_HoTen", "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh",
     "UyQuyen_NguoiDuocUyQuyen_NgaySinh", "bên được ủy quyền"),
)
_KINDS = {"ho_ten": ("Họ tên", "literal"), "so": ("Số định danh cá nhân", "code"), "ngay_sinh": ("Ngày sinh", "date")}
UNITS = {}
for _key, _, _name, _id, _dob, _who in PEOPLE:
    for _part, _field in (("ho_ten", _name), ("so", _id), ("ngay_sinh", _dob)):
        _label, _kind = _KINDS[_part]
        UNITS[_field] = Unit(f"{_key}_{_part}", f"{_label} của {_who}", (Field(_field, _label, _kind),))
_OWNER = {field: who for _, _, *fields, who in PEOPLE for field in fields}

RULES = """
<nhan_than>
Nguồn chắc nhất là thẻ căn cước in của chính người đó, rồi tới các trang giấy khác cùng ghi người đó (giấy ủy quyền ghi lại
chủ hộ, giấy đề nghị ghi lại người được ủy quyền), cuối cùng là dòng viết tay của giấy chính. Tín hiệu mã nêu cách viết họ
tên của A chỉ có trên dòng viết tay của giấy chính, còn trang giấy khác ghi cách viết của B (chỉ khác dấu) ở nhiều trang hơn
→ chọn B. Thẻ căn cước của chính người đó in số định danh / ngày sinh của B, còn số / ngày của A không có trên thẻ nào →
chọn B. Dòng chứng cứ thuộc người khác → KHONG_DU_CAN_CU.
</nhan_than>
"""


def _windows(page: dict, size: int) -> list[tuple[str, str]]:
    """(khóa họ tên, dòng) của mọi cụm ``size`` chữ trên trang."""
    out = []
    for line in page["lines"]:
        words = trang.words(line).split()
        out += [(" ".join(words[at:at + size]), line) for at in range(len(words) - size + 1)]
    return out


def _spelled(key: str, line: str) -> str:
    """Cách viết trên chính dòng OCR của cụm có khóa ``key`` (khóa đã chuẩn vị trí dấu thanh, không đọc được như chữ)."""
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", line))
    size = len(key.split())
    for at in range(len(words) - size + 1):
        window = " ".join(words[at:at + size])
        if " ".join(trang.words(window).split()) == key:
            return window
    return ""


def name_finding(name, primary: str, page_list: list[dict]) -> tuple[str, str, int, str] | None:
    """(cách viết đúng, dòng chứng cứ, số tài liệu, lý do) khi họ tên của A lệch dấu so với trang giấy khác."""
    target = " ".join(trang.words(name).split())
    size = len(target.split())
    if size < 2:
        return None
    folded = fold(target)
    mine = {"trang": 0, "ngoai": 0}
    found: dict[str, dict] = {}
    for at, page in enumerate(page_list):
        if page["kind"] == "khac":
            continue
        hits = {key: line for key, line in _windows(page, size) if fold(key) == folded}
        outside = page["kind"] != primary
        for key, line in hits.items():
            if key == target:
                mine["trang"] += 1
                mine["ngoai"] += outside
                continue
            stat = found.setdefault(key, {"trang": set(), "ngoai": set(), "line": line, "doc": page["doc"]})
            stat["trang"].add(at)
            if outside:
                stat["ngoai"].add(at)
                stat["line"], stat["doc"] = line, page["doc"]
    if mine["ngoai"] or not found:
        return None
    ranked = sorted(found.items(), key=lambda item: (len(item[1]["ngoai"]), len(item[1]["trang"])), reverse=True)
    best, stat = ranked[0]
    outside, count = len(stat["ngoai"]), len(stat["trang"])
    if not outside or (count <= mine["trang"] and outside < 2):
        return None
    if len(ranked) > 1 and (len(ranked[1][1]["ngoai"]), len(ranked[1][1]["trang"])) == (outside, count):
        return None
    spelled = _spelled(best, stat["line"])
    if not spelled:
        return None
    return spelled, stat["line"], stat["doc"], (
        f'họ tên "{name}" của A chỉ có trên trang giấy chính ({mine["trang"]} trang); {count} trang ({outside} trang giấy '
        f'khác) ghi "{spelled}", chỉ khác dấu')


def _card_pages(name, page_list: list[dict]) -> list[dict]:
    """Trang thẻ căn cước có họ tên (bỏ dấu) của người này."""
    target = fold(" ".join(trang.words(name).split()))
    size = len(target.split())
    if size < 2:
        return []
    return [page for page in page_list if page["kind"] == "ban_in"
            and any(fold(key) == target for key, _ in _windows(page, size))]


def id_year(number) -> int | None:
    """Năm sinh mã hoá trong số định danh 12 chữ số: chữ số thứ 4 là thế kỷ + giới tính (0/1 → 19xx, 2/3 → 20xx), chữ số
    5–6 là hai số cuối của năm."""
    digits = trang.digits(number)
    if len(digits) != 12:
        return None
    return 1900 + 100 * (int(digits[3]) // 2) + int(digits[4:6])


def number_finding(name, number, page_list: list[dict], birth=None) -> tuple[str, str, int, str] | None:
    """Thẻ của chính người đó in một số 12 chữ số lệch 1–2 chữ số với số của A, số của A không có trên thẻ nào. Biết ngày
    sinh thì số trên thẻ phải mang đúng năm sinh đó (OCR thẻ cũng có thể đọc lệch)."""
    mine = trang.digits(number)
    cards = _card_pages(name, page_list)
    if len(mine) != 12 or not cards:
        return None
    if any(mine in alnum(line) for page in page_list if page["kind"] == "ban_in" for line in page["lines"]):
        return None
    seen: dict[str, tuple[str, int]] = {}
    for page in cards:
        for line in page["lines"]:
            for other in re.findall(r"(?<!\d)\d{12}(?!\d)", re.sub(r"(?<=\d)[ .](?=\d)", "", line)):
                year = parse_date(birth).year if parse_date(birth) else None
                if 1 <= sum(a != b for a, b in zip(other, mine)) <= 2 and (year is None or id_year(other) == year):
                    seen.setdefault(other, (line, page["doc"]))
    if len(seen) != 1:
        return None
    other, (line, doc) = next(iter(seen.items()))
    return other, line, doc, f'thẻ căn cước của chính người này in số {other}; số "{mine}" của A không có trên thẻ nào'


_DOB_LINE = re.compile(r"(?i)sinh|birth")
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})(?!\d)")


def date_finding(name, value, page_list: list[dict], number=None) -> tuple[str, str, int, str] | None:
    """Thẻ của chính người đó in ngày sinh khác ngày của A, ngày của A không có trên thẻ nào. Năm sinh trên thẻ phải khớp
    năm mã hoá trong số định danh (số in trên thẻ đó, không có thì số của A) — OCR thẻ cũng có thể đọc lệch chữ số."""
    mine = parse_date(value)
    cards = _card_pages(name, page_list)
    if not mine or not cards:
        return None
    seen: dict[str, tuple[str, int]] = {}
    for page in page_list:
        if page["kind"] != "ban_in":
            continue
        for line in page["lines"]:
            for match in _DATE_RE.finditer(line):
                if parse_date("/".join(match.groups())) == mine:
                    return None
    for page in cards:
        printed = {other for line in page["lines"]
                   for other in re.findall(r"(?<!\d)\d{12}(?!\d)", re.sub(r"(?<=\d)[ .](?=\d)", "", line))}
        year = id_year(next(iter(printed))) if len(printed) == 1 else id_year(number)
        if year is None:
            continue
        for line in page["lines"]:
            if not _DOB_LINE.search(line):
                continue
            for match in _DATE_RE.finditer(line):
                parsed = parse_date("/".join(match.groups()))
                if parsed and parsed != mine and parsed.year == year:
                    seen.setdefault(parsed.strftime("%d/%m/%Y"), (line, page["doc"]))
    if len(seen) != 1:
        return None
    other, (line, doc) = next(iter(seen.items()))
    return other, line, doc, f'thẻ căn cước của chính người này in ngày sinh {other}; ngày "{value}" của A không có trên thẻ nào'


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    page_list = trang.pages(case.documents, case.values)
    out = []
    for _, primary, name_field, id_field, dob_field, who in PEOPLE:
        name = case.values.get(name_field)
        if not str(name or "").strip():
            continue
        for field, hit in ((name_field, name_finding(name, primary, page_list)),
                           (id_field, number_finding(name, case.values.get(id_field), page_list,
                                                     case.values.get(dob_field))),
                           (dob_field, date_finding(name, case.values.get(dob_field), page_list,
                                                    case.values.get(id_field)))):
            if not hit:
                continue
            value, line, doc, why = hit
            out.append(Finding(INSPECTOR, UNITS[field], {field: value}, line, doc, "dòng giấy ghi người này", who,
                               backed=True, evidence=(why,)))
    return out


_OWNERS = tuple(who for *_, who in PEOPLE)
INSPECTOR = Inspector("dinh_danh", "NHÂN THÂN (họ tên, số định danh, ngày sinh) chủ hộ, bên được ủy quyền",
                      tuple(UNITS.values()), RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
