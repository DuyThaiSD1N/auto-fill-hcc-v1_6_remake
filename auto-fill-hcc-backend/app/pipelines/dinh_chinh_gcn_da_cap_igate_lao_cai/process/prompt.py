"""Luật prompt cho thủ tục 1.115686 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dinh_chinh_gcn_da_cap_lao_cai; chỉ mapper sang ô UI
là khác.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
