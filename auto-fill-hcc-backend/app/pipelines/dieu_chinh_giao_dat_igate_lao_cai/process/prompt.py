"""Luật prompt cho thủ tục 1.115652 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dieu_chinh_giao_dat_lao_cai; chỉ mapper sang ô UI là
khác.
"""

from app.pipelines.dieu_chinh_giao_dat_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
