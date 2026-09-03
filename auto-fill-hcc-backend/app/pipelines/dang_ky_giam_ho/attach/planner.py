"""Điều phối hai chế độ đính kèm của thủ tục đăng ký giám hộ."""

from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_khong_tach.planner import plan as plan_without_split
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_tach.planner import plan as plan_with_split
from app.process.schemas import FileItem


async def plan_dang_ky_giam_ho_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Chỉ boolean ``True`` mới tách; client cũ tiếp tục giữ nguyên từng file."""
    planner = plan_with_split if (options or {}).get("splitDocuments") is True else plan_without_split
    return await planner(files, options, session=session)


plan = plan_dang_ky_giam_ho_attachments

__all__ = ["plan", "plan_dang_ky_giam_ho_attachments"]
