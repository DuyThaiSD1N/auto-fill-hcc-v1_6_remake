"""Compact schema cho thủ tục 1.115682 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (su_dung_dat_ket_hop_da_muc_dich_cap_xa): khối ChuHoSo_* (người sử
dụng đất, cá nhân hoặc tổ chức), khối NguoiNop_* (bên được uỷ quyền hoặc bản chép chủ hồ sơ), diện tích kết hợp.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai, thêm hai ô Fax (cổng cũ có nguồn Fax). Ô "Ghi chú" không điền.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[fax]": "dom-input", "data[ownerFax]": "dom-input"}
