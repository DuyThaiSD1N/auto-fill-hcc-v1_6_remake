"""Compact schema cho thủ tục 1.115685 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (xac_dinh_lai_dien_tich_dat_o): khối ChuHoSo_* (người sử dụng đất),
khối NguoiNop_* (người được ủy quyền hoặc bản chép chủ hồ sơ), GCN cấp trước 01/7/2004, mẫu Đơn.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng bảng ô UI của
su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai (bảng chung + hai ô Fax). Ô "Ghi chú" không điền.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
