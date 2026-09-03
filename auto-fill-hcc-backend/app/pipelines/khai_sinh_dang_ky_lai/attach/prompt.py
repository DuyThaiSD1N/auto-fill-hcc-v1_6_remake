"""Tương thích import cũ; mặc định dùng prompt giữ nguyên file."""

from app.pipelines.khai_sinh_dang_ky_lai.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
