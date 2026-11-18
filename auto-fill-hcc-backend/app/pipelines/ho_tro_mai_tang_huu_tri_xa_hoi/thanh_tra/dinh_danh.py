"""Thanh tra ĐỊNH DANH hồ sơ mai táng hưu trí xã hội: người đứng ra mai táng, người nộp, người chết — họ tên, số
định danh, ngày sinh, giới tính.

Mã thuần, không qua LLM; mỗi người soát trên chính field lượt trích của người đó:
1. Họ tên: mọi cách viết có nguyên văn trên giấy — cùng chữ cái khác dấu, hoặc (người có số định danh) lệch một hai chữ cái
   trên trang mang số định danh của người đó — đếm số TRANG ghi; nhiều trang hơn thắng, bằng nhau theo hạng nguồn (giấy in
   cơ quan cấp > văn bản đề nghị viết tay > giấy tự lập). Chặn bản rơi dấu / "Đ" thành "D"; chặn đổi chữ cái khi chữ cái
   của lượt trích đã có trên giấy ngoài văn bản đề nghị (cách viết khác chữ thường là người khác trong gia đình).
2. Số định danh, ngày sinh, giới tính: vùng MRZ mặt sau thẻ mang họ tên (không dấu) của người đó, năm sinh mã hoá trong số
   khớp năm sinh in ở MRZ; thẻ trùng tên mà số lệch xa và năm sinh khác là thẻ người khác.
"""

import re
from dataclasses import dataclass

from app.pipelines._shared.cccd import id_birth_year, mrz_records
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import _edit, close_name
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

from . import trang


@dataclass(frozen=True)
class Person:
    key: str
    label: str
    prefix: str

    @property
    def name(self) -> str:
        return f"{self.prefix}_HoTen"

    @property
    def number(self) -> str:
        return f"{self.prefix}_SoDinhDanh"

    @property
    def birth(self) -> str:
        return f"{self.prefix}_NgaySinh"

    @property
    def gender(self) -> str:
        return f"{self.prefix}_GioiTinh"

    @property
    def issued(self) -> str:
        return f"{self.prefix}_NgayCap"


PERSONS = (
    Person("chu_ho_so", "người đứng ra mai táng", "ChuHoSo"),
    Person("nguoi_nop", "người nộp", "NguoiNop"),
    # Chỉ có field khi tài khoản khai người chết làm chủ hồ sơ (cờ deceasedAsOwner / công tắc theo tờ khai).
    Person("nguoi_chet", "người chết", "NguoiMat"),
)


def _units(person: Person) -> dict[str, Unit]:
    return {
        "ho_ten": Unit(f"{person.key}.ho_ten", f"Họ tên {person.label}",
                       (Field(person.name, "họ, chữ đệm, tên", canon=trang.name_key),)),
        "so_dinh_danh": Unit(f"{person.key}.so_dinh_danh", f"Số định danh {person.label}",
                             (Field(person.number, "số định danh 12 chữ số", "code"),)),
        "ngay_sinh": Unit(f"{person.key}.ngay_sinh", f"Ngày sinh {person.label}",
                          (Field(person.birth, "ngày sinh dd/mm/yyyy", "date"),)),
        "gioi_tinh": Unit(f"{person.key}.gioi_tinh", f"Giới tính {person.label}",
                          (Field(person.gender, '"Nam" hoặc "Nữ"', "free", canon=fold),)),
        "ngay_cap": Unit(f"{person.key}.ngay_cap", f"Ngày cấp giấy tờ định danh {person.label}",
                         (Field(person.issued, "ngày cấp dd/mm/yyyy", "date"),)),
    }


_UNITS = {person.key: _units(person) for person in PERSONS}
UNITS = tuple(unit for units in _UNITS.values() for unit in units.values())

RULES = """
<ho_ten>
Mỗi vụ xét họ tên của MỘT người (người đứng ra mai táng, người nộp hoặc người chết — nêu ở tên mục). Mã đã đếm số TRANG giấy
ghi nguyên văn từng cách viết (dòng "TỔNG số trang" trong tín hiệu mã). B được nhiều trang ghi hơn A → chọn B; số trang bằng
nhau thì theo hạng: giấy in cơ quan cấp (CCCD, giấy khai sinh) > văn bản đề nghị (viết tay) > giấy người dân tự lập. Hai
cách viết chỉ khác DẤU là chuyện thường (OCR đọc lệch dấu chữ viết tay), KHÔNG phải lý do giữ A. Dòng trích dẫn là họ tên
của người khác (không phải người nêu ở tên mục) → KHONG_DU_CAN_CU. Họ tên A chỉ có trên đơn viết tay còn thẻ của chính
người đó (mã nhận theo ngày sinh in ở MRZ trùng ngày sinh A, cùng họ và chữ đệm, số gần số A) ghi B → chọn B: OCR đọc sai
chữ viết tay của đơn.
</ho_ten>

<so_ngay>
Số định danh / ngày sinh / giới tính lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của đúng người đó, năm sinh trong số
khớp ngày sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số viết tay. Ô số định danh chỉ nhận số căn cước 12
chữ số: A là số CMND 9 số / số thiếu chữ số → chọn B (số trên thẻ của chính người đó).
</so_ngay>

<ngay_cap>
Ngày cấp: mã chấm ĐIỂM từng ngày ghi cho người này (dòng thuộc khối tờ khai của người đó, hoặc cùng dòng số định danh của
người đó) — mỗi dòng ghi trên giấy IN (thẻ căn cước, trích lục, hợp đồng dịch vụ tang lễ…) 2 điểm, dòng viết tay (tờ khai,
dòng chấm điền) / giấy tự lập 1 điểm. B được nhiều nguồn ghi hơn A (điểm cao hơn) → chọn B: OCR hay đọc lệch một chữ số.
</ngay_cap>
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


def name_finding(person: Person, values: dict, page_list: list[dict], card: dict | None = None) -> Finding | None:
    current = " ".join(str(values.get(person.name) or "").split())
    target = fold(current).split()
    if len(target) < 2:
        return None
    ours = trang.name_key(current)
    number = trang.digits(values.get(person.number))
    # Thẻ nhận theo ngày sinh (tên lượt trích đọc sai hẳn): họ tên trên thẻ cũng là một ứng viên để chấm số trang.
    on_card = card["name"].split() if card and card.get("by_birth") else []
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
                elif on_card and letters == on_card and "<" not in line:  # dòng MRZ không dấu không phải cách viết
                    candidates[key] = {"name": window.upper(), "quote": line, "doc": page["doc"], "letters": True}
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
        stat = trang.support(cand["name"], page_list)
        # Đề xuất chỉ là bản rơi dấu / mất nét "Đ" của lượt trích: OCR hay làm rơi dấu chữ in hoa trên THẺ, nên chỉ nhận khi
        # giấy in KHÔNG phải thẻ (trích lục, giấy chứng tử…) ghi đúng cách viết đó.
        if not cand["letters"] and (base._adds_marks(key, ours) or base._lost_stroke(key, ours)) and stat["ban_in"] < 1:
            continue
        if cand["letters"] and letters_on_paper:
            continue
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
                    f"quan cấp, {best['the']} dòng họ tên thẻ, {best['tu_lap']} giấy tự lập, {best['don']} văn bản đề "
                    f"nghị; A: {mine['ban_in']} giấy in cơ quan cấp, {mine['the']} dòng thẻ, {mine['tu_lap']} giấy tự "
                    f"lập, {mine['don']} văn bản đề nghị")


def _card(person: Person, values: dict, documents: list[dict]) -> dict | None:
    """Thẻ của người này: MRZ mang họ tên (không dấu) của người đó, năm sinh trong số khớp năm sinh in ở MRZ, và thẻ không
    trái với người đó (số lệch quá 2 chữ số VÀ năm sinh khác → thẻ người khác trùng họ tên)."""
    name = " ".join(fold(values.get(person.name)).split())
    if not name:
        return None
    number = trang.digits(values.get(person.number))
    born = parse_date(values.get(person.birth))
    every = [card for document in documents for card in mrz_records(document.get("text"))]
    cards = [card for card in every if card.get("name") == name and card.get("birth")
             and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]
             and not (len(number) >= 9 and _edit(number, card["id"]) > 2
                      and born and born.year != id_birth_year(card["id"]))]
    if cards:
        return cards[0] if len({card["id"] for card in cards}) == 1 else None
    return _card_by_birth(name, number, born, every, documents)


_NEAR_NUMBER = 3


def _card_by_birth(name: str, number: str, born, every: list[dict], documents: list[dict]) -> dict | None:
    """Tên lượt trích đọc sai hẳn (chữ viết tay) nên không thẻ nào mang tên đó: nhận thẻ có ngày sinh in ở MRZ trùng HẲN
    ngày sinh của người này, cùng họ và chữ đệm, số không lệch quá 3 chữ số. Các bản quét của cùng thẻ có thể đọc lệch số
    MRZ → lấy số được in nhiều lần nhất trên giấy; các số còn lại phải gần số đó (khác hẳn → thẻ người khác, không đoán)."""
    words = name.split()
    if not born or len(words) < 3:
        return None
    pool = [card for card in every if card.get("name") and card["name"].split()[:2] == words[:2]
            and len(card["name"].split()) >= 3]
    dated = [card for card in pool if card.get("birth") == (born.year % 100, born.month, born.day)]
    if not dated or len({card["name"] for card in dated}) != 1:
        return None
    pool = [card for card in pool if card["name"] == dated[0]["name"] and card.get("birth") in (None, dated[0]["birth"])]
    text = "\n".join(str(document.get("text") or "") for document in documents)
    seen = {card["id"]: len(re.findall(rf"(?<!\d){card['id']}(?!\d)", text)) for card in pool}
    ranked = sorted(seen.items(), key=lambda item: item[1], reverse=True)
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    best = ranked[0][0]
    if (id_birth_year(best) or 0) != born.year or any(_edit(best, other) > 2 for other in seen):
        return None
    if len(number) >= 9 and _edit(number, best) > _NEAR_NUMBER:
        return None
    return {**dated[0], "id": best, "by_birth": True}


def card_findings(person: Person, values: dict, documents: list[dict]) -> list[Finding]:
    card = _card(person, values, documents)
    if not card:
        return []
    out = []
    how = ("thẻ có ngày sinh in ở MRZ trùng ngày sinh của người này, cùng họ và chữ đệm, số gần số lượt trích (tên lượt "
           "trích đọc sai chữ viết tay); số lấy theo số in nhiều lần nhất trên thẻ" if card.get("by_birth") else
           "vùng MRZ của thẻ mang họ tên (không dấu) của người này, năm sinh trong số khớp ngày sinh in ở MRZ")
    mrz_line = lambda text: bool(re.search(rf"I[DO]VNM\S*{card['id']}", re.sub(r"\s+", "", text)))  # noqa: E731
    current = trang.digits(values.get(person.number))
    if current != card["id"]:
        quote, doc = _line_with(documents, mrz_line)
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
    if gender and fold(gender) != fold(values.get(person.gender)):
        line, at = _line_with(documents, mrz_line)
        if line:
            out.append(_finding(person, "gioi_tinh", gender, line, at, f"giới tính in ở MRZ thẻ của {person.label}", how))
    return out


# Ngày trên dòng chấm điền viết tay ("..12..../08./.2021"): chấm điền xen giữa ngày / tháng / năm.
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[\s.…]*[/.-][\s.…]*(\d{1,2})[\s.…]*[/.-][\s.…]*(\d{4})(?!\d)")
_ISSUE_RE = re.compile(r"(?i)c[aấ]p")
_ID_RE = re.compile(r"(?<!\d)\d{9,12}(?!\d)")


def _has_number(line: str, number: str) -> bool:
    """Dòng ghi đúng số định danh này như MỘT cụm số (cho phép dấu cách / chấm trong cụm) — không nối chữ số cả dòng: OCR
    dính hai dòng làm số ghép tình cờ chứa số của người khác."""
    return any(re.sub(r"\D", "", token) == number for token in re.findall(r"\d[\d .]*\d", line))


def issue_scores(number: str, page_list: list[dict], own: frozenset = frozenset()) -> dict[str, dict]:
    """{ngày cấp dd/mm/yyyy: {điểm, in, dòng, trang}} — ngày có chữ "cấp" ghi trên dòng thuộc khối tờ khai của chính người này
    (`own`), hoặc cùng dòng số định danh của người này (dòng sau nếu dòng số không có ngày, dừng ở dòng mang số người
    khác). Mỗi dòng ghi là một nguồn: giấy in 2 điểm, dòng viết tay (đơn, dòng chấm điền) / giấy tự lập 1 điểm."""
    out: dict[str, dict] = {}
    for page in page_list:
        lines = page["lines"]
        for at, line in enumerate(lines):
            mine = line.strip() in own
            if not mine and not (len(number) in (9, 12) and _has_number(line, number)):
                continue
            near = [line]
            if not mine:
                for nxt in lines[at + 1:at + 3]:
                    if any(found != number for found in _ID_RE.findall(re.sub(r"\s+", "", nxt))):
                        break
                    near.append(nxt)
            for text in near:
                if not _ISSUE_RE.search(text):
                    continue
                dates = {f"{int(d):02d}/{int(m):02d}/{y}" for d, m, y in _DATE_RE.findall(text)}
                printed = page["kind"] == "ban_in" and ".." not in text
                for key in dates:
                    item = out.setdefault(key, {"diem": 0, "in": 0, "dong": text.strip(), "trang": page["doc"]})
                    item["diem"] += 2 if printed else 1
                    item["in"] += printed
                    if printed:
                        item["dong"], item["trang"] = text.strip(), page["doc"]
                if dates:
                    break
    return out


def issue_finding(person: Person, values: dict, page_list: list[dict], own: frozenset = frozenset()) -> Finding | None:
    number = trang.digits(values.get(person.number))
    current = parse_date(values.get(person.issued))
    scores = issue_scores(number, page_list, own)
    if not scores:
        return None
    mine = next((item for key, item in scores.items() if parse_date(key) == current), {"diem": 0, "in": 0})
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["diem"], reverse=True)
    best_key, best = ranked[0]
    # Ngày được nhiều nguồn ghi hơn thắng (giấy in nặng gấp đôi dòng viết tay); cần ít nhất hai điểm.
    if parse_date(best_key) == current or best["diem"] < 2 or best["diem"] <= mine["diem"]:
        return None
    if len(ranked) > 1 and ranked[1][1]["diem"] == best["diem"]:
        return None
    return _finding(person, "ngay_cap", best_key, best["dong"], best["trang"], f"giấy ghi ngày cấp của {person.label}",
                    f"điểm ngày cấp ghi cho người này: B {best['diem']} ({best['in']} giấy in), A {mine['diem']} "
                    f"({mine['in']} giấy in)")


def _own_lines(person: Person, values: dict, documents: list[dict]) -> frozenset:
    """Các dòng thuộc khối tờ khai của chính người này: người chết → mục người chết; người đứng ra mai táng → mục người đề
    nghị / 3.1; người nộp → khối đó chỉ khi chính là người ghi ở khối (tên / số có trong khối)."""
    from . import dia_chi

    part = "deceased" if person.prefix == "NguoiMat" else "organizer"
    lines, _ = dia_chi._sections(documents).get(part, ([], 0))
    if person.prefix == "NguoiNop":
        text = " ".join(lines)
        name = fold(values.get(person.name)).strip()
        number = trang.digits(values.get(person.number))
        if not ((name and name in fold(text)) or (len(number) >= 9 and number in trang.digits(text))):
            return frozenset()
    return frozenset(line.strip() for line in lines)


def findings_from(case: Case) -> list[Finding]:
    page_list = trang.pages(case.documents)
    out = []
    for person in PERSONS:
        card = _card(person, case.values, case.documents)
        name = name_finding(person, case.values, page_list, card)
        issued = issue_finding(person, case.values, page_list, _own_lines(person, case.values, case.documents))
        out += [*([name] if name else []), *card_findings(person, case.values, case.documents), *([issued] if issued else [])]
    return out


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


_OWNERS = tuple(person.label for person in PERSONS)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH người đứng ra mai táng, người nộp, người chết (họ tên, số định danh, ngày sinh, ngày cấp)",
                      UNITS, RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
