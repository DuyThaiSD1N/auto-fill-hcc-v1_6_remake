"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Đăng ký nội quy lao động của doanh nghiệp"
(2.001955). Loại giấy lấy nguyên khối của prompt chế độ tách."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
)

from ..dinh_kem_tach import prompt as split_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

SYSTEM_PROMPT = build_system_prompt(
    "Đăng ký nội quy lao động của doanh nghiệp",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["van_ban_de_nghi","quyet_dinh_ban_hanh"]},'
    '{"index":1,"docTypes":["noi_quy_lao_dong"]},{"index":2,"docTypes":["giay_uy_quyen","cccd"]}]}',
)
