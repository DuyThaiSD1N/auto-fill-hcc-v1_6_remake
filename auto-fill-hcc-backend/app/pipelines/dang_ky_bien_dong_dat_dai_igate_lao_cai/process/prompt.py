"""Luật prompt cho thủ tục 1.115668 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dang_ky_quyen_su_dung_dat_lao_cai; chỉ mapper sang
ô UI là khác.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
