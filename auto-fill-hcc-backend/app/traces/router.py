"""API trace: danh sách + chi tiết các lần gọi /process (tài khoản, thủ tục, OCR text, JSON LLM).

Toàn bộ gác require_trace_reader: chỉ admin của TRANG QUẢN LÝ cũ và super_admin của Monitor
được đọc. Tài khoản phường đăng nhập qua extension không thể gọi thẳng API lấy PII toàn hệ thống.
"""
import asyncio
import io
import os
import zipfile
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.core.deps import require_trace_reader
from app.core.errors import AppError
from app.process import requests_repo
from app.stats import cutover
from app.traces import repo
from app.traces.date_range import parse_stats_range

router = APIRouter(prefix="/api/v1/traces", tags=["traces"])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise AppError("BAD_DATE", f"Thời gian không hợp lệ: {value}", 400) from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# Giữ tên cũ để caller/test hiện có không vỡ khi parser được dùng chung cho module báo cáo.
_parse_stats_range = parse_stats_range


@router.get("")
async def list_traces(
    _: dict = Depends(require_trace_reader),
    userId: str | None = Query(None),
    procedure: str | None = Query(None),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    requestId: str | None = Query(None),  # "mã hỗ trợ" cán bộ copy từ extension
    source: Literal["all", "autofill", "handfree"] = Query("all"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    res = await repo.list_traces(
        user_id=userId,
        procedure=procedure,
        date_from=_parse_dt(dateFrom),
        date_to=_parse_dt(dateTo),
        request_id=requestId,
        experience=None if source == "all" else source,
        skip=(page - 1) * pageSize,
        limit=pageSize,
    )
    return {**res, "page": page, "pageSize": pageSize}


@router.get("/facets")
async def facets(
    _: dict = Depends(require_trace_reader),
    source: Literal["all", "autofill", "handfree"] = Query("all"),
):
    return await repo.facets(experience=None if source == "all" else source)


@router.get("/stats")
async def stats(
    _: dict = Depends(require_trace_reader),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    scope: Literal["all", "official"] = Query("all"),
    source: Literal["all", "autofill", "handfree"] = Query("all"),
):
    start, end = _parse_stats_range(dateFrom, dateTo)
    # Qua app/stats/cutover.py: đến hết 14/9/2026 đếm theo cách cũ (suy từ trace), từ 15/9
    # đếm hồ sơ ĐÃ NỘP — cùng con số với bảng thống kê phường và báo cáo Excel.
    result = await cutover.admin_stats(
        date_from=start,
        date_to=end,
        scope=scope,
        experience=None if source == "all" else source,
    )
    return {**result, "counting": cutover.counting_info(start, end)}


@router.get("/{trace_id}")
async def get_trace(trace_id: str, _: dict = Depends(require_trace_reader)):
    doc = await repo.get_trace(trace_id)
    if not doc:
        raise AppError("TRACE_NOT_FOUND", "Không tìm thấy trace", 404)
    return doc


@router.get("/{trace_id}/files/{index}")
async def get_trace_file(trace_id: str, index: int, _: dict = Depends(require_trace_reader)):
    """Serve nội dung 1 file đã đính kèm để xem trong drawer trace.

    File lưu trên disk lúc /process; metadata (path, type) ở process_requests.files,
    index khớp với trace.attachments (cùng dựng từ body.files theo thứ tự).
    """
    trace = await repo.get_trace(trace_id)
    if not trace:
        raise AppError("TRACE_NOT_FOUND", "Không tìm thấy trace", 404)
    req = await requests_repo.get_request_by_request_id(trace["request_id"])
    files = (req or {}).get("files") or []
    if index < 0 or index >= len(files):
        raise AppError("FILE_NOT_FOUND", "Không tìm thấy file", 404)

    meta = files[index]
    rel_path = meta.get("path")
    if not rel_path:
        raise AppError("FILE_NOT_FOUND", "File không khả dụng", 404)

    storage_root = os.path.realpath(settings.storage_dir)
    abs_path = os.path.realpath(os.path.join(storage_root, rel_path))
    # Chống path traversal: đường dẫn phải nằm trong storage_dir.
    if os.path.commonpath([storage_root, abs_path]) != storage_root or not os.path.isfile(abs_path):
        raise AppError("FILE_NOT_FOUND", "File không còn trên hệ thống", 404)

    return FileResponse(
        abs_path,
        media_type=meta.get("type") or "application/octet-stream",
        filename=meta.get("name") or os.path.basename(abs_path),
        content_disposition_type="inline",
    )


@router.get("/{trace_id}/download")
async def download_all_files(trace_id: str, _: dict = Depends(require_trace_reader)):
    """Gom TẤT CẢ tài liệu của trace thành 1 file ZIP để tải một lần.

    Cùng nguồn file với /files/{index} (process_requests.files). Nén ở thread riêng để không
    chặn event loop. Tên file trong zip trùng nhau được thêm hậu tố _1, _2… cho khỏi đè.
    """
    trace = await repo.get_trace(trace_id)
    if not trace:
        raise AppError("TRACE_NOT_FOUND", "Không tìm thấy trace", 404)
    req = await requests_repo.get_request_by_request_id(trace["request_id"])
    files = (req or {}).get("files") or []
    if not files:
        raise AppError("FILE_NOT_FOUND", "Trace không có tài liệu để tải", 404)

    storage_root = os.path.realpath(settings.storage_dir)

    def _build_zip() -> bytes:
        buf = io.BytesIO()
        used: dict[str, int] = {}
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for meta in files:
                rel_path = meta.get("path")
                if not rel_path:
                    continue
                abs_path = os.path.realpath(os.path.join(storage_root, rel_path))
                # Chống path traversal: chỉ lấy file nằm trong storage_dir.
                if os.path.commonpath([storage_root, abs_path]) != storage_root or not os.path.isfile(abs_path):
                    continue
                name = meta.get("name") or os.path.basename(abs_path)
                if name in used:
                    used[name] += 1
                    stem, dot, ext = name.rpartition(".")
                    name = f"{stem}_{used[name]}.{ext}" if dot else f"{name}_{used[name]}"
                else:
                    used[name] = 0
                zf.write(abs_path, arcname=name)
        return buf.getvalue()

    data = await asyncio.to_thread(_build_zip)
    if not data:
        raise AppError("FILE_NOT_FOUND", "Không có tài liệu khả dụng để tải", 404)

    fname = f"{trace.get('procedure') or 'ho-so'}_{trace['request_id']}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
