"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115686 (Lào Cai, cổng iGate mới — cấp phường/xã).

Bước 1 có HAI form (crawl 18/11/2026, xem schema.py):

1. "FORM NGUOI NOP" — chọn người GIỮ NGUYÊN mapper cổng cũ (dinh_chinh_gcn_da_cap_lao_cai/process/mapper.py): người nộp
   theo mốc tài khoản (CCCD → người trong giấy tờ → bên được ủy quyền → khối phẳng) hoặc theo tờ khai (khác tài khoản thì
   bỏ khoá Họ tên/CCCD/Ngày sinh); chủ hồ sơ = người đứng tên Đơn, phát đủ cả 3 ô địa chỉ. Phần đổi ô CongDan_*/ChuHoSo_*
   sang data[...] dùng chung `su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o`. Ô "Ghi chú"
   data[tenHoSo] = câu "Về việc" + "Ghi chú" của cổng cũ (thửa đất, người đồng sử dụng).
2. eForm Đơn Mẫu 24 — người sử dụng đất (mục 1) lấy ĐÚNG theo khối chủ hồ sơ vừa chốt (tên/CCCD hoặc tên tổ chức/MST,
   địa chỉ ghép xã + tỉnh, SĐT, email) để hai nơi không lệch nhau; nội dung biến động = câu đính chính + số hiệu GCN;
   giấy tờ kèm (2)/(3) chỉ ghi loại hồ sơ CÓ (CCCD chứng minh sai sót, văn bản ủy quyền); tỉnh ký đơn = Tỉnh Lào Cai;
   người viết đơn = chủ hồ sơ cá nhân. "Kính gửi" theo Đơn, Đơn không ghi thì suy Chi nhánh VPĐKĐĐ theo xã nơi có đất
   (bảng 99 xã → "khu vực …" của ke_khai_links, QĐ 2748/QĐ-UBND) + cảnh báo.

⚑ Hai form trùng tên ô data[fullname]/data[identityNumber]/data[address]/data[phoneNumber]/data[email]: ô người nộp
ghim occurrence 0, ô của Đơn occurrence 1.
"""

from functools import lru_cache

from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.process.schema import UI_COMP_BY_NAME, UI_DON_MAU_24
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process import mapper as _goc
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import _dia_chi, doi_ten_o

# Tên ô có mặt ở CẢ hai form của bước 1.
_TRUNG_TEN = frozenset({"data[fullname]", "data[identityNumber]", "data[address]", "data[phoneNumber]", "data[email]"})
_EXPECT_DON = ("data[kinhGui]", "data[fullname]", "data[identityNumber]", "data[address]", "data[noiDungBienDong]")
_TINH_KY_DON = "Tỉnh Lào Cai"
_CHI_NHANH = "Chi nhánh Văn phòng đăng ký đất đai"


@lru_cache(maxsize=1)
def _khu_vuc_theo_xa() -> dict[str, str]:
    """Bảng xã/phường (fold) → "khu vực <tên>" của Chi nhánh VPĐKĐĐ Lào Cai, lấy từ link cấp Sở 1.115650."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    for link in KE_KHAI_LINKS:
        bang = (((link.get("agencyLevelByAccount") or {}).get("xa") or {}).get("submitCardIncludesByWard"))
        if str(link.get("code")) == "1.115650" and bang:
            # Khoá theo tên BỎ tiền tố Xã/Phường: địa chỉ giấy tờ hay ghi "Yên Bái" trơn.
            return {_goc._fold(_goc._strip_admin_prefix(xa)): khu_vuc for xa, khu_vuc in bang.items()}
    return {}


def _kinh_gui(values: dict) -> tuple[str | None, bool]:
    """(giá trị, có phải suy ra không). Đơn ghi → giữ nguyên; không thì chi nhánh theo xã nơi có đất."""
    tren_don = _goc._plain(values.get("Don_KinhGui"))
    if tren_don and _goc._fold(tren_don).strip(". "):
        return tren_don, False
    thua_dat = _goc._area(values.get("ThuaDat_DiaChi")) or {}
    khu_vuc = _khu_vuc_theo_xa().get(_goc._fold(_goc._strip_admin_prefix(thua_dat.get("xa"))))
    return (f"{_CHI_NHANH} {khu_vuc}", True) if khu_vuc else (None, False)


def _giay_to_kem(values: dict) -> list[str]:
    """Mục 3 (2)/(3) — (1) "Giấy chứng nhận đã cấp" cổng in sẵn. Chỉ ghi loại giấy hồ sơ có thật."""
    kem = []
    if _goc._people(values, "DanhSachCccd"):
        kem.append("Căn cước công dân (giấy tờ chứng minh sai sót thông tin)")
    if values.get("NguoiDuocUyQuyen"):
        kem.append("Văn bản ủy quyền")
    return kem


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = doi_ten_o(_goc, fields, options)
    values = _goc._by_name([{**f, "value": _dia_chi(f.get("value"))} for f in fields])
    ghi_chu = " ".join(x for x in (_goc._ve_viec(values), _goc._ghi_chu(values)) if x)
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    # Form người nộp đứng trước Đơn: ô trùng tên ghim occurrence 0 (kể cả ô khoá theo tờ khai và dom-expect).
    for field in out:
        if field["name"] in _TRUNG_TEN and "occurrence" not in field:
            field["occurrence"] = 0
    out.extend(_don_mau_24(out, values, warnings))
    return out, warnings


def _don_mau_24(nguoi_nop_form: list[dict], values: dict, warnings: list[str]) -> list[dict]:
    chu = {f["name"]: f.get("value") for f in nguoi_nop_form if f.get("comp") != "dom-expect" and not f.get("clear")}
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        field = {"name": name, "comp": UI_DON_MAU_24[name], "value": value}
        if name in _TRUNG_TEN:
            field["occurrence"] = 1
        out.append(field)
        seen.add(name)

    kinh_gui, suy_ra = _kinh_gui(values)
    add("data[kinhGui]", kinh_gui)
    if suy_ra:
        warnings.append(
            f"Đơn Mẫu 24 không ghi \"Kính gửi\" — đã điền \"{kinh_gui}\" theo xã/phường nơi có đất, cán bộ kiểm tra "
            "lại đúng cơ quan tiếp nhận."
        )

    to_chuc = chu.get("data[ChuHS]") not in (None, "Cá nhân")
    if to_chuc:
        ten, so = chu.get("data[ownerOrganizationFullname]"), chu.get("data[ownerTaxCode]")
    else:
        ten, so = chu.get("data[ownerFullname]"), chu.get("data[ownerIdentityNumber]")
        ten = upper_person_name(ten) if ten else None
    add("data[fullname]", ten)
    add("data[identityNumber]", so)
    add("data[address]", ", ".join(
        str(x) for x in (chu.get("data[ownerAddress]"), chu.get("data[ownerDistrict]"), chu.get("data[ownerProvince]"))
        if x
    ))
    add("data[phoneNumber]", chu.get("data[ownerPhoneNumber]"))
    add("data[email]", chu.get("data[ownerEmail]"))
    if not ten:
        warnings.append(
            "Không xác định được người sử dụng đất đứng tên Đơn — mục 1 của Đơn Mẫu 24 đang giữ họ tên/CCCD cổng đổ "
            "theo TÀI KHOẢN, cán bộ sửa lại theo Giấy chứng nhận."
        )

    add("data[noiDungBienDong]", _goc._ve_viec(values))
    for name, giay in zip(("data[giayToKem2]", "data[giayToKem3]"), _giay_to_kem(values)):
        add(name, giay)
    add("data[ngayHtTinh]", _TINH_KY_DON)
    if not to_chuc:
        add("data[nguoiKy]", ten)

    for name in _EXPECT_DON:
        if name not in seen:
            field = {"name": name, "comp": "dom-expect", "value": ""}
            if name in _TRUNG_TEN:
                field["occurrence"] = 1
            out.append(field)
            seen.add(name)
    return out
