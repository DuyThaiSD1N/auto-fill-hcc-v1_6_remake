"""Ghép các bước của luồng mới cho một hồ sơ + đo thời gian từng bước."""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import re
import time

from app.procedures import registry
from app.services import ocr, ocr_qwen
from app.services.llm import client as llm_client
from scripts.luongmoi import du_lieu, kiem_tra, muc_dich, prompt

PROC = "xac-nhan-tinh-trang-hon-nhan"
_AGENT_MAX_TOKENS = 2000

# Thay OCR Vintern / LLM trích xuất THEO TỪNG TASK (contextvar), không đè toàn cục: nhiều hồ sơ chạy song song,
# hồ sơ này đang chạy lại mapper trên v2 thì hồ sơ khác vẫn gọi LLM thật.
_VINTERN = contextvars.ContextVar("vintern_by_sha", default=None)
_LLM_JSON = contextvars.ContextVar("llm_json", default=None)
_real_ocr, _real_chat = ocr.ocr_per_file, llm_client.chat


async def _ocr_per_file(items, **kwargs):
    stored = _VINTERN.get()
    if stored is None:
        return await _real_ocr(items, **kwargs)
    return [{"name": d["name"], "type": d["type"], "provider": "tiengnoi",
             "text": stored.get(hashlib.sha256(d["dataUrl"].encode()).hexdigest(), "")} for d in items]


async def _chat(*args, **kwargs):
    fixed = _LLM_JSON.get()
    if fixed is None:
        return await _real_chat(*args, **kwargs)
    return "```json\n" + json.dumps(fixed, ensure_ascii=False) + "\n```"


ocr.ocr_per_file, llm_client.chat = _ocr_per_file, _chat


async def _pipeline(case: dict, llm_json: dict | None = None) -> dict:
    _VINTERN.set(case["vintern_by_sha"])
    _LLM_JSON.set(llm_json)
    return await registry.get_pipeline(PROC)({"doc": case["docs"]}, dict(case["options"]))


async def _timed(coro):
    t0 = time.monotonic()
    value = await coro
    return value, round(time.monotonic() - t0, 1)


def _ui(res: dict) -> dict:
    return {f["name"]: f["value"] for f in res.get("fields") or []}


def _probe(value):
    """Giá trị dò để biết một ô cảnh báo đi vào ô UI nào (ô không lên form thì cảnh báo vô ích)."""
    if isinstance(value, dict):
        return {**value, "diaChi": f"{value.get('diaChi') or ''} ZZQ9"}
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", str(value or "").strip()):
        return "01/01/1901"
    return "ZZQ9"


def _changed(ui1: dict, ui2: dict) -> list[str]:
    return [k for k in sorted(set(ui1) | set(ui2))
            if json.dumps(ui1.get(k), sort_keys=True, ensure_ascii=False) != json.dumps(ui2.get(k), sort_keys=True, ensure_ascii=False)]


async def _gan_o_ui(case: dict, v1: dict, ui1: dict, flags: list[dict]) -> list[dict]:
    kept = []
    for row in flags:
        trial = row["value"] if row["flag"] == "sua" else _probe(row["old"])
        res = await _pipeline(case, {"fields": {**v1, row["name"]: trial}})
        keys = _changed(ui1, _ui(res))
        if keys:
            kept.append({**row, "ui_keys": keys})
    return kept


async def chay(case: dict, refresh_qwen: bool = False) -> dict:
    # (1) + (2) song song: luồng hiện tại (OCR Vintern prod đã lưu → LLM → mapper) và OCR Qwen
    (res1, v1_s), ((qwen_rows, qwen_s, cached), _) = await asyncio.gather(
        _timed(_pipeline(case)), _timed(du_lieu.qwen_ocr(case, refresh_qwen)))
    v1 = dict(((res1.get("llm_output") or {}).get("fields")) or {})
    ui1 = _ui(res1)

    # (3) gợi ý từ code → (4) agent rà soát ∥ bước mục đích → (5) chốt cờ
    goi_y = kiem_tra.goi_y(v1)
    qtext = du_lieu.qwen_text(qwen_rows)
    messages = prompt.build_messages(v1, goi_y, qtext, case["vintern_text"])
    resp, md = await asyncio.gather(
        ocr_qwen.chat(messages, max_tokens=_AGENT_MAX_TOKENS, timeout_s=180),
        muc_dich.chuan_hoa(v1.get("Purpose") or "", case["vintern_text"], qtext))
    try:
        agent = llm_client.extract_json_block(resp["content"])
    except Exception as exc:  # noqa: BLE001 — giữ output thô để xem agent trả sai định dạng ra sao
        agent = {"_parse_error": str(exc), "_raw": resp["content"][:3000]}
    flags = kiem_tra.chot(agent.get("fields") or [], v1, case["vintern_text"] + "\n" + qtext, qwen_rows)
    md_row = kiem_tra.chot_muc_dich(md, v1)
    if md_row:
        flags.append(md_row)

    # (5b) Chỉ giữ cờ làm ô trên FORM thay đổi, gắn mã ô UI cho FE tô đúng ô.
    flags = await _gan_o_ui(case, v1, ui1, flags)

    # (6) v2 = v1 + các chỗ SỬA → chạy lại fallback/validate/mapper như pipeline thật
    v2 = {**v1, **{r["name"]: r["value"] for r in flags if r["flag"] == "sua"}}
    res2, v2_s = await _timed(_pipeline(case, {"fields": v2}))
    ui2 = _ui(res2)
    ui_changes = {k: [ui1.get(k), ui2.get(k)] for k in sorted(set(ui1) | set(ui2))
                  if json.dumps(ui1.get(k), sort_keys=True) != json.dumps(ui2.get(k), sort_keys=True)}

    agent_s = round(max(resp["ms"], (md or {}).get("ms") or 0) / 1000, 1)
    output1_s = round(case["vintern_prod_s"] + v1_s, 1)
    return {
        "rid": case["rid"],
        "output1": {"llm": v1, "ui": ui1},
        "output2": {"review": flags, "ui_changes": ui_changes},
        "v2_llm": v2,
        "agent": {"goi_y": goi_y, "raw": agent, "finish": resp["finish_reason"], "usage": resp["usage"]},
        "muc_dich": md,
        "thoi_gian": {
            "vintern_prod_s": case["vintern_prod_s"], "v1_llm_mapper_s": v1_s,
            "qwen_ocr_s": qwen_s, "qwen_tu_cache": cached, "agent_s": agent_s, "v2_mapper_s": v2_s,
            "uoc_output1_s": output1_s,
            "uoc_output2_s": round(max(output1_s, qwen_s) + agent_s + v2_s, 1),
        },
    }
