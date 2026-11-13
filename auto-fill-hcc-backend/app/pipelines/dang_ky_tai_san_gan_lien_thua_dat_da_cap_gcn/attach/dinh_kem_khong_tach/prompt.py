"""Prompt LLM-first liệt kê giấy tờ trong từng tệp (KHÔNG tách trang) — "Đăng ký tài sản gắn liền với thửa đất đã
được cấp GCN..." (1.013995, Đà Nẵng). Loại giấy lấy nguyên từ prompt chế độ tách."""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.prompt import (  # noqa: E501
    build_user_prompt,
    system_prompt,
)

from ..dinh_kem_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = system_prompt(
    "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi về tài sản gắn liền với "
    "đất",
    DOC_TYPE_DEFINITIONS,
    '{"documents":[{"index":0,"docTypes":["don_mau_18","gcn_da_cap"]},{"index":1,"docTypes":["ho_so_thiet_ke"]},'
    '{"index":2,"docTypes":["van_ban_dai_dien","cccd"]}]}',
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
