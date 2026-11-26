"""Prompt rules cho Khánh Hòa - tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148).

Cùng thủ tục, cùng bộ giấy, cùng facts với bản Lâm Đồng → dùng lại nguyên quy tắc đọc giấy, chỉ đổi tên cổng."""

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.prompt import EXTRA_RULES as _LAM_DONG_RULES

# Test khoá: chuỗi này phải còn trong prompt Lâm Đồng, prompt Khánh Hòa không còn chữ "Lâm Đồng" ở dòng tên cổng.
_LAM_DONG_PORTAL = "(cổng DVC Lâm Đồng)"

EXTRA_RULES = _LAM_DONG_RULES.replace(_LAM_DONG_PORTAL, "(cổng DVC Khánh Hòa; thửa đất và người có thể ở tỉnh khác)")
