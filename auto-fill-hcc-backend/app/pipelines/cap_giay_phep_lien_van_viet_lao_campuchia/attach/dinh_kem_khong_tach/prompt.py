"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và
Campuchia" (1.002877). Loại giấy lấy nguyên khối của prompt chế độ tách."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
)

from ..dinh_kem_tach import prompt as split_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

SYSTEM_PROMPT = build_system_prompt(
    "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["giay_de_nghi_phi_thuong_mai","dang_ky_xe"]},'
    '{"index":1,"docTypes":["hop_dong_du_an"]},{"index":2,"docTypes":["cccd"]}]}',
)
