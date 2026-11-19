"""Lớp soát thứ hai của thủ tục cấp điều chỉnh giấy phép xây dựng (cổng Bộ Xây dựng, form Form.io): ba thanh tra — định
danh chủ hộ / người nộp, thửa đất (dùng chung với cấp mới), giấy phép đã cấp + thời gian hoàn thành — và toà án (khung ở
_shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.cap_giay_phep_xay_dung.thanh_tra import dia_diem, dinh_danh, giay_phep

TITLE = "cấp điều chỉnh giấy phép xây dựng (nhà ở riêng lẻ, công trình cấp III, IV)"
INSPECTORS = (dinh_danh.INSPECTOR, dia_diem.INSPECTOR, giay_phep.inspector(giay_phep.SO, giay_phep.THOI_GIAN))


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    values = dict(values)
    # Khối chủ hộ / người nộp trên form: thiếu bên nào thì mapper lấy bên kia (không ủy quyền thì là một người).
    for mine, other in (("ChuHo", "Applicant"), ("Applicant", "ChuHo")):
        if not values.get(f"{mine}_HoTen") and not values.get(f"{mine}_SoDinhDanh"):
            for suffix in ("HoTen", "SoDinhDanh"):
                if values.get(f"{other}_{suffix}"):
                    values[f"{mine}_{suffix}"] = values[f"{other}_{suffix}"]
    return await engine.run(Case(documents, "", values, options or {}), INSPECTORS, title=TITLE)
