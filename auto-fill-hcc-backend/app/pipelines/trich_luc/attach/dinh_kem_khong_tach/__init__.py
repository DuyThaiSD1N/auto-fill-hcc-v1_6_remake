"""Nhánh giữ nguyên file của thủ tục cấp bản sao trích lục hộ tịch."""

from app.pipelines.trich_luc.attach.dinh_kem_khong_tach.planner import plan

__all__ = ["plan"]
