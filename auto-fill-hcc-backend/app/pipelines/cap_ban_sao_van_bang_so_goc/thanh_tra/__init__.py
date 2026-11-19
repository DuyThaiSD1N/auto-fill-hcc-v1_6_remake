"""Lớp soát thứ hai của thủ tục cấp bản sao văn bằng, chứng chỉ từ sổ gốc (cổng Bộ GD&ĐT, form Form.io): thanh tra định
danh chủ văn bằng và toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, kết quả thành các ô điền đợt 2
(dot_hai.py, app/second_pass)."""

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from ..process import mapper
from . import dinh_danh

TITLE = "cấp bản sao văn bằng, chứng chỉ từ sổ gốc"
INSPECTORS = (dinh_danh.INSPECTOR,)


async def review(documents: list[dict], values: dict, options: dict | None = None, ocr_text: str = "") -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết + biên bản."""
    values = dict(values)
    # Thanh tra so với đúng giá trị form đang có: lượt trích bỏ trống thì mapper lấy dòng phiếu đọc thẳng từ OCR.
    phieu = mapper._phieu_owner(ocr_text)
    for name, key in (("VanBang_HoTen", "name"), ("VanBang_SoGiayTo", "id"), ("VanBang_NgaySinh", "dob")):
        if not values.get(name) and phieu.get(key):
            values[name] = phieu[key]
    return await engine.run(Case(documents, "", values, options or {}), INSPECTORS, title=TITLE)
