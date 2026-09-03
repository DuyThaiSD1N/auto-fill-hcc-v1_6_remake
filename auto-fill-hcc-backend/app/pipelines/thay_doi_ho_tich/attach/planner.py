"""Điều phối hai chế độ đính kèm của thủ tục thay đổi, cải chính hộ tịch."""

from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_khong_tach.planner import (
    plan as plan_without_split,
)
from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_tach.planner import plan as plan_with_split
from app.process.schemas import FileItem


async def plan_thay_doi_ho_tich_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    """Client cũ không gửi ``splitDocuments`` nên luôn giữ nguyên file tải lên."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session=session)


plan = plan_thay_doi_ho_tich_attachments

__all__ = ["plan", "plan_thay_doi_ho_tich_attachments"]
