"""Attachment pipeline for Xóa đăng ký tạm trú (mục "Hồ sơ đính kèm" cùng trang kê khai)."""
from app.pipelines.xoa_dang_ky_tam_tru.attach.planner import plan

__all__ = ["plan"]
