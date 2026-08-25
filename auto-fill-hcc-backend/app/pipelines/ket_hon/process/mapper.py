"""Map compact marriage facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.foreign_id import (
    normalize_nationality,
    normalize_id_type,
    normalize_foreign_tinh,
    is_foreign,
)
from app.pipelines.ket_hon.process.schema import UI_COMP_BY_NAME


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


_HCM_PROVINCE_KEYS = {
    "hochiminh",
    "tphochiminh",
    "thanhphohochiminh",
    "tphcm",
    "thanhphohcm",
    "hcm",
}


def _normalize_domestic_province(value) -> str:
    """Chuẩn hóa alias cấp tỉnh cục bộ cho đăng ký kết hôn."""
    raw = re.sub(r"\s+", " ", str(value or "")).strip()
    key = re.sub(r"[^a-z0-9]+", "", _fold(raw))
    if key in _HCM_PROVINCE_KEYS:
        return "Thành phố Hồ Chí Minh"
    return raw


# Chuẩn hóa dân tộc về ĐÚNG nhãn option trong dropdown x-select của form.
# Phân biệt 2 option khác nhau: "Mông" (ghi "Mông") và "Mông (Hmông)" (ghi "H'Mông"/"H Mông"/"Hmông").
# Key = fold(bỏ dấu) đã loại bỏ ' và khoảng trắng.
_DAN_TOC_CANON = {
    "mong": "Mông",            # ghi "Mông" → option "Mông"
    "hmong": "Mông (Hmông)",   # ghi "H'Mông"/"H Mông"/"Hmông" → option "Mông (Hmông)"
}

_TINH_TRANG_HON_NHAN = {
    "1": "Hiện tại đang có vợ/chồng",
    "2": "Hiện tại chưa đăng ký kết hôn với ai",
    "3": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai",
    "4": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai",
    "5": "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng",
    "6": "Khác",
}


# Radio "Loại đăng ký" của cổng khớp theo hậu tố id (loaiDangKy-1) hoặc theo nhãn hiển thị.
_LOAI_DANG_KY_LAN_DAU = "1"


def _loai_dang_ky(value) -> str:
    """Loại đăng ký ĐỌC TỪ TỜ KHAI → giá trị radio; rỗng nếu tờ khai không ghi."""
    text = str(value or "").strip()
    if not text:
        return ""
    # "Đăng ký lần đầu" dùng mã id để chắc chắn khớp; nhãn khác giữ nguyên cho
    # extension khớp theo text (vd "Đăng ký lại").
    return _LOAI_DANG_KY_LAN_DAU if "lan dau" in _fold(text) else text


def _normalize_dan_toc(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    key = _fold(raw).replace("'", "").replace("’", "").replace(" ", "")
    return _DAN_TOC_CANON.get(key, raw)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _copy_value(value) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _positive_copy_quantity(value) -> str:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _normalize_admin_unit(value):
    """Giữ loại đơn vị và mở rộng P/X/TT để khớp nhãn phường xã trên form."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    patterns = (
        (r"^P(?:\.\s*|\s+)", "Phường "),
        (r"^X(?:\.\s*|\s+)", "Xã "),
        (r"^TT(?:\.\s*|\s+)", "Thị trấn "),
        (r"^phường\s+", "Phường "),
        (r"^xã\s+", "Xã "),
        (r"^thị\s+trấn\s+", "Thị trấn "),
    )
    for pattern, replacement in patterns:
        if re.match(pattern, text, flags=re.IGNORECASE):
            return re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE).strip()
    return text


def _area(value, nationality: str = "Việt Nam"):
    if not isinstance(value, dict):
        return None
    # quocGia: dùng từ LLM nếu có, không thì suy từ nationality
    quoc_gia = value.get("quocGia") or value.get("quoc_gia") or ""
    if not quoc_gia or _fold(quoc_gia) == "viet nam":
        # Nếu LLM trả "Việt Nam" nhưng người này là nước ngoài → dùng nationality
        quoc_gia = nationality if is_foreign(nationality) else "Việt Nam"

    tinh_raw = value.get("tinh") or value.get("tỉnh") or ""

    # Normalize tên tỉnh nước ngoài nếu có trong bảng
    if is_foreign(quoc_gia) and tinh_raw:
        tinh_raw = normalize_foreign_tinh(quoc_gia, tinh_raw)
    elif tinh_raw:
        # Prompt phải trả tên cấp tỉnh đầy đủ; mapper vẫn chặn các alias HCM phổ biến.
        tinh_raw = _normalize_domestic_province(tinh_raw)

    out = {
        "quocGia": quoc_gia,
        "tinh":    tinh_raw,
        "xa":      _normalize_admin_unit(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi":  value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    # Chỉ remap địa chỉ Việt Nam (bảng remap_lam_dong không có địa danh nước ngoài)
    if not is_foreign(quoc_gia):
        return remap_area(out)
    return out


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        # default=True: giá trị suy diễn/mặc định (không đọc từ giấy tờ) — FE tô viền VÀNG
        # để người dân tự rà và sửa nếu không đúng hoàn cảnh của mình.
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_person(src: str, dst: str, declaration_area_name: str) -> None:
        has_person = bool(values.get(f"{src}_SoDinhDanh") or values.get(f"{src}_HoTen"))
        if not has_person:
            return
        issuer = values.get(f"{src}_NoiCap") or default_issuer(values.get(f"{src}_NgayCap"))

        # Suy nationality: ưu tiên field QuocTich, fallback từ quocGia trong địa chỉ
        # v2: thêm fallback quocGia để xử lý khi LLM bỏ sót QuocTich
        raw_quoc_tich = values.get(f"{src}_QuocTich")
        if not raw_quoc_tich:
            # LLM hay bỏ sót QuocTich nhưng đặt đúng quocGia trong địa chỉ
            addr_raw = values.get(f"{src}_NoiCuTru_TrongNuoc")
            if isinstance(addr_raw, dict):
                raw_quoc_tich = addr_raw.get("quocGia") or addr_raw.get("quoc_gia")
        nationality = normalize_nationality(raw_quoc_tich)
        # Ưu tiên nơi cư trú từ TỜ KHAI (chính xác hơn), fallback CCCD.
        to_khai_area_raw = values.get(declaration_area_name)
        cccd_area_raw = values.get(f"{src}_NoiCuTru_TrongNuoc")
        area_raw = to_khai_area_raw if isinstance(to_khai_area_raw, dict) and (
            to_khai_area_raw.get("tinh") or to_khai_area_raw.get("xa") or to_khai_area_raw.get("diaChi")
        ) else cccd_area_raw
        area = _area(area_raw, nationality)

        add(f"HoTen{dst}", values.get(f"{src}_HoTen"))
        add(f"SoDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))
        add(f"SoGiayToDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))

        # Loại giấy tờ: người nước ngoài dùng foreign_id_map, người VN dùng issuer
        if is_foreign(nationality):
            # Ưu tiên loại giấy tờ từ LLM → normalize, fallback "Hộ chiếu (CMND nước ngoài)"
            raw_id_type = values.get(f"{src}_LoaiGiayTo")
            id_type = normalize_id_type(raw_id_type) or "Hộ chiếu (CMND nước ngoài)"
        else:
            id_type = id_doc_type("Thẻ căn cước công dân", issuer)
        add(f"LoaiGiayToDinhDanh_{dst}", id_type)

        add(f"NgaySinh{dst}", values.get(f"{src}_NgaySinh"))
        add(f"NgayCapDD_{dst}", values.get(f"{src}_NgayCap"))
        add(f"NoiCapDD_{dst}", issuer)
        add(f"DanToc{dst}", _normalize_dan_toc(values.get(f"{src}_DanToc")))
        add(f"QuocTich{dst}", nationality)
        add(f"LoaiCuTru_{dst}", "Thường trú")
        if area:
            if is_foreign(nationality):
                # Người nước ngoài: radio "2" (Khác) + field NuocNgoai
                add(f"NoiCuTru_{dst}", "2")
                full_addr = ", ".join(p for p in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if p)
                add(f"NoiCuTru_{dst}_NuocNgoai", {"quocGia": area["quocGia"], "diaChi": full_addr})
            else:
                # Người Việt Nam: radio "1" (Trong nước) + field TrongNuoc
                add(f"NoiCuTru_{dst}", "1")
                add(f"NoiCuTru_{dst}_TrongNuoc", area)
        # Mỗi bên xử lý độc lập: nếu cả số lần và tình trạng đều không có
        # thì giữ mặc định nghiệp vụ của form (lần 1, chưa đăng ký).
        # Nếu một trong hai có bằng chứng thì chỉ điền field có bằng chứng,
        # không suy diễn field còn thiếu.
        so_lan = str(values.get(f"{src}_SoLanKetHon") or "").strip()
        status_code = str(values.get(f"{src}_TinhTrangHonNhan") or "").strip()
        if not so_lan and not status_code:
            add(f"SoLanKetHon_{dst}", "1", default=True)
            add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN["2"], default=True)
        else:
            if so_lan:
                add(f"SoLanKetHon_{dst}", so_lan)
            add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN.get(status_code))
            # Kết hôn lần 1 = chưa từng đăng ký kết hôn lần nào → tình trạng hôn nhân
            # chỉ có thể là "Hiện tại chưa đăng ký kết hôn với ai" (suy ra được chắc
            # chắn từ số lần, nên không tô vàng).
            if so_lan == "1":
                add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN["2"])

    add_person("CccdNu", "BenNu", "ToKhaiNu_NoiCuTru_TrongNuoc")
    add_person("CccdNam", "BenNam", "ToKhaiNam_NoiCuTru_TrongNuoc")

    # Loại đăng ký: ƯU TIÊN tờ khai ghi rõ (không tô vàng vì đọc được từ giấy tờ); tờ khai
    # không ghi mới fallback "Đăng ký lần đầu" — form này là tờ khai đăng ký kết hôn MỚI,
    # đăng ký lại có thủ tục riêng. Tích SAU khi đã điền thông tin hai bên (add ở cuối danh
    # sách nên extension điền cuối cùng).
    loai_dang_ky = _loai_dang_ky(values.get("ToKhai_LoaiDangKy"))
    if loai_dang_ky:
        add("loaiDangKy", loai_dang_ky)
    elif out:
        add("loaiDangKy", _LOAI_DANG_KY_LAN_DAU, default=True)

    # Số lượng dương vừa là bằng chứng chọn "Có", vừa được điền vào input raw SoLuong.
    # Không có số lượng thật thì không tự mặc định.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "Có")
        add("SoLuong", copy_quantity)
    else:
        add("CapBanSao", _copy_value(values.get("CopyRequest_WantsCopy")))

    return out
