"""Điều phối hai chế độ đính kèm của thủ tục đăng ký kết hôn."""

from app.pipelines.ket_hon.attach.dinh_kem_khong_tach.planner import plan as plan_without_split
from app.pipelines.ket_hon.attach.dinh_kem_tach.planner import plan as plan_with_split
from app.process.schemas import FileItem


async def plan_ket_hon_attachments(
    files: list[FileItem], options: dict | None = None, session: dict | None = None,
) -> dict:
    """Chỉ boolean ``True`` mới bật tách; client cũ/mất option luôn giữ nguyên file."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session=session)


plan = plan_ket_hon_attachments

__all__ = ["plan", "plan_ket_hon_attachments"]
