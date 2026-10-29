"""Compact schema cho thủ tục 1.115670 — Lào Cai, cổng iGate MỚI (Form.io).

"Đăng ký biến động … do chia, tách, hợp nhất, sáp nhập tổ chức hoặc chuyển đổi mô hình tổ chức, chuyển đổi loại hình
doanh nghiệp …; điều chỉnh quy hoạch xây dựng chi tiết; cấp Giấy chứng nhận cho từng thửa đất theo quy hoạch xây dựng
chi tiết cho chủ đầu tư dự án có nhu cầu" — nộp tại Sở Nông nghiệp và Môi trường. Dữ kiện nguồn giữ NGUYÊN schema
pipeline cổng cũ (dang_ky_bien_dong_chia_tach_to_chuc_lao_cai): khối nhân thân cùng dạng 1.115650, thêm trích yếu Đơn.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng bảng ô UI của 1.115652 (bộ ô chung + ô
"Ghi chú" data[tenHoSo]): cổng mới không còn ô "Về việc" nên trích yếu hồ sơ ghi vào "Ghi chú".
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
