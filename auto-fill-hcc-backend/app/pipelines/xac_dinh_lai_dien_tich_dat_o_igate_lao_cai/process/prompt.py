"""Luật prompt cho thủ tục 1.115685 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ xac_dinh_lai_dien_tich_dat_o; chỉ mapper sang ô UI
là khác.
"""

from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
