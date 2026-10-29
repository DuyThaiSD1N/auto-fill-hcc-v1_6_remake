"""Luật prompt cho thủ tục 1.115671 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dang_ky_bien_dong_lao_cai; chỉ mapper sang ô UI là
khác.
"""

from app.pipelines.dang_ky_bien_dong_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
