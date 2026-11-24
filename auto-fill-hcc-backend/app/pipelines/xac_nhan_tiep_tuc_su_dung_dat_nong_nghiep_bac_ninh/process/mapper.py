"""Map compact facts → UI field cho e-form Bắc Ninh 1.115462 (xác nhận tiếp tục sử dụng đất nông nghiệp).

Thân đơn Mẫu 09 khớp NAME element_<id> (eform 2869); khối người nhận kết quả và khối ủy quyền khớp NAME cố định của
cổng. Người nhận kết quả tại nhà = chủ hồ sơ (người sử dụng đất đứng Đơn), như mapping.
"""

import re
from datetime import date

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.process import schema as S

# Chấm giữ chỗ của mẫu in ("đến ngày…….", "…") và gạch ngăn cấp hành chính ("Thôn X - Xã Y - Tỉnh Z").
_PLACEHOLDER_DOTS_RE = re.compile(r"\s*(?:\.\s*){2,}|\s*…+\s*")
_DASH_SEP_RE = re.compile(r"\s+[–—-]\s+")
# Phần điện thoại / email trong ô "2. Địa chỉ liên hệ (điện thoại, email...)".
_PHONE_PART_RE = re.compile(r"[,;]?\s*(?:đ(?:iện)?\s*t(?:hoại)?|đt|sđt|email|e-mail)\b.*$", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:điện\s*thoại|đt|sđt)\s*[:.]?\s*((?:\+?84|0)[\d.\s-]{8,14}\d)", re.IGNORECASE)
_ADMIN_HEAD_RE = re.compile(r"^(?:xã|phường|thị trấn|tỉnh|thành phố|huyện|quận|thị xã)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = _PLACEHOLDER_DOTS_RE.sub(" ", str(value))
    return " ".join(text.split()).strip(" ,;") or None


def _digits(value) -> str | None:
    return re.sub(r"\D+", "", str(value or "")) or None


def _one_line(value) -> str | None:
    """Ô input một dòng: nối các đoạn bằng dấu cách (nội dung xác nhận UBND xã có nhiều đoạn — dán đủ, không cắt)."""
    if value in (None, "", {}, []):
        return None
    lines = [_text(line) for line in str(value).replace("\r", "\n").split("\n")]
    return " ".join(line for line in lines if line) or None


def _series(value) -> str | None:
    """Danh sách thửa / tờ / diện tích: "59; 156\\n43" → "59, 156, 43" (giữ thứ tự, bỏ phần tử rỗng)."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, (list, tuple)):
        parts = [str(p) for p in value]
    else:
        # Dấu phẩy KHÔNG kèm dấu cách là phần thập phân ("312,5") → không tách ở đó.
        parts = re.split(r"\s*[;\n]\s*|,\s+|\s+và\s+", str(value))
    parts = [_text(p) for p in parts]
    return ", ".join(p for p in parts if p) or None


def _flatten_address(value) -> str | None:
    if isinstance(value, str):
        text = _PLACEHOLDER_DOTS_RE.sub(" ", value)
        text = _DASH_SEP_RE.sub(", ", text)
        text = " ".join(text.split())
        text = re.sub(r"\s+,", ",", text)
        return text.strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "chiTietDuoiXa", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _phone_from_address(address: str | None) -> str | None:
    m = _PHONE_RE.search(address or "")
    return _digits(m.group(1)) if m else None


def _address_detail(address: str | None) -> str | None:
    """Phần dưới xã của địa chỉ liên hệ ("Thôn Quan Đình, xã …, điện thoại …" → "Thôn Quan Đình")."""
    base = _PHONE_PART_RE.sub("", address or "").strip(" ,;")
    parts = [p.strip() for p in base.split(",") if p.strip()]
    if len(parts) < 2 or _ADMIN_HEAD_RE.match(parts[0]):
        return None
    return parts[0]


def _number(value) -> str | None:
    """Ngày / tháng / năm viết tay ở mục 4: chỉ giữ chữ số."""
    return _digits(_text(value))


def enrich(fields: list[dict]) -> list[dict]:
    """Suy ra UI field điền vào e-form Bắc Ninh từ fact nguồn."""
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

    dia_chi = _flatten_address(v.get("Don_DiaChiLienHe"))
    phone = _digits(v.get("Don_DienThoai")) or _phone_from_address(dia_chi)

    # Thân đơn Mẫu 09 — nơi / ngày khai theo Đơn giấy (cổng điền sẵn "Bắc Ninh" + ngày hôm nay).
    add(S.E_NOI_KHAI, _text(v.get("Don_NoiKhai")))
    add(S.E_NGAY_KHAI, _text(v.get("Don_NgayKhai")))
    add(S.E_KINH_GUI, _text(v.get("Don_KinhGui")))
    add(S.E_DIA_CHI, dia_chi)
    add(S.E_THUA_SO, _series(v.get("Don_ThuaSo")))
    add(S.E_TO_BAN_DO, _series(v.get("Don_ToBanDo")))
    add(S.E_DIEN_TICH, _series(v.get("Don_DienTich")))
    add(S.E_MUC_DICH, _text(v.get("Don_MucDich")))
    add(S.E_THOI_HAN, _text(v.get("Don_ThoiHan")))
    add(S.E_TAI_SAN, _text(v.get("Don_TaiSan")))
    add(S.E_DIA_DIEM, _one_line(v.get("Don_DiaDiem")))
    add(S.E_SO_PHAT_HANH, _text(v.get("Gcn_SoPhatHanh")))
    add(S.E_SO_VAO_SO, _text(v.get("Gcn_SoVaoSo")))
    add(S.E_NGAY_CAP_GCN, _text(v.get("Gcn_NgayCap")))
    add(S.E_NOI_DUNG, _one_line(v.get("Don_NoiDungDeNghi")))
    add(S.E_DEN_NGAY, _number(v.get("Don_DenNgay")))
    add(S.E_DEN_THANG, _number(v.get("Don_DenThang")))
    add(S.E_DEN_NAM, _number(v.get("Don_DenNam")))
    xn = _one_line(v.get("Xn_NoiDung"))
    add(S.E_XN_NOI_DUNG, xn)
    if xn:  # ngày ký chỉ có nghĩa khi trang xác nhận có nội dung
        add(S.E_XN_NGAY, _text(v.get("Xn_NgayXacNhan")))

    # Người nhận kết quả tại nhà = chủ hồ sơ. Tỉnh / xã người nhận là select cascade, để user chọn tay.
    add(S.N_HOTEN, _text(v.get("Don_NguoiSuDungDat")))
    add(S.N_CCCD, _digits(v.get("ChuHoSo_SoDinhDanh")))
    add(S.N_SDT, phone)
    add(S.N_DIACHI, _address_detail(dia_chi))
    return out


def enrich_authorized(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """purpose="authorized_person": khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*) = CHỦ HỒ SƠ.

    Extension tự tick ô bổ sung + chọn loại đối tượng trước khi điền. Tỉnh/phường là select2 cascade → phát Tỉnh
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
        add("doiTuongKhactinhThanhId", tt.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", tt.get("xa") or tt.get("phuong"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", tt.get("chiTietDuoiXa") or tt.get("diaChi"))
    else:
        add("doiTuongKhacdiaChiChiTiet", _flatten_address(tt))

    if not name or not ident:
        return [], ["Chưa bóc tách đủ họ tên và CCCD của chủ hồ sơ (bên ủy quyền) từ Giấy ủy quyền/Đơn/CCCD."]
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
