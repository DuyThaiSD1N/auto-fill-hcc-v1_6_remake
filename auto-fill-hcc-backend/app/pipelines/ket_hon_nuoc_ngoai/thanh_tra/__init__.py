"""Lớp soát thứ hai của thủ tục đăng ký kết hôn có yếu tố nước ngoài: thanh tra định danh (họ tên theo hộ chiếu) và tình
trạng hôn nhân của hai bên + toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền
đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dinh_danh, tinh_trang

TITLE = "đăng ký kết hôn có yếu tố nước ngoài"
INSPECTORS = (dinh_danh.INSPECTOR, tinh_trang.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    return await engine.run(Case(documents, "", dict(values), options or {}), INSPECTORS, title=TITLE)
