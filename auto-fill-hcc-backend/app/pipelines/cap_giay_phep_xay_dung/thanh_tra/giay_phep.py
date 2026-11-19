"""Thanh tra GIẤY PHÉP XÂY DỰNG ĐÃ CẤP (thủ tục điều chỉnh, gia hạn): số, ngày cấp, cơ quan cấp giấy phép cũ và số tháng dự
kiến hoàn thành theo đơn. Số / ngày / cơ quan in trên chính giấy phép là căn cứ; đơn viết tay hay đọc lệch. Giấy phép cũ
cũng có dòng "Dự kiến thời gian hoàn thành" (thời hạn cũ) — ô của thủ tục lấy theo ĐƠN, không lấy dòng đó."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, fold

from ..process import mapper
from . import chung

SO = Unit("so_gpxd", "Số giấy phép xây dựng đã cấp", (
    Field("GPXD_So", "số giấy phép xây dựng đã cấp (dòng 'Số: …')", "code"),
))
NGAY_CAP = Unit("cap_gpxd", "Ngày cấp, cơ quan cấp giấy phép xây dựng đã cấp", (
    Field("GPXD_NgayCap", "ngày cấp giấy phép, dd/mm/yyyy", "date"),
    Field("GPXD_CoQuanCap", "cơ quan cấp giấy phép", "free", canon=chung.text_key),
))
THOI_GIAN = Unit("thoi_gian", "Dự kiến thời gian hoàn thành theo đơn", (
    Field("CongTrinh_ThoiGianDuKienHoanThanh", "số tháng dự kiến hoàn thành", "free",
          canon=lambda value: mapper._months(value) or ""),
))

RULES = """
<nguon>
- Số, ngày cấp, cơ quan cấp giấy phép xây dựng đã cấp: theo CHÍNH giấy phép (số "Số: …" đầu giấy, ngày "…, ngày … tháng
  … năm …" đầu giấy, cơ quan ban hành ở góc trên bên trái). Dòng "Giấy phép xây dựng số … ngày …" của đơn là nguồn thứ hai
  (viết tay hay đọc lệch).
- Thời gian dự kiến hoàn thành: số THÁNG ở mục "Dự kiến thời gian hoàn thành công trình theo thiết kế điều chỉnh / gia hạn"
  của ĐƠN. Không lấy dòng "Dự kiến thời gian hoàn thành" của giấy phép đã cấp (thời hạn cũ), thời hạn hiệu lực khởi công
  của giấy phép, ngày làm đơn.
</nguon>

<cach_phan_xu>
- A bỏ trống mà giấy có ghi → chọn B.
- Số / ngày cấp giấy phép của A không có nguyên văn trên giấy nào, còn B có trên chính giấy phép → chọn B.
- Tín hiệu mã nói thời gian của A không phải số tháng, B là số tháng ghi trên đơn → chọn B.
- A và B chỉ khác cách viết (hậu tố sau số giấy phép, hoa thường, dấu câu, "0" đứng đầu) → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    if unit is SO and values.get("GPXD_So"):
        numbered = bool(re.search(r"\d", str(values["GPXD_So"])))
        out.append((numbered, "số giấy phép " + ("có chữ số" if numbered else "KHÔNG có chữ số")))
    if unit is THOI_GIAN and values.get("CongTrinh_ThoiGianDuKienHoanThanh"):
        valid = mapper._months(values["CongTrinh_ThoiGianDuKienHoanThanh"]) is not None
        out.append((valid, "thời gian " + ("là số tháng hợp lệ" if valid else "không phải số tháng (năm / số lạ)")))
    return out


def check(unit: Unit, values: dict, case: Case) -> str:
    if unit is SO and values.get("GPXD_So") and not re.search(r"\d", str(values["GPXD_So"])):
        return "số giấy phép không có chữ số"
    if unit is THOI_GIAN and values.get("CongTrinh_ThoiGianDuKienHoanThanh") and mapper._months(
            values["CongTrinh_ThoiGianDuKienHoanThanh"]) is None:
        return "thời gian không phải số tháng"
    return ""


# Trang giấy phép đã cấp và trang đơn (mục giấy phép đã cấp, thời gian hoàn thành).
_MARKERS = ("giay phep xay dung", "hoan thanh")


async def find(inspector: Inspector, case: Case, title: str):
    findings = await engine.llm_findings(inspector, chung.narrowed(case, _MARKERS), title)
    # Thời gian chỉ nhận dòng của ĐƠN ghi theo tháng: giấy phép cũ cũng có dòng "thời gian hoàn thành" (thời hạn cũ).
    return [finding for finding in findings if finding.unit is not THOI_GIAN
            or ("thang" in chung.text_key(finding.quote) and fold(finding.owner) == fold(chung.DON))]


def inspector(*units: Unit) -> Inspector:
    """Mỗi thủ tục chỉ soát các mục mà tờ khai của nó có (điều chỉnh không có ô ngày / cơ quan cấp giấy phép cũ)."""
    return Inspector("giay_phep", "GIẤY PHÉP XÂY DỰNG ĐÃ CẤP (số, ngày, cơ quan cấp) và thời gian hoàn thành", units, RULES,
                     check, signals=signals, owners=chung.OWNERS, accepted=(chung.DON, chung.GPXD), find=find)
