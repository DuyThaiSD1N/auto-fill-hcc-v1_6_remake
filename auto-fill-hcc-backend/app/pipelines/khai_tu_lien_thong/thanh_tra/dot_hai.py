"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (form Angular liên thông) cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.area_remap import ward_hints
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, review

# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm). Quốc gia đổi thì form đổi bộ ô địa chỉ.
_CLUSTERS = (
    ("NctccMaQuocgia", dia_chi.INSPECTOR.key, ("NctccDiaChi",)),
    ("NoichetMaQuocgia", dia_chi.INSPECTOR.key, ("NoichetDiachi",)),
)


async def patch(documents: list[dict], context: str, raw_fields: list[dict], base_fields: list[dict],
                options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension; ``context``:
    khối phân vai của lượt đầu; ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    # Chạy ở nền ngoài khối gợi ý của lượt đầu: đặt lại xã quầy để mapper tính như lượt đầu (mapper tự thêm "Kính gửi").
    with ward_hints(options.get("counterWard")):
        values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
        verdict = await review(documents, context, values, options)
        out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
        ocr_text = join_ocr_documents(documents)

        def ui(raw: dict) -> list[dict]:
            fields = mapper.enrich([{"name": name, "value": value} for name, value in raw.items()], options,
                                   reasoning_context=context, ocr_text=ocr_text)
            normalize_ui_dates(fields)
            return fields

        after = ui(verdict.values)
        then = {f.get("name"): f.get("value") for f in after}
        # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
        unchanged = {f.get("name"): f.get("value") for f in ui(values)}
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS:
        if first.get(gate) == then.get(gate):
            by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by)]
    return out
