"""Lớp soát thứ hai của thủ tục đăng ký lại kết hôn: hai thanh tra (định danh, địa chỉ) chạy cho cả hai vợ chồng + toà
án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py,
app/second_pass). Khuôn chép riêng từ thanh tra của thủ tục đăng ký kết hôn; tờ khai đăng ký lại chia khối vợ / chồng
thay cho bảng hai cột (chu_the.py)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import chu_the, dia_chi, dinh_danh

TITLE = "đăng ký lại kết hôn"
INSPECTORS = (dinh_danh.INSPECTOR, dia_chi.INSPECTOR)


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản. Các thanh tra soát trên giá
    trị mapper sẽ dùng để điền (``chu_the.effective``) và ghi đè vào chính field đó."""
    return await engine.run(Case(documents, "", chu_the.effective(values), options or {}), INSPECTORS, title=TITLE)
