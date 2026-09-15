"""Lõi chạy một hồ sơ, dùng chung cho API tương tác và batch worker.

Module này chỉ kiểm tra input + gọi pipeline. Việc lưu trace/audit thuộc về caller để batch test
không làm sai thống kê hồ sơ thực tế của extension.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.config import settings
from app.core.errors import AppError
from app.pipelines._shared.formatting import normalize_ui_dates
from app.process.schemas import ProcessReq
from app.services import ocr


_ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

Pipeline = Callable[[dict[str, list[dict]], dict], Awaitable[dict]]


@dataclass(slots=True)
class PreparedProcess:
    procedure: str
    proc: dict
    pipeline: Pipeline
    files_by_role: dict[str, list[dict]]
    pipeline_options: dict[str, Any]
    total_bytes: int
    ocr_provider: str


def is_allowed_file_type(file_item) -> bool:
    if file_item.type in _ALLOWED_TYPES:
        return True
    name = (file_item.name or "").lower()
    return name.endswith(".docx") and file_item.type in {"", "application/octet-stream"}


def data_url_bytes(data_url: str) -> int:
    """Ước lượng số byte file gốc từ độ dài phần base64."""
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return (len(b64) * 3) // 4


def prepare_process(
    body: ProcessReq,
    *,
    proc: dict | None,
    pipeline: Pipeline | None,
    include_review: bool,
) -> PreparedProcess:
    if not proc or not pipeline:
        raise AppError("UNKNOWN_PROCEDURE", f"Thủ tục không hợp lệ: {body.procedure}", 400)
    if not body.files:
        raise AppError("NO_FILES", "Không có file nào", 400)

    max_file = settings.max_file_size_mb * 1024 * 1024
    max_total = settings.max_total_payload_mb * 1024 * 1024
    is_agent = proc.get("mode") == "agent"
    valid_roles = {item["value"] for item in proc.get("roles") or []}
    total_bytes = 0
    files_by_role: dict[str, list[dict]] = {}

    for file_item in body.files:
        if not is_allowed_file_type(file_item):
            raise AppError("BAD_FILE_TYPE", f"Loại file không hỗ trợ: {file_item.type}", 400)
        if not is_agent and file_item.role not in valid_roles:
            raise AppError(
                "BAD_ROLE",
                f"Role không hợp lệ cho thủ tục: {file_item.role}",
                400,
            )
        size = data_url_bytes(file_item.dataUrl)
        if size > max_file:
            raise AppError(
                "FILE_TOO_LARGE",
                f"File {file_item.name} vượt quá {settings.max_file_size_mb}MB",
                413,
            )
        total_bytes += size
        files_by_role.setdefault(file_item.role, []).append({
            "name": file_item.name,
            "type": file_item.type,
            "dataUrl": file_item.dataUrl,
        })

    if total_bytes > max_total:
        raise AppError(
            "PAYLOAD_TOO_LARGE",
            f"Tổng payload vượt quá {settings.max_total_payload_mb}MB",
            413,
        )

    pipeline_options = dict(body.options or {})
    if include_review and proc.get("review"):
        pipeline_options["_review"] = True

    return PreparedProcess(
        procedure=body.procedure,
        proc=proc,
        pipeline=pipeline,
        files_by_role=files_by_role,
        pipeline_options=pipeline_options,
        total_bytes=total_bytes,
        ocr_provider=ocr.resolved_label(),
    )


async def execute_process(prepared: PreparedProcess) -> dict:
    result = await prepared.pipeline(prepared.files_by_role, prepared.pipeline_options)
    # Chốt chặn CHUNG cho mọi thủ tục: mỗi pipeline tự chuẩn hóa ngày một kiểu (nhiều pipeline
    # không chuẩn hóa gì cả), nên siết một lần ở đây thay vì vá rải rác 90 mapper.
    if isinstance(result, dict):
        normalize_ui_dates(result.get("fields"))
    return result
