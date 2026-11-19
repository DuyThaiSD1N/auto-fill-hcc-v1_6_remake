"""Lớp soát thứ hai của thủ tục cấp giấy phép xây dựng mới (cổng Bộ Xây dựng, form Form.io): bốn thanh tra — thông số công
trình, địa điểm xây dựng, định danh chủ hộ / người nộp, đơn vị thiết kế — và toà án (khung ở _shared/thanh_tra). Chạy ở
nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_diem, dinh_danh, thiet_ke, thong_so

TITLE = "cấp giấy phép xây dựng mới (nhà ở riêng lẻ, công trình cấp III, IV)"
INSPECTORS = (thong_so.INSPECTOR, dia_diem.INSPECTOR, dinh_danh.INSPECTOR, thiet_ke.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    values = dict(values)
    site = values.get("Dat_DiaDiemXayDung")
    # Ô đường / phố trên form lấy phần chi tiết của địa điểm xây dựng khi lượt trích không tách riêng (mapper): thanh tra
    # phải so với đúng giá trị form đang có, không coi là ô trống.
    if not values.get("Dat_DuongPho") and isinstance(site, dict) and str(site.get("diaChi") or "").strip():
        values["Dat_DuongPho"] = site["diaChi"]
    # Khối chủ hộ / người nộp trên form: thiếu bên nào thì mapper lấy bên kia (không ủy quyền thì là một người).
    for mine, other in (("ChuHo", "Applicant"), ("Applicant", "ChuHo")):
        if not values.get(f"{mine}_HoTen") and not values.get(f"{mine}_SoDinhDanh"):
            for suffix in ("HoTen", "SoDinhDanh"):
                if values.get(f"{other}_{suffix}"):
                    values[f"{mine}_{suffix}"] = values[f"{other}_{suffix}"]
    return await engine.run(Case(documents, "", values, options or {}), INSPECTORS, title=TITLE)
