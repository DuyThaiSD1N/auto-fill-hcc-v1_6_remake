"""Compact schema cho thủ tục 1.115679 — Lào Cai, cổng iGate MỚI (Form.io), bản nộp ở PHƯỜNG/XÃ.

Cùng tên với 1.115651 (bản nộp ở Sở). Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (chuyen_md_sd_dat_phuong_xa_lao_cai):
CCCD, người trong giấy tờ, bên được uỷ quyền, khối ChuHoSo_* 4 loại đối tượng + địa chỉ Đơn / Giấy uỷ quyền / GCN.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Ô "Ghi chú" không điền.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
