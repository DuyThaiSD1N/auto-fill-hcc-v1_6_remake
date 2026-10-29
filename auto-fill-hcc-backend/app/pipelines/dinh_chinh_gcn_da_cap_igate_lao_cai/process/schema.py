"""Compact schema cho thủ tục 1.115686 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dinh_chinh_gcn_da_cap_lao_cai): CCCD, người trong giấy tờ, bên được
ủy quyền, khối ChuHoSo_*/NguoiNop_*, nội dung đính chính, số hiệu GCN, thửa đất, người đồng sử dụng.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 29/10/2026) → bảng ô UI của
su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai (bảng chung + hai ô Fax) thêm ô "Ghi chú" data[tenHoSo]: cổng mới không còn
ô "Về việc" ở bước thành phần hồ sơ nên nội dung đính chính của cổng cũ dồn vào đây.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}
