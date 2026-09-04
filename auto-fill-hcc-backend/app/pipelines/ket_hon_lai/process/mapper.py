"""Map compact facts của "Đăng ký lại kết hôn" sang field UI x-*."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.ket_hon_lai.process.schema import UI_COMP_BY_NAME

_TINH_TRANG_HON_NHAN_DEFAULT = "Hiện tại đang có vợ/chồng"
_LOAI_DANG_KY_LAI = "Đăng ký lại"


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# Chuẩn hóa dân tộc về đúng nhãn option dropdown: "Mông" vs "Mông (Hmông)".
_DAN_TOC_CANON = {
    "mong": "Mông",
    "hmong": "Mông (Hmông)",
}


def _normalize_dan_toc(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    key = _fold(raw).replace("'", "").replace("’", "").replace(" ", "")
    return _DAN_TOC_CANON.get(key, raw)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _previous_registration_area(values: dict) -> dict | None:
    """Nơi đăng ký kết hôn trước đây → đơn vị hành chính HIỆN HÀNH (dropdown của cổng).

    Giữ tiền tố loại đơn vị ("Xã/Phường/Thị trấn") vì option trên cổng có tiền tố.
    Không tra được đơn vị mới thì remap_area trả xã rỗng — chỉ điền tỉnh, để cán bộ tự chọn
    đơn vị còn hơn chọn nhầm một xã đã giải thể.
    """
    tinh = str(values.get("KetHonCu_TinhDangKy") or "").strip()
    xa = str(values.get("KetHonCu_XaDangKy") or "").strip()
    if not tinh and not xa:
        return None
    return remap_area({"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": ""})


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Suy field UI tất định từ compact facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    def add_person(src: str, dst: str) -> None:
        if not (values.get(f"{src}_SoDinhDanh") or values.get(f"{src}_HoTen")):
            return
        issuer = normalize_issuer(values.get(f"{src}_NoiCap")) or default_issuer(values.get(f"{src}_NgayCap"))
        area = _area(values.get(f"{src}_NoiCuTru_TrongNuoc"))

        add(f"HoTen{dst}", values.get(f"{src}_HoTen"))
        add(f"SoDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))
        add(f"SoGiayToDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))
        add(f"LoaiGiayToDinhDanh_{dst}", "Căn cước công dân")
        add(f"NgaySinh{dst}", values.get(f"{src}_NgaySinh"))
        add(f"NgayCapDD_{dst}", values.get(f"{src}_NgayCap"))
        add(f"NoiCapDD_{dst}", issuer)
        add(f"DanToc{dst}", _normalize_dan_toc(values.get(f"{src}_DanToc")))
        add(f"QuocTich{dst}", values.get(f"{src}_QuocTich") or "Việt Nam")
        add(f"LoaiCuTru_{dst}", "Thường trú")
        if area:
            add(f"NoiCuTru_{dst}", "1")
            add(f"NoiCuTru_{dst}_TrongNuoc", area)
        # Mặc định (bôi vàng): kết hôn lần thứ 1, tình trạng hôn nhân "Hiện đang có vợ/chồng".
        add(f"SoLanKetHon_{dst}", "1", default=True)
        add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN_DEFAULT, default=True)

    add_person("CccdNu", "BenNu")
    add_person("CccdNam", "BenNam")

    # Hồ sơ gốc (lần đăng ký kết hôn trước đây).
    add("loaiDangKy", _LOAI_DANG_KY_LAI, default=True)
    add("soDangKyTruocDay", values.get("KetHonCu_So"))
    # Quyển số không có công thức suy ra đáng tin cậy; chỉ điền khi tài liệu ghi rõ.
    add("quyenDangKyTruocDay", values.get("KetHonCu_QuyenSo"))
    add("ngayDangKyTruocDay", values.get("KetHonCu_NgayDangKy"))
    # Cascading: chọn TỈNH (filter) trước để dropdown đơn vị load, rồi mới chọn đơn vị.
    # Cơ quan đăng ký cũ thường ghi theo đơn vị TRƯỚC SÁP NHẬP ("xã Đoan Bái, tỉnh Bắc Giang"),
    # trong khi dropdown của cổng chỉ liệt kê đơn vị HIỆN HÀNH → phải remap trước, nếu không
    # cả hai ô đều không khớp option nào và bị bỏ trống.
    noi_dang_ky_cu = _previous_registration_area(values)
    if noi_dang_ky_cu:
        add("noiDangKyTruocDay_filter", noi_dang_ky_cu.get("tinh"))
        add("noiDangKyTruocDay", noi_dang_ky_cu.get("xa"))

    # Đề nghị cấp bản sao: mặc định Có, số lượng 1 bản (bôi vàng).
    add("CapBanSao", "Có", default=True)
    add("SoLuong", "1", default=True)

    return out
