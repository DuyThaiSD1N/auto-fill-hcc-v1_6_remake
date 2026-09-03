"""Tương thích import cũ; prompt mặc định trước đây là prompt của nhánh tách."""

from app.pipelines.trich_luc.attach.dinh_kem_tach.prompt import SYSTEM_PROMPT, build_user_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
