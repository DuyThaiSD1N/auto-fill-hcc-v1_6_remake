"""Điều phối hai chế độ đính kèm theo cài đặt "Có tách hồ sơ khi đính kèm" (cổng iGate Tuyên Quang)."""

from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested
from app.process.schemas import FileItem

from .dinh_kem_khong_tach.planner import plan as plan_without_split
from .dinh_kem_tach.planner import plan as plan_with_split


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    """Chỉ ``splitDocuments`` là boolean ``True`` (và client cắt được trang) mới tách; còn lại đính nguyên tệp."""
    planner = plan_with_split if split_requested(options) else plan_without_split
    return await planner(files, options, session)
