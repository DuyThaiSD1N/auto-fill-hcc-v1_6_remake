"""Đính kèm bước 3 cho thủ tục đăng ký kết hôn."""
from app.pipelines.ket_hon.attach.planner import plan
from app.pipelines.ket_hon.attach.planner import plan_ket_hon_attachments

__all__ = ["plan", "plan_ket_hon_attachments"]

