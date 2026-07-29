"""Đính kèm bước 3 cho thủ tục khai sinh liên thông."""
from app.pipelines.khai_sinh_lien_thong.attach.planner import plan
from app.pipelines.khai_sinh_lien_thong.attach.planner import plan_khai_sinh_attachments

__all__ = ["plan", "plan_khai_sinh_attachments"]
