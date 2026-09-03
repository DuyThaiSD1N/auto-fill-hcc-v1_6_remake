"""Định tuyến nhân thân HSSV vào khối "được ủy quyền" (doiTuongKhac*) của eForm Bắc Ninh 1.014581."""

from typing import Any

from app.pipelines._shared import fold as _fold


def _values(fields: list[dict]) -> dict[str, Any]:
    return {
        field["name"]: field["value"]
        for field in fields
        if field.get("name") and field.get("value") not in (None, "", {}, [])
    }


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    return " ".join(str(value).replace("\n", " ").split()).strip() or None


def _gender_option(value: Any) -> str | None:
    """Select giới tính là NATIVE, option đầy đủ 'Giới tính Nam'/'Giới tính Nữ' → phải khớp nguyên văn."""
    folded = _fold(value)
    if not folded:
        return None
    if "nu" in folded:  # 'nữ' fold thành 'nu'; xét trước 'nam' để không dính chữ 'nam' trong 'nu'
        return "Giới tính Nữ"
    if "nam" in folded:
        return "Giới tính Nam"
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    """Chỉ có một mục đích (khối ủy quyền = HSSV) nên bỏ qua purpose; luôn phát doiTuongKhac*."""
    values = _values(fields)
    out: list[dict] = []

    def add(name: str, value: Any, comp: str = "bn-input") -> None:
        value = _text(value)
        if value:
            out.append({"name": name, "comp": comp, "value": value})

    add("doiTuongKhachoTen", values.get("HocSinh_HoTen"))
    add("doiTuongKhacgioiTinhId", _gender_option(values.get("HocSinh_GioiTinh")), "bn-select")
    add("doiTuongKhacsoDinhDanh", values.get("HocSinh_SoDinhDanh"))
    add("doiTuongKhacngayCap", values.get("HocSinh_NgayCap"))
    add("doiTuongKhacnoiCap", values.get("HocSinh_NoiCap"))
    add("doiTuongKhacngaySinh", values.get("HocSinh_NgaySinh"))
    add("doiTuongKhacemail", values.get("HocSinh_Email"))
    add("doiTuongKhacsoDienThoai", values.get("HocSinh_SoDienThoai"))

    address = values.get("HocSinh_ThuongTru")
    if isinstance(address, dict):
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("diaChi"))

    name = _text(values.get("HocSinh_HoTen"))
    identity = _text(values.get("HocSinh_SoDinhDanh"))
    if not name or not identity:
        return out, ["Chưa trích đủ họ tên và số định danh của học sinh, sinh viên từ hồ sơ."]
    return out, []
