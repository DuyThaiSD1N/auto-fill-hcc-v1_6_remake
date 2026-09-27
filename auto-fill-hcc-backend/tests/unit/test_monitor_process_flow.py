"""Luồng điền Auto Fill (/process, /v2/process) ghi đủ timeline + output cho web Monitor.

Chạy qua runner chung thật (compact_agent) với OCR/LLM giả để kiểm: đủ bước, nhóm thời gian,
field bị validate loại, output trả FE — và response KHÔNG đổi so với khi tắt bộ ghi.
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.main import timing_middleware
from app.pipelines._shared.compact_agent import runner as agent
from app.process import router as process_router
from app.services import ocr
from app.services.llm import client
from app.v2 import router as v2

FIELDS = [
    {"name": "HoTen", "comp": "x-input", "desc": "họ tên"},
    {"name": "NgaySinh", "comp": "x-date", "desc": "ngày sinh"},
]
LLM_RAW = '```json\n{"fields": {"HoTen": "nguyễn văn a", "NgaySinh": "01/02/1990", "Bịa": "x", "NgaySinh ": ""}}\n```'


async def fake_pipeline(files_by_role, options):
    res = await agent.run(
        files_by_role, fields=FIELDS, allowed={"HoTen", "NgaySinh"},
        comp_by_name={"HoTen": "x-input", "NgaySinh": "x-date"},
    )
    for field in res["fields"]:  # "mapper" của package sửa tại chỗ
        if field["name"] == "HoTen":
            field["value"] = field["value"].upper()
    return res


@pytest.fixture
def env(monkeypatch):
    captured = {"traces": [], "scheduled": []}

    async def fake_uncached(files, classify=False):
        return [{"name": f.get("name"), "text": "Họ tên: Nguyễn Văn A", "provider": "tiengnoi"} for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return LLM_RAW

    async def noop(*args, **kwargs):
        return "doc-1"

    async def fake_create_trace(**kwargs):
        captured["traces"].append(kwargs)

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(settings, "trace_detail", "full")
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    monkeypatch.setattr(process_router, "get_procedure", lambda key: {"label": "Thủ tục test", "mode": "agent"})
    monkeypatch.setattr(process_router, "get_pipeline", lambda key: fake_pipeline)
    monkeypatch.setattr(process_router, "save_request_files", lambda *a, **k: [])
    monkeypatch.setattr(process_router.requests_repo, "create_request", noop)
    monkeypatch.setattr(process_router.requests_repo, "finish_request", noop)
    monkeypatch.setattr(process_router.audit, "log_request", noop)
    monkeypatch.setattr(process_router, "_touch_dossier", noop)
    monkeypatch.setattr(process_router.traces_repo, "create_trace", fake_create_trace)
    monkeypatch.setattr(process_router.monitor_persist, "schedule",
                        lambda rec, rid: captured["scheduled"].append((rec, rid)))

    app = FastAPI()
    app.middleware("http")(timing_middleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(process_router.router)
    app.include_router(v2.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "username": "phuong", "name": "Phường A"}
    captured["client"] = TestClient(app)
    return captured


def _body():
    return {"procedure": "thu-tuc-test", "options": {},
            "files": [{"name": "cccd.png", "type": "image/png", "role": "doc",
                       "dataUrl": "data:image/png;base64,QUJD"}]}


def test_process_ghi_du_buoc_va_output(env):
    r = env["client"].post("/api/v1/process", json=_body())
    assert r.status_code == 200
    assert [(f["name"], f["value"]) for f in r.json()["fields"]] == [
        ("HoTen", "NGUYỄN VĂN A"), ("NgaySinh", "01/02/1990")]

    rec, rid = env["scheduled"][0]
    assert rid == r.json()["requestId"]
    names = [s.name for s in rec.spans]
    for name in ("pre.request", "pre.prepare", "pipeline", "ocr.call", "ocr.remote", "llm.extract",
                 "post.parse", "post.validate", "post.mapper", "post.dates", "persist.files", "persist.db"):
        assert name in names, name
    assert rec.llm_calls[0]["purpose"] == "extract" and rec.llm_calls[0]["system_hash"]
    assert json.loads(rec.llm_calls[0]["parsed_src"])["fields"]["Bịa"] == "x"   # T3 = đúng LLM trả
    dropped = {d["name"]: d["reason"] for d in rec.outputs["validate_dropped"]}
    assert dropped == {"Bịa": "not_allowed", "NgaySinh ": "not_allowed"}
    # T4 trước mapper: tên còn thường (mapper viết hoa sau đó) — chụp chuỗi nên không bị sửa theo.
    assert json.loads(rec.outputs["fields_after_validate"])[0]["value"] == "nguyễn văn a"
    assert rec.outputs["response"]["fields"][0]["value"] == "NGUYỄN VĂN A"   # T5
    assert rec.ocr_files[0]["text"] == "Họ tên: Nguyễn Văn A"                 # T1
    assert rec.outcome == "ok"

    trace = env["traces"][0]
    assert trace["status"] == "done" and trace["outcome"] == "ok"
    timing = trace["timing"]
    assert set(timing["g"]) == {"pre", "ocr", "llm", "post"}
    assert "llm_extract" in timing["s"] and timing["n"]["llm_calls"] == 1
    assert timing["wait"] >= 0 and timing["other"] >= 0


def test_response_khong_doi_khi_tat_bo_ghi(env, monkeypatch):
    on = env["client"].post("/api/v1/process", json=_body()).json()
    monkeypatch.setattr(settings, "trace_detail", "off")
    off = env["client"].post("/api/v1/process", json=_body()).json()
    for key in ("fields", "extracted", "stats", "errors", "pages", "businessFlow"):
        assert on[key] == off[key], key


def test_ocr_loi_thi_outcome_partial_va_luu_errors(env, monkeypatch):
    async def failing_uncached(files, classify=False):
        return [{"name": "cccd.png", "text": "", "error": "OCR Tiếng Nói: timeout", "provider": "tiengnoi"}]

    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", failing_uncached)
    r = env["client"].post("/api/v1/process", json=_body())
    assert r.status_code == 200
    trace = env["traces"][0]
    assert trace["status"] == "done"            # giữ nguyên cho web quản lý cũ
    assert trace["outcome"] == "partial"
    assert any("timeout" in e for e in trace["errors"])


def test_pipeline_no_thi_khong_ghi_traces_chi_ghi_trace_steps(env, monkeypatch):
    async def boom(files_by_role, options):
        raise RuntimeError("hỏng giữa chừng")

    monkeypatch.setattr(process_router, "get_pipeline", lambda key: boom)
    r = env["client"].post("/api/v1/process", json=_body())
    assert r.status_code == 500
    assert env["traces"] == []
    rec, _ = env["scheduled"][0]
    assert rec.outcome == "error" and "hỏng giữa chừng" in rec.errors[0]


def test_v2_dung_chung_mot_recorder_co_buoc_nhan_multipart(env):
    r = env["client"].post("/api/v2/process", data={
        "action": "fill", "procedure": "thu-tuc-test", "options": "{}",
        "fileMetadata": json.dumps([{"name": "cccd.png", "type": "image/png", "role": "doc"}]),
    }, files=[("files", ("cccd.png", b"ABC", "image/png"))])
    assert r.status_code == 200
    assert len(env["scheduled"]) == 1
    rec, _ = env["scheduled"][0]
    names = [s.name for s in rec.spans]
    assert names.count("pre.request") == 1
    assert "pre.receive" in names and "post.response" in names and "llm.extract" in names
    assert rec.meta.get("api") == "v2"
