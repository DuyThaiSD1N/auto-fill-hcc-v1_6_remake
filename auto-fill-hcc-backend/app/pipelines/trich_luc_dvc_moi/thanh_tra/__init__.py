"""Lớp soát thứ hai của thủ tục cấp bản sao trích lục hộ tịch: ba thanh tra + toà án (khung ở _shared/thanh_tra)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, ho_tich, nhan_than

TITLE = "cấp bản sao trích lục hộ tịch / bản sao giấy khai sinh"
INSPECTORS = (nhan_than.INSPECTOR, ho_tich.INSPECTOR, dia_chi.INSPECTOR)


async def review(documents: list[dict], context: str, values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản; chưa nối vào luồng điền."""
    return await engine.run(Case(documents, context or "", dict(values), options or {}), INSPECTORS, title=TITLE)
