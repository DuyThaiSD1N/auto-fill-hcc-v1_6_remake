"""Thanh tra ĐỊNH DANH hồ sơ xác định mức độ khuyết tật: người khuyết tật (họ tên, số định danh, ngày sinh, giới tính) và
người đại diện (họ tên, số định danh, ngày sinh, mối quan hệ với người khuyết tật).

Mã thuần, không qua LLM; mỗi người soát trên chính field lượt trích của người đó. Chủ hồ sơ luôn là người khuyết tật và người
nộp là một trong hai người này nên kết quả được chép sang các khối đó ở bước dựng bản vá (__init__.sync), không soát lại.
1. Họ tên: mọi cách viết có nguyên văn trên giấy — cùng chữ cái khác dấu, hoặc (người có số định danh) lệch một hai chữ cái
   trên trang mang số định danh của người đó — đếm số TRANG ghi; nhiều trang hơn thắng, bằng nhau theo hạng nguồn (giấy in
   cơ quan cấp > đơn đề nghị viết tay > giấy tự lập). Chặn bản rơi dấu / "Đ" thành "D"; chặn đổi chữ cái khi chữ cái của
   lượt trích đã có trên giấy ngoài đơn (cách viết khác chữ thường là người khác trong gia đình).
2. Số định danh, ngày sinh, giới tính: vùng MRZ mặt sau thẻ mang họ tên (không dấu) của người đó, năm sinh mã hoá trong số
   khớp năm sinh in ở MRZ.
3. Mối quan hệ: chữ đứng sau nhãn "Mối quan hệ với người được xác định khuyết tật" ở mục II của đơn.
"""

import re
from dataclasses import dataclass

from app.pipelines._shared.cccd import id_birth_year, mrz_records
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import _edit, close_name
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

from ..process import mapper
from . import trang


@dataclass(frozen=True)
class Person:
    key: str
    label: str
    name: str
    number: str
    birth: str
    gender: str = ""


NKT = Person("nkt", "người khuyết tật", "Nkt_HoTen", "Nkt_SoDinhDanh", "Nkt_NgaySinh", "Nkt_GioiTinh")
NDD = Person("ndd", "người đại diện", "Ndd_HoTen", "Ndd_SoDinhDanh", "Ndd_NgaySinh")
PERSONS = (NKT, NDD)


def _relation_key(value) -> str:
    return mapper._relation(value) or ""


def _units(person: Person) -> dict[str, Unit]:
    units = {
        "ho_ten": Unit(f"{person.key}.ho_ten", f"Họ tên {person.label}",
                       (Field(person.name, "họ, chữ đệm, tên", canon=trang.name_key),)),
        "so_dinh_danh": Unit(f"{person.key}.so_dinh_danh", f"Số định danh {person.label}",
                             (Field(person.number, "số định danh 12 chữ số", "code"),)),
        "ngay_sinh": Unit(f"{person.key}.ngay_sinh", f"Ngày sinh {person.label}",
                          (Field(person.birth, "ngày sinh dd/mm/yyyy", "date"),)),
    }
    if person.gender:
        units["gioi_tinh"] = Unit(f"{person.key}.gioi_tinh", f"Giới tính {person.label}",
                                  (Field(person.gender, '"Nam" hoặc "Nữ"', "free", canon=fold),))
    if person is NDD:
        units["quan_he"] = Unit("ndd.quan_he", "Mối quan hệ của người đại diện với người khuyết tật",
                                (Field("Ndd_QuanHe", "người đại diện là gì của người khuyết tật", "free",
                                       canon=_relation_key),))
    return units


_UNITS = {person.key: _units(person) for person in PERSONS}
UNITS = tuple(unit for units in _UNITS.values() for unit in units.values())

RULES = """
<ho_ten>
Mỗi vụ xét họ tên của MỘT người (người khuyết tật hoặc người đại diện — nêu ở tên mục). Mã đã đếm số TRANG giấy ghi nguyên văn
từng cách viết (dòng "TỔNG số trang" trong tín hiệu mã). B được nhiều trang ghi hơn A → chọn B; số trang bằng nhau thì theo
hạng: giấy in cơ quan cấp (CCCD, giấy khai sinh, giấy ra viện / bệnh án của cơ sở y tế) > đơn đề nghị (viết tay) > giấy người
dân tự lập. Hai cách viết chỉ khác DẤU là chuyện thường (OCR đọc lệch dấu chữ viết tay), KHÔNG phải lý do giữ A. Dòng trích
dẫn là họ tên của người khác (không phải người nêu ở tên mục) → KHONG_DU_CAN_CU.
</ho_ten>

<so_ngay>
Số định danh / ngày sinh / giới tính lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của đúng người đó, năm sinh trong số
khớp ngày sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số viết tay. Ô số định danh chỉ nhận số căn cước 12
chữ số: A là số CMND 9 số / số thiếu chữ số → chọn B (số trên thẻ của chính người đó).
</so_ngay>

<quan_he>
Mối quan hệ là người đại diện LÀ GÌ của người khuyết tật, theo đúng chữ đơn ghi sau nhãn "Mối quan hệ với người được xác định
khuyết tật" ở mục II (dòng trích dẫn). A đảo chiều (đơn ghi "con" mà A là "Cha") hoặc khác chữ đơn ghi → chọn B.
</quan_he>
"""


def _finding(person: Person, unit: str, value: str, quote: str, doc: int, note: str, evidence: str) -> Finding:
    target = _UNITS[person.key][unit]
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
    number = trang.digits(values.get(person.number))
    candidates: dict[str, dict] = {}
    for page in page_list:
        if page["kind"] == "don":
            continue
        anchored = len(number) >= 9 and number in trang.digits(" ".join(page["lines"]))
        for line in page["lines"]:
            tokens = trang.WORD_RE.findall(line)
            for start in range(len(tokens) - len(target) + 1):
                window = " ".join(tokens[start:start + len(target)])
                key = trang.name_key(window)
                letters = fold(window).split()
                if key == ours or key in candidates:
                    continue
                if letters == target:
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": False}
                elif anchored and letters[0] == target[0] and close_name(window, current):
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": True}
    if not candidates:
        return None
    mine = trang.support(current, page_list)
    target_words = f" {' '.join(target)} "
    letters_on_paper = any(target_words in f" {' '.join(fold(line).split())} "
                           for page in page_list if page["kind"] != "don" for line in page["lines"])
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
                    f"quan cấp, {best['the']} dòng họ tên thẻ, {best['tu_lap']} giấy tự lập, {best['don']} đơn đề nghị; "
                    f"A: {mine['ban_in']} giấy in cơ quan cấp, {mine['the']} dòng thẻ, {mine['tu_lap']} giấy tự lập, "
                    f"{mine['don']} đơn đề nghị")


def _card(person: Person, values: dict, documents: list[dict]) -> dict | None:
    """Thẻ của người này: MRZ mang họ tên (không dấu) của người đó, năm sinh trong số khớp năm sinh in ở MRZ, và thẻ không
    trái với người đó — lượt trích đã có số mà số thẻ lệch quá 2 chữ số, đồng thời năm sinh khác, là thẻ của người khác
    trùng họ tên (mẹ và con trong hồ sơ trẻ em hay trùng tên)."""
    name = " ".join(fold(values.get(person.name)).split())
    if not name:
        return None
    number = trang.digits(values.get(person.number))
    born = parse_date(values.get(person.birth))
    cards = [card for document in documents for card in mrz_records(document.get("text"))]
    cards = [card for card in cards if card.get("name") == name and card.get("birth")
             and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]
             and not (len(number) >= 9 and _edit(number, card["id"]) > 2
                      and born and born.year != id_birth_year(card["id"]))]
    return cards[0] if len({card["id"] for card in cards}) == 1 else None


def card_findings(person: Person, values: dict, documents: list[dict]) -> list[Finding]:
    card = _card(person, values, documents)
    if not card:
        return []
    out = []
    how = "vùng MRZ của thẻ mang họ tên (không dấu) của người này, năm sinh trong số khớp ngày sinh in ở MRZ"
    current = trang.digits(values.get(person.number))
    if current != card["id"]:
        quote, doc = _line_with(documents, lambda line: bool(re.search(rf"I[DO]VNM\S*{card['id']}",
                                                                       re.sub(r"\s+", "", line))))
        if quote:
            out.append(_finding(person, "so_dinh_danh", card["id"], quote, doc, f"dòng MRZ mặt sau thẻ của {person.label}",
                                how + ("; số của A không đủ 12 chữ số" if len(current) != 12 else "")))
    year = id_birth_year(card["id"])
    yy, mm, dd = card["birth"]
    birth = f"{dd:02d}/{mm:02d}/{year}" if year and year % 100 == yy else ""
    pattern = rf"(?<!\d)0?{dd}\s*[/.-]\s*0?{mm}\s*[/.-]\s*{year}(?!\d)"
    if birth and parse_date(values.get(person.birth)) != parse_date(birth):
        line, at = _line_with(documents, lambda text: bool(re.search(pattern, text)))
        if line:
            out.append(_finding(person, "ngay_sinh", birth, line, at, f"ngày sinh in trên thẻ của {person.label}",
                                "ngày sinh khớp ngày sinh mã hoá ở MRZ thẻ của người này"))
    gender = card.get("gender")
    if person.gender and gender and fold(gender) != fold(values.get(person.gender)):
        line, at = _line_with(documents, lambda text: bool(re.search(rf"I[DO]VNM\S*{card['id']}",
                                                                     re.sub(r"\s+", "", text))))
        if line:
            out.append(_finding(person, "gioi_tinh", gender, line, at, f"giới tính in ở MRZ thẻ của {person.label}", how))
    return out


_RELATION_LINE_RE = re.compile(r"(?i)quan\s*h[eệ]\s*v[oớ]i\s*ng[uư][oờ]i\s*(?:[đd][uư][oợ]c\s*x[aá]c\s*[đd][iị]nh\s*)?"
                               r"(?:m[uứ]c\s*[đd][oộ]\s*)?khuy[eế]t\s*t[aậ]t\s*:\s*(.*)")


def relation_finding(values: dict, page_list: list[dict]) -> Finding | None:
    """Chữ sau nhãn mối quan hệ ở mục II của đơn (đơn đánh máy / viết rõ): khác hẳn lượt trích → đề xuất chữ trên đơn. Đơn
    có nhiều dòng như thế mà ghi khác nhau, hay chữ không thuộc danh sách quan hệ, thì không chắc → bỏ."""
    found: dict[str, tuple[str, str, int]] = {}
    for page in page_list:
        if page["kind"] != "don":
            continue
        for line in page["lines"]:
            match = _RELATION_LINE_RE.search(line)
            text = (match.group(1) if match else "").strip(" .…:-")
            label = mapper._relation(text) if text else None
            if label:
                found.setdefault(label, (text, line, page["doc"]))
    if len(found) != 1:
        return None
    label, (text, line, doc) = next(iter(found.items()))
    if mapper._relation(values.get("Ndd_QuanHe")) == label:
        return None
    return _finding(NDD, "quan_he", text, line, doc, "dòng mối quan hệ ở mục II của đơn",
                    f'đơn ghi "{text}" sau nhãn mối quan hệ (ra "{label}" trong danh sách quan hệ của cổng)')


def findings_from(case: Case) -> list[Finding]:
    page_list = trang.pages(case.documents)
    out = []
    for person in PERSONS:
        name = name_finding(person, case.values, page_list)
        out += [*([name] if name else []), *card_findings(person, case.values, case.documents)]
    relation = relation_finding(case.values, page_list)
    return out + ([relation] if relation else [])


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


_OWNERS = tuple(person.label for person in PERSONS)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH người khuyết tật, người đại diện (họ tên, số định danh, ngày sinh, quan hệ)",
                      UNITS, RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
