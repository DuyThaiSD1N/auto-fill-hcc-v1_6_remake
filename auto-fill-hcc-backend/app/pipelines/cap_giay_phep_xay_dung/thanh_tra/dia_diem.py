"""Thanh tra ĐỊA ĐIỂM XÂY DỰNG cấp giấy phép xây dựng mới: thửa đất, tờ bản đồ, diện tích lô đất, số nhà, đường / phố. Thửa
và tờ bản đồ, diện tích có trên giấy chứng nhận quyền sử dụng đất (giấy in do cơ quan cấp) — đơn viết tay hay đọc lệch;
số nhà, đường / phố là nơi xây dựng hiện nay trên đơn. Ô tỉnh / xã của địa điểm không vá ở đợt 2 (form có hai cặp tỉnh /
xã cùng tên ô) nên không soát ở đây."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, fold

from ..process import mapper
from . import chung

_LO_DAT = Unit("lo_dat", "Thửa đất, tờ bản đồ, diện tích lô đất", (
    Field("Dat_ThuaDatSo", "thửa đất số / lô đất số", "code"),
    Field("Dat_ToBanDoSo", "tờ bản đồ số", "code"),
    Field("Dat_DienTich", "diện tích lô đất, m² (chỉ số)", "free", canon=chung.number_key),
))
_DUONG = Unit("duong_pho", "Số nhà, đường / phố nơi xây dựng", (
    Field("Dat_SoNha", "số nhà", "free", canon=chung.text_key),
    Field("Dat_DuongPho", "tên đường / phố (không có thì tổ / thôn / khu phố)", "free",
          canon=lambda value: chung.text_key(mapper._clean_street(value, None)[1])),
))
# Số nhà, đường / phố không soát ở đợt 2: cán bộ giữ nguyên cách ghi của đơn (tổ, chữ "đường"), thanh tra viết lại thì
# lệch; chữ mẫu / số lô lẫn vào ô đường đã được mapper làm sạch ở lượt đầu.
UNITS = (_LO_DAT,)

RULES = """
<nguon>
- Thửa đất số, tờ bản đồ số, diện tích lô đất: đơn (mục "Địa điểm xây dựng") và GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT
  (giấy in do cơ quan cấp) của CÙNG thửa. Đơn viết tay hay đọc lệch một chữ số: số trên giấy chứng nhận là căn cứ khi hai
  bên chỉ lệch vài chữ số. Giấy chứng nhận ghi thửa KHÁC hẳn (đã tách / hợp thửa) thì theo đơn.
- Số nhà, đường / phố: theo đơn (nơi xây dựng hiện nay). Ô đường / phố chỉ có tên đường / phố (không có thì tổ / thôn /
  khu phố); không kèm số nhà, số thửa / tờ bản đồ, chấm điền của mẫu đơn. Tên đường đơn viết tay đọc lệch vài chữ mà giấy
  chứng nhận in đúng tên đó → theo giấy chứng nhận.
</nguon>

<cach_phan_xu>
- A bỏ trống mà giấy có ghi → chọn B.
- Tín hiệu mã nói A lẫn số thửa / tờ bản đồ / chấm điền vào ô đường phố, hoặc số thửa / tờ bản đồ của A không phải số →
  chọn B nếu B sạch.
- Số thửa / tờ bản đồ của A không có nguyên văn trên giấy nào còn của B có trên giấy chứng nhận → chọn B.
- A và B chỉ khác cách viết (hoa thường, "đường" / "Đường", dấu câu) → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""

_STREET_JUNK_RE = re.compile(r"(?i)\b(lô đất|thửa|tờ bản đồ)\b|\.{2,}|…|đường/phố")


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    if unit is _DUONG and values.get("Dat_DuongPho"):
        dirty = bool(_STREET_JUNK_RE.search(str(values["Dat_DuongPho"])))
        out.append((not dirty, "ô đường / phố " + ("lẫn số thửa / tờ bản đồ / chấm điền của mẫu" if dirty else "sạch")))
    if unit is _LO_DAT:
        for name, label in (("Dat_ThuaDatSo", "số thửa"), ("Dat_ToBanDoSo", "số tờ bản đồ")):
            if values.get(name):
                numeric = bool(re.search(r"\d", str(values[name]))) and not re.search(r"[a-zà-ỹ]{4,}", fold(values[name]))
                out.append((numeric, f"{label} " + ("là số" if numeric else "không phải số")))
    return out


# Dòng thuộc mục ĐỊA ĐIỂM XÂY DỰNG của đơn / giấy chứng nhận; dòng thuộc mục chủ hộ / chủ đầu tư / người đại diện là nơi
# ở của người, không phải nơi xây dựng (hai mục cùng có "Số nhà … đường …").
_SITE_MARKERS = ("dia diem xay dung", "tai so nha", "tai dia chi", "lo dat", "thua dat", "thong tin cong trinh",
                 "dia chi thua dat", "dia chi:")
_PERSON_MARKERS = ("chu ho", "chu dau tu", "nguoi dai dien", "thong tin ve chu", "noi cu tru", "thuong tru",
                   "dia chi lien he", "ho ten", "ho va ten")


def _site_line(quote: str, case: Case) -> bool:
    """Dòng chứng cứ nằm trong mục địa điểm xây dựng: chính dòng có dấu hiệu nơi xây dựng, hoặc dò ngược lên gặp dấu hiệu
    nơi xây dựng trước dấu hiệu mục người."""
    target = fold(quote).strip()
    for document in case.documents:
        lines = [fold(line).strip() for line in str(document.get("text") or "").splitlines()]
        for at, line in enumerate(lines):
            if not target or target not in line:
                continue
            for back in range(at, max(-1, at - 8), -1):
                if any(marker in lines[back] for marker in _SITE_MARKERS):
                    return True
                if any(marker in lines[back] for marker in _PERSON_MARKERS):
                    return False
    return False


_ADMIN_RE = re.compile(r"(?i)\b(phường|xã|thị trấn|quận|huyện|tỉnh|thành phố|tp\.)\s")


_LOT_NO_RE = re.compile(r"^[A-Za-z]{0,3}-?\d[\w/-]*$")


def check(unit: Unit, values: dict, case: Case) -> str:
    if unit is _DUONG and _ADMIN_RE.search(f"{values.get('Dat_DuongPho') or ''} "):
        return "ô đường / phố kèm tên phường xã / tỉnh (thuộc ô tỉnh, xã riêng)"
    for name in ("Dat_ThuaDatSo", "Dat_ToBanDoSo"):
        value = str(values.get(name) or "").strip()
        if unit is _LO_DAT and value and not _LOT_NO_RE.match(value):
            return f"{name}: không phải số / mã thửa gọn (lẫn nhãn, chữ ghi chú)"
    return ""


_PAGE_MARKERS = ("dia diem xay dung", "thua dat", "lo dat", "to ban do", "quyen su dung dat", "tai so nha")


async def find(inspector: Inspector, case: Case, title: str):
    findings = await engine.llm_findings(inspector, chung.narrowed(case, _PAGE_MARKERS), title)
    return [finding for finding in findings if finding.unit is not _DUONG or _site_line(finding.quote, case)]


_ACCEPTED = (chung.DON, chung.GCN)
INSPECTOR = Inspector("dia_diem", "ĐỊA ĐIỂM XÂY DỰNG (thửa đất, tờ bản đồ, diện tích lô, số nhà, đường / phố)", UNITS,
                      RULES, check, signals=signals, owners=chung.OWNERS, accepted=_ACCEPTED, find=find)
