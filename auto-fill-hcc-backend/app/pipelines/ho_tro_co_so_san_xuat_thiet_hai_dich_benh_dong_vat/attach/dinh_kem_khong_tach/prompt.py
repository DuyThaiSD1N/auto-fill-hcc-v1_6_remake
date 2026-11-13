"""Prompt liệt kê giấy tờ trong từng tệp — hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (1.013997), chế
độ KHÔNG tách. Định nghĩa loại giấy lấy nguyên văn từ prompt chế độ tách."""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
    split_prompt_blocks,
)

from ..dinh_kem_tach import prompt as _tach

__all__ = ["DOC_TYPES", "SYSTEM_PROMPT", "build_user_prompt"]

DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "disambiguation")

SYSTEM_PROMPT = build_system_prompt(
    "Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["don_de_nghi","bien_ban_tieu_huy"]},'
    '{"index":1,"docTypes":["bien_ban_tieu_huy"]},{"index":2,"docTypes":["cccd"]}]}',
)
