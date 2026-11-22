"""Thanh tra ĐỊA CHỈ hồ sơ đăng ký khai sinh: tên thôn / tổ dân phố / xóm / bản trong phần chi tiết dưới xã.

Tờ khai đăng ký khai sinh viết tay: OCR hay đọc lệch dấu hoặc một hai chữ cái của tên thôn / tổ dân phố (nơi cư
trú của người yêu cầu, cha, mẹ; nơi sinh, quê quán của người được khai sinh). Cách kiểm do MÃ làm, không qua LLM:
tên thôn của lượt trích không có nguyên văn trên giấy nào ngoài tờ khai, mà một dòng của giấy do cơ quan hộ tịch cấp
(trích lục, giấy khai sinh, giấy khai tử) ghi cùng loại đơn vị (thôn / tổ dân phố...) với tên lệch nhẹ, kèm đúng tên
xã của địa chỉ đó → đề xuất tên trên giấy đó. Bản cam đoan, đơn, tờ khai khác không làm căn cứ: cũng do người dân tự
viết / tự gõ, đo trên hồ sơ thật đúng ngang sai. Chỉ thay TÊN, giữ loại đơn vị, số nhà và phần còn lại của lượt trích.
"""

import re
from dataclasses import replace

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold

from . import chu_the, ten_xa
from .chu_the import ROLE_BY_KEY
from .dinh_danh import _edit, declaration_lines

_MAX_LETTER_SLIP = 2

# Loại đơn vị dưới xã. Nhóm cùng nghĩa (tổ dân phố / TDP / tổ) so như nhau; không đổi loại của lượt trích.
_KINDS = {"thon": "thon", "xom": "xom", "ban": "ban", "ap": "ap", "lang": "lang",
          "to dan pho": "tdp", "tdp": "tdp", "to": "tdp", "khu pho": "khu", "khu": "khu", "khoi": "khoi"}
_KIND_RE = r"thôn|xóm|bản|ấp|làng|tổ dân phố|tdp|tổ|khu phố|khu|khối"
_UNIT_RE = re.compile(rf"(?i)(?<![^\W\d_])({_KIND_RE})\.?\s+([^,;()\n]+)")
_STOP_RE = re.compile(r"(?i)\s+(?:xã|phường|thị trấn|huyện|quận|tỉnh|thành phố|tp\.?)\s.*$")

# (field lượt trích, nhãn, vai) — nơi cư trú của người yêu cầu / cha / mẹ, nơi sinh và quê quán của người được ĐKL.
_TARGETS = (
    ("Requester_ResidenceDomestic", "Nơi cư trú người yêu cầu", ROLE_BY_KEY["nyc"].label),
    ("Mother_ResidenceDomestic", "Nơi cư trú của mẹ", ROLE_BY_KEY["me"].label),
    ("Father_ResidenceDomestic", "Nơi cư trú của cha", ROLE_BY_KEY["cha"].label),
    ("Subject_BirthPlaceDomestic", "Nơi sinh người được đăng ký khai sinh", ROLE_BY_KEY["con"].label),
    ("Subject_HometownDomestic", "Quê quán người được đăng ký khai sinh", ROLE_BY_KEY["con"].label),
)
UNITS = tuple(Unit(name, label, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),)) for name, label, _ in _TARGETS)
_UNIT_BY_NAME = {unit.key: unit for unit in UNITS}
_OWNER_BY_NAME = {name: owner for name, _, owner in _TARGETS}

RULES = """
<ten_thon_to>
Mỗi vụ chỉ xét TÊN thôn / tổ dân phố / xóm / bản trong phần chi tiết dưới xã của một địa chỉ. Mã đã kiểm: tên của A
không có nguyên văn trên giấy nào của hồ sơ ngoài tờ khai viết tay, còn B là tên lệch nhẹ (dấu, một hai chữ cái) ghi
trên giấy do cơ quan hộ tịch cấp (trích lục, giấy khai sinh, giấy khai tử) cùng loại đơn vị và cùng tên xã của địa chỉ
đó → chọn B: giấy cơ quan cấp đứng trên chữ viết tay bị OCR đọc lệch.
Hai tên khác hẳn nhau, khác loại đơn vị, hoặc dòng của B là địa chỉ của nơi khác (khác xã) → KHONG_DU_CAN_CU.
</ten_thon_to>

<ten_duong>
Nơi cư trú ghi số nhà + tên đường. Mã đã kiểm: B là tên đường in trên CCCD mang ĐÚNG số định danh của chính người đó,
ngay sau CÙNG số nhà với A, chỉ lệch nhẹ (dấu, một hai chữ cái) với tên đường OCR đọc trên tờ khai viết tay → chọn B:
chữ in trên thẻ đứng trên chữ viết tay bị OCR đọc lệch. Giữ số nhà, tỉnh, xã của A. Hai tên khác hẳn nhau, khác số
nhà, hoặc thẻ là của người khác → KHONG_DU_CAN_CU.
</ten_duong>

<noi_sinh_que_quan>
Nơi sinh / quê quán của người được khai sinh. Mã đã kiểm: mọi dòng cùng nhãn ("Nơi sinh" / "Quê quán") ghi ĐÚNG tên
xã hiện tại của A (tính cả dòng trên tờ khai đăng ký khai sinh không ghi xã) đều chỉ ra một tên thôn / tổ dân phố là B; chi
tiết của A bỏ trống, hoặc là tên đơn vị khác hẳn chỉ có trên dòng ghi xã khác (địa chỉ cũ trước sáp nhập, nơi khác) → chọn B (tên đơn vị đúng như dòng đó, giữ tỉnh / xã của
A). Dòng trích dẫn không có nhãn đó → KHONG_DU_CAN_CU.
</noi_sinh_que_quan>

<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (tờ khai viết tay) hoặc
cụm khác (tên thôn, tổ) bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B là tên xã trong danh mục hiện hành
của tỉnh (tỉnh của B là tỉnh hiện hành sau sáp nhập, không phải đổi nơi ở). Dòng trích dẫn có tên B (cho lệch OCR vài chữ)
và là địa chỉ của chính ô đang xét, giấy tờ của chính người đó (CCCD, giấy khai sinh...), hoặc dòng "Kính gửi: UBND ..."
với nơi cư trú người yêu cầu → chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có
trong danh mục, giữ A là để ô xã trống. Dòng trích dẫn là địa chỉ của người khác / nơi khác → KHONG_DU_CAN_CU.
</ten_xa>
"""


def _spell(value) -> str:
    return " ".join(re.findall(r"[^\W_]+", str(value or "").casefold()))


def _name_of(raw: str) -> str:
    name = _STOP_RE.sub("", raw).strip(" .-")
    return " ".join(name.split())


def units_in(text: str) -> list[tuple[str, str]]:
    """(loại đơn vị, tên) theo thứ tự xuất hiện trong chuỗi."""
    out = []
    for match in _UNIT_RE.finditer(str(text or "")):
        kind = _KINDS.get(fold(match.group(1)).rstrip("."))
        name = _name_of(match.group(2))
        if kind and name:
            out.append((kind, name))
    return out


def printed_lines(documents: list[dict]) -> list[tuple[int, list[str], int, bool]]:
    """(số tài liệu, các dòng của trang, vị trí dòng, trang là giấy cơ quan cấp) của mọi dòng ngoài tờ khai đăng ký
    lại khai sinh viết tay."""
    out = []
    for index, document in enumerate(documents, start=1):
        pages: dict[int, list[tuple[str, bool]]] = {}
        for page, line, handwritten in declaration_lines(document):
            pages.setdefault(page, []).append((line, handwritten))
        for rows in pages.values():
            lines = [line for line, _ in rows]
            official = chu_the.issued(lines)
            out += [(index, lines, at, official) for at, (_, handwritten) in enumerate(rows) if not handwritten]
    return out


def _words(text: str) -> str:
    return f" {' '.join(re.findall(r'[0-9a-z]+', fold(text)))} "


def _near_xa(lines: list[str], at: int, xa: str) -> bool:
    """Dòng ghi tên đơn vị dưới xã thuộc đúng xã của địa chỉ: tên xã trên chính dòng đó, hoặc dòng đó chưa ghi xã nào
    và dòng ngay sau ghi tên xã (địa chỉ in xuống dòng)."""
    if not xa:
        return False
    needle = f" {' '.join(re.findall(r'[0-9a-z]+', fold(xa)))} "
    if needle in _words(lines[at]):
        return True
    if re.search(r" (?:xa|phuong|thi tran) ", _words(lines[at])):
        return False
    return at + 1 < len(lines) and needle in _words(lines[at + 1])


def _xa_name(value: dict) -> str:
    return re.sub(r"(?i)^(xã|phường|thị trấn|đặc khu)\s+", "", str(value.get("xa") or "")).strip()


def address_finding(name: str, value, documents: list[dict], lines: list) -> Finding | None:
    if not isinstance(value, dict):
        return None
    detail = str(value.get("diaChi") or "")
    xa = _xa_name(value)
    if not detail or "chet" in fold(detail) or not xa:
        return None
    found = units_in(detail)
    if len(found) != 1:
        return None
    kind, ours = found[0]
    if any(_spell(ours) in _spell(page[at]) for _, page, at, _ in lines):
        return None  # tên của lượt trích đã có nguyên văn ngoài tờ khai
    candidates: dict[str, dict] = {}
    for doc, page, at, official in lines:
        if not official:
            continue
        for their_kind, theirs in units_in(page[at]):
            if their_kind != kind or len(theirs.split()) != len(ours.split()) or _spell(theirs) == _spell(ours):
                continue
            if _edit(fold(theirs), fold(ours)) > _MAX_LETTER_SLIP or not _near_xa(page, at, xa):
                continue
            slot = candidates.setdefault(_spell(theirs), {"name": theirs, "quote": page[at], "doc": doc, "count": 0})
            slot["count"] += 1
    if len(candidates) != 1:
        return None
    best = next(iter(candidates.values()))
    fixed = detail.replace(ours, best["name"], 1)
    if fixed == detail:
        return None
    return Finding(INSPECTOR, _UNIT_BY_NAME[name], {name: {**value, "diaChi": fixed}}, best["quote"], best["doc"],
                   "giấy cơ quan hộ tịch cấp ghi cùng loại đơn vị, cùng xã", _OWNER_BY_NAME[name], backed=True,
                   evidence=(f"tên đơn vị dưới xã của A không có nguyên văn trên giấy nào ngoài tờ khai viết tay; B lấy theo "
                             f"{best['count']} dòng của giấy do cơ quan hộ tịch cấp, cùng loại đơn vị, tên lệch nhẹ, "
                             f"cùng tên xã {xa}",))


# Nơi sinh / quê quán trên tờ khai đăng ký khai sinh chỉ có ở mục người được khai sinh: dòng có nhãn đó là của
# đúng người, đúng ô. Nơi cư trú KHÔNG làm theo cách này: tờ khai ghi cho cả người yêu cầu, mẹ, cha, và dòng ghi xã hiện
# tại hay là nơi ở của người yêu cầu trong khi cha / mẹ (đã mất, ở nơi khác) có thôn riêng.
_LABELS = {"Subject_BirthPlaceDomestic": ("noi sinh", "nơi sinh"), "Subject_HometownDomestic": ("que quan", "quê quán")}
_ANY_XA_RE = re.compile(r" (?:xa|phuong|thi tran) ")


def _labeled_rest(line: str, label: str) -> str:
    """Phần sau nhãn của dòng "Nơi sinh: ..." / "Quê quán: ..." (bỏ số chú thích "(4)"); không phải dòng nhãn → ""."""
    if not fold(line).startswith(label):
        return ""
    rest = line.split(":", 1)[1] if ":" in line else line[len(label):]
    return re.sub(r"^\s*\(\d+\)\s*", "", rest).strip()


def declared_detail_finding(name: str, value, documents: list[dict]) -> Finding | None:
    """Các dòng nơi sinh / quê quán ghi thôn / tổ dân phố kèm đúng tên xã (có chữ "xã" / "phường") của lượt trích — hoặc
    dòng trên tờ khai đăng ký khai sinh không ghi xã — cùng chỉ ra MỘT tên đơn vị, mà lượt trích bỏ trống phần chi tiết hoặc lấy
    tên đơn vị khác hẳn, không có trên dòng nào như thế (thường là địa chỉ cũ trước sáp nhập, hay địa chỉ ở dòng khác) →
    đề xuất tên đó."""
    if name not in _LABELS or not isinstance(value, dict):
        return None
    label, label_text = _LABELS[name]
    xa = _xa_name(value)
    detail = str(value.get("diaChi") or "").strip()
    if not xa or "chet" in fold(detail):
        return None
    current = re.compile(rf" (?:xa|phuong|thi tran) {' '.join(re.findall(r'[0-9a-z]+', fold(xa)))} ")
    found: dict[str, dict] = {}
    rests: list[str] = []
    for index, document in enumerate(documents, start=1):
        for _, line, handwritten in declaration_lines(document):
            rest = _labeled_rest(line, label)
            words = _words(rest)
            # Dòng ghi đúng xã hiện tại; dòng tờ khai không ghi xã nào cũng là của ô này. Dòng ghi xã khác (địa chỉ cũ
            # trước sáp nhập, nơi khác) không dùng.
            if not rest or not (current.search(words) or (handwritten and not _ANY_XA_RE.search(words))):
                continue
            rests.append(rest)
            for match in _UNIT_RE.finditer(rest):
                unit = _name_of(match.group(2))
                if unit and _KINDS.get(fold(match.group(1)).rstrip(".")):
                    # "TDP Tổ dân phố X": tên đã mang loại đơn vị thì không ghép thêm loại lần nữa.
                    text = unit if _UNIT_RE.match(unit) else f"{match.group(1)} {unit}"
                    found.setdefault(_spell(text), {"text": text[:1].upper() + text[1:], "quote": line, "doc": index})
    if len(found) != 1:
        return None
    best = next(iter(found.values()))
    ours = units_in(detail)
    if ours and any(_spell(ours[0][1]) in _spell(rest) for rest in rests):
        return None  # tên đơn vị của lượt trích đã có trên một dòng như thế
    if ours and _edit(fold(ours[0][1]), fold(units_in(best["text"])[0][1] if units_in(best["text"]) else best["text"])) \
            <= _MAX_LETTER_SLIP:
        return None  # chỉ lệch dấu / một hai chữ: OCR dòng nào cũng có thể lệch, không đổi theo một dòng
    if not ours and detail:
        return None  # chi tiết không có loại đơn vị (số nhà, tên bệnh viện...) — không đụng
    return Finding(INSPECTOR, _UNIT_BY_NAME[name], {name: {**value, "diaChi": best["text"]}}, best["quote"], best["doc"],
                   f"dòng {label_text} ghi đúng xã {xa}", _OWNER_BY_NAME[name], backed=True,
                   evidence=(f"mọi dòng {label_text} ghi thôn / tổ dân phố kèm đúng xã {xa} (hoặc là dòng tờ khai không "
                             f"ghi xã); chi tiết của A {'bỏ trống' if not detail else 'không có trên dòng nào như thế'}",))


# Nơi cư trú ghi "số nhà + tên đường" (không có thôn / tổ): tên đường viết tay trên tờ khai bị OCR đọc lệch một hai chữ
# cái ("Bình" → "Đình"). CCCD của CHÍNH người đó (khớp số định danh) in cùng số nhà kèm tên đường → theo bản in.
_ID_BY_RESIDENCE = {"Requester_ResidenceDomestic": "Requester_IdNumber", "Mother_ResidenceDomestic": "Mother_IdNumber",
                    "Father_ResidenceDomestic": "Father_IdNumber"}
_STREET_RE = re.compile(r"(?i)^\s*(?:số\s+(?:nhà\s+)?)?(\d+[0-9a-z]*(?:/\d+[0-9a-z]*)*)\s+(?:đường\s+)?([^\d,;()\n]+?)\s*$")
_CARD_MARKERS = ("can cuoc", "citizen identity", "identity card", "idvnm")
_RESIDENCE_LABEL_RE = re.compile(r"(?i)(?:nơi\s+thường\s+trú|nơi\s+cư\s+trú|place\s+of\s+residence)[^:]*:")


def _card_pages(documents: list[dict], id_number: str) -> list[tuple[int, list[str]]]:
    """(số tài liệu, các dòng in) của các trang thẻ CCCD / căn cước mang đúng số định danh."""
    out = []
    for index, document in enumerate(documents, start=1):
        pages: dict[int, list[str]] = {}
        for page, line, handwritten in declaration_lines(document):
            if not handwritten:
                pages.setdefault(page, []).append(line)
        for lines in pages.values():
            text = " ".join(lines)
            if any(marker in fold(text) for marker in _CARD_MARKERS) and id_number in re.sub(r"\D", "", text):
                out.append((index, lines))
    return out


def street_finding(name: str, value, documents: list[dict], values: dict) -> Finding | None:
    if name not in _ID_BY_RESIDENCE or not isinstance(value, dict):
        return None
    id_number = re.sub(r"\D", "", str(values.get(_ID_BY_RESIDENCE[name]) or ""))
    detail = str(value.get("diaChi") or "")
    if len(id_number) != 12 or units_in(detail):
        return None
    head = detail.split(",", 1)[0]
    match = _STREET_RE.match(head)
    if not match or len(match.group(2).split()) < 2:
        return None
    house, ours = match.group(1), " ".join(match.group(2).split())
    candidates: dict[str, dict] = {}
    for doc, lines in _card_pages(documents, id_number):
        text = " ".join(lines)
        label = _RESIDENCE_LABEL_RE.search(text)
        if not label:
            continue
        after = text[label.end():]
        found = re.search(rf"(?<![\d/]){re.escape(house)}\s+((?:\S+\s+){{{len(ours.split()) - 1}}}[^\s,;]+)", after)
        if not found:
            continue
        theirs = found.group(1).strip(" ,;.")
        if _spell(theirs) == _spell(ours):
            return None  # thẻ in đúng tên đường của lượt trích
        if _edit(fold(theirs), fold(ours)) > _MAX_LETTER_SLIP:
            continue
        quote = next((line for line in lines if house in line), lines[0])
        candidates.setdefault(_spell(theirs), {"name": theirs, "quote": quote, "doc": doc})
    if len(candidates) != 1:
        return None
    best = next(iter(candidates.values()))
    fixed = detail.replace(ours, best["name"], 1)
    if fixed == detail:
        return None
    return Finding(INSPECTOR, _UNIT_BY_NAME[name], {name: {**value, "diaChi": fixed}}, best["quote"], best["doc"],
                   "CCCD của chính người đó in cùng số nhà", _OWNER_BY_NAME[name], backed=True,
                   evidence=(f"CCCD mang đúng số định danh của người này in số nhà {house} kèm tên đường lệch nhẹ "
                             f"(dấu, một hai chữ cái) so với chữ OCR đọc trên tờ khai viết tay",))


def _ward_evidence(fix: dict, before) -> str:
    read = str((before or {}).get("xa") or "") if isinstance(before, dict) else ""
    return (f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện hành nên trên cổng sẽ TRỐNG; "
            f"B là tên xã trong danh mục hiện hành của "
            f"tỉnh {fix['value'].get('tinh')}, có trên dòng trích dẫn ({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}"
            f": {fix['why']})")


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    lines = printed_lines(case.documents)
    wards = await ten_xa.fixes(case.values, tuple(name for name, _, _ in _TARGETS), case.documents, case.options)
    findings = []
    for name, _, _ in _TARGETS:
        fix = wards.get(name)
        # Tên thôn / tổ soát trên địa chỉ đã sửa xã: một vụ cho cả địa chỉ, không để hai đề xuất ghi đè nhau.
        value = fix["value"] if fix else case.values.get(name)
        finding = declared_detail_finding(name, value, case.documents) or address_finding(
            name, value, case.documents, lines) or street_finding(name, value, case.documents, case.values)
        if finding and fix:
            finding = replace(finding, evidence=(*finding.evidence, _ward_evidence(fix, case.values.get(name))))
        elif fix:
            finding = Finding(INSPECTOR, _UNIT_BY_NAME[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                              "dòng giấy ghi tên xã của địa chỉ", _OWNER_BY_NAME[name], backed=True,
                              evidence=(_ward_evidence(fix, case.values.get(name)),))
        if finding:
            findings.append(finding)
    return findings


_OWNERS = tuple(dict.fromkeys(owner for _, _, owner in _TARGETS))
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tên thôn / tổ dân phố) đăng ký khai sinh", UNITS, RULES,
                      owners=_OWNERS, accepted=_OWNERS, find=find)
