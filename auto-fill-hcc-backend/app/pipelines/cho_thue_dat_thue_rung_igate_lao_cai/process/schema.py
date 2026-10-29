"""Compact schema cho thủ tục 1.115678 — Lào Cai, cổng iGate MỚI (Form.io).

"Giao đất, cho thuê đất … ; giao đất và giao rừng; cho thuê đất và cho thuê rừng (Điều 3 Quyết định số
40/2026/QĐ-UBND)" — nộp tại UBND phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (cho_thue_dat_thue_rung): khối ChuHoSo_* (người trúng đấu giá /
được giao đất) + NguoiNop_* (bên được ủy quyền; không có ủy quyền thì chép chủ hồ sơ).

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (Form.io _id 6916cf3c3c79b700198bc20d) đã dùng cho 1.115651 — bản
crawl 1.115678 (29/10/2026) ra y hệt bộ ô, logic khoá/ẩn và calculateValue → dùng chung bảng ô UI của pipeline
chuyen_doi_md_sd_dat_igate_lao_cai (xem ghi chú các ô bị khoá/không khai ở file đó).
"""

from app.pipelines.cho_thue_dat_thue_rung.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
