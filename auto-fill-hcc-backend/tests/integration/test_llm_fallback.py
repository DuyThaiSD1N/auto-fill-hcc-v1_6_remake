"""LLM chỉ chạy trên máy riêng (vLLM): hết máy thì ném lỗi, không gửi sang OpenAI dù có OPENAI_API_KEY."""
import httpx
import respx

from app.config import settings
from app.services.llm import client


@respx.mock
async def test_may_rieng_loi_thi_nem_loi_khong_sang_openai(monkeypatch):
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="upstream down")
    )
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    for fn in (client.chat, client.chat_text):
        try:
            await fn([{"role": "user", "content": "x"}])
            assert False, "phải ném lỗi khi hết máy riêng"
        except RuntimeError as e:
            assert "500" in str(e)


@respx.mock
async def test_no_fallback_raises_when_no_key(monkeypatch):
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="down")
    )
    monkeypatch.setattr(settings, "openai_api_key", "")
    try:
        await client.chat([{"role": "user", "content": "x"}])
        assert False, "phải ném lỗi khi không có fallback"
    except RuntimeError:
        pass


@respx.mock
async def test_primary_ok_no_fallback(monkeypatch):
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "```json\n{\"ok\":1}\n```"}}]})
    )

    out = await client.chat([{"role": "user", "content": "x"}])
    assert client.extract_json_block(out) == {"ok": 1}


def test_extract_json_dong_not_ngoac_llm_bo_sot():
    # Thiếu đúng một "}" cuối → trước đây JSONDecodeError, mất trắng mọi field.
    out = '```json\n{"fields": {"A": "1", "B": {"tinh": "Hà Nội", "xa": ""}}\n```'
    assert client.extract_json_block(out) == {"fields": {"A": "1", "B": {"tinh": "Hà Nội", "xa": ""}}}
    try:
        client.extract_json_block('```json\n{"fields": {"A": "1"]}\n```')
    except ValueError:
        pass
    else:
        raise AssertionError("ngoặc lệch nhau thì vẫn phải báo lỗi")
