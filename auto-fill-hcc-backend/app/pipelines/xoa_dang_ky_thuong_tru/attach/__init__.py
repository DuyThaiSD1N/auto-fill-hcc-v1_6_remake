"""Attachment pipeline for Xóa đăng ký thường trú (mục "Trường hợp và hồ sơ đính kèm" cùng trang kê khai)."""
from app.pipelines.xoa_dang_ky_thuong_tru.attach.planner import plan

__all__ = ["plan"]
