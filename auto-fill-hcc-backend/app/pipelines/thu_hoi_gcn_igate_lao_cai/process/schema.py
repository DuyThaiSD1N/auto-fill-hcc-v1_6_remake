"""Compact schema cho thủ tục 1.115687 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai): CCCD, người trong
giấy tờ (Bên A/Bên B Giấy ủy quyền), khối ChuHoSo_* (người ĐỨNG ĐƠN, 4 loại đối tượng), liên hệ trên Đơn.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → dùng chung bảng ô UI của
chuyen_doi_md_sd_dat_igate_lao_cai. Fax và "Ghi chú" (data[tenHoSo]) không có nguồn — cổng cũ cũng để nguyên ô "Về việc" /
"Ghi chú" cổng điền sẵn.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
