"""Lớp soát thứ hai của thủ tục gia hạn giấy phép xây dựng (cổng Bộ Xây dựng, form Form.io): ba thanh tra — định danh chủ
hộ / người nộp, thửa đất (dùng chung với cấp mới), giấy phép đã cấp (số, ngày, cơ quan cấp) + thời gian hoàn thành — và
toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import dia_diem, dinh_danh, giay_phep

from ..process import mapper

TITLE = "gia hạn giấy phép xây dựng (nhà ở riêng lẻ, công trình cấp III, IV)"
INSPECTORS = (dinh_danh.INSPECTOR, dia_diem.INSPECTOR,
              giay_phep.inspector(giay_phep.SO, giay_phep.NGAY_CAP, giay_phep.THOI_GIAN))


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    values = dict(values)
    # Người nộp trên form là MỘT người: thiếu thì mapper lấy người đứng đầu của chủ hộ (tên + số đầu tiên).
    if not values.get("Applicant_HoTen") and not values.get("Applicant_SoDinhDanh"):
        values["Applicant_HoTen"] = mapper._first_person(values.get("ChuHo_HoTen"))
        values["Applicant_SoDinhDanh"] = next(iter(mapper._identities(values.get("ChuHo_SoDinhDanh"))), None)
    for suffix in ("HoTen", "SoDinhDanh"):
        if not values.get("ChuHo_HoTen") and not values.get("ChuHo_SoDinhDanh") and values.get(f"Applicant_{suffix}"):
            values[f"ChuHo_{suffix}"] = values[f"Applicant_{suffix}"]
    return await engine.run(Case(documents, "", {k: v for k, v in values.items() if v not in (None, "")},
                                 options or {}), INSPECTORS, title=TITLE)
