"""Lớp soát thứ hai của thủ tục liên thông khai tử (lienthong.dichvucong.gov.vn, form Angular): thanh tra địa chỉ (tên xã)
của người chết + toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2
(dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi

TITLE = "liên thông đăng ký khai tử"
INSPECTORS = (dia_chi.INSPECTOR,)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    return await engine.run(Case(documents, context or "", dict(values), options or {}), INSPECTORS, title=TITLE)
