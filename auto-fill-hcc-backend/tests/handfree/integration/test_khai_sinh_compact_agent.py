"""Compact agent đăng ký khai sinh: short LLM output -> Angular UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.khai_sinh_lien_thong import process as agent
from app.channels.handfree.procedure_registry import get_pipeline


def _file(name, typ="image/jpeg"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,QUFB"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")


@respx.mock
async def test_khai_sinh_compact_agent_rejects_direct_ui_keys(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    respx.post(settings.ocr_tiengnoi_base_url.rstrip("/") + "/v1/ocr").mock(
        return_value=httpx.Response(200, json={"results": [{"text": "..."}] * 10})
    )
    out = {
        "fields": {
            "Ho": "TÊN_UI_SAI",
            "ChaHo": "CHA_UI_SAI",
            "MeHo": "MẸ_UI_SAI",
            "Gcs_HoTenCon": "TRẦN ANH QUÂN",
            "Gcs_NgaySinhCon": "10/04/2025",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("gcs.pdf", "application/pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["Ho"] == "TRẦN"
    assert d["ChuDem"] == "ANH"
    assert d["Ten"] == "QUÂN"
    assert d["NgaySinh"] == "10/04/2025"
    assert "ChaHo" not in d
    assert "MeHo" not in d
    assert not res["errors"]


def test_registry_uses_compact_birth_pipelines():
    assert get_pipeline("khai-sinh-dang-ky") is agent.run
