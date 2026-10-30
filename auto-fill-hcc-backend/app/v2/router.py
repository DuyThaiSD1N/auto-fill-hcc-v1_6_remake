import asyncio
import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

from app.attachments.router import plan_attachments as plan_attachments_v1
from app.attachments.schemas import AttachmentPlanReq, AttachmentPlanResp
from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError
from app.monitor import recorder as mon
from app.process import requests_repo
from app.process.router import process as process_v1
from app.process.schemas import FileItem, ProcessReq, ProcessResp


router = APIRouter(prefix="/api/v2", tags=["v2"])

# Tệp chính tài khoản đã gửi ở lượt trước (điền/đính) đang nằm trên đĩa máy chủ: extension chỉ gửi
# sha256 (fileMetadata[i].stored) thay vì nội dung → mạng chậm không phải đẩy lại cả chục MB.
_STORED_LOOKBACK = timedelta(hours=6)
# Lượt điền ghi tệp NỀN sau khi đã trả kết quả → bước đính gọi ngay sau đó có thể tới trước.
_STORED_RETRY_DELAYS_S = (0.5, 1.0, 1.5)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    if any("stored" in item and not _SHA256_RE.match(str(item["stored"])) for item in value):
        raise AppError("BAD_FILE_METADATA", "Mã tệp đã lưu không hợp lệ", 400)
    if value and sum(1 for item in value if not item.get("stored")) != files_count:
        raise AppError(
            "BAD_FILE_METADATA",
            "Số phần tử thông tin file không khớp số file tải lên",
            400,
        )
    return value or [{} for _ in range(files_count)]


def _read_stored(rel_path: str, sha256: str) -> bytes | None:
    try:
        with open(os.path.join(settings.storage_dir, rel_path), "rb") as fh:
            raw = fh.read()
    except OSError:
        return None  # đã chuyển sang kho và xoá khỏi đĩa
    return raw if hashlib.sha256(raw).hexdigest() == sha256 else None


async def _load_stored(user_id: str, sha256s: set[str]) -> dict[str, bytes]:
    since = datetime.now(timezone.utc) - _STORED_LOOKBACK
    found: dict[str, bytes] = {}
    for delay in (0, *_STORED_RETRY_DELAYS_S):
        if delay:
            await asyncio.sleep(delay)
        paths = await requests_repo.find_stored_files(user_id, sorted(sha256s - found.keys()), since)
        for sha256, rel_path in paths.items():
            raw = await asyncio.to_thread(_read_stored, rel_path, sha256)
            if raw is not None:
                found[sha256] = raw
        if sha256s <= found.keys():
            break
    return found


async def _to_file_items(
    uploads: list[UploadFile], metadata_raw: str, user_id: str,
) -> list[FileItem]:
    """Đổi multipart binary về contract FileItem để dùng nguyên lõi v1.

    Binary chỉ được base64 hóa sau khi đã tới backend; vì vậy không làm phình payload
    trên đường truyền. FileItem tiếp tục đi qua cùng validation, OCR, trace và storage v1.
    """
    metadata = _parse_file_metadata(metadata_raw, len(uploads))
    wanted = {str(meta["stored"]) for meta in metadata if meta.get("stored")}
    stored: dict[str, bytes] = {}
    if wanted:
        with mon.span("pre.stored", files=len(wanted)) as sp:
            stored = await _load_stored(user_id, wanted)
            sp.attrs["bytes"] = sum(len(raw) for raw in stored.values())
        if wanted - stored.keys():
            raise AppError("STORED_FILE_MISSING", "Máy chủ không còn tệp đã gửi trước đó, cần gửi lại.", 409)
    pending = iter(uploads)
    items: list[FileItem] = []
    for meta in metadata:
        if meta.get("stored"):
            upload = None
            raw = stored[str(meta["stored"])]
        else:
            upload = next(pending)
            try:
                raw = await upload.read()
            finally:
                await upload.close()
        mime = str(meta.get("type") or (upload and upload.content_type) or "application/octet-stream")
        name = str(meta.get("name") or (upload and upload.filename) or "file")

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
    handler_start = time.perf_counter()
    action = (action or "").strip().lower()
    if action not in {"fill", "attach"}:
        raise AppError("BAD_ACTION", "action chỉ nhận giá trị fill hoặc attach", 400)

    # v1 bên dưới dùng lại recorder này (cùng kind) → timeline có cả phần nhận multipart.
    rec = mon.start("autofill" if action == "fill" else "attach", "autofill", api="v2")
    if rec is not None:
        rec.add_span("pre.request", rec.origin, handler_start)
    parsed_options = _parse_json_object(options, error="BAD_OPTIONS", label="options")
    with mon.span("pre.receive", files=len(files or [])):
        file_items = await _to_file_items(files or [], fileMetadata, user["id"])

    if action == "fill":
        result = await process_v1(
            ProcessReq(procedure=procedure, options=parsed_options, files=file_items),
            background,
            user,
        )
        with mon.span("post.response"):
            payload = ProcessResp.model_validate(result).model_dump(mode="json")
        if rec is not None:
            rec.output("response", payload)
            rec.mark_wait_end()
        return {"action": action, "fileRefs": True, **payload}

    result = await plan_attachments_v1(
        AttachmentPlanReq(procedure=procedure, options=parsed_options, files=file_items),
        user,
    )
    # Gọi handler trực tiếp sẽ bỏ qua response_model của route v1. Validate lại để v2
    # không vô tình lộ ocr_text/llm_output nội bộ và giữ đúng shape attachment hiện hành.
    with mon.span("post.response"):
        payload = AttachmentPlanResp.model_validate(result).model_dump(mode="json")
    if rec is not None:
        # replaceFiles mang cả tệp nén (base64, cỡ MB) → không ghi vào trace.
        rec.output("response", {k: v for k, v in payload.items() if k != "replaceFiles"})
        rec.mark_wait_end()
    return {"action": action, "fileRefs": True, **payload}
