"""Prompt LLM-first liệt kê giấy tờ trong từng tệp (KHÔNG tách trang) — "Đăng ký đất đai lần đầu ... Nhà nước giao
đất để quản lý" (1.012756, Đà Nẵng). Loại giấy lấy nguyên từ prompt chế độ tách."""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.prompt import (  # noqa: E501
    build_user_prompt,
    system_prompt,
)

from ..dinh_kem_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = system_prompt(
    "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản lý",
    DOC_TYPE_DEFINITIONS,
    '{"documents":[{"index":0,"docTypes":["don_mau_15","quyet_dinh","hop_dong_thue_dat"]},'
    '{"index":1,"docTypes":["bao_cao_ra_soat","trich_luc_ban_do"]},{"index":2,"docTypes":["cccd"]}]}',
)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
