"""Lớp soát thứ hai của thủ tục đăng ký khai sinh: ba thanh tra (định danh gồm họ tên + dân tộc, giấy tờ tùy thân gồm
số định danh + ngày cấp, địa chỉ tên thôn / tổ dân phố) chạy cho các vai đã phân (người được khai sinh, mẹ, cha, người
yêu cầu) + toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, dinh_danh, giay_to

TITLE = "đăng ký khai sinh"
INSPECTORS = (dinh_danh.INSPECTOR, giay_to.INSPECTOR, dia_chi.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (sau bước lọc theo phân vai, trước mapper). Trả giá trị sau phán quyết + biên bản."""
    account = dinh_danh.account_document(options)
    return await engine.run(Case([*documents, *([account] if account else [])], "", dict(values), options or {}),
                            INSPECTORS, title=TITLE)
