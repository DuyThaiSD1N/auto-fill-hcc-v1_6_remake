"""Luật prompt cho thủ tục 1.115677 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ xac_nhan_tiep_tuc_dat_nong_nghiep; chỉ mapper sang ô
UI là khác.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
