"""API rà soát bbox: sources và ảnh chỉ đọc được bằng capability của request."""
from fastapi import APIRouter, Response

from app.core.errors import AppError
from app.review import store
from app.review.access import verify_review_capability

router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.get("/{request_id}/sources")
async def get_sources(request_id: str, token: str = ""):
    if not verify_review_capability(request_id, token):
        raise AppError("REVIEW_FORBIDDEN", "Token rà soát không hợp lệ", 401)
    data = store.load_sources(request_id)
    if data is None:
        raise AppError("REVIEW_NOT_FOUND", "Không có dữ liệu rà soát cho phiên này", 404)
    return data


@router.get("/{request_id}/image")
async def get_image(request_id: str, index: int = 0, token: str = ""):
    if not verify_review_capability(request_id, token):
        raise AppError("REVIEW_FORBIDDEN", "Token rà soát không hợp lệ", 401)
    img = store.load_image(request_id, index)
    if img is None:
        raise AppError("REVIEW_IMAGE_NOT_FOUND", "Không tìm thấy ảnh rà soát", 404)
    data, mime = img
    return Response(
        content=data, media_type=mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )
