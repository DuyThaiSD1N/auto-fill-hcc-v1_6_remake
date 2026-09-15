"""Map compact facts → UI field cho e-form Bắc Ninh "Đăng ký biến động QSDĐ" (1.115468).

Nguồn = CHỦ HỒ SƠ (bên nhận = người ủy quyền). route theo purpose:
- registration_form → Đơn Mẫu 18 (element_* khớp CLASS eform-element-<Key>); GỘP 2 người vào ô Tên/Giấy tờ.
- authorized_person → khối "Thông tin trong trường hợp được ủy quyền" = CHỦ HỒ SƠ → doiTuongKhac*.
"""

import re
import unicodedata

from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.process import schema as S

# Loại giao dịch (fold) → (Nội dung biến động, tên hợp đồng mặc định).
_NOIDUNG_BY_LOAI = {
    "chuyen doi": ("Chuyển đổi quyền sử dụng đất nông nghiệp", "Hợp đồng chuyển đổi quyền sử dụng đất"),
    "chuyen nhuong": ("Nhận chuyển nhượng quyền sử dụng đất", "Hợp đồng chuyển nhượng quyền sử dụng đất"),
    "tang cho": ("Nhận tặng cho quyền sử dụng đất", "Hợp đồng tặng cho quyền sử dụng đất"),
    "thua ke": ("Nhận thừa kế quyền sử dụng đất", "Văn bản thừa kế quyền sử dụng đất"),
    "gop von": ("Nhận góp vốn bằng quyền sử dụng đất", "Hợp đồng góp vốn bằng quyền sử dụng đất"),
    "cho thue": ("Cho thuê, cho thuê lại quyền sử dụng đất", "Hợp đồng cho thuê quyền sử dụng đất"),
    "mua ban nha": ("Mua bán nhà ở có thời hạn", "Hợp đồng mua bán nhà ở có thời hạn"),
}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value) -> str | None:
    if value in (None, "", {}, []):
        return None
    return " ".join(str(value).replace("\n", " ").split()).strip(" ,;") or None


def _flatten(value) -> str | None:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _fold(text: str) -> str:
    t = (text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def _digits(value) -> str | None:
    d = re.sub(r"\D+", "", str(value or ""))
    return d or None


def _year(value) -> str | None:
    m = re.search(r"(\d{4})", str(value or ""))
    return m.group(1) if m else None


def _truthy(value) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "co", "có", "1"}


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    purpose = str((options or {}).get("purpose") or "registration_form")
    if purpose == "authorized_person":
        return _authorized_fields(values)
    return _registration_fields(values)


def _authorized_fields(v: dict) -> tuple[list[dict], list[str]]:
    """Khối "Thông tin trong trường hợp được ủy quyền" = NGƯỜI ỦY QUYỀN (= CHỦ HỒ SƠ), KHÔNG phải người
    được ủy quyền (người đó chính là tài khoản đang nộp)."""
    name = _text(v.get("ChuHoSo_HoTen"))
    ident = _digits(v.get("ChuHoSo_SoDinhDanh"))
    out: list[dict] = []

    def add(field: str, value, comp: str = "bn-input") -> None:
        value = _text(value)
        if value:
            out.append({"name": field, "comp": comp, "value": value})

    add("doiTuongKhachoTen", name)
    add("doiTuongKhacgioiTinhId", v.get("ChuHoSo_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", ident)
    add("doiTuongKhacngayCap", v.get("ChuHoSo_NgayCap"))
    add("doiTuongKhacnoiCap", v.get("ChuHoSo_NoiCap"))
    add("doiTuongKhacngaySinh", v.get("ChuHoSo_NgaySinh"))
    add("doiTuongKhacemail", v.get("ChuHoSo_Email"))
    add("doiTuongKhacsoDienThoai", _digits(v.get("ChuHoSo_DienThoai")))
    tt = v.get("ChuHoSo_ThuongTru")
    if isinstance(tt, dict):
        add("doiTuongKhactinhThanhId", tt.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", tt.get("xa") or tt.get("phuong"), "bn-select")
    add("doiTuongKhacdiaChiChiTiet", _flatten(tt))

    if not name or not ident:
        return [], ["Chưa bóc tách đủ họ tên và CCCD của chủ hồ sơ (người ủy quyền)."]
    return out, []


def _nguoi_str(name, year) -> str | None:
    name = _text(name)
    if not name:
        return None
    y = _year(year)
    return f"{name}, sinh năm {y}" if y else name


def _giayto_str(cccd, name) -> str | None:
    cccd = _digits(cccd)
    if not cccd:
        return None
    nm = _text(name)
    return f"{cccd} ({nm})" if nm else cccd


def _registration_fields(v: dict) -> tuple[list[dict], list[str]]:
    out: list[dict] = []
    seen: set[str] = set()

    def add(field: str, value) -> None:
        if field in seen or value in (None, "", {}, []):
            return
        comp = S.UI_COMP_BY_NAME.get(field)
        if not comp:
            return
        out.append({"name": field, "comp": comp, "value": value})
        seen.add(field)

    dia_chi = _flatten(v.get("ChuHoSo_ThuongTru"))
    phone = _digits(v.get("ChuHoSo_DienThoai"))
    email = _text(v.get("ChuHoSo_Email"))
    mst = _digits(v.get("ChuHoSo_MaSoThue"))

    # GỘP 2 người đồng nhận (nếu có) vào ô Tên(2) và Giấy tờ nhân thân.
    ten_parts = [_nguoi_str(v.get("ChuHoSo_HoTen"), v.get("ChuHoSo_NgaySinh")),
                 _nguoi_str(v.get("DongSuDung_HoTen"), v.get("DongSuDung_NgaySinh"))]
    ten = " và ".join(p for p in ten_parts if p) or None
    gt_parts = [_giayto_str(v.get("ChuHoSo_SoDinhDanh"), v.get("ChuHoSo_HoTen")),
                _giayto_str(v.get("DongSuDung_SoDinhDanh"), v.get("DongSuDung_HoTen"))]
    giay_to = "; ".join(p for p in gt_parts if p) or None

    # Nội dung biến động theo loại giao dịch (đây là ô bắt buộc "II. Nội dung biến động" → luôn suy ra được).
    loai = _fold(v.get("Don_LoaiGiaoDich") or "chuyen nhuong")
    noi_dung = _NOIDUNG_BY_LOAI["chuyen nhuong"][0]
    for key, val in _NOIDUNG_BY_LOAI.items():
        if key in loai:
            noi_dung = val[0]
            break

    add(S.K_KINHGUI, _text(v.get("Don_KinhGui")))
    add(S.K_TEN, ten)
    add(S.K_GIAYTO, giay_to)
    add(S.K_DIACHI, dia_chi)
    add(S.K_MST, mst)
    add(S.K_DIENTHOAI, phone)
    add(S.K_EMAIL, email)
    add(S.K_NOIDUNG, noi_dung)
    add(S.K_MIENGIAM, _text(v.get("Don_MienGiam")))
    # IV. Giấy tờ nộp kèm: mục (2) = hợp đồng chuyển quyền; mục (3) = giấy tờ tùy thân/hộ tịch.
    # "Có thì điền, không thì để trống" → KHÔNG mặc định ép, chỉ điền khi LLM bóc tách được.
    add(S.K_GIAYTOKEM2, _text(v.get("Don_TenHopDong")))
    add(S.K_GIAYTOKEM3, _text(v.get("Don_GiayToKem")))
    add(S.K_TRANHCHAP, _text(v.get("Don_TranhChap")))
    add(S.K_RANHGIOI, _text(v.get("Don_RanhGioi")))

    return out, ([] if out else ["Không bóc tách được dữ liệu Đơn đăng ký biến động."])
