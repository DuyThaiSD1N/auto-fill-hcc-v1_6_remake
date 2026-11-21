"""Thanh tra ĐỊA CHỈ hồ sơ liên thông khai tử: tên xã / phường của nơi cư trú cuối cùng và nơi chết của người chết. Tờ
khai viết tay, OCR đọc lệch tên xã: ô xã trên cổng TRỐNG (tên không có trong danh mục), hoặc bước sửa chính tả của mapper
chọn xã gần chữ nhất — có thể là xã khác (xã cũ lệch 1 chữ thay cho xã nhận hồ sơ lệch 2 chữ). Khung chung ở
_shared/thanh_tra/ten_xa.py (LLM theo danh sách xã hiện hành của tỉnh + xã quầy, rồi mã), bật soát cả ô xã do mã đoán."""

import re

from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit
from app.pipelines._shared.thanh_tra.ten_xa import Slot
from app.pipelines.khai_tu.process import mapper as khai_tu_mapper

TITLE = "liên thông đăng ký khai tử"
_OWNER = "người được đăng ký khai tử (người chết)"
# Field lượt trích → ô địa chỉ. Cccd_NoiCuTru là thẻ của NGƯỜI YÊU CẦU (schema khai tử) nên không soát.
SLOTS = {
    "NguoiMat_NoiCuTruCuoiCung": Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú cuối cùng của NGƯỜI CHẾT"),
    "NguoiMat_NoiChet": Slot(re.compile(r"(?i)n[oơ]i\s*ch[eế]t|n[oơ]i\s*t[uử]\s*vong|ch[eế]t\s*t[aạ]i"),
                             "NƠI CHẾT của người chết"),
}
UNITS = tuple(Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, slot in SLOTS.items())
_UNIT = {unit.key: unit for unit in UNITS}

RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành" (cổng để TRỐNG ô xã) hoặc "mã sửa chính tả đã chọn xã gần
chữ nhất" (cổng chọn xã đó, có thể là xã khác): tên xã của A là chữ OCR đọc lệch (chữ viết tay) hoặc cụm khác (tên thôn,
xóm) bị lấy nhầm làm tên xã. B là tên xã trong danh mục hiện hành của tỉnh. Dòng trích dẫn có tên B (cho lệch OCR vài chữ)
và là nơi cư trú / nơi chết của CHÍNH người chết (khối người chết trên tờ khai, giấy báo tử, thẻ của người chết), hoặc
dòng "Kính gửi: UBND ..." (nơi đăng ký khai tử — chỉ cho nơi cư trú) → chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG
phải lý do giữ A: tên đó không có trong danh mục. Dòng trích dẫn là địa chỉ của người yêu cầu / người khác → KHONG_DU_CAN_CU.
</ten_xa>
"""


def mapped(name: str, value: dict):
    return khai_tu_mapper._area(value)


def _evidence(fix: dict, value) -> str:
    read = str((value or {}).get("xa") or "")
    shown = f"“{read}”" if read else "bỏ trống"
    where = (f"mã sửa chính tả đã chọn xã gần chữ nhất “{fix['guess']}” — có thể là xã khác" if fix.get("guess")
             else "trên cổng sẽ TRỐNG")
    return (f"ô xã của A ({shown}) không có trong danh mục hiện hành, {where}; B là tên xã trong danh mục hiện hành của "
            f"tỉnh {fix['value'].get('tinh')}, có trên dòng trích dẫn "
            f"({'model chọn' if fix['by'] == 'llm' else 'mã chọn'}: {fix['why']})")


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    wards = await ten_xa.fixes(case.values, SLOTS, case.documents, case.options, title=TITLE, mapped=mapped,
                               guessed=True)
    return [Finding(INSPECTOR, _UNIT[name], {name: fix["value"]}, fix["quote"], fix["doc"],
                    "dòng giấy ghi tên xã của địa chỉ", _OWNER, backed=True,
                    evidence=(_evidence(fix, case.values.get(name)),))
            for name, fix in wards.items()]


INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tên xã) nơi cư trú cuối cùng, nơi chết của người chết", UNITS, RULES,
                      owners=(_OWNER, "người yêu cầu / người đi khai tử", "người khác"), accepted=(_OWNER,), find=find)
