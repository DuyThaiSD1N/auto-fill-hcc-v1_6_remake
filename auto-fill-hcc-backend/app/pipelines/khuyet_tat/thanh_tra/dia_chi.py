"""Thanh tra ĐỊA CHỈ hồ sơ xác định mức độ khuyết tật: tên xã / phường của hộ khẩu thường trú, nơi ở hiện nay của người
khuyết tật, nơi ở của người đại diện, nơi cư trú chủ hồ sơ / người nộp mà ô xã trên cổng sẽ TRỐNG (tên xã đọc lệch, lượt
trích lấy nhầm tên tổ / thôn làm xã, tên xã cũ). Khung chung ở _shared/thanh_tra/ten_xa.py (LLM theo danh sách xã hiện hành
của tỉnh + xã quầy, rồi mã); ở đây khai các field nguồn của từng ô địa chỉ."""

import re

from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit
from app.pipelines._shared.thanh_tra.ten_xa import Slot

from ..process import mapper

TITLE = "xác định mức độ khuyết tật"
_NOW_RE = re.compile(r"(?i)n[oơ]i\s*[oở]\s*hi[eệ]n")
_ANY_RE = re.compile(r"(?i)n[oơ]i\s*c[uư]\s*tr[uú]|th[uư][ờo]ng\s*tr[uú]|place of res|n[oơ]i\s*[oở]\s*hi[eệ]n")
# (field nguồn, ô địa chỉ, người)
SLOTS = {
    "Nkt_ThuongTru": (Slot(ten_xa.RESIDENCE_RE, "HỘ KHẨU THƯỜNG TRÚ của người khuyết tật"), "người khuyết tật"),
    "ChuHoSo_NoiCuTru": (Slot(ten_xa.RESIDENCE_RE, "HỘ KHẨU THƯỜNG TRÚ của người khuyết tật (chủ hồ sơ)"),
                         "người khuyết tật"),
    "Nkt_NoiOHienNay": (Slot(_NOW_RE, "NƠI Ở HIỆN NAY của người khuyết tật"), "người khuyết tật"),
    "Ndd_NoiCuTru": (Slot(_ANY_RE, "Nơi cư trú / nơi ở hiện nay của NGƯỜI ĐẠI DIỆN"), "người đại diện"),
    "NguoiNop_NoiCuTru": (Slot(ten_xa.RESIDENCE_RE, "Nơi thường trú của NGƯỜI NỘP (trên thẻ căn cước của người nộp)"),
                          "người nộp"),
}
UNITS = tuple(Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (slot, _) in SLOTS.items())
_UNIT = {unit.key: unit for unit in UNITS}

RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (chữ viết tay), tên xã cũ
trước sáp nhập, hoặc cụm khác (tên tổ dân phố, thôn, bản) bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B là
tên xã trong danh mục hiện hành của tỉnh. Dòng trích dẫn có tên B (cho lệch OCR vài chữ) và là địa chỉ của chính ô đang xét
(dòng hộ khẩu thường trú / nơi ở hiện nay của đúng người trên đơn, thẻ căn cước của chính người đó), hoặc dòng "Kính gửi:
UBND ..." → chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có trong danh mục, giữ A là để
ô xã trống. Dòng trích dẫn là địa chỉ của người khác / nơi khác → KHONG_DU_CAN_CU.
</ten_xa>
"""


def _ocr(case: Case) -> str:
    return "\n".join(str(document.get("text") or "") for document in case.documents)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    ocr_text = _ocr(case)
    slots = {name: slot for name, (slot, _) in SLOTS.items()}
    wards = await ten_xa.fixes(case.values, slots, case.documents, case.options, title=TITLE,
                               mapped=lambda name, value: mapper._area(value, ocr_text))
    out = []
    for name, fix in wards.items():
        read = str((case.values.get(name) or {}).get("xa") or "")
        out.append(Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                           "dòng giấy ghi tên xã của địa chỉ", SLOTS[name][1], backed=True,
                           evidence=(f"ô xã của A ({f'“{read}”' if read else 'bỏ trống'}) không có trong danh mục hiện "
                                     f"hành nên trên cổng sẽ TRỐNG; B là tên xã trong danh mục hiện hành của tỉnh "
                                     f"{fix['value'].get('tinh')}, có trên dòng trích dẫn "
                                     f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})",)))
    return out


_OWNERS = tuple(dict.fromkeys(owner for _, owner in SLOTS.values()))
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tên xã) thường trú, nơi ở của người khuyết tật, người đại diện, người nộp", UNITS,
                      RULES, owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
