"""Prompt LLM-first liệt kê giấy tờ trong từng tệp (KHÔNG tách trang) — "Đính chính GCN đã cấp lần đầu có sai sót"
(Đà Nẵng). Loại giấy lấy nguyên từ prompt chế độ tách."""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.prompt import (  # noqa: E501
    build_user_prompt,
    system_prompt,
)

from ..dinh_kem_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = system_prompt(
    "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
    DOC_TYPE_DEFINITIONS,
    '{"documents":[{"index":0,"docTypes":["gcn_da_cap","giay_to_chung_minh"]},{"index":1,"docTypes":["don_mau_18"]},'
    '{"index":2,"docTypes":["van_ban_uy_quyen"]}]}',
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
