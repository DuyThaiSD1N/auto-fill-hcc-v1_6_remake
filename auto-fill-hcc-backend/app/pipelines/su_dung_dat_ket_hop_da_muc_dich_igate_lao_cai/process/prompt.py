"""Luật prompt cho thủ tục 1.115682 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ su_dung_dat_ket_hop_da_muc_dich_cap_xa; chỉ mapper
sang ô UI là khác.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
