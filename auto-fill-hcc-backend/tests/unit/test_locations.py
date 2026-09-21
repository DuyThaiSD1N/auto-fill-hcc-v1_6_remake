import pytest

from app.core.errors import AppError
from app.locations.catalog import (
    PROVINCES,
    WARDS_BY_SLUG,
    canonical_location,
    province_by_slug,
)
from app.locations.router import get_wards, list_provinces


def test_catalog_has_complete_post_merger_data():
    assert len(PROVINCES) == 34
    assert sum(len(item["communes"]) for item in WARDS_BY_SLUG.values()) == 3321


def test_bac_ninh_contains_song_lieu():
    province = province_by_slug("bacninh")
    assert province and province["text"] == "Tỉnh Bắc Ninh"
    # Nhãn hiển thị đổi riêng, "text" phải giữ nguyên để còn khớp option trên cổng DVC.
    assert province["label"] == "Thành phố Bắc Ninh"
    assert len(WARDS_BY_SLUG["bacninh"]["communes"]) == 99
    assert "Phường Song Liễu" in WARDS_BY_SLUG["bacninh"]["communes"]


def test_canonical_location_accepts_legacy_short_names():
    assert canonical_location("Bắc Ninh", "Song Liễu") == (
        "Tỉnh Bắc Ninh",
        "Phường Song Liễu",
    )


def test_canonical_location_rejects_ward_from_another_province():
    with pytest.raises(AppError) as error:
        canonical_location("Tỉnh Lai Châu", "Phường Song Liễu")
    assert error.value.error == "INVALID_LOCATION"
    assert error.value.code == 422


def test_empty_location_keeps_existing_nullable_contract():
    assert canonical_location(None, None) == (None, None)
    assert canonical_location("", "") == ("", "")


@pytest.mark.asyncio
async def test_location_endpoints_return_expected_contract():
    provinces = await list_provinces()
    wards = await get_wards("bacninh")
    assert provinces["provinces"][0].keys() == {"text", "slug", "name", "label"}
    assert wards["province"] == "Tỉnh Bắc Ninh"
    assert "Phường Song Liễu" in wards["communes"]
