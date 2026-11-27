"""Map facts nguồn sang Form.io cổng iGate Ninh Bình — tách thửa hoặc hợp thửa đất (1.012784, quy trình "Phi địa giới").

Theo file mapping "Tách thửa - Phi địa giới" (DOM cổng Ninh Bình, bản "Phi địa giới" và "Phi địa giới - Miền núi" cùng ô):
- Thông tin người nộp  -> data[fullname]/birthday/phoneNumber/email/identityNumber/identityDate/identityAgency/province/
                          village/address. Chủ hồ sơ là TỔ CHỨC: thêm data[organization]/taxCode/province1/village1/
                          address1, phần cá nhân là người đại diện/được ủy quyền.
- Địa chỉ thửa đất     -> data[TuCachNguoiNopHoSo]/SoThuaDat/SoToBanDo/diaChiThuaDat/village2. data[province2] cổng khoá
                          "Tỉnh Ninh Bình" và danh mục Phường/Xã chỉ có xã Ninh Bình: thửa đất ở tỉnh khác thì không chọn
                          village2 và cảnh báo cán bộ (hồ sơ phải nộp ở cổng tỉnh có thửa đất).
- Người nhận kết quả   -> data[hoTen]/soCCCD/diaChi = người nộp. data[hinhThucNopHs] cổng chọn sẵn "Trực tuyến".
Người nộp khác tên chủ hồ sơ = có ủy quyền: khối người nộp chỉ dùng facts của bên được ủy quyền, không mượn chéo.

Cổng đổ sẵn khối người nộp theo tài khoản đăng nhập (sai người khi cán bộ nộp thay) → ô chữ/ngày giấy tờ không có thì TRẢ VỀ
TRỐNG (clear, ô bắt buộc tô đỏ + nhắc trong cảnh báo); chỉ giữ giá trị cổng khi formContext cho thấy tài khoản chính là người
nộp (cùng số định danh). Ô chọn Tỉnh/Phường-xã không xoá.
"""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import canonical_province, canonical_ward
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import _date_loose, _phone_vn, phone_warning
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
    _area,
    _by_name,
    _fold,
    _identity,
    _is_to_chuc,
    _parcel_number,
    _province,
    _text,
    _ward,
    account_is_applicant,
)

from .schema import UI_COMP_BY_NAME

PORTAL_PROVINCE = "Ninh Bình"
TU_CACH_CHU_DAT = "Người sử dụng đất"
TU_CACH_UY_QUYEN = "Người được ủy quyền"

# Khối người nộp cổng đổ sẵn theo tài khoản: giấy tờ không có thì xoá trắng (trừ khi tài khoản chính là người nộp).
_BLANK_PART_ONE = ("data[fullname]", "data[birthday]", "data[phoneNumber]", "data[email]", "data[identityNumber]",
                   "data[identityDate]", "data[address]")
_BLANK_PARCEL = ("data[SoThuaDat]", "data[SoToBanDo]", "data[diaChiThuaDat]")
# Ô có dấu (*) trên form (cột "Bắt buộc điền" của file mapping) -> nhãn nhắc cán bộ khi giấy tờ không có.
_REQUIRED_LABELS = {
    "data[fullname]": "Họ và tên người nộp",
    "data[birthday]": "Ngày sinh người nộp",
    "data[phoneNumber]": "Số điện thoại người nộp",
    "data[identityNumber]": "Số CMND/CCCD người nộp",
    "data[address]": "Địa chỉ chi tiết người nộp",
    "data[village2]": "Phường/Xã của thửa đất",
}


def _is_portal_province(tinh: Any) -> bool:
    return _fold(canonical_province(tinh) or tinh) == _fold(PORTAL_PROVINCE)


def _detail_address(area: dict) -> str | None:
    """Ô "Địa chỉ chi tiết" (bắt buộc): số nhà/thôn/tổ; giấy chỉ ghi tới phường/xã thì ghi "<xã>, <tỉnh>" như cột Dữ liệu
    mẫu của file mapping, không để trống ô bắt buộc."""
    detail = _text(area.get("diaChi"))
    if detail:
        return detail
    return ", ".join(part for part in (_ward(area), _province(area)) if part) or None


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _ward(area), _province(area)]
    return ", ".join(part for part in parts if part) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_area(province_name: str, ward_name: str, address_name: str, area: dict | None, who: str) -> None:
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province_name, _province(area))
        ward = _ward(area)
        add(ward_name, ward)
        add(address_name, _detail_address(area))
        tinh = _text(area.get("tinh"))
        if ward and tinh and not canonical_ward(tinh, ward):
            warnings.append(f"Phường/xã '{ward}' ({who}) không có trong danh mục {_province(area)} — cán bộ chọn lại.")

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))
    if not authorized and owner_name:
        applicant_name = owner_name  # cùng một người: LLM hay trả hai kiểu hoa/thường
    owner_is_org = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)

    def applicant_val(key: str) -> Any:
        if authorized:
            return values.get(f"NguoiNop_{key}")
        value = values.get(f"ChuHoSo_{key}")
        return value if value not in (None, "", {}, []) else values.get(f"NguoiNop_{key}")

    rejected_phones: set[str] = set()

    def phone(value: Any) -> str | None:
        number, rejected = _phone_vn(value)
        if rejected:
            rejected_phones.add(rejected)
        return number

    # Tổ chức đứng tên mà không có người đại diện/được ủy quyền riêng: không biết ai là cá nhân nộp → để trống khối cá nhân.
    person_known = not (owner_is_org and not authorized)
    applicant_id = _identity(applicant_val("SoDinhDanh")) if person_known else None
    applicant_area = _area(applicant_val("DiaChi")) if person_known else None

    # --- Thông tin người nộp ---
    if person_known:
        add("data[fullname]", applicant_name)
        add("data[birthday]", _date_loose(applicant_val("NgaySinh")))
        add("data[phoneNumber]", phone(applicant_val("DienThoai")))
        add("data[email]", _text(applicant_val("Email")))
        add("data[identityNumber]", applicant_id)
        add("data[identityDate]", _date_loose(applicant_val("NgayCap")))
        issuer = _text(applicant_val("NoiCap"))
        add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
        add_area("data[province]", "data[village]", "data[address]", applicant_area, "người nộp")
    else:
        warnings.append(f"Người sử dụng đất là tổ chức ({owner_name}) nhưng giấy tờ không có người đại diện/được ủy quyền "
                        "đi nộp — cán bộ nhập thông tin cá nhân người nộp.")
    if owner_is_org:
        add("data[organization]", owner_name)
        add("data[taxCode]", _identity(values.get("ChuHoSo_MaSoThue")))
        add_area("data[province1]", "data[village1]", "data[address1]", _area(values.get("ChuHoSo_DiaChi")), "tổ chức")

    # --- Địa chỉ thửa đất — chỉ từ nguồn thửa đất, KHÔNG lấy nơi cư trú thay thế ---
    if authorized:
        add("data[TuCachNguoiNopHoSo]", TU_CACH_UY_QUYEN)
    elif owner_name and not owner_is_org:
        add("data[TuCachNguoiNopHoSo]", TU_CACH_CHU_DAT)
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))
    add("data[SoToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    raw_parcel = values.get("ThuaDat_DiaChi")
    parcel_area = _area(raw_parcel)
    full_parcel = _text(values.get("ThuaDat_DiaChiDayDu")) or _full_address(parcel_area)
    add("data[diaChiThuaDat]", full_parcel)
    if parcel_area and _text(parcel_area.get("xa")):
        tinh = _text(parcel_area.get("tinh"))
        if tinh and not _is_portal_province(tinh):
            warnings.append(
                f"Thửa đất ở {_ward(parcel_area)}, {_province(parcel_area)} — cổng Ninh Bình khoá Tỉnh/TP của thửa đất là "
                "Tỉnh Ninh Bình và danh mục Phường/Xã không có xã này; chưa chọn Phường/Xã thửa đất, cán bộ xác nhận lại "
                "địa bàn (hồ sơ thường phải nộp ở cổng tỉnh có thửa đất)."
            )
        else:
            ward = canonical_ward(PORTAL_PROVINCE, parcel_area.get("xa"))
            if ward:
                add("data[village2]", ward)
            else:
                warnings.append(f"Phường/xã thửa đất '{_text(parcel_area.get('xa'))}' không có trong danh mục Tỉnh Ninh "
                                "Bình — cán bộ chọn lại.")

    # --- Người nhận kết quả: đúng người trực tiếp nộp/được ủy quyền ---
    if person_known:
        add("data[hoTen]", applicant_name)
        add("data[soCCCD]", applicant_id)
        add("data[diaChi]", _full_address(applicant_area))

    warnings.extend(phone_warning(rejected_phones))
    if not owner_name:
        warnings.append("Thiếu tên người sử dụng đất đề nghị tách/hợp thửa (Đơn Mẫu số 01/ĐK).")

    keep_part_one = account_is_applicant(options, applicant_id)
    missing = [label for name, label in _REQUIRED_LABELS.items()
               if name not in seen and not (keep_part_one and name in _BLANK_PART_ONE)]
    if missing:
        warnings.append("Ô bắt buộc chưa có trong giấy tờ: " + "; ".join(missing) + " — đã để trống, cán bộ nhập tay.")
    for name in _BLANK_PART_ONE + _BLANK_PARCEL:
        if name in seen or (keep_part_one and name in _BLANK_PART_ONE):
            continue
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True}
        if name in _REQUIRED_LABELS:
            item["markEmpty"] = True
        out.append(item)
        seen.add(name)
    return out, warnings
