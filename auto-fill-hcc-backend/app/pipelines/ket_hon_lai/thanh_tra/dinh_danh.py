"""Thanh tra ĐỊNH DANH hai bên vợ / chồng của hồ sơ đăng ký lại kết hôn: họ tên, số định danh, ngày sinh, dân tộc,
ngày cấp thẻ.

Cách kiểm của thanh tra định danh thủ tục cấp Giấy XNTTHN (đọc RIÊNG từng trang thành danh sách nhân thân, MÃ nhận
người khi trùng hai trong ba thông tin, giấy in hơn chữ viết tay, vùng MRZ của thẻ), chạy cho từng bên trên cùng một
lượt đọc trang (khuôn chép từ thanh tra định danh của thủ tục đăng ký kết hôn). Phần riêng:
- khối vợ / khối chồng của tờ khai là hai người, mỗi khối một mục; chữ trên tờ khai là nguồn yếu như chữ viết tay;
- ngày cấp thẻ lượt trích bỏ trống thì MÃ đọc ở mặt sau thẻ mang đúng số định danh của bên đó (khối kết thúc bằng
  vùng MRZ).
"""

import asyncio
import re
import unicodedata
from dataclasses import replace

from app.config import settings
from app.pipelines._shared.cccd import id_birth_year, id_gender, mrz_records
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base
from app.services.llm import client

from ..process import runner as process_runner
from ..process.mapper import _edit_distance
from . import chu_the
from .chu_the import SIDES, Side

_TABLE_NOTE = "- người yêu cầu và người được cấp trên tờ khai — hai khối khác nhau là HAI mục, kể cả khi trùng họ tên;"
assert _TABLE_NOTE in base._PAGE_PROMPT
# Lượt đọc một trang: thêm cách đọc khối vợ / chồng của tờ khai đăng ký lại kết hôn.
_PAGE_PROMPT = base._PAGE_PROMPT.replace(_TABLE_NOTE, _TABLE_NOTE + """
- vợ và chồng trên TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN — khối "Họ, chữ đệm, tên của vợ" và khối "Họ, chữ đệm, tên của chồng",
  mỗi khối gồm các dòng ngay dưới nó: mỗi khối là MỘT mục, "vai" ghi "vợ" / "chồng", "loai_giay" là "to_khai", "dong"
  chép nguyên dòng họ tên;""")

RULES = """
<hai_ben>
Hồ sơ đăng ký lại kết hôn có HAI người: chồng (bên nam) và vợ (bên nữ). Mỗi vụ chỉ xét MỘT bên, nêu ở tên mục.
"Người được cấp" trong các luật dưới đây là BÊN ĐANG XÉT. Mã đã nhận từng bản ghi là của bên nào; không lấy thông tin
của bên kia, của con, của cha mẹ hay người làm chứng. Khối vợ / chồng của tờ khai đăng ký lại kết hôn tính như TỜ KHAI
(nguồn yếu nhất, 0,5 điểm). Hồ sơ điền theo THẺ CĂN CƯỚC của chính người đó: A và B ngang điểm nguồn thì không thành vụ (giữ A), trừ khi B ĐỦ DẤU HƠN A.
Họ tên chỉ khác DẤU mà dòng "Tín hiệu mã" ghi cách viết của A chỉ có trên dòng VIẾT TAY (tờ khai) còn B có trên giấy IN
của chính người đó → chọn B: chữ in đứng trên chữ viết tay.
</hai_ben>

<dan_toc_cha_me>
Dòng "Tín hiệu mã" ghi B lấy ở dòng CHA (chồng) / MẸ (vợ) trên giấy khai sinh của con chung, trùng ĐỦ họ tên và
năm sinh của bên đang xét, lượt trích bỏ trống dân tộc → chọn B: giấy khai sinh là giấy do cơ quan cấp, ghi dân tộc
của chính người đó ở vai cha / mẹ.
</dan_toc_cha_me>
""" + base.RULES + """
<ho_ten_giay_khac_the>
Dòng "Tín hiệu mã" ghi B là cách viết họ tên được NHIỀU giấy khác thẻ của chính bên đang xét ghi (bản cam đoan, giấy
khai sinh của con ở dòng cha / mẹ, giấy cư trú, tờ khai), còn cách viết của A chỉ có trên thẻ → chọn B: OCR chữ in hoa
trên thẻ hay rơi / lệch dấu, nhiều giấy độc lập cùng ghi một cách viết thì đó là tên thật.
</ho_ten_giay_khac_the>

<vung_mrz>
Dòng "Tín hiệu mã" ghi B lấy ở vùng MRZ của thẻ mang họ tên bên đang xét (số định danh là 12 chữ số đứng ngay trước
dấu "<<" của dòng "IDVNM...", ngày sinh là sáu chữ số năm-tháng-ngày đầu dòng kế) → chọn B: lượt trích hay cắt nhầm
12 chữ số khác trong dòng "IDVNM...", hoặc đọc lệch chữ số trên mặt thẻ. A là số 9 chữ số (CMND cũ) còn B là số định
danh 12 chữ số của chính người đó trên giấy khác → chọn B. Họ tên in trên mặt thẻ lệch một tiếng với MRZ của chính thẻ
đó (cùng số định danh), còn B là họ tên có dấu trên giấy in khác khớp đúng MRZ → chọn B.
</vung_mrz>

<the_can_cuoc>
Ngày cấp thẻ chỉ thành vụ khi lượt trích BỎ TRỐNG: mã đọc ở mặt sau thẻ, trong khối kết thúc bằng vùng MRZ mang đúng
số định danh của bên đang xét — khối đó chắc chắn là thẻ của người này → chọn B. Ngày hết hạn ("Có giá trị đến")
không phải ngày cấp.
</the_can_cuoc>
"""

_KEYS = {base.NAME: "HoTen", base.NUMBER: "SoDinhDanh", base.BIRTHDAY: "NgaySinh", base.ETHNIC: "DanToc"}
_BASE_UNITS = {unit.key: unit for unit in base.UNITS}


def _units(side: Side) -> tuple[Unit, ...]:
    def renamed(key: str, label: str) -> Unit:
        spec = _BASE_UNITS[key].fields[0]
        return Unit(f"{side.key}.{key}", f"{label} {side.label}", (replace(spec, name=f"{side.card}_{_KEYS[spec.name]}"),))

    return (renamed("ho_ten", "Họ tên"), renamed("so_dinh_danh", "Số định danh cá nhân"),
            renamed("ngay_sinh", "Ngày sinh"), renamed("dan_toc", "Dân tộc"),
            Unit(f"{side.key}.the", f"Ngày cấp thẻ căn cước của {side.label}",
                 (Field(f"{side.card}_NgayCap", "ngày cấp thẻ dd/mm/yyyy", "date"),)))


UNITS_BY_SIDE = {side.key: {unit.key.split(".", 1)[1]: unit for unit in _units(side)} for side in SIDES}
UNITS = tuple(unit for side in SIDES for unit in UNITS_BY_SIDE[side.key].values())
_SIDE_BY_UNIT = {unit.key: side for side in SIDES for unit in UNITS_BY_SIDE[side.key].values()}


def _on_declaration(name_line: str, page_text: str) -> bool:
    """Bản ghi nằm trong TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN (từ đầu tờ khai tới hết khối chữ ký)."""
    if "to khai dang ky lai ket hon" not in fold(page_text):
        return False
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    end = next((i for i, line in enumerate(lines) if "ky, ghi ro ho" in fold(line)), None)
    at = next((i for i, line in enumerate(lines) if name_line and base._name_key(name_line) in base._name_key(line)), None)
    if end is None or at is None:
        return True
    return at <= end + base._SIGNATURE_LINES


async def _read_page(page: dict, title: str) -> list[dict]:
    raw = await client.chat(
        [{"role": "system", "content": _PAGE_PROMPT.format(title=title)},
         {"role": "user", "content": f"Chữ OCR của trang giấy:\n\n{page['text']}"}],
        max_tokens=base._MAX_TOKENS, temperature=0, enable_thinking=settings.agent_reasoning,
        purpose="thanh_tra.dinh_danh",
    )
    people = engine.parse_json(raw).get("nguoi")
    records = []
    for person in people if isinstance(people, list) else []:
        if not isinstance(person, dict) or not str(person.get("ho_ten") or "").strip():
            continue
        kind = str(person.get("loai_giay") or "").strip()
        weak = kind == "to_khai" or _on_declaration(str(person.get("dong") or person["ho_ten"]), page["text"])
        records.append({"name": " ".join(str(person["ho_ten"]).split()), "number": base._digits(person.get("so_dinh_danh")),
                        "birth": base._birth_key(person.get("ngay_sinh")),
                        "birth_text": str(person.get("ngay_sinh") or "").strip(),
                        "ethnic": base._ethnic(person.get("dan_toc")), "role": str(person.get("vai") or "").strip(),
                        "doc": page["doc"], "text": page["text"], "handwritten": weak,
                        "tier": base._LOW_TIER if weak else base._TIERS.get(kind, base._LOW_TIER)})
    return records


def _exact(value) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value or "")).casefold().split())


def _weak_mark_change(finding: Finding, side_case: Case, records: list[dict]) -> bool:
    """Họ tên đề xuất chỉ khác DẤU với lượt trích mà không phải "đủ dấu hơn": cùng một thẻ thường được chụp / quét
    hai lần trong hồ sơ, hai lần đọc lệch dấu của cùng tấm thẻ không phải hai nguồn độc lập → không đề xuất.
    Ngoại lệ: cách viết của lượt trích chỉ có trên dòng VIẾT TAY (tờ khai) còn đề xuất có trên giấy IN — chữ in đứng
    trên chữ viết tay."""
    proposed = finding.values.get(base.NAME)
    current = side_case.values.get(base.NAME)
    if not proposed or fold(proposed) != fold(current):
        return False
    if any("ĐỦ DẤU HƠN" in line for line in finding.evidence):
        return False
    return not _printed_over_handwritten(proposed, current, records)


def _printed_over_handwritten(proposed, current, records: list[dict]) -> bool:
    """Cách viết của lượt trích chỉ có trên dòng VIẾT TAY, cách viết đề xuất có trên giấy IN."""
    ours = [record for record in records if _exact(record["name"]) == _exact(current)]
    theirs = [record for record in records if _exact(record["name"]) == _exact(proposed)]
    return bool(ours) and all(record["handwritten"] for record in ours) and any(
        not record["handwritten"] for record in theirs)


def _backed_by_print(finding: Finding, side_case: Case, records: list[dict]) -> Finding:
    """Họ tên chỉ khác dấu, A chỉ có trên dòng viết tay còn B có trên giấy in → mã đứng về phía B."""
    proposed, current = finding.values.get(base.NAME), side_case.values.get(base.NAME)
    if not proposed or fold(proposed) != fold(current) or not _printed_over_handwritten(proposed, current, records):
        return finding
    return replace(finding, backed=True, evidence=(
        "cách viết họ tên của A chỉ có trên dòng VIẾT TAY (tờ khai), cách viết của B có trên giấy IN của chính người đó",
        *finding.evidence))


def _side_case(case: Case, side: Side) -> Case:
    """Hồ sơ nhìn từ MỘT bên, theo tên field của thanh tra gốc. Số 9 chữ số là CMND cũ, không phải số định danh: để
    trống thì giấy ghi số định danh 12 chữ số của chính người đó (trùng họ tên + ngày sinh) mới được nhận là cùng người
    — thanh tra gốc coi hai số khác hẳn nhau là hai người."""
    identity = chu_the.identity(case.values, side)
    number = identity["number"] if len(identity["number"]) == 12 else ""
    return Case(case.documents, "", {base.NAME: identity["name"], base.NUMBER: number,
                                     base.BIRTHDAY: identity["birth"], base.ETHNIC: identity["ethnic"]}, case.options)


def _mrz_line(documents: list[dict], pattern: str) -> tuple[str, int]:
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if re.search(pattern, re.sub(r"\s+", "", line)):
                return line.strip(), index
    return "", 0


def _mrz_findings(side: Side, case: Case, mrz: list[dict]) -> tuple[list[Finding], str]:
    """Vùng MRZ ở mặt sau thẻ của CHÍNH bên đó (họ tên không dấu trùng hẳn, giới tính đúng, số và ngày sinh trong MRZ
    khớp nhau) ghi số định danh / ngày sinh khác lượt trích → đề xuất theo MRZ: ba dòng in máy đọc ổn định hơn chữ trên
    mặt thẻ, và lượt trích hay cắt nhầm 12 chữ số từ dòng "IDVNM...". Trả thêm số định danh theo MRZ ("" = không có)."""
    identity = chu_the.identity(case.values, side)
    name = " ".join(fold(identity["name"]).split())
    cards = [card for card in mrz if name and card.get("name") == name and card.get("birth")
             and card.get("gender") == side.gender == id_gender(card["id"])
             and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]]
    if len({card["id"] for card in cards}) != 1:
        return [], ""
    card, units, out = cards[0], UNITS_BY_SIDE[side.key], []
    why = (f"vùng MRZ của thẻ mang họ tên {side.label} (không dấu), giới tính và năm sinh trong số định danh khớp ngày "
           f"sinh in ở MRZ",)
    if card["id"] != identity["number"]:
        quote, doc = _mrz_line(case.documents, rf"I[DO]VNM\S*{card['id']}")
        if quote:
            out.append(Finding(INSPECTOR, units["so_dinh_danh"], {f"{side.card}_SoDinhDanh": card["id"]}, quote, doc,
                               f"dòng MRZ ở mặt sau thẻ của {side.label}", side.label, backed=True, evidence=why))
    year, (yy, month, day) = id_birth_year(card["id"]), card["birth"]
    born = parse_date(identity["birth"])
    if year and (not born or (born.day, born.month, born.year) != (day, month, year)):
        quote, doc = _mrz_line(case.documents, rf"^{yy:02d}{month:02d}{day:02d}\d[MF]\d{{6}}")
        if quote and parse_date(f"{day:02d}/{month:02d}/{year}"):
            out.append(Finding(INSPECTOR, units["ngay_sinh"], {f"{side.card}_NgaySinh": f"{day:02d}/{month:02d}/{year}"},
                               quote, doc, f"dòng MRZ ở mặt sau thẻ của {side.label} (năm-tháng-ngày sinh)", side.label,
                               backed=True, evidence=why))
    return out, card["id"]


def _mrz_name_finding(side: Side, case: Case, mrz: list[dict], records: list[dict]) -> Finding | None:
    """Họ tên in trên mặt thẻ bị OCR đọc lệch một tiếng: vùng MRZ của ĐÚNG thẻ đó (cùng 12 chữ số với số định danh đang
    điền) ghi họ tên không dấu khác lượt trích chỉ ở TÊN, và một giấy IN khác của hồ sơ ghi họ tên có dấu khớp đúng MRZ
    → đề xuất cách viết có dấu đó. MRZ không có dấu nên tự nó không cho được họ tên để điền."""
    identity = chu_the.identity(case.values, side)
    current = " ".join(fold(identity["name"]).split())
    own = {card["name"] for card in mrz if card.get("id") == identity["number"] and card.get("name")}
    if len(identity["number"]) != 12 or len(own) != 1:
        return None
    printed = next(iter(own))
    head, _, last = current.rpartition(" ")
    if printed == current or not head or printed.rpartition(" ")[0] != head or (
            _edit_distance(printed.rpartition(" ")[2], last) > 2):
        return None
    spellings = {" ".join(record["name"].split()) for record in records
                 if not record["handwritten"] and " ".join(fold(record["name"]).split()) == printed}
    if len(spellings) != 1:
        return None
    name = next(iter(spellings))
    quote, doc = _mrz_line(case.documents, rf"I[DO]VNM\S*{identity['number']}")
    if not quote:
        return None
    return Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["ho_ten"], {f"{side.card}_HoTen": name}, quote, doc,
                   f"dòng MRZ ở mặt sau thẻ của {side.label}", side.label, backed=True,
                   evidence=(f"vùng MRZ của thẻ mang đúng số định danh {side.label} ghi họ tên không dấu khác lượt trích "
                             f"ở tên; giấy in khác của hồ sơ ghi họ tên có dấu khớp MRZ",))


_PARENT_ROLES = {"nam": ("cha", "bo"), "nu": ("me",)}


def _block_birth_year(record: dict) -> str:
    """Năm sinh in trong khối của người đó trên trang (từ dòng họ tên tới dòng họ tên kế tiếp) khi model không trả: giấy
    khai sinh in "Năm sinh: ..." của cha / mẹ cùng khối với dòng dân tộc."""
    text = fold(record.get("text"))
    at = text.find(fold(record["name"]))
    if at < 0:
        return ""
    block = re.split(r"ho (?:va|,) ?(?:chu dem,? )?ten", text[at + len(fold(record["name"])):], maxsplit=1)[0]
    found = re.search(r"nam sinh\D{0,6}((?:19|20)\d{2})", block)
    return found.group(1) if found else ""


def _parent_ethnic_finding(side: Side, side_case: Case, records: list[dict]) -> Finding | None:
    """Giấy khai sinh của con chung ghi dân tộc ở dòng CHA / MẸ (chỉ kèm họ tên và năm sinh, không đủ điểm để mã nhận
    là chính người đó theo luật chung): bản ghi vai cha (bên nam) / mẹ (bên nữ) trùng ĐỦ họ tên và năm sinh với bên đó
    → bổ sung dân tộc khi lượt trích bỏ trống. Hai giá trị khác nhau thì không đề xuất."""
    if side_case.values.get(base.ETHNIC) or side_case.values.get(base.OTHER_ETHNIC):
        return None
    name = fold(side_case.values.get(base.NAME))
    year = (re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", str(side_case.values.get(base.BIRTHDAY) or "")) or [""])[-1]
    matched = [record for record in records
               if record.get("ethnic") and name and year and fold(record["name"]) == name
               and set(fold(record.get("role")).split()) & set(_PARENT_ROLES[side.key])
               and year in (str(record.get("birth_text") or "") or _block_birth_year(record))]
    if len({fold(record["ethnic"]) for record in matched}) != 1:
        return None
    record = matched[0]
    quote = next((line.strip() for line in record["text"].splitlines()
                  if "dan toc" in fold(line) and fold(record["ethnic"]) in fold(line)), "")
    if not quote:
        return None
    return Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["dan_toc"], {f"{side.card}_DanToc": record["ethnic"]}, quote,
                   record["doc"], f"dòng {record['role']} trên giấy khai sinh của con ghi đúng họ tên và năm sinh của "
                   f"{side.label}", side.label, backed=True,
                   evidence=(f"lượt trích bỏ trống dân tộc; giấy khai sinh của con ghi dân tộc ở dòng {record['role']} "
                             f"trùng đủ họ tên và năm sinh {year} của {side.label}",))


_SELF_ROLES = {"nam": ("cha", "bo", "chong"), "nu": ("me", "vo")}
_MIN_SPELLING_SCORE = 2


def _of_side(record: dict, side: Side, identity: dict) -> bool:
    """Bản ghi là của chính bên đang xét: họ tên trùng khi bỏ dấu, kèm trùng số định danh, trùng ngày sinh, hoặc đứng ở
    vai của chính họ (cha / mẹ của con chung, vợ / chồng)."""
    if fold(record["name"]).split() != fold(identity["name"]).split():
        return False
    if len(identity["number"]) == 12 and record.get("number") == identity["number"]:
        return True
    birth = base._birth_key(identity.get("birth"))
    if birth and record.get("birth") == birth:
        return True
    return bool(set(fold(record.get("role")).split()) & set(_SELF_ROLES[side.key]))


def _is_card(record: dict) -> bool:
    return record.get("tier") == base._CARD_TIER and not record["handwritten"]


def _printed_spelling_finding(side: Side, case: Case, records: list[dict]) -> Finding | None:
    """Họ tên chỉ khác DẤU: cách viết được các giấy KHÁC thẻ của chính người đó ghi nhiều nhất (giấy in 1, viết tay 0,5,
    nhân đôi khi giấy ghi đúng số định danh) thắng cách viết của lượt trích khi hơn hẳn mọi cách viết khác. Thẻ không
    tính: OCR chữ in hoa trên thẻ chính là chỗ hay rơi / lệch dấu."""
    identity = chu_the.identity(case.values, side)
    current = _exact(identity["name"])
    if not current:
        return None
    scores: dict[str, float] = {}
    sample: dict[str, dict] = {}
    pages: dict[str, set] = {}
    for record in records:
        if _is_card(record) or not _of_side(record, side, identity):
            continue
        key = _exact(record["name"])
        weight = (0.5 if record["handwritten"] else 1) * (2 if record.get("number") == identity["number"] else 1)
        scores[key] = scores.get(key, 0) + weight
        pages.setdefault(key, set()).add((record["doc"], record["text"]))
        if key not in sample or (not record["handwritten"] and sample[key]["handwritten"]):
            sample[key] = record
    if not scores:
        return None
    best = max(scores, key=scores.get)
    others = [score for key, score in scores.items() if key != best] + [scores.get(current, 0)]
    # Phải có ít nhất hai trang giấy ghi cách viết đó: một dòng duy nhất (vd dòng chủ hộ trên giấy xác nhận cư trú, đủ
    # điểm nhờ trùng số định danh) có thể chính giấy in sai hoặc OCR rơi dấu — không đủ để đè chữ trên thẻ.
    if (best == current or scores[best] < _MIN_SPELLING_SCORE or scores[best] <= max(others)
            or len(pages[best]) < 2):
        return None
    record = sample[best]
    quote = next((line.strip() for line in record["text"].splitlines() if fold(record["name"]) in fold(line)), "")
    if not quote:
        return None
    name = " ".join(record["name"].split())
    return Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["ho_ten"], {f"{side.card}_HoTen": name}, quote, record["doc"],
                   f"giấy {record['role'] or 'khác thẻ'} ghi họ tên của {side.label}", side.label, backed=True,
                   evidence=(f"cách viết của B được các giấy khác thẻ của {side.label} ghi với {scores[best]:g} điểm, hơn "
                             f"mọi cách viết khác (A: {scores.get(current, 0):g} điểm ngoài thẻ)",))


def _remap(finding: Finding, side: Side) -> Finding:
    unit = UNITS_BY_SIDE[side.key][finding.unit.key]
    values = {f"{side.card}_{_KEYS[name]}": value for name, value in finding.values.items()}
    return replace(finding, inspector=INSPECTOR, unit=unit, values=values, owner=side.label)


def _line_with(documents: list[dict], needle: str) -> tuple[str, int]:
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if needle and needle in fold(line):
                return line.strip(), index
    return "", 0


def _card_finding(side: Side, case: Case, number: str = "") -> Finding | None:
    """Lượt trích bỏ trống ngày cấp mà mặt sau thẻ của chính bên đó có in → đề xuất bổ sung. Ngày cấp đang có thì
    không đổi: ngày mã đọc và ngày lượt trích đọc cùng từ một chữ OCR, mã không chắc hơn. ``number``: số định danh
    theo vùng MRZ của bên đó, khi có."""
    number = number or chu_the.identity(case.values, side)["number"]
    facts = process_runner._card_facts_by_id(case.documents).get(number) if len(number) == 12 else None
    date_name = f"{side.card}_NgayCap"
    printed = parse_date((facts or {}).get("issue_date"))
    if not printed or case.values.get(date_name):
        return None
    proposed = {date_name: printed.strftime("%d/%m/%Y")}
    quote, doc = _line_with(case.documents, facts["issue_date"])
    if not quote:
        return None
    return Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["the"], proposed, quote, doc,
                   f"dòng in ở mặt sau thẻ của {side.label}", side.label, backed=True,
                   evidence=(f"mã đọc ở mặt sau thẻ, trong khối kết thúc bằng vùng MRZ mang đúng số định danh của "
                             f"{side.label}",))


def check(unit: Unit, values: dict, case: Case) -> str:
    side = _SIDE_BY_UNIT[unit.key]
    number = base._digits(values.get(f"{side.card}_SoDinhDanh"))
    gender = id_gender(number) if unit.key.endswith(".so_dinh_danh") else ""
    if gender and gender != side.gender:
        return f"số mã hoá giới tính {gender}, không phải {side.label}"
    return ""


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    # Bên có thẻ của người khác: mapper điền theo tờ khai, không có giá trị thẻ để soát.
    sides = [(side, _side_case(case, side)) for side in SIDES if not chu_the.card_is_other(case.values, side)]
    pages, seen = [], set()
    for _, side_case in sides:
        for page in base.pages(side_case):
            if (page["doc"], page["text"]) not in seen:
                seen.add((page["doc"], page["text"]))
                pages.append(page)
    read = await asyncio.gather(*(_read_page(page, title) for page in pages[:base._MAX_PAGES]), return_exceptions=True)
    records = [record for answer in read if not isinstance(answer, BaseException) for record in answer]
    mrz = [card for document in case.documents for card in mrz_records(document.get("text"))]
    findings = []
    for side, side_case in sides:
        by_mrz, mrz_id = _mrz_findings(side, case, mrz)
        fixed = {finding.unit.key for finding in by_mrz}
        findings += by_mrz
        # Hai cách viết NGANG điểm nguồn: thủ tục gốc cho giấy do cơ quan cấp đứng trên thẻ; hồ sơ này điền theo thẻ
        # căn cước của chính người đó (giấy khác chỉ nhắc tên họ ở vai cha / mẹ của con) → ngang điểm thì giữ.
        # Ngang điểm mà B đủ dấu hơn A (mọi dấu của A có trong B, B thêm dấu) thì lấy B: OCR hay rơi dấu, ít khi thêm.
        findings += [remapped for finding in base.findings_from(records, mrz, side_case)
                     if (not any("NGANG điểm" in line for line in finding.evidence)
                         or any("ĐỦ DẤU HƠN" in line for line in finding.evidence))
                     and not _weak_mark_change(finding, side_case, records)
                     and (remapped := _remap(_backed_by_print(finding, side_case, records), side)).unit.key not in fixed]
        card = _card_finding(side, case, mrz_id)
        if card:
            findings.append(card)
        if not any(finding.unit.key == f"{side.key}.ho_ten" and finding.backed for finding in findings):
            spelled = _printed_spelling_finding(side, case, records)
            if spelled:
                findings = [finding for finding in findings if finding.unit.key != f"{side.key}.ho_ten"] + [spelled]
        if not any(finding.unit.key == f"{side.key}.ho_ten" for finding in findings):
            renamed = _mrz_name_finding(side, case, mrz, records)
            if renamed:
                findings.append(renamed)
        if not any(finding.unit.key == f"{side.key}.dan_toc" for finding in findings):
            parent = _parent_ethnic_finding(side, side_case, records)
            if parent:
                findings.append(parent)
    return findings


_OWNERS = tuple(side.label for side in SIDES)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH hai vợ chồng đăng ký lại kết hôn", UNITS, RULES, check=check,
                      owners=_OWNERS, accepted=_OWNERS, find=find)
