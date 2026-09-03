"""Lưu bằng chứng chấp thuận: Mongo `consent_logs` (KHÔNG TTL — bằng chứng phải giữ lâu dài)
+ file PDF trên đĩa `{storage_dir}/consent/<log_id>.pdf`.

PDF do BE tự sinh (app/consent/pdf.py) từ metadata → không nhận file từ client, chống sửa.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.consent.pdf import build_consent_pdf
from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _consent_dir() -> Path:
    p = Path(settings.storage_dir) / "consent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "consent")[:60]


async def save_consent(*, log_id: str, user: dict, procedure: str | None,
                       procedure_label: str | None, version: str,
                       statements: list[str], optimize: bool, at: str | None,
                       principal_cccd: str | None = None,
                       principal_name: str | None = None) -> dict:
    created_at = _now()
    server_time = created_at.astimezone().strftime("%H:%M:%S %d/%m/%Y")
    pdf_bytes = build_consent_pdf(
        log_id=log_id, username=user.get("username"), name=user.get("name"),
        procedure_label=procedure_label, version=version, statements=statements,
        optimize=optimize, client_time=at, server_time=server_time,
        principal_cccd=principal_cccd, principal_name=principal_name,
    )
    fname = f"{_safe(log_id)}.pdf"
    (_consent_dir() / fname).write_bytes(pdf_bytes)
    doc = {
        "log_id": log_id,
        "user_id": user["id"],
        "username": user.get("username"),
        "name": user.get("name"),          # tên hiển thị theo phường
        "procedure": procedure,
        "procedure_label": procedure_label,
        "version": version,                # phiên bản nội dung chấp thuận (vd "v1.1")
        "statements": statements or [],    # các câu chấp thuận đã tick
        "optimize": bool(optimize),        # đồng ý (tùy chọn) lưu data lần xử lý để tối ưu hệ thống
        "principal_cccd": principal_cccd,  # CCCD chủ thể dữ liệu (VNeID trên cổng); None nếu cổng không lộ
        "principal_name": principal_name,  # tên chủ thể dữ liệu (đối chiếu, không dùng làm khóa)
        "pdf_path": str(Path("consent") / fname),
        "client_time": at,                 # thời điểm hiển thị phía client (chuỗi)
        "experience": "autofill",
        "created_at": created_at,
    }
    res = await get_db().consent_logs.insert_one(doc)
    return {"id": str(res.inserted_id)}
