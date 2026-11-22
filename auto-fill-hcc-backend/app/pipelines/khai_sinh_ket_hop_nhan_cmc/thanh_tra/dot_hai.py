"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI (eForm cũ moj, theo biến thể form đang mở) cần ghi lại so với lượt
điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, dinh_danh, review

_ID = dinh_danh.INSPECTOR.key
_AREA = dia_chi.INSPECTOR.key
# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm) theo biến thể form. Ô quyết định khác lượt
# đầu thì không vá cụm đó: form hiện / ẩn cụm theo ô này.
_CLUSTERS = {
    mapper.BIRTH_VARIANT: (
        (None, _ID, ("HoTenKS",)),
        (None, _ID, ("HoTenMeKS", "NamSinhMeKS", "SoDinhDanhMe", "SoGiayToDinhDanhMe")),
        (None, _ID, ("HoTenChaKS", "NamSinhChaKS", "SoDinhDanhCha", "SoGiayToDinhDanhCha")),
        (None, _ID, ("HoVaTenC", "SoDinhDanhC", "SoGiayToDinhDanhC")),
        ("nksNoiSinh", _AREA, ("nksNoiSinh_TrongNuoc",)),
        ("nksQueQuan", _AREA, ("nksQueQuan_TrongNuoc",)),
        ("MeNoiCuTru", _AREA, ("MeNoiCuTru_TrongNuoc",)),
        ("ChaNoiCuTru", _AREA, ("ChaNoiCuTru_TrongNuoc",)),
        ("nycNoiCuTru", _AREA, ("nycNoiCuTru_TrongNuoc",)),
    ),
    mapper.RECOGNITION_VARIANT: (
        (None, _ID, ("HoVaTenC", "SoDinhDanhC", "SoGiayToDinhDanhC")),
        (None, _ID, ("HotenA", "ngaysinhA", "sodinhdanhA", "sogiaytodinhdanhA")),
        (None, _ID, ("hotenB", "ngaysinhB")),
        (None, _AREA, ("DiaChiC", "TT_TinhThanhC", "TT_PhuongXaC")),
        ("noicutruA", _AREA, ("noicutruA_TrongNuoc",)),
        ("noicutruB", _AREA, ("noicutruB_TrongNuoc",)),
    ),
}
# Ô xã người yêu cầu (form nhận cha, mẹ, con) bị form xoá khi ô tỉnh đổi → ghi lại kèm.
_FOLLOWS = {"TT_PhuongXaC": "TT_TinhThanhC"}


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict,
                variant: str) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension; ``options``:
    options đã dùng cho mapper.enrich ở lượt đầu; ``variant``: biến thể form lượt đầu đã điền."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}

    def ui(raw: dict) -> list[dict]:
        fields = mapper.enrich([{"name": name, "value": value} for name, value in raw.items()], variant, options)
        normalize_ui_dates(fields)
        return fields

    after = ui(verdict.values)
    then = {f.get("name"): f.get("value") for f in after}
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ.
    unchanged = {f.get("name"): f.get("value") for f in ui(values)}
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS.get(variant, ()):
        if gate is None or first.get(gate) == then.get(gate):
            by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    # Ô xã đi cùng ô tỉnh của cụm khi ô tỉnh đổi (ban_va.diff đọc follows trên các ô có trong "by").
    for ward, province in _FOLLOWS.items():
        if province in by:
            by.setdefault(ward, by[province])
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by, follows=_FOLLOWS)]
    return out
