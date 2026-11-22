"""Điền đợt 2: soát lại lượt trích rồi tính các ô UI cần ghi lại so với lượt điền đầu."""

from app.pipelines._shared.formatting import normalize_ui_dates
from app.pipelines._shared.thanh_tra import ban_va
from app.pipelines._shared.thanh_tra import sdt_nguoi_nop

from ..process import mapper, reason
from . import dia_chi_ghep, dinh_danh, giay_to, noi_dung, review

_RELATION = "citizenQuanhevsngcaichinhhotich1"
_AREA = "citizenNDKNoiCuTru_TrongNuoc"
# (thanh tra soát cụm, các ô của cụm). Radio "Trong Nước" đi cùng ô địa chỉ: các ô địa chỉ chỉ hiện sau khi chọn.
_CLUSTERS = (
    (sdt_nguoi_nop.INSPECTOR.key, ("citizenPhone",)),
    (dinh_danh.INSPECTOR.key, ("citizenNDKHoTen", "citizenNDKSodinhdanh", "citizenNDK_NgaySinh",
                               "citizenNDKLoaiGiaytotuythan", "citizenNDKSogiaytotuythan",
                               "citizenNDKNgaycapgiaytotuythan", "citizenNDKCoquancap", "citizenNDKGioitinh",
                               "citizenNDKDantoc")),
    (dia_chi_ghep.INSPECTOR.key, ("citizenNDKNoiCuTru", _AREA)),
    (giay_to.INSPECTOR.key, ("citizenLoainghiepvu", "citizenTTSodangkyhosogoc", "citizenTTQuyensodangkyhosogoc",
                             "citizenTTngayDangKyHSGoc", "citizenTTNoidangkyhosogoc")),
    (noi_dung.INSPECTOR.key, ("citizenViecDangKy", "citizenTTNoidungdk", "citizenLydothaydoi")),
)


async def patch(documents: list[dict], context: str, raw_fields: list[dict], base_fields: list[dict],
                options: dict) -> dict:
    """``raw_fields``: field lượt trích trước mapper; ``base_fields``: ô UI lượt đầu đã trả cho extension;
    ``options``: options đã dùng cho mapper.enrich ở lượt đầu."""
    values = {f["name"]: f.get("value") for f in raw_fields if isinstance(f, dict) and f.get("name")}
    verdict = await review(documents, context, values, options)
    out = {"fields": [], "rulings": verdict.rulings, "timing": verdict.timing}
    # Cùng chốt với lượt đầu: thanh tra không sửa thì không ghi lại số / ngày của giấy khai sinh cha / mẹ.
    final = reason.drop_other_holder_registration(verdict.values, documents, context)
    after, _ = mapper.enrich([{"name": name, "value": value} for name, value in final.items()], options)
    normalize_ui_dates(after)
    first = {f.get("name"): f.get("value") for f in base_fields or [] if isinstance(f, dict)}
    then = {f.get("name"): f.get("value") for f in after}
    # Quan hệ đổi thì khối người có nội dung thay đổi đổi nguồn (tài khoản / giấy tờ) và form đổi bố cục: không vá gì.
    if first.get(_RELATION) != then.get(_RELATION):
        return out
    by: dict[str, str] = {}
    for inspector, cluster in _CLUSTERS:
        # Ô địa chỉ gộp chỉ ghi lại được khi extension khai biết ghi ô địa chỉ ở đợt 2 (options._secondPassArea).
        if _AREA in cluster and not options.get("_secondPassArea"):
            continue
        by.update(dict.fromkeys(cluster, inspector))
    # "by" = thanh tra soát cụm chứa ô, để trang xem lại nối ô đã sửa với biên bản của thanh tra đó.
    out["fields"] = [{**field, "by": by[field["name"]]} for field in ban_va.diff(
        base_fields, after, by, follows={_AREA: "citizenNDKNoiCuTru"})]
    return out
