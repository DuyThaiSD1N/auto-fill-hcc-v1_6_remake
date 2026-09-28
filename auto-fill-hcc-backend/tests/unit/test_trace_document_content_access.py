"""Nội dung giấy tờ (text OCR, JSON LLM, kết quả điền, tệp gốc) chỉ super_admin (web Monitor) đọc được.

Admin trang quản lý vẫn đọc được thông tin lượt: thủ tục, đơn vị, thời gian, tên tệp.
"""
import pytest

from app.core.deps import require_super_admin
from app.core.errors import AppError
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
    "attachments": [{"name": "giay-to.pdf", "role": "file"}],
    "stats": {"ocr_latency_ms": 2, "llm_latency_ms": 387, "total_latency_ms": 389},
    "timing": {"wait": 389},
    "ocr_text": "noi dung giay to",
    "llm_output": {"fields": {"HoTen": "x"}},
    "report": {"filled": ["HoTen"]},
}


def _has_content(doc: dict) -> bool:
    return any(k in doc for k in ("ocr_text", "llm_output", "report"))


@pytest.mark.asyncio
async def test_admin_chi_nhan_thong_tin_luot_khong_nhan_noi_dung_giay_to(monkeypatch):
    async def fake_get(_):
        return dict(TRACE)

    monkeypatch.setattr(traces_repo, "get_trace", fake_get)
    doc = await traces_router.get_trace("t1", user=ADMIN)
    assert not _has_content(doc)
    assert doc["attachments"][0]["name"] == "giay-to.pdf"
    assert doc["timing"] == {"wait": 389} and doc["stats"]["total_latency_ms"] == 389


@pytest.mark.asyncio
async def test_super_admin_van_nhan_du_cho_monitor(monkeypatch):
    async def fake_get(_):
        return dict(TRACE)

    monkeypatch.setattr(traces_repo, "get_trace", fake_get)
    doc = await traces_router.get_trace("t1", user=MONITOR)
    assert doc["ocr_text"] and doc["llm_output"] and doc["report"]


@pytest.mark.asyncio
async def test_danh_sach_va_ho_so_cua_admin_khong_lo_ket_qua_dien(monkeypatch):
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
        user=ADMIN, userId=None, procedure=None, dateFrom=None, dateTo=None, requestId=None,
        source="all", page=1, pageSize=20,
    )
    assert not _has_content(listed["items"][0])
    detail = await dossiers_router.get_dossier("d1", user=ADMIN)
    assert not _has_content(detail["traces"][0])


@pytest.mark.asyncio
async def test_admin_bi_chan_xem_va_tai_tep_goc():
    with pytest.raises(AppError) as error:
        await require_super_admin(ADMIN)
    assert error.value.error == "FORBIDDEN"
    assert await require_super_admin(MONITOR) is MONITOR

    guarded = {
        route.path: {d.call for d in route.dependant.dependencies}
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1/traces/{trace_id}/")
    }
    assert require_super_admin in guarded["/api/v1/traces/{trace_id}/files/{index}"]
    assert require_super_admin in guarded["/api/v1/traces/{trace_id}/download"]
