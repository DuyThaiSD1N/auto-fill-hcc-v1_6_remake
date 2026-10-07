"""Cầu nối hội thoại ↔ pipeline OCR/LLM (docs/06 §2.1).

Chạy pipeline NỀN (10-60s) rồi báo kết quả qua WS phiên upload — FE nhận event
`fields_ready`/`attach_ready` thì gọi lại /assistant/chat lấy actions. KHÔNG mở
API /process /attachments/plan cho FE (nguyên tắc 1 cửa — docs/03 §2.3).

Hợp đồng fields/attachments GIỮ NGUYÊN của auto-fill (docs/00 §4) — fill engine
extension chạy không sửa.
"""
import asyncio
import base64
import logging
import time

from app.channels.handfree.chat import store as conv_store
from app.channels.handfree.chat import tracing
from app.monitor import persist as monitor_persist
from app.monitor import recorder as mon
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_owner_info_pipeline,
    get_pipeline,
    get_procedure,
)
from app.pipelines.chung_thuc_ban_sao.attach.stt1_virtual import apply_stt1_virtual_copy
from app.pipelines.cai_chinh_dvc_moi.process.mapper import (
    with_account_process_options as with_cai_chinh_account_process_options,
)
from app.pipelines.cap_giay_phep_xay_dung.process.mapper import (
    with_account_process_options as with_gpxd_account_process_options,
)
from app.pipelines.dang_ky_kinh_doanh.process.mapper import (
    with_account_process_options as with_hkd_account_process_options,
)
from app.pipelines.khai_sinh_dang_ky_lai.process.mapper import with_account_process_options
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.mapper import (
    with_account_process_options as with_mai_tang_htxh_account_process_options,
)
from app.pipelines.xac_nhan_tthn.process.mapper import (
    with_account_process_options as with_tthn_account_process_options,
)
from app.pipelines.khai_sinh_lien_thong.attach.planner import with_nghia_lo_attach_options
from app.pipelines.xac_nhan_tthn.attach.nghia_hung import with_account_attach_options
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


def _execution_subject_for_owner(conv: dict) -> str:
    """Nhánh đang chạy ở bước chủ hồ sơ. TRANG là sự thật, không phải lựa chọn của cán bộ.

    Trang mọc khối "Thông tin ủy quyền cá nhân" nghĩa là cổng đang ở nhánh ủy quyền; cán bộ
    quên chọn "Đối tượng thực hiện" trong sidebar thì bốn ô đó sẽ không bao giờ được điền.
    """
    if conv.get("authorization_page"):
        return "authorized_person"
    return str(conv.get("execution_subject") or "self")


def _owner_pipeline_options(conv: dict, owner_context: dict) -> dict:
    """Only the authorized branch may carry authorization context into OCR/LLM."""
    options = {"ownerContext": owner_context}
    if _execution_subject_for_owner(conv) == "authorized_person":
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


def _start_recorder(kind: str, conv_id: str, sid: str, procedure_key: str):
    """Recorder cho một lượt chạy nền; mốc 0 = lúc pipeline bắt đầu (không phải request chat).

    ``fresh`` vì task nền kế thừa context của request đã spawn nó.
    """
    return mon.start(kind, "handfree", origin=time.perf_counter(), fresh=True,
                     conversation_id=conv_id, dossier_id=conv_id, upload_session_id=sid,
                     procedure=procedure_key, steps_only=kind == "owner_info")


def _finish_recorder(rec, request_id: str | None) -> None:
    """Mốc kết quả đã tới extension (sau broadcast) rồi đặt lịch ghi chi tiết ở nền."""
    if rec is None:
        return
    rec.mark_wait_end()
    monitor_persist.schedule(rec, request_id or f"hf_{rec.kind}_{rec.meta.get('conversation_id')}")


def _fail_recorder(rec, exc: Exception) -> None:
    if rec is not None:
        rec.set_outcome("error")
        rec.error(f"{type(exc).__name__}: {exc}")


def _note_result(rec, result: dict) -> None:
    if rec is None:
        return
    for err in result.get("errors") or []:
        rec.error(err)
    if result.get("errors"):
        rec.set_outcome("partial")


def _session_files(sess: dict) -> list[dict]:
    """Dựng lại payload {name,type,dataUrl} từ file đã lưu trên disk theo phiên."""
    return _session_files_with_fids(sess)[0]


def _session_files_with_fids(sess: dict) -> tuple[list[dict], list[str]]:
    """Như `_session_files`, kèm fid của từng phần tử (cùng thứ tự) để ánh xạ ngược fileIndex → tệp phiên."""
    out, fids = [], []
    for f in sess.get("files", []):
        data_url = up_store.file_to_data_url(sess["_id"], f)
        if data_url:
            out.append({"name": f["name"], "type": f.get("type") or "image/jpeg",
                        "dataUrl": data_url, "role": ""})
            fids.append(f["fid"])
    return out, fids


async def _store_shrunk_files(sid: str, fids: list[str], replace_files: dict | None) -> dict | None:
    """Bản nén của planner (`replaceFiles`, khóa = fileIndex) → lưu vào phiên, trả {fid gốc: {fid, name, type}}.

    Extension trợ lý tự kéo tệp từ phiên theo fid, nên bản nén phải nằm trong phiên chứ không đi kèm lệnh
    (lệnh được lưu vào hội thoại trên Mongo, nhét base64 vài MB vào đó là phình doc).
    """
    metas, by_source = [], {}
    for index, item in (replace_files or {}).items():
        i = int(index)
        if not (0 <= i < len(fids)) or not item.get("dataUrl"):
            continue
        data_url = str(item["dataUrl"])
        raw = base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)
        name = str(item.get("name") or "tai-lieu.pdf")
        meta = {"fid": up_store.new_file_id(name), "name": name, "type": item.get("type") or "application/pdf",
                "size": len(raw), "source_fid": fids[i]}
        up_store.save_file_bytes(sid, meta["fid"], raw)
        metas.append(meta)
        by_source[fids[i]] = {k: meta[k] for k in ("fid", "name", "type")}
    await up_store.set_shrunk_files(sid, metas)
    return by_source or None


async def run_process(conv_id: str, sid: str, procedure_key: str) -> None:
    """OCR + trích field (state filling). Xong → conv.fields + WS `fields_ready`."""
    rec = _start_recorder("autofill", conv_id, sid, procedure_key)
    try:
        with mon.span("pre.load"):
            sess = await up_store.get(sid)
            proc = get_procedure(procedure_key)
            pipeline = get_pipeline(procedure_key)
            if not sess or not proc or not pipeline:
                raise RuntimeError("Thiếu phiên/thủ tục/pipeline.")
            files = _session_files(sess)
        if not files:
            raise RuntimeError("Phiên không còn file nào.")

        files_by_role = {"": files}  # mode agent: không gắn role, BE tự suy luận
        with mon.span("pre.prepare"):
            conv = await conv_store.get(conv_id)
            options: dict = {}
            if conv and conv.get("form_context"):
                options["formContext"] = dict(conv["form_context"])
            if proc.get("review"):
                options["_review"] = True
            owner_user = await _load_owner_user(conv, sess)
            options = with_account_process_options(options, owner_user, procedure_key)
            options = with_tthn_account_process_options(options, owner_user, procedure_key)
            options = with_gpxd_account_process_options(options, owner_user, procedure_key)
            options = with_mai_tang_htxh_account_process_options(options, owner_user, procedure_key)
            options = with_hkd_account_process_options(options, owner_user, procedure_key)
            options = with_cai_chinh_account_process_options(options, owner_user, procedure_key)

        t_pipe = time.monotonic()
        async with mon.span("pipeline", procedure=procedure_key):
            result = await pipeline(files_by_role, options)
            if rec is not None:
                rec.close_gap("agent_end", "post.mapper")
        pipe_ms = int((time.monotonic() - t_pipe) * 1000)
        _note_result(rec, result)

        # Bbox review (docs/06 §2.2): lưu theo conversation_id để FE xem lại vùng ảnh.
        review_data = result.pop("_review", None)
        if review_data:
            try:
                from app.review import store as review_store
                with mon.span("persist.review"):
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
        mon.output("response", {"fields": conv["fields"]})
        # Trace kênh sidebar (kèm ảnh — consent v1.1): giữ request_id để fill_report
        # thật từ FE gắn vào đúng trace.
        with mon.span("persist.db"):
            conv["trace_request_id"] = await tracing.record_process(
                conv, procedure_key, proc, files, result, pipe_ms, rec=rec,
            )
            await conv_store.save(conv)
        await broadcast(sid, {"type": "fields_ready", "count": len(conv["fields"])})
        _finish_recorder(rec, conv["trace_request_id"])
        # Tách chặng để soi chỗ chậm: review-bbox không có đồng hồ riêng
        # → xấp xỉ = pipeline - (ocr + llm).
        stats = result.get("stats") or {}
        ocr_ms, llm_ms = stats.get("ocr_latency_ms") or 0, stats.get("llm_latency_ms") or 0
        logger.info("[pipeline] process xong (%s): %d fields — ocr=%dms llm=%dms review~%dms pipeline=%dms",
                    conv_id, len(conv["fields"]), ocr_ms, llm_ms, max(0, pipe_ms - ocr_ms - llm_ms), pipe_ms)
    except Exception as e:  # noqa: BLE001 — lỗi pipeline phải ra bot, không nuốt
        logger.exception("[pipeline] process lỗi (%s)", conv_id)
        _fail_recorder(rec, e)
        conv = await conv_store.get(conv_id)
        error_request_id = None
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            error_request_id = await tracing.record_error(conv, procedure_key, "autofill", str(e), rec=rec)
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})
        _finish_recorder(rec, error_request_id)


async def run_business_registration(conv_id: str, sid: str, procedure_key: str) -> None:
    """Chuẩn bị trọn gói cho HkdOnline: 8 trang + kế hoạch đính kèm.

    Cổng hộ kinh doanh reload toàn trang sau từng lần lưu nên extension phải nhận toàn bộ
    dữ liệu trước khi khởi động state machine. Giữ hai pipeline nghiệp vụ độc lập như
    Auto-fill, nhưng chỉ phát một sự kiện ``business_ready`` khi cả hai đã sẵn sàng.
    """
    rec = _start_recorder("autofill", conv_id, sid, procedure_key)
    rec_attach = None
    try:
        with mon.span("pre.load"):
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
        async with mon.span("pipeline", procedure=procedure_key):
            process_result = await pipeline({"": raw_files}, process_options)
            if rec is not None:
                rec.close_gap("agent_end", "post.mapper")
        process_ms = int((time.monotonic() - t_process) * 1000)
        _note_result(rec, process_result)

        # Lượt đính kèm là một trace riêng (kind=attach) → recorder riêng, mốc 0 = lúc bắt đầu lập kế hoạch.
        rec_attach = _start_recorder("attach", conv_id, sid, procedure_key)
        file_items = [FileItem(**item) for item in raw_files]
        async with mon.span("post.plan", procedure=procedure_key):
            attach_result = await attach_fn(file_items, {}, session=None)
        _note_result(rec_attach, attach_result)

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
        conv["attach_fail_streak"] = 0  # kế hoạch MỚI → cho watcher tự đính lại từ đầu
        conv["pipeline_status"] = "business_ready"
        conv["pipeline_error"] = ""
        if rec_attach is not None:
            rec_attach.output("plan", conv["attach_plan"])
            rec_attach.output("extracted", attach_result.get("extracted"))
        if rec is not None:
            rec.output("response", {"fields": conv["fields"], "pages": pages,
                                    "businessFlow": conv["business_flow"]})
        with mon.span("persist.db"):
            conv["trace_request_id"] = await tracing.record_process(
                conv, procedure_key, proc, raw_files, process_result, process_ms, rec=rec
            )
            conv["attach_trace_request_id"] = await tracing.record_attach(
                conv, procedure_key, proc, raw_files, attach_result, rec=rec_attach
            )
            await conv_store.save(conv)
        await broadcast(sid, {
            "type": "business_ready",
            "pages": len(pages),
            "attachments": len(conv["attach_plan"]),
        })
        _finish_recorder(rec, conv["trace_request_id"])
        _finish_recorder(rec_attach, conv["attach_trace_request_id"])
        logger.info(
            "[pipeline] HKD sẵn sàng (%s): %d trang, %d tệp đính kèm",
            conv_id, len(pages), len(conv["attach_plan"]),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] HKD lỗi (%s)", conv_id)
        failed = rec_attach or rec
        _fail_recorder(failed, e)
        conv = await conv_store.get(conv_id)
        error_request_id = None
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            error_request_id = await tracing.record_error(
                conv, procedure_key, "business_registration", str(e), rec=failed)
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})
        _finish_recorder(failed, error_request_id)


async def run_owner_info(conv_id: str, sid: str, procedure_key: str) -> None:
    """Extract the matched owner's fields before the main declaration page."""
    # Không ghi traces (kind mới sẽ lẫn vào cách đếm hồ sơ cũ) — chỉ trace_steps cho web Monitor.
    rec = _start_recorder("owner_info", conv_id, sid, procedure_key)
    try:
        with mon.span("pre.load"):
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

        execution_subject = _execution_subject_for_owner(conv)
        # Nhánh bản thân tuyệt đối không truyền context ủy quyền vào pipeline/prompt.
        pipeline_options = _owner_pipeline_options(conv, owner_context)
        async with mon.span("pipeline", procedure=procedure_key):
            result = await pipeline({"": files}, pipeline_options)
            if rec is not None:
                rec.close_gap("agent_end", "post.mapper")
        _note_result(rec, result)
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
        mon.output("response", {"owner_fields": plan, "owner_match": conv["owner_match"]})
        with mon.span("persist.db"):
            await conv_store.save(conv)
        await broadcast(sid, {"type": "owner_fields_ready", "count": len(plan)})
        _finish_recorder(rec, None)
        logger.info("[pipeline] owner info xong (%s): matched=%s fields=%d",
                    conv_id, bool(conv["owner_match"].get("matched")), len(plan))
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] owner info lỗi (%s)", conv_id)
        _fail_recorder(rec, e)
        conv = await conv_store.get(conv_id)
        error_request_id = None
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            error_request_id = await tracing.record_error(conv, procedure_key, "owner_info", str(e), rec=rec)
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})
        _finish_recorder(rec, error_request_id)


async def run_attach(conv_id: str, sid: str, procedure_key: str,
                     options: dict | None = None) -> None:
    """Lập kế hoạch đính kèm (state attaching). Xong → conv.attach_plan + WS `attach_ready`."""
    rec = _start_recorder("attach", conv_id, sid, procedure_key)
    try:
        with mon.span("pre.load"):
            sess = await up_store.get(sid)
            attach_fn = get_attach_pipeline(procedure_key)
            if not sess or not attach_fn:
                raise RuntimeError("Thiếu phiên hoặc pipeline đính kèm.")
            raw_files, raw_fids = _session_files_with_fids(sess)
            files = [FileItem(**f) for f in raw_files]
        if not files:
            raise RuntimeError("Phiên không còn file nào.")

        attach_options = dict(options or {})
        from app.channels.handfree.chat import guided_steps as guided

        proc_cfg = get_procedure(procedure_key) or {}
        auth_key = guided.authorization_doc_key(proc_cfg)
        # Gác bằng CHÍNH checklist của phiên, không chỉ bằng khai báo của thủ tục: phiên của
        # bản extension cũ chỉ có một ô nên không bao giờ có ô giấy ủy quyền, và mọi tệp đều
        # đã có loại — nhưng dựa vào dây chuyền đó là dựa vào thứ ở xa, dễ đứt khi sửa chỗ khác.
        session_keys = {str(d.get("key") or "") for d in sess.get("required_docs") or []}
        if auth_key and auth_key in session_keys:
            # KHÔNG được đính vào thành phần hồ sơ:
            #  - giấy ủy quyền: nó có ô riêng ở bước chủ hồ sơ, không phải giấy đem chứng thực;
            #  - tệp chưa nhận ra loại: với thủ tục này bộ phân loại có sẵn ô "giấy tờ khác" nên
            #    để trống loại nghĩa là nó ĐÃ TỪ CHỐI (giấy ủy quyền không đúng người) — đính
            #    vào là đem giấy của cặp người khác đi chứng thực.
            attach_options["excludeFileNames"] = [
                str(f.get("name") or "") for f in sess.get("files", [])
                if f.get("doc_key") == auth_key or not f.get("doc_key")
            ]
        if attach_options.get("excludeIdentityDocuments"):
            # Đã phân loại lúc upload thì biết ĐÍCH DANH tệp nào là căn cước của chủ hồ sơ —
            # chính xác hơn để planner tự đoán lại theo loại giấy tờ nó nhận ra.
            owner_keys = guided.owner_doc_keys(proc_cfg)
            attach_options["identityFileNames"] = [
                str(f.get("name") or "") for f in sess.get("files", [])
                if f.get("doc_key") in owner_keys
            ]
        # Tài khoản chủ phiên quyết các cấu hình theo xã (STT1 ảo Hải Châu, bỏ Tờ khai Nghĩa Hưng,
        # bỏ Tờ khai khai sinh Nghĩa Lộ).
        with mon.span("pre.prepare"):
            owner_user = await _load_owner_user(await conv_store.get(conv_id), sess)
            attach_options = with_account_attach_options(attach_options, owner_user, procedure_key)
            attach_options = with_nghia_lo_attach_options(attach_options, owner_user, procedure_key)
        # Bọc cả planner: OCR/LLM bên trong tự tách thành bước riêng; phần còn lại = luật planner.
        async with mon.span("post.plan", procedure=procedure_key):
            result = await attach_fn(files, attach_options, session=None)
        _note_result(rec, result)
        # Cổng giới hạn dung lượng (DVC quốc gia mới < 2 MB): lấy bản nén ra khỏi result trước khi ghi trace.
        async with mon.span("post.shrunk"):
            replace_by_fid = await _store_shrunk_files(sid, raw_fids, result.pop("replaceFiles", None))

        conv = await conv_store.get(conv_id)
        if not conv:
            return
        # STT1 nhận 1 file ẢO. HTTP router auto-fill gọi sẵn; handfree đi qua chat pipeline nên
        # phải gọi Ở ĐÂY. Account/thủ tục khác → no-op (directive None), plan giữ nguyên.
        with mon.span("post.stt1"):
            result = apply_stt1_virtual_copy(result, owner_user, procedure_key)
        if rec is not None:
            rec.output("plan", result.get("attachments"))
            rec.output("extracted", result.get("extracted"))
            rec.output("response", {"attach_plan": result.get("attachments"),
                                    "stt1VirtualCopy": result.get("stt1VirtualCopy")})
        conv["attach_plan"] = result.get("attachments", [])
        conv["attach_plan_stt1_virtual"] = result.get("stt1VirtualCopy")
        conv["attach_plan_replace_files"] = replace_by_fid
        conv["attach_errors"] = result.get("errors", [])
        conv["attach_fail_streak"] = 0  # kế hoạch MỚI → cho watcher tự đính lại từ đầu
        conv["attach_action_in_progress"] = False
        conv["attach_action_dispatch_id"] = ""
        conv["attach_action_lease_until"] = None
        conv["pipeline_status"] = "attach_ready"
        proc = get_procedure(procedure_key) or {}
        with mon.span("persist.db"):
            conv["attach_trace_request_id"] = await tracing.record_attach(
                conv, procedure_key, proc, raw_files, result,
                split=(bool(attach_options.get("splitMode"))
                       if "splitMode" in attach_options else None),
                rec=rec)
            await conv_store.save(conv)
        await broadcast(sid, {"type": "attach_ready", "count": len(conv["attach_plan"])})
        _finish_recorder(rec, conv["attach_trace_request_id"])
        logger.info("[pipeline] attach plan xong (%s): %d mục", conv_id, len(conv["attach_plan"]))
    except Exception as e:  # noqa: BLE001
        logger.exception("[pipeline] attach lỗi (%s)", conv_id)
        _fail_recorder(rec, e)
        conv = await conv_store.get(conv_id)
        error_request_id = None
        if conv:
            conv["pipeline_status"] = "error"
            conv["pipeline_error"] = str(e)[:300]
            await conv_store.save(conv)
            error_request_id = await tracing.record_error(conv, procedure_key, "attach", str(e), rec=rec)
        await broadcast(sid, {"type": "pipeline_error", "message": str(e)[:200]})
        _finish_recorder(rec, error_request_id)


def spawn(coro) -> None:
    """Chạy nền trong event loop hiện tại (uvicorn) — flow không chờ pipeline."""
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda t: t.exception())  # nuốt cảnh báo un-retrieved (đã log trong coro)
