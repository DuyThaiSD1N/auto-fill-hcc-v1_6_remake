"""Tương thích import cũ: prompt mặc định là nhánh giữ nguyên file."""

from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
