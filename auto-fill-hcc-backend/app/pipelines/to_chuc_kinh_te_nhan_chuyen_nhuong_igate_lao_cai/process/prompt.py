"""Luật prompt cho thủ tục 1.115681 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an; chỉ
mapper sang ô UI là khác.
"""

from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
