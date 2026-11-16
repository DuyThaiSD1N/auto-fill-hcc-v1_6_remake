"""Attachment pipeline for Đăng ký thường trú (mục "Trường hợp và hồ sơ đính kèm" cùng trang kê khai)."""
from app.pipelines.dang_ky_thuong_tru.attach.planner import plan

__all__ = ["plan"]
