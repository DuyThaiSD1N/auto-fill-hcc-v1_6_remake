"""Lớp soát thứ hai của thủ tục liên thông đăng ký khai sinh (lienthong.dichvucong.gov.vn, form Angular): thanh tra định
danh (cha, mẹ, chủ hộ, trẻ), địa chỉ (tên xã), giấy kết hôn của cha mẹ + toà án (khung ở _shared/thanh_tra). Chạy ở nền
sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, dinh_danh, giay_to

TITLE = "liên thông đăng ký khai sinh"
INSPECTORS = (dinh_danh.INSPECTOR, dia_chi.INSPECTOR, giay_to.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    return await engine.run(Case(documents, "", dict(values), options or {}), INSPECTORS, title=TITLE)
