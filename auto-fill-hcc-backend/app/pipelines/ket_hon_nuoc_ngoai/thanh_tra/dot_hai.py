"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (eForm cũ x-*) cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dinh_danh, review, tinh_trang

# (thanh tra soát cụm, các ô của cụm) cho từng bên.
_CLUSTERS = tuple(cluster for side in ("BenNam", "BenNu") for cluster in (
    (dinh_danh.INSPECTOR.key, (f"HoTen{side}",)),
    (tinh_trang.INSPECTOR.key, (f"SoLanKetHon_{side}", f"LoaiTinhTrangHonNhan_{side}", f"TTHN_LyHon{side}")),
))


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension;
    ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}

    def ui(raw: dict) -> list[dict]:
        fields = mapper.enrich([{"name": name, "value": value} for name, value in raw.items()], options)
        normalize_ui_dates(fields)
        return fields

    after = ui(verdict.values)
    then = {f.get("name"): f.get("value") for f in after}
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
    unchanged = {f.get("name"): f.get("value") for f in ui(values)}
    by: dict[str, str] = {}
    for inspector, cluster in _CLUSTERS:
        by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by)]
    return out
