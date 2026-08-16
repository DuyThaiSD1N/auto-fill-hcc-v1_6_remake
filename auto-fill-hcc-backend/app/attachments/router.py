import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.attachments.schemas import AttachmentPlanReq, AttachmentPlanResp
from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.process import requests_repo
from app.procedures.registry import get_attach_pipeline, get_procedure
from app.services import ocr
from app.storage.files import save_request_files
from app.traces import repo as traces_repo
from app.traces.applicant import resolve_applicant_name
from app.traces.metadata import build_attach_trace_metadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])

_ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
    "application/xml",
    "text/xml",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "video/mp4",
    "video/quicktime",
    # DOCX: đính nguyên file (luồng attach không OCR docx → xếp "other", tạo thành phần hồ sơ mới).
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _data_url_bytes(data_url: str) -> int:
    if "," in data_url:
        b64 = data_url.split(",", 1)[1]
    else:
        b64 = data_url
    return (len(b64) * 3) // 4


async def _save_attach_trace(
    body: AttachmentPlanReq, proc: dict, options: dict, result: dict, user: dict,
    total_bytes: int, request_id: str,
) -> None:
    """Lưu file xuống disk + bản ghi request + trace cho thủ tục đính kèm (attach-only).

    request_id do handler sinh & trả về FE (nút "Mã hỗ trợ") → dùng ĐÚNG id đó khi lưu trace.
    Best-effort: mọi lỗi ở đây không được làm hỏng response đính kèm.
    """
    created_at = datetime.now(timezone.utc)
    files_meta: list[dict] = []
    try:
        # Lưu file + bản ghi process_requests để trace detail xem được nội dung file (qua /traces/{id}/files).
        files_meta = save_request_files(request_id, created_at, body.files)
        await requests_repo.create_request(
            request_id=request_id, created_at=created_at, user_id=user["id"],
            procedure=body.procedure, options=options, files_meta=files_meta,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Lưu file/bản ghi request đính kèm thất bại (%s): %s", request_id, e)

    plan = result.get("attachments") or []
    applicant_name = resolve_applicant_name(options, result)
    # Lựa chọn "tách hồ sơ" popup gửi trong options (chỉ chứng thực bản sao/chữ ký có ô tick);
    # chỉ nhận bool thật để trace phân biệt được với "không rõ" (None — extension cũ).
    split = options.get("splitMode")
    split_value = split if isinstance(split, bool) else None
    trace_files_meta = files_meta or [
        {"name": f.name, "type": f.type, "role": f.role, "sha256": None}
        for f in body.files
    ]
    attachments, dossier_ids = build_attach_trace_metadata(
        request_id=request_id,
        session_id=str(options.get("sessionId") or options.get("requestId") or "").strip() or None,
        procedure=body.procedure,
        split=split_value is True,
        plan=plan,
        files_meta=trace_files_meta,
    )
    if not attachments:
        attachments = [
            {"name": f.name, "role": f.role, "sha256": None, "uses": 1}
            for f in body.files
        ]
    await traces_repo.create_trace(
        request_id=request_id, user_id=user["id"],
        username=user.get("username"), name=user.get("name"),
        applicant_name=applicant_name, attachments=attachments,
        split=split_value, stats_version=2, dossier_ids=dossier_ids,
        kind="attach",  # bước đính kèm — phân biệt với autofill trên màn trace
        stats=result.get("stats"), total_bytes=total_bytes,
        procedure=body.procedure, procedure_label=proc.get("label"),
        # Nhãn engine THẬT: OCR_BY_TIENGNOI bật → tiengnoi (vintern-v6); tắt → "raw" (→ Gemini nếu RAW_BY_GEMINI).
        ocr_provider=ocr.resolved_label(None if settings.ocr_by_tiengnoi else "raw"),
        ocr_text=result.get("ocr_text", ""),
        # Lưu kế hoạch đính kèm để xem chi tiết (file → tài liệu → ô/component đích).
        llm_output={"attachments": plan, "extracted": result.get("extracted")},
        fields_count=len(plan), status="done",
        created_at=created_at,
    )


@router.post("/plan", response_model=AttachmentPlanResp)
async def plan_attachments(body: AttachmentPlanReq, user: dict = Depends(require_auth)):
    proc = get_procedure(body.procedure)
    if not proc or (proc.get("mode") != "attach" and not proc.get("hasAttachmentStep")):
        raise AppError("UNKNOWN_ATTACHMENT_PROCEDURE", f"Thủ tục đính kèm không hợp lệ: {body.procedure}", 400)
    if not body.files:
        raise AppError("NO_FILES", "Không có file nào", 400)

    # Bước đính kèm luôn dùng OCR raw vnekyc, không phụ thuộc option "Có bản viết tay".
    ocr.use_provider("raw")

    max_file = settings.max_file_size_mb * 1024 * 1024
    max_total = settings.max_total_payload_mb * 1024 * 1024
    total_bytes = 0
    for f in body.files:
        # Chấp nhận theo mime HOẶC đuôi .docx (một số máy trả mime docx rỗng/octet-stream).
        if f.type not in _ALLOWED_TYPES and not (f.name or "").lower().endswith(".docx"):
            raise AppError("BAD_FILE_TYPE", f"Loại file không hỗ trợ: {f.type}", 400)
        size = _data_url_bytes(f.dataUrl)
        if size > max_file:
            raise AppError("FILE_TOO_LARGE", f"File {f.name} vượt quá {settings.max_file_size_mb}MB", 413)
        total_bytes += size
    if total_bytes > max_total:
        raise AppError("PAYLOAD_TOO_LARGE", f"Tổng payload vượt quá {settings.max_total_payload_mb}MB", 413)

    options = body.options or {}

    session = None
    session_id = str(options.get("sessionId") or options.get("requestId") or "").strip()
    if session_id:
        session = await requests_repo.get_request_by_request_id(session_id, user_id=user["id"])
        if not session:
            raise AppError("SESSION_NOT_FOUND", f"Không tìm thấy session: {session_id}", 404)
        if session.get("procedure") != body.procedure:
            raise AppError("SESSION_PROCEDURE_MISMATCH", "Session không thuộc thủ tục đang chọn", 400)

    # Thủ tục đã migrate sang app/pipelines/<thủ tục>/attach → dispatch qua registry.
    attach_fn = get_attach_pipeline(body.procedure)
    if attach_fn:
        result = await attach_fn(body.files, options, session=session)
        # Mã hỗ trợ: sinh 1 request_id cho lượt đính kèm, trả về FE để cán bộ copy khi báo lỗi.
        request_id = "req_" + uuid.uuid4().hex[:12]
        result["requestId"] = request_id
        # Mỗi lượt đính kèm là một hành động riêng trên hồ sơ. Lưu trace kind="attach"
        # cho cả attach-only và thủ tục có hasAttachmentStep để màn trace đối chiếu được.
        await _save_attach_trace(body, proc, options, result, user, total_bytes, request_id)
        return result

    raise AppError("UNSUPPORTED_ATTACHMENT_PROCEDURE", f"Chưa hỗ trợ plan đính kèm cho {body.procedure}", 400)
