"""Thanh tra ĐỊNH DANH CHỦ VĂN BẰNG: họ tên, số định danh, ngày sinh, người ký phiếu. Phiếu đề nghị hay viết tay (OCR đọc
lệch chữ, dấu, chữ số) còn căn cước và văn bằng là giấy in của chính người đó → cùng một người thì theo giấy in.

Thanh tra và lượt trích cùng một mô hình, hai cách viết đều có trên OCR (phiếu ghi một kiểu, căn cước ghi kiểu kia) → mã
đếm số TRANG giấy ghi nguyên văn từng cách viết (kèm vùng MRZ mặt sau căn cước): cách viết của thanh tra được nhiều trang
ghi hơn mới đem ra toà để thay."""

import re
from dataclasses import replace

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, fold, is_empty, locate, parse_date

from . import chung

HO_TEN = Unit("ho_ten", "Họ tên chủ văn bằng", (Field("VanBang_HoTen", "họ, chữ đệm, tên chủ văn bằng"),))
SO = Unit("so_dinh_danh", "Số định danh chủ văn bằng", (
    Field("VanBang_SoGiayTo", "số định danh 12 chữ số (hoặc CMND 9 số) của chủ văn bằng", "code"),))
NGAY_SINH = Unit("ngay_sinh", "Ngày sinh chủ văn bằng", (Field("VanBang_NgaySinh", "ngày sinh, dd/mm/yyyy", "date"),))
NGUOI_KY = Unit("nguoi_ky", "Người đề nghị ký cuối phiếu", (
    Field("Phieu_NguoiViet", "họ tên người đề nghị ký cuối phiếu"),))
UNITS = (HO_TEN, SO, NGAY_SINH, NGUOI_KY)
_NAMES = ("VanBang_HoTen", "Phieu_NguoiViet")
_FALLBACK = {"VanBang_HoTen": "ChuHoSo_HoTen", "VanBang_SoGiayTo": "ChuHoSo_SoGiayTo",
             "VanBang_NgaySinh": "ChuHoSo_NgaySinh", "Phieu_NguoiViet": "VanBang_HoTen"}

RULES = """
<mot_nguoi>
Chỉ xét CHỦ VĂN BẰNG: người đứng tên văn bằng, dòng "Tên tôi là" của phiếu đề nghị. Căn cước của người nộp thay / cán bộ
(họ tên khác) không phải nguồn. Người ký cuối phiếu thường chính là chủ văn bằng; người khác ký thì giữ nguyên.
</mot_nguoi>

<nguon>
Phiếu đề nghị thường VIẾT TAY: OCR hay đọc lệch chữ, dấu, chữ số. Căn cước (mặt trước, vùng MRZ mặt sau) và văn bằng là giấy
IN của chính người đó → họ tên, số định danh, ngày sinh theo giấy in. Họ tên chép đúng dấu như giấy in.
</nguon>

<cach_phan_xu>
- A bỏ trống mà giấy của chủ văn bằng có ghi → chọn B.
- Tín hiệu mã: cách viết của B được nhiều trang giấy ghi hơn A (A chỉ có trên phiếu viết tay, B có trên căn cước / văn bằng
  in của CÙNG người: cùng họ, chữ đệm, lệch một chữ hoặc vài chữ số) → chọn B.
- Dòng chứng cứ của B là của người khác (người nộp thay, cán bộ, người thân) → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""

_PAGE_BREAK_RE = re.compile(r"─────\s*Trang\s*\d+\s*/\s*\d+\s*─────")
# Dòng họ tên vùng MRZ mặt sau căn cước: chữ in hoa không dấu nối bằng "<" (vd "NGUYEN<<VAN<A").
_MRZ_NAME_RE = re.compile(r"^[A-Z]+(?:<+[A-Z]+)+<*$")


def _pages(case: Case) -> list[str]:
    return [page for document in case.documents for page in _PAGE_BREAK_RE.split(str(document.get("text") or ""))
            if page.strip()]


def _mrz_names(page: str) -> set[str]:
    return {" ".join(part for part in line.strip().split("<") if part).lower()
            for line in page.splitlines() if _MRZ_NAME_RE.match(line.strip())}


def support(spec: Field, value, case: Case) -> int:
    """Số trang ghi nguyên văn giá trị; họ tên tính thêm trang có vùng MRZ ghi đúng họ tên đó (không dấu)."""
    if is_empty(value):
        return 0
    count = 0
    for page in _pages(case):
        found = bool(locate(spec, value, [{"text": page}]))
        if not found and spec.name in _NAMES:
            found = " ".join(fold(value).split()) in _mrz_names(page)
        count += found
    return count


def _near_name(a, b) -> bool:
    """Cùng người, lệch chính tả: cùng số chữ, khác nhiều nhất một chữ và chữ đó cùng hai ký tự đầu (OCR chữ viết tay)."""
    x, y = fold(a).split(), fold(b).split()
    if len(x) != len(y):
        return False
    diff = [(p, q) for p, q in zip(x, y) if p != q]
    return len(diff) <= 1 and all(p[:2] == q[:2] for p, q in diff)


def _near_digits(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(p != q for p, q in zip(a, b)) <= 2


def check(unit: Unit, values: dict, case: Case) -> str:
    """Chỉ sửa chính tả / chữ số của CÙNG người: lượt trích đã chốt người (định tuyến chủ văn bằng ↔ người nộp ở mapper),
    thanh tra không được đổi sang người khác."""
    spec = unit.fields[0]
    # Lượt trích bỏ trống ô văn bằng thì form đang mang giá trị mapper lấy từ căn cước / tên chủ văn bằng: so với giá trị đó.
    ours = case.values.get(spec.name) or case.values.get(_FALLBACK[spec.name])
    theirs = values.get(spec.name)
    if is_empty(ours) or is_empty(theirs):
        return ""
    if spec.name in _NAMES and not _near_name(ours, theirs):
        return f"{spec.name}: họ tên của người khác (không phải lệch chính tả của cùng người)"
    if spec.kind == "code" and not _near_digits(re.sub(r"\D", "", str(ours)), re.sub(r"\D", "", str(theirs))):
        return f"{spec.name}: số của người khác / khác loại giấy"
    if spec.kind == "date":
        a, b = parse_date(ours), parse_date(theirs)
        if a and b and not _near_digits(a.strftime("%d%m%Y"), b.strftime("%d%m%Y")):
            return f"{spec.name}: ngày sinh của người khác"
    return ""


async def find(inspector: Inspector, case: Case, title: str):
    out = []
    for finding in await engine.llm_findings(inspector, case, title):
        spec = finding.unit.fields[0]
        theirs = support(spec, finding.values.get(spec.name), case)
        ours = support(spec, case.values.get(spec.name), case)
        out.append(replace(finding, backed=theirs >= 2 and theirs > ours, evidence=(
            f"cách viết của B có trên {theirs} trang giấy (kể cả vùng MRZ căn cước), của A có trên {ours} trang",)))
    return out


_ACCEPTED = (chung.PHIEU, chung.VAN_BANG, chung.CCCD, chung.UY_QUYEN)
INSPECTOR = Inspector("dinh_danh", "ĐỊNH DANH CHỦ VĂN BẰNG (họ tên, số định danh, ngày sinh, người ký phiếu)", UNITS, RULES,
                      check, owners=chung.OWNERS, accepted=_ACCEPTED, find=find)
