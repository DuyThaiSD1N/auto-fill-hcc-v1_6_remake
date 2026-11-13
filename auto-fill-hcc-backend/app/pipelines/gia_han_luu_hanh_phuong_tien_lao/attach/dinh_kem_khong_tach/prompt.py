"""Prompt liệt kê giấy tờ trong từng tệp — "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào", chế độ
KHÔNG tách. Định nghĩa loại giấy lấy nguyên văn từ prompt chế độ tách."""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
    split_prompt_blocks,
)

from ..dinh_kem_tach import prompt as _tach

__all__ = ["DOC_TYPES", "SYSTEM_PROMPT", "build_user_prompt"]

DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "traps")

SYSTEM_PROMPT = build_system_prompt(
    "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["giay_de_nghi"]},'
    '{"index":1,"docTypes":["giay_to_chung_minh","giay_phep_lien_van"]}]}',
)
