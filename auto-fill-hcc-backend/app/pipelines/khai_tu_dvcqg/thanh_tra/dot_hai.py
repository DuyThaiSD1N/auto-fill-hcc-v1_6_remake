"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop

from ..process import mapper
from . import dia_chi, dinh_danh, quan_he, review, thong_tin_chet

# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm). Ô quyết định khác lượt đầu thì không vá
# cụm đó: form hiện / ẩn cụm theo ô này, ghi vào cụm đang ẩn là mất giá trị.
_CLUSTERS = (
    (None, sdt_nguoi_nop.INSPECTOR.key, ("citizenPhone",)),
    (None, dinh_danh.INSPECTOR.key, ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh",
                                     "citizenLoaiGiaytotuythan_NgdcKT", "citizenSogiaytotuythan_NgdcKT",
                                     "citizenField19", "citizenNoicapgiaytotuythan_NgdcKT")),
    (None, thong_tin_chet.INSPECTOR.key, ("citizenField56", "citizenNDKLoaidangky")),
    (None, quan_he.INSPECTOR.key, ("citizenmoiquanhe",)),
    ("citizenNDKnoicutru", dia_chi.INSPECTOR.key, ("citizenNDKTinh_Thtru", "citizenNDKXa_Thtru", "citizenNDKDiaChi_Thtru")),
    ("citizenNoichet", dia_chi.INSPECTOR.key, ("citizenNoichet_TrongNuoc",)),
)


async def patch(documents: list[dict], context: str, raw_fields: list[dict], base_fields: list[dict],
                options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension;
    ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, context, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}

    def ui(raw: dict) -> list[dict]:
        fields, _ = mapper.enrich([{"name": name, "value": value} for name, value in raw.items()], options)
        normalize_ui_dates(fields)
        return fields

    after = ui(verdict.values)
    then = {f.get("name"): f.get("value") for f in after}
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
    unchanged = {f.get("name"): f.get("value") for f in ui(values)}
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS:
        if gate is None or first.get(gate) == then.get(gate):
            by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by)]
    return out
