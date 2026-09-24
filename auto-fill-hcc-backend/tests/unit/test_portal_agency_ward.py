import asyncio

from app.channels.handfree.chat import flow
from app.locations.catalog import WARDS_BY_SLUG, portal_agency_ward
from app.locations.router import get_wards, locations_catalog


def test_portal_agency_ward_uses_old_portal_name_for_hiep_hoa():
    assert portal_agency_ward("bacninh", "Phường Hiệp Hòa") == "Xã Hiệp Hòa"
    assert portal_agency_ward("Tỉnh Bắc Ninh", "Phường Hiệp Hòa") == "Xã Hiệp Hòa"
    assert portal_agency_ward("Bắc Ninh", "phuong hiep hoa") == "Xã Hiệp Hòa"


def test_portal_agency_ward_keeps_other_wards_and_provinces():
    assert portal_agency_ward("bacninh", "Phường Kinh Bắc") == "Phường Kinh Bắc"
    assert portal_agency_ward("Tỉnh Lâm Đồng", "Phường Hiệp Hòa") == "Phường Hiệp Hòa"
    assert portal_agency_ward("bacninh", "") == ""


def test_catalog_for_extension_lists_portal_name_but_wards_api_keeps_current_name():
    catalog = asyncio.run(locations_catalog())
    extension_wards = catalog["wardsBySlug"]["bacninh"]["communes"]
    assert "Xã Hiệp Hòa" in extension_wards
    assert "Phường Hiệp Hòa" not in extension_wards

    # Biểu mẫu kê khai và tài khoản vẫn dùng tên hiện hành.
    assert "Phường Hiệp Hòa" in WARDS_BY_SLUG["bacninh"]["communes"]
    assert "Phường Hiệp Hòa" in asyncio.run(get_wards("bacninh"))["communes"]


def test_handfree_agency_actions_use_portal_ward_name():
    loc = {"province": "Tỉnh Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Hiệp Hòa"}

    assert flow._portal_ward(loc) == "Xã Hiệp Hòa"
    plan = flow._resolve_agency_plan([{"field": "xa", "value": "{ward}"}], loc)
    assert plan == [{"field": "xa", "value": "Xã Hiệp Hòa"}]
