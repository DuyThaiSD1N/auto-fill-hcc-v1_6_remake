"""Luật prompt cho thủ tục 1.115688 (Lào Cai, cổng iGate mới).

Giấy tờ không đổi theo cổng → dùng nguyên luật của pipeline cổng cũ dk_dat_dai_gan_tai_san_lao_cai; chỉ mapper sang ô UI
là khác.
"""

from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process.prompt import EXTRA_RULES

__all__ = ["EXTRA_RULES"]
