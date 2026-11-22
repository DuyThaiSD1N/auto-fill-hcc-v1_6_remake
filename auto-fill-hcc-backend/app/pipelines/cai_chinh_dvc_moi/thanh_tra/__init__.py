"""Lớp soát thứ hai của thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc: bốn thanh tra +
toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from ..process import mapper
from . import dia_chi_ghep, dinh_danh, giay_to, noi_dung

TITLE = "thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc"
INSPECTORS = (dinh_danh.INSPECTOR, dia_chi_ghep.INSPECTOR, giay_to.INSPECTOR, noi_dung.INSPECTOR,
              sdt_nguoi_nop.INSPECTOR)
# Giấy tờ đăng ký và nội dung đề nghị không có trong tài khoản nên soát ở mọi hồ sơ.
INSPECTORS_ALWAYS = (giay_to.INSPECTOR, noi_dung.INSPECTOR, sdt_nguoi_nop.INSPECTOR)
# Chỉ soát khi người nộp KHÔNG phải người có nội dung thay đổi: "Bản thân" thì cổng chép khối đó từ tài khoản.
INSPECTORS_FOR_OTHERS = (dinh_danh.INSPECTOR, dia_chi_ghep.INSPECTOR)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    options = options or {}
    relation = mapper._relation(values, context or "", options)[0]
    inspectors = INSPECTORS_ALWAYS + (INSPECTORS_FOR_OTHERS if relation == mapper._OTHER else ())
    return await engine.run(Case(documents, context or "", dict(values), options), inspectors, title=TITLE)
