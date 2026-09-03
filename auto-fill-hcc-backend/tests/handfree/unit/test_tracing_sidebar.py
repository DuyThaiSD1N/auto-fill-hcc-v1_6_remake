"""Trace kênh sidebar dùng cùng danh tính tài khoản với Auto Fill;
ảnh lưu qua save_request_files + process_requests (nguồn xem file/ZIP của trang quản lý)."""
import re

import pytest

from app.channels.handfree.chat import tracing


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
         "auth_user": {"id": "u-song-lieu", "username": "hccsonglieu",
                       "name": "Phường Song Liễu tỉnh Bắc Ninh"},
         "location": {"ward": "Phường Song Liễu", "province": "Tỉnh Bắc Ninh"},
         "consent": {"id": "TLND-ABC", "accepted": True}}

_FILES = [{"name": "cccd.jpg", "type": "image/jpeg", "dataUrl": "data:x;base64,QUFB", "role": ""}]


@pytest.mark.asyncio
async def test_record_process_ghi_du_request_va_trace(captured):
    result = {"fields": [{"name": "HoTen", "value": "A"}], "extracted": {},
              "ocr_text": "CĂN CƯỚC", "llm_output": {"fields": {}},
              "stats": {"ocr_latency_ms": 100, "llm_latency_ms": 200}}
    rid = await tracing.record_process(_CONV, "ket-hon", {"label": "Kết hôn"}, _FILES, result, 999)

    assert rid and re.fullmatch(r"req_[0-9a-f]{12}", rid)
    req = captured["requests"][0]
    assert req["user_id"] == "u-song-lieu" and req["request_id"] == rid
    assert req["options"]["channel"] == "sidebar"
    assert req["options"]["consent_id"] == "TLND-ABC"  # trace nối được về nhật ký chấp thuận
    tr = captured["traces"][0]
    assert tr["kind"] == "autofill" and tr["status"] == "done"
    assert tr["experience"] == "handfree"
    assert tr["name"] == "Phường Song Liễu tỉnh Bắc Ninh"
    assert tr["username"] == "hccsonglieu" and tr["ocr_text"] == "CĂN CƯỚC"
    assert captured["finishes"][0][1]["fields_count"] == 1


@pytest.mark.asyncio
async def test_record_process_dien_lai_tao_request_va_trace_moi(captured):
    first_result = {
        "fields": [{"name": "HoTen", "value": "A"}],
        "extracted": {"documents": ["cccd.jpg"]},
        "ocr_text": "CĂN CƯỚC LẦN ĐẦU",
        "llm_output": {"fields": {"HoTen": "A"}},
        "stats": {"ocr_latency_ms": 100, "llm_latency_ms": 200},
    }
    result = {
        "fields": [{"name": "HoTen", "value": "B"}],
        "extracted": {"documents": ["cccd.jpg"]},
        "ocr_text": "CĂN CƯỚC MỚI",
        "llm_output": {"fields": {"HoTen": "B"}},
        "stats": {"ocr_latency_ms": 90, "llm_latency_ms": 180},
    }

    first_rid = await tracing.record_process(
        _CONV, "ket-hon", {"label": "Kết hôn"}, _FILES, first_result, 450,
    )
    refill_rid = await tracing.record_process(
        _CONV, "ket-hon", {"label": "Kết hôn"}, _FILES, result, 400,
    )

    assert first_rid and refill_rid and refill_rid != first_rid
    assert [request["request_id"] for request in captured["requests"]] == [
        first_rid, refill_rid,
    ]
    assert [trace["request_id"] for trace in captured["traces"]] == [
        first_rid, refill_rid,
    ]
    assert captured["traces"][1]["ocr_text"] == "CĂN CƯỚC MỚI"
    assert captured["finishes"][1][1]["fields"] == result["fields"]


@pytest.mark.asyncio
async def test_record_attach_va_set_report(captured):
    stats = {"ocr_latency_ms": 120, "llm_latency_ms": 230, "total_latency_ms": 350}
    classification = {"0": {"detectedType": "Căn cước công dân"}}
    result = {"attachments": [{"fileName": "cccd.pdf", "componentName": "STT 2"}],
              "extracted": {}, "stats": stats, "ocr_provider": "tiengnoi",
              "llm_output": classification}
    rid = await tracing.record_attach(
        _CONV, "chung-thuc-ban-sao", {"label": "Chứng thực bản sao"},
        _FILES, result, split=True,
    )
    assert rid and re.fullmatch(r"req_[0-9a-f]{12}", rid)
    tr = captured["traces"][0]
    assert tr["kind"] == "attach" and tr["attachments"][0]["role"] == "STT 2"
    assert tr["experience"] == "handfree"
    assert tr["attachments"][0]["name"] == "cccd.jpg"
    assert tr["stats"] == stats
    assert tr["ocr_provider"] == "tiengnoi"
    assert tr["llm_output"]["classification"] == classification
    assert tr["split"] is True
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


def test_account_name_fallback_cho_phien_cu():
    assert tracing._account_name({  # noqa: SLF001 — kiểm tra tương thích phiên legacy
        "location": {"ward": "Phường Tân Phong", "province": "Tỉnh Lai Châu"},
    }) == "Phường Tân Phong, Tỉnh Lai Châu"
