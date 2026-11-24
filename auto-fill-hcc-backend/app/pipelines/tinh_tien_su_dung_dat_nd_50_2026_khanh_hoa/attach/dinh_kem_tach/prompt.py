"""Prompt chia trang thành từng giấy khi TÁCH đính kèm tính hoặc tính lại tiền sử dụng đất (1.115148, cổng Khánh Hòa).

Quy tắc chia giấy giống hệt bản Lâm Đồng (cùng bộ giấy) — lấy nguyên prompt đó, chỉ thêm tên cổng vào persona."""

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as _LAM_DONG_PROMPT,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_tach.prompt import build_user_prompt

_PERSONA_END = "thành từng GIẤY TỜ riêng"
SYSTEM_PROMPT = _LAM_DONG_PROMPT.replace(_PERSONA_END, f"(cổng dịch vụ công tỉnh Khánh Hòa) {_PERSONA_END}", 1)

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
