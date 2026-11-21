"""Hai chủ thể của hồ sơ kết hôn có yếu tố nước ngoài (bên nam, bên nữ). Field lượt trích của thủ tục này đặt tiền tố
Nam_ / Nu_ (giấy tờ tùy thân và giấy khác) và ToKhaiNam_ / ToKhaiNu_ (cột tờ khai). Bảng hai cột của tờ khai cùng mẫu với
kết hôn trong nước nên dùng lại cách tách cột của thanh tra kết hôn."""

import re

from app.pipelines.ket_hon.thanh_tra.chu_the import Side, cell, declaration_tables  # noqa: F401 — dùng lại

SIDES = (Side("nam", "Nam", "ToKhaiNam", "bên nam", "Nam"), Side("nu", "Nu", "ToKhaiNu", "bên nữ", "Nữ"))


def identity(values: dict, side: Side) -> dict:
    """Nhân thân đang dùng của một bên: giấy tờ tùy thân trước, cột tờ khai bù (như mapper)."""
    name = values.get(f"{side.card}_HoTen") or values.get(f"{side.declared}_HoTen")
    return {"name": " ".join(str(name or "").split()),
            "number": re.sub(r"\D+", "", str(values.get(f"{side.card}_SoDinhDanh") or "")),
            "birth": values.get(f"{side.card}_NgaySinh") or values.get(f"{side.declared}_NgaySinh")}
