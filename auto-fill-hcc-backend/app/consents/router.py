"""Tra cứu nhật ký chấp thuận PDPL của Handfree (chỉ admin).

Module được giữ riêng với ``app.consent``: số ít là API ghi nhận của Auto Fill, số nhiều
là API quản trị dùng chung để xem log/PDF do channel Handfree sinh ra.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings
from app.core.deps import require_admin
from app.db.mongo import get_db

router = APIRouter(prefix="/api/v1/consents", tags=["consents"])

_LOG_ID = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


def _iso(value) -> str | None:
    """ISO có KÈM offset UTC — Mongo trả datetime NAIVE (driver không bật tz_aware) nên thiếu
    offset là trình duyệt hiểu thành giờ địa phương và hiện lệch 7 tiếng."""
    if not isinstance(value, datetime):
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


@router.get("")
async def list_consents(
    _admin: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    accepted: str = Query("", description="'true'/'false'; rỗng là tất cả"),
):
    query: dict = {}
    if accepted in ("true", "false"):
        query["accepted"] = accepted == "true"
    collection = get_db().consent_logs
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort("at", -1)
        .skip((page - 1) * pageSize)
        .limit(pageSize)
    )
    items = []
    async for document in cursor:
        items.append({
            "id": document["_id"],
            "at": _iso(document.get("at")),
            "at_display": document.get("at_display", ""),
            "procedure_key": document.get("procedure_key", ""),
            "procedure_label": document.get("procedure_label", ""),
            "accepted": bool(document.get("accepted")),
            "method": document.get("method", ""),
            "version": document.get("version", ""),
            "location": document.get("location") or {},
            "auth_username": document.get("auth_username", ""),
            "principal_cccd": document.get("principal_cccd"),
            "principal_name": document.get("principal_name"),
            "conversation_id": document.get("conversation_id", ""),
            "has_pdf": bool(document.get("pdf_path")),
        })
    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.get("/{log_id}/pdf")
async def download_consent_pdf(
    log_id: str,
    _admin: dict = Depends(require_admin),
):
    if not _LOG_ID.match(log_id):
        raise HTTPException(status_code=404, detail="Mã nhật ký không hợp lệ.")
    path = Path(settings.storage_dir) / "consent" / f"{log_id}.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Không có PDF cho mã nhật ký này.")
    return FileResponse(path, media_type="application/pdf", filename=f"{log_id}.pdf")
