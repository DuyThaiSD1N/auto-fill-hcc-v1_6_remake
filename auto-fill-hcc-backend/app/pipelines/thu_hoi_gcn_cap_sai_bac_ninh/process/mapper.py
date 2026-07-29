"""Map compact facts → UI field cho e-form Bắc Ninh (thu hồi GCN cấp sai)."""

from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.process import schema as S


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


def _giay_to(so, noi_cap, ngay) -> str | None:
    so = (so or "").strip()
    if not so:
        return None
    out = f"CCCD số {so}"
    if (noi_cap or "").strip():
        out += f" do {noi_cap.strip()}"
    if (ngay or "").strip():
        out += f" cấp ngày {ngay.strip()}"
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

    dia_chi = _flatten(v.get("Don_DiaChi"))
    ho_ten = v.get("Cccd_HoTen")
    so_dd = v.get("Cccd_SoDinhDanh")
    phone = v.get("Don_DienThoai")

    # Thân đơn: a) Tên = tên chủ SDĐ trên GCN (dạng "Hộ ông…"); fallback họ tên CCCD.
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_TEN, v.get("TenChuSuDungDat") or ho_ten)
    add(S.L_GIAYTO, _giay_to(so_dd, v.get("Cccd_NoiCap"), v.get("Cccd_NgayCap")))
    add(S.L_DIACHI, dia_chi)
    add(S.L_DIENTHOAI, phone)

    # Người nhận (dùng họ tên CCCD thật, KHÔNG "Hộ ông").
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    return out
