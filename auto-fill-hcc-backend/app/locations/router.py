"""API danh mục địa giới cho combobox tỉnh/xã trên trang quản trị."""
from fastapi import APIRouter, HTTPException

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG, portal_agency_wards_by_slug

router = APIRouter(prefix="/api/v1", tags=["locations"])


@router.get("/provinces")
async def list_provinces():
    return {"provinces": PROVINCES}


# Toàn bộ danh mục trong MỘT lần gọi — extension dựng sẵn bảng tra tỉnh + xã trong bộ nhớ (trước
# đây đọc từ data/vn_provinces_wards.json đóng gói kèm extension). Gọi /wards từng tỉnh sẽ phải 34
# request mới đủ bảng, nên tách endpoint riêng thay vì bắt client lặp.
#
# Extension chỉ dùng tên xã ở đây để chọn cơ quan trên cổng (khối "Chọn cơ quan thực hiện") nên
# trả đúng chuỗi cổng đang liệt kê; /wards giữ tên hiện hành cho trang quản trị lưu tài khoản.
_PORTAL_WARDS_BY_SLUG = portal_agency_wards_by_slug()


@router.get("/locations/catalog")
async def locations_catalog():
    return {"provinces": PROVINCES, "wardsBySlug": _PORTAL_WARDS_BY_SLUG}


@router.get("/wards")
async def get_wards(slug: str = ""):
    data = WARDS_BY_SLUG.get(slug.strip())
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Không có dữ liệu xã/phường cho tỉnh '{slug}'.",
        )
    return data
