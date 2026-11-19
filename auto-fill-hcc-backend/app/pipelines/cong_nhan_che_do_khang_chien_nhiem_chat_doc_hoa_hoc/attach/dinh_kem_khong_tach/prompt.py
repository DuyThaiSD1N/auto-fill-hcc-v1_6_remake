"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Công nhận và giải quyết chế độ ưu đãi người hoạt động
kháng chiến bị nhiễm chất độc hóa học" (1.010816). Loại giấy lấy nguyên khối của prompt chế độ tách."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
)

from ..dinh_kem_tach import prompt as split_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

SYSTEM_PROMPT = build_system_prompt(
    "Công nhận và giải quyết chế độ ưu đãi người hoạt động kháng chiến bị nhiễm chất độc hóa học",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["ban_khai_mau_09","cccd"]},'
    '{"index":1,"docTypes":["giay_to_khang_chien"]},{"index":2,"docTypes":["giay_to_mac_benh"]}]}',
)
