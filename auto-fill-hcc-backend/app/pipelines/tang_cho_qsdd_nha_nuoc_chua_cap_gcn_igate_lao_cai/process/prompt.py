"""Luật prompt cho thủ tục 1.115690 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ tang_cho_qsdd_nha_nuoc_chua_cap_gcn; chỉ mapper sang
ô UI là khác.
"""

from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
