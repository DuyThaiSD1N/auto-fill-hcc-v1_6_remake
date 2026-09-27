"""API đọc cho web Monitor (`monitor-fe`) — CHỈ super_admin.

Không thay API cũ (`/api/v1/traces`, `/api/v1/dossiers` của web quản lý): Monitor cần gộp thêm
các lượt chỉ có ở ``trace_steps`` và dữ liệu thời gian từng công đoạn, nên có cửa riêng.
Ngày lọc theo giờ VN (``parse_stats_range``), giống các báo cáo khác.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_auth
from app.core.errors import AppError
from app.db.mongo import get_db
from app.dossiers import repo as dossiers_repo
from app.monitor import queries
from app.traces import repo as traces_repo
from app.traces.date_range import parse_stats_range
from app.users.roles import SUPER_ADMIN_ROLE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])

Source = Literal["all", "autofill", "handfree"]
Kind = Literal["all", "autofill", "attach", "classify", "owner_info"]
Outcome = Literal["all", "ok", "partial", "error", "issues"]


async def require_super_admin(user: dict = Depends(require_auth)) -> dict:
    """Monitor chứa OCR/output LLM/ảnh giấy tờ của mọi đơn vị → chỉ role nội bộ super_admin."""
    if (user.get("role") or "user") != SUPER_ADMIN_ROLE:
        raise AppError("FORBIDDEN", "Chỉ tài khoản Monitor được xem dữ liệu này", 403)
    return user


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        # Motor trả datetime NAIVE nhưng giá trị là UTC (mọi chỗ ghi dùng timezone.utc).
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
    return value


def _clean(doc: Any) -> Any:
    """ObjectId/datetime → chuỗi, đệ quy (document trace_steps lồng nhiều tầng)."""
    if isinstance(doc, dict):
        return {("id" if k == "_id" else k): _clean(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [_clean(v) for v in doc]
    if isinstance(doc, datetime):
        return _iso(doc)
    if doc.__class__.__name__ == "ObjectId":
        return str(doc)
    return doc


Metric = Literal["wait", "ocr", "llm"]


def _filters(q, userId, procedure, source, kind, outcome, dateFrom, dateTo, minWaitMs,
             maxWaitMs=None, metric="wait") -> dict:
    date_from, date_to = parse_stats_range(dateFrom, dateTo)
    return {
        "q": q, "user_id": userId, "procedure": procedure, "source": source, "kind": kind,
        "outcome": outcome, "date_from": date_from, "date_to": date_to, "min_wait_ms": minWaitMs,
        "max_wait_ms": maxWaitMs, "metric": metric,
    }


@router.get("/facets")
async def facets(_: dict = Depends(require_super_admin)):
    return await traces_repo.facets()


@router.get("/runs")
async def list_runs(
    _: dict = Depends(require_super_admin),
    q: str | None = Query(None, max_length=200),
    userId: str | None = Query(None),
    procedure: str | None = Query(None),
    source: Source = Query("all"),
    kind: Kind = Query("all"),
    outcome: Outcome = Query("all"),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    minWaitMs: int | None = Query(None, ge=0),
    maxWaitMs: int | None = Query(None, ge=0),
    metric: Metric = Query("wait"),
    sort: Literal["new", "slow"] = Query("new"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
):
    pipeline = queries.runs_list_pipeline(
        sort=sort, skip=(page - 1) * pageSize, limit=pageSize,
        **_filters(q, userId, procedure, source, kind, outcome, dateFrom, dateTo, minWaitMs, maxWaitMs, metric),
    )
    rows = await get_db().traces.aggregate(pipeline, allowDiskUse=True).to_list(length=1)
    facet = rows[0] if rows else {"items": [], "total": []}
    total = facet["total"][0]["n"] if facet.get("total") else 0
    return {"items": _clean(facet.get("items") or []), "total": total, "page": page, "pageSize": pageSize}


@router.get("/runs/{request_id}")
async def get_run(
    request_id: str,
    _: dict = Depends(require_super_admin),
    kind: str | None = Query(None),
):
    """Một lượt: trace (nếu có) + chi tiết công đoạn/output (nếu lượt được ghi sau khi bật bộ ghi)."""
    trace = await traces_repo.get_trace_by_request(request_id, kind)
    step_kind = kind or (trace or {}).get("kind")
    steps_query: dict = {"_id": f"{request_id}:{step_kind}"} if step_kind else {"request_id": request_id}
    steps = await get_db().trace_steps.find_one(steps_query)
    if not trace and not steps:
        raise AppError("RUN_NOT_FOUND", "Không tìm thấy lượt xử lý", 404)
    return {"trace": _clean(trace), "steps": _clean(steps)}


@router.get("/ocr/{sha}")
async def get_ocr_text(sha: str, _: dict = Depends(require_super_admin)):
    doc = await get_db().ocr_texts.find_one({"_id": sha})
    if not doc:
        raise AppError("OCR_TEXT_NOT_FOUND", "Không còn text OCR của tệp này", 404)
    return _clean(doc)


@router.get("/dossiers")
async def list_dossiers(
    _: dict = Depends(require_super_admin),
    q: str | None = Query(None, max_length=200),
    userId: str | None = Query(None),
    procedure: str | None = Query(None),
    source: Source = Query("all"),
    status: Literal["all", "submitted", "unsubmitted"] = Query("all"),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100),
):
    date_from, date_to = parse_stats_range(dateFrom, dateTo)
    res = await dossiers_repo.search_dossiers(
        q=q, user_id=userId, procedure=procedure,
        experience=None if source == "all" else source,
        submitted=None if status == "all" else status == "submitted",
        date_from=date_from, date_to=date_to,
        skip=(page - 1) * pageSize, limit=pageSize,
    )
    ids = [item["id"] for item in res["items"] if item.get("id")]
    counts = await _run_counts(ids)
    for item in res["items"]:
        item["runs"] = counts.get(item.get("id"), 0)
    return {**res, "page": page, "pageSize": pageSize}


async def _run_counts(dossier_ids: list[str]) -> dict[str, int]:
    if not dossier_ids:
        return {}
    db = get_db()
    counts: dict[str, int] = {}
    for coll, field, extra in (
        (db.traces, "dossier_id", {}),
        (db.trace_steps, "meta.dossier_id", {"steps_only": True}),
    ):
        rows = await coll.aggregate([
            {"$match": {field: {"$in": dossier_ids}, **extra}},
            {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
        ]).to_list(length=len(dossier_ids))
        for row in rows:
            counts[row["_id"]] = counts.get(row["_id"], 0) + int(row["n"])
    return counts


@router.get("/dossiers/{dossier_id}")
async def get_dossier(dossier_id: str, _: dict = Depends(require_super_admin)):
    """Hồ sơ + mọi lượt của nó (traces + lượt chỉ có ở trace_steps), xếp theo thời gian."""
    dossier = await dossiers_repo.get_dossier(dossier_id)
    traces = await traces_repo.list_by_dossier(dossier_id)
    if not dossier and not traces:
        raise AppError("DOSSIER_NOT_FOUND", "Không tìm thấy hồ sơ", 404)
    steps_only = await get_db().trace_steps.find(
        {"meta.dossier_id": dossier_id, "steps_only": True},
        {"request_id": 1, "kind": 1, "experience": 1, "outcome": 1, "created_at": 1,
         "timing": 1, "errors": 1, "meta": 1},
    ).sort("created_at", 1).to_list(length=200)
    return {"dossier": dossier, "traces": _clean(traces), "stepsOnly": _clean(steps_only)}


@router.get("/stats/latency")
async def latency_stats(
    _: dict = Depends(require_super_admin),
    group: Literal["day", "procedure", "unit", "all"] = Query("day"),
    metric: Metric = Query("wait"),
    q: str | None = Query(None, max_length=200),
    userId: str | None = Query(None),
    procedure: str | None = Query(None),
    source: Source = Query("all"),
    kind: Kind = Query("all"),
    outcome: Outcome = Query("all"),
    dateFrom: str | None = Query(None),
    dateTo: str | None = Query(None),
):
    filters = _filters(q, userId, procedure, source, kind, outcome, dateFrom, dateTo, None)
    filters.pop("metric")
    rows = await get_db().traces.aggregate(
        queries.latency_group_pipeline(group=group, metric=metric, **filters), allowDiskUse=True,
    ).to_list(length=500)
    return {
        "group": group, "metric": metric,
        # Mốc phân bố (ms) của chỉ số → FE ghi nhãn "dưới 2 giây"… đúng với chỉ số đang xem.
        "bounds": list(queries.METRICS[metric][2]),
        "rows": [_latency_row(r) for r in rows],
    }


def _latency_row(row: dict) -> dict:
    def num(value):
        return round(value) if isinstance(value, (int, float)) else None

    def run(ref):
        if not isinstance(ref, dict) or not ref.get("request_id"):
            return None
        return {"requestId": ref["request_id"], "kind": ref.get("kind"), "ms": num(ref.get("value"))}

    return {
        "key": row.get("_id"), "label": row.get("label"), "name": row.get("name"), "n": row.get("n", 0),
        "avg": num(row.get("avg")),
        "fastest": run(row.get("fastest")), "slowest": run(row.get("slowest")),
        "preAvg": num(row.get("pre")), "ocrAvg": num(row.get("ocr")), "llmAvg": num(row.get("llm")),
        "postAvg": num(row.get("post")), "otherAvg": num(row.get("other")),
        "persistWaitAvg": num(row.get("persist_wait")),
        "buckets": [row.get(f"b{i}", 0) for i in range(4)],
        "errors": row.get("errors", 0), "partial": row.get("partial", 0),
        "ocrHit": row.get("ocr_hit", 0), "ocrMiss": row.get("ocr_miss", 0),
        "llmCalls": round(row["llm_calls"], 2) if row.get("llm_calls") is not None else None,
        "tokOut": num(row.get("tok_out")),
    }

