"""API trace: danh sách + chi tiết các lần gọi /process (tài khoản, thủ tục, thời gian xử lý).

Gác require_trace_reader: chỉ admin của TRANG QUẢN LÝ và super_admin của Monitor được đọc. Tài khoản
phường không gọi được các API này.
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response

from app.core.deps import require_trace_reader
from app.core.errors import AppError
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
    user: dict = Depends(require_trace_reader),
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
    res = {**res, "items": [repo.without_document_content(t) for t in res["items"]]}
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
async def get_trace(trace_id: str, user: dict = Depends(require_trace_reader)):
    doc = await repo.get_trace(trace_id)
    if not doc:
        raise AppError("TRACE_NOT_FOUND", "Không tìm thấy trace", 404)
    return repo.without_document_content(doc)
