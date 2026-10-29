"""Luật prompt cho thủ tục 1.115650 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ giao_thue_dat_lao_cai; chỉ mapper sang ô UI là khác.
"""

from app.pipelines.giao_thue_dat_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
