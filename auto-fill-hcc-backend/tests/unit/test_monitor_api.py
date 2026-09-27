"""API đọc của web Monitor: chỉ super_admin; pipeline gộp traces + trace_steps(steps_only)."""
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.monitor import queries
from app.monitor import router as monitor_router


def test_pipeline_loc_truoc_roi_gop_hai_nguon():
    start = datetime(2026, 9, 20, tzinfo=timezone.utc)
    end = datetime(2026, 9, 27, tzinfo=timezone.utc)
    p = queries.runs_list_pipeline(user_id="u1", procedure="khai-sinh", date_from=start, date_to=end,
                                   q="req_(1", kind="classify", outcome="issues", min_wait_ms=5000,
                                   sort="slow", skip=50, limit=50)
    first = p[0]["$match"]
    assert first == {"created_at": {"$gte": start, "$lt": end}, "user_id": "u1", "procedure": "khai-sinh"}
    union = p[2]["$unionWith"]
    assert union["coll"] == "trace_steps"
    assert union["pipeline"][0]["$match"] == {
        "steps_only": True, "created_at": {"$gte": start, "$lt": end},
        "meta.user_id": "u1", "meta.procedure": "khai-sinh"}
    post = p[3]["$match"]
    assert post["kind"] == "classify"
    assert post["outcome"] == {"$in": ["partial", "error"]}
    assert post["wait_ms"] == {"$gte": 5000}
    assert post["$or"][0]["request_id"]["$regex"] == r"req_\(1"   # ký tự đặc biệt đã escape
    items = p[4]["$facet"]["items"]
    assert items[0] == {"$sort": {"wait_ms": -1, "created_at": -1}}
    assert items[1] == {"$skip": 50} and items[2] == {"$limit": 50}


def test_pipeline_thong_ke_trung_binh_cuc_tri_va_moc_thoi_gian():
    p = queries.latency_group_pipeline(group="day")
    # Sắp theo chỉ số TRƯỚC khi gom → $first/$last là lượt nhanh nhất/lâu nhất.
    sort_idx = next(i for i, s in enumerate(p) if s.get("$sort") == {"timing.wait": 1})
    group_idx = next(i for i, s in enumerate(p) if "$group" in s)
    assert sort_idx < group_idx
    group = p[group_idx]["$group"]
    assert group["_id"]["$dateToString"]["timezone"] == "+07:00"
    assert group["avg"] == {"$avg": "$timing.wait"}
    assert group["fastest"]["$first"]["value"] == "$timing.wait"
    assert "$percentile" not in str(p)
    assert group["b3"]["$sum"]["$cond"][0]["$and"] == [{"$gte": ["$timing.wait", 20000]}]
    assert group["b0"]["$sum"]["$cond"][0]["$and"] == [{"$lt": ["$timing.wait", 5000]}]


def test_chi_so_ocr_chi_tinh_luot_ocr_that_va_moc_rieng():
    p = queries.latency_group_pipeline(group="procedure", metric="ocr")
    match = next(s["$match"] for s in p if "$match" in s and "timing.wait" in s["$match"])
    assert match["timing.n.ocr_miss"] == {"$gt": 0}
    assert {"$sort": {"timing.g.ocr": 1}} in p
    group = next(s["$group"] for s in p if "$group" in s)
    assert group["avg"] == {"$avg": "$timing.g.ocr"}
    assert group["b3"]["$sum"]["$cond"][0]["$and"] == [{"$gte": ["$timing.g.ocr", 10000]}]


def test_loc_khoang_thoi_gian_theo_chi_so():
    stage = queries.runs_filter_stage(min_wait_ms=5000, max_wait_ms=10000)
    assert stage["$match"]["wait_ms"] == {"$gte": 5000, "$lt": 10000}
    llm = queries.runs_filter_stage(min_wait_ms=3000, metric="llm")["$match"]
    assert llm["timing.g.llm"] == {"$gte": 3000} and llm["timing.n.llm_calls"] == {"$gt": 0}
    p = queries.runs_list_pipeline(sort="slow", metric="ocr")
    assert p[-1]["$facet"]["items"][0] == {"$sort": {"timing.g.ocr": -1, "created_at": -1}}


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows

    def sort(self, *a, **k):
        return self


class _Coll:
    def __init__(self, agg=None, one=None, many=None):
        self.agg, self.one, self.many = agg or [], one, many or []
        self.pipelines = []

    def aggregate(self, pipeline, **kw):
        self.pipelines.append(pipeline)
        return _Cursor(self.agg)

    async def find_one(self, *a, **k):
        return self.one

    def find(self, *a, **k):
        return _Cursor(self.many)


class _DB:
    def __init__(self, **colls):
        for k, v in colls.items():
            setattr(self, k, v)


def _client(role):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(monitor_router.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "x", "username": "x", "role": role}
    return TestClient(app)


@pytest.mark.parametrize("role", ["admin", "user", "province_admin"])
def test_chi_super_admin_duoc_vao(role):
    assert _client(role).get("/api/v1/monitor/runs").status_code == 403


def test_runs_tra_items_va_total(monkeypatch):
    created = datetime(2026, 9, 26, 2, 0)
    db = _DB(traces=_Coll(agg=[{"items": [{"request_id": "req_1", "created_at": created}],
                                "total": [{"n": 7}]}]))
    monkeypatch.setattr(monitor_router, "get_db", lambda: db)
    r = _client("super_admin").get("/api/v1/monitor/runs?dateFrom=2026-09-20&dateTo=2026-09-26&sort=slow")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 7 and body["items"][0]["created_at"] == "2026-09-26T02:00:00+00:00"


def test_run_khong_co_trace_van_mo_duoc_tu_trace_steps(monkeypatch):
    async def no_trace(request_id, kind=None):
        return None

    db = _DB(trace_steps=_Coll(one={"_id": "req_9:classify", "kind": "classify", "spans": []}))
    monkeypatch.setattr(monitor_router, "get_db", lambda: db)
    monkeypatch.setattr(monitor_router.traces_repo, "get_trace_by_request", no_trace)
    r = _client("super_admin").get("/api/v1/monitor/runs/req_9?kind=classify")
    assert r.status_code == 200
    assert r.json()["trace"] is None and r.json()["steps"]["id"] == "req_9:classify"


def test_run_khong_ton_tai_404(monkeypatch):
    async def no_trace(request_id, kind=None):
        return None

    monkeypatch.setattr(monitor_router, "get_db", lambda: _DB(trace_steps=_Coll(one=None)))
    monkeypatch.setattr(monitor_router.traces_repo, "get_trace_by_request", no_trace)
    assert _client("super_admin").get("/api/v1/monitor/runs/req_x").status_code == 404


def test_latency_tra_trung_binh_cuc_tri_va_moc(monkeypatch):
    db = _DB(traces=_Coll(agg=[{
        "_id": "2026-09-26", "n": 3, "avg": 7321.6, "llm": 4800.2, "errors": 1,
        "fastest": {"request_id": "req_a", "kind": "attach", "value": 1200},
        "slowest": {"request_id": "req_z", "kind": "autofill", "value": 72000},
        "b0": 1, "b1": 1, "b2": 0, "b3": 1,
    }]))
    monkeypatch.setattr(monitor_router, "get_db", lambda: db)
    body = _client("super_admin").get("/api/v1/monitor/stats/latency?group=day&metric=llm").json()
    assert body["metric"] == "llm" and body["bounds"] == [3000, 6000, 12000]
    row = body["rows"][0]
    assert row["avg"] == 7322 and row["llmAvg"] == 4800 and row["preAvg"] is None
    assert row["fastest"] == {"requestId": "req_a", "kind": "attach", "ms": 1200}
    assert row["slowest"]["requestId"] == "req_z"
    assert row["buckets"] == [1, 1, 0, 1]
    assert row["errors"] == 1
