"""Map compact facts → UI field cho e-form Bắc Ninh (cấp lại GCN do bị mất, 1.115465).

Thân đơn khớp CLASS eform-element-<Key>; khối người nhận kết quả và khối ủy quyền khớp NAME. Tự nộp → người nhận kết
quả = chính người đứng đơn (dùng lại Cccd_*/Don_*).
"""

import re

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process import schema as S

# Chấm giữ chỗ của mẫu in ("Mã số thuế: ....") và gạch ngăn cấp hành chính ("Thôn X - Phường Y - Tỉnh Z").
_PLACEHOLDER_DOTS_RE = re.compile(r"\s*(?:\.\s*){2,}|\s*…+\s*")
_DASH_SEP_RE = re.compile(r"\s+[–—-]\s+")

# Câu mặc định theo hướng dẫn (3) của Mẫu 18 khi Đơn không ghi mục II mà vẫn có số GCN bị mất.
NOI_DUNG_MAC_DINH = "Cấp lại Giấy chứng nhận do bị mất"


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


def _giay_to_nhan_than(so: str | None, ngay: str | None, noi_cap: str | None) -> str | None:
    """Ghép "Giấy tờ nhân thân/pháp nhân" = "CCCD số {số}, cấp {ngày}, {nơi cấp}"."""
    so = (so or "").strip()
    if not so:
        return None
    parts = [f"CCCD số {so}"]
    if (ngay or "").strip():
        parts.append(f"cấp {ngay.strip()}")
    if (noi_cap or "").strip():
        parts.append(noi_cap.strip())
    return ", ".join(parts)


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


def _compact(value: str) -> str:
    """So khớp số GCN bỏ khoảng trắng/dấu: "CĐ 123456" ≡ "CĐ123456"."""
    return re.sub(r"\W+", "", value or "").upper()


def _noi_dung_bien_dong(noi_dung, so_vao_so, so_phat_hanh) -> str | None:
    """Mục II + thông tin GCN bị mất theo hướng dẫn (3) Mẫu 18: "đề nghị cấp lại GCN do bị mất" kèm Số vào sổ cấp GCN
    và Số phát hành (số seri). Đơn đã ghi số nào thì không ghi lại."""
    lines = _lines(noi_dung)
    have = _compact(" ".join(lines))
    extra = []
    so_vao_so = _text(so_vao_so)
    if so_vao_so and _compact(so_vao_so) not in have:
        extra.append(f"Số vào sổ cấp Giấy chứng nhận: {so_vao_so}")
    so_phat_hanh = _text(so_phat_hanh)
    if so_phat_hanh and _compact(so_phat_hanh) not in have:
        extra.append(f"Số phát hành (số seri): {so_phat_hanh}")
    if not lines and not extra:
        return None
    if not lines:
        lines = [NOI_DUNG_MAC_DINH]
    if extra:
        lines.append("Thông tin Giấy chứng nhận bị mất: " + "; ".join(extra))
    return "\n".join(lines)


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

    ho_ten = _text(v.get("Cccd_HoTen"))
    so_dd = _digits(v.get("Cccd_SoDinhDanh"))
    phone = _digits(v.get("Don_DienThoai"))
    dia_chi = _flatten_address(v.get("Don_DiaChi"))
    noi_cap = _text(v.get("Cccd_NoiCap"))

    # Thân đơn (Đơn Mẫu 18). Nơi/ngày khai hồ sơ cổng tự điền sẵn → không phát.
    add(S.K_KINHGUI, _text(v.get("Don_KinhGui")))
    add(S.K_TEN, ho_ten)
    add(S.K_GIAYTO, _giay_to_nhan_than(so_dd, _text(v.get("Cccd_NgayCap")),
                                       normalize_issuer(noi_cap) if noi_cap else None))
    add(S.K_DIACHI, dia_chi)
    add(S.K_MST, _digits(_text(v.get("Don_MaSoThue"))))
    add(S.K_DIENTHOAI, phone)
    add(S.K_EMAIL, _text(v.get("Don_Email")))
    add(S.K_NOIDUNG, _noi_dung_bien_dong(v.get("Don_NoiDungBienDong"), v.get("Gcn_SoVaoSo"),
                                         v.get("Gcn_SoPhatHanh")))
    add(S.K_MIENGIAM, _text(v.get("Don_MienGiam")))
    add(S.K_GIAYTO2, _text(v.get("Don_GiayTo2")))
    add(S.K_GIAYTO3, _text(v.get("Don_GiayTo3")))
    add(S.K_THANHVIENHO, _text(v.get("Don_ThanhVienHo")))
    add(S.K_TRANHCHAP, _text(v.get("Don_TranhChap")))
    add(S.K_RANHGIOI, _text(v.get("Don_RanhGioi")))

    # Người nhận kết quả (tự nộp → cùng người đứng đơn). Tỉnh/phường người nhận là select cascade, để user chọn tay.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

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
        tt = {**tt, "diaChi": tt.get("diaChi") or tt.get("chiTietDuoiXa")}
        add("doiTuongKhactinhThanhId", tt.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", tt.get("xa") or tt.get("phuong"), "bn-select")
    add("doiTuongKhacdiaChiChiTiet", _flatten_address(tt))

    if not name or not ident:
        return [], ["Chưa bóc tách đủ họ tên và CCCD của chủ hồ sơ (người ủy quyền) từ Đơn/CCCD."]
    return out, []
