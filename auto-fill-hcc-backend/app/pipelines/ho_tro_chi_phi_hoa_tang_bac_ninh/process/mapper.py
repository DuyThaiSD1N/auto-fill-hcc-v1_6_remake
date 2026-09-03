"""Định tuyến dữ liệu nguồn vào hai thao tác riêng trên eForm Bắc Ninh."""

from typing import Any


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


def _truthy(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "co", "có", "1"}


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _values(fields)
    purpose = str((options or {}).get("purpose") or "registration_form")
    if purpose == "authorized_person":
        return _authorized_fields(values)
    return _registration_fields(values)


def _registration_fields(values: dict[str, Any]) -> tuple[list[dict], list[str]]:
    # Các key semantic NgaySinh/SoCCCD/CapNgay/NoiCap/Địa chỉ bị lặp giữa mục I và II.
    # Dùng đúng name element của eForm 1.014582 để không bao giờ điền nhầm người.
    mapping = [
        ("element_75750", "Don_KinhGui"),
        ("element_75752", "NguoiChet_HoTen"),
        ("element_75753", "NguoiChet_NgaySinh"),
        ("element_75754", "NguoiChet_GioiTinh"),
        ("element_75755", "NguoiChet_DanToc"),
        ("element_75756", "NguoiChet_SoDinhDanh"),
        ("element_75757", "NguoiChet_NgayCap"),
        ("element_75758", "NguoiChet_NoiCap"),
        ("element_75759", "NguoiChet_DiaChiThuongTru"),
        ("element_75760", "NguoiChet_NgayChet"),
        ("element_75761", "KhaiTu_So"),
        ("element_75762", "KhaiTu_CoQuanCap"),
        ("element_75763", "KhaiTu_NgayCap"),
        ("element_75764", "HoaTang_ThoiGian"),
        ("element_75765", "HoaTang_DiaDiem"),
        ("element_75767", "NguoiDungRa_HoTen"),
        ("element_75768", "NguoiDungRa_NgaySinh"),
        ("element_75769", "NguoiDungRa_SoDinhDanh"),
        ("element_75770", "NguoiDungRa_NgayCap"),
        ("element_75771", "NguoiDungRa_NoiCap"),
        ("element_75772", "NguoiDungRa_DiaChiThuongTru"),
        ("element_75773", "NguoiDungRa_SoDienThoai"),
        ("element_75774", "NguoiDungRa_SoTaiKhoan"),
        ("element_75775", "NguoiDungRa_NganHang"),
        ("element_75776", "NguoiDungRa_QuanHeVoiNguoiChet"),
        ("element_75778", "Don_CoQuanDeNghi"),
        ("element_75780", "Don_NgayLap"),
    ]
    out = [
        {"name": target, "comp": "bn-input", "value": value}
        for target, source in mapping
        if (value := _text(values.get(source)))
    ]
    warnings = [] if out else ["Không bóc tách được dữ liệu của Đơn đề nghị hỗ trợ kinh phí hỏa táng."]
    return out, warnings


def _authorized_fields(values: dict[str, Any]) -> tuple[list[dict], list[str]]:
    if not _truthy(values.get("UyQuyen_CoBienBan")):
        return [], ["Không tìm thấy Biên bản/Văn bản ủy quyền trong hồ sơ."]

    out: list[dict] = []

    def add(name: str, value: Any, comp: str = "bn-input") -> None:
        value = _text(value)
        if value:
            out.append({"name": name, "comp": comp, "value": value})

    add("doiTuongKhachoTen", values.get("NguoiDuocUyQuyen_HoTen"))
    add("doiTuongKhacgioiTinhId", values.get("NguoiDuocUyQuyen_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", values.get("NguoiDuocUyQuyen_SoDinhDanh"))
    add("doiTuongKhacngayCap", values.get("NguoiDuocUyQuyen_NgayCap"))
    add("doiTuongKhacnoiCap", values.get("NguoiDuocUyQuyen_NoiCap"))
    add("doiTuongKhacngaySinh", values.get("NguoiDuocUyQuyen_NgaySinh"))
    add("doiTuongKhacemail", values.get("NguoiDuocUyQuyen_Email"))
    add("doiTuongKhacsoDienThoai", values.get("NguoiDuocUyQuyen_SoDienThoai"))
    address = values.get("NguoiDuocUyQuyen_ThuongTru")
    if isinstance(address, dict):
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("diaChi"))

    identity = _text(values.get("NguoiDuocUyQuyen_SoDinhDanh"))
    name = _text(values.get("NguoiDuocUyQuyen_HoTen"))
    if not name or not identity:
        return [], ["Biên bản ủy quyền chưa cho biết đủ họ tên và CCCD của người được ủy quyền."]
    return out, []
