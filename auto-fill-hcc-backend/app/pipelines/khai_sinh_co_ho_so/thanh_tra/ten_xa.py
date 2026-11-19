"""Tên XÃ / PHƯỜNG của các địa chỉ đăng ký khai sinh mà ô xã trên cổng sẽ TRỐNG — khung chung ở
_shared/thanh_tra/ten_xa.py; ở đây chỉ khai các ô địa chỉ của thủ tục và cách mapper của thủ tục chuẩn hoá địa chỉ."""

from app.pipelines._shared.hospital_lookup import hospital_area
from app.pipelines._shared.thanh_tra import ten_xa as base
from app.pipelines._shared.thanh_tra.ten_xa import Slot

from ..process import mapper

TITLE = "đăng ký khai sinh"
SLOTS = {
    "Requester_ResidenceDomestic": Slot(base.RESIDENCE_RE, "Nơi cư trú của NGƯỜI YÊU CẦU"),
    "Mother_ResidenceDomestic": Slot(base.RESIDENCE_RE, "Nơi cư trú của MẸ"),
    "Father_ResidenceDomestic": Slot(base.RESIDENCE_RE, "Nơi cư trú của CHA"),
    "Subject_BirthPlaceDomestic": Slot(base.BIRTH_PLACE_RE, "NƠI SINH của người được đăng ký khai sinh"),
    "Subject_HometownDomestic": Slot(base.HOMETOWN_RE, "QUÊ QUÁN của người được đăng ký khai sinh"),
}


def mapped(name: str, value: dict):
    return mapper._normalize_domestic_area(hospital_area(value) if name == "Subject_BirthPlaceDomestic" else value)


def blank_ward(name: str, value):
    return base.blank_ward(value, mapped(name, value) if isinstance(value, dict) else None)


def rule_ward(name: str, value: dict, province: str, wards: tuple[str, ...], documents: list[dict]) -> tuple[str, str]:
    return base.rule_ward(SLOTS[name], value, province, wards, documents)


async def fixes(values: dict, names: tuple[str, ...], documents: list[dict], options: dict) -> dict[str, dict]:
    return await base.fixes(values, {name: SLOTS[name] for name in names}, documents, options, title=TITLE,
                            mapped=mapped)
