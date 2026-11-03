"""Luật prompt cho thủ tục 1.115693 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi; chỉ mapper sang ô UI là khác.
"""

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
