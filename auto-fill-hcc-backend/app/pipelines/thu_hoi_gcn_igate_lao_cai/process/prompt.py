"""Luật prompt cho thủ tục 1.115687 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai;
chỉ mapper sang ô UI là khác.
"""

from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
