"""Thanh tra NHÂN THÂN người được cấp: họ tên, số định danh, ngày sinh, giới tính, dân tộc, cụm giấy tờ tùy thân.

Cách kiểm riêng: đối chiếu chéo NGUỒN. Mỗi trang giấy được đọc riêng, vùng MRZ thẻ căn cước do mã đọc; mã đếm
số nguồn độc lập cùng ghi một giá trị. Hồ sơ chỉ có một trang nhắc tên người được cấp thì không có gì để đối
chiếu — chỉ còn tác dụng bổ sung ô trống.
"""

import asyncio
import re
from dataclasses import replace
from datetime import date

from app.config import settings
from app.pipelines._shared.cccd import id_birth_year, id_gender, mrz_records
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import (Case, Field, Finding, Inspector, Unit, alnum, compare_key, fold,
                                                   parse_date)

from app.services.llm import client

from ..process.reason import labeled_value, name_match, requester_context, section


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


RULES = """
<dung_nguoi>
Người được cấp bản sao là người ở khối <nguoi_duoc_cap> của <phan_vai_da_xac_dinh>. CHỈ lấy dòng thuộc chính
người đó; không lấy của người nộp, người yêu cầu, cha / mẹ, vợ / chồng, người đi khai, người được ủy quyền.
Mỗi thông tin đi cùng đúng một người: không ghép họ tên người này với số / ngày sinh của người khác.
</dung_nguoi>

<nguon>
Một thông tin của người được cấp có thể nằm ở nhiều giấy:
(1) khối người được cấp trên TỜ KHAI (sau câu "cho người có tên dưới đây");
(2) giấy hộ tịch của chính người đó — giấy khai sinh: khối người được khai sinh; trích lục khai tử: khối người
    chết; giấy chứng nhận kết hôn: đúng cột vợ / chồng của người đó; giấy chứng sinh: "Dự định đặt tên con",
    ngày sinh trong "Đã sinh con ... ngày ...", "Giới tính của con";
(3) thẻ căn cước / CCCD / CMND có họ tên in trên thẻ là chính người đó.
Các nguồn ghi GIỐNG nhau → lấy giá trị đó. Các nguồn ghi KHÁC nhau (lệch dấu, lệch một chữ, lệch một chữ số):
tờ khai thường viết tay nên OCR hay đọc sai → lấy theo GIẤY IN MÁY của chính người đó (thẻ căn cước, giấy hộ
tịch in), và chọn bản mà nhiều giấy cùng ghi. Chỉ một nguồn có → lấy nguồn đó, chép đúng từng ký tự.
</nguon>

<tung_muc>
- Họ tên: chép đúng chữ và dấu trên giấy, không tự sửa dấu, không viết hoa lại.
- Số định danh cá nhân: đúng 12 chữ số của chính người được cấp. Số 9 chữ số là CMND, không phải số định danh.
  Dòng "Số: <mã>/<năm>" đầu giấy hộ tịch là số đăng ký, không phải số định danh.
- Ngày sinh: dd/mm/yyyy, chỉ khi giấy ghi đủ ngày, tháng, năm. Một giấy chỉ ghi năm mà giấy khác của chính
  người đó ghi đủ ngày → lấy bản đủ ngày.
- Giới tính: "Nam" hoặc "Nữ" theo dòng giới tính của chính người đó; trên giấy kết hôn theo vai (chồng = Nam,
  vợ = Nữ).
- Dân tộc: giữ nguyên chữ trên giấy.
- Cụm giấy tờ tùy thân (loại, số, ngày cấp, nơi cấp) đi NGUYÊN CỤM từ MỘT giấy của chính người được cấp; người
  có cả căn cước 12 số lẫn CMND 9 số thì lấy cụm của thẻ 12 số. Nơi cấp chép đúng chữ trên giấy. A là CMND 9 số
  (kể cả khi A nằm ở ô số định danh), B là số 12 chữ số trên thẻ căn cước mà dòng "Tín hiệu mã" báo trùng vùng MRZ
  của thẻ mang tên người được cấp → chọn B.
- Họ tên: dòng "Tín hiệu mã" báo họ tên không dấu của B trùng vùng MRZ của thẻ còn A không trùng → chọn B (giấy
  viết tay / giấy cũ đọc lệch một chữ, MRZ là chữ in máy).
  + Dòng "Giấy tờ tùy thân: ... số ... cấp ngày ..." trên GIẤY KHAI SINH là của người đi khai sinh → không lấy.
  + TRÍCH LỤC KHAI TỬ: người được cấp đã chết; giấy tờ tùy thân của họ chỉ là dòng in trong khối NGƯỜI CHẾT.
    Mọi thẻ căn cước kèm trích lục khai tử là của người khác → không lấy. Dòng đó để trống → cụm này null.
  + Thẻ căn cước của người nộp hay của bất kỳ ai khác tên người được cấp → không lấy.
</tung_muc>
"""

UNITS = (
    Unit("ho_ten", "Họ tên người được cấp", (Field("NguoiDuocCap_HoTen", "họ, chữ đệm, tên"),)),
    Unit("so_dinh_danh", "Số định danh cá nhân người được cấp",
         (Field("NguoiDuocCap_SoDinhDanh", "số định danh 12 chữ số", "code", canon=_digits),)),
    Unit("ngay_sinh", "Ngày sinh người được cấp", (Field("NguoiDuocCap_NgaySinh", "ngày sinh dd/mm/yyyy", "date"),)),
    Unit("gioi_tinh", "Giới tính người được cấp",
         (Field("NguoiDuocCap_GioiTinh", '"Nam" hoặc "Nữ"', "free", canon=alnum),)),
    Unit("dan_toc", "Dân tộc người được cấp", (Field("NguoiDuocCap_DanToc", "dân tộc", "free", canon=alnum),)),
    Unit("giay_to_tuy_than", "Cụm giấy tờ tùy thân của người được cấp", (
        Field("NguoiDuocCap_LoaiGiayTo", "loại: Căn cước / Căn cước công dân / CMND / Hộ chiếu", "free", canon=alnum),
        Field("NguoiDuocCap_SoGiayTo", "số giấy tờ", "code"),
        Field("NguoiDuocCap_NgayCap", "ngày cấp dd/mm/yyyy", "date"),
        Field("NguoiDuocCap_NoiCap", "cơ quan cấp", "free", canon=lambda value: alnum(normalize_issuer(value))),
    )),
)


def _subject(case: Case) -> dict:
    """Người được cấp theo phân vai, thiếu thì theo lượt trích."""
    block = section(case.context, "nguoi_duoc_cap")
    values = case.values
    return {
        "name": labeled_value(block, "Họ tên") or str(values.get("NguoiDuocCap_HoTen") or ""),
        "birth": parse_date(labeled_value(block, "Ngày sinh")) or parse_date(values.get("NguoiDuocCap_NgaySinh")),
        "gender": labeled_value(block, "Giới tính") or str(values.get("NguoiDuocCap_GioiTinh") or ""),
    }


def _same_person(name: str, other: str) -> bool:
    return bool(name and other) and (fold(name).split() == fold(other).split() or bool(name_match(name, other)))


def _id_mismatch(number: str, subject: dict) -> str:
    """Số căn cước 12 số mã hoá giới tính và năm sinh: lệch với người được cấp thì là số của người khác."""
    gender = id_gender(number)
    if gender and subject["gender"] and fold(gender) != fold(subject["gender"]):
        return f"số mã hoá giới tính {gender}, người được cấp là {subject['gender']}"
    year = id_birth_year(number)
    if year and subject["birth"] and year != subject["birth"].year:
        return f"số mã hoá năm sinh {year}, người được cấp sinh {subject['birth'].year}"
    return ""


def check(unit: Unit, values: dict, case: Case) -> str:
    subject = _subject(case)
    account_name, account_id = requester_context(case.options)
    if unit.key == "ho_ten":
        name = str(values.get("NguoiDuocCap_HoTen") or "")
        if subject["name"] and not _same_person(subject["name"], name):
            return "họ tên khác người được cấp đã phân vai"
    number = _digits(values.get("NguoiDuocCap_SoDinhDanh") or values.get("NguoiDuocCap_SoGiayTo"))
    if unit.key == "so_dinh_danh" and len(number) != 12:
        return "số định danh không đủ 12 chữ số"
    if unit.key in ("so_dinh_danh", "giay_to_tuy_than") and number:
        if account_id and number == account_id and not _same_person(account_name, subject["name"]):
            return "số của người nộp, không phải người được cấp"
        if len(number) == 12:
            return _id_mismatch(number, subject)
    if unit.key == "ngay_sinh":
        born = parse_date(values.get("NguoiDuocCap_NgaySinh"))
        if born and born > date.today():
            return "ngày sinh ở tương lai"
    return ""


def _subject_cards(case: Case) -> list[dict]:
    """Vùng MRZ của các thẻ căn cước mang họ tên người được cấp — kể cả lệch một chữ cái, vì chính họ tên lượt trích
    (đọc từ giấy viết tay / giấy cũ) có thể là chỗ đang sai; thẻ khác giới tính với người được cấp thì không nhận."""
    subject = _subject(case)
    name = subject["name"]
    cards = []
    for document in case.documents:
        for record in mrz_records(document.get("text")):
            if not name or not name_match(name, record.get("name") or ""):
                continue
            if subject["gender"] and record.get("gender") and fold(record["gender"]) != fold(subject["gender"]):
                continue
            cards.append(record)
    return cards


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    out = []
    cards = _subject_cards(case)
    if unit.key == "ho_ten":
        name = " ".join(fold(values.get("NguoiDuocCap_HoTen")).split())
        for card in cards:
            if name and card.get("name"):
                out.append((name == card["name"], "họ tên (không dấu) in ở vùng máy đọc (MRZ) thẻ căn cước của người này"))
    if unit.key == "ngay_sinh":
        born = parse_date(values.get("NguoiDuocCap_NgaySinh"))
        for card in cards:
            if born and card.get("birth"):
                out.append(((born.year % 100, born.month, born.day) == card["birth"],
                            "ngày sinh in ở vùng máy đọc (MRZ) thẻ căn cước của người này"))
    if unit.key in ("so_dinh_danh", "giay_to_tuy_than"):
        number = _digits(values.get("NguoiDuocCap_SoDinhDanh") or values.get("NguoiDuocCap_SoGiayTo"))
        if len(number) == 12:
            if cards:
                out.append((any(card["id"] == number for card in cards),
                            "số in ở vùng máy đọc (MRZ) thẻ căn cước của người này"))
            mismatch = _id_mismatch(number, _subject(case))
            if mismatch:
                out.append((False, mismatch))
    if unit.key == "gioi_tinh":
        gender = str(values.get("NguoiDuocCap_GioiTinh") or "")
        for card in cards:
            if card.get("gender"):
                out.append((fold(card["gender"]) == fold(gender),
                            "giới tính in ở vùng máy đọc (MRZ) thẻ căn cước của người này"))
    return out


_PAGE_BREAK_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$")
_MAX_PAGES = 8
# Từ hai nguồn độc lập (hai trang giấy, hoặc một trang + vùng MRZ) cùng ghi một giá trị mới đủ để thay lượt trích.
_MIN_SUPPORT = 2


def _pages(case: Case) -> list[tuple[int, str]]:
    """(số tài liệu, chữ của trang) cho mỗi trang có nhắc tên người được cấp — mỗi trang là một nguồn đọc riêng."""
    name = _subject(case)["name"]
    pages = []
    for index, document in enumerate(case.documents, start=1):
        for text in _PAGE_BREAK_RE.split(str(document.get("text") or "")):
            if text.strip() and (not name or name_match(name, text)):
                pages.append((index, text.strip()))
    return pages[:_MAX_PAGES]


def _unit_key(unit: Unit, values: dict):
    """Khóa gom các nguồn ghi cùng một giá trị; cụm giấy tờ tùy thân gom theo số giấy tờ."""
    if unit.key == "giay_to_tuy_than":
        return _digits(values.get("NguoiDuocCap_SoGiayTo")) or None
    return compare_key(unit.fields[0], values.get(unit.fields[0].name))


_UNKNOWN_RE = re.compile(r"^(khong (xac dinh|ro|co|ghi)|chua (ro|xac dinh)|n/?a|null|none|\?+)$")
# Nơi cấp phải là tên một cơ quan cấp giấy tờ tùy thân; "Cấp tại: <xã, tỉnh>" trên giấy kết hôn cũ là nơi cấp chính
# giấy kết hôn đó.
_ISSUER_WORD_RE = re.compile(r"\b(cong an|ca|cuc|bo|canh sat|cs|phong|pc\d*|pa\d*|qlhc|xuat nhap canh|giam doc)\b")
_CARD_MIN_AGE = 14


def _tidy_card(finding: Finding, case: Case) -> dict:
    """Cụm giấy tờ tùy thân đọc từ một trang: bỏ ngày cấp vô lý (trùng ngày sinh, hoặc khi người đó chưa đủ tuổi cấp
    thẻ — model hay vớ ngày sinh in cạnh vùng MRZ) và nơi cấp kiểu "Không xác định"; số thẻ vẫn giữ."""
    values = dict(finding.values)
    if finding.unit.key != "giay_to_tuy_than":
        return values
    issued = parse_date(values.get("NguoiDuocCap_NgayCap"))
    births = {parse_date(case.values.get("NguoiDuocCap_NgaySinh")), _subject(case)["birth"]} - {None}
    # Lượt trích / phân vai hay chỉ có năm sinh: ngày sinh in ở vùng MRZ của thẻ (năm 2 chữ số) cũng dùng để so.
    mrz_births = {card["birth"] for card in _subject_cards(case) if card.get("birth")}
    # Ngày ở tương lai là ngày HẾT HẠN của thẻ ("Có giá trị đến").
    if issued and (issued > date.today()
                   or any(issued == born or (issued - born).days < _CARD_MIN_AGE * 365 for born in births)
                   or (issued.year % 100, issued.month, issued.day) in mrz_births):
        values.pop("NguoiDuocCap_NgayCap", None)
    issuer = fold(values.get("NguoiDuocCap_NoiCap")).strip(" .")
    if issuer and (_UNKNOWN_RE.match(issuer) or not _ISSUER_WORD_RE.search(issuer)):
        values.pop("NguoiDuocCap_NoiCap", None)
    return values


def _card_backs(unit: Unit, values: dict, case: Case) -> bool:
    """Vùng MRZ của thẻ mang tên người được cấp cùng ghi giá trị này: một nguồn in máy độc lập với chữ trên giấy."""
    return any(ok for ok, _ in signals(unit, values, case) if "MRZ" in _)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    """Agent chính đọc gộp cả hồ sơ nên hay bám một nguồn. Ở đây mỗi trang được đọc RIÊNG (lượt đọc không thấy
    trang khác), rồi MÃ đếm số nguồn cùng ghi một giá trị: giá trị có nhiều nguồn hơn giá trị lượt trích mới
    được đem ra toà để thay; ít nguồn hơn hoặc ngang thì chỉ dùng để bổ sung ô trống."""
    out = await _cross_check(inspector, case, title)
    if not any(finding.unit.key == "dan_toc" for finding in out):
        ethnic = await _ethnic_finding(case, title)
        if ethnic:
            out.append(ethnic)
    return out


async def _cross_check(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    pages = _pages(case)
    if len(pages) <= 1:
        return await engine.llm_findings(inspector, case, title)
    answers = await asyncio.gather(*(
        engine.llm_findings(inspector, Case([{"name": case.documents[index - 1].get("name"), "text": text}],
                                            case.context, case.values, case.options), title)
        for index, text in pages), return_exceptions=True)
    out = []
    for unit in UNITS:
        sources: dict = {}  # khóa giá trị → [(số trang, finding)]
        for page_no, (answer, (index, _)) in enumerate(zip(answers, pages)):
            for finding in ([] if isinstance(answer, BaseException) else answer):
                finding = replace(finding, inspector=INSPECTOR, doc=index, values=_tidy_card(finding, case))
                key = _unit_key(unit, finding.values) if finding.unit is unit else None
                if key is not None and not engine.reject_reason(finding, case):
                    sources.setdefault(key, []).append((page_no, finding))
        if not sources:
            continue

        def support(key, values) -> int:
            return len({page_no for page_no, _ in sources.get(key, [])}) + _card_backs(unit, values, case)

        ranked = sorted(sources, key=lambda key: -support(key, sources[key][0][1].values))
        best = ranked[0]
        finding = max((f for _, f in sources[best]), key=lambda f: len(f.values))
        best_support = support(best, finding.values)
        current = {spec.name: case.values.get(spec.name) for spec in unit.fields}
        current_support = support(_unit_key(unit, current), current)
        runner_up = support(ranked[1], sources[ranked[1]][0][1].values) if len(ranked) > 1 else 0
        backed = best_support >= _MIN_SUPPORT and best_support > max(current_support, runner_up)
        evidence = (f"{best_support} nguồn độc lập (trang đọc riêng / vùng MRZ) cùng ghi giá trị của B; giá trị của A có "
                    f"{current_support} nguồn",)
        out.append(replace(finding, backed=backed, evidence=evidence))
    return out


_OWNERS = ("người được cấp", "cha / mẹ của người được cấp", "vợ / chồng của người được cấp",
           "người yêu cầu / người nộp", "người đi khai", "người khác")

# Dân tộc: lượt trích hay bỏ sót dòng "Dân tộc" chung dòng với giới tính / ngày sinh. Lượt đọc chung các trang ở
# trên cũng hay bỏ qua ô này → câu hỏi đóng riêng trên các dòng có chữ "Dân tộc" (kèm vài dòng phía trên để biết
# dòng thuộc khối của ai), chỉ khi lượt trích bỏ trống.
_ETHNIC_CONTEXT_LINES = 4
_ETHNIC_MAX_LINES = 12
_ETHNIC_MAX_TOKENS = 200
_ETHNIC_PROMPT = """<vai_tro>
Bạn là THANH TRA NHÂN THÂN của dây chuyền soát hồ sơ {title}. Bạn chỉ thấy các DÒNG có chữ "Dân tộc" đã chắt từ
OCR, mỗi dòng có số thứ tự trong ngoặc vuông, kèm vài dòng đứng ngay phía trên để biết dòng nằm trong khối của ai.
</vai_tro>

<nhiem_vu>
Người được cấp: {subject}. Chọn ĐÚNG MỘT dòng ghi dân tộc của CHÍNH người được cấp — khối người được khai sinh trên
giấy khai sinh, khối người được cấp trên tờ khai, cột của chính người đó trên giấy kết hôn, khối người chết trên
trích lục khai tử, thẻ CMND của chính họ. KHÔNG lấy dân tộc của cha, mẹ, vợ / chồng, người yêu cầu, người đi khai.
"value" chép đúng chữ đứng sau nhãn "Dân tộc" của người đó, bỏ số chú thích kiểu "(2)". Không dòng nào là của
người được cấp → null. Thà thiếu còn hơn sai.
</nhiem_vu>

<dinh_dang_tra_ve>
Chỉ trả MỘT object JSON: {{"dong": <số thứ tự dòng>, "value": "<dân tộc>", "thuoc_ve": "<một lựa chọn>"}} hoặc
{{"dong": null}}. "thuoc_ve" chọn ĐÚNG MỘT lựa chọn dưới đây, chép nguyên chữ, trả lời thật:
{owners}
</dinh_dang_tra_ve>"""


def _ethnic_lines(case: Case) -> list[dict]:
    out = []
    for index, document in enumerate(case.documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            if "dan toc" in fold(line):
                out.append({"doc": index, "line": line, "above": lines[max(0, at - _ETHNIC_CONTEXT_LINES):at]})
    return out[:_ETHNIC_MAX_LINES]


async def _ethnic_finding(case: Case, title: str) -> Finding | None:
    if case.values.get("NguoiDuocCap_DanToc"):
        return None
    lines = _ethnic_lines(case)
    if not lines:
        return None
    subject = _subject(case)
    who = ", ".join(part for part in (subject["name"], f"sinh {subject['birth'].strftime('%d/%m/%Y')}"
                                      if subject["birth"] else "", subject["gender"]) if part) or "?"
    listing = []
    for number, item in enumerate(lines, start=1):
        listing += [f"    {above}" for above in item["above"]] + [f"[{number}] {item['line']}", ""]
    raw = await client.chat(
        [{"role": "system", "content": _ETHNIC_PROMPT.format(title=title, subject=who,
                                                             owners="\n".join(f'- "{o}"' for o in _OWNERS))},
         {"role": "user", "content": "Các dòng đã chắt lọc:\n" + "\n".join(listing)}],
        max_tokens=_ETHNIC_MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose="thanh_tra.nhan_than",
    )
    answer = engine.parse_json(raw)
    value = re.sub(r"^\s*\(\s*\d+\s*\)\s*", "", str(answer.get("value") or "")).strip(" .,;:")
    try:
        item = lines[int(answer.get("dong")) - 1]
    except (TypeError, ValueError, IndexError):
        return None
    if not value or fold(value) not in fold(item["line"]):
        return None
    unit = next(unit for unit in UNITS if unit.key == "dan_toc")
    return Finding(INSPECTOR, unit, {"NguoiDuocCap_DanToc": value}, item["line"], item["doc"],
                   owner=str(answer.get("thuoc_ve") or "").strip()[:80],
                   evidence=("lượt trích bỏ trống dân tộc; dòng chứng cứ chọn trong các dòng có chữ \"Dân tộc\"",))

INSPECTOR = Inspector("nhan_than", "NHÂN THÂN người được cấp bản sao", UNITS, RULES, check, signals, _OWNERS,
                      _OWNERS[:1], find=find)
