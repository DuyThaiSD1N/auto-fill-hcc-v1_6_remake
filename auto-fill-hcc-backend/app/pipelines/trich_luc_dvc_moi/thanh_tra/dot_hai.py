"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop

from ..process import mapper
from . import dia_chi_ghep, ho_tich, nhan_than, review

_RELATION = "citizenQuanhe"
# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm). Ô quyết định khác lượt đầu thì không
# vá cụm đó: form hiện / ẩn cụm theo ô này, ghi vào cụm đang ẩn là mất giá trị.
_CLUSTERS = (
    (None, sdt_nguoi_nop.INSPECTOR.key, ("citizenPhone",)),
    (None, nhan_than.INSPECTOR.key, ("citizenNDK_HoVaTen", "citizenNDK_NgaySinh", "citizenNDK_SoDinhDanh",
                                     "citizenField13", "citizenField32", "citizenNDK_LoaiGiayToTuyThan",
                                     "citizenNDK_SoGiayToTuyThan", "citizenNDK_NgayCap", "citizenNDK_NoiCap")),
    ("citizenNDK_Noicutru", dia_chi_ghep.INSPECTOR.key, ("citizenNDK_TinhThanh", "citizenNDK_PhuongXa", "citizenField38")),
    ("citizenLoaiViecYeuCau", ho_tich.INSPECTOR.key, ("citizenHoSo_CoQuanDangKy", "citizencauhoi3", "citizencauhoi4",
                                                     "citizencauhoi5")),
)


async def patch(documents: list[dict], context: str, raw_fields: list[dict], base_fields: list[dict],
                options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension;
    ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, context, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    after, _ = mapper.enrich([{"name": name, "value": value} for name, value in verdict.values.items()], options)
    normalize_ui_dates(after)
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    then = {f.get("name"): f.get("value") for f in after}
    # Quan hệ đổi thì khối người được cấp đổi nguồn (tài khoản / giấy tờ) và form đổi bố cục: không vá gì.
    if first.get(_RELATION) != then.get(_RELATION):
        return out
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS:
        if gate is None or first.get(gate) == then.get(gate):
            by.update(dict.fromkeys(cluster, inspector))
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(
        base_fields, after, by, follows={"citizenNDK_PhuongXa": "citizenNDK_TinhThanh"})]
    return out
