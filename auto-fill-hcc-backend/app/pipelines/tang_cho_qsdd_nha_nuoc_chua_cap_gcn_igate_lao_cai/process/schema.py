"""Compact schema cho thủ tục 1.115690 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (tang_cho_qsdd_nha_nuoc_chua_cap_gcn): người tặng cho = chủ hồ sơ,
người được uỷ quyền = người nộp, vợ/chồng đồng sử dụng, Giấy chứng nhận + thửa đất (chỉ lưu trace).

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 02/11/2026, UBND Phường Yên Bái) → bảng ô UI của
su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai (bảng chung + hai ô Fax). Ô "Ghi chú" không điền: cổng cũ không có ô nào
cho thửa đất và pipeline cũ cố ý chỉ lưu trace.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]
