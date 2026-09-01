import base64
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

from app.attachments.router import plan_attachments as plan_attachments_v1
from app.attachments.schemas import AttachmentPlanReq, AttachmentPlanResp
from app.core.deps import require_auth
from app.core.errors import AppError
from app.process.router import process as process_v1
from app.process.schemas import FileItem, ProcessReq, ProcessResp


router = APIRouter(prefix="/api/v2", tags=["v2"])


def _parse_json_object(raw: str, *, error: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise AppError(error, f"{label} không phải JSON hợp lệ", 400) from exc
    if not isinstance(value, dict):
        raise AppError(error, f"{label} phải là một object JSON", 400)
    return value


def _parse_file_metadata(raw: str, files_count: int) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise AppError("BAD_FILE_METADATA", "Thông tin file không phải JSON hợp lệ", 400) from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AppError("BAD_FILE_METADATA", "Thông tin file phải là một mảng object JSON", 400)
    if value and len(value) != files_count:
        raise AppError(
            "BAD_FILE_METADATA",
            "Số phần tử thông tin file không khớp số file tải lên",
            400,
        )
    return value or [{} for _ in range(files_count)]


async def _to_file_items(
    uploads: list[UploadFile], metadata_raw: str,
) -> list[FileItem]:
    """Đổi multipart binary về contract FileItem để dùng nguyên lõi v1.

    Binary chỉ được base64 hóa sau khi đã tới backend; vì vậy không làm phình payload
    trên đường truyền. FileItem tiếp tục đi qua cùng validation, OCR, trace và storage v1.
    """
    metadata = _parse_file_metadata(metadata_raw, len(uploads))
    items: list[FileItem] = []
    for upload, meta in zip(uploads, metadata):
        mime = str(meta.get("type") or upload.content_type or "application/octet-stream")
        name = str(meta.get("name") or upload.filename or "file")
        try:
            raw = await upload.read()
        finally:
            await upload.close()

        data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        items.append(FileItem(
            name=name,
            type=mime,
            dataUrl=data_url,
            role=str(meta.get("role") or "doc"),
        ))
    return items


@router.post("/process")
async def process_v2(
    background: BackgroundTasks,
    action: str = Form(...),
    procedure: str = Form(...),
    options: str = Form("{}"),
    fileMetadata: str = Form("[]"),
    files: list[UploadFile] | None = File(None),
    user: dict = Depends(require_auth),
):
    """Một endpoint multipart cho cả điền form và lập kế hoạch đính kèm."""
    action = (action or "").strip().lower()
    if action not in {"fill", "attach"}:
        raise AppError("BAD_ACTION", "action chỉ nhận giá trị fill hoặc attach", 400)

    parsed_options = _parse_json_object(options, error="BAD_OPTIONS", label="options")
    file_items = await _to_file_items(files or [], fileMetadata)

    if action == "fill":
        result = await process_v1(
            ProcessReq(procedure=procedure, options=parsed_options, files=file_items),
            background,
            user,
        )
        payload = ProcessResp.model_validate(result).model_dump(mode="json")
        return {"action": action, **payload}

    result = await plan_attachments_v1(
        AttachmentPlanReq(procedure=procedure, options=parsed_options, files=file_items),
        user,
    )
    # Gọi handler trực tiếp sẽ bỏ qua response_model của route v1. Validate lại để v2
    # không vô tình lộ ocr_text/llm_output nội bộ và giữ đúng shape attachment hiện hành.
    payload = AttachmentPlanResp.model_validate(result).model_dump(mode="json")
    return {"action": action, **payload}
