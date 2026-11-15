"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, dinh_danh, giay_ho_tich, review

_RELATION = "citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"
# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm). Ô quyết định khác lượt đầu thì không
# vá cụm đó: form hiện / ẩn cụm theo ô này, ghi vào cụm đang ẩn là mất giá trị.
_CLUSTERS = (
    (None, dinh_danh.INSPECTOR.key, ("citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh",
                                     "citizenNDKSoDinhDanh", "citizenNDKSogiaytotuythan", "citizenNDKDantoc")),
    ("citizenNDKnoicutru", dia_chi.INSPECTOR.key, ("citizenNDKTinh_ThTru", "citizenNDKXa_ThTru",
                                                   "citizenNDKDiaChi_ThTru")),
    ("citizenTinhtranghonnhan", giay_ho_tich.INSPECTOR.key, (
        "citizenSoBananQuyetdinhlyhon", "citizenField46", "citizenField47",
        "citizenSogiaychungtuTrichluckhaituBanan", "citizenField50", "citizenField51")),
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
        base_fields, after, by, follows={"citizenNDKXa_ThTru": "citizenNDKTinh_ThTru"})]
    return out
