"""Luật prompt cho thủ tục 1.115679 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ chuyen_md_sd_dat_phuong_xa_lao_cai; chỉ mapper sang
ô UI là khác.
"""

from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
