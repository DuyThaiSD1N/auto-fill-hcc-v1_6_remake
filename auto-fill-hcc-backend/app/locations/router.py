"""API danh mục địa giới cho combobox tỉnh/xã trên trang quản trị."""
from fastapi import APIRouter, HTTPException

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG

router = APIRouter(prefix="/api/v1", tags=["locations"])


@router.get("/provinces")
async def list_provinces():
    return {"provinces": PROVINCES}


@router.get("/wards")
async def get_wards(slug: str = ""):
    data = WARDS_BY_SLUG.get(slug.strip())
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Không có dữ liệu xã/phường cho tỉnh '{slug}'.",
        )
    return data
