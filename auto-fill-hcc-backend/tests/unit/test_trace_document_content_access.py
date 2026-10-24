import pytest

from app.dossiers import router as dossiers_router
from app.main import app
from app.traces import repo as traces_repo
from app.traces import router as traces_router

ADMIN = {"id": "admin", "role": "admin"}
MONITOR = {"id": "monitor", "role": "super_admin"}

TRACE = {
    "id": "t1",
    "request_id": "req_x",
    "procedure": "khai-tu",
    "applicant_name": "NGUYEN VAN A",
    "attachments": [{"name": "giay-to.pdf", "role": "file", "sha256": "s1", "uses": 1, "nk": "k:x"}],
    "stats": {"ocr_latency_ms": 2, "llm_latency_ms": 387, "total_latency_ms": 389},
    "timing": {"wait": 389},
    "ocr_text": "noi dung giay to",
    "llm_output": {"fields": {"HoTen": "x"}},
    "report": {"filled": ["HoTen"]},
    "errors": ["LLM loi voi HoTen=A"],
}


def _assert_clean(doc: dict) -> None:
    for key in ("ocr_text", "llm_output", "report", "applicant_name", "errors"):
        assert key not in doc, key
    assert doc["attachments"] == [{"sha256": "s1", "uses": 1}]
    assert doc["timing"] == {"wait": 389} and doc["stats"]["total_latency_ms"] == 389


@pytest.mark.asyncio
@pytest.mark.parametrize("user", [ADMIN, MONITOR])
async def test_chi_tiet_khong_lo_noi_dung_cho_ai(monkeypatch, user):
    async def fake_get(_):
        return dict(TRACE)

    monkeypatch.setattr(traces_repo, "get_trace", fake_get)
    _assert_clean(await traces_router.get_trace("t1", user=user))


@pytest.mark.asyncio
@pytest.mark.parametrize("user", [ADMIN, MONITOR])
async def test_danh_sach_va_ho_so_khong_lo_noi_dung(monkeypatch, user):
    async def fake_list(**_):
        return {"items": [dict(TRACE)], "total": 1}

    async def fake_dossier(_):
        return {"id": "d1"}

    async def fake_by_dossier(_):
        return [dict(TRACE)]

    monkeypatch.setattr(traces_repo, "list_traces", fake_list)
    monkeypatch.setattr(dossiers_router.dossiers_repo, "get_dossier", fake_dossier)
    monkeypatch.setattr(traces_repo, "list_by_dossier", fake_by_dossier)

    listed = await traces_router.list_traces(
        user=user, userId=None, procedure=None, dateFrom=None, dateTo=None, requestId=None,
        source="all", page=1, pageSize=20,
    )
    _assert_clean(listed["items"][0])
    detail = await dossiers_router.get_dossier("d1", user=user)
    _assert_clean(detail["traces"][0])


def test_khong_con_api_xem_hay_tai_tep_goc_va_text_ocr():
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/v1/traces/{trace_id}/files/{index}" not in paths
    assert "/api/v1/traces/{trace_id}/download" not in paths
    assert "/api/v1/monitor/ocr/{sha}" not in paths


def test_serialize_cua_repo_cung_bo_noi_dung():
    doc = traces_repo._serialize({"_id": "x", **{k: v for k, v in TRACE.items() if k != "id"}})
    _assert_clean(doc)
