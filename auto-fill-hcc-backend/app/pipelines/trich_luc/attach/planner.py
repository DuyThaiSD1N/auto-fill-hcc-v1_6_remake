"""Điều phối hai chế độ đính kèm của thủ tục cấp bản sao trích lục hộ tịch."""

from app.pipelines.trich_luc.attach.dinh_kem_khong_tach.planner import plan as plan_without_split
from app.pipelines.trich_luc.attach.dinh_kem_tach.planner import plan as plan_with_split
from app.process.schemas import FileItem


async def plan_trich_luc_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    """Chỉ boolean ``True`` mới tách; client cũ luôn giữ nguyên file tải lên."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session=session)


plan = plan_trich_luc_attachments

__all__ = ["plan", "plan_trich_luc_attachments"]
