"""Kênh handfree ghi timeline + output cho web Monitor: run_process / run_attach / lỗi / phân loại.

Mốc 0 của lượt chạy nền = lúc pipeline bắt đầu; ghi DB (trước khi gửi fields_ready) nằm TRONG
thời gian chờ. Trace phân loại lúc tải lên chỉ ghi trace_steps (kind=classify).
"""
import pytest

from app.channels.handfree.chat import pipeline_runner, tracing
from app.channels.handfree.documents import router as documents_router
from app.config import settings
from app.monitor import recorder as mon
from app.pipelines._shared.compact_agent import runner as agent
from app.services import ocr
from app.services.llm import client


@pytest.fixture
def env(monkeypatch):
    captured = {"scheduled": [], "traces": [], "conv": {"_id": "c-1", "form_context": {}}}

    async def fake_uncached(files, classify=False):
        return [{"name": f.get("name"), "text": "CĂN CƯỚC CÔNG DÂN", "provider": "tiengnoi"} for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return '{"fields": {"HoTen": "Nguyễn Văn A"}, "d": [{"t": "cccd", "n": "Căn cước"}]}'

    async def fake_get_session(_sid):
        return {"_id": "HS-1", "files": [{"name": "cccd.png", "type": "image/png"}]}

    async def fake_get_conv(_conv_id):
        return captured["conv"]

    async def noop(*a, **k):
        return "doc-1"

    async def fake_create_trace(**kwargs):
        captured["traces"].append(kwargs)

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(settings, "trace_detail", "full")
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    monkeypatch.setattr(pipeline_runner.up_store, "get", fake_get_session)
    monkeypatch.setattr(pipeline_runner.up_store, "file_to_data_url",
                        lambda _sid, _f: "data:image/png;base64,QUJD")
    monkeypatch.setattr(pipeline_runner.conv_store, "get", fake_get_conv)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", noop)
    monkeypatch.setattr(pipeline_runner, "broadcast", noop)
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", noop)
    monkeypatch.setattr(pipeline_runner, "get_procedure", lambda _k: {"label": "Test", "review": False})
    monkeypatch.setattr(tracing, "save_request_files", lambda *a, **k: [])
    monkeypatch.setattr(tracing.requests_repo, "create_request", noop)
    monkeypatch.setattr(tracing.requests_repo, "finish_request", noop)
    monkeypatch.setattr(tracing.traces_repo, "create_trace", fake_create_trace)
    monkeypatch.setattr(pipeline_runner.monitor_persist, "schedule",
                        lambda rec, rid: captured["scheduled"].append((rec, rid)))
    token = mon._current.set(None)
    yield captured
    mon._current.reset(token)


async def fill_pipeline(files_by_role, options):
    res = await agent.run(files_by_role, fields=[{"name": "HoTen", "comp": "x-input", "desc": "tên"}],
                          allowed={"HoTen"}, comp_by_name={"HoTen": "x-input"})
    for f in res["fields"]:
        f["value"] = f["value"].upper()
    return res


async def attach_planner(files, options, session=None):
    docs = await ocr.ocr_per_file([{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files])
    parsed = client.extract_json_block(await client.chat([{"role": "user", "content": docs[0]["text"]}]))
    return {"attachments": [{"fileIndex": 0, "fileName": files[0].name,
                             "documentName": parsed["d"][0]["n"], "componentName": "CCCD",
                             "target": "existing"}],
            "extracted": {}, "errors": []}


async def test_run_process_ghi_timeline_va_ghi_db_trong_thoi_gian_cho(env, monkeypatch):
    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _k: fill_pipeline)
    await pipeline_runner.run_process("c-1", "HS-1", "thu-tuc-test")

    rec, rid = env["scheduled"][0]
    assert rec.kind == "autofill" and rec.experience == "handfree"
    assert rid == env["conv"]["trace_request_id"]
    names = [s.name for s in rec.spans]
    for name in ("pre.load", "pre.prepare", "pipeline", "ocr.call", "llm.extract", "post.validate",
                 "post.mapper", "persist.db"):
        assert name in names, name
    assert rec.meta["conversation_id"] == "c-1" and rec.meta["upload_session_id"] == "HS-1"
    assert rec.outputs["response"]["fields"][0]["value"] == "NGUYỄN VĂN A"
    trace = env["traces"][0]
    assert trace["experience"] == "handfree" and trace["outcome"] == "ok"
    assert "persist_wait" in trace["timing"] and "llm_extract" in trace["timing"]["s"]


async def test_run_process_loi_ghi_trace_loi_co_timing(env, monkeypatch):
    async def boom(files_by_role, options):
        raise RuntimeError("pipeline chết")

    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _k: boom)
    await pipeline_runner.run_process("c-1", "HS-1", "thu-tuc-test")

    rec, rid = env["scheduled"][0]
    assert rec.outcome == "error" and "pipeline chết" in rec.errors[0]
    trace = env["traces"][0]
    assert trace["status"] == "error" and trace["outcome"] == "error"
    assert rid == trace["request_id"]


async def test_run_attach_co_post_plan_va_ocr_text_tu_dich_vu(env, monkeypatch):
    monkeypatch.setattr(pipeline_runner, "get_attach_pipeline", lambda _k: attach_planner)
    await pipeline_runner.run_attach("c-1", "HS-1", "thu-tuc-test")

    rec, _ = env["scheduled"][0]
    assert rec.kind == "attach"
    names = [s.name for s in rec.spans]
    for name in ("pre.load", "pre.prepare", "post.plan", "ocr.call", "llm.plan", "post.stt1", "persist.db"):
        assert name in names, name
    assert rec.outputs["plan"][0]["documentName"] == "Căn cước"
    assert "CĂN CƯỚC CÔNG DÂN" in env["traces"][0]["ocr_text"]


async def test_trace_phan_loai_luc_tai_len(env, monkeypatch):
    scheduled = []

    async def fake_upload(sid, files, doc_key, sess):
        # Giống classify thật: OCR lô rồi LLM từng tệp.
        async with mon.span("post.route"):
            docs = await ocr.ocr_per_file([{"name": "cccd.png", "dataUrl": "data:image/png;base64,QUJD"}])
            await client.chat([{"role": "user", "content": docs[0]["text"]}], purpose="classify")
        return {"accepted": [{"fid": "f1", "doc_key": "cccd"}], "progress": {}}

    monkeypatch.setattr(documents_router, "_upload_files", fake_upload)
    monkeypatch.setattr(documents_router.monitor_persist, "schedule",
                        lambda rec, rid: scheduled.append((rec, rid)))
    out = await documents_router.upload_files("HS-1", [object()], "", {"conversation_id": "c-1",
                                                                          "procedure_key": "x"})
    assert out["accepted"][0]["doc_key"] == "cccd"
    rec, rid = scheduled[0]
    assert rec.kind == "classify" and rec.experience == "handfree" and rid
    assert rec.meta["conversation_id"] == "c-1"
    assert [c["purpose"] for c in rec.llm_calls] == ["classify"]
    assert rec.outputs["response"]["accepted"][0]["doc_key"] == "cccd"
    assert rec.ocr_files[0]["text"] == "CĂN CƯỚC CÔNG DÂN"
