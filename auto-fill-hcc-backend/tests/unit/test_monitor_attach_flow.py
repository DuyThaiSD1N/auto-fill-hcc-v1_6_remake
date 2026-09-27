"""Luồng đính kèm Auto Fill (/attachments/plan, /v2 attach, /client-trace) cho web Monitor.

Planner giả KHÔNG trả ``ocr_text`` (giống ~130 planner thật) để khoá việc trace vẫn có OCR text
lấy từ dịch vụ OCR; kiểm tách tầng: output LLM parse (T3) ≠ kế hoạch sau luật (T4) ≠ JSON trả FE (T5).
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.attachments import router as attach_router
from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.main import timing_middleware
from app.monitor import persist
from app.services import ocr
from app.services.llm import client
from app.v2 import router as v2

LLM_RAW = '{"d": [{"t": "cccd", "n": "Căn cước"}]}'


async def fake_planner(files, options, session=None):
    """Giống planner thật: OCR → 1 lần gọi LLM → parse → luật hậu xử lý tự viết."""
    docs = await ocr.ocr_per_file([{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files])
    raw = await client.chat([{"role": "system", "content": "phân loại"},
                             {"role": "user", "content": docs[0]["text"]}], max_tokens=300)
    parsed = client.extract_json_block(raw)
    item = parsed["d"][0]
    return {
        "attachments": [{
            "fileIndex": 0, "fileName": files[0].name, "documentName": item["n"].upper(),
            "componentName": "Giấy tờ tuỳ thân", "target": "existing", "componentIndex": 0,
            "needsAddComponent": False, "detectedType": item["t"], "rowDocumentName": "nội bộ",
        }],
        "extracted": {"documents": [files[0].name]},
        "stats": {"ocr_latency_ms": 1, "llm_latency_ms": 1, "total_latency_ms": 2},
        "errors": [],
    }


@pytest.fixture
def env(monkeypatch):
    captured = {"traces": [], "scheduled": []}

    async def fake_uncached(files, classify=False):
        return [{"name": f.get("name"), "text": "CĂN CƯỚC CÔNG DÂN", "provider": "tiengnoi"} for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return LLM_RAW

    async def noop(*a, **k):
        return None

    async def fake_create_trace(**kwargs):
        captured["traces"].append(kwargs)

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(settings, "trace_detail", "full")
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    monkeypatch.setattr(attach_router, "get_procedure", lambda key: {
        "label": "Chứng thực test", "mode": "attach",
        "clientAttachmentCase": {"type": "single-row", "componentName": "Bản sao", "componentIndex": 0},
    })
    monkeypatch.setattr(attach_router, "get_attach_pipeline", lambda key: fake_planner)
    monkeypatch.setattr(attach_router, "save_request_files", lambda *a, **k: [])
    monkeypatch.setattr(attach_router.requests_repo, "create_request", noop)
    monkeypatch.setattr(attach_router.dossiers_repo, "upsert_started", noop)
    monkeypatch.setattr(attach_router.traces_repo, "create_trace", fake_create_trace)
    monkeypatch.setattr(attach_router.monitor_persist, "schedule",
                        lambda rec, rid: captured["scheduled"].append((rec, rid)))

    app = FastAPI()
    app.middleware("http")(timing_middleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(attach_router.router)
    app.include_router(v2.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "username": "phuong", "name": "Phường A"}
    captured["client"] = TestClient(app, raise_server_exceptions=False)
    return captured


def _body():
    return {"procedure": "chung-thuc-test", "options": {},
            "files": [{"name": "cccd.png", "type": "image/png", "role": "doc",
                       "dataUrl": "data:image/png;base64,QUJD"}]}


def test_plan_ghi_du_buoc_va_tach_tang_output(env):
    r = env["client"].post("/api/v1/attachments/plan", json=_body())
    assert r.status_code == 200
    assert "rowDocumentName" not in r.json()["attachments"][0]   # response_model lược key nội bộ

    rec, rid = env["scheduled"][0]
    assert rid == r.json()["requestId"]
    names = [s.name for s in rec.spans]
    for name in ("pre.request", "pre.prepare", "post.plan", "ocr.call", "llm.plan", "post.parse",
                 "post.stt1", "persist.files", "persist.db"):
        assert name in names, name
    call = rec.llm_calls[0]
    assert call["purpose"] == "plan" and call["system_hash"]
    assert json.loads(call["parsed_src"]) == {"d": [{"t": "cccd", "n": "Căn cước"}]}      # T3
    assert rec.outputs["plan"][0]["documentName"] == "CĂN CƯỚC"                        # T4
    t5 = persist._resolve(rec.outputs["response"])                                      # T5
    assert t5["attachments"][0]["documentName"] == "CĂN CƯỚC"
    assert "rowDocumentName" not in t5["attachments"][0]

    trace = env["traces"][0]
    # Planner không trả ocr_text → trace vẫn có OCR text lấy từ dịch vụ OCR.
    assert "CĂN CƯỚC CÔNG DÂN" in trace["ocr_text"]
    assert trace["status"] == "done" and trace["outcome"] == "ok"
    assert trace["llm_output"]["attachments"][0]["documentName"] == "CĂN CƯỚC"  # giữ nguyên như cũ
    timing = trace["timing"]
    assert "post_plan" in timing["s"] and "llm_plan" in timing["s"]
    assert "persist_wait" in timing


def test_response_khong_doi_khi_tat_bo_ghi(env, monkeypatch):
    on = env["client"].post("/api/v1/attachments/plan", json=_body()).json()
    monkeypatch.setattr(settings, "trace_detail", "off")
    off = env["client"].post("/api/v1/attachments/plan", json=_body()).json()
    on.pop("requestId"), off.pop("requestId")
    assert on == off
    assert env["traces"][1]["ocr_text"] == ""   # tắt bộ ghi → như cũ (planner không trả ocr_text)


def test_planner_loi_khong_ghi_traces_chi_trace_steps(env, monkeypatch):
    async def boom(files, options, session=None):
        raise RuntimeError("planner hỏng")

    monkeypatch.setattr(attach_router, "get_attach_pipeline", lambda key: boom)
    r = env["client"].post("/api/v1/attachments/plan", json=_body())
    assert r.status_code == 500
    assert env["traces"] == []
    rec, _ = env["scheduled"][0]
    assert rec.outcome == "error" and "planner hỏng" in rec.errors[0]


def test_v2_attach_dung_chung_recorder(env):
    r = env["client"].post("/api/v2/process", data={
        "action": "attach", "procedure": "chung-thuc-test", "options": "{}",
        "fileMetadata": json.dumps([{"name": "cccd.png", "type": "image/png", "role": "doc"}]),
    }, files=[("files", ("cccd.png", b"ABC", "image/png"))])
    assert r.status_code == 200
    rec, _ = env["scheduled"][0]
    names = [s.name for s in rec.spans]
    assert names.count("pre.request") == 1 and "pre.receive" in names and "post.response" in names
    assert rec.outputs["response"]["attachments"][0]["documentName"] == "CĂN CƯỚC"


def test_client_trace_co_timing_va_co_client_attach(env):
    r = env["client"].post("/api/v1/attachments/client-trace", json={
        "procedure": "ctv", "options": {},
        "files": [{"name": "a.pdf", "type": "application/pdf", "size": 10}],
        "attachments": [{"fileIndex": 0, "fileName": "a.pdf", "documentName": "A",
                         "componentName": "Bản sao", "target": "existing",
                         "componentIndex": 0, "needsAddComponent": False}],
    })
    assert r.status_code == 200
    rec, _ = env["scheduled"][0]
    assert rec.flags.get("client_attach") is True
    trace = env["traces"][0]
    assert trace["timing"]["f"]["client_attach"] is True and trace["outcome"] == "ok"
