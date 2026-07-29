"""Map compact facts → UI field cho e-form Bắc Ninh (giao/thuê/chuyển mục đích SDĐ).

Thân đơn (Phần II) khớp theo NHÃN; người nhận kết quả (Phần IV) khớp theo NAME cố định.
"""

from app.pipelines.giao_thue_chuyen_muc_dich_dat_bac_ninh.process.schema import (
    UI_COMP_BY_NAME,
    UI_LABEL_CAMKET,
    UI_LABEL_DIACHILH,
    UI_LABEL_DIACHITS,
    UI_LABEL_DIADIEM,
    UI_LABEL_DIENTICH,
    UI_LABEL_KINHGUI,
    UI_LABEL_LOAIDON,
    UI_LABEL_LUAA,
    UI_LABEL_LUAB,
    UI_LABEL_MUCDICH,
    UI_LABEL_NGUOIDN,
    UI_LABEL_RUNG,
    UI_LABEL_TAILIEU,
    UI_LABEL_THOIHAN,
    UI_NAME_NN_CCCD,
    UI_NAME_NN_DIACHI,
    UI_NAME_NN_HOTEN,
    UI_NAME_NN_SDT,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten(value) -> str | None:
    """Địa chỉ nên là chuỗi (fallback đã lo). Nếu lỡ là object → ghép ĐỦ phường/xã."""
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


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

    dia_chi = _flatten(values.get("Don_DiaChiTruSo"))
    phone = values.get("Don_SoDienThoai")
    ho_ten = values.get("Don_NguoiDeNghi")

    # Thân đơn (Phần II) — theo NHÃN.
    add(UI_LABEL_LOAIDON, values.get("Don_LoaiDon"))
    add(UI_LABEL_KINHGUI, values.get("Don_KinhGui"))
    add(UI_LABEL_NGUOIDN, ho_ten)
    add(UI_LABEL_DIACHITS, dia_chi)
    add(UI_LABEL_DIACHILH, phone)
    add(UI_LABEL_DIADIEM, _flatten(values.get("Don_DiaDiemThuaDat")))
    add(UI_LABEL_DIENTICH, values.get("Don_DienTichDat"))
    add(UI_LABEL_LUAA, values.get("Don_DienTichLuaA"))
    add(UI_LABEL_LUAB, values.get("Don_DienTichLuaB"))
    add(UI_LABEL_RUNG, values.get("Don_DienTichRung"))
    add(UI_LABEL_MUCDICH, values.get("Don_MucDich"))
    add(UI_LABEL_THOIHAN, values.get("Don_ThoiHan"))
    add(UI_LABEL_CAMKET, values.get("Don_CamKet"))
    add(UI_LABEL_TAILIEU, values.get("Don_TaiLieuKem"))

    # Người nhận kết quả (Phần IV) — theo NAME cố định.
    add(UI_NAME_NN_HOTEN, ho_ten)
    add(UI_NAME_NN_CCCD, values.get("Cccd_SoDinhDanh"))
    add(UI_NAME_NN_SDT, phone)
    add(UI_NAME_NN_DIACHI, dia_chi)

    return out
