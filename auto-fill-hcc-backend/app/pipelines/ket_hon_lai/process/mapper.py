"""Map compact facts của "Đăng ký lại kết hôn" sang field UI x-*."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import upper_person_name
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


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _names_align(a, b) -> bool:
    """Cùng một tên, cho phép lệch MỘT ký tự ở MỘT tiếng (mức sai của OCR chữ viết tay)."""
    words_a, words_b = _fold(a).split(), _fold(b).split()
    if not words_a or not words_b:
        return False
    if words_a == words_b:
        return True
    if len(words_a) != len(words_b) or len(words_a) < 2:
        return False
    diff = [(x, y) for x, y in zip(words_a, words_b) if x != y]
    if len(diff) != 1:
        return False
    x, y = diff[0]
    if len(x) == len(y):
        return sum(p != q for p, q in zip(x, y)) == 1
    short, long = sorted((x, y), key=len)
    return len(long) - len(short) == 1 and any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def _ids_close(a: str, b: str) -> bool:
    """Hai số định danh khớp, hoặc chỉ lệch mức OCR (một chữ số / rơi 1–2 chữ số)."""
    if a == b:
        return True
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long = sorted((a, b), key=len)
    if not 0 < len(long) - len(short) <= 2:
        return False
    it = iter(long)
    return all(ch in it for ch in short)


def _card_is_other_person(card_name, card_id, declared_name, declared_id) -> bool:
    """TH1: nhân thân CCCD lệch CẢ họ tên lẫn số định danh so với tờ khai → giấy tờ của người khác.

    Trùng số (TH2) hoặc chỉ lệch một trong hai (thường do OCR chữ viết tay) thì vẫn là cùng người.
    """
    if not declared_name or not card_name or _names_align(card_name, declared_name):
        return False
    card_digits, declared_digits = _digits(card_id), _digits(declared_id)
    return not (card_digits and declared_digits and _ids_close(card_digits, declared_digits))


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

    def add_person(src: str, dst: str, declaration: str) -> None:
        if not (
            values.get(f"{src}_SoDinhDanh") or values.get(f"{src}_HoTen")
            or values.get(f"{declaration}_SoDinhDanh") or values.get(f"{declaration}_HoTen")
        ):
            return
        # TH1 — nhân thân trích được (CCCD) lệch CẢ tên lẫn số so với khối vợ/chồng trên tờ khai: đó là
        # giấy tờ của NGƯỜI KHÁC. Họ tên/số/ngày sinh điền theo tờ khai (viền vàng), bỏ ngày/nơi cấp của
        # thẻ đó. TH2 (trùng số) và ca còn lại: thẻ (bản IN) trước, tờ khai chỉ bù ô thẻ thiếu.
        card_is_other = _card_is_other_person(
            values.get(f"{src}_HoTen"), values.get(f"{src}_SoDinhDanh"),
            values.get(f"{declaration}_HoTen"), values.get(f"{declaration}_SoDinhDanh"))

        def identity(name: str) -> tuple:
            declared = values.get(f"{declaration}_{name}")
            if card_is_other:
                return declared, bool(declared)
            return values.get(f"{src}_{name}") or declared, False

        ho_ten, ho_ten_default = identity("HoTen")
        so_dinh_danh, so_default = identity("SoDinhDanh")
        ngay_sinh, ngay_sinh_default = identity("NgaySinh")
        ngay_cap = None if card_is_other else values.get(f"{src}_NgayCap")
        noi_cap = None if card_is_other else values.get(f"{src}_NoiCap")
        issuer = normalize_issuer(noi_cap) or default_issuer(ngay_cap)
        area = _area(values.get(f"{src}_NoiCuTru_TrongNuoc"))

        add(f"HoTen{dst}", upper_person_name(ho_ten), ho_ten_default)
        add(f"SoDinhDanh_{dst}", so_dinh_danh, so_default)
        add(f"SoGiayToDinhDanh_{dst}", so_dinh_danh, so_default)
        add(f"LoaiGiayToDinhDanh_{dst}", id_doc_type("Căn cước công dân", issuer))
        add(f"NgaySinh{dst}", ngay_sinh, ngay_sinh_default)
        add(f"NgayCapDD_{dst}", ngay_cap)
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

    add_person("CccdNu", "BenNu", "ToKhaiNu")
    add_person("CccdNam", "BenNam", "ToKhaiNam")

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
