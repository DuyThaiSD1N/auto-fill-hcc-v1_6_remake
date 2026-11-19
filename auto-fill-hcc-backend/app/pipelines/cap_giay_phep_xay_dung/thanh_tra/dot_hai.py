"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (form Form.io cổng Bộ Xây dựng) cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_diem, dinh_danh, review, thiet_ke, thong_so

# Ô tỉnh / xã KHÔNG vá: form có hai cặp tỉnh / xã cùng tên ô (người nộp, địa điểm công trình) mà bản vá chỉ phân biệt ô
# theo tên.
_BLOCKS = (
    (thong_so.INSPECTOR.key, (
        "data[capCongTrinhNhaO]", "data[soTangNhaO]", "data[chiTietSoTangNhaO]", "data[dienTichXayDungTang1NhaO]",
        "data[tongDienTichSanNhaO]", "data[chiTietDienTichSanNhaO]", "data[chieuCaoCongTrinhNhaO]",
        "data[chiTietChieuCaoNhaO]", "data[cotXayDungNhaO]", "data[khoangLuiNhaO]",
        "data[capCongTrinhKhongTheoTuyen]", "data[soTangCongTrinhKhongTheoTuyen]", "data[chiTietSoTangKhongTheoTuyen]",
        "data[dienTichXayDungKhongTheoTuyen]", "data[tongDienTichSanKhongTheoTuyen]",
        "data[chiTietDienTichSanKhongTheoTuyen]", "data[chieuCaoCongTrinhKhongTheoTuyen]",
        "data[chiTietChieuCaoCongTrinhKhongTheoTuyen]", "data[cotXayDungKhongTheoTuyen]",
        "data[khoangLuiKhongTheoTuyen]", "data[thoiGianDuKienHoanThanh]")),
    (dia_diem.INSPECTOR.key, ("data[loDatSo]", "data[dienTichLoDat]", "data[soNha]", "data[duongPho]")),
    (dinh_danh.INSPECTOR.key, ("data[tenChuHo]", "data[soDinhDanhChuHo]", "data[fullname]", "data[identityNumber]",
                               "data[identityDate]", "data[identityAgency]")),
    (thiet_ke.INSPECTOR.key, ("data[tenDoanhNghiepLapThietKe]", "data[maSoDoanhNghiepLapThietKe]",
                              "data[tenChuNhiemThietKe]", "data[maSoChungChiChuNhiemThietKe]")),
)
# Ô quyết định bố cục form: phán quyết làm đổi ô nào trong số này thì form đang theo nhánh cũ → không vá gì.
_LAYOUT = ("data[loaiCongTrinh]", "data[chonDoiTuong]", "data[loaiHinhChuDauTu]", "data[toChucCaNhanLapThietKe]")


def _ui(values: dict, options: dict) -> list[dict]:
    fields, _ = mapper.enrich([{"name": name, "value": value} for name, value in values.items()], options)
    normalize_ui_dates(fields)
    return [field for field in fields if field.get("occurrence") in (None, 0)]


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension; ``options``:
    options đã dùng cho mapper.enrich ở lượt đầu (kèm ``_ocr_text``)."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    after = _ui(verdict.values, options)
    then = {f.get("name"): f.get("value") for f in after}
    unchanged = {f.get("name"): f.get("value") for f in _ui(values, options)}
    if any(then.get(name) != unchanged.get(name) for name in _LAYOUT):
        return out
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
    by: dict[str, str] = {}
    for inspector, cluster in _BLOCKS:
        by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    base = [field for field in base_fields or [] if isinstance(field, dict) and field.get("occurrence") in (None, 0)]
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base, after, by)]
    return out
