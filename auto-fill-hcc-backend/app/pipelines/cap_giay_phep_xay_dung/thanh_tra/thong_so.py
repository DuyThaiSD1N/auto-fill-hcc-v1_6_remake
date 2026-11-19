"""Thanh tra THÔNG SỐ CÔNG TRÌNH cấp giấy phép xây dựng mới: cấp công trình, số tầng, diện tích, chiều cao, cốt, khoảng lùi,
thời gian hoàn thành. Nguồn chính là mục "Nội dung đề nghị cấp phép" của đơn; bản vẽ / thuyết minh (bảng thông số, khung
tên) để bổ sung ô đơn bỏ trống và gỡ số đơn viết tay đọc lệch. Mã thêm tín hiệu tất định: cấp ngoài I–IV, thời gian không
phải số tháng, tổng diện tích sàn không bằng tổng các tầng ở dòng "Trong đó"."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit

from ..process import mapper
from . import chung

_CAP = Unit("cap", "Cấp công trình", (Field("CongTrinh_Cap", "cấp công trình: Cấp III / Cấp IV", "free",
                                            canon=chung.cap_key),))
_SO_TANG = Unit("so_tang", "Số tầng", (
    Field("CongTrinh_SoTang", "số tầng (chỉ số)", "free", canon=chung.number_key),
    Field("CongTrinh_ChiTietSoTang", "cách ghi số tầng nguyên văn (ô 'Trong đó')", "free", canon=chung.detail_key),
))
_DIEN_TICH = Unit("dien_tich", "Diện tích xây dựng tầng 1, tổng diện tích sàn và chi tiết từng tầng", (
    Field("CongTrinh_DienTichXayDung", "diện tích xây dựng tầng 1, m² (chỉ số)", "free", canon=chung.number_key),
    Field("CongTrinh_TongDienTichSan", "tổng diện tích sàn, m² (chỉ số)", "free", canon=chung.number_key),
    Field("CongTrinh_ChiTietDienTichSan", "diện tích sàn từng tầng (ô 'Trong đó')", "free", canon=chung.detail_key),
))
_CHIEU_CAO = Unit("chieu_cao", "Chiều cao công trình và chi tiết từng tầng", (
    Field("CongTrinh_ChieuCao", "chiều cao công trình, m (chỉ số)", "free", canon=chung.number_key),
    Field("CongTrinh_ChiTietChieuCao", "chiều cao từng tầng (ô 'Trong đó')", "free", canon=chung.detail_key),
))
_COT = Unit("cot", "Cốt xây dựng và khoảng lùi", (
    Field("CongTrinh_CotXayDung", "cốt xây dựng, m (chỉ số)", "free", canon=chung.number_key),
    Field("CongTrinh_KhoangLui", "khoảng lùi, m (chỉ số)", "free", canon=chung.number_key),
))
_THOI_GIAN = Unit("thoi_gian", "Thời gian dự kiến hoàn thành", (
    Field("CongTrinh_ThoiGianDuKienHoanThanh", "số tháng dự kiến hoàn thành", "free",
          canon=lambda value: mapper._months(value) or ""),
))
UNITS = (_CAP, _SO_TANG, _DIEN_TICH, _CHIEU_CAO, _COT, _THOI_GIAN)

RULES = """
<nguon>
Nguồn chính là mục "Nội dung đề nghị cấp phép" ("Đối với công trình nhà ở riêng lẻ") của ĐƠN đề nghị cấp giấy phép xây
dựng. Bản vẽ / thuyết minh thiết kế (bảng thống kê diện tích, khung tên, ghi chú cao độ) chỉ dùng khi đơn BỎ TRỐNG mục đó,
hoặc khi số trên đơn viết tay đọc lệch mà bản vẽ in ghi rõ và tín hiệu mã nói số của đơn không khớp chính nó.
</nguon>

<tung_muc>
- Cấp công trình: "Cấp III" / "Cấp IV" ở dòng "Cấp công trình" (đơn ghi số "3" / "4" là cấp III / IV). Không lấy chữ
  của dòng khác.
- Số tầng: chỉ số tầng; chi tiết = cách ghi nguyên văn ở dòng số tầng (vd "<n> tầng + tum").
- Diện tích: diện tích xây dựng TẦNG 1 (không cộng các tầng), tổng diện tích sàn, chi tiết từng tầng. Chi tiết chỉ gồm
  tầng người khai đã điền số; bỏ khung mẫu chấm điền ("Tầng 2: ....m²"), chữ hướng dẫn "(ghi rõ …)", tầng hầm bằng 0.
- Chiều cao: chiều cao công trình và chiều cao từng tầng; không lấy dòng "Cốt …" vào đây.
- Cốt xây dựng, khoảng lùi: chỉ số ở dòng "Cốt xây dựng" / "Khoảng lùi".
- Thời gian dự kiến hoàn thành: số THÁNG ("....3.... tháng" → 3); không lấy năm, ngày làm đơn.
</tung_muc>

<cach_phan_xu>
- A bỏ trống mục mà đơn (hoặc bản vẽ khi đơn bỏ trống) có ghi → chọn B.
- Tín hiệu mã nói giá trị của A không hợp lệ (cấp ngoài I–IV, thời gian không phải số tháng, tổng diện tích sàn không
  bằng tổng các tầng), còn B hợp lệ và có trên giấy → chọn B.
- A và B đều có trên đơn, chỉ khác cách viết (dấu câu, đơn vị, "0" đứng đầu) → KHONG_DU_CAN_CU.
- B lấy từ bản vẽ trong khi đơn ghi rõ một số khác và tín hiệu mã không nói đơn sai → KHONG_DU_CAN_CU.
</cach_phan_xu>
"""

_FLOOR_ITEM_RE = re.compile(r"\s*;\s*|,\s+(?=[^\d\s])")


def floors_total(detail) -> float | None:
    """Tổng diện tích các tầng ở dòng chi tiết (mỗi mục lấy số giá trị cuối, bỏ số thứ tự tầng)."""
    text = mapper._clean_detail(detail)
    if not text:
        return None
    amounts = [values[-1] for part in _FLOOR_ITEM_RE.split(text) if (values := mapper._slot_values(part))]
    return sum(amounts) if len(amounts) >= 2 else None


def signals(unit: Unit, values: dict, case: Case) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    if unit is _CAP and values.get("CongTrinh_Cap"):
        valid = mapper._cap(values["CongTrinh_Cap"]) is not None
        out.append((valid, "cấp công trình " + ("hợp lệ (I–IV)" if valid else "không phải cấp I–IV")))
    if unit is _THOI_GIAN and values.get("CongTrinh_ThoiGianDuKienHoanThanh"):
        valid = mapper._months(values["CongTrinh_ThoiGianDuKienHoanThanh"]) is not None
        out.append((valid, "thời gian " + ("là số tháng hợp lệ" if valid else "không phải số tháng (năm / số lạ)")))
    if unit is _DIEN_TICH:
        total = chung.number_key(values.get("CongTrinh_TongDienTichSan"))
        floors = floors_total(values.get("CongTrinh_ChiTietDienTichSan"))
        if total and floors:
            same = abs(float(total) - floors) <= max(0.5, float(total) * 0.01)
            out.append((same, f"tổng diện tích sàn {total} m² {'bằng' if same else 'KHÁC'} tổng các tầng ở dòng "
                              f"chi tiết ({floors:g} m²)"))
    return out


# Trang đơn (mục nội dung đề nghị cấp phép) và trang bản vẽ / thuyết minh có bảng thông số.
_MARKERS = ("dien tich xay dung", "tong dien tich san", "chieu cao cong trinh", "so tang", "cap cong trinh",
            "cot xay dung", "thoi gian hoan thanh", "du kien thoi gian")


async def find(inspector: Inspector, case: Case, title: str):
    findings = await engine.llm_findings(inspector, chung.narrowed(case, _MARKERS), title)
    # Thời gian hoàn thành chỉ nhận khi dòng chứng cứ ghi theo THÁNG ("Quý IV năm …" không phải số tháng).
    return [finding for finding in findings
            if finding.unit is not _THOI_GIAN or "thang" in chung.text_key(finding.quote)]


_ACCEPTED = (chung.DON, chung.BAN_VE)
INSPECTOR = Inspector("thong_so", "THÔNG SỐ CÔNG TRÌNH (cấp, số tầng, diện tích, chiều cao, cốt, thời gian)", UNITS,
                      RULES, signals=signals, owners=chung.OWNERS, accepted=_ACCEPTED, find=find)
