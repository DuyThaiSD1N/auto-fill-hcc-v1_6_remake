"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, dinh_danh, review

# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm) cho từng bên. Ô quyết định khác lượt
# đầu thì không vá cụm đó: form hiện / ẩn cụm theo ô này.
_CLUSTERS = tuple(cluster for side in ("BenNam", "BenNu") for cluster in (
    (None, dinh_danh.INSPECTOR.key, (f"HoTen{side}", f"SoDinhDanh_{side}", f"SoGiayToDinhDanh_{side}", f"NgaySinh{side}",
                                     f"LoaiGiayToDinhDanh_{side}", f"NgayCapDD_{side}", f"NoiCapDD_{side}",
                                     f"DanToc{side}")),
    (f"NoiCuTru_{side}", dia_chi.INSPECTOR.key, (f"NoiCuTru_{side}_TrongNuoc",)),
))


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension;
    ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    after = mapper.enrich([{"name": name, "value": value} for name, value in verdict.values.items()], options)
    normalize_ui_dates(after)
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    then = {f.get("name"): f.get("value") for f in after}
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS:
        if gate is None or first.get(gate) == then.get(gate):
            by.update(dict.fromkeys(cluster, inspector))
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by)]
    return out
