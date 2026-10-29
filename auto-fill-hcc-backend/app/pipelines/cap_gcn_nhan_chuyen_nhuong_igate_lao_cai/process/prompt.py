"""Luật prompt cho thủ tục 1.115667 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ cap_GCN_nhan_chuyen_nhuong; chỉ mapper sang ô UI là
khác.
"""

from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
