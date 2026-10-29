"""Compact schema cho thủ tục 1.115652 — Lào Cai, cổng iGate MỚI (Form.io).

"Điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất" — nộp tại Sở Nông nghiệp và Môi
trường. Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dieu_chinh_giao_dat_lao_cai) — cùng dạng với 1.115650 (ứng
viên người nộp + ChuHoSo_* / NguoiNop_*), thêm trích yếu Đơn (số/ngày quyết định bị điều chỉnh, tên dự án).

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (Form.io _id 6916cf3c3c79b700198bc20d, crawl 29/10/2026) → dùng chung
bảng ô UI của chuyen_doi_md_sd_dat_igate_lao_cai, CỘNG ô "Ghi chú" (data[tenHoSo]): cổng mới không còn ô "Về việc" ở
bước Thành phần hồ sơ nên trích yếu hồ sơ (cổng cũ ghi vào "Về việc") ghi vào đây.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG
from app.pipelines.dieu_chinh_giao_dat_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
