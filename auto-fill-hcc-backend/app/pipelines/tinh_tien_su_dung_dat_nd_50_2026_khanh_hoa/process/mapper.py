"""Map compact source facts → Form.io data[...] cho Khánh Hòa - tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP
(1.115148), theo file mapping "Mapping_HoSo_NopTrucTuyen" (24/11/2026).

Hai khối:
  - Chủ hồ sơ = người đứng Đơn (chủ đầu tư / người đề nghị): ownerFullname, ownerIdentityNumber, ownerBirthday,
    ownerPhoneNumber, ownerAddress (MỘT ô chữ: "<chi tiết>, <Phường/Xã>, <Tỉnh>").
  - Người nộp: có giấy của người nộp thay (Giấy ủy quyền bên B, hoặc CCCD của người KHÁC chủ hồ sơ) → người đó, BỎ tick
    "Người nộp hồ sơ đồng thời là chủ hồ sơ"; còn lại (tự nộp) → chính chủ hồ sơ, TICK ô đó. Bật "Lấy người nộp theo tờ
    khai" (options.submitterMode) → luôn là người đứng Đơn, như các thủ tục Khánh Hòa khác.
Phần người nộp cổng đổ sẵn theo TÀI KHOẢN đăng nhập (ngày sinh, giới tính "Nam"…) và ô ngày sinh chủ hồ sơ cũng đổ sẵn ngày
sinh tài khoản → ô chữ/ngày giấy tờ không có thì TRẢ VỀ TRỐNG (clear, ô bắt buộc tô đỏ) như các thủ tục Khánh Hòa; tài
khoản chính là người nộp thì giữ khối người nộp của cổng.

Nơi ở: CCCD ("Nơi thường trú/Nơi cư trú") hoặc địa chỉ người trên Đơn. Đơn đề nghị cấp GPXD chỉ ghi ĐỊA ĐIỂM XÂY DỰNG
(file mapping để nguồn ưu tiên 2) → thiếu CCCD thì tạm lấy địa chỉ thửa đất cho ô địa chỉ, kèm cảnh báo đối chiếu CCCD.
"Nội dung yêu cầu giải quyết" ghép tất định theo cách cán bộ Khánh Hòa nhập (như đăng ký đất đai lần đầu Khánh Hòa):
"<tên thủ tục> tại TĐ <thửa> TBĐ <tờ> diện tích <m²> địa chỉ <địa chỉ thửa> - <HỌ TÊN CHỦ HỒ SƠ IN HOA>".
"""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import PORTAL_PROVINCE, _person_area, _phone_vn, phone_warning
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
    _by_name,
    _date,
    _first_person,
    _fold,
    _identity,
    _is_to_chuc,
    _province,
    _text,
    _ward,
    account_is_applicant,
    submitter_is_declarant,
)
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.mapper import (
    _cccd_issuer,
    _gender,
    _land_area,
    _number,
)

from .schema import UI_COMP_BY_NAME

REQUEST_TITLE = "Tính hoặc tính lại tiền sử dụng đất"

# Ô chữ / ngày cổng có thể đổ sẵn theo tài khoản: giấy tờ không có thì trả về trống. Select (giới tính, nơi cấp, tỉnh,
# phường/xã) không xoá — engine chưa bỏ chọn được ô Choices, giới tính luôn suy được từ số định danh.
_BLANK_APPLICANT = ("data[fullname]", "data[birthday]", "data[email]", "data[phoneNumber]", "data[identityNumber]",
                    "data[identityDate]", "data[address]")
_BLANK_OWNER = ("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerBirthday]", "data[ownerPhoneNumber]",
                "data[ownerAddress]")
# Ô có dấu bắt buộc trên form (file mapping cột "Bắt buộc điền") → nhãn nhắc cán bộ.
_REQUIRED_LABELS = {
    "data[ownerFullname]": "Họ và tên chủ hồ sơ",
    "data[ownerIdentityNumber]": "CMND/CCCD chủ hồ sơ",
    "data[ownerBirthday]": "Ngày sinh chủ hồ sơ",
    "data[fullname]": "Tên người nộp hồ sơ",
    "data[birthday]": "Ngày sinh người nộp",
    "data[phoneNumber]": "Số điện thoại người nộp",
    "data[identityNumber]": "Số giấy tờ người nộp",
    "data[province]": "Tỉnh/TP người nộp",
    "data[district]": "Phường/xã người nộp",
    "data[address]": "Địa chỉ chi tiết người nộp",
}


def _full_address(area: dict | None) -> str | None:
    """Ô "Địa chỉ chi tiết" của chủ hồ sơ là MỘT ô chữ: "Thôn A, Xã B, Tỉnh C"."""
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _ward(area), _province(area)]
    return ", ".join(part for part in parts if part) or None


def request_text(values: dict, land: dict | None, owner_name: str | None) -> str:
    parts = [REQUEST_TITLE]
    thua, to_ban_do = _number(values.get("ThuaDat_SoThua")), _number(values.get("ThuaDat_SoTo"))
    vi_tri = " ".join(part for part in (f"TĐ {thua}" if thua else "", f"TBĐ {to_ban_do}" if to_ban_do else "") if part)
    if vi_tri:
        parts.append(f"tại {vi_tri}")
    dien_tich = _land_area(values.get("ThuaDat_DienTich"))
    if dien_tich:
        parts.append(f"diện tích {dien_tich} m²")
    dia_chi = _full_address(land)
    if dia_chi:
        parts.append(f"địa chỉ {dia_chi}")
    text = " ".join(parts)
    person = _first_person(owner_name)
    return f"{text} - {person.upper()}" if person else text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    rejected_phones: set[str] = set()

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

    def phone(value: Any) -> str | None:
        number, rejected = _phone_vn(value)
        if rejected:
            rejected_phones.add(rejected)
        return number

    land = _person_area(values.get("ThuaDat_DiaChi"), (PORTAL_PROVINCE,))
    fallback_provinces = ((land or {}).get("tinh"), PORTAL_PROVINCE)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_identity = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_residence = _person_area(values.get("ChuHoSo_ThuongTru"), fallback_provinces)
    if not owner_residence and land:
        owner_residence = land
        warnings.append("Không có CCCD / địa chỉ cư trú của chủ hồ sơ — địa chỉ chủ hồ sơ tạm lấy theo địa chỉ thửa đất "
                        "(địa điểm xây dựng trên Đơn); cán bộ đối chiếu CCCD.")
    owner = {
        "name": owner_name,
        "identity": owner_identity,
        "birthday": _date(values.get("ChuHoSo_NgaySinh")),
        "gender": _gender(values.get("ChuHoSo_GioiTinh"), owner_identity),
        "phone": phone(values.get("ChuHoSo_DienThoai")),
        "email": _text(values.get("ChuHoSo_Email")),
        "id_date": _date(values.get("ChuHoSo_NgayCapCccd")),
        "id_agency": _cccd_issuer(values.get("ChuHoSo_NoiCapCccd"), values.get("ChuHoSo_NgayCapCccd")),
        "residence": owner_residence,
    }

    # Người nộp thay chỉ tính khi thật sự là NGƯỜI KHÁC (LLM có lúc chép lại chính chủ hồ sơ vào object).
    rep = values.get("NguoiNopThay")
    rep = rep if isinstance(rep, dict) else {}
    rep_name = _text(rep.get("hoTen"))
    rep_identity = _identity(rep.get("soDinhDanh"))
    same_as_owner = bool((rep_name and owner_name and _fold(rep_name) == _fold(owner_name))
                         or (rep_identity and owner_identity and rep_identity == owner_identity))
    has_rep = (bool(rep_name or rep_identity) and not same_as_owner
               and not submitter_is_declarant(options, owner_name, "Tổ chức" if values.get("ToChuc_Ten") else None))

    # ---- Chủ hồ sơ ----
    add("data[ownerFullname]", owner["name"])
    add("data[ownerIdentityNumber]", owner["identity"])
    add("data[ownerBirthday]", owner["birthday"])
    add("data[ownerPhoneNumber]", owner["phone"])
    add("data[ownerAddress]", _full_address(owner["residence"]))
    add("data[isOwnerDossier]", not has_rep)

    # ---- Người nộp ----
    if has_rep:
        # Hai người khác nhau → không mượn SĐT/email/nơi ở của chủ hồ sơ cho người đi nộp thay.
        sub = {
            "name": rep_name,
            "identity": rep_identity,
            "birthday": _date(rep.get("ngaySinh")),
            "gender": _gender(rep.get("gioiTinh"), rep_identity),
            "phone": phone(rep.get("dienThoai")),
            "email": None,
            "id_date": _date(rep.get("ngayCapCccd")),
            "id_agency": _cccd_issuer(rep.get("noiCapCccd"), rep.get("ngayCapCccd")),
            "residence": _person_area(rep.get("thuongTru"), fallback_provinces),
        }
    else:
        sub = owner
    add("data[fullname]", sub["name"])
    add("data[birthday]", sub["birthday"])
    add("data[gender]", sub["gender"])
    add("data[email]", sub["email"])
    add("data[phoneNumber]", sub["phone"])
    add("data[identityNumber]", sub["identity"])
    add("data[identityDate]", sub["id_date"])
    add("data[identityAgency]", sub["id_agency"])
    add("data[noidungyeucaugiaiquyet]", request_text(values, land, owner_name))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    residence = sub["residence"]
    # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán → bỏ cả cụm.
    if residence and (_text(residence.get("xa")) or _text(residence.get("diaChi"))):
        add("data[nation]", residence.get("quocGia") or "Việt Nam", default=True)
        add("data[province]", _province(residence))
        ward = _ward(residence)
        add("data[district]", ward)
        add("data[address]", _text(residence.get("diaChi")))
        tinh = _text(residence.get("tinh"))
        if ward and tinh and not canonical_ward(tinh, ward):
            warnings.append(f"Phường/xã '{ward}' (người nộp) không có trong danh mục {_province(residence)} — cán bộ "
                            "chọn lại.")

    if _text(values.get("ToChuc_Ten")) or _is_to_chuc(None, owner_name):
        warnings.append(f"Chủ đầu tư / người đề nghị là tổ chức ({_text(values.get('ToChuc_Ten')) or owner_name}) — "
                        "cán bộ chọn 'Tổ chức' ở Thông tin người nộp và nhập panel thông tin tổ chức.")
    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh chủ hồ sơ từ Đơn hoặc CCCD.")
    if not land:
        warnings.append("Chưa đọc được địa chỉ thửa đất từ Đơn / Giấy chứng nhận.")
    warnings.extend(phone_warning(rejected_phones))

    # ---- Ô giấy tờ không có → trả về TRỐNG (cổng đổ sẵn theo tài khoản) ----
    keep_applicant = account_is_applicant(options, sub["identity"])
    missing = [label for name, label in _REQUIRED_LABELS.items()
               if name not in seen and not (keep_applicant and name in _BLANK_APPLICANT + ("data[province]",
                                                                                         "data[district]"))]
    if missing:
        warnings.append("Ô bắt buộc chưa có trong giấy tờ: " + "; ".join(missing) + " — đã để trống, cán bộ nhập tay.")
    for name in _BLANK_APPLICANT + _BLANK_OWNER:
        if name in seen or (keep_applicant and name in _BLANK_APPLICANT):
            continue
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True}
        if name in _REQUIRED_LABELS:
            item["markEmpty"] = True
        out.append(item)
        seen.add(name)
    return out, warnings
