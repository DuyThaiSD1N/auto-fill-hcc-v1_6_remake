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

from app.channels.handfree.chat import store as conv_store
from app.channels.handfree.chat import tracing
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_owner_info_pipeline,
    get_pipeline,
    get_procedure,
)
from app.pipelines.chung_thuc_ban_sao.attach.stt1_virtual import apply_stt1_virtual_copy
from app.process.schemas import FileItem
from app.upload_session import store as up_store
from app.upload_session.ws import broadcast


async def _load_owner_user(conv: dict | None, sess: dict | None) -> dict | None:
    """Load tài khoản chủ phiên để lấy tỉnh/xã cho STT1 ảo.

    Best-effort: thiếu id / lỗi query → None → apply_stt1_virtual_copy no-op (giữ hành vi cũ).
    """
    uid = str(((conv or {}).get("auth_user") or {}).get("id")
              or (sess or {}).get("owner_user_id") or "").strip()
    if not uid:
        return None
    try:
        from bson import ObjectId

        from app.db.mongo import get_db

        return await get_db().users.find_one({"_id": ObjectId(uid)})
    except Exception:  # noqa: BLE001
        return None

logger = logging.getLogger(__name__)


def _owner_pipeline_options(conv: dict, owner_context: dict) -> dict:
    """Only the authorized branch may carry authorization context into OCR/LLM."""
    options = {"ownerContext": owner_context}
    if str(conv.get("execution_subject") or "self") == "authorized_person":
        options["executionSubject"] = "authorized_person"
    return options


def _owner_field_config(proc: dict, execution_subject: str) -> dict:
    config = dict((proc.get("ownerInfo") or {}).get("fields") or {})
    authorization_config = proc.get("authorizationInfo") or {}
    active_when = authorization_config.get("activeWhen") or {}
    if (
        authorization_config.get("enabled")
        and execution_subject == active_when.get("executionSubject")
    ):
        config.update(dict(authorization_config.get("fields") or {}))
    return config


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

        files_by_role = {"": files}  # mode agent: không gắn role, BE tự suy luận
        conv = await conv_store.get(conv_id)
        options: dict = {}
        if conv and conv.get("form_context"):
            options["formContext"] = dict(conv["form_context"])
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
            conv, procedure_key, proc, files, result, pipe_ms,
        )
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


async def run_business_registration(conv_id: str, sid: str, procedure_key: str) -> None:
    """Chuẩn bị trọn gói cho HkdOnline: 8 trang + kế hoạch đính kèm.

    Cổng hộ kinh doanh reload toàn trang sau từng lần lưu nên extension phải nhận toàn bộ
    dữ liệu trước khi khởi động state machine. Giữ hai pipeline nghiệp vụ độc lập như
    Auto-fill, nhưng chỉ phát một sự kiện ``business_ready`` khi cả hai đã sẵn sàng.
    """
    try:
        sess = await up_store.get(sid)
        proc = get_procedure(procedure_key)
        pipeline = get_pipeline(procedure_key)
        attach_fn = get_attach_pipeline(procedure_key)
        if not sess or not proc or not pipeline or not attach_fn:
            raise RuntimeError("Thiếu phiên/thủ tục/pipeline hộ kinh doanh.")

        raw_files = _session_files(sess)
        if not raw_files:
            raise RuntimeError("Phiên không còn file nào.")

        # Thành lập mới: dựng đủ 8 trang. Thay đổi nội dung (page="__change__"): pipeline
        # so "hiện tại vs đề nghị" rồi chỉ dựng trang cần sửa + businessFlow (khóa tra cứu).
        workflow = str(proc.get("businessWorkflow") or "create")
        process_options = {"allPages": True} if workflow == "create" else {"page": f"__{workflow}__"}
        t_process = time.monotonic()
        process_result = await pipeline({"": raw_files}, process_options)
        process_ms = int((time.monotonic() - t_process) * 1000)

        file_items = [FileItem(**item) for item in raw_files]
        attach_result = await attach_fn(file_items, {}, session=None)

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        pages = process_result.get("pages") or {}
        conv["fields"] = process_result.get("fields", [])
        conv["business_pages"] = pages
        conv["business_flow"] = process_result.get("businessFlow") or {}
        conv["extracted"] = process_result.get("extracted", {})
        conv["attach_plan"] = attach_result.get("attachments", [])
        conv["attach_errors"] = attach_result.get("errors", [])
        conv["pipeline_status"] = "business_ready"
        conv["pipeline_error"] = ""
        conv["trace_request_id"] = await tracing.record_process(
            conv, procedure_key, proc, raw_files, process_result, process_ms
        )
        conv["attach_trace_request_id"] = await tracing.record_attach(
            conv, procedure_key, proc, raw_files, attach_result
        )
        await conv_store.save(conv)
        await broadcast(sid, {
            "type": "business_ready",
            "pages": len(pages),
            "attachments": len(conv["attach_plan"]),
        })
        logger.info(
            "[pipeline] HKD sẵn sàng (%s): %d trang, %d tệp đính kèm",
            conv_id, len(pages), len(conv["attach_plan"]),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] HKD lỗi (%s)", conv_id)
        conv = await conv_store.get(conv_id)
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            await tracing.record_error(conv, procedure_key, "business_registration", str(e))
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})


async def run_owner_info(conv_id: str, sid: str, procedure_key: str) -> None:
    """Extract the matched owner's fields before the main declaration page."""
    try:
        sess = await up_store.get(sid)
        proc = get_procedure(procedure_key)
        pipeline = get_owner_info_pipeline(procedure_key)
        conv = await conv_store.get(conv_id)
        if not sess or not proc or not pipeline or not conv:
            raise RuntimeError("Thiếu phiên/thủ tục/pipeline thông tin chủ hồ sơ.")
        files = _session_files(sess)
        if not files:
            raise RuntimeError("Phiên không còn file nào.")

        owner_context = dict(conv.get("owner_context") or {})
        if not (owner_context.get("fullName") or owner_context.get("identityNumber")):
            raise RuntimeError("Chưa đọc được họ tên hoặc số định danh của chủ hồ sơ trên trang.")

        execution_subject = str(conv.get("execution_subject") or "self")
        # Nhánh bản thân tuyệt đối không truyền context ủy quyền vào pipeline/prompt.
        pipeline_options = _owner_pipeline_options(conv, owner_context)
        result = await pipeline({"": files}, pipeline_options)
        config = _owner_field_config(proc, execution_subject)
        extracted_values = {
            field.get("name"): field.get("value") for field in (result.get("fields") or [])
            if field.get("name")
        }
        # Gửi đủ contract đang hoạt động để extension còn kiểm tra giá trị portal đang có.
        # Nhánh self có 4 owner fields; nhánh authorized mới ghép thêm authorization fields.
        # Giá trị OCR thiếu vẫn là rỗng; extension chỉ báo người dân nhập, tuyệt đối không đoán.
        plan = [
            {**spec, "value": extracted_values.get(source_name, ""), "overwrite": False}
            for source_name, spec in config.items()
        ]

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        conv["owner_fields"] = plan
        conv["owner_match"] = result.get("owner_match") or {"matched": False}
        conv["authorization_match"] = result.get("authorization_match") or {}
        conv["owner_errors"] = list(result.get("errors") or [])
        conv["pipeline_status"] = "owner_fields_ready"
        conv["pipeline_error"] = ""
        await conv_store.save(conv)
        await broadcast(sid, {"type": "owner_fields_ready", "count": len(plan)})
        logger.info("[pipeline] owner info xong (%s): matched=%s fields=%d",
                    conv_id, bool(conv["owner_match"].get("matched")), len(plan))
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] owner info lỗi (%s)", conv_id)
        conv = await conv_store.get(conv_id)
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            await tracing.record_error(conv, procedure_key, "owner_info", str(e))
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})


async def run_attach(conv_id: str, sid: str, procedure_key: str,
                     options: dict | None = None) -> None:
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

        attach_options = dict(options or {})
        result = await attach_fn(files, attach_options, session=None)

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        # STT1 nhận 1 file ẢO. HTTP router auto-fill gọi sẵn; handfree đi qua chat pipeline nên
        # phải gọi Ở ĐÂY. Account/thủ tục khác → no-op (directive None), plan giữ nguyên.
        owner_user = await _load_owner_user(conv, sess)
        result = apply_stt1_virtual_copy(result, owner_user, procedure_key)
        conv["attach_plan"] = result.get("attachments", [])
        conv["attach_plan_stt1_virtual"] = result.get("stt1VirtualCopy")
        conv["attach_errors"] = result.get("errors", [])
        conv["attach_action_in_progress"] = False
        conv["attach_action_dispatch_id"] = ""
        conv["attach_action_lease_until"] = None
        conv["pipeline_status"] = "attach_ready"
        proc = get_procedure(procedure_key) or {}
        conv["attach_trace_request_id"] = await tracing.record_attach(
            conv, procedure_key, proc, raw_files, result,
            split=(bool(attach_options.get("splitMode"))
                   if "splitMode" in attach_options else None))
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
