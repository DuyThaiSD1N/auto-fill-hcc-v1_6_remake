"""Map compact facts → UI field cho e-form Bắc Ninh (khớp theo NHÃN).

E-form Bắc Ninh (Liferay) không có tên field ổn định: mỗi ô là `element_<id>` với
NHÃN ở thuộc tính `title`. Nên UI field ở đây đặt `name` = cốt nhãn; engine
`fill-bacninh.js` khớp `fold(input.title).startsWith(fold(name))`.
"""

from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process.schema import (
    UI_COMP_BY_NAME,
    UI_LABEL_DIACHI,
    UI_LABEL_DIENTHOAI,
    UI_LABEL_GIAYTO,
    UI_LABEL_GIAYTO2,
    UI_LABEL_GIAYTO3,
    UI_LABEL_KINHGUI,
    UI_LABEL_NOIDUNG,
    UI_LABEL_TEN,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten_address(value) -> str | None:
    """Don_DiaChi nên là chuỗi (fallback đã đảm bảo). Nếu lỡ là object → ghép ĐỦ phường/xã."""
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        # Giữ đủ đơn vị: số nhà/tổ → phường/xã → huyện → tỉnh (quy tắc chung bỏ xã nên vá ở đây).
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        joined = ", ".join(dict.fromkeys(parts))  # bỏ trùng, giữ thứ tự
        return joined or None
    return None


def _giay_to_nhan_than(so: str | None, ngay: str | None, noi_cap: str | None) -> str | None:
    """Ghép "b) Giấy tờ nhân thân/pháp nhân" = "{số}, cấp {ngày}, {nơi cấp}"."""
    so = (so or "").strip()
    if not so:
        return None
    parts = [so]
    if (ngay or "").strip():
        parts.append(f"cấp {ngay.strip()}")
    if (noi_cap or "").strip():
        parts.append(noi_cap.strip())
    return ", ".join(parts)


def enrich(fields: list[dict]) -> list[dict]:
    """Suy ra UI field điền vào e-form Bắc Ninh từ fact nguồn."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(label: str, value) -> None:
        if label in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(label)
        if not comp:
            return
        out.append({"name": label, "comp": comp, "value": value})
        seen.add(label)

    add(UI_LABEL_KINHGUI, values.get("Don_KinhGui"))
    add(UI_LABEL_TEN, values.get("Cccd_HoTen"))
    add(UI_LABEL_GIAYTO, _giay_to_nhan_than(
        values.get("Cccd_SoDinhDanh"), values.get("Cccd_NgayCap"), values.get("Cccd_NoiCap")))
    add(UI_LABEL_DIACHI, _flatten_address(values.get("Don_DiaChi")))
    add(UI_LABEL_DIENTHOAI, values.get("Don_DienThoai"))
    add(UI_LABEL_NOIDUNG, values.get("Don_NoiDungBienDong"))
    add(UI_LABEL_GIAYTO2, values.get("Don_GiayTo2"))
    add(UI_LABEL_GIAYTO3, values.get("Don_GiayTo3"))

    return out
