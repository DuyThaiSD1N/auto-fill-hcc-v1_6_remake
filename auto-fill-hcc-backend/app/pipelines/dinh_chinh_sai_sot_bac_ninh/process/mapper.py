"""Map compact facts → UI field cho e-form Bắc Ninh (đính chính GCN lần đầu có sai sót).

Thân đơn khớp theo CLASS eform-element-<Key>; khối người nhận kết quả khớp theo NAME. Tự nộp →
người nhận kết quả = chính người đứng đơn (dùng lại Cccd_*/Don_*).
"""

import re

from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process import schema as S

# Chấm giữ chỗ của mẫu in ("Mã số thuế: ....") và gạch dài ngăn cấp hành chính ("– xã X –").
_PLACEHOLDER_DOTS_RE = re.compile(r"\s*(?:\.\s*){2,}|\s*…+\s*")
_DASH_SEP_RE = re.compile(r"\s+[–—-]\s+")


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

    # Thân đơn (Đơn Mẫu 18). Ô Tên/Giấy tờ ưu tiên NGUYÊN VĂN dòng của đơn (đơn đại diện hộ/thừa kế
    # ghi kèm năm sinh + tư cách đại diện); không có thì dựng từ CCCD. Nơi/ngày khai cổng tự điền sẵn.
    add(S.K_KINHGUI, _text(v.get("Don_KinhGui")))
    add(S.K_TEN, _text(v.get("Don_Ten")) or ho_ten)
    add(S.K_GIAYTO, _text(v.get("Don_GiayToNhanThan"))
        or _giay_to_nhan_than(so_dd, v.get("Cccd_NgayCap"), v.get("Cccd_NoiCap")))
    add(S.K_DIACHI, dia_chi)
    add(S.K_MST, _digits(_text(v.get("Don_MaSoThue"))))
    add(S.K_DIENTHOAI, phone)
    add(S.K_EMAIL, _text(v.get("Don_Email")))
    add(S.K_NOIDUNG, _text(v.get("Don_NoiDungBienDong")))
    add(S.K_MIENGIAM, _text(v.get("Don_MienGiam")))
    add(S.K_GIAYTO2, _text(v.get("Don_GiayTo2")))
    add(S.K_GIAYTO3, _text(v.get("Don_GiayTo3")))
    add(S.K_THANHVIENHO, _text(v.get("Don_ThanhVienHo")))
    add(S.K_TRANHCHAP, _text(v.get("Don_TranhChap")))
    add(S.K_RANHGIOI, _text(v.get("Don_RanhGioi")))

    # Người nhận kết quả (tự nộp → cùng người đứng đơn; dùng họ tên CCCD, không phải dòng Tên dài).
    # Tỉnh/phường người nhận là select cascade, để user chọn tay theo địa bàn.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    return out
