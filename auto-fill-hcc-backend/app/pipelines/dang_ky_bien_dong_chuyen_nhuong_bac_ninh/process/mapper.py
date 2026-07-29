"""Map compact facts → UI field cho e-form Bắc Ninh (đăng ký biến động: chuyển nhượng/thừa kế/tặng cho).

Thân đơn (Phần II) khớp theo NHÃN; người nhận kết quả (Phần IV) khớp theo NAME cố định.
"""

from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.process import schema as S

# Loại giao dịch (chuẩn hóa fold) → (Nội dung biến động, tiền tố tên hợp đồng mặc định).
_NOIDUNG_BY_LOAI = {
    "chuyen nhuong": ("Nhận chuyển nhượng quyền sử dụng đất", "Hợp đồng chuyển nhượng quyền sử dụng đất"),
    "tang cho": ("Nhận tặng cho quyền sử dụng đất", "Hợp đồng tặng cho quyền sử dụng đất"),
    "thua ke": ("Nhận thừa kế quyền sử dụng đất", "Văn bản thừa kế quyền sử dụng đất"),
    "gop von": ("Nhận góp vốn bằng quyền sử dụng đất", "Hợp đồng góp vốn bằng quyền sử dụng đất"),
}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten(value) -> str | None:
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _fold(text: str) -> str:
    import unicodedata
    t = (text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def _giay_to(so, ngay, noi_cap) -> str | None:
    so = (so or "").strip()
    if not so:
        return None
    out = f"CCCD số {so}"
    if (ngay or "").strip():
        out += f" cấp ngày {ngay.strip()}"
    if (noi_cap or "").strip():
        out += f", {noi_cap.strip()}"
    return out


def enrich(fields: list[dict]) -> list[dict]:
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

    ho_ten = v.get("Cccd_HoTen")
    so_dd = v.get("Cccd_SoDinhDanh")
    dia_chi = _flatten(v.get("Don_DiaChi"))
    phone = v.get("Don_DienThoai")

    # Nội dung biến động + tên hợp đồng mặc định theo loại giao dịch (mặc định "chuyển nhượng").
    loai = _fold(v.get("Don_LoaiGiaoDich") or "chuyen nhuong")
    noi_dung, hd_default = _NOIDUNG_BY_LOAI.get("chuyen nhuong")
    for key, val in _NOIDUNG_BY_LOAI.items():
        if key in loai:
            noi_dung, hd_default = val
            break
    ten_hd = v.get("Don_TenHopDong") or hd_default

    # Thân đơn (Phần II) — khớp NHÃN.
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_TEN, ho_ten)
    add(S.L_GIAYTO, _giay_to(so_dd, v.get("Cccd_NgayCap"), v.get("Cccd_NoiCap")))
    add(S.L_DIACHI, dia_chi)
    add(S.L_DIENTHOAI, phone)
    add(S.L_NOIDUNG, noi_dung)
    # (3) Giấy tờ liên quan nộp kèm = tên hợp đồng chuyển quyền (mục (1) là nhãn tĩnh GCN).
    add(S.L_GIAYTOKEM3, ten_hd)

    # Người nhận kết quả (Phần IV) — khớp NAME cố định.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    return out
