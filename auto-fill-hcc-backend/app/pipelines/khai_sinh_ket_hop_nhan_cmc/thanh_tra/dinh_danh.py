"""Thanh tra ĐỊNH DANH hồ sơ khai sinh kết hợp nhận cha, mẹ, con: họ tên, số định danh, ngày sinh của cha, mẹ, người yêu
cầu; họ tên trẻ.

Mã thuần, không qua LLM; mỗi người soát trên chính field lượt trích của người đó (thủ tục không có bước phân vai):
1. Họ tên: mọi cách viết có nguyên văn trên giấy — cùng chữ cái khác dấu, hoặc (người có số định danh) lệch một hai chữ cái
   trên trang mang số định danh của người đó — đếm số TRANG ghi; nhiều trang hơn thắng, bằng nhau theo hạng nguồn (giấy in
   cơ quan cấp > tờ khai > giấy tự lập). Lượt trích hay chép lệch dấu tên hiếm gặp sang tên thông dụng dù OCR đọc đúng; chặn
   bản rơi dấu / "Đ" thành "D"; chặn đổi chữ cái khi chữ cái của lượt trích đã có trên giấy ngoài tờ khai. Tên trẻ chỉ xét
   cách viết khác dấu.
2. Số định danh, ngày sinh: vùng MRZ mặt sau thẻ mang họ tên (không dấu) của người đó, năm sinh mã hoá trong số khớp năm
   sinh in ở MRZ. Ô số định danh chỉ nhận số căn cước 12 chữ số.
"""

import re
from dataclasses import dataclass, replace

from app.pipelines._shared.cccd import id_birth_year, mrz_records
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import close_name
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

from . import trang


@dataclass(frozen=True)
class Person:
    key: str
    label: str
    name: str
    number: str = ""
    birth: str = ""


PERSONS = (
    Person("cha", "cha của trẻ", "Father_FullName", "Father_IdNumber", "Father_BirthDate"),
    Person("me", "mẹ của trẻ", "Mother_FullName", "Mother_IdNumber", "Mother_BirthDate"),
    Person("nyc", "người yêu cầu", "Requester_FullName", "Requester_IdNumber", "Requester_BirthDate"),
)
# Tên trẻ: mapper lấy tên dự định trên tờ khai trước, rồi tên trên giấy chứng sinh — soát đúng field đang lên form.
CHILD = (Person("con", "trẻ được khai sinh", "Child_FullName"),
         Person("con", "trẻ được khai sinh", "Child_NameOnBirthCertificate"))


def _units(person: Person) -> dict[str, Unit]:
    units = {"ho_ten": Unit(f"{person.key}.ho_ten", f"Họ tên {person.label}",
                            (Field(person.name, "họ, chữ đệm, tên", canon=trang.name_key),))}
    if person.number:
        units["so_dinh_danh"] = Unit(f"{person.key}.so_dinh_danh", f"Số định danh {person.label}",
                                     (Field(person.number, "số định danh 12 chữ số", "code"),))
    if person.birth:
        units["ngay_sinh"] = Unit(f"{person.key}.ngay_sinh", f"Ngày sinh {person.label}",
                                  (Field(person.birth, "ngày sinh dd/mm/yyyy", "date"),))
    return units


_UNITS = {**{p.key: _units(p) for p in PERSONS},
          **{f"con:{p.name}": _units(p) for p in CHILD}}
UNITS = tuple(unit for units in _UNITS.values() for unit in units.values())

RULES = """
<ho_ten>
Mỗi vụ xét họ tên của MỘT người (cha, mẹ, người yêu cầu hoặc trẻ — nêu ở tên mục). Mã đã đếm số TRANG giấy ghi nguyên văn
từng cách viết (dòng "TỔNG số trang" trong tín hiệu mã). B được nhiều trang ghi hơn A → chọn B; số trang bằng nhau thì theo
hạng: giấy in cơ quan cấp (giấy chứng sinh, CCCD, hộ chiếu, giấy khai sinh) > tờ khai (đăng ký khai sinh, đăng ký nhận cha,
mẹ, con — viết tay) > giấy người dân tự lập. Hai cách viết chỉ khác DẤU là chuyện thường (lượt trích chép lệch dấu, OCR đọc
lệch dấu chữ viết tay), KHÔNG phải lý do giữ A; A không có trên trang nào thì càng không giữ. Mã đã tự loại cách viết là
bản rơi dấu của A, chữ Đ đọc thành D, và cách viết đổi chữ cái khi chữ cái của A đã có trên giấy ngoài tờ khai. Dòng trích
dẫn là họ tên của người khác (không phải người nêu ở tên mục) → KHONG_DU_CAN_CU.
</ho_ten>

<so_ngay>
Số định danh / ngày sinh lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của đúng người đó, năm sinh trong số khớp ngày
sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số viết tay. Ô số định danh chỉ nhận số căn cước 12 chữ số:
A là số CMND 9 số / số thiếu chữ số → chọn B (số trên thẻ của chính người đó).
</so_ngay>
"""


def _finding(person: Person, unit: str, value: str, quote: str, doc: int, note: str, evidence: str) -> Finding:
    target = _UNITS[person.key if person.key != "con" else f"con:{person.name}"][unit]
    return Finding(INSPECTOR, target, {target.fields[0].name: value}, quote, doc, note, person.label, backed=True,
                   evidence=(evidence,))


def _line_with(documents: list[dict], test) -> tuple[str, int]:
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if line.strip() and test(line):
                return line.strip(), index
    return "", 0


def name_finding(person: Person, values: dict, page_list: list[dict]) -> Finding | None:
    current = " ".join(str(values.get(person.name) or "").split())
    target = fold(current).split()
    if len(target) < 2:
        return None
    ours = trang.name_key(current)
    number = trang.digits(values.get(person.number)) if person.number else ""
    candidates: dict[str, dict] = {}
    for page in page_list:
        if page["kind"] == "to_khai":
            continue
        anchored = len(number) >= 9 and number in trang.digits(" ".join(page["lines"]))
        for line in page["lines"]:
            tokens = trang.WORD_RE.findall(line)
            for start in range(len(tokens) - len(target) + 1):
                window = " ".join(tokens[start:start + len(target)])
                key = trang.name_key(window)
                letters = fold(window).split()
                if key == ours:
                    continue
                if key in candidates:
                    # Người yêu cầu hay đồng thời là cha / mẹ: dòng đầu tìm thấy có thể là mục của vai kia — trích dòng
                    # trên giấy mang số định danh của chính người này để toà thấy đúng người.
                    if anchored and not candidates[key]["anchored"]:
                        candidates[key].update(quote=line, doc=page["doc"], anchored=True)
                    continue
                if letters == target:
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": False,
                                       "anchored": anchored}
                elif anchored and letters[0] == target[0] and close_name(window, current):
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": True,
                                       "anchored": True}
    if not candidates:
        return None
    mine = trang.support(current, page_list)
    target_words = f" {' '.join(target)} "
    letters_on_paper = any(target_words in f" {' '.join(fold(line).split())} "
                           for page in page_list if page["kind"] != "to_khai" for line in page["lines"])
    winners = []
    for key, cand in candidates.items():
        if not cand["letters"] and (base._adds_marks(key, ours) or base._lost_stroke(key, ours)):
            continue  # đề xuất chỉ là bản rơi dấu / mất nét "Đ" của lượt trích
        if cand["letters"] and letters_on_paper:
            continue
        stat = trang.support(cand["name"], page_list)
        if stat["ban_in"] + stat["the"] + stat["tu_lap"] < 1 or trang.rank(stat) <= trang.rank(mine):
            continue
        # Chỉ khác dấu mà căn cứ in duy nhất là dòng họ tên in hoa trên thẻ: OCR hay đọc lệch dấu chữ in hoa.
        if not cand["letters"] and stat["ban_in"] + stat["tu_lap"] < 1:
            continue
        winners.append((trang.rank(stat), key, cand, stat))
    winners.sort(key=lambda item: item[0], reverse=True)
    if not winners or (len(winners) > 1 and winners[0][0] == winners[1][0]):
        return None
    _, _, cand, best = winners[0]
    return _finding(person, "ho_ten", cand["name"], cand["quote"], cand["doc"], f"giấy ghi họ tên {person.label}",
                    f"TỔNG số trang ghi nguyên văn: B {best['trang']}, A {mine['trang']}. B: {best['ban_in']} giấy in cơ "
                    f"quan cấp, {best['the']} dòng họ tên thẻ, {best['tu_lap']} giấy tự lập, {best['to_khai']} tờ khai; "
                    f"A: {mine['ban_in']} giấy in cơ quan cấp, {mine['the']} dòng thẻ, {mine['tu_lap']} giấy tự lập, "
                    f"{mine['to_khai']} tờ khai"
                    + ("; dòng trích dẫn nằm trên trang giấy mang đúng số định danh của người này" if cand["anchored"]
                       else ""))


def _card(person: Person, values: dict, documents: list[dict]) -> dict | None:
    """Thẻ của người này: MRZ mang họ tên (không dấu) của người đó, năm sinh trong số khớp năm sinh in ở MRZ."""
    name = " ".join(fold(values.get(person.name)).split())
    if not name:
        return None
    cards = [card for document in documents for card in mrz_records(document.get("text"))]
    cards = [card for card in cards if card.get("name") == name and card.get("birth")
             and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]]
    return cards[0] if len({card["id"] for card in cards}) == 1 else None


def card_findings(person: Person, values: dict, documents: list[dict]) -> list[Finding]:
    card = _card(person, values, documents) if person.number else None
    if not card:
        return []
    out = []
    current = trang.digits(values.get(person.number))
    if current != card["id"]:
        quote, doc = _line_with(documents, lambda line: bool(re.search(rf"I[DO]VNM\S*{card['id']}",
                                                                       re.sub(r"\s+", "", line))))
        if quote:
            out.append(_finding(person, "so_dinh_danh", card["id"], quote, doc, f"dòng MRZ mặt sau thẻ của {person.label}",
                                "vùng MRZ của thẻ mang họ tên (không dấu) của người này, năm sinh trong số khớp ngày "
                                "sinh in ở MRZ" + ("; số của A không đủ 12 chữ số" if len(current) != 12 else "")))
    year = id_birth_year(card["id"])
    yy, mm, dd = card["birth"]
    birth = f"{dd:02d}/{mm:02d}/{year}" if year and year % 100 == yy else ""
    pattern = rf"(?<!\d)0?{dd}\s*[/.-]\s*0?{mm}\s*[/.-]\s*{year}(?!\d)"
    if birth and parse_date(values.get(person.birth)) != parse_date(birth):
        line, at = _line_with(documents, lambda text: bool(re.search(pattern, text)))
        if line:
            out.append(_finding(person, "ngay_sinh", birth, line, at, f"ngày sinh in trên thẻ của {person.label}",
                                "ngày sinh khớp ngày sinh mã hoá ở MRZ thẻ của người này"))
    return out


def _same_as(person: Person, values: dict) -> str:
    """Người yêu cầu mang cùng số định danh với cha / mẹ → nhãn vai kia (cùng một người, dòng trích dẫn hay là mục của vai
    kia trên giấy)."""
    number = trang.digits(values.get(person.number))
    if person.key != "nyc" or len(number) < 9:
        return ""
    return next((other.label for other in PERSONS
                 if other.key != "nyc" and trang.digits(values.get(other.number)) == number), "")


def findings_from(case: Case) -> list[Finding]:
    page_list = trang.pages(case.documents)
    out = []
    for person in PERSONS:
        name = name_finding(person, case.values, page_list)
        same = _same_as(person, case.values) if name else ""
        if same:
            name = replace(name, evidence=(*name.evidence, f"{person.label} mang cùng số định danh với {same}: cùng một "
                                                           f"người, dòng ghi họ tên {same} cũng là họ tên người này"))
        out += [*([name] if name else []), *card_findings(person, case.values, case.documents)]
    child = next((person for person in CHILD if str(case.values.get(person.name) or "").strip()), None)
    name = name_finding(child, case.values, page_list) if child else None
    return out + ([name] if name else [])


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


_OWNERS = tuple(dict.fromkeys(person.label for person in (*PERSONS, *CHILD)))
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH cha, mẹ, người yêu cầu, trẻ (họ tên, số định danh, ngày sinh)", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
