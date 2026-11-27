"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Giải quyết chế độ mai táng phí đối với cựu chiến binh"
(2.002307). Loại giấy lấy nguyên khối của prompt chế độ tách."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
)

from ..dinh_kem_tach import prompt as split_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

SYSTEM_PROMPT = build_system_prompt(
    "Giải quyết chế độ mai táng phí đối với cựu chiến binh",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["ban_khai_mau_01"]},{"index":1,"docTypes":["trich_luc_khai_tu"]},'
    '{"index":2,"docTypes":["xac_nhan_cuu_chien_binh"]},'
    '{"index":3,"docTypes":["ban_khai_mau_01","trich_luc_khai_tu","xac_nhan_cuu_chien_binh"]}]}',
)
