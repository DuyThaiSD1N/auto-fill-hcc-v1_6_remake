"""Attachment pipeline for Tách hộ (mục "Trường hợp và hồ sơ đính kèm" cùng trang kê khai)."""
from app.pipelines.tach_ho.attach.planner import plan

__all__ = ["plan"]
