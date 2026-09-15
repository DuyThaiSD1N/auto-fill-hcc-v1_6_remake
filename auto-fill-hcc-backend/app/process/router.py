import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from app.audit import service as audit
from app.core.deps import require_auth
from app.core.errors import AppError
from app.dossiers import repo as dossiers_repo
from app.dossiers.options import dossier_id_from_options
from app.process import requests_repo
from app.process.schemas import ProcessReq, ProcessResp
from app.process.service import execute_process, prepare_process
from app.procedures.registry import get_pipeline, get_procedure
from app.review.access import create_review_capability
from app.storage.files import save_request_files
from app.traces import repo as traces_repo
from app.traces.applicant import resolve_applicant_name
from app.traces.key_fields import count_key_fields
from app.traces.metadata import build_process_trace_attachments

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["process"])

@router.post("/process", response_model=ProcessResp)
async def process(body: ProcessReq, background: BackgroundTasks,
                  user: dict = Depends(require_auth)):
    request_id = traces_repo.new_request_id()
    created_at = datetime.now(timezone.utc)

    proc = get_procedure(body.procedure)
    pipeline = get_pipeline(body.procedure)
    prepared = prepare_process(
        body,
        proc=proc,
        pipeline=pipeline,
        include_review=True,
    )
    total_bytes = prepared.total_bytes
    ocr_provider = prepared.ocr_provider

    try:
        result = await execute_process(prepared)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        # Lỗi pipeline: ghi audit/bản ghi lỗi ở NỀN (không chặn việc trả lỗi cho FE).
        background.add_task(_persist_error, request_id, created_at, user, body,
                            total_bytes, "PIPELINE_ERROR")
        raise AppError("PIPELINE_ERROR", f"Lỗi xử lý: {e}", 500)

    # Pop dữ liệu rà soát khỏi result để không lọt ra FE (lưu ở nền bên dưới).
    review_data = result.pop("_review", None)
    review_token = create_review_capability(request_id) if review_data else None

    # TẤT CẢ việc lưu vết (disk + 4 lượt Mongo) đẩy sang NỀN: fields đã sẵn sàng ngay đây,
    # người dùng KHÔNG cần chờ audit/trace/finish ghi xong. Cắt phần "im lặng" sau OCR+LLM.
    background.add_task(_persist_success, request_id, created_at, user, body, proc,
                        total_bytes, ocr_provider, result, review_data)

    return {
        "sessionId": request_id,
        "requestId": request_id,
        "reviewToken": review_token,
        "fields": result["fields"],
        "extracted": result.get("extracted", {}),
        "stats": result.get("stats", {}),
        "errors": result.get("errors", []),
        "pages": result.get("pages"),
        "businessFlow": result.get("businessFlow"),
    }


async def _touch_dossier(dossier_id, user, procedure, proc, created_at, applicant_name=None) -> None:
    """Ghi/cập nhật hồ sơ Auto Fill trong `dossiers`. Không có dossierId (bản cũ) → bỏ qua."""
    if not dossier_id:
        return
    await dossiers_repo.upsert_started(
        dossier_id=dossier_id, user_id=str(user.get("id") or ""),
        username=user.get("username"), name=user.get("name"),
        procedure=procedure, procedure_label=proc.get("label"),
        province=user.get("tinh"), ward=user.get("xa"),
        started_at=created_at, experience="autofill", applicant_name=applicant_name,
    )


async def _persist_success(request_id, created_at, user, body, proc, total_bytes,
                           ocr_provider, result, review_data) -> None:
    """Lưu vết 1 request thành công — chạy NỀN sau khi đã trả response.

    Toàn bộ best-effort: lỗi lưu KHÔNG ảnh hưởng kết quả người dùng đã nhận.
    """
    dossier_id = dossier_id_from_options(body.options)
    # 1) Dữ liệu rà soát bbox (nếu có) → LƯU ĐẦU TIÊN: FE gọi /review ngay sau khi điền xong form,
    #    ưu tiên ghi trước để card "Xem trên ảnh" kịp có dữ liệu (né đua với FE).
    if review_data:
        try:
            from app.review import store as review_store
            await asyncio.to_thread(review_store.save_review, request_id,
                                    review_data["sources"], review_data["images"])
        except Exception as e:  # noqa: BLE001
            logger.warning("Nền: lưu review thất bại (%s): %s", request_id, e)

    # 2) Lưu file xuống disk (đồng bộ → to_thread để không chặn event loop) + bản ghi request.
    doc_id: str | None = None
    files_meta: list[dict] = []
    try:
        files_meta = await asyncio.to_thread(save_request_files, request_id, created_at, body.files)
        doc_id = await requests_repo.create_request(
            request_id=request_id, created_at=created_at, user_id=user["id"],
            procedure=body.procedure, options=body.options or {}, files_meta=files_meta,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Nền: lưu file/bản ghi request thất bại (%s): %s", request_id, e)

    # 3) Audit + finish + trace theo dõi.
    try:
        await audit.log_request(
            user_id=user["id"], request_id=request_id, procedure=body.procedure,
            files_count=len(body.files), total_bytes=total_bytes, status=200,
            stats=result.get("stats"),
        )
        await requests_repo.finish_request(
            doc_id, status="done", stats=result.get("stats"),
            fields_count=len(result.get("fields", [])),
            fields=result.get("fields", []),
            extracted=result.get("extracted", {}),
        )
        attachments = build_process_trace_attachments(files_meta)
        if not attachments:
            attachments = [{"name": f.name, "role": f.role, "sha256": None, "uses": 1}
                           for f in body.files]
        applicant_name = resolve_applicant_name(body.options or {}, result)
        kf_total, kf_filled = count_key_fields(body.procedure, result.get("fields", []))
        await traces_repo.create_trace(
            request_id=request_id, user_id=user["id"],
            username=user.get("username"), name=user.get("name"),
            applicant_name=applicant_name, attachments=attachments,
            stats_version=2, dossier_ids=[request_id],
            kind="autofill", key_fields_total=kf_total, key_fields_filled=kf_filled,
            stats=result.get("stats"), total_bytes=total_bytes,
            procedure=body.procedure, procedure_label=proc.get("label"),
            # Ưu tiên provider hiệu lực per-file từ pipeline ("both" nếu hỗn hợp); fallback theo option.
            ocr_provider=result.get("ocr_provider") or ocr_provider,
            ocr_text=result.get("ocr_text", ""), llm_output=result.get("llm_output"),
            fields_count=len(result.get("fields", [])), status="done",
            created_at=created_at,
            dossier_id=dossier_id,
        )
        # Mốc BẮT ĐẦU hồ sơ của Auto Fill = lượt process/đính kèm ĐẦU TIÊN (upsert_started chỉ
        # ghi started_at lần đầu). Extension bản cũ không gửi dossierId → bỏ qua, không vỡ.
        await _touch_dossier(dossier_id, user, body.procedure, proc, created_at, applicant_name)
    except Exception as e:  # noqa: BLE001
        logger.warning("Nền: ghi audit/trace thất bại (%s): %s", request_id, e)


async def _persist_error(request_id, created_at, user, body, total_bytes, error_code) -> None:
    """Lưu vết 1 request lỗi pipeline — chạy NỀN. Best-effort."""
    try:
        files_meta = await asyncio.to_thread(save_request_files, request_id, created_at, body.files)
        doc_id = await requests_repo.create_request(
            request_id=request_id, created_at=created_at, user_id=user["id"],
            procedure=body.procedure, options=body.options or {}, files_meta=files_meta,
        )
        await audit.log_request(
            user_id=user["id"], request_id=request_id, procedure=body.procedure,
            files_count=len(body.files), total_bytes=total_bytes, status=500,
            error_code=error_code,
        )
        await requests_repo.finish_request(doc_id, status="error", error_code=error_code)
    except Exception as e:  # noqa: BLE001
        logger.warning("Nền: ghi bản ghi lỗi thất bại (%s): %s", request_id, e)
