"""Lưu multipart batch theo luồng, không giữ cả chiến dịch hoặc cả file trong RAM."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from fastapi import UploadFile
from pydantic import ValidationError

from app.batch.schemas import BatchItemMetadata
from app.config import settings
from app.core.errors import AppError


_CHUNK_BYTES = 1024 * 1024
_ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def parse_item_metadata(raw: str, files_count: int) -> BatchItemMetadata:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise AppError("BAD_BATCH_METADATA", "Thông tin hồ sơ không phải JSON hợp lệ.", 400) from exc
    try:
        metadata = BatchItemMetadata.model_validate(value)
    except ValidationError as exc:
        raise AppError("BAD_BATCH_METADATA", "Thông tin hồ sơ không hợp lệ.", 400) from exc
    if metadata.files and len(metadata.files) != files_count:
        raise AppError(
            "BAD_BATCH_FILE_METADATA",
            "Số phần tử thông tin file không khớp số file tải lên.",
            400,
        )
    return metadata


def safe_name(value: str | None, fallback: str = "file") -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", str(value or fallback))[:120]
    return name.strip("._") or fallback


def batch_root() -> Path:
    root = Path(settings.batch_storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def item_dir(job_id: str, item_id: str) -> Path:
    return batch_root() / safe_name(job_id, "job") / safe_name(item_id, "item")


def remove_item_files(job_id: str, item_id: str) -> None:
    """Chỉ xóa đúng thư mục item do server tự sinh, không nhận path từ client."""
    target = item_dir(job_id, item_id).resolve()
    root = batch_root()
    try:
        target.relative_to(root)
    except ValueError:
        return
    if target.is_dir():
        shutil.rmtree(target)


def remove_job_files(job_id: str) -> None:
    """Dọn toàn bộ file một batch đã kết thúc, với target bị giới hạn trong batch root."""
    target = (batch_root() / safe_name(job_id, "job")).resolve()
    root = batch_root()
    try:
        target.relative_to(root)
    except ValueError:
        return
    if target.is_dir():
        shutil.rmtree(target)


def _is_allowed(name: str, media_type: str) -> bool:
    if media_type in _ALLOWED_TYPES:
        return True
    return name.lower().endswith(".docx") and media_type in {"", "application/octet-stream"}


async def save_uploads(
    *,
    job_id: str,
    item_id: str,
    uploads: list[UploadFile],
    metadata: BatchItemMetadata,
) -> tuple[list[dict], int]:
    if not uploads:
        raise AppError("NO_FILES", "Không có file nào.", 400)

    root = batch_root()
    free_bytes = shutil.disk_usage(root).free
    required_free = settings.batch_min_free_disk_mb * 1024 * 1024
    if free_bytes < required_free:
        raise AppError("BATCH_DISK_LOW", "Ổ đĩa lưu batch không còn đủ dung lượng.", 507)

    target_dir = item_dir(job_id, item_id)
    target_dir.mkdir(parents=True, exist_ok=False)
    max_file = settings.max_file_size_mb * 1024 * 1024
    max_total = settings.max_total_payload_mb * 1024 * 1024
    total_bytes = 0
    stored: list[dict] = []

    try:
        for index, upload in enumerate(uploads):
            meta = metadata.files[index] if metadata.files else None
            original_name = str((meta.name if meta else None) or upload.filename or f"file_{index + 1}")
            media_type = str((meta.type if meta else None) or upload.content_type or "application/octet-stream")
            role = str((meta.role if meta else "doc") or "doc")
            handwriting = bool(meta.hasHandwriting) if meta else False
            if not _is_allowed(original_name, media_type):
                raise AppError("BAD_FILE_TYPE", f"Loại file không hỗ trợ: {media_type}", 400)

            filename = f"{index:03d}_{safe_name(original_name)}"
            path = target_dir / filename
            digest = hashlib.sha256()
            file_bytes = 0
            try:
                with path.open("wb") as handle:
                    while True:
                        chunk = await upload.read(_CHUNK_BYTES)
                        if not chunk:
                            break
                        file_bytes += len(chunk)
                        total_bytes += len(chunk)
                        if file_bytes > max_file:
                            raise AppError(
                                "FILE_TOO_LARGE",
                                f"File {original_name} vượt quá {settings.max_file_size_mb}MB.",
                                413,
                            )
                        if total_bytes > max_total:
                            raise AppError(
                                "PAYLOAD_TOO_LARGE",
                                f"Tổng hồ sơ vượt quá {settings.max_total_payload_mb}MB.",
                                413,
                            )
                        digest.update(chunk)
                        handle.write(chunk)
            finally:
                await upload.close()

            if file_bytes == 0:
                raise AppError("EMPTY_FILE", f"File {original_name} không có dữ liệu.", 400)
            stored.append({
                "name": original_name,
                "type": media_type,
                "role": role,
                "hasHandwriting": handwriting,
                "size": file_bytes,
                "sha256": digest.hexdigest(),
                "path": str(path.relative_to(root)),
            })
    except Exception:
        remove_item_files(job_id, item_id)
        for upload in uploads:
            try:
                await upload.close()
            except Exception:  # noqa: BLE001 - cleanup best-effort.
                pass
        raise

    return stored, total_bytes


def input_fingerprint(procedure: str, files_meta: list[dict]) -> str:
    hashes = sorted(str(item.get("sha256") or "") for item in files_meta)
    payload = json.dumps(
        {"procedure": procedure, "hashes": hashes},
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(b"hcc-batch-input-v1\0" + payload).hexdigest()
