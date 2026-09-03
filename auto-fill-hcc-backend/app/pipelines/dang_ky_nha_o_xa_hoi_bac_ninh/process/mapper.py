"""Định tuyến dữ liệu nguồn vào hai thao tác riêng trên eForm Bắc Ninh (eForm 2836).

- purpose="registration_form" (mặc định): điền ĐƠN Mẫu 02 theo NAME element_762xx. Dùng element id vì các
  key semantic (CapNgay/Tai/CCCD) TRÙNG giữa người kê khai (mục 3) và vợ/chồng (mục 6) → khớp theo class
  sẽ dính nhầm ô đầu tiên.
- purpose="authorized_person": điền khối doiTuongKhac* của người được ủy quyền (fillAuthorizedPersonBacNinh).
"""

from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer


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


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


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
    # (element id, source field, có chuẩn hóa nơi cấp?). Khớp theo NAME element để không nhầm
    # người kê khai (mục 2-5) với vợ/chồng (mục 6) — class CapNgay/Tai/CCCD bị trùng giữa 2 khối.
    mapping: list[tuple[str, str, bool]] = [
        ("element_76240", "Don_KinhGui", False),
        ("element_76241", "NguoiKeKhai_HoTen", False),
        ("element_76242", "NguoiKeKhai_SoCCCD", False),
        ("element_76243", "NguoiKeKhai_NgayCap", False),
        ("element_76244", "NguoiKeKhai_NoiCap", True),
        ("element_76245", "NguoiKeKhai_NoiOHienTai", False),
        ("element_76246", "NguoiKeKhai_DangKyThuongTru", False),
        ("element_76247", "VoChong_HoTen", False),
        ("element_76248", "VoChong_SoCCCD", False),
        ("element_76249", "VoChong_NgayCap", False),
        ("element_76250", "VoChong_NoiCap", True),
        ("element_76251", "DangKyKetHon_So", False),
        ("element_76252", "DoiTuong", False),
        ("element_76255", "TinhDuAn", False),
        ("element_76259", "Don_NoiKhai", False),
        ("element_76260", "Don_NgayKhai", False),
    ]
    out: list[dict] = []
    for target, source, is_issuer in mapping:
        value = _issuer(values.get(source)) if is_issuer else _text(values.get(source))
        if value:
            out.append({"name": target, "comp": "bn-input", "value": value})
    warnings = [] if out else ["Không bóc tách được dữ liệu của Giấy xác nhận điều kiện nhà ở (Mẫu 02)."]
    return out, warnings


def _authorized_fields(values: dict[str, Any]) -> tuple[list[dict], list[str]]:
    if not _truthy(values.get("UyQuyen_CoVanBan")):
        return [], ["Không tìm thấy Văn bản ủy quyền trong hồ sơ."]

    out: list[dict] = []

    def add(name: str, value: Any, comp: str = "bn-input") -> None:
        value = _text(value)
        if value:
            out.append({"name": name, "comp": comp, "value": value})

    add("doiTuongKhachoTen", values.get("NguoiDuocUyQuyen_HoTen"))
    add("doiTuongKhacgioiTinhId", values.get("NguoiDuocUyQuyen_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", values.get("NguoiDuocUyQuyen_SoDinhDanh"))
    add("doiTuongKhacngayCap", values.get("NguoiDuocUyQuyen_NgayCap"))
    add("doiTuongKhacnoiCap", _issuer(values.get("NguoiDuocUyQuyen_NoiCap")))
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
        return [], ["Văn bản ủy quyền chưa cho biết đủ họ tên và CCCD của người được ủy quyền."]
    return out, []
