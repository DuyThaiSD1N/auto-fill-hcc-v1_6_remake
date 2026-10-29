"""Compact schema cho thủ tục 1.115666 — Lào Cai, cổng iGate MỚI (Form.io).

"Đăng ký, cấp Giấy chứng nhận đối với trường hợp đã chuyển quyền sử dụng đất trước ngày 01 tháng 8 năm 2024 mà bên
chuyển quyền đã được cấp Giấy chứng nhận nhưng chưa thực hiện thủ tục chuyển quyền" — nộp tại Sở Nông nghiệp và Môi
trường. Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai): khối nhân thân
cùng dạng 1.115650 (ứng viên người nộp + ChuHoSo_* / NguoiNop_*), thêm trích yếu Đơn Mẫu 24 (thửa, tờ bản đồ, địa chỉ).

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng bảng ô UI của 1.115652 (bộ ô chung + ô
"Ghi chú" data[tenHoSo]): cổng mới không còn ô "Về việc" nên trích yếu hồ sơ ghi vào "Ghi chú".
"""

from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
