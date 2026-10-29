"""Compact schema cho thủ tục 1.115677 — Lào Cai, cổng iGate MỚI (Form.io).

"Xác nhận tiếp tục sử dụng đất nông nghiệp" (Đơn Mẫu số 39) — nộp tại Sở Nông nghiệp và Môi trường. Dữ kiện nguồn giữ
NGUYÊN schema pipeline cổng cũ (xac_nhan_tiep_tuc_dat_nong_nghiep): ứng viên người nộp, danh sách người sử dụng đất mục 1
của Đơn, người làm đơn, khối ChuHoSo_* + liên hệ mục 2.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Ô "Ghi chú" không điền (cổng cũ cũng không ghi đè ô này).
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
