"""Compact schema cho thủ tục 1.115689 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ NGUYÊN schema pipeline cổng cũ (dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai): CCCD, người trong giấy tờ,
bên được ủy quyền, khối ChuHoSo_*/NguoiNop_*, thửa đất + ghi chú hồ sơ.

Bước 1 của cổng mới là ĐÚNG form "FORM NGUOI NOP" (crawl 02/11/2026, UBND Phường Yên Bái) → bảng ô UI của
su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai (bảng chung + hai ô Fax) thêm ô "Ghi chú" data[tenHoSo]: cổng cũ ghi ô
"Ghi chú" (HoSoOnline_ghiChu) ở bước thành phần hồ sơ, cổng mới chỉ còn ô này ở bước 1.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input"}
