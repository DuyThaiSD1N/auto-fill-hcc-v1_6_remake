"""Thanh tra ĐỊA CHỈ hồ sơ khai sinh kết hợp nhận cha, mẹ, con: nơi sinh, quê quán, nơi cư trú của trẻ; nơi cư trú của mẹ,
cha, người yêu cầu.

Ba việc:
1. Tên xã / phường mà ô xã trên cổng sẽ TRỐNG (tên xã đọc lệch, lượt trích lấy nhầm tên thôn làm xã) — khung chung ở
   _shared/thanh_tra/ten_xa.py (LLM theo danh sách xã hiện hành của tỉnh + xã quầy, rồi mã).
2. Cách viết tên thôn / tổ trong chi tiết nơi cư trú theo số trang giấy ghi (cùng luật với liên thông khai sinh).
3. Tên đường của nơi cư trú ghi "số nhà + tên đường": tờ khai viết tay bị OCR đọc lệch một hai chữ cái, CCCD của CHÍNH
   người đó (khớp số định danh) in cùng số nhà kèm tên đường → theo bản in.
"""

import re

from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines._shared.thanh_tra.ten_xa import Slot
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra.dinh_danh import _edit
from app.pipelines.khai_sinh_lien_thong.thanh_tra.dia_chi import detail_fix
from app.pipelines.khai_sinh_thuong.process import mapper as birth_mapper

from . import trang

TITLE = "đăng ký khai sinh kết hợp nhận cha, mẹ, con"
_CHILD = "trẻ được khai sinh"
# (field lượt trích) → (ô địa chỉ, người, field số định danh của người đó)
SLOTS = {
    "Child_BirthPlaceDomestic": (Slot(ten_xa.BIRTH_PLACE_RE, "NƠI SINH của trẻ được khai sinh"), _CHILD, ""),
    "Child_OriginDomestic": (Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của trẻ được khai sinh"), _CHILD, ""),
    "Child_ResidenceDomestic": (Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của TRẺ được khai sinh"), _CHILD, ""),
    "Mother_ResidenceDomestic": (Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của MẸ"), "mẹ của trẻ", "Mother_IdNumber"),
    "Father_ResidenceDomestic": (Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của CHA"), "cha của trẻ", "Father_IdNumber"),
    "Requester_ResidenceDomestic": (Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của NGƯỜI YÊU CẦU"), "người yêu cầu",
                                    "Requester_IdNumber"),
}
UNITS = tuple(Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (slot, _, _) in SLOTS.items())
_UNIT = {unit.key: unit for unit in UNITS}
_DETAIL_SLOTS = ("Mother_ResidenceDomestic", "Father_ResidenceDomestic", "Requester_ResidenceDomestic",
                 "Child_ResidenceDomestic")

RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (chữ viết tay) hoặc cụm
khác (tên thôn, bản, tổ) bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B là tên xã trong danh mục hiện hành
của tỉnh (tỉnh của B là tỉnh hiện hành sau sáp nhập, không phải đổi nơi ở). Dòng trích dẫn có tên B (cho lệch OCR vài chữ)
và là địa chỉ của chính ô đang xét, giấy tờ của chính người đó (CCCD, giấy chứng sinh...), hoặc dòng "Kính gửi: UBND ..."
→ chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có trong danh mục, giữ A là để ô xã
trống. Dòng trích dẫn là địa chỉ của người khác / nơi khác → KHONG_DU_CAN_CU.
</ten_xa>
<chi_tiet>
Vụ có tín hiệu mã "cách viết tên thôn / tổ": A và B là CÙNG một nơi (cùng xã, cùng tên thôn / tổ), chỉ lệch dấu / 1–2 chữ
cái do OCR. B là cách viết ghi trên NHIỀU trang giấy hơn (có giấy in), kể cả dòng nơi cư trú của người khác trong hồ sơ
(cha mẹ ở cùng thôn) → chọn B dù dòng trích dẫn là của người kia: chỉ sửa chữ, không đổi nơi ở.
</chi_tiet>
<ten_duong>
Nơi cư trú ghi số nhà + tên đường. Mã đã kiểm: B là tên đường in trên CCCD mang ĐÚNG số định danh của chính người đó,
ngay sau CÙNG số nhà với A, chỉ lệch nhẹ (dấu, một hai chữ cái) với tên đường OCR đọc trên tờ khai viết tay → chọn B:
chữ in trên thẻ đứng trên chữ viết tay bị OCR đọc lệch. Giữ số nhà, tỉnh, xã của A. Hai tên khác hẳn nhau, khác số
nhà, hoặc thẻ là của người khác → KHONG_DU_CAN_CU.
</ten_duong>
"""

_MAX_LETTER_SLIP = 2
_STREET_RE = re.compile(r"(?i)^\s*(?:số\s+(?:nhà\s+)?)?(\d+[0-9a-z]*(?:/\d+[0-9a-z]*)*)\s+(?:đường\s+)?([^\d,;()\n]+?)\s*$")
_CARD_MARKERS = ("can cuoc", "citizen identity", "identity card", "idvnm")
_RESIDENCE_LABEL_RE = re.compile(r"(?i)(?:nơi\s+thường\s+trú|nơi\s+cư\s+trú|place\s+of\s+residence)[^:]*:")
# Chi tiết có loại đơn vị dưới xã (thôn / tổ...) thì không phải "số nhà + tên đường".
_UNIT_WORD_RE = re.compile(r"(?i)(?<![^\W\d_])(?:thôn|xóm|bản|ấp|làng|tổ|khu|khối|tdp)(?![^\W\d_])")


def _spell(value) -> str:
    return " ".join(re.findall(r"[^\W_]+", str(value or "").casefold()))


def street_fix(detail, id_number: str, page_list: list[dict]) -> dict | None:
    """Tên đường trong chi tiết "số nhà + tên đường" của A lệch dấu / một hai chữ cái so với tên đường in sau CÙNG số nhà
    trên CCCD mang đúng số định danh của người đó → {"diaChi", "quote", "doc"}."""
    detail = str(detail or "")
    if len(id_number) != 12 or _UNIT_WORD_RE.search(detail):
        return None
    match = _STREET_RE.match(detail.split(",", 1)[0])
    if not match or len(match.group(2).split()) < 2:
        return None
    house, ours = match.group(1), " ".join(match.group(2).split())
    candidates: dict[str, dict] = {}
    for page in page_list:
        text = " ".join(page["lines"])
        if not any(marker in fold(text) for marker in _CARD_MARKERS) or id_number not in trang.digits(text):
            continue
        label = _RESIDENCE_LABEL_RE.search(text)
        found = label and re.search(rf"(?<![\d/]){re.escape(house)}\s+((?:\S+\s+){{{len(ours.split()) - 1}}}[^\s,;]+)",
                                    text[label.end():])
        if not found:
            continue
        theirs = found.group(1).strip(" ,;.")
        if _spell(theirs) == _spell(ours):
            return None  # thẻ in đúng tên đường của lượt trích
        if _edit(fold(theirs), fold(ours)) > _MAX_LETTER_SLIP:
            continue
        quote = next((line for line in page["lines"] if house in line), page["lines"][0])
        candidates.setdefault(_spell(theirs), {"name": theirs, "quote": quote, "doc": page["doc"]})
    if len(candidates) != 1:
        return None
    best = next(iter(candidates.values()))
    fixed = detail.replace(ours, best["name"], 1)
    return {"diaChi": fixed, "quote": best["quote"], "doc": best["doc"]} if fixed != detail else None


def mapped(name: str, value: dict):
    return birth_mapper._area(value)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    slots = {name: slot for name, (slot, _, _) in SLOTS.items()}
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE, mapped=mapped)
    out = []
    for name, fix in wards.items():
        read = str((case.values.get(name) or {}).get("xa") or "")
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", SLOTS[name][1], backed=True,
                           evidence=(f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện "
                                     f"hành nên trên cổng sẽ TRỐNG; B là tên xã trong danh mục hiện hành của tỉnh "
                                     f"{fix['value'].get('tinh')}, có trên dòng trích dẫn "
                                     f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})",)))
    page_list = trang.pages(case.documents)
    for name in _DETAIL_SLOTS:
        value = case.values.get(name)
        if name in wards or not isinstance(value, dict):
            continue
        fix = detail_fix(value.get("diaChi"), page_list)
        if fix:
            out.append(Finding(INSPECTOR, _UNIT[name], {name: {**value, "diaChi": fix["diaChi"]}}, fix["quote"],
                               fix["doc"], "dòng giấy ghi tên thôn / tổ của nơi cư trú", SLOTS[name][1], backed=True,
                               evidence=(f"cách viết tên thôn / tổ: {fix['why']}",)))
            continue
        id_field = SLOTS[name][2]
        street = street_fix(value.get("diaChi"), trang.digits(case.values.get(id_field)) if id_field else "", page_list)
        if street:
            out.append(Finding(INSPECTOR, _UNIT[name], {name: {**value, "diaChi": street["diaChi"]}}, street["quote"],
                               street["doc"], "CCCD của chính người đó in cùng số nhà", SLOTS[name][1], backed=True,
                               evidence=("CCCD mang đúng số định danh của người này in cùng số nhà kèm tên đường lệch "
                                         "nhẹ (dấu, một hai chữ cái) so với chữ OCR đọc trên tờ khai viết tay",)))
    return out


_OWNERS = tuple(dict.fromkeys(owner for _, owner, _ in SLOTS.values()))
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ nơi sinh, quê quán, nơi cư trú của trẻ, mẹ, cha, người yêu cầu", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
