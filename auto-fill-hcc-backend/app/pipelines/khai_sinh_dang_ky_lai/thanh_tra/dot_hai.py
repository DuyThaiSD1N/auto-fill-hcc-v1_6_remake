"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

import re

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va

from ..process import mapper
from . import dia_chi, dinh_danh, giay_to, review

# (ô quyết định cụm có hiện trên form không, thanh tra soát cụm, các ô của cụm). Ô quyết định khác lượt đầu thì không vá
# cụm đó: form hiện / ẩn cụm theo ô này.
_CLUSTERS = (
    (None, dinh_danh.INSPECTOR.key, ("HoTenKS", "DanTocKS")),
    (None, dinh_danh.INSPECTOR.key, ("HoTenMeKS", "DanTocMeKS", "NamSinhMeKS")),
    (None, dinh_danh.INSPECTOR.key, ("HoTenChaKS", "DanTocChaKS", "NamSinhChaKS")),
    (None, dinh_danh.INSPECTOR.key, ("HoVaTenC", "DanTocC")),
    (None, giay_to.INSPECTOR.key, ("SoDinhDanhMe", "SoGiayToDinhDanhMe", "LoaiGiayToDinhDanhMe", "NgayCapDDMe", "NoiCapDDMe")),
    (None, giay_to.INSPECTOR.key, ("SoDinhDanhCha", "SoGiayToDinhDanhCha", "LoaiGiayToDinhDanhCha", "NgayCapDDCha",
                                   "NoiCapDDCha")),
    (None, giay_to.INSPECTOR.key, ("SoDinhDanhC", "SoGiayToDinhDanhC", "LoaiGiayToDinhDanhC", "NgayCapDDC", "NoiCapDDC")),
    ("MeNoiCuTru", dia_chi.INSPECTOR.key, ("MeNoiCuTru_TrongNuoc",)),
    ("ChaNoiCuTru", dia_chi.INSPECTOR.key, ("ChaNoiCuTru_TrongNuoc",)),
    ("nycNoiCuTru", dia_chi.INSPECTOR.key, ("nycNoiCuTru_TrongNuoc",)),
    ("nksNoiSinh", dia_chi.INSPECTOR.key, ("nksNoiSinh_TrongNuoc",)),
    ("nksQueQuan", dia_chi.INSPECTOR.key, ("nksQueQuan_TrongNuoc",)),
)
_SELF_NAME_RE = re.compile(r"(?m)^(Họ tên thống nhất:\s*)(.+)$")


def _with_self_name(options: dict, before: dict, after: dict) -> dict:
    """Người yêu cầu là chính người được đăng ký lại: mapper điền cả hai ô họ tên theo dòng "Họ tên thống nhất" của
    phân vai, không theo field lượt trích. Thanh tra sửa họ tên đó (có nguyên văn giấy in) thì dòng này đi theo."""
    context = str(options.get("_reasoning_context") or "")
    match = _SELF_NAME_RE.search(context)
    if not match:
        return options
    for name in ("Subject_FullName", "Requester_FullName"):
        new = str(after.get(name) or "").strip()
        if new and new != str(before.get(name) or "").strip() and dinh_danh.close_name(new, match.group(2)):
            return {**options, "_reasoning_context": context[:match.start(2)] + new + context[match.end(2):]}
    return options


async def patch(documents: list[dict], raw_fields: list[dict], base_fields: list[dict], options: dict) -> dict:
    """``raw_fields``: field lượt trích sau bước lọc theo phân vai, trước mapper; ``base_fields``: ô UI lượt đầu đã trả
    cho extension; ``options``: options đã dùng cho mapper.enrich ở lượt đầu (kèm ``_reasoning_context``)."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    # Ca tự đi làm cho chính mình: form hiện họ tên theo dòng "Họ tên thống nhất" chứ không theo field lượt trích → thanh
    # tra phải soát đúng họ tên đang hiện, không thì field lượt trích đã đúng mà ô trên form vẫn lệch dấu.
    match = _SELF_NAME_RE.search(str(options.get("_reasoning_context") or ""))
    if match:
        for name in ("Subject_FullName", "Requester_FullName"):
            if values.get(name) and dinh_danh.close_name(values[name], match.group(2).strip()):
                values[name] = match.group(2).strip()
    verdict = await review(documents, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    defaults = {f["name"] for f in raw_fields if isinstance(f, dict) and f.get("default")}

    def ui(raw: dict, opts: dict) -> dict:
        fields = mapper.enrich([{"name": name, "value": value, **({"default": True} if name in defaults else {})}
                                for name, value in raw.items()], opts)
        normalize_ui_dates(fields)
        return fields

    after = ui(verdict.values, _with_self_name(options, values, verdict.values))
    then = {f.get("name"): f.get("value") for f in after}
    # Chỉ vá ô mà phán quyết thực sự làm đổi: so với chính mapper chạy lại trên lượt trích cũ, không so thẳng với lượt
    # đầu (nơi gọi pipeline có thể đã chỉnh ô lượt đầu theo tài khoản).
    unchanged = {f.get("name"): f.get("value") for f in ui(values, options)}
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    by: dict[str, str] = {}
    for gate, inspector, cluster in _CLUSTERS:
        if gate is None or first.get(gate) == then.get(gate):
            by.update({name: inspector for name in cluster if then.get(name) != unchanged.get(name)})
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(base_fields, after, by)]
    return out
