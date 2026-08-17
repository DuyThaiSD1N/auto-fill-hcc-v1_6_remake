"""Trích trường từ text OCR bằng LLM, theo từng loại giấy tờ.

Port từ services/llm/<thủ tục>/index.js — gộp lại vì chỉ khác system prompt.
"""
from app.services.llm import client
from app.services.llm.prompts import khai_sinh, khai_tu, trich_luc


async def _extract(full_text: str, system_prompt: str) -> dict:
    if not full_text or not full_text.strip():
        return {}
    out = await client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "TEXT OCR:\n\n" + full_text},
        ]
    )
    return client.extract_json_block(out)


async def extract_cccd(full_text: str) -> dict:
    return await _extract(full_text, khai_sinh.CCCD_SYSTEM_PROMPT)


async def extract_gcs(full_text: str) -> dict:
    return await _extract(full_text, khai_sinh.GCS_SYSTEM_PROMPT)


async def extract_gks(full_text: str) -> dict:
    return await _extract(full_text, trich_luc.GKS_SYSTEM_PROMPT)


async def extract_gbt(full_text: str) -> dict:
    return await _extract(full_text, khai_tu.GBT_SYSTEM_PROMPT)
