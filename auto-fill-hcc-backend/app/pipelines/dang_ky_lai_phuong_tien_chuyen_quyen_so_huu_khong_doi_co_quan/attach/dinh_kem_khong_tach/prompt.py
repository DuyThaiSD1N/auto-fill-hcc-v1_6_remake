"""Prompt liệt kê giấy tờ trong từng tệp — "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (1.004002), chế độ KHÔNG
tách. Định nghĩa loại giấy lấy nguyên văn từ prompt chế độ tách."""

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.prompt import (
    build_system_prompt,
    build_user_prompt,
    split_prompt_blocks,
)

from ..dinh_kem_tach import prompt as _tach

__all__ = ["DOC_TYPES", "SYSTEM_PROMPT", "build_user_prompt"]

DOC_TYPES = split_prompt_blocks(_tach.SYSTEM_PROMPT, "allowed_types", "disambiguation")

SYSTEM_PROMPT = build_system_prompt(
    "Đăng ký lại phương tiện thủy nội địa khi chuyển quyền sở hữu",
    DOC_TYPES,
    '{"documents":[{"index":0,"docTypes":["don_dang_ky_lai","gcn_dang_ky","hop_dong"]},'
    '{"index":1,"docTypes":["gcn_an_toan_ky_thuat"]},{"index":2,"docTypes":["bien_lai_le_phi"]}]}',
    ("Lời chứng của công chứng viên, trang chứng thực bản sao đi kèm một giấy thuộc chính giấy đó.",),
)
