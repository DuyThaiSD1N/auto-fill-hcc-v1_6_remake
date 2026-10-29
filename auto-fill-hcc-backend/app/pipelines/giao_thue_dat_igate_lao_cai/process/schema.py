"""Compact schema cho thủ tục 1.115650 — Lào Cai, cổng iGate MỚI (Form.io).

"Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử dụng đất, không đấu thầu lựa
chọn nhà đầu tư …; giao đất và giao rừng; cho thuê đất và cho thuê rừng" — nộp tại Sở Nông nghiệp và Môi trường.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (giao_thue_dat_lao_cai): danh sách ứng viên người nộp (CCCD, người ghi
trong giấy tờ, bên được ủy quyền) + khối ChuHoSo_* / NguoiNop_*.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (Form.io _id 6916cf3c3c79b700198bc20d) như 1.115651 / 1.115678 —
bản crawl 29/10/2026 ra y hệt bộ ô → dùng chung bảng ô UI của pipeline chuyen_doi_md_sd_dat_igate_lao_cai.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.giao_thue_dat_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
