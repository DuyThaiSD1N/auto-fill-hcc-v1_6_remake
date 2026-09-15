"""Map compact facts → UI field cho form "[Bắc Ninh] Điền thông tin tài khoản" (VNeID SSO).

Ô portlet khớp theo NAME SUFFIX `_<key>` (engine FE fillAccountBacNinh). Select (bn-select) FE khớp theo
text option; địa chỉ tỉnh/xã remap sau sáp nhập để khớp danh mục.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process import schema as S

_NOI_CAP_CHIP = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def _fold(value) -> str:
    t = str(value or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _text(value) -> str | None:
    if value in (None, "", {}, []):
        return None
    return " ".join(str(value).split()).strip(" ,;") or None


def _strip_admin_prefix(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "", text, flags=re.IGNORECASE,
    ).strip()


def _parse_area_text(value) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = parts[-1]
        out["xa"] = parts[-3]
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = parts[-1]
        out["xa"] = parts[-2]
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = parts[-1]
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value) -> dict | None:
    """CCCD address (chuỗi/object) → {tinh,xa,diaChi} đã chuẩn hóa tỉnh/xã sau sáp nhập."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        return None
    if not out:
        return None
    # ⚠ strip prefix tỉnh TRƯỚC remap ("bac ninh" ≠ "tinh bac ninh").
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


def _gioi_tinh(value) -> str | None:
    h = _fold(value)
    if not h:
        return None
    if h.startswith("nu") or "female" in h:
        return "Giới tính Nữ"
    if h.startswith("nam") or "male" in h:
        return "Giới tính Nam"
    return None


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    v = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, comp: str | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = comp or S.UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    so_cccd = _digits(v.get("SoCCCD"))
    noi_cap = _text(v.get("NoiCapCCCD"))
    # CCCD gắn chip 12 số: nơi cấp là hằng số → điền mặc định nếu OCR không đọc được.
    if not noi_cap and len(so_cccd) == 12:
        noi_cap = _NOI_CAP_CHIP

    # --- Khối định danh chính ---
    add(S.K_HOTEN, _text(v.get("HoTen")))
    add(S.K_GIOITINH, _gioi_tinh(v.get("GioiTinh")))
    add(S.K_LOAIDINHDANH, "Căn cước công dân")   # mặc định (đa số là CCCD)
    add(S.K_SODINHDANH, so_cccd or None)
    add(S.K_NGAYCAP, _text(v.get("NgayCapCCCD")))
    add(S.K_QUOCGIA, "Việt Nam")                 # mặc định công dân VN
    add(S.K_NGAYSINH, _text(v.get("NgaySinh")))
    add(S.K_SDT, _digits(v.get("SoDienThoai")) or None)
    add(S.K_EMAIL, _text(v.get("Email")))

    # --- Địa chỉ thường trú (tỉnh/xã select + chi tiết) ---
    tt = _area(v.get("ThuongTru"))
    if tt:
        add(S.K_TT_TINH, _strip_admin_prefix(tt.get("tinh")) or None)
        add(S.K_TT_XA, _text(tt.get("xa")))
        add(S.K_TT_CHITIET, _text(tt.get("diaChi")))
    add(S.K_QUEQUAN, _text(v.get("QueQuan")))

    # --- Địa chỉ hiện tại: CHỈ khi có nguồn riêng (không copy thường trú) ---
    ht = _area(v.get("DiaChiHienTai"))
    if ht:
        add(S.K_HT_TINH, _strip_admin_prefix(ht.get("tinh")) or None)
        add(S.K_HT_XA, _text(ht.get("xa")))
        add(S.K_HT_CHITIET, _text(ht.get("diaChi")))

    # --- Khối giấy tờ CCCD (lặp số/ngày/nơi cấp) ---
    add(S.K_SOCCCD, so_cccd or None)
    add(S.K_NGAYCAPCCCD, _text(v.get("NgayCapCCCD")))
    add(S.K_NOICAPCCCD, noi_cap)

    return out
