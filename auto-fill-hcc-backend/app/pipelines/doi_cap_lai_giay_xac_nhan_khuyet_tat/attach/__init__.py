"""Attachment pipeline cho thủ tục đổi, cấp lại Giấy xác nhận khuyết tật."""
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.attach.planner import plan

__all__ = ["plan"]
