"""Ghi audit log mỗi request /process. KHÔNG log nội dung extracted (PII)."""
from datetime import datetime, timezone

from app.db.mongo import get_db


async def log_request(
    *,
    user_id: str,
    request_id: str,
    procedure: str,
    files_count: int,
    total_bytes: int,
    status: int,
    stats: dict | None = None,
    error_code: str | None = None,
) -> None:
    stats = stats or {}
    try:
        await get_db().audit_logs.insert_one({
            "user_id": user_id,
            "request_id": request_id,
            "endpoint": "/api/v1/process",
            "procedure": procedure,
            "files_count": files_count,
            "total_bytes": total_bytes,
            "status": status,
            "ocr_latency_ms": stats.get("ocr_latency_ms"),
            "llm_latency_ms": stats.get("llm_latency_ms"),
            "total_latency_ms": stats.get("total_latency_ms"),
            "error_code": error_code,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:  # noqa: BLE001 — audit không được phép làm hỏng request
        pass
