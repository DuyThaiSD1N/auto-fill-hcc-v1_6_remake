"""Luật cấp cơ quan tiếp nhận (Sở hay UBND xã) và API link kê khai trải sẵn nhánh cho Auto Fill bản cũ."""
import asyncio

import pytest

from app.procedures import router as procedures_router
from app.procedures.agency_level import agency_level, with_agency_level

KEY = "cap-gcn-attp-co-so-kinh-doanh-dich-vu-an-uong-byt"


@pytest.mark.parametrize(("role", "ward", "level"), [
    ("province", "Xã A", "so"),
    ("province", "", "so"),
    ("commune", "Xã A", "xa"),
    ("commune", "", "so"),
    ("user", "Xã A", "xa"),
    ("user", "", "so"),
    ("", "  ", "so"),
])
def test_luat_cap_co_quan(role, ward, level):
    assert agency_level(role, ward) == level


def test_thu_tuc_khong_khai_cap_giu_nguyen():
    item = {"key": "x", "selectSo": True}
    assert with_agency_level(item, "commune", "Xã A") is item


def _link(user):
    links = asyncio.run(procedures_router.ke_khai_links(user))["links"]
    return next(link for link in links if link["key"] == KEY)


@pytest.mark.parametrize(("user", "select_so", "card"), [
    (None, True, "Cơ quan thực hiện: Sở Y tế"),
    ({"role": "province", "tinh": "Tỉnh Lai Châu", "xa": ""}, True, "Cơ quan thực hiện: Sở Y tế"),
    ({"role": "commune", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong"}, False, "Cơ quan thực hiện: UBND"),
    ({"role": "user", "tinh": "", "xa": ""}, True, "Cơ quan thực hiện: Sở Y tế"),
])
def test_api_trai_nhanh_theo_tai_khoan_cho_extension_cu(user, select_so, card):
    link = _link(user)
    assert link["selectSo"] is select_so
    assert link["submitCardIncludes"] == card
    # Bản mới vẫn nhận đủ hai nhánh để chọn lại theo xã chọn tay trên popup.
    assert set(link["agencyLevelByAccount"]) == {"xa", "so"}
