"""Map compact facts → UI field cho e-form Bắc Ninh 1.115460 (đổi tên / thay đổi thông tin người sử dụng đất).

Thân đơn khớp CLASS eform-element-<Key>; nơi / ngày khai, khối người nhận kết quả và khối ủy quyền khớp NAME. Theo
mapping Excel 25/11/2026: Đơn hai người đồng sử dụng (Mẫu 24 mục 1.1 + 1.2) ghép một ô ("Ông: A; Bà: B"); mục II chép
nguyên văn Đơn; mục IV (2) và mục V lấy từ Văn bản cam kết của các thành viên hộ khi Đơn để trống. Người nhận kết quả =
người thứ nhất đứng đơn.
"""

import re
from datetime import date

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process import schema as S

# Chấm giữ chỗ của mẫu in ("Mã số thuế: ....") và gạch ngăn cấp hành chính ("Thôn X - Phường Y - Tỉnh Z").
_PLACEHOLDER_DOTS_RE = re.compile(r"\s*(?:\.\s*){2,}|\s*…+\s*")
_DASH_SEP_RE = re.compile(r"\s+[–—-]\s+")
_ADMIN_HEAD_RE = re.compile(r"^(?:xã|phường|thị trấn|tỉnh|thành phố|huyện|quận|thị xã)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value) -> str | None:
    if value in (None, "", {}, []):
        return None
    # Bỏ chấm giữ chỗ: "CCCD...." → "CCCD"; ô chỉ có "...." → trống.
    text = _PLACEHOLDER_DOTS_RE.sub(" ", str(value))
    return " ".join(text.split()).strip(" ,;") or None


def _digits(value) -> str | None:
    return re.sub(r"\D+", "", str(value or "")) or None


def _flatten_address(value) -> str | None:
    """Don_DiaChi nên là chuỗi (fallback đã đảm bảo). Nếu lỡ là object → ghép ĐỦ phường/xã."""
    if isinstance(value, str):
        text = _PLACEHOLDER_DOTS_RE.sub(" ", value)
        text = _DASH_SEP_RE.sub(", ", text)
        text = " ".join(text.split())
        text = re.sub(r"\s+,", ",", text)
        return text.strip(" ,;.") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _lines(value) -> list[str]:
    """Mục II viết tay nhiều dòng gạch đầu dòng → giữ từng dòng (ô là textarea), bỏ dòng chỉ có dấu chấm."""
    if value in (None, "", {}, []):
        return []
    out = []
    for raw in str(value).replace("\r", "\n").split("\n"):
        line = " ".join(_PLACEHOLDER_DOTS_RE.sub(" ", raw).split()).strip(" ,;")
        if line and line not in ("-", "–"):
            out.append(line)
    return out


def _danh_xung(value) -> str | None:
    text = (_text(value) or "").strip(" :.").lower()
    return {"ông": "Ông", "bà": "Bà"}.get(text)


def _fold(value) -> str:
    return re.sub(r"\W+", "", str(value or "")).lower()


def _address_detail(address: str | None) -> str | None:
    """Phần dưới xã của địa chỉ một dòng ("Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh" → "Thôn Đông") cho ô Địa chỉ liên hệ
    người nhận (tỉnh / xã là select riêng). Không tách được → None."""
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    if len(parts) < 2 or _ADMIN_HEAD_RE.match(parts[0]):
        return None
    return parts[0]


def _join_people(values: list[tuple[str | None, str | None]]) -> str | None:
    """Ô một dòng cho nhiều người đứng đơn: một người → giá trị trơn; hai người → "Ông: A; Bà: B" (thiếu danh xưng thì
    nối "; ")."""
    items = [(dx, val) for dx, val in values if val]
    if not items:
        return None
    if len(items) == 1:
        return items[0][1]
    return "; ".join(f"{dx}: {val}" if dx else val for dx, val in items)


def _unique(values: list[str | None]) -> str | None:
    """Ghép các giá trị khác nhau bằng "; " (hai người cùng địa chỉ → ghi một lần)."""
    out: dict[str, str] = {}
    for value in values:
        if value and _fold(value) not in out:
            out[_fold(value)] = value
    return "; ".join(out.values()) or None


def _members(value) -> str | None:
    """Vbck_ThanhVien (mảng) → "1. Ông A, sinh ngày …, CCCD số …, thường trú: …; 2. Bà B, …" cho ô một dòng mục V (1)."""
    if isinstance(value, str):
        return _text(value)
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("hoTen"))
        if not name:
            continue
        dx = _danh_xung(item.get("danhXung"))
        parts = [f"{dx} {name}" if dx else name]
        if _text(item.get("ngaySinh")):
            parts.append(f"sinh ngày {_text(item.get('ngaySinh'))}")
        if _digits(item.get("soDinhDanh")):
            parts.append(f"CCCD số {_digits(item.get('soDinhDanh'))}")
        if _flatten_address(item.get("thuongTru")):
            parts.append(f"thường trú: {_flatten_address(item.get('thuongTru'))}")
        out.append(f"{len(out) + 1}. " + ", ".join(parts))
    return "; ".join(out) or None


def _van_ban_cam_ket(tieu_de, chung_thuc) -> str | None:
    """Giấy nộp kèm (2) khi Đơn để trống: tên văn bản cam kết thành viên hộ + lời chứng thực trong ngoặc."""
    tieu_de = _text(tieu_de)
    if not tieu_de:
        return None
    tieu_de = tieu_de[0].upper() + tieu_de[1:]
    chung_thuc = _text(chung_thuc)
    return f"{tieu_de} ({chung_thuc})" if chung_thuc else tieu_de


def enrich(fields: list[dict]) -> list[dict]:
    """Suy ra UI field điền vào e-form Bắc Ninh từ fact nguồn (mapping Excel 25/11/2026)."""
    v = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = S.UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    # Người thứ nhất (CCCD → Đơn) và người thứ hai đồng sử dụng (mục 1.2 Mẫu 24).
    ho_ten = _text(v.get("Cccd_HoTen"))
    so_dd = _digits(v.get("Cccd_SoDinhDanh"))
    dia_chi = _flatten_address(v.get("Don_DiaChi"))
    ho_ten2 = _text(v.get("Don2_HoTen"))
    so_dd2 = _digits(v.get("Don2_SoGiayTo"))
    dia_chi2 = _flatten_address(v.get("Don2_DiaChi"))
    if ho_ten2 and ho_ten and _fold(ho_ten2) == _fold(ho_ten):
        ho_ten2 = so_dd2 = dia_chi2 = None  # LLM chép lại người thứ nhất
    phone = _digits(v.get("Don_DienThoai")) or (_digits(v.get("Don2_DienThoai")) if ho_ten2 else None)
    email = _text(v.get("Don_Email")) or (_text(v.get("Don2_Email")) if ho_ten2 else None)

    # Thân đơn. Tên / giấy tờ / địa chỉ hai người ghép một ô theo mapping ("Ông: A; Bà: B").
    add(S.K_KINHGUI, _text(v.get("Don_KinhGui")))
    add(S.K_TEN, _join_people([(_danh_xung(v.get("Don_DanhXung")), ho_ten),
                               (_danh_xung(v.get("Don2_DanhXung")), ho_ten2)]))
    add(S.K_GIAYTO, _unique([so_dd, so_dd2 if ho_ten2 else None]))
    add(S.K_DIACHI, _unique([dia_chi, dia_chi2 if ho_ten2 else None]))
    add(S.K_MST, _digits(_text(v.get("Don_MaSoThue"))))
    add(S.K_DIENTHOAI, phone)
    add(S.K_EMAIL, email)
    noi_dung = _lines(v.get("Don_NoiDungBienDong"))
    add(S.K_NOIDUNG, "\n".join(noi_dung) or None)  # nguyên văn Đơn, không tự đặt câu
    add(S.K_MIENGIAM, _text(v.get("Don_MienGiam")))
    add(S.K_GIAYTO2, _text(v.get("Don_GiayTo2")) or _van_ban_cam_ket(v.get("Vbck_TieuDe"), v.get("Vbck_ChungThuc")))
    add(S.K_GIAYTO3, _text(v.get("Don_GiayTo3")))
    # Mục V: Đơn Mẫu 24 không có mục này → lấy từ Văn bản cam kết của các thành viên hộ gia đình.
    add(S.K_THANHVIENHO, _text(v.get("Don_ThanhVienHo")) or _members(v.get("Vbck_ThanhVien")))
    add(S.K_TRANHCHAP, _text(v.get("Don_TranhChap")) or _text(v.get("Vbck_TranhChap")))
    add(S.K_RANHGIOI, _text(v.get("Don_RanhGioi")))
    add(S.E_NOI_KHAI, _text(v.get("Don_NoiKhai")))
    add(S.E_NGAY_KHAI, _text(v.get("Don_NgayKhai")) if _DATE_RE.fullmatch(_text(v.get("Don_NgayKhai")) or "") else None)

    # Người nhận kết quả = người thứ nhất đứng đơn. Tỉnh / xã người nhận là select cascade, để user chọn tay.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, _address_detail(dia_chi) or dia_chi)

    return out


def enrich_authorized(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """purpose="authorized_person": khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*).

    Khối này = CHỦ HỒ SƠ (người đứng Đơn / bên A của Giấy ủy quyền), KHÔNG phải người nộp thay (đó là tài khoản đang
    nộp). Extension tự tick ô bổ sung + chọn loại đối tượng trước khi điền. Tỉnh/phường là select2 cascade → phát Tỉnh
    trước Phường.
    """
    v = _by_name(fields)
    name = _text(v.get("ChuHoSo_HoTen"))
    ident = _digits(v.get("ChuHoSo_SoDinhDanh"))
    out: list[dict] = []

    def add(field: str, value, comp: str = "bn-input") -> None:
        value = _text(value)
        if value:
            out.append({"name": field, "comp": comp, "value": value})

    gioi_tinh = _text(v.get("ChuHoSo_GioiTinh"))
    add("doiTuongKhachoTen", name)
    add("doiTuongKhacgioiTinhId", gioi_tinh if gioi_tinh in ("Nam", "Nữ") else None, "bn-select")
    add("doiTuongKhacsoDinhDanh", ident)
    add("doiTuongKhacngayCap", v.get("ChuHoSo_NgayCap"))
    noi_cap = _text(v.get("ChuHoSo_NoiCap"))
    add("doiTuongKhacnoiCap", normalize_issuer(noi_cap) if noi_cap else None)
    add("doiTuongKhacngaySinh", v.get("ChuHoSo_NgaySinh"))
    add("doiTuongKhacemail", v.get("ChuHoSo_Email"))
    add("doiTuongKhacsoDienThoai", _digits(v.get("ChuHoSo_DienThoai")))
    tt = v.get("ChuHoSo_ThuongTru")
    if isinstance(tt, dict):
        # Tỉnh / xã là select riêng → ô "Địa chỉ" chỉ phần dưới xã (mapping: "Thôn …").
        add("doiTuongKhactinhThanhId", tt.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", tt.get("xa") or tt.get("phuong"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", tt.get("chiTietDuoiXa") or tt.get("diaChi") or _flatten_address(tt))
    else:
        add("doiTuongKhacdiaChiChiTiet", _flatten_address(tt))

    if not name or not ident:
        return [], ["Chưa bóc tách đủ họ tên và CCCD của chủ hồ sơ (người ủy quyền) từ Đơn/CCCD."]
    return out, []


def authorized_subject(fields: list[dict], today: date | None = None) -> str | None:
    """Loại "Người ủy quyền là:" — chủ hồ sơ đủ 60 tuổi → "Người cao tuổi"; không rõ ngày sinh / dưới 60 → None (loại
    mặc định của registry)."""
    m = _DATE_RE.search(str(_by_name(fields).get("ChuHoSo_NgaySinh") or ""))
    if not m:
        return None
    try:
        born = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    today = today or date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return S.SUBJECT_NGUOI_CAO_TUOI if age >= S.TUOI_CAO_TUOI else None
