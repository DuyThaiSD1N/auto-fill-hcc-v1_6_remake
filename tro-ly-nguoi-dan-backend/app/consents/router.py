"""Tra cứu nhật ký chấp thuận PDPL (chỉ admin) — tab "Chấp thuận" trang quản trị.

GET /api/v1/consents            — danh sách phân trang (lọc theo kết quả đồng ý/từ chối)
GET /api/v1/consents/{id}/pdf   — tải PDF biên bản (app/chat/consent.py sinh lúc đồng ý,
                                  nằm {storage_dir}/consent/; lượt từ chối không có → 404)
"""
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings
from app.core.deps import require_admin
from app.db.mongo import get_db

router = APIRouter(prefix="/api/v1/consents", tags=["consents"])

# Mã nhật ký dạng TLND-XXXX — chặn ký tự lạ để không thành path traversal.
_LOG_ID = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


@router.get("")
async def list_consents(
    _admin: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    accepted: str = Query("", description="'true'/'false' — lọc kết quả; rỗng = tất cả"),
):
    q: dict = {}
    if accepted in ("true", "false"):
        q["accepted"] = accepted == "true"
    coll = get_db().consent_logs
    total = await coll.count_documents(q)
    cursor = coll.find(q).sort("at", -1).skip((page - 1) * pageSize).limit(pageSize)
    items = []
    async for d in cursor:
        # Log v1.0/1.1 (trước 2026-08-07) chưa có location/auth_username/pdf_path → default rỗng.
        items.append({
            "id": d["_id"],
            "at": d["at"].isoformat() if d.get("at") else None,
            "at_display": d.get("at_display", ""),
            "procedure_key": d.get("procedure_key", ""),
            "procedure_label": d.get("procedure_label", ""),
            "accepted": bool(d.get("accepted")),
            "method": d.get("method", ""),
            "version": d.get("version", ""),
            "location": d.get("location") or {},
            "auth_username": d.get("auth_username", ""),
            "principal_cccd": d.get("principal_cccd"),
            "principal_name": d.get("principal_name"),
            "conversation_id": d.get("conversation_id", ""),
            "has_pdf": bool(d.get("pdf_path")),
        })
    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.get("/{log_id}/pdf")
async def download_consent_pdf(log_id: str, _: dict = Depends(require_admin)):
    if not _LOG_ID.match(log_id):
        raise HTTPException(status_code=404, detail="Mã nhật ký không hợp lệ.")
    path = Path(settings.storage_dir) / "consent" / f"{log_id}.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không có PDF cho mã nhật ký này.")
    return FileResponse(path, media_type="application/pdf", filename=f"{log_id}.pdf")
