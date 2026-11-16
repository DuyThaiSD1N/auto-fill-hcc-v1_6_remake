"""Lớp soát thứ hai của thủ tục cấp bản sao trích lục hộ tịch: ba thanh tra + toà án (khung ở _shared/thanh_tra).
Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from ..process import mapper
from . import dia_chi_ghep, ho_tich, nhan_than

TITLE = "cấp bản sao trích lục hộ tịch / bản sao giấy khai sinh"
INSPECTORS = (nhan_than.INSPECTOR, ho_tich.INSPECTOR, dia_chi_ghep.INSPECTOR)
# Giấy hộ tịch đã đăng ký không có trong tài khoản nên soát ở mọi hồ sơ.
INSPECTORS_ALWAYS = (ho_tich.INSPECTOR,)
# Chỉ soát khi người nộp KHÔNG phải người được cấp: "Bản thân" thì khối người được cấp lấy theo tài khoản.
INSPECTORS_FOR_OTHERS = (nhan_than.INSPECTOR, dia_chi_ghep.INSPECTOR)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    options = options or {}
    event = mapper._event_type(values, context or "")
    relation = mapper._relation(values, context or "", options, event)[0]
    inspectors = INSPECTORS_ALWAYS + (() if relation == mapper._SELF else INSPECTORS_FOR_OTHERS)
    return await engine.run(Case(documents, context or "", dict(values), options), inspectors, title=TITLE)
