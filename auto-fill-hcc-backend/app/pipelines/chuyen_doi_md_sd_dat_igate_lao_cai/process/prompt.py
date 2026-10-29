"""Luật prompt cho thủ tục 1.115651 (Lào Cai, cổng iGate mới).

Dữ kiện nguồn KHÔNG đổi theo cổng (cùng Đơn Mẫu 02/03/17/18, GCN, CCCD…) → dùng nguyên luật của pipeline cổng cũ
chuyen_doi_md_sd_dat_lao_cai; chỉ mapper sang ô UI là khác.
"""

from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
