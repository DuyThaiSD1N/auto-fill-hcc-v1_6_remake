"""Thanh tra ĐỊNH DANH cấp giấy phép xây dựng mới: chủ hộ (người đứng tên công trình) và người nộp / được ủy quyền — họ tên,
số định danh; ngày cấp, nơi cấp của người nộp. Họ tên và số theo căn cước (giấy in) của CHÍNH người đó; đơn viết tay hay đọc
lệch dấu / chữ số."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, fold

from . import chung

_CHU_HO = Unit("chu_ho", "Chủ hộ / chủ đầu tư (người đứng tên công trình)", (
    Field("ChuHo_HoTen", "họ, chữ đệm, tên chủ hộ"),
    Field("ChuHo_SoDinhDanh", "số định danh 12 chữ số của chủ hộ", "code"),
))
_NGUOI_NOP = Unit("nguoi_nop", "Người nộp hồ sơ / người được ủy quyền", (
    Field("Applicant_HoTen", "họ, chữ đệm, tên người nộp"),
    Field("Applicant_SoDinhDanh", "số định danh 12 chữ số của người nộp", "code"),
    Field("Applicant_NgayCap", "ngày cấp căn cước của người nộp, dd/mm/yyyy", "date"),
    Field("Applicant_NoiCap", "nơi cấp căn cước của người nộp", "free", canon=chung.text_key),
))
UNITS = (_CHU_HO, _NGUOI_NOP)

RULES = """
<hai_nguoi>
Chủ hộ / chủ đầu tư = người đứng tên công trình (mục "chủ đầu tư / chủ hộ" của đơn, người đứng tên giấy chứng nhận quyền
sử dụng đất). Người nộp = người đi nộp: có giấy ủy quyền thì là BÊN ĐƯỢC ỦY QUYỀN, không có thì chính chủ hộ. Không lấy
nhân thân của người này cho người kia; vợ / chồng cùng đứng tên giấy chứng nhận là hai người khác nhau.
</hai_nguoi>

<nguon>
- Họ tên, số định danh: theo CĂN CƯỚC (giấy in) của CHÍNH người đó; không có căn cước thì giấy chứng nhận quyền sử dụng
  đất / giấy phép xây dựng đã cấp ("Cấp cho") / giấy ủy quyền in; đơn viết tay kém tin nhất. Họ tên chép đúng dấu như giấy in.
- Ngày cấp, nơi cấp của người nộp: theo căn cước của người đó hoặc dòng "căn cước số … cấp ngày … tại …" của giấy ủy quyền.
</nguon>

<cach_phan_xu>
- A bỏ trống mà giấy của CHÍNH người đó có ghi → chọn B.
- Họ tên / số của A không có nguyên văn trên giấy nào, còn B có trên căn cước của chính người đó → chọn B.
- Số định danh của A không đủ 12 chữ số (tín hiệu mã), B đủ 12 chữ số trên căn cước của chính người đó → chọn B.
- Dòng chứng cứ của B là của người khác (vợ / chồng, người được ủy quyền khi đang xét chủ hộ) → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    for name in ("ChuHo_SoDinhDanh", "Applicant_SoDinhDanh"):
        if any(spec.name == name for spec in unit.fields) and values.get(name):
            digits = re.sub(r"\D", "", str(values[name]))
            out.append((len(digits) == 12, f"số định danh {'đủ' if len(digits) == 12 else 'KHÔNG đủ'} 12 chữ số"))
    return out


def _edit(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def check(unit: Unit, values: dict, case: Case) -> str:
    """Chỉ sửa chính tả / chữ số của CÙNG người: lượt trích đã chốt người (chủ hộ theo tài khoản, đơn hai chủ đầu tư…), thanh
    tra không được đổi sang người khác. Lượt trích ghi CMND 9 số theo đơn thì giữ (cán bộ giữ số đơn ghi)."""
    for name_field, number_field in (("ChuHo_HoTen", "ChuHo_SoDinhDanh"), ("Applicant_HoTen", "Applicant_SoDinhDanh")):
        if not any(spec.name == name_field for spec in unit.fields):
            continue
        ours, theirs = case.values.get(name_field), values.get(name_field)
        if ours and theirs:
            a, b = fold(ours).split(), fold(theirs).split()
            if len(a) != len(b) or _edit(" ".join(a), " ".join(b)) > 2:
                return f"{name_field}: họ tên của người khác (không phải lệch chính tả của cùng người)"
        ours_no, theirs_no = re.sub(r"\D", "", str(case.values.get(number_field) or "")), re.sub(
            r"\D", "", str(values.get(number_field) or ""))
        if ours_no and theirs_no and ours_no != theirs_no:
            if len(ours_no) == 9:
                return f"{number_field}: lượt trích ghi CMND 9 số theo đơn — giữ"
            if len(ours_no) == len(theirs_no) and _edit(ours_no, theirs_no) > 2:
                return f"{number_field}: số định danh của người khác"
    return ""


# Trang đơn (mục chủ hộ / người đại diện), căn cước, giấy chứng nhận, giấy ủy quyền.
_MARKERS = ("don de nghi", "chu ho", "chu dau tu", "can cuoc", "chung minh nhan dan", "quyen su dung dat", "uy quyen",
            "identity card", "so dinh danh", "cap cho")


async def find(inspector: Inspector, case: Case, title: str):
    return await engine.llm_findings(inspector, chung.narrowed(case, _MARKERS), title)


_ACCEPTED = (chung.DON, chung.CCCD, chung.GCN, chung.GPXD, chung.UY_QUYEN)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH chủ hộ và người nộp (họ tên, số định danh, ngày / nơi cấp)", UNITS, RULES,
                      check, signals=signals, owners=chung.OWNERS, accepted=_ACCEPTED, find=find)
