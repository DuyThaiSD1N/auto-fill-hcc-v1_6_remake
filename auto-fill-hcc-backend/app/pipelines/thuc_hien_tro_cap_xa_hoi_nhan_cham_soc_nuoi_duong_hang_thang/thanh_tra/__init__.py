"""Lớp soát thứ hai của thủ tục thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng hằng tháng (form Form.io cổng Bộ Y
tế): thanh tra định danh (đối tượng, người nộp, bên được ủy quyền) và địa chỉ + toà án (khung ở _shared/thanh_tra). Chạy ở
nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, dinh_danh

TITLE = "trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng hằng tháng"
INSPECTORS = (dinh_danh.INSPECTOR, dia_chi.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    return await engine.run(Case(documents, "", dict(values), options or {}), INSPECTORS, title=TITLE)
