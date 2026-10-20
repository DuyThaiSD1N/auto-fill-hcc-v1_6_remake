"""Luồng kết hợp cho đăng ký kết hôn: tách thẻ một lần → (Vintern OCR + LLM trích) ‖ (Qwen đọc ảnh ra JSON) → ghép.

- Tách thẻ (OpenCV) chạy MỘT lần, dùng chung cho cả hai nhánh: trang scan nhiều thẻ được cắt riêng từng thẻ.
- Nhánh Vintern giữ nguyên luồng cũ (OCR + LLM + validate), chỉ OCR trên ảnh đã tách thẻ.
- Nhánh Qwen lỗi / quá giờ → giữ nguyên kết quả Vintern (lỗi chỉ ghi trace + log). Vintern không ra field nào →
  ghép tự lấy Qwen.
- Ghép trên field THÔ (trước mapper) theo ``ghep.py``; quyết định từng field lưu vào llm_output["ket_hop"] để soi trace.
"""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.pipelines._shared.compact_agent.runner import flatten
from app.pipelines.ket_hon.process.ket_hop import ghep
from app.pipelines.ket_hon.process.schema import COMPACT_COMP_BY_NAME
from app.services import ocr

logger = logging.getLogger(__name__)


async def _qwen(files: list[dict], da_cat: list[list[tuple]]) -> dict:
    from app.pipelines.ket_hon.process.ket_hop import qwen_json
    try:
        return await asyncio.wait_for(asyncio.to_thread(qwen_json.doc, files, da_cat),
                                      timeout=settings.ket_hon_qwen_timeout_ms / 1000)
    except asyncio.TimeoutError:
        return {"raw": {}, "error": f"quá {settings.ket_hon_qwen_timeout_ms} ms"}
    except Exception as e:  # noqa: BLE001 — lỗi nhánh Qwen không được làm hỏng luồng Vintern
        logger.warning("ket_hon ket_hop qwen lỗi: %s", e)
        return {"raw": {}, "error": f"{type(e).__name__}: {e}"[:300]}


async def run(files_by_role: dict[str, list[dict]], chay_vintern) -> dict:
    """chay_vintern(ocr_fn) → kết quả runner chung (fields thô đã validate, ocr_text, llm_output...)."""
    # OpenCV chỉ nạp khi luồng này chạy: thư viện video đi kèm OpenCV xung đột bộ mã hoá HEIC (x265) của pillow_heif,
    # nạp sẵn lúc khởi động app làm mọi tiến trình mang theo rủi ro đó.
    from app.services import tach_the

    files = flatten(files_by_role)
    try:
        da_cat, cat_ms = await asyncio.to_thread(tach_the.cat, files)
    except Exception as e:  # noqa: BLE001 — tách thẻ lỗi thì chạy như cũ
        logger.warning("ket_hon tách thẻ lỗi: %s", e)
        res = await chay_vintern(None)
        res.setdefault("errors", []).append(f"tach_the: {e}")
        return res

    theo_id = {id(f): tep for f, tep in zip(files, da_cat)}
    theo_ten = {f.get("name"): tep for f, tep in zip(files, da_cat)}
    so_the = {"n": 0}

    async def ocr_tach(ocr_files: list[dict]) -> list[dict]:
        tep = [theo_id.get(id(f)) or theo_ten.get(f.get("name")) or [] for f in ocr_files]
        items, groups, n = tach_the.tach(ocr_files, tep)
        so_the["n"] = n
        return tach_the.gop_ket_qua(ocr_files, await ocr.ocr_per_file(items), groups)

    qwen_task = asyncio.create_task(_qwen(files, da_cat))
    res = await chay_vintern(ocr_tach)
    q = await qwen_task

    q_raw = q.get("raw") or {}
    info = {"cat_ms": cat_ms, "so_the_cat": so_the["n"], "qwen_ms": q.get("ms"), "qwen_usage": q.get("usage"),
            "qwen": q_raw}
    if q.get("error"):
        # Nhánh phụ: kết quả Vintern vẫn dùng được nên không đưa vào errors của hồ sơ, chỉ lưu trace + log.
        info["qwen_loi"] = q["error"]
        logger.warning("ket_hon ket_hop qwen: %s", q["error"])
    if q_raw:
        chu_v = res.get("ocr_text") or ""
        v_raw = {f["name"]: f.get("value") for f in res.get("fields") or [] if f.get("name")}
        out, quyet = ghep.ghep(v_raw, q_raw, [chu_v], soat=True, chu_v=chu_v, chu_q=None)
        if ghep.co_to_khai(chu_v):
            out = ghep.o_tich_theo_qwen(out, q_raw, quyet)
        res["fields"] = [{"name": k, "comp": COMPACT_COMP_BY_NAME.get(k, "x-input"), "value": val}
                         for k, val in out.items()]
        info["ghep"] = quyet
    llm_output = res.get("llm_output")
    res["llm_output"] = {**(llm_output if isinstance(llm_output, dict) else {"vintern": llm_output}), "ket_hop": info}
    res.setdefault("stats", {})["qwen_latency_ms"] = q.get("ms")
    return res
