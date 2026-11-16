"""Compact schema cho thủ tục 1.115668 — Lào Cai, cổng iGate MỚI (Form.io).

"Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp chuyển đổi … chuyển
nhượng, thừa kế, tặng cho … chuyển nhượng quyền khai thác khoáng sản". Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ
(dang_ky_quyen_su_dung_dat_lao_cai): DanhSachCccd, NguoiTrongGiayTo, NguoiDuocUyQuyen + khối ChuHoSo_* (bên NHẬN quyền)
+ SĐT/Email của Đơn, hợp đồng, GCN đăng ký doanh nghiệp.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (Form.io _id 6916cf3c3c79b700198bc20d, crawl 16/11/2026 ở cổng
test, Chi nhánh VPĐKĐĐ khu vực Yên Bái) như 1.115650/1.115651/1.115667 → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Ô "Ghi chú" (data[tenHoSo]) không có nguồn → không điền.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
