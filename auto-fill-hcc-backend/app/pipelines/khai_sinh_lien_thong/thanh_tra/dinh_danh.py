"""Thanh tra ĐỊNH DANH hồ sơ liên thông khai sinh: họ tên, số định danh, ngày sinh của cha, mẹ, chủ hộ (CT01); họ tên trẻ.

Mã thuần, không qua LLM; mỗi người soát trên chính field lượt trích của người đó (không phân vai lại):
1. Họ tên: mọi cách viết có nguyên văn trên giấy — cùng chữ cái khác dấu, hoặc (người có số định danh) lệch một hai chữ cái
   trên trang mang số định danh của người đó — đếm số TRANG ghi; nhiều trang hơn thắng, bằng nhau theo hạng nguồn (giấy in
   cơ quan cấp > tờ khai > giấy tự lập). Chặn bản rơi dấu / "Đ" thành "D"; chặn đổi chữ cái khi chữ cái của lượt trích đã
   có trên giấy ngoài tờ khai (cách viết khác chữ thường là người khác trong gia đình). Tên trẻ chỉ xét cách viết khác dấu.
2. Số định danh, ngày sinh: vùng MRZ mặt sau thẻ mang họ tên (không dấu) của người đó, năm sinh mã hoá trong số khớp năm
   sinh in ở MRZ. Ô số định danh chỉ nhận số căn cước 12 chữ số (lượt trích ghi số CMND 9 số → đề xuất số trên thẻ).
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
    name: str
    number: str = ""
    birth: str = ""


PERSONS = (
    Person("cha", "cha của trẻ", "ThongTinBo_HoTen", "ThongTinBo_SoDinhDanh", "ThongTinBo_NgaySinh"),
    Person("me", "mẹ của trẻ", "ThongTinMe_HoTen", "ThongTinMe_SoDinhDanh", "ThongTinMe_NgaySinh"),
    Person("chu_ho", "chủ hộ trên tờ khai thay đổi thông tin cư trú", "Ct01_ChuHoHoTen", "Ct01_ChuHoSoDinhDanh"),
)
# Tên trẻ: mapper lấy tờ khai trước, rồi giấy chứng sinh — soát đúng field đang lên form.
CHILD = (Person("con", "trẻ được khai sinh", "Tk_HoTenCon"), Person("con", "trẻ được khai sinh", "Gcs_HoTenCon"))


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
Mỗi vụ xét họ tên của MỘT người (cha, mẹ, chủ hộ hoặc trẻ — nêu ở tên mục). Mã đã đếm số TRANG giấy ghi nguyên văn từng cách
viết (dòng "TỔNG số trang" trong tín hiệu mã). B được nhiều trang ghi hơn A → chọn B; số trang bằng nhau thì theo hạng: giấy
in cơ quan cấp (giấy chứng sinh, CCCD, giấy / trích lục kết hôn) > tờ khai (đăng ký khai sinh, thay đổi thông tin cư trú —
viết tay) > giấy người dân tự lập. Hai cách viết chỉ khác DẤU là chuyện thường (OCR đọc lệch dấu chữ viết tay), KHÔNG phải
lý do giữ A. Mã đã tự loại cách viết là bản rơi dấu của A, chữ Đ đọc thành D, và cách viết đổi chữ cái khi chữ cái của A đã
có trên giấy ngoài tờ khai. Dòng trích dẫn là họ tên của người khác (không phải người nêu ở tên mục) → KHONG_DU_CAN_CU.
Riêng TÊN TRẺ: A theo tờ khai đăng ký khai sinh, B là tên mục 1 tờ CT01, cùng chữ cái chỉ khác dấu, không giấy in cơ quan
cấp nào ghi A → chọn B (OCR hay đọc lệch dấu ở tờ khai đăng ký khai sinh viết tay, mục 1 CT01 viết in hoa trong ô kẻ).
</ho_ten>

<so_ngay>
Số định danh / ngày sinh lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của đúng người đó, năm sinh trong số khớp ngày
sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số viết tay. Ô số định danh chỉ nhận số căn cước 12 chữ số:
A là số CMND 9 số / số thiếu chữ số → chọn B (số trên thẻ của chính người đó).
Tín hiệu "khối người mẹ in trên giấy chứng sinh": giấy chứng sinh do cơ sở y tế cấp ghi họ tên, ngày sinh, số định danh
của chính mẹ đẻ của trẻ → B (theo giấy chứng sinh) thay cho A chép từ tờ khai viết tay, kể cả khi họ tên khác chữ cái.
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
        # Chủ hộ hay là ông / bà của trẻ, họ tên trùng chữ (chỉ khác dấu) với cha: chỉ xét trang mang số của chủ hộ.
        if person.key == "chu_ho" and not anchored:
            continue
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
                    f"{mine['to_khai']} tờ khai")


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
    if person.key == "chu_ho" and (len(current) == 12 or card["id"] in {
            trang.digits(values.get(other.number)) for other in PERSONS if other.key != "chu_ho"}):
        # Chủ hộ (ông / bà) trùng chữ họ tên với cha / mẹ: thẻ đó là của cha / mẹ. Số chủ hộ đủ 12 chữ số thì giữ.
        return []
    if current != card["id"]:
        quote, doc = _line_with(documents, lambda line: bool(re.search(rf"I[DO]VNM\S*{card['id']}",
                                                                       re.sub(r"\s+", "", line))))
        if quote:
            out.append(_finding(person, "so_dinh_danh", card["id"], quote, doc, f"dòng MRZ mặt sau thẻ của {person.label}",
                                "vùng MRZ của thẻ mang họ tên (không dấu) của người này, năm sinh trong số khớp ngày "
                                "sinh in ở MRZ" + ("; số của A không đủ 12 chữ số" if len(current) != 12 else "")))
    if not person.birth:
        return out
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


_GCS_NAME_RE = re.compile(r"(?i)h[oọ],?\s*ch[uữ]\s*[đd][eệ]m,?\s*t[eê]n\s*(?:khai\s*sinh\s*)?c[uủ]a\s*m[eẹ]\s*:\s*(.+)")
_GCS_BIRTH_RE = re.compile(r"(?i)ng[aà]y,?\s*th[aá]ng,?\s*n[aă]m\s*sinh\s*:\s*(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})")
_GCS_ID_RE = re.compile(r"(?i)s[oố]\s*(?:[đd]dcn|[đd]inh\s*danh|cccd)[^:]*:\s*([\d\s]{9,16})")
# Nhãn kế tiếp trên cùng dòng họ tên mẹ ("…của mẹ: NGUYỄN THỊ A Dân tộc: Kinh") — tên dừng ở đó.
_GCS_NEXT_LABEL_RE = re.compile(r"(?i)\s+(?:d[aâ]n\s*t[oộ]c|ng[aà]y|n[aă]m\s*sinh|s[oố]\s|qu[oố]c\s*t[iị]ch|n[oơ]i\s)")


def _gcs_mother(page_list: list[dict]) -> dict | None:
    """Khối người mẹ in trên GIẤY CHỨNG SINH (cơ sở y tế cấp): họ tên, ngày sinh, số định danh của mẹ đẻ của trẻ."""
    for page in page_list:
        if page["kind"] != "ban_in" or "giay chung sinh" not in fold(" ".join(page["lines"][:12])):
            continue
        out: dict = {}
        for at, line in enumerate(page["lines"]):
            name = _GCS_NAME_RE.search(line)
            if name and "name" not in out:
                text = _GCS_NEXT_LABEL_RE.split(name.group(1), maxsplit=1)[0]
                out.update(name=" ".join(text.split()).strip(" .,;:"), name_line=line, doc=page["doc"])
                for follow in page["lines"][at:at + 4]:
                    birth = _GCS_BIRTH_RE.search(follow)
                    if birth and "birth" not in out:
                        out.update(birth=re.sub(r"\s+", "", birth.group(1)), birth_line=follow)
                    number = _GCS_ID_RE.search(follow)
                    if number and "id" not in out:
                        out.update(id=trang.digits(number.group(1)), id_line=follow)
        if out.get("name"):
            return out
    return None


def _near_digits(a: str, b: str) -> bool:
    return bool(a) and bool(b) and _edit(a, b) <= 2


def gcs_mother_findings(values: dict, page_list: list[dict], card_done: set[str]) -> list[Finding]:
    """Mẹ trên giấy chứng sinh (giấy in) thay cho tờ khai viết tay: họ tên, ngày sinh, số định danh. Chỉ khi khối đó gắn được
    với mẹ của lượt trích (số lệch ≤2 chữ số, hoặc ngày sinh / họ tên gần) — tránh giấy chứng sinh của hồ sơ khác."""
    gcs = _gcs_mother(page_list)
    me = next(p for p in PERSONS if p.key == "me")
    if not gcs:
        return []
    ours_name, ours_id = str(values.get(me.name) or ""), trang.digits(values.get(me.number))
    ours_birth, gcs_birth = parse_date(values.get(me.birth)), parse_date(gcs.get("birth") or "")
    birth_near = bool(ours_birth and gcs_birth and _edit(f"{ours_birth:%d%m%Y}", f"{gcs_birth:%d%m%Y}") <= 1)
    linked = (_near_digits(gcs.get("id", ""), ours_id) or close_name(gcs["name"], ours_name) or birth_near
              or not (ours_name.strip() or ours_id or ours_birth))
    if not linked:
        return []
    how = "khối người mẹ in trên giấy chứng sinh (cơ sở y tế cấp), gắn với mẹ của lượt trích"
    out = []
    # Chỉ khác DẤU thì giấy chứng sinh không hơn tờ khai (OCR cũng đọc lệch dấu bản in) → để luật đếm trang quyết; khác
    # CHỮ CÁI (tờ khai viết tay đọc sai cả tên) mới theo giấy chứng sinh.
    if fold(gcs["name"]).split() != fold(ours_name).split() and len(gcs["name"].split()) >= 2:
        out.append(_finding(me, "ho_ten", gcs["name"].upper(), gcs["name_line"], gcs["doc"], "giấy chứng sinh", how))
    # Số của mẹ: mã giới tính nữ (chữ số thứ 4 lẻ), năm sinh mã hoá trong số khớp ngày sinh in cùng khối.
    number = gcs.get("id", "")
    valid = (len(number) == 12 and int(number[3]) % 2 == 1
             and (not gcs_birth or id_birth_year(number) == gcs_birth.year))
    if "so_dinh_danh" not in card_done and valid and number != ours_id:
        out.append(_finding(me, "so_dinh_danh", gcs["id"], gcs["id_line"], gcs["doc"], "giấy chứng sinh", how))
    if "ngay_sinh" not in card_done and gcs_birth and gcs_birth != ours_birth:
        out.append(_finding(me, "ngay_sinh", f"{gcs_birth:%d/%m/%Y}", gcs["birth_line"], gcs["doc"], "giấy chứng sinh",
                            how))
    return out


_CT01_HEAD = "to khai thay doi thong tin cu tru"


def ct01_child_finding(child: Person, values: dict, page_list: list[dict]) -> Finding | None:
    """Tên trẻ lấy theo tờ khai đăng ký khai sinh mà mục 1 tờ CT01 ghi cùng chữ cái, chỉ khác DẤU → theo CT01.

    Hai tờ khai cùng hạng, cùng viết tay nên phép đếm trang hoà nhau và giữ tờ khai. Trên hồ sơ thật, chỗ lệch là OCR
    đọc dấu ở tờ khai đăng ký khai sinh; tên mục 1 CT01 viết in hoa trong ô kẻ, OCR giữ dấu đúng. Giấy in (giấy chứng
    sinh, thẻ) ghi theo cách viết đang có thì giữ nguyên."""
    if child.name != "Tk_HoTenCon":
        return None
    current = " ".join(str(values.get(child.name) or "").split())
    ct01 = " ".join(str(values.get("Ct01_HoTen") or "").split())
    if not current or not ct01 or fold(current).split() != fold(ct01).split():
        return None
    if trang.name_key(ct01) == trang.name_key(current):
        return None
    if base._adds_marks(trang.name_key(ct01), trang.name_key(current)) or base._lost_stroke(
            trang.name_key(ct01), trang.name_key(current)):
        return None  # CT01 chỉ là bản rơi dấu / "Đ" đọc thành "D" của tên đang có
    needle = trang.words(ct01)
    quote = next(((line, page["doc"]) for page in page_list if page["kind"] == "to_khai"
                  and _CT01_HEAD in " ".join(fold(line) for line in page["lines"][:12])
                  for line in page["lines"] if needle in trang.words(line)), None)
    if quote is None:
        return None
    mine = trang.support(current, page_list)
    if mine["ban_in"] + mine["the"]:
        return None
    return _finding(child, "ho_ten", ct01.upper(), quote[0], quote[1], "tờ khai thay đổi thông tin cư trú (CT01)",
                    f"Tờ khai đăng ký khai sinh ghi A, mục 1 tờ CT01 ghi B — cùng chữ cái, chỉ khác dấu; không giấy in "
                    f"cơ quan cấp nào ghi A (A: {mine['to_khai']} tờ khai, {mine['tu_lap']} giấy tự lập)")


def findings_from(case: Case) -> list[Finding]:
    page_list = trang.pages(case.documents)
    out = []
    for person in PERSONS:
        cards = card_findings(person, case.values, case.documents)
        if person.key == "me":
            # Mẹ: giấy chứng sinh in (cơ sở y tế) thắng tờ khai viết tay; số / ngày sinh theo thẻ (MRZ) nếu có thẻ.
            gcs = gcs_mother_findings(case.values, page_list, {f.unit.key.split(".")[1] for f in cards})
            if any(person.name in f.values for f in gcs):
                out += gcs + cards
                continue
            cards = gcs + cards
        name = name_finding(person, case.values, page_list)
        out += [*([name] if name else []), *cards]
    child = next((person for person in CHILD if str(case.values.get(person.name) or "").strip()), None)
    name = (name_finding(child, case.values, page_list) or ct01_child_finding(child, case.values, page_list)
            if child else None)
    return out + ([name] if name else [])


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


_OWNERS = tuple(dict.fromkeys(person.label for person in (*PERSONS, *CHILD)))
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH cha, mẹ, chủ hộ, trẻ (họ tên, số định danh, ngày sinh)", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
