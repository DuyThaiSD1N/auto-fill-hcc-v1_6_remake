"""Cầu nối hội thoại ↔ pipeline OCR/LLM (docs/06 §2.1).

Chạy pipeline NỀN (10-60s) rồi báo kết quả qua WS phiên upload — FE nhận event
`fields_ready`/`attach_ready` thì gọi lại /assistant/chat lấy actions. KHÔNG mở
API /process /attachments/plan cho FE (nguyên tắc 1 cửa — docs/03 §2.3).

Hợp đồng fields/attachments GIỮ NGUYÊN của auto-fill (docs/00 §4) — fill engine
extension chạy không sửa.
"""
import asyncio
import logging
import time

from app.chat import store as conv_store
from app.chat import tracing
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.process.schemas import FileItem
from app.services import ocr
from app.upload_session import store as up_store
from app.upload_session.ws import broadcast

logger = logging.getLogger(__name__)


def _session_files(sess: dict) -> list[dict]:
    """Dựng lại payload {name,type,dataUrl} từ file đã lưu trên disk theo phiên."""
    out = []
    for f in sess.get("files", []):
        data_url = up_store.file_to_data_url(sess["_id"], f)
        if data_url:
            out.append({"name": f["name"], "type": f.get("type") or "image/jpeg",
                        "dataUrl": data_url, "role": ""})
    return out


async def run_process(conv_id: str, sid: str, procedure_key: str) -> None:
    """OCR + trích field (state filling). Xong → conv.fields + WS `fields_ready`."""
    try:
        sess = await up_store.get(sid)
        proc = get_procedure(procedure_key)
        pipeline = get_pipeline(procedure_key)
        if not sess or not proc or not pipeline:
            raise RuntimeError("Thiếu phiên/thủ tục/pipeline.")
        files = _session_files(sess)
        if not files:
            raise RuntimeError("Phiên không còn file nào.")

        ocr.use_provider(None)  # mặc định raw; viết tay per-file để phase sau
        files_by_role = {"": files}  # mode agent: không gắn role, BE tự suy luận
        options: dict = {}
        if proc.get("review"):
            options["_review"] = True

        t_pipe = time.monotonic()
        result = await pipeline(files_by_role, options)
        pipe_ms = int((time.monotonic() - t_pipe) * 1000)

        # Bbox review (docs/06 §2.2): lưu theo conversation_id để FE xem lại vùng ảnh.
        review_data = result.pop("_review", None)
        if review_data:
            try:
                from app.review import store as review_store
                review_store.save_review(conv_id, review_data["sources"], review_data["images"])
            except Exception as e:  # noqa: BLE001 — review là phụ, không chặn fill
                logger.warning("[pipeline] lưu review lỗi (%s): %s", conv_id, e)

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        conv["fields"] = result.get("fields", [])
        conv["extracted"] = result.get("extracted", {})
        conv["pipeline_status"] = "fields_ready"
        conv["pipeline_error"] = ""
        # Trace kênh sidebar (kèm ảnh — consent v1.1): giữ request_id để fill_report
        # thật từ FE gắn vào đúng trace.
        conv["trace_request_id"] = await tracing.record_process(
            conv, procedure_key, proc, files, result, pipe_ms)
        await conv_store.save(conv)
        await broadcast(sid, {"type": "fields_ready", "count": len(conv["fields"])})
        # Tách chặng để soi chỗ chậm: review-bbox không có đồng hồ riêng
        # → xấp xỉ = pipeline - (ocr + llm).
        stats = result.get("stats") or {}
        ocr_ms, llm_ms = stats.get("ocr_latency_ms") or 0, stats.get("llm_latency_ms") or 0
        logger.info("[pipeline] process xong (%s): %d fields — ocr=%dms llm=%dms review~%dms pipeline=%dms",
                    conv_id, len(conv["fields"]), ocr_ms, llm_ms, max(0, pipe_ms - ocr_ms - llm_ms), pipe_ms)
    except Exception as e:  # noqa: BLE001 — lỗi pipeline phải ra bot, không nuốt
        logger.exception("[pipeline] process lỗi (%s)", conv_id)
        conv = await conv_store.get(conv_id)
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            await tracing.record_error(conv, procedure_key, "autofill", str(e))
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})


async def run_attach(conv_id: str, sid: str, procedure_key: str) -> None:
    """Lập kế hoạch đính kèm (state attaching). Xong → conv.attach_plan + WS `attach_ready`."""
    try:
        sess = await up_store.get(sid)
        attach_fn = get_attach_pipeline(procedure_key)
        if not sess or not attach_fn:
            raise RuntimeError("Thiếu phiên hoặc pipeline đính kèm.")
        raw_files = _session_files(sess)
        files = [FileItem(**f) for f in raw_files]
        if not files:
            raise RuntimeError("Phiên không còn file nào.")

        result = await attach_fn(files, {}, session=None)

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        conv["attach_plan"] = result.get("attachments", [])
        conv["attach_errors"] = result.get("errors", [])
        conv["pipeline_status"] = "attach_ready"
        proc = get_procedure(procedure_key) or {}
        conv["attach_trace_request_id"] = await tracing.record_attach(
            conv, procedure_key, proc, raw_files, result)
        await conv_store.save(conv)
        await broadcast(sid, {"type": "attach_ready", "count": len(conv["attach_plan"])})
        logger.info("[pipeline] attach plan xong (%s): %d mục", conv_id, len(conv["attach_plan"]))
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] attach lỗi (%s)", conv_id)
        conv = await conv_store.get(conv_id)
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            await tracing.record_error(conv, procedure_key, "attach", str(e))
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})


def spawn(coro) -> None:
    """Chạy nền trong event loop hiện tại (uvicorn) — flow không chờ pipeline."""
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda t: t.exception())  # nuốt cảnh báo un-retrieved (đã log trong coro)
