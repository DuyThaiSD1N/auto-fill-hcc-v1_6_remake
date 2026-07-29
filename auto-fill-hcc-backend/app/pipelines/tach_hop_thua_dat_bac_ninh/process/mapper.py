"""Map compact facts → UI field cho e-form Bắc Ninh (tách thửa đất).

Thân đơn khớp theo NHÃN (Phần II/III trùng title → FE lấy DOM đầu = tách); người nhận kết quả
khớp theo NAME cố định.
"""

from app.pipelines.tach_hop_thua_dat_bac_ninh.process import schema as S


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


def _split_address(full: str | None) -> tuple[str, str, str]:
    """Tách chuỗi địa chỉ "chi tiết, [phường/xã X], [tỉnh/tp Y]" → (tỉnh, xã, chi_tiết).

    Giữ NGUYÊN tiền tố ("Phường …"/"Xã …"/"tỉnh …") để khớp EXACT option của select. Cấp nhỏ nhất
    (tổ dân phố/xóm/số nhà) đi vào chi tiết; phần tử cuối coi là tỉnh/thành, phần "phường/xã/thị trấn"
    là xã. Không có xã → xã rỗng, chi tiết = tất cả trừ tỉnh.
    """
    if not isinstance(full, str) or not full.strip():
        return "", "", ""
    parts = [p.strip() for p in full.split(",") if p.strip()]
    if not parts:
        return "", "", ""
    tinh = parts[-1] if len(parts) >= 1 else ""
    rest = parts[:-1]
    xa = ""
    xa_idx = None
    for i, p in enumerate(rest):
        low = p.lower()
        if low.startswith(("phường", "xã", "thị trấn")):
            xa = p
            xa_idx = i
            break
    if xa_idx is not None:
        chi_tiet = ", ".join(rest[:xa_idx])
    else:
        chi_tiet = ", ".join(rest)
    return tinh, xa, chi_tiet


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
    dia_chi = _flatten(v.get("Nguoi_DiaChiThuongTru"))
    phone = v.get("Nguoi_DienThoai")  # thường không có
    tinh, xa, chi_tiet = _split_address(dia_chi)

    # Phần I — người sử dụng đất. Địa chỉ TÁCH: Tỉnh/Xã → select (bn-select, FE điền cascade);
    # ô "Địa chỉ chi tiết" chỉ nhận tổ dân phố/xóm/số nhà (bỏ nếu không có).
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_TEN, ho_ten)
    add(S.L_GIAYTO, so_dd)
    add(S.S_TINH_DON, tinh)
    add(S.S_XA_DON, xa)
    add(S.L_DIACHI_CT, chi_tiet)

    # Phần II — thửa đất gốc + thửa mới.
    add(S.L_THUA_SO, v.get("Thua_So"))
    add(S.L_TOBANDO, v.get("Thua_ToBanDo"))
    add(S.L_DIENTICH, v.get("Thua_DienTich"))
    add(S.L_LOAIDAT, v.get("Thua_LoaiDat"))
    add(S.L_DIACHITHUA, _flatten(v.get("Thua_DiaChi")))
    add(S.L_SOVAOSO, v.get("Gcn_SoVaoSo"))
    add(S.L_NGAYCAP, v.get("Gcn_NgayCap"))
    add(S.L_THUAMOI1, v.get("ThuaMoi_DienTich1"))
    add(S.L_THUAMOI2, v.get("ThuaMoi_DienTich2"))

    # Phần IV — lý do/giấy tờ kèm/đề nghị cấp GCN.
    add(S.L_LYDO, v.get("Don_LyDo"))
    add(S.L_GIAYTOKEM, v.get("Don_GiayToKem"))
    add(S.L_DENGHIGCN, v.get("Don_DeNghiCapGCN"))

    # Người nhận kết quả — theo NAME cố định. Cũng tách Tỉnh/Xã select (cascade) + chi tiết.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_TINH, tinh)
    add(S.N_XA, xa)
    add(S.N_DIACHI, chi_tiet)

    return out
