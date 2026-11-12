"""Điều phối hai chế độ đính kèm 1.011442 Bắc Ninh theo cài đặt "Tách giấy tờ" của extension."""

from app.process.schemas import FileItem

from .dinh_kem_khong_tach.planner import plan as plan_without_split
from .dinh_kem_tach.planner import plan as plan_with_split


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    """Chỉ boolean ``True`` mới tách (và extension phải cắt được trang); client cũ / tắt tách đính nguyên tệp."""
    opts = options or {}
    split = opts.get("splitDocuments") is True and opts.get("supportsSourceSegments") is not False
    planner = plan_with_split if split else plan_without_split
    return await planner(files, options, session)
