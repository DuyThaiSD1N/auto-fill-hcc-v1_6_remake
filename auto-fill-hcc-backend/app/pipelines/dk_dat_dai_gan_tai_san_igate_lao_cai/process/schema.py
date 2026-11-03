"""Compact schema cho thủ tục 1.115688 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dk_dat_dai_gan_tai_san_lao_cai): CCCD, người trong giấy tờ (Đơn Mẫu
15/21, Mẫu 15a, Giấy ủy quyền), khối ChuHoSo_* (người sử dụng đất ở mục 1 Đơn, 4 loại đối tượng), liên hệ trên Đơn.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 02/11/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Fax và "Ghi chú" (data[tenHoSo]) không có nguồn.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
