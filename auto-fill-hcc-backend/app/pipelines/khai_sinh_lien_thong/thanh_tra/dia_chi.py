"""Thanh tra ĐỊA CHỈ hồ sơ liên thông khai sinh: tên xã / phường của nơi sinh, quê quán của trẻ, nơi cư trú của mẹ và cha
mà ô xã trên cổng sẽ TRỐNG (tên xã đọc lệch, lượt trích lấy nhầm tên thôn làm xã). Khung chung ở
_shared/thanh_tra/ten_xa.py (LLM theo danh sách xã hiện hành của tỉnh + xã quầy, rồi mã); ở đây khai các field nguồn của
từng ô địa chỉ — mapper chọn một trong các nguồn, nên soát mọi nguồn: nguồn không lên form thì bản vá không có ô nào đổi."""

from app.pipelines._shared.hospital_lookup import hospital_area
from app.pipelines._shared.thanh_tra import ten_xa
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit
from app.pipelines._shared.thanh_tra.ten_xa import Slot

from ..process import mapper

TITLE = "liên thông đăng ký khai sinh"
_BIRTH = Slot(ten_xa.BIRTH_PLACE_RE, "NƠI SINH của trẻ được khai sinh")
_HOMETOWN = Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của trẻ được khai sinh")
_MOTHER = Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của MẸ")
_FATHER = Slot(ten_xa.RESIDENCE_RE, "Nơi cư trú của CHA")
# (field nguồn, ô địa chỉ, người)
SLOTS = {
    "Tk_NoiSinh": (_BIRTH, "trẻ được khai sinh"),
    "Gcs_NoiSinh": (_BIRTH, "trẻ được khai sinh"),
    "Tk_QueQuanCon": (_HOMETOWN, "trẻ được khai sinh"),
    "ThongTinBo_QueQuan": (Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của CHA (dùng làm quê quán của trẻ)"), "cha của trẻ"),
    "ThongTinMe_QueQuan": (Slot(ten_xa.HOMETOWN_RE, "QUÊ QUÁN của MẸ (dùng làm quê quán của trẻ)"), "mẹ của trẻ"),
    "Tk_NoiCuTruMe": (_MOTHER, "mẹ của trẻ"),
    "ThongTinMe_NoiCuTru": (_MOTHER, "mẹ của trẻ"),
    "Gcs_NoiThuongTruMe": (_MOTHER, "mẹ của trẻ"),
    "Tk_NoiCuTruCha": (_FATHER, "cha của trẻ"),
    "ThongTinBo_NoiCuTru": (_FATHER, "cha của trẻ"),
}
UNITS = tuple(Unit(name, slot.label_text, (Field(name, "địa chỉ {tinh, xa, diaChi}", "area"),))
              for name, (slot, _) in SLOTS.items())
_UNIT = {unit.key: unit for unit in UNITS}

RULES = """
<ten_xa>
Vụ có tín hiệu "ô xã của A không có trong danh mục hiện hành": tên xã của A là chữ OCR đọc lệch (chữ viết tay) hoặc cụm
khác (tên thôn, bản, tổ) bị lấy nhầm làm tên xã, cổng không chọn được nên ô xã TRỐNG. B là tên xã trong danh mục hiện hành
của tỉnh (tỉnh của B là tỉnh hiện hành sau sáp nhập, không phải đổi nơi ở). Dòng trích dẫn có tên B (cho lệch OCR vài chữ)
và là địa chỉ của chính ô đang xét, giấy tờ của chính người đó (CCCD, giấy chứng sinh...), hoặc dòng "Kính gửi: UBND ..."
→ chọn B. Tên xã của A có nguyên văn trên dòng KHÔNG phải lý do giữ A: tên đó không có trong danh mục, giữ A là để ô xã
trống. Dòng trích dẫn là địa chỉ của người khác / nơi khác → KHONG_DU_CAN_CU.
</ten_xa>
"""


def mapped(name: str, value: dict):
    if name in ("Tk_NoiSinh", "Gcs_NoiSinh"):
        area = mapper._area(mapper._norm_birth_place(value))
        return hospital_area(area) if area else area
    return mapper._area(value)


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    slots = {name: slot for name, (slot, _) in SLOTS.items()}
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
    return out


_OWNERS = tuple(dict.fromkeys(owner for _, owner in SLOTS.values()))
INSPECTOR = Inspector("dia_chi", "ĐỊA CHỈ (tên xã) nơi sinh, quê quán của trẻ, nơi cư trú của mẹ, cha", UNITS, RULES,
                      owners=(*_OWNERS, "người khác"), accepted=_OWNERS, find=find)
