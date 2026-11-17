"""Lớp soát thứ hai của thủ tục xác định, xác định lại mức độ khuyết tật (form Form.io cổng Bộ Y tế): thanh tra định danh
(người khuyết tật, người đại diện) và địa chỉ (tên xã) + toà án (khung ở _shared/thanh_tra). Bảng dạng khuyết tật / mức độ
(mục III) đã đọc thẳng từ ảnh ở lượt đầu (process/vision.py) nên không soát lại. Chạy ở nền sau lượt điền đầu, kết quả thành
các ô điền đợt 2 (dot_hai.py, app/second_pass)."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result

from . import dia_chi, dinh_danh

TITLE = "xác định mức độ khuyết tật"
INSPECTORS = (dinh_danh.INSPECTOR, dia_chi.INSPECTOR)

# Chủ hồ sơ LUÔN là người khuyết tật; người nộp là người khuyết tật hoặc người đại diện. Thanh tra soát theo NGƯỜI nên
# giá trị đã sửa của người đó được chép sang các khối kia — chỉ khi khối kia vốn ghi đúng như người đó (hoặc trống), để
# không đè giá trị khối đó đọc từ nguồn riêng.
_NKT_TO_OWNER = {"Nkt_HoTen": "ChuHoSo_HoTen", "Nkt_SoDinhDanh": "ChuHoSo_SoDinhDanh", "Nkt_NgaySinh": "ChuHoSo_NgaySinh",
                 "Nkt_GioiTinh": "ChuHoSo_GioiTinh", "Nkt_ThuongTru": "ChuHoSo_NoiCuTru"}
_NKT_TO_REQUESTER = {"Nkt_HoTen": "NguoiNop_HoTen", "Nkt_SoDinhDanh": "NguoiNop_SoDinhDanh",
                     "Nkt_NgaySinh": "NguoiNop_NgaySinh", "Nkt_GioiTinh": "NguoiNop_GioiTinh",
                     "Nkt_ThuongTru": "NguoiNop_NoiCuTru"}
_NDD_TO_REQUESTER = {"Ndd_HoTen": "NguoiNop_HoTen", "Ndd_SoDinhDanh": "NguoiNop_SoDinhDanh",
                     "Ndd_NgaySinh": "NguoiNop_NgaySinh", "Ndd_NoiCuTru": "NguoiNop_NoiCuTru"}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def sync(before: dict, after: dict) -> dict:
    """Chép giá trị thanh tra đã sửa của một người sang các khối cùng người đó (chủ hồ sơ, người nộp)."""
    out = dict(after)
    requester = _digits(before.get("NguoiNop_SoDinhDanh"))
    maps = [_NKT_TO_OWNER]
    if requester and requester in (_digits(before.get("Nkt_SoDinhDanh")), _digits(before.get("ChuHoSo_SoDinhDanh"))):
        maps.append(_NKT_TO_REQUESTER)
    elif requester and requester == _digits(before.get("Ndd_SoDinhDanh")):
        maps.append(_NDD_TO_REQUESTER)
    for mapping in maps:
        for source, target in mapping.items():
            if after.get(source) == before.get(source) or after.get(target) != before.get(target):
                continue  # nguồn không đổi, hoặc chính khối đích đã được thanh tra sửa riêng
            if before.get(target) in (None, "", {}) or before.get(target) == before.get(source):
                out[target] = after.get(source)
    return out


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). Trả giá trị sau phán quyết (đã chép sang khối cùng người) + biên bản."""
    verdict = await engine.run(Case(documents, "", dict(values), options or {}), INSPECTORS, title=TITLE)
    return Result(sync(values, verdict.values), verdict.rulings, verdict.timing)
