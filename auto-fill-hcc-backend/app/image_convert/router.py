"""Đổi ảnh HEIC (iPhone) sang JPG cho tệp cán bộ chọn thẳng trên panel Auto Fill.

Tệp qua phiên tải ảnh (QR, handfree) đã được đổi lúc nhận; riêng tệp chọn tay ở panel nằm trong trình duyệt,
mà Chrome không giải mã được HEIC, nên panel gửi lên đây đổi rồi dùng bản JPG cho cả quét lẫn đính kèm.
"""
import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.deps import require_auth
from app.services import heic

router = APIRouter(tags=["image-convert"])


@router.post("/api/v1/files/convert-image")
async def convert_image(file: UploadFile = File(...), _user: dict = Depends(require_auth)):
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Ảnh {file.filename} vượt {settings.max_file_size_mb}MB.")
    if not heic.is_heic(data, file.filename or "", file.content_type or ""):
        raise HTTPException(status_code=400, detail="Chỉ đổi ảnh HEIC/HEIF.")
    try:
        jpeg = await run_in_threadpool(heic.to_jpeg, data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Không đọc được ảnh HEIC.") from exc
    # Trả JSON (dataUrl) chứ không trả nhị phân: client của extension đọc mọi phản hồi dạng chữ.
    return {
        "name": heic.jpeg_name(file.filename or ""),
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii"),
    }
