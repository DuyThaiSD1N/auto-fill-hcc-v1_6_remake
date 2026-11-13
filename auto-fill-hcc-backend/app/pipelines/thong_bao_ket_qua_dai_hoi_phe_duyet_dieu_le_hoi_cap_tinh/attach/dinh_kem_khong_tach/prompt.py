"""Prompt LLM liệt kê giấy tờ trong từng tệp — chế độ KHÔNG tách, "Thông báo kết quả đại hội và phê duyệt đổi tên hội,
phê duyệt điều lệ hội (cấp tỉnh)" (1.012943). Loại giấy lấy nguyên khối của prompt chế độ tách."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
)

from ..dinh_kem_tach import prompt as split_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]

SYSTEM_PROMPT = build_system_prompt(
    "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh)",
    split_prompt.SYSTEM_PROMPT,
    '{"documents":[{"index":0,"docTypes":["bao_cao_ket_qua","danh_sach","nghi_quyet_dai_hoi"]},'
    '{"index":1,"docTypes":["bien_ban","danh_sach"]},{"index":2,"docTypes":["bao_cao_tong_ket"]}]}',
)
