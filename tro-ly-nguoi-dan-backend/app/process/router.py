import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.audit import service as audit
from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.process import requests_repo
from app.process.schemas import ProcessReq, ProcessResp
from app.procedures.registry import get_pipeline, get_procedure
from app.services import ocr
from app.storage.files import save_request_files
from app.traces import repo as traces_repo
from app.traces.applicant import resolve_applicant_name
from app.traces.key_fields import count_key_fields

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["process"])

_ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _is_allowed_file_type(file_item) -> bool:
    if file_item.type in _ALLOWED_TYPES:
        return True
    name = (file_item.name or "").lower()
    return name.endswith(".docx") and file_item.type in {"", "application/octet-stream"}


def _data_url_bytes(data_url: str) -> int:
    """Ước lượng số byte file gốc từ độ dài phần base64."""
    if "," in data_url:
        b64 = data_url.split(",", 1)[1]
    else:
        b64 = data_url
    return (len(b64) * 3) // 4


@router.post("/process", response_model=ProcessResp)
async def process(body: ProcessReq, user: dict = Depends(require_auth)):
    request_id = "req_" + uuid.uuid4().hex[:12]
    created_at = datetime.now(timezone.utc)

    proc = get_procedure(body.procedure)
    pipeline = get_pipeline(body.procedure)
    if not proc or not pipeline:
        raise AppError("UNKNOWN_PROCEDURE", f"Thủ tục không hợp lệ: {body.procedure}", 400)

    if not body.files:
        raise AppError("NO_FILES", "Không có file nào", 400)

    max_file = settings.max_file_size_mb * 1024 * 1024
    max_total = settings.max_total_payload_mb * 1024 * 1024
    total_bytes = 0
    is_agent = proc.get("mode") == "agent"  # agent: không gắn role, BE tự suy luận
    valid_roles = {r["value"] for r in proc["roles"]}

    files_by_role: dict[str, list[dict]] = {}
    for f in body.files:
        if not _is_allowed_file_type(f):
            raise AppError("BAD_FILE_TYPE", f"Loại file không hỗ trợ: {f.type}", 400)
        if not is_agent and f.role not in valid_roles:
            raise AppError("BAD_ROLE", f"Role không hợp lệ cho thủ tục: {f.role}", 400)
        size = _data_url_bytes(f.dataUrl)
        if size > max_file:
            raise AppError("FILE_TOO_LARGE", f"File {f.name} vượt quá {settings.max_file_size_mb}MB", 413)
        total_bytes += size
        files_by_role.setdefault(f.role, []).append(
            {"name": f.name, "type": f.type, "dataUrl": f.dataUrl,
             "hasHandwriting": bool(f.hasHandwriting)}
        )

    if total_bytes > max_total:
        raise AppError("PAYLOAD_TOO_LARGE",
                       f"Tổng payload vượt quá {settings.max_total_payload_mb}MB", 413)

    # Lưu file xuống disk + tạo bản ghi request (id mới + create_time). Best-effort:
    # nếu lưu lỗi vẫn xử lý OCR bình thường.
    doc_id: str | None = None
    try:
        files_meta = save_request_files(request_id, created_at, body.files)
        doc_id = await requests_repo.create_request(
            request_id=request_id, created_at=created_at, user_id=user["id"],
            procedure=body.procedure, options=body.options or {}, files_meta=files_meta,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Lưu file/bản ghi request thất bại (%s): %s", request_id, e)

    # Chọn OCR provider theo option "Có bản viết tay": có -> Vintern, không -> raw (mặc định).
    ocr_provider = ocr.provider_from_options(body.options)
    ocr.use_provider(ocr_provider)

    # Thủ tục bật rà soát bbox → báo pipeline chụp tokens+bbox (Kiểu A, tính lúc process).
    pipeline_options = dict(body.options or {})
    if proc.get("review"):
        pipeline_options["_review"] = True

    try:
        result = await pipeline(files_by_role, pipeline_options)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        await audit.log_request(
            user_id=user["id"], request_id=request_id, procedure=body.procedure,
            files_count=len(body.files), total_bytes=total_bytes, status=500,
            error_code="PIPELINE_ERROR",
        )
        await requests_repo.finish_request(doc_id, status="error", error_code="PIPELINE_ERROR")
        raise AppError("PIPELINE_ERROR", f"Lỗi xử lý: {e}", 500)

    # Lưu dữ liệu rà soát (sources + ảnh baked) theo request_id để endpoint /review đọc lại.
    # Best-effort: lỗi lưu không chặn response autofill. Pop khỏi result để không lọt ra FE.
    review_data = result.pop("_review", None)
    if review_data:
        try:
            from app.review import store as review_store
            review_store.save_review(request_id, review_data["sources"], review_data["images"])
        except Exception as e:  # noqa: BLE001
            logger.warning("Lưu review thất bại (%s): %s", request_id, e)

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

    # Trace cho màn theo dõi: tài khoản (phường), người làm thủ tục, file đính kèm,
    # thủ tục, OCR text gộp, JSON LLM parse được.
    attachments = [{"name": f.name, "role": f.role} for f in body.files]
    applicant_name = resolve_applicant_name(body.options or {}, result)
    kf_total, kf_filled = count_key_fields(body.procedure, result.get("fields", []))
    await traces_repo.create_trace(
        request_id=request_id, user_id=user["id"],
        username=user.get("username"), name=user.get("name"),
        applicant_name=applicant_name, attachments=attachments,
        kind="autofill", key_fields_total=kf_total, key_fields_filled=kf_filled,
        procedure=body.procedure, procedure_label=proc.get("label"),
        # Ưu tiên provider hiệu lực per-file từ pipeline ("both" nếu hỗn hợp); fallback theo option.
        ocr_provider=result.get("ocr_provider") or ocr_provider,
        ocr_text=result.get("ocr_text", ""), llm_output=result.get("llm_output"),
        fields_count=len(result.get("fields", [])), status="done",
        created_at=created_at,
    )

    return {
        "sessionId": request_id,
        "requestId": request_id,
        "fields": result["fields"],
        "extracted": result.get("extracted", {}),
        "stats": result.get("stats", {}),
        "errors": result.get("errors", []),
        "pages": result.get("pages"),
    }
