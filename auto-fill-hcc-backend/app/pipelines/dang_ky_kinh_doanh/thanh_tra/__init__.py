"""Lớp soát thứ hai của thủ tục đăng ký thành lập hộ kinh doanh (cổng HkdOnline, điền 8 trang): thanh tra địa chỉ, ngành
nghề, nhân thân, tên hộ + toà án (khung ở _shared/thanh_tra). Chạy ở nền sau lượt điền đầu, trong lúc extension đính kèm hồ
sơ; kết quả là các trang (dot_hai.py, app/second_pass) extension dùng thay khi bắt đầu điền 8 trang."""

import re

from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Result, fold

from . import dia_chi, dinh_danh, nganh_nghe, ten_ho

TITLE = dia_chi.TITLE
INSPECTORS = (dia_chi.INSPECTOR, nganh_nghe.INSPECTOR, dinh_danh.INSPECTOR, ten_ho.INSPECTOR)

# Chủ hộ ghi lại ở khối người nộp (khi chủ hộ tự nộp) và ở phần "Bên ủy quyền" của giấy ủy quyền: giá trị thanh tra sửa của
# chủ hộ chép sang các khối đó — chỉ khi khối đó vốn ghi đúng như chủ hộ (hoặc trống), để không đè giá trị đọc từ nguồn riêng.
_OWNER_COPIES = {
    "ChuHo_HoTen": ("NguoiNop_HoTen", "UyQuyen_NguoiUyQuyen_HoTen"),
    "ChuHo_SoDinhDanh": ("NguoiNop_SoDinhDanh", "UyQuyen_NguoiUyQuyen_SoDinhDanh"),
    "ChuHo_NgaySinh": ("NguoiNop_NgaySinh",),
    "ChuHo_DiaChi": ("NguoiNop_DiaChi",),
}


def _same(a, b) -> bool:
    if isinstance(a, dict) or isinstance(b, dict):
        return a == b
    return " ".join(str(a or "").split()).casefold() == " ".join(str(b or "").split()).casefold()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def sync(before: dict, after: dict) -> dict:
    out = dict(after)
    for source, targets in _OWNER_COPIES.items():
        if _same(after.get(source), before.get(source)):
            continue
        for target in targets:
            if _same(after.get(target), before.get(target)) and before.get(target) not in (None, "", {}) and _same(
                    before.get(target), before.get(source)):
                out[target] = after.get(source)
    # Tên hộ đặt theo họ tên chủ hộ (hay gặp) → sửa theo khi họ tên chủ hộ được sửa.
    name_before, name_after = before.get("ChuHo_HoTen"), after.get("ChuHo_HoTen")
    if not _same(name_after, name_before) and _same(after.get("HoKinhDoanh_Ten"), before.get("HoKinhDoanh_Ten")) and \
            fold(before.get("HoKinhDoanh_Ten")).strip() == fold(name_before).strip():
        out["HoKinhDoanh_Ten"] = str(name_after or "").upper()
    # Mã ngành chính bị sửa theo bảng → ngành chính theo dòng mới.
    rows = after.get("NganhNghe_DanhSach")
    if rows != before.get("NganhNghe_DanhSach") and isinstance(rows, list):
        codes = [_digits(row.get("ma")) for row in rows if isinstance(row, dict)]
        main = _digits(before.get("NganhNghe_MaChinh"))
        if main and main not in codes:
            # Thanh tra giữ thứ tự dòng của lượt trích: mã chính cũ là mã cũ của một dòng vừa được sửa → theo mã mới của dòng đó.
            old_rows = [row for row in before.get("NganhNghe_DanhSach") or [] if isinstance(row, dict)]
            moved = next((new for old, new in zip(old_rows, rows) if isinstance(new, dict)
                          and _digits(old.get("ma")) == main and _digits(new.get("ma")) != main), None)
            row = moved or next((row for row in rows if isinstance(row, dict) and row.get("chinh")), None)
            out["NganhNghe_MaChinh"] = _digits(row.get("ma")) if row else ""
            out["NganhNghe_TenChinh"] = str(row.get("ten") or "") if row else ""
    return out


async def review(documents: list[dict], values: dict, options: dict | None = None) -> Result:
    """Soát lại field lượt trích (trước mapper). ``options["_vision"]``: kết quả (hoặc tác vụ đang chạy) lượt Qwen đọc ảnh
    giấy đề nghị. Trả giá trị sau phán quyết (đã chép sang khối cùng người) + biên bản."""
    verdict = await engine.run(Case(documents, "", dict(values), options or {}), INSPECTORS, title=TITLE)
    return Result(sync(values, verdict.values), verdict.rulings, verdict.timing)
