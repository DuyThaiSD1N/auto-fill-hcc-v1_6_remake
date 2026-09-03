"""Map thông tin nguồn người cao tuổi sang field semantic của eForm Bắc Ninh."""

from typing import Any


def _text(v: Any) -> str | None:
    if v in (None, "", {}, []):
        return None
    return " ".join(str(v).replace("\n", " ").split()).strip() or None


def enrich(fields: list[dict]) -> list[dict]:
    values = {f.get("name"): f.get("value") for f in fields if f.get("value") not in (None, "", {}, [])}
    out: list[dict] = []

    def add(name: str, value: Any, comp: str = "bn-input"):
        value = _text(value)
        if value:
            # Engine Bắc Ninh tự thêm prefix portlet khi khớp NAME; giữ field semantic ngắn để
            # select2 cascade và class eform-element-* hoạt động ổn định giữa các snapshot.
            out.append({"name": name, "comp": comp, "value": value})

    add("doiTuongKhachoTen", values.get("NguoiCaoTuoi_HoTen"))
    add("doiTuongKhacgioiTinhId", values.get("NguoiCaoTuoi_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", values.get("NguoiCaoTuoi_SoDinhDanh"))
    add("doiTuongKhacngayCap", values.get("NguoiCaoTuoi_NgayCap"))
    add("doiTuongKhacnoiCap", values.get("NguoiCaoTuoi_NoiCap"))
    add("doiTuongKhacngaySinh", values.get("NguoiCaoTuoi_NgaySinh"))
    add("doiTuongKhacemail", values.get("NguoiCaoTuoi_Email"))
    add("doiTuongKhacsoDienThoai", values.get("NguoiCaoTuoi_SoDienThoai"))
    address = values.get("NguoiCaoTuoi_ThuongTru") or {}
    if isinstance(address, dict):
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("diaChi"))
    return out
