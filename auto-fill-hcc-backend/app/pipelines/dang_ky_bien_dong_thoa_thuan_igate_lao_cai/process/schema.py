"""Compact schema cho thủ tục 1.115671 — Lào Cai, cổng iGate MỚI (Form.io).

"Đăng ký biến động … theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng; công trình ngầm; tài sản công;
tranh chấp, bản án, phán quyết Trọng tài; xử lý tài sản thế chấp" — nộp tại Sở Nông nghiệp và Môi trường. Dữ kiện nguồn
giữ NGUYÊN schema pipeline cổng cũ (dang_ky_bien_dong_lao_cai): CCCD, người trong giấy tờ, khối ChuHoSo_* (bên đứng tên
SAU biến động, 4 loại đối tượng) + liên hệ Đơn / văn bản căn cứ / GCN ĐKDN.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Ô "Ghi chú" không điền.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.dang_ky_bien_dong_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
