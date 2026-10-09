"""Điều phối hai chế độ đính kèm theo cài đặt "Tách giấy tờ" (Cổng DVC quốc gia mới)."""

from app.process.schemas import FileItem

from .dinh_kem_khong_tach.planner import plan as plan_without_split
from .dinh_kem_tach.planner import plan as plan_with_split


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    """Chỉ boolean ``True`` mới tách; client cũ / tắt tách luôn đính nguyên tệp."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session)
