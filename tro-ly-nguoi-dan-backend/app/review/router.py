"""API rà soát bbox: đọc lại sources + ảnh baked đã chụp lúc process (theo request_id).

Public theo request_id ngẫu nhiên (ảnh nạp bằng <img src> nên không gắn được header auth).
request_id là hex ngẫu nhiên khó đoán; TODO: siết auth trước khi lên production.
"""
from fastapi import APIRouter, Response

from app.core.errors import AppError
from app.review import store

router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.get("/{request_id}/sources")
async def get_sources(request_id: str):
    data = store.load_sources(request_id)
    if data is None:
        raise AppError("REVIEW_NOT_FOUND", "Không có dữ liệu rà soát cho phiên này", 404)
    return data


@router.get("/{request_id}/image")
async def get_image(request_id: str, index: int = 0):
    img = store.load_image(request_id, index)
    if img is None:
        raise AppError("REVIEW_IMAGE_NOT_FOUND", "Không tìm thấy ảnh rà soát", 404)
    data, mime = img
    return Response(
        content=data, media_type=mime,
        headers={"Cache-Control": "private, max-age=86400"},
    )
