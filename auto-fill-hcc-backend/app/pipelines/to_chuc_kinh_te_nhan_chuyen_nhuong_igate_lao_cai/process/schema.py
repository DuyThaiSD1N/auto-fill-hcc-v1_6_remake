"""Compact schema cho thủ tục 1.115681 — Lào Cai, cổng iGate MỚI (Form.io).

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an): tổ chức chủ hồ sơ
(tên, MST, trụ sở theo GCN ĐKDN mới nhất), người đại diện theo pháp luật, người được uỷ quyền đi nộp + đơn vị của họ.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai, thêm hai ô Fax (cổng cũ có nguồn Fax của người nộp/tổ chức). Ô "Ghi chú" không điền.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[fax]": "dom-input", "data[ownerFax]": "dom-input"}
