"""Compact schema cho thủ tục 1.115693 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi): người sử dụng đất (cá nhân hoặc
tổ chức) = chủ hồ sơ, người được ủy quyền = người nộp, thửa đất gốc + phần diện tích tăng thêm (chỉ lưu trace).

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 02/11/2026, UBND Phường Yên Bái) → bảng ô UI của
su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai (bảng chung + hai ô Fax). Ô "Ghi chú" không điền: pipeline cũ cố ý để
nguyên ô "Ghi chú" của cổng.
"""

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
