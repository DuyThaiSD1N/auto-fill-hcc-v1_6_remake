"""Tương thích import cũ; prompt trước đây là prompt của nhánh tách giấy tờ."""

from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
