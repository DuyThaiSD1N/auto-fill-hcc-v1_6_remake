"""Khi LLM primary lỗi và có OPENAI_API_KEY → tự fallback sang OpenAI."""
import httpx
import respx

from app.config import settings
from app.services.llm import client


@respx.mock
async def test_fallback_to_openai_when_primary_fails(monkeypatch):
    # primary trả 500
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="upstream down")
    )
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")

    called = {}

    async def fake_openai(messages, temperature):
        called["used"] = True
        return '{"name": "FALLBACK"}'

    monkeypatch.setattr(client, "_chat_openai", fake_openai)

    out = await client.chat([{"role": "user", "content": "x"}])
    assert called.get("used") is True
    assert client.extract_json_block(out) == {"name": "FALLBACK"}


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

    async def boom(*a, **k):
        raise AssertionError("không được gọi fallback khi primary ok")

    monkeypatch.setattr(client, "_chat_openai", boom)
    out = await client.chat([{"role": "user", "content": "x"}])
    assert client.extract_json_block(out) == {"ok": 1}
