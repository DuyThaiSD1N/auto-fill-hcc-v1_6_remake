"""Compare OCR API text with LLM-as-OCR text for a local Giay bao tu PDF.

Run manually:
RUN_LIVE_GBT_LLM_OCR=1 .venv/bin/pytest -q -s tests/integration/test_khai_tu_gbt_live_llm.py

Optional:
LIVE_LLM_OCR_PROVIDER=primary|openai  # default: primary
LIVE_LLM_OCR_MODEL=gpt-4.1-mini       # only for provider=openai
"""

import base64
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.services import ocr
from app.services.llm import client as llm_client


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_GBT_LLM_OCR") != "1",
    reason="live OCR comparison; set RUN_LIVE_GBT_LLM_OCR=1 to run",
)


def _local_gbt_pdf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "giấy báo tử đèo sóp.pdf"


def _pdf_file_item(path: Path) -> dict:
    data_url = "data:application/pdf;base64," + base64.b64encode(path.read_bytes()).decode()
    return {"name": path.name, "type": "application/pdf", "dataUrl": data_url}


def _pdf_first_page_image_data_url(path: Path) -> str:
    """Render PDF to PNG for primary OpenAI-compatible multimodal chat endpoints."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        output = Path(tmp_dir) / "page.png"
        proc = subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            pytest.fail(f"Cannot render PDF to image with sips: {proc.stderr or proc.stdout}")
        return "data:image/png;base64," + base64.b64encode(output.read_bytes()).decode()


def _response_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(value)
    return "\n".join(chunks)


async def _api_ocr_text(path: Path) -> tuple[str, int]:
    started = time.monotonic()
    result = (await ocr.ocr_per_file([_pdf_file_item(path)]))[0]
    latency_ms = int((time.monotonic() - started) * 1000)
    assert not result.get("error"), result.get("error")
    return result.get("text") or "", latency_ms


def _ocr_prompt() -> str:
    return (
        "Bạn là OCR engine. Đọc tài liệu đính kèm và trả lại văn bản nhìn thấy được.\n"
        "- Giữ xuống dòng gần giống tài liệu.\n"
        "- Đọc cả chữ in và chữ viết tay nếu nhìn rõ.\n"
        "- Không suy luận, không chuẩn hóa, không map field.\n"
        "- Nếu một đoạn không chắc, ghi [không rõ] thay vì đoán.\n"
        "- Chỉ trả về text OCR, không giải thích."
    )


async def _primary_llm_ocr_text(path: Path) -> tuple[str, int, str]:
    image_data_url = _pdf_first_page_image_data_url(path)
    payload = {
        "model": settings.llm_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _ocr_prompt()},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }],
        "temperature": 0,
        "max_tokens": 3000,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": settings.agent_reasoning},
    }
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=settings.llm_timeout_ms / 1000, verify=False) as http:
        response = await http.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions", json=payload)
    latency_ms = int((time.monotonic() - started) * 1000)
    if response.status_code >= 400:
        pytest.fail(f"Primary LLM OCR HTTP {response.status_code}: {response.text[:1000]}")
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    return content, latency_ms, f"primary:{settings.llm_model}"


async def _openai_llm_ocr_text(path: Path) -> tuple[str, int, str]:
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY is required for LLM OCR comparison")

    model = os.getenv("LIVE_LLM_OCR_MODEL", "gpt-4.1-mini")
    file_data = _pdf_file_item(path)["dataUrl"]

    started = time.monotonic()
    response = await llm_client._get_openai_client().responses.create(  # noqa: SLF001
        model=model,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": _ocr_prompt()},
                {"type": "input_file", "filename": path.name, "file_data": file_data},
            ],
        }],
        max_output_tokens=3000,
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    return _response_text(response), latency_ms, f"openai:{model}"


async def _llm_ocr_text(path: Path) -> tuple[str, int, str]:
    provider = os.getenv("LIVE_LLM_OCR_PROVIDER", "primary").lower()
    if provider == "primary":
        return await _primary_llm_ocr_text(path)
    if provider == "openai":
        return await _openai_llm_ocr_text(path)
    pytest.fail(f"Unsupported LIVE_LLM_OCR_PROVIDER={provider!r}")


async def test_compare_api_ocr_with_llm_ocr_for_gbt_pdf():
    path = _local_gbt_pdf_path()

    api_text, api_latency_ms = await _api_ocr_text(path)
    llm_text, llm_latency_ms, model = await _llm_ocr_text(path)

    print("\n=== OCR API ===")
    print(f"latency_ms={api_latency_ms} chars={len(api_text)}")
    print("--- OCR API TEXT START ---")
    print(api_text)
    print("--- OCR API TEXT END ---")

    print("\n=== LLM OCR ===")
    print(f"model={model} latency_ms={llm_latency_ms} chars={len(llm_text)}")
    print("--- LLM OCR TEXT START ---")
    print(llm_text)
    print("--- LLM OCR TEXT END ---")

    assert "GIẤY BÁO TỬ" in api_text
    assert "GIẤY BÁO TỬ" in llm_text
