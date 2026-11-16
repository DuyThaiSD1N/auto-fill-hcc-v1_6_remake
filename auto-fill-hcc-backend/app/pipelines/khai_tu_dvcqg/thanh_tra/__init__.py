"""Lớp soát thứ hai của thủ tục đăng ký khai tử (Cổng DVC quốc gia mới): các thanh tra soát dữ kiện của người đã được
bước phân vai chốt là người chết + toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các
ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, dinh_danh, quan_he, thong_tin_chet

TITLE = "đăng ký khai tử"
INSPECTORS = (dinh_danh.INSPECTOR, thong_tin_chet.INSPECTOR, dia_chi.INSPECTOR, quan_he.INSPECTOR)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    return await engine.run(Case(documents, context or "", dict(values), options or {}), INSPECTORS, title=TITLE)
