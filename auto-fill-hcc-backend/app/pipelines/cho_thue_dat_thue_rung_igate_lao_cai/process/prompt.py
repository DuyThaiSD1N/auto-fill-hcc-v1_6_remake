"""Luật prompt cho thủ tục 1.115678 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng (Đơn Mẫu số 01, bộ hồ sơ trúng đấu giá, hợp đồng ủy quyền, CCCD…) → dùng nguyên luật của
pipeline cổng cũ cho_thue_dat_thue_rung; chỉ mapper sang ô UI là khác.
"""

from app.pipelines.cho_thue_dat_thue_rung.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
