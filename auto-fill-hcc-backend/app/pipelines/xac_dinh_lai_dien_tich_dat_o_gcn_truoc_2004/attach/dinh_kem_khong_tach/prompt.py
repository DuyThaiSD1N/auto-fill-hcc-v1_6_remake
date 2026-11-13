"""Prompt LLM-first liệt kê giấy tờ trong từng tệp (KHÔNG tách trang) — "Xác định lại diện tích đất ở (GCN cấp trước
01/7/2004)" (Đà Nẵng). Loại giấy lấy nguyên từ prompt chế độ tách."""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.prompt import (  # noqa: E501
    build_user_prompt,
    system_prompt,
)

from ..dinh_kem_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = system_prompt(
    "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận trước ngày 01 tháng 7 năm 2004",
    DOC_TYPE_DEFINITIONS,
    '{"documents":[{"index":0,"docTypes":["don_bien_dong","ban_mo_ta_ranh_gioi"]},{"index":1,"docTypes":["gcn_da_cap"]},'
    '{"index":2,"docTypes":["van_ban_dai_dien","cccd"]}]}',
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
