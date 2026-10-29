"""Compact schema cho thủ tục 1.115667 — Lào Cai, cổng iGate MỚI (Form.io).

"Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho người nhận chuyển nhượng
quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất động sản" — nộp tại Sở Nông nghiệp và Môi
trường. Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (cap_GCN_nhan_chuyen_nhuong): DanhSachCccd, NguoiTrongGiayTo,
NguoiDuocUyQuyen + khối ChuHoSo_* (bên NHẬN chuyển nhượng) + SĐT/Email mục 1.d) của Đơn.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (Form.io _id 6916cf3c3c79b700198bc20d, crawl 29/10/2026) như
1.115650/1.115651/1.115652/1.115678 → dùng chung bảng ô UI của chuyen_doi_md_sd_dat_igate_lao_cai. Ô "Ghi chú"
(data[tenHoSo]) không có nguồn → không điền.
"""

from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
