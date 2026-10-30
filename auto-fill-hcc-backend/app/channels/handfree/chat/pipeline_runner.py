"""Cầu nối hội thoại ↔ pipeline OCR/LLM (docs/06 §2.1).

Chạy pipeline NỀN (10-60s) rồi báo kết quả qua WS phiên upload — FE nhận event
`fields_ready`/`attach_ready` thì gọi lại /assistant/chat lấy actions. KHÔNG mở
API /process /attachments/plan cho FE (nguyên tắc 1 cửa — docs/03 §2.3).

Hợp đồng fields/attachments GIỮ NGUYÊN của auto-fill (docs/00 §4) — fill engine
extension chạy không sửa.
"""
import asyncio
import base64
import functools
import logging
import time
from datetime import datetime, timezone

from app.account_settings import service as account_settings
from app.channels.handfree.chat import store as conv_store
from app.channels.handfree.chat import tracing
from app.db.mongo import get_db
from app.monitor import persist as monitor_persist
from app.monitor import recorder as mon
from app.channels.handfree.procedure_registry import (
    case_pipeline_options,
    get_attach_pipeline,
    get_owner_info_pipeline,
    get_pipeline,
    get_procedure,
)
from app.pipelines.chung_thuc_ban_sao.attach.stt1_virtual import apply_stt1_virtual_copy
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import MAX_FILE_BYTES, shrink_file
from app.pipelines.cai_chinh_dvc_moi.process.mapper import (
    with_account_process_options as with_cai_chinh_account_process_options,
)
from app.pipelines.cap_giay_phep_xay_dung.process.mapper import (
    with_account_process_options as with_gpxd_account_process_options,
)
from app.pipelines.dang_ky_kinh_doanh.process.mapper import (
    with_account_process_options as with_hkd_account_process_options,
)
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.mapper import (
    with_account_process_options as with_mai_tang_htxh_account_process_options,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.process.mapper import (
    with_account_process_options as with_giao_dat_ninh_binh_account_process_options,
)
from app.pipelines.khai_sinh_dang_ky_lai.process.mapper import (
    with_account_process_options as with_khai_sinh_dang_ky_lai_account_process_options,
)
from app.pipelines.khai_sinh_lien_thong.attach.planner import with_nghia_lo_attach_options
from app.pipelines.cap_giay_phep_xay_dung.attach.planner import (
    with_account_attach_options as with_gpxd_attach_options,
)
from app.pipelines.khai_sinh_lien_thong.process.mapper import (
    with_account_process_options as with_khai_sinh_lien_thong_account_process_options,
)
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.mapper import (
    with_account_process_options as with_tro_cap_nhan_cham_soc_account_process_options,
)
from app.pipelines.xac_nhan_tthn_dvc_moi.attach.nghia_hung import with_account_attach_options
from app.pipelines._shared.lao_cai_tach_giay_to import always_split, plan_with_split
from app.pipelines._shared.lao_cai_tach_giay_to import with_account_attach_options as with_cam_duong_attach_options
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


def _bac_ninh_authorized_block(proc: dict, conv: dict | None) -> dict | None:
    """Khối "Thông tin trong trường hợp được ủy quyền" của cổng Bắc Ninh cần điền ở lượt này không.

    Chỉ khi công dân chọn đối tượng thực hiện có ủy quyền VÀ extension biết tick ô bổ sung + chọn loại
    đối tượng trước khi điền — bản cũ điền trơn thì mọi ô doiTuongKhac* rơi vào unmatched.
    """
    config = proc.get("bacNinhAuthorizedPerson") or {}
    caps = (conv or {}).get("client_capabilities") or {}
    if not config or caps.get("supportsBacNinhAuthorizedPerson") is not True:
        return None
    from app.channels.handfree.chat import bac_ninh

    choice = bac_ninh.authorized_choice(conv or {}, proc)
    if choice is not None:
        # Luồng tab Bắc Ninh: công dân đã trả lời ngay ở tab "Chọn cơ quan tiếp nhận" có điền khối này không.
        return config if choice else None
    subject = str((conv or {}).get("execution_subject") or "self")
    return config if subject in (config.get("executionSubjects") or []) else None


async def _run_bac_ninh_authorized(pipeline, files_by_role: dict, options: dict, config: dict) -> dict:
    """Lượt purpose="authorized_person" (logic điền của auto-fill) → ô đánh dấu loại đối tượng + doiTuongKhac*.

    Lỗi ở lượt này không được làm hỏng lệnh điền đơn: trả về lỗi để ghi trace, đơn vẫn điền.
    """
    try:
        res = await pipeline(files_by_role, {**options, "purpose": "authorized_person"})
    except Exception as e:  # noqa: BLE001
        logger.warning("[pipeline] lượt người ủy quyền Bắc Ninh lỗi: %s", e)
        return {"fields": [], "errors": [f"Không đọc được thông tin người ủy quyền: {str(e)[:200]}"]}
    fields = list(res.get("fields") or [])
    if fields:
        # Thủ tục đọc được loại bên ủy quyền (doanh nghiệp, tổ chức…) thì chọn đúng loại đó; không thì loại mặc định.
        fields.insert(0, {"name": "loaiDoiTuongKhac", "comp": "bn-doi-tuong-khac",
                          "value": res.get("authorizedSubject") or config["subjectOption"]})
    return {"fields": fields, "errors": list(res.get("errors") or [])}


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


# Lệnh đính kèm mang TOÀN BỘ tệp của phiên sang trang trong MỘT tin nhắn của Chrome (trần cứng 64 MiB; base64 phình
# ~1,34 lần): 10 bản quét màu độ phân giải cao là vượt, tin bị trình duyệt chặn và trang "không nhận lệnh đính kèm".
# Tổng byte gốc vượt ngưỡng → nén các tệp nặng nhất (nấc ~5 MB giữ nét trước, vẫn quá thì xuống nấc của cổng
# ~1,9 MB) tới khi lọt; tệp planner đã nén sẵn để nguyên. Tổng dưới ngưỡng thì không đụng gì.
_ATTACH_MESSAGE_BUDGET = 40_000_000
_SHRINK_STEPS = (5_000_000, MAX_FILE_BYTES)


def _data_url_bytes(data_url: str) -> bytes:
    return base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)


async def _fit_attach_message(files: list[dict], replace_files: dict | None, errors: list) -> dict | None:
    replaced = dict(replace_files or {})
    sizes = {}
    for i, f in enumerate(files):
        if not f.get("dataUrl"):
            continue
        entry = replaced.get(str(i))
        sizes[i] = entry["bytes"] if entry and entry.get("bytes") else len(_data_url_bytes(f["dataUrl"]))
    total = sum(sizes.values())
    if total <= _ATTACH_MESSAGE_BUDGET:
        return replace_files
    for limit in _SHRINK_STEPS:
        for i in sorted(sizes, key=sizes.get, reverse=True):
            if total <= _ATTACH_MESSAGE_BUDGET:
                break
            if sizes[i] <= limit or (str(i) in (replace_files or {})):
                continue
            try:
                out, _label = await asyncio.to_thread(shrink_file, _data_url_bytes(files[i]["dataUrl"]), limit)
            except Exception as e:  # noqa: BLE001 — nén hỏng thì để bản gốc
                logger.warning("[attach] không nén được tệp %s: %s", files[i].get("name"), e)
                continue
            if len(out) >= sizes[i]:
                continue
            stem = (str(files[i].get("name") or "tai-lieu").rsplit(".", 1)[0]) or "tai-lieu"
            replaced[str(i)] = {"name": f"{stem}.pdf", "type": "application/pdf", "bytes": len(out),
                                "dataUrl": "data:application/pdf;base64," + base64.b64encode(out).decode("ascii")}
            total -= sizes[i] - len(out)
            sizes[i] = len(out)
        if total <= _ATTACH_MESSAGE_BUDGET:
            break
    if total > _ATTACH_MESSAGE_BUDGET:
        errors.append(f"Giấy tờ quá nặng (khoảng {total / 1e6:.0f} MB sau khi nén) — công dân scan lại nhẹ hơn "
                      "(ảnh xám / độ phân giải thấp hơn) hoặc bỏ bớt tệp không cần.")
    return replaced or None


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


# Tác vụ nền chạy ngay trong tiến trình BE (4 worker uvicorn): BE khởi động lại là tác vụ mất mà hồ sơ vẫn ghi
# pipeline_status="running". Tác vụ ghi nhịp tim vào collection riêng (không nằm trong bản ghi hội thoại — flow lưu
# hội thoại bằng replace_one sẽ ghi đè) để lượt đồng bộ sau khi nối lại (__event:pipeline_resync) biết mà chạy lại.
_HEARTBEAT_S = 10
_STALE_S = 45


async def _heartbeat(conv_id: str, kind: str) -> None:
    while True:
        try:
            await get_db().pipeline_heartbeats.update_one(
                {"_id": conv_id}, {"$set": {"kind": kind, "at": datetime.now(timezone.utc)}}, upsert=True)
        except Exception as e:  # noqa: BLE001 — nhịp tim lỗi không được làm hỏng tác vụ chính
            logger.warning("[pipeline] ghi nhịp tim lỗi (%s): %s", conv_id, e)
        await asyncio.sleep(_HEARTBEAT_S)


def _tracked(kind: str):
    def wrap(fn):
        @functools.wraps(fn)
        async def run(conv_id: str, *args, **kwargs):
            beat = asyncio.create_task(_heartbeat(conv_id, kind))
            try:
                return await fn(conv_id, *args, **kwargs)
            finally:
                beat.cancel()
                try:
                    await get_db().pipeline_heartbeats.delete_one({"_id": conv_id, "kind": kind})
                except Exception:  # noqa: BLE001
                    pass
        return run
    return wrap


async def last_heartbeat(conv_id: str) -> tuple[str, bool]:
    """(loại tác vụ gần nhất, còn sống). Không có bản ghi = không có tác vụ nào đang chạy cho hồ sơ này."""
    doc = await get_db().pipeline_heartbeats.find_one({"_id": conv_id}) or {}
    at = doc.get("at")
    if not isinstance(at, datetime):
        return str(doc.get("kind") or ""), False
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return str(doc.get("kind") or ""), (datetime.now(timezone.utc) - at).total_seconds() < _STALE_S


@_tracked("process")
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
            eform = (conv or {}).get("eform_running")
            if proc.get("declarationEforms") and isinstance(eform, dict):
                # Mẫu điện tử chốt lúc công dân bấm "Điền tờ khai": lượt chat đến sau (tờ khai vừa
                # đóng/đổi) có thể đã xoá formVariant khỏi form_context trước khi task này đọc.
                options["formContext"] = {**options.get("formContext", {}), **eform}
            if proc.get("review"):
                options["_review"] = True
            owner_user = await _load_owner_user(conv, sess)
            options = with_gpxd_account_process_options(options, owner_user, procedure_key)
            options = with_mai_tang_htxh_account_process_options(options, owner_user, procedure_key)
            options = with_hkd_account_process_options(options, owner_user, procedure_key)
            options = with_cai_chinh_account_process_options(options, owner_user, procedure_key)
            options = with_khai_sinh_dang_ky_lai_account_process_options(options, owner_user, procedure_key)
            options = with_khai_sinh_lien_thong_account_process_options(options, owner_user, procedure_key)
            options = with_tro_cap_nhan_cham_soc_account_process_options(options, owner_user, procedure_key)
            options = with_giao_dat_ninh_binh_account_process_options(options, owner_user, procedure_key)
            # Cài đặt theo tài khoản "Lấy người nộp theo tờ khai" — pipeline chưa hỗ trợ thì bỏ qua khoá này.
            if isinstance(owner_user, dict) and account_settings.resolve(owner_user)["submitterFromDeclaration"]:
                options["submitterMode"] = "owner_as_submitter"
            # Trường hợp giải quyết công dân đã chốt (vd nhà ở riêng lẻ / công trình) → ép nhánh
            # form cho mapper thay vì để nó tự đoán từ giấy tờ.
            options.update(case_pipeline_options(proc, conv))
            authorized = _bac_ninh_authorized_block(proc, conv)
            from app.channels.handfree.chat import bac_ninh

            if bac_ninh.account_phase(conv or {}, proc):
                # Trang hoàn thiện tài khoản Bắc Ninh: request tài khoản, neo đúng chủ tài khoản bằng họ tên + số định
                # danh cổng điền sẵn. Request đơn chạy ngầm cùng lúc để sang trang thủ tục điền ngay.
                pipeline = get_pipeline(bac_ninh.ACCOUNT_PROCEDURE)
                options = {"formContext": bac_ninh.account_context(conv)}
                authorized = None
                spawn(run_bac_ninh_prefill(conv_id, sid, procedure_key))

        t_pipe = time.monotonic()
        async with mon.span("pipeline", procedure=procedure_key):
            if authorized and proc.get("mode") == "attach":
                # Thủ tục chỉ đính kèm (vd hỗ trợ người cao tuổi): pipeline lõi chính là pipeline khối ủy quyền.
                result = await _run_bac_ninh_authorized(pipeline, files_by_role, options, authorized)
            elif authorized:
                # Hai lượt OCR/LLM độc lập trên cùng bộ giấy tờ → chạy song song cho đỡ chờ.
                result, extra = await asyncio.gather(
                    pipeline(files_by_role, options),
                    _run_bac_ninh_authorized(pipeline, files_by_role, options, authorized),
                )
                result["fields"] = [*(result.get("fields") or []), *extra["fields"]]
                result["errors"] = [*(result.get("errors") or []), *extra["errors"]]
            else:
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
        conv["fields_dispatched"] = False
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


# Kết quả request đơn chạy ngầm ở bước tài khoản Bắc Ninh: collection riêng (không ghi vào conversation — lượt chat
# đang chạy lưu lại cả hội thoại sẽ đè mất), xoá khi đã dùng, TTL dọn bản bỏ dở (app/db/indexes.py).
_PREFILL_WAIT_S = 600


async def run_bac_ninh_prefill(conv_id: str, sid: str, procedure_key: str) -> None:
    """Pipeline đơn (+ lượt người ủy quyền nếu thủ tục có) trên đúng bộ giấy tờ nhận ở bước tài khoản. Lượt ủy quyền
    chạy luôn vì câu hỏi có điền hay không đến sau; apply_bac_ninh_prefill chỉ ghép khi công dân chọn điền."""
    db = get_db().bac_ninh_prefill
    await db.replace_one({"_id": conv_id}, {"_id": conv_id, "status": "running", "at": datetime.now(timezone.utc)},
                         upsert=True)
    try:
        sess = await up_store.get(sid)
        proc = get_procedure(procedure_key)
        pipeline = get_pipeline(procedure_key)
        files = _session_files(sess) if sess else []
        conv = await conv_store.get(conv_id)
        if not files or not proc or not pipeline or not conv:
            raise RuntimeError("Thiếu phiên/thủ tục/pipeline.")
        files_by_role = {"": files}
        options: dict = {"formContext": dict(conv.get("form_context") or {})}
        options.update(case_pipeline_options(proc, conv))
        config = proc.get("bacNinhAuthorizedPerson") or {}
        caps = conv.get("client_capabilities") or {}
        t_pipe = time.monotonic()
        if config and caps.get("supportsBacNinhAuthorizedPerson") is True:
            result, extra = await asyncio.gather(
                pipeline(files_by_role, options),
                _run_bac_ninh_authorized(pipeline, files_by_role, options, config),
            )
        else:
            result, extra = await pipeline(files_by_role, options), {"fields": [], "errors": []}
        pipe_ms = int((time.monotonic() - t_pipe) * 1000)
        trace_id = await tracing.record_process(conv, procedure_key, proc, files, result, pipe_ms)
        await db.update_one({"_id": conv_id}, {"$set": {
            "status": "done", "fields": result.get("fields") or [], "authFields": extra["fields"],
            "extracted": result.get("extracted") or {}, "errors": [*(result.get("errors") or []), *extra["errors"]],
            "traceId": trace_id, "at": datetime.now(timezone.utc),
        }})
    except Exception as e:  # noqa: BLE001 — chạy ngầm hỏng thì apply_bac_ninh_prefill đọc lại như thường
        logger.warning("[pipeline] đọc ngầm đơn Bắc Ninh lỗi (%s): %s", conv_id, e)
        await db.update_one({"_id": conv_id}, {"$set": {"status": "error", "at": datetime.now(timezone.utc)}})


@_tracked("process")
async def apply_bac_ninh_prefill(conv_id: str, sid: str, procedure_key: str) -> None:
    """Sang trang thủ tục sau bước tài khoản: chờ kết quả đọc ngầm rồi phát fields_ready như một lượt process; không có /
    hỏng / quá hạn → đọc lại bằng run_process (giấy tờ vẫn là phiên cũ)."""
    db = get_db().bac_ninh_prefill
    deadline = time.monotonic() + _PREFILL_WAIT_S
    doc = await db.find_one({"_id": conv_id})
    while doc and doc.get("status") == "running" and time.monotonic() < deadline:
        await asyncio.sleep(1)
        doc = await db.find_one({"_id": conv_id})
    await db.delete_one({"_id": conv_id})
    if not doc or doc.get("status") != "done":
        await run_process.__wrapped__(conv_id, sid, procedure_key)
        return
    conv = await conv_store.get(conv_id)
    if not conv:
        return
    authorized = (conv.get("bac_ninh") or {}).get("authorized") is True
    conv["fields"] = [*(doc.get("fields") or []), *((doc.get("authFields") or []) if authorized else [])]
    conv["extracted"] = doc.get("extracted") or {}
    conv["pipeline_status"] = "fields_ready"
    conv["pipeline_error"] = ""
    conv["fields_dispatched"] = False
    if doc.get("traceId"):
        conv["trace_request_id"] = doc["traceId"]
    await conv_store.save(conv)
    await broadcast(sid, {"type": "fields_ready", "count": len(conv["fields"])})


@_tracked("business")
async def run_business_registration(conv_id: str, sid: str, procedure_key: str,
                                    attach_options: dict | None = None) -> None:
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
            attach_result = await attach_fn(file_items, attach_options or {}, session=None)
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
        # Kế hoạch lập theo cài đặt tách giấy tờ nào (cùng khóa với run_attach).
        conv["attach_plan_split_documents"] = (attach_options or {}).get("splitDocuments") is True
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


@_tracked("owner")
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
        conv["owner_fields_dispatched"] = False
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


@_tracked("attach")
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
            attach_options = with_gpxd_attach_options(attach_options, owner_user, procedure_key)
            attach_options = with_cam_duong_attach_options(attach_options, owner_user, procedure_key)
            # Cam Đường luôn tách giấy tờ — chỉ khi extension có engine cắt trang (sourceSegments).
            if always_split(attach_options) and attach_options.get("supportsSourceSegments") is True:
                attach_fn = functools.partial(plan_with_split, attach_fn)
        # Bọc cả planner: OCR/LLM bên trong tự tách thành bước riêng; phần còn lại = luật planner.
        async with mon.span("post.plan", procedure=procedure_key):
            result = await attach_fn(files, attach_options, session=None)
        _note_result(rec, result)
        # Cổng giới hạn dung lượng (DVC quốc gia mới < 2 MB): lấy bản nén ra khỏi result trước khi ghi trace.
        async with mon.span("post.shrunk"):
            replace_files = await _fit_attach_message(raw_files, result.pop("replaceFiles", None),
                                                      result.setdefault("errors", []))
            replace_by_fid = await _store_shrunk_files(sid, raw_fids, replace_files)

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
        # Kế hoạch lập theo cài đặt tách giấy tờ nào: đổi cài đặt rồi bấm "Đính kèm lại" thì lập lại.
        conv["attach_plan_split_documents"] = attach_options.get("splitDocuments") is True
        # Cùng lý do cho gộp/tách hồ sơ chứng thực: thiếu splitMode = kế hoạch không gắn chế độ.
        conv["attach_plan_attach_mode"] = (
            ("split" if attach_options.get("splitMode") is True else "merge")
            if "splitMode" in attach_options else None
        )
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
