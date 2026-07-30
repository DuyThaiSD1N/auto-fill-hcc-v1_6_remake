"""Map compact marriage facts (có yếu tố nước ngoài) to legacy x-* UI fields.

Khác ket_hon nội địa: KHÔNG mặc định quốc tịch = Việt Nam, KHÔNG mặc định nơi cư trú = trong nước.
Bên nước ngoài → radio cư trú "2" (Khác) + ô NuocNgoai (quốc gia + địa chỉ), loại giấy tờ = "Giấy tờ khác...".
"""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    default_issuer,
    id_doc_type,
    normalize_issuer,
)
from app.pipelines.ket_hon_nuoc_ngoai.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.area_remap import remap_area

# Loại giấy tờ cho giấy tờ NƯỚC NGOÀI — PHẢI khớp ĐÚNG text option dropdown (ô có tìm kiếm, gõ
# chuỗi lệch sẽ lọc ra 0 kết quả → không chọn được). Text option trên form: "Giấy tờ khác bao gồm
# các giấy tờ có dán".
FOREIGN_DOC_TYPE = "Giấy tờ khác bao gồm các giấy tờ có dán"

# Category tình trạng hôn nhân (LLM trả) → ĐÚNG text option dropdown.
# CỐ Ý KHÔNG có "dang_co_vo_chong": người đi đăng ký kết hôn luôn độc thân → nếu LLM lỡ trả
# "đang có vợ/chồng" (bịa từ ngữ cảnh) thì .get() ra None → DROP tất định.
_MARITAL_STATUS = {
    "chua_ket_hon": "Hiện tại chưa đăng ký kết hôn với ai",
    "ly_hon": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai",
    "goa": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai",
}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_vn(value) -> bool:
    return _fold(value) in ("viet nam", "vietnam", "vn")


_DAN_TOC_CANON = {"mong": "Mông", "hmong": "Mông (Hmông)"}


def _normalize_dan_toc(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    key = _fold(raw).replace("'", "").replace("’", "").replace(" ", "")
    return _DAN_TOC_CANON.get(key, raw)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _strip_admin_prefix(value):
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _area(value):
    """Object cư trú thô {quocGia,tinh,xa,diaChi}; KHÔNG mặc định quocGia = Việt Nam."""
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"] and not out["quocGia"]:
        return None
    return remap_area(out)


def enrich(fields: list[dict]) -> list[dict]:
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_person(src: str, dst: str) -> None:
        if not (values.get(f"{src}_SoDinhDanh") or values.get(f"{src}_HoTen")):
            return

        quoc_tich = values.get(f"{src}_QuocTich")
        area = _area(values.get(f"{src}_NoiCuTru"))
        res_country = area.get("quocGia") if area else ""
        issuer_raw = values.get(f"{src}_NoiCap")
        vn_issuer = normalize_issuer(issuer_raw) in (ISSUER_BO_CONG_AN, ISSUER_CUC)

        # Xác định người NƯỚC NGOÀI: quốc tịch hoặc quốc gia cư trú khác Việt Nam.
        # Giấy tờ do cơ quan VN cấp (Bộ Công an/Cục Cảnh sát) → coi là người Việt (ghi đè).
        foreign = False
        if quoc_tich and not _is_vn(quoc_tich):
            foreign = True
        if res_country and not _is_vn(res_country):
            foreign = True
        if vn_issuer:
            foreign = False

        add(f"HoTen{dst}", values.get(f"{src}_HoTen"))
        add(f"SoDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))
        add(f"SoGiayToDinhDanh_{dst}", values.get(f"{src}_SoDinhDanh"))
        add(f"NgaySinh{dst}", values.get(f"{src}_NgaySinh"))
        add(f"NgayCapDD_{dst}", values.get(f"{src}_NgayCap"))
        add(f"DanToc{dst}", _normalize_dan_toc(values.get(f"{src}_DanToc")))

        if foreign:
            # Giấy tờ nước ngoài: loại = "Giấy tờ khác..." + ô "Nhập tên giấy tờ" = tên giấy tờ thật.
            add(f"LoaiGiayToDinhDanh_{dst}", FOREIGN_DOC_TYPE)
            add(f"NhapTenGiayTo_{dst}", values.get(f"{src}_TenGiayTo") or "Chứng minh thư")
            add(f"NoiCapDD_{dst}", issuer_raw)  # nơi cấp GIỮ NGUYÊN (không chuẩn hóa VN)
            add(f"QuocTich{dst}", quoc_tich)  # KHÔNG mặc định
            add(f"LoaiCuTru_{dst}", "Thường trú")  # foreign vẫn mặc định Thường trú
            # Cư trú: radio "2" (Khác) + ô NuocNgoai {quốc gia, địa chỉ đầy đủ}.
            add(f"NoiCuTru_{dst}", "2")
            if area:
                full_addr = ", ".join(p for p in (area["diaChi"], area["xa"], area["tinh"]) if p)
                add(f"NoiCuTru_{dst}_NuocNgoai", {"quocGia": area["quocGia"], "diaChi": full_addr})
        else:
            issuer = normalize_issuer(issuer_raw) or default_issuer(values.get(f"{src}_NgayCap"))
            add(f"LoaiGiayToDinhDanh_{dst}", id_doc_type("Căn cước", issuer))
            add(f"NoiCapDD_{dst}", issuer)
            add(f"QuocTich{dst}", quoc_tich or "Việt Nam")  # giấy tờ VN → Việt Nam
            add(f"LoaiCuTru_{dst}", "Thường trú")
            if area:
                vn_area = {**area, "quocGia": area["quocGia"] or "Việt Nam"}
                add(f"NoiCuTru_{dst}", "1")
                add(f"NoiCuTru_{dst}_TrongNuoc", vn_area)

        # Tình trạng hôn nhân + số lần kết hôn (suy 2 chiều).
        status_cat = _fold(values.get(f"{src}_TinhTrangHonNhan")).replace(" ", "_")
        status_label = _MARITAL_STATUS.get(status_cat)
        so_lan = str(values.get(f"{src}_SoLanKetHon") or "").strip()
        # Chưa kết hôn (theo giấy xác nhận) → suy số lần kết hôn = 1 nếu tờ khai không ghi.
        if not so_lan and status_cat == "chua_ket_hon":
            so_lan = "1"
        # Ngược lại: tờ khai ghi lần 1 mà chưa có tình trạng → suy "chưa đăng ký kết hôn với ai".
        if not status_label and so_lan == "1":
            status_label = _MARITAL_STATUS["chua_ket_hon"]
        add(f"SoLanKetHon_{dst}", so_lan or None)
        add(f"LoaiTinhTrangHonNhan_{dst}", status_label)

    add_person("CccdNu", "BenNu")
    add_person("CccdNam", "BenNam")
    return out
