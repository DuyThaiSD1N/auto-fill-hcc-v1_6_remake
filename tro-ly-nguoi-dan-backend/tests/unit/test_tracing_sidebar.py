"""Trace kênh sidebar: người dân nặc danh → user 'citizen', name = phường/xã từ conv.location;
ảnh lưu qua save_request_files + process_requests (nguồn xem file/ZIP của trang quản lý)."""
import pytest

from app.chat import tracing


@pytest.fixture
def captured(monkeypatch, tmp_path):
    out = {"requests": [], "traces": [], "finishes": [], "reports": []}

    def fake_save_files(request_id, created_at, files):
        return [{"name": f.name, "type": f.type, "role": f.role, "size": 3, "path": "x"} for f in files]

    async def fake_create_request(**kw):
        out["requests"].append(kw)
        return "doc1"

    async def fake_finish_request(doc_id, **kw):
        out["finishes"].append((doc_id, kw))

    async def fake_create_trace(**kw):
        out["traces"].append(kw)
        return "t1"

    async def fake_set_report(request_id, kind, report):
        out["reports"].append((request_id, kind, report))

    monkeypatch.setattr(tracing, "save_request_files", fake_save_files)
    monkeypatch.setattr(tracing.requests_repo, "create_request", fake_create_request)
    monkeypatch.setattr(tracing.requests_repo, "finish_request", fake_finish_request)
    monkeypatch.setattr(tracing.traces_repo, "create_trace", fake_create_trace)
    monkeypatch.setattr(tracing.traces_repo, "set_report", fake_set_report)
    return out


_CONV = {"_id": "conv1", "upload_session_id": "HS-1",
         "location": {"ward": "Phường Song Liễu", "province": "Tỉnh Bắc Ninh"},
         "consent": {"id": "TLND-ABC", "accepted": True}}

_FILES = [{"name": "cccd.jpg", "type": "image/jpeg", "dataUrl": "data:x;base64,AAA", "role": ""}]


@pytest.mark.asyncio
async def test_record_process_ghi_du_request_va_trace(captured):
    result = {"fields": [{"name": "HoTen", "value": "A"}], "extracted": {},
              "ocr_text": "CĂN CƯỚC", "llm_output": {"fields": {}},
              "stats": {"ocr_latency_ms": 100, "llm_latency_ms": 200}}
    rid = await tracing.record_process(_CONV, "ket-hon", {"label": "Kết hôn"}, _FILES, result, 999)

    assert rid
    req = captured["requests"][0]
    assert req["user_id"] == "citizen" and req["request_id"] == rid
    assert req["options"]["channel"] == "sidebar"
    assert req["options"]["consent_id"] == "TLND-ABC"  # trace nối được về nhật ký chấp thuận
    tr = captured["traces"][0]
    assert tr["kind"] == "autofill" and tr["status"] == "done"
    assert tr["name"] == "Phường Song Liễu, Tỉnh Bắc Ninh"  # lọc/thống kê theo phường
    assert tr["username"] == "sidebar" and tr["ocr_text"] == "CĂN CƯỚC"
    assert captured["finishes"][0][1]["fields_count"] == 1


@pytest.mark.asyncio
async def test_record_attach_va_set_report(captured):
    stats = {"ocr_latency_ms": 120, "llm_latency_ms": 230, "total_latency_ms": 350}
    classification = {"0": {"detectedType": "Căn cước công dân"}}
    result = {"attachments": [{"fileName": "cccd.pdf", "componentName": "STT 2"}],
              "extracted": {}, "stats": stats, "ocr_provider": "gemini",
              "llm_output": classification}
    rid = await tracing.record_attach(_CONV, "ket-hon", {"label": "Kết hôn"}, _FILES, result)
    tr = captured["traces"][0]
    assert tr["kind"] == "attach" and tr["attachments"][0]["role"] == "STT 2"
    assert tr["stats"] == stats
    assert tr["ocr_provider"] == "gemini"
    assert tr["llm_output"]["classification"] == classification
    assert captured["finishes"][0][1]["stats"] == stats

    await tracing.set_report(rid, "attach", {"attached": 1, "errors": []})
    assert captured["reports"][0] == (rid, "attach", {"attached": 1, "errors": []})
    # request_id rỗng (trace ghi fail trước đó) → im lặng, không nổ.
    await tracing.set_report(None, "attach", {})
    assert len(captured["reports"]) == 1


@pytest.mark.asyncio
async def test_record_process_loi_khong_chan_luong(captured, monkeypatch):
    async def boom(**_kw):
        raise RuntimeError("mongo chết")

    monkeypatch.setattr(tracing.traces_repo, "create_trace", boom)
    rid = await tracing.record_process(_CONV, "ket-hon", {}, _FILES, {"fields": []}, 1)
    assert rid is None  # best-effort: lỗi ghi vết → trả None, không raise
