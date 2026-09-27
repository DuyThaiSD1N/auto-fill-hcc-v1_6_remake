"""Ghi dữ liệu của ``TraceRecorder`` xuống Mongo — CHỈ chạy nền, sau khi người dùng đã có kết quả.

Ba chỗ lưu:
- ``traces.timing``  : tóm tắt ~1 KB, gắn vào document trace sẵn có (người gọi tự đưa vào lúc
                       ``create_trace``) → dashboard chỉ đọc trường này, không đụng tài liệu nặng.
- ``trace_steps``    : 1 document / lượt — span chi tiết + output từng tầng (LLM thô, parse…).
- ``ocr_texts``      : text OCR theo sha256 file → một file OCR ở phân loại, điền, đính kèm chỉ
                       lưu một bản; ``trace_steps`` chỉ giữ tham chiếu hash.

Không bao giờ làm hỏng request: mọi lỗi nuốt + log; quá tải thì bỏ phần chi tiết (đếm lại số
lượt bị bỏ) chứ không xếp hàng chờ làm chậm tiến trình chính. Dựng document (cắt, serialize)
chạy trong thread để không chặn event loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import UpdateOne

from app.config import settings
from app.db.mongo import get_db
from app.monitor.recorder import TraceRecorder

logger = logging.getLogger(__name__)

_tasks: set[asyncio.Task] = set()
_sem: asyncio.Semaphore | None = None
dropped = 0  # số lượt bỏ phần chi tiết vì quá tải — đọc được khi điều tra


def timing(rec: TraceRecorder | None) -> dict | None:
    """Tóm tắt thời gian cho ``traces.timing``; lỗi → None, không làm hỏng lượt ghi trace."""
    if rec is None:
        return None
    try:
        summary = rec.summary()
        # Khoá có dấu chấm khó truy vấn trong Mongo → đổi sang gạch dưới cho bảng bước.
        summary["s"] = {k.replace(".", "_"): v for k, v in summary["s"].items()}
        return summary
    except Exception as exc:  # noqa: BLE001
        logger.warning("[monitor] tóm tắt timing lỗi: %s", exc)
        return None


def recorded_ocr_text(rec: TraceRecorder | None) -> str:
    """OCR text dựng lại từ text đã ghi ở dịch vụ OCR (cùng định dạng header của bước điền) —
    cho trace của các planner/bước không tự trả ``ocr_text``."""
    if rec is None:
        return ""
    from app.pipelines._shared.documents import join_ocr_documents

    docs = [{"name": f.get("name"), "text": f.get("text"), "provider": f.get("provider")}
            for f in rec.ocr_files if f.get("text")]
    return join_ocr_documents(docs) if docs else ""


def schedule(rec: TraceRecorder | None, request_id: str | None) -> None:
    """Đặt lịch ghi ``trace_steps`` + ``ocr_texts`` ở nền; gọi được từ mọi chỗ, không await."""
    global dropped
    if rec is None or not request_id or rec.detail == "off":
        return
    if len(_tasks) >= settings.trace_persist_max_pending:
        dropped += 1
        if dropped % 50 == 1:
            logger.warning("[monitor] quá tải ghi trace chi tiết, đã bỏ %s lượt", dropped)
        return
    try:
        task = asyncio.get_running_loop().create_task(save(rec, request_id))
    except RuntimeError:
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def save(rec: TraceRecorder, request_id: str) -> None:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(max(settings.trace_persist_concurrency, 1))
    try:
        async with _sem:
            steps_doc, ocr_ops = await asyncio.to_thread(build_documents, rec, request_id)
            db = get_db()
            if ocr_ops:
                await db.ocr_texts.bulk_write(ocr_ops, ordered=False)
            try:
                await db.trace_steps.replace_one({"_id": steps_doc["_id"]}, steps_doc, upsert=True)
            except Exception:  # noqa: BLE001 — output lạ (khoá "$…") → lưu dạng chuỗi JSON
                steps_doc["outputs"] = {"_json": _dumps(steps_doc.get("outputs"))[: _cap()]}
                steps_doc["llm"] = {"_json": _dumps(steps_doc.get("llm"))[: _cap()]}
                await db.trace_steps.replace_one({"_id": steps_doc["_id"]}, steps_doc, upsert=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[monitor] ghi trace_steps lỗi (%s): %s", request_id, exc)


# --- dựng document (chạy trong thread) ---------------------------------------------------------
def build_documents(rec: TraceRecorder, request_id: str) -> tuple[dict, list[UpdateOne]]:
    truncated: list[dict] = []
    now = datetime.now(timezone.utc)

    spans = [
        {
            "i": s.id,
            "p": s.parent,
            "n": s.name,
            "t0": rec.ms(s.t0),
            "ms": int(round(((s.t1 if s.t1 is not None else s.t0) - s.t0) * 1000)),
            "st": s.status if s.t1 is not None else "open",
            "a": _safe(s.attrs, f"span.{s.id}", truncated) if s.attrs else {},
        }
        for s in rec.spans
    ]

    ocr_ops: list[UpdateOne] = []
    ocr_refs: list[dict] = []
    text_cap = settings.trace_ocr_text_max_chars
    for idx, f in enumerate(rec.ocr_files):
        ref = {k: v for k, v in f.items() if k != "text"}
        text = f.get("text")
        sha = f.get("sha256")
        if sha and text and rec.detail == "full":
            ocr_ops.append(UpdateOne(
                {"_id": sha},
                {"$setOnInsert": {
                    "text": text[:text_cap],
                    "chars": len(text),
                    "truncated": len(text) > text_cap,
                    "provider": f.get("provider"),
                    "created_at": now,
                }},
                upsert=True,
            ))
        if text and not sha and rec.detail == "full":
            # Không có hash (file đến theo đường lạ) → lưu thẳng trong trace để không mất OCR.
            ref["text"] = text
        ocr_refs.append({k: _safe(v, f"ocr.{idx}.{k}", truncated) for k, v in ref.items()})

    # Cắt TỪNG trường (không gói cả lần gọi) để text thô dài không làm mất n/purpose/ms.
    heavy = () if rec.detail == "full" else ("raw", "parsed", "parsed_src")
    llm = []
    for c in rec.llm_calls:
        call = dict(c)
        src = call.pop("parsed_src", None)
        if src is not None and rec.detail == "full":
            try:
                call["parsed"] = json.loads(src)
            except ValueError:
                call["parsed"] = src
        llm.append({
            k: _safe(v, f"llm.{c.get('n')}.{k}", truncated)
            for k, v in call.items() if k not in heavy
        })

    outputs = {k: _safe(_resolve(v), f"out.{k}", truncated) for k, v in rec.outputs.items()}

    doc = {
        "_id": f"{request_id}:{rec.kind}",
        "request_id": request_id,
        "kind": rec.kind,
        "experience": rec.experience,
        "outcome": rec.outcome,
        # Lượt KHÔNG có bản ghi trong `traces` (phân loại, chủ hồ sơ, Auto Fill hỏng) → danh sách
        # Monitor gộp riêng nhóm này vào cùng traces.
        "steps_only": bool(rec.meta.get("steps_only")),
        "created_at": now,
        "meta": _safe(rec.meta, "meta", truncated),
        "timing": timing(rec),
        "spans": spans,
        "ocr": ocr_refs,
        "llm": llm,
        "outputs": outputs,
        "errors": list(rec.errors),
        "truncated": truncated,
    }
    _fit(doc)
    return doc, ocr_ops


def _resolve(value: Any) -> Any:
    if callable(value):
        try:
            return value()
        except Exception as exc:  # noqa: BLE001
            return {"_error": f"{type(exc).__name__}: {exc}"[:300]}
    return value


def _cap() -> int:
    return settings.trace_output_max_chars


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _safe(value: Any, path: str, truncated: list[dict]) -> Any:
    """Về dạng JSON thuần (BSON ghi được) + cắt chuỗi/cấu trúc quá cỡ, ghi lại chỗ đã cắt."""
    cap = _cap()
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) > cap:
            truncated.append({"path": path, "len": len(value)})
            return value[:cap]
        return value
    try:
        text = _dumps(value)
    except Exception:  # noqa: BLE001
        text = str(value)
    if len(text) > cap:
        truncated.append({"path": path, "len": len(text)})
        return {"_json": text[:cap]}
    return json.loads(text) if text[:1] in "{[" else text


def _fit(doc: dict) -> None:
    """Giữ document dưới trần: bỏ output lớn nhất trước, rồi tới text LLM thô."""
    limit = settings.trace_doc_max_bytes
    if len(_dumps(doc).encode("utf-8")) <= limit:
        return
    outputs = doc["outputs"]
    for key in sorted(outputs, key=lambda k: len(_dumps(outputs[k])), reverse=True):
        doc["truncated"].append({"path": f"out.{key}", "dropped": True})
        outputs[key] = None
        if len(_dumps(doc).encode("utf-8")) <= limit:
            return
    for call in doc["llm"]:
        if isinstance(call, dict) and call.get("raw"):
            doc["truncated"].append({"path": f"llm.{call.get('n')}.raw", "dropped": True})
            call["raw"] = None
            if len(_dumps(doc).encode("utf-8")) <= limit:
                return
