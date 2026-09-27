"""Bộ ghi Monitor gắn vào 3 hàm dịch vụ chung: OCR, gọi LLM, parse JSON.

Khoá hai điều: (1) có recorder thì ghi đủ thời gian/output từng bước; (2) giá trị trả về và
hành vi của dịch vụ KHÔNG đổi (có hay không có recorder).
"""
import json

import httpx
import pytest
import respx

from app.config import settings
from app.monitor import persist
from app.monitor import recorder as mon
from app.services import ocr, ocr_cache
from app.services.llm import client

DATA_URL = "data:image/png;base64,QUJDREVG"
DATA_URL_2 = "data:image/png;base64,WFlaWFla"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    token = mon._current.set(None)
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.test")
    monkeypatch.setattr(settings, "fallback_llm_base_url", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "ocr_tiengnoi_base_url", "https://ocr.test")
    monkeypatch.setattr(settings, "fallback_ocr_tiengnoi_base_url", "")
    monkeypatch.setattr(ocr_cache, "put_many_bg", lambda items: None)
    yield
    mon._current.reset(token)


def _llm_response(content, *, prompt=120, completion=30, finish="stop"):
    return httpx.Response(200, json={
        "model": "qwen-test",
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    })


# --- LLM -------------------------------------------------------------------------------------
@respx.mock
async def test_chat_ghi_token_endpoint_output_tho_va_tra_ve_y_nguyen():
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=_llm_response('```json\n{"fields": []}\n```'))
    rec = mon.start("autofill", "autofill")

    out = await client.chat([{"role": "user", "content": "abc"}], max_tokens=500)

    assert out == '```json\n{"fields": []}\n```'
    call = rec.llm_calls[0]
    assert call["n"] == 1 and call["purpose"] == "extract"  # suy theo loại lượt
    assert call["tokens_in"] == 120 and call["tokens_out"] == 30
    assert call["target"] == "primary" and call["model"] == "qwen-test"
    assert call["tries"][0]["ok"] is True
    assert call["raw"] is out
    assert call["max_tokens"] == 500 and call["prompt_chars"] == 3
    assert [s.name for s in rec.spans] == ["llm.extract"]


@respx.mock
async def test_purpose_truyen_tuong_minh_va_nhieu_lan_goi_danh_so():
    respx.post("https://llm.test/v1/chat/completions").mock(return_value=_llm_response("{}"))
    rec = mon.start("autofill", "autofill")
    await client.chat([{"role": "user", "content": "x"}], purpose="reason")
    await client.chat_text([{"role": "user", "content": "y"}])
    assert [(c["n"], c["purpose"], c["fn"]) for c in rec.llm_calls] == [
        (1, "reason", "chat"), (2, "extract", "chat_text")]
    t = rec.summary()
    assert t["n"]["llm_calls"] == 2
    assert set(t["s"]) == {"llm.reason", "llm.extract"}


@respx.mock
async def test_primary_loi_roi_sang_fallback_ghi_tung_lan_thu(monkeypatch):
    monkeypatch.setattr(settings, "fallback_llm_base_url", "https://llm2.test")
    respx.post("https://llm.test/v1/chat/completions").mock(return_value=httpx.Response(500))
    respx.post("https://llm2.test/v1/chat/completions").mock(return_value=_llm_response("{}"))
    rec = mon.start("attach", "autofill")

    await client.chat([{"role": "user", "content": "x"}])

    call = rec.llm_calls[0]
    assert [t["target"] for t in call["tries"]] == ["primary", "fallback-vllm"]
    assert call["tries"][0]["ok"] is False and "500" in call["tries"][0]["error"]
    assert call["target"] == "fallback-vllm" and call["purpose"] == "plan"
    assert rec.flags.get("llm_fallback") is True


@respx.mock
async def test_bi_cat_do_max_tokens_bat_co():
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=_llm_response("{", finish="length"))
    rec = mon.start("autofill", "autofill")
    await client.chat([{"role": "user", "content": "x"}])
    assert rec.flags.get("llm_cut") is True


@respx.mock
async def test_loi_llm_van_nem_ra_va_ghi_loi():
    respx.post("https://llm.test/v1/chat/completions").mock(return_value=httpx.Response(502))
    rec = mon.start("autofill", "autofill")
    with pytest.raises(RuntimeError):
        await client.chat([{"role": "user", "content": "x"}])
    assert "502" in rec.llm_calls[0]["error"]
    assert rec.errors and rec.spans[0].status == "error"


@respx.mock
async def test_khong_recorder_thi_chat_nhu_cu():
    respx.post("https://llm.test/v1/chat/completions").mock(return_value=_llm_response("xin chào"))
    assert await client.chat([{"role": "user", "content": "x"}]) == "xin chào"
    assert client.extract_json_block('{"a": 1}') == {"a": 1}


# --- parse -----------------------------------------------------------------------------------
@respx.mock
async def test_parse_gan_vao_dung_lan_goi_va_khong_bi_sua_theo_noi_goi():
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=_llm_response('trước ```json\n{"d": [1, 2]}\n``` sau'))
    rec = mon.start("attach", "autofill")
    raw = await client.chat([{"role": "user", "content": "x"}])

    parsed = client.extract_json_block(raw)
    parsed["d"].append(99)  # planner sửa dict sau khi parse

    call = rec.llm_calls[0]
    assert json.loads(call["parsed_src"]) == {"d": [1, 2]}
    doc, _ = persist.build_documents(rec, "req_x")
    assert doc["llm"][0]["parsed"] == {"d": [1, 2]}
    assert "post.parse" in [s.name for s in rec.spans]


@respx.mock
async def test_parse_loi_ghi_parse_error_va_van_nem_loi_cu():
    respx.post("https://llm.test/v1/chat/completions").mock(return_value=_llm_response("không có json"))
    rec = mon.start("autofill", "autofill")
    raw = await client.chat([{"role": "user", "content": "x"}])
    with pytest.raises(ValueError):
        client.extract_json_block(raw)
    assert "ValueError" in rec.llm_calls[0]["parse_error"]
    assert rec.flags.get("parse_fail") is True


def test_parse_text_khong_tu_llm_thi_dem_unlinked():
    rec = mon.start("autofill", "autofill")
    assert client.extract_json_block('{"a": 1}') == {"a": 1}
    assert rec.counters.get("parse_unlinked") == 1


# --- OCR -------------------------------------------------------------------------------------
@respx.mock
async def test_ocr_tach_tien_xu_ly_cache_server_va_ghi_tung_file(monkeypatch):
    hit_key = ocr_cache.content_key(DATA_URL)

    async def fake_get_many(keys):
        return {hit_key: {"text": "CĂN CƯỚC CÔNG DÂN", "provider": "tiengnoi", "max_tokens": 4096}}

    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    respx.post("https://ocr.test/v1/ocr").mock(return_value=httpx.Response(200, json={
        "results": [{"text": "GIẤY KHAI SINH"}]}))
    rec = mon.start("attach", "autofill")

    out = await ocr.ocr_per_file([
        {"name": "cccd.png", "type": "image/png", "dataUrl": DATA_URL},
        {"name": "ks.png", "type": "image/png", "dataUrl": DATA_URL_2},
    ])

    assert [o["text"] for o in out] == ["CĂN CƯỚC CÔNG DÂN", "GIẤY KHAI SINH"]
    assert out[0].get("_cached") is True
    names = [s.name for s in rec.spans]
    for name in ("ocr.call", "pre.hash", "ocr.cache", "ocr.remote", "pre.decode", "ocr.server", "ocr.split"):
        assert name in names
    files = rec.ocr_files
    assert [(f["name"], f["cache"], f["reason"]) for f in files] == [
        ("cccd.png", "hit", None), ("ks.png", "miss", "not_found")]
    assert files[0]["sha256"] == hit_key.split(":", 1)[1]
    assert files[1]["text"] == "GIẤY KHAI SINH"
    t = rec.summary()
    assert t["n"]["ocr_hit"] == 1 and t["n"]["ocr_miss"] == 1
    server = next(s for s in rec.spans if s.name == "ocr.server")
    assert server.attrs["target"] == "primary"


async def test_ocr_cache_mong_bi_bo_qua_co_ly_do(monkeypatch):
    key = ocr_cache.content_key(DATA_URL)

    async def fake_get_many(keys):
        return {key: {"text": "chữ", "provider": "tiengnoi", "max_tokens": 100}}

    async def fake_uncached(files, classify=False):
        return [{"name": f.get("name"), "text": "OCR lại đủ dày", "provider": "tiengnoi"} for f in files]

    monkeypatch.setattr(ocr_cache, "get_many", fake_get_many)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    rec = mon.start("autofill", "autofill")
    out = await ocr.ocr_per_file([{"name": "a.png", "dataUrl": DATA_URL}])
    assert out[0]["text"] == "OCR lại đủ dày"
    assert rec.ocr_files[0]["reason"] == "thin"


async def test_ocr_khong_recorder_giu_nguyen_ket_qua(monkeypatch):
    async def fake_uncached(files, classify=False):
        return [{"name": "a", "text": "abc", "provider": "tiengnoi"}]

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    assert await ocr.ocr_per_file([{"name": "a"}]) == [{"name": "a", "text": "abc", "provider": "tiengnoi"}]
