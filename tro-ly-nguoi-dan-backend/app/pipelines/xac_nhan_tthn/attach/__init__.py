"""Đính kèm bước 3 cho thủ tục cấp Giấy xác nhận tình trạng hôn nhân."""
from app.pipelines.xac_nhan_tthn.attach.planner import plan
from app.pipelines.xac_nhan_tthn.attach.planner import plan_xac_nhan_tthn_attachments

__all__ = ["plan", "plan_xac_nhan_tthn_attachments"]

