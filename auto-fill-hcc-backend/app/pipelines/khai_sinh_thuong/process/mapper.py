"""Map compact OCR-derived facts to regular birth registration legacy fields."""

import re

from app.pipelines._shared.legacy_fields.dang_ky_lai import ALLOWED as LEGACY_COMP_BY_NAME
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area

# Đổi tên tỉnh/thành theo sắp xếp đơn vị hành chính 2025 (giấy tờ cũ ghi tên cũ → chuẩn hóa tên mới).
_TINH_RENAME = {"thua thien hue": "Huế"}


def _fold_tinh(value: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


def _norm_tinh(value):
    if not value:
        return value
    return _TINH_RENAME.get(_fold_tinh(value), value)


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()

_COMP_BY_NAME = {
    **LEGACY_COMP_BY_NAME,
    "LoaiDangKy": "x-radio",
    "nksLoaiKhaiSinh": "x-select-default",
    "QuanHe": "x-radio",
}

_STRUCTURAL_DEFAULTS = [
    {"name": "LoaiDangKy", "comp": "x-radio", "value": "1"},
    {"name": "nksLoaiKhaiSinh", "comp": "x-select-default", "value": "Đã xác định được cả cha lẫn mẹ"},
]

_TAIL_DEFAULTS = [
    {"name": "QuanHe", "comp": "x-radio", "value": "ChaDe"},
]


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _area(value):
    if not isinstance(value, dict):
        return None
    xa = _strip_admin_prefix(value.get("xa") or value.get("xã"))
    dia = value.get("diaChi") or value.get("dia_chi") or value.get("diachi")
    # diaChi chỉ là phần CHI TIẾT; nếu chính là tên xã/phường (vd "Phường Tân Phong" trong khi
    # xa="Tân Phong") → trùng lặp vô nghĩa, bỏ đi.
    if dia and _strip_admin_prefix(dia).strip().lower() == (xa or "").strip().lower():
        dia = None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": _norm_tinh(value.get("tinh") or value.get("tỉnh")),
        "xa": xa,
        "diaChi": dia,
    }
    return remap_area({k: v for k, v in out.items() if v not in (None, "", {}, [])})


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic legacy UI fields while preserving response shape."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = _COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    for default in _STRUCTURAL_DEFAULTS:
        add(default["name"], default["value"])

    father_residence = _area(values.get("CccdNam_NoiCuTru_TrongNuoc"))
    mother_residence = _area(values.get("CccdNu_NoiCuTru_TrongNuoc"))
    father_origin = _area(values.get("CccdNam_QueQuan")) or father_residence
    child_birth_place = _area(values.get("Gcs_NoiSinh"))

    has_father = bool(values.get("CccdNam_SoDinhDanh") or values.get("CccdNam_HoTen"))
    has_mother = bool(values.get("CccdNu_SoDinhDanh") or values.get("CccdNu_HoTen"))
    has_child = bool(values.get("Gcs_HoTenCon") or values.get("Gcs_NgaySinhCon") or child_birth_place)

    father_issuer = values.get("CccdNam_NoiCap") or default_issuer(values.get("CccdNam_NgayCap"))
    mother_issuer = values.get("CccdNu_NoiCap") or default_issuer(values.get("CccdNu_NgayCap"))

    # Người yêu cầu mặc định là cha.
    if has_father:
        add("HoVaTenC", values.get("CccdNam_HoTen"))
        add("SoDinhDanhC", values.get("CccdNam_SoDinhDanh"))
        add("SoGiayToDinhDanhC", values.get("CccdNam_SoDinhDanh"))
        add("LoaiGiayToDinhDanhC", "Căn cước công dân")
        add("NgayCapDDC", values.get("CccdNam_NgayCap"))
        add("NoiCapDDC", father_issuer)
        add("nycLoaiCuTru", "Thường trú")
        if father_residence:
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", father_residence)

    if has_child:
        add("HoTenKS", values.get("Gcs_HoTenCon"))
        add("NgaySinhChon", values.get("Gcs_NgaySinhCon"))
        add("GioiTinhKS", values.get("Gcs_GioiTinhCon"))
        add("DanTocKS", values.get("Gcs_DanTocCon"))
        add("QuocTichKS", "Việt Nam")
        if child_birth_place:
            add("nksNoiSinh", "1")
            add("nksNoiSinh_TrongNuoc", child_birth_place)
        if father_origin:
            add("nksQueQuan", "1")
            add("nksQueQuan_TrongNuoc", father_origin)

    if has_mother:
        add("HoTenMeKS", values.get("CccdNu_HoTen"))
        add("NamSinhMeKS", values.get("CccdNu_NgaySinh"))
        add("SoDinhDanhMe", values.get("CccdNu_SoDinhDanh"))
        add("SoGiayToDinhDanhMe", values.get("CccdNu_SoDinhDanh"))
        add("LoaiGiayToDinhDanhMe", "Căn cước công dân")
        add("NgayCapDDMe", values.get("CccdNu_NgayCap"))
        add("NoiCapDDMe", mother_issuer)
        add("DanTocMeKS", values.get("CccdNu_DanToc"))
        add("QuocTichMeKS", values.get("CccdNu_QuocTich") or "Việt Nam")
        add("MeLoaiCuTru", "Thường trú")
        if mother_residence:
            add("MeNoiCuTru", "1")
            add("MeNoiCuTru_TrongNuoc", mother_residence)

    if has_father:
        add("HoTenChaKS", values.get("CccdNam_HoTen"))
        add("NamSinhChaKS", values.get("CccdNam_NgaySinh"))
        add("SoDinhDanhCha", values.get("CccdNam_SoDinhDanh"))
        add("SoGiayToDinhDanhCha", values.get("CccdNam_SoDinhDanh"))
        add("LoaiGiayToDinhDanhCha", "Căn cước công dân")
        add("NgayCapDDCha", values.get("CccdNam_NgayCap"))
        add("NoiCapDDCha", father_issuer)
        add("DanTocChaKS", values.get("CccdNam_DanToc"))
        add("QuocTichChaKS", values.get("CccdNam_QuocTich") or "Việt Nam")
        add("ChaLoaiCuTru", "Thường trú")
        if father_residence:
            add("ChaNoiCuTru", "1")
            add("ChaNoiCuTru_TrongNuoc", father_residence)

    for default in _TAIL_DEFAULTS:
        add(default["name"], default["value"])

    return out

