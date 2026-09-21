import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.attachments.schemas import (
    AttachmentPlanReq,
    AttachmentPlanResp,
    ClientAttachmentTraceReq,
    ClientAttachmentTraceResp,
)
from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.dossiers import repo as dossiers_repo
from app.dossiers.options import dossier_id_from_options
from app.process import requests_repo
from app.pipelines.chung_thuc_ban_sao.attach.stt1_virtual import apply_stt1_virtual_copy
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
        ocr_provider=ocr.resolved_label(),
        ocr_text=result.get("ocr_text", ""),
        # Lưu kế hoạch đính kèm để xem chi tiết (file → tài liệu → ô/component đích).
        llm_output={"attachments": plan, "extracted": result.get("extracted")},
        fields_count=len(plan), status="done",
        created_at=created_at,
        dossier_id=dossier_id_from_options(options),
    )
    # Mốc BẮT ĐẦU hồ sơ Auto Fill = lượt process/đính kèm ĐẦU TIÊN. Đường này là DUY NHẤT với
    # thủ tục attach-only (chứng thực bản sao/chữ ký) — nhóm nhiều lượt nhất mà không hề gọi
    # /process, nên thiếu chỗ này là mất hẳn nhóm đó khỏi thống kê.
    dossier_id = dossier_id_from_options(options)
    if dossier_id:
        await dossiers_repo.upsert_started(
            dossier_id=dossier_id, user_id=str(user.get("id") or ""),
            username=user.get("username"), name=user.get("name"),
            procedure=body.procedure, procedure_label=proc.get("label"),
            province=user.get("tinh"), ward=user.get("xa"),
            started_at=created_at, experience="autofill", applicant_name=applicant_name,
        )


@router.post("/plan", response_model=AttachmentPlanResp)
async def plan_attachments(body: AttachmentPlanReq, user: dict = Depends(require_auth)):
    proc = get_procedure(body.procedure)
    if not proc or (proc.get("mode") != "attach" and not proc.get("hasAttachmentStep")):
        raise AppError("UNKNOWN_ATTACHMENT_PROCEDURE", f"Thủ tục đính kèm không hợp lệ: {body.procedure}", 400)
    if not body.files:
        raise AppError("NO_FILES", "Không có file nào", 400)

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
        # Hotfix theo tài khoản (Chứng thực bản sao, Đà Nẵng/Hải Châu): chèn directive file ảo STT1.
        # Gate ở đây vì router mới có `user` (tinh/xa); no-op với mọi thủ tục/tài khoản khác.
        result = apply_stt1_virtual_copy(result, user, body.procedure)
        # Mã hỗ trợ: sinh 1 request_id cho lượt đính kèm, trả về FE để cán bộ copy khi báo lỗi.
        request_id = traces_repo.new_request_id()
        result["requestId"] = request_id
        # Mỗi lượt đính kèm là một hành động riêng trên hồ sơ. Lưu trace kind="attach"
        # cho cả attach-only và thủ tục có hasAttachmentStep để màn trace đối chiếu được.
        await _save_attach_trace(body, proc, options, result, user, total_bytes, request_id)
        return result

    raise AppError("UNSUPPORTED_ATTACHMENT_PROCEDURE", f"Chưa hỗ trợ plan đính kèm cho {body.procedure}", 400)


@router.post("/client-trace", response_model=ClientAttachmentTraceResp)
async def create_client_attachment_trace(
    body: ClientAttachmentTraceReq,
    user: dict = Depends(require_auth),
) -> dict:
    """Sinh mã hỗ trợ cho case FE tự đính, không nhận/lưu binary hay dataUrl.

    Chỉ thủ tục khai báo ``clientAttachmentCase`` trong registry mới được gọi endpoint
    này. Guard đó giữ luồng metadata-only cô lập, tránh một thủ tục OCR vô tình bỏ qua
    pipeline phân loại tài liệu ở backend.
    """
    proc = get_procedure(body.procedure)
    client_case = proc.get("clientAttachmentCase") if proc else None
    if not proc or not isinstance(client_case, dict):
        raise AppError(
            "UNKNOWN_CLIENT_ATTACHMENT_PROCEDURE",
            f"Thủ tục không hỗ trợ đính kèm cục bộ: {body.procedure}",
            400,
        )
    if not body.files:
        raise AppError("NO_FILES", "Không có metadata file nào", 400)
    if len(body.attachments) != len(body.files):
        raise AppError(
            "CLIENT_ATTACHMENT_PLAN_MISMATCH",
            "Số kế hoạch đính kèm phải bằng số file",
            400,
        )

    component_name = str(client_case.get("componentName") or "").strip()
    component_index = int(client_case.get("componentIndex") or 0)
    plan = [item.model_dump(mode="json") for item in body.attachments]
    seen_indexes: set[int] = set()
    for item in plan:
        file_index = item.get("fileIndex")
        if not isinstance(file_index, int) or not 0 <= file_index < len(body.files):
            raise AppError("BAD_CLIENT_ATTACHMENT_INDEX", "Chỉ số file trong kế hoạch không hợp lệ", 400)
        if file_index in seen_indexes:
            raise AppError("DUPLICATE_CLIENT_ATTACHMENT_INDEX", "Một file bị khai báo đính kèm nhiều lần", 400)
        seen_indexes.add(file_index)
        if (
            item.get("componentName") != component_name
            or item.get("componentIndex") != component_index
            or item.get("target") != "existing"
            or item.get("needsAddComponent") is not False
        ):
            raise AppError(
                "CLIENT_ATTACHMENT_TARGET_MISMATCH",
                "Kế hoạch đính kèm không đúng thành phần hồ sơ đã cấu hình",
                400,
            )

    request_id = traces_repo.new_request_id()
    created_at = datetime.now(timezone.utc)
    options = body.options or {}
    # CTV cho chọn: tách (mỗi file 1 hồ sơ/tab) hoặc gộp 1 tab. Extension gửi lựa chọn ở
    # options.splitMode; bản extension cũ không gửi thì trước đây luôn tách → mặc định tách.
    # Ghi sai cờ này là gộp 4 tệp vào 1 hồ sơ vẫn bị thống kê đếm thành 4.
    client_split = options.get("splitMode")
    split = (client_case.get("type") == "single-row-local-split"
             and (client_split if isinstance(client_split, bool) else True))
    files_meta = [
        {
            "name": item.name,
            "type": item.type,
            "role": item.role,
            "size": item.size,
            "sha256": None,
        }
        for item in body.files
    ]
    attachments, dossier_ids = build_attach_trace_metadata(
        request_id=request_id,
        session_id=str(options.get("sessionId") or options.get("requestId") or "").strip() or None,
        procedure=body.procedure,
        split=split,
        plan=plan,
        files_meta=files_meta,
    )
    applicant_name = resolve_applicant_name(options, {"attachments": plan})
    await traces_repo.create_trace(
        request_id=request_id,
        user_id=user["id"],
        username=user.get("username"),
        name=user.get("name"),
        applicant_name=applicant_name,
        attachments=attachments,
        split=split,
        stats_version=2,
        dossier_ids=dossier_ids,
        kind="attach",
        stats={"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        total_bytes=sum(item.size for item in body.files),
        procedure=body.procedure,
        procedure_label=proc.get("label"),
        ocr_provider=None,
        ocr_text="",
        llm_output={
            "attachments": plan,
            "extracted": {
                "documents": [item.name for item in body.files],
                "clientAttachmentCase": client_case.get("type"),
            },
        },
        fields_count=len(plan),
        status="done",
        created_at=created_at,
        dossier_id=dossier_id_from_options(options),
    )
    # Đính kèm phía client (không qua planner) vẫn là một lượt làm việc trên hồ sơ đó →
    # cũng phải chấm mốc, nếu không hồ sơ tách-tab sẽ không có started_at.
    dossier_id = dossier_id_from_options(options)
    if dossier_id:
        await dossiers_repo.upsert_started(
            dossier_id=dossier_id, user_id=str(user.get("id") or ""),
            username=user.get("username"), name=user.get("name"),
            procedure=body.procedure, procedure_label=proc.get("label"),
            province=user.get("tinh"), ward=user.get("xa"),
            started_at=created_at, experience="autofill", applicant_name=applicant_name,
        )
    return {"requestId": request_id}
