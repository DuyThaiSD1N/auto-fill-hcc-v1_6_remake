"""Map facts Thông báo Mẫu 01 (điện mặt trời mái nhà, hạ áp) → Form.io data[...] (cổng Bộ Công Thương).

- Loại đối tượng: Tổ chức khi Thông báo ghi mã số doanh nghiệp hoặc tên mang dạng tổ chức (công ty, hộ kinh
  doanh, HTX…); còn lại Cá nhân. Panel được chọn quyết định bộ field-key (PANEL_KEYS: key trần / ...ToChuc).
- Khối tài khoản: chỉ điền khi CCCD trong hồ sơ khớp tài khoản đăng nhập (giống thong_bao_sua_doi_ctkm).
- Chủ hồ sơ: người đứng tên Thông báo. Cá nhân TRÙNG tài khoản → tích "Cũng là thông tin của tài khoản nộp hồ
  sơ" cho cổng tự chép; khác (hoặc tổ chức) → bỏ tích và điền tường minh.
- Công suất/lưu trữ/inverter: Thông báo trước, Bản vẽ thiết kế dự phòng (default); lệch nhau thì cảnh báo.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.schema import (
    CA_NHAN,
    PANEL_KEYS,
    SURPLUS_OPTIONS,
    TO_CHUC,
    UI_COMP_BY_NAME,
)
from app.pipelines.thong_bao_sua_doi_ctkm.process.mapper import (
    _account_anchor,
    _area,
    _area_label,
    _by_name,
    _date,
    _digits,
    _fold,
    _full_address,
    _identity,
    _matches_account,
    _phone,
    _province,
    _submission_province,
    _tax_code,
    _text,
)

_REQUEST = (
    "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ đấu nối với hệ thống điện quốc "
    "gia tại cấp điện áp hạ áp"
)
_DEFAULT_LOCATION = "Trên mái nhà"
# Tên mở đầu bằng các cụm này (trọn từ, đã bỏ dấu) là tổ chức. Không có "truong": trùng họ Trương.
_ORG_PREFIXES = (
    "cong ty", "cty", "tong cong ty", "tap doan", "ho kinh doanh", "hkd", "doanh nghiep", "dntn", "hop tac xa",
    "htx", "chi nhanh", "van phong", "nha may", "xi nghiep", "benh vien", "trung tam", "uy ban", "ubnd",
    "co quan", "to chuc", "hiep hoi", "ngan hang",
)
_ORG_MARKERS = ("tnhh", "co phan", "trach nhiem huu han")


def _is_org(name: Any, tax: Any) -> bool:
    if _digits(tax):
        return True
    words = re.sub(r"[^a-z0-9 ]+", " ", _fold(name)).split()
    folded = " ".join(words)
    return bool(folded) and (
        any(folded == p or folded.startswith(p + " ") for p in _ORG_PREFIXES)
        or any(f" {m} " in f" {folded} " for m in _ORG_MARKERS)
    )


def _title_name(value: Any) -> str | None:
    """Họ tên viết tay → Hoa Đầu Mỗi Chữ (ô cam kết / người ký trên mẫu giấy viết thường)."""
    text = _text(value)
    return " ".join(w[:1].upper() + w[1:].lower() for w in text.split()) if text else None


def _number(value: Any) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    return float(match.group(0).replace(",", ".")) if match else None


def _with_unit(value: Any, unit: str) -> str | None:
    """'26' → '26 kWp'; giá trị đã có chữ (đơn vị) giữ nguyên, chỉ chuẩn 'm2' → 'm²'."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?<=m)2\b", "²", text)
    return f"{text} {unit}" if re.fullmatch(r"[\d.,\s]+", text) else text


def _surplus_option(value: Any) -> str | None:
    folded = _fold(value).replace(" ", "")
    if not folded:
        return None
    if folded.startswith("5.2") or folded in {"2", "khongban"} or "khongban" in folded:
        return "khongBan"
    if folded.startswith("5.1") or folded in {"1", "dongyban"} or "dongyban" in folded:
        return "dongYBan"
    return None


def _same_name(a: Any, b: Any) -> bool:
    fa, fb = _fold(a), _fold(b)
    return bool(fa and fb) and (fa == fb or fa in fb or fb in fa)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, *, default: bool = False, extra: dict | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        if extra:
            item.update(extra)
        out.append(item)
        seen.add(name)

    name = _text(values.get("TB_Ten"))
    tax = _tax_code(values.get("TB_MaSoDoanhNghiep"))
    is_org = _is_org(name, values.get("TB_MaSoDoanhNghiep"))
    panel = 1 if is_org else 0

    def key(logic: str) -> str:
        return PANEL_KEYS[logic][panel]

    if not name:
        warnings.append("Không đọc được tên tổ chức/cá nhân trên Thông báo Mẫu 01 — vui lòng nhập tay mục I.1.")
    if values.get("TB_MaSoDoanhNghiep") and not tax:
        warnings.append(f"Mã số doanh nghiệp đọc được \"{_text(values.get('TB_MaSoDoanhNghiep'))}\" nhưng không đủ "
                        "chữ số — vui lòng nhập tay.")

    # === CCCD ↔ Thông báo ===
    card_name = _text(values.get("Cccd_HoTen"))
    card_id = _identity(values.get("Cccd_SoDinhDanh"))
    notice_id = _identity(values.get("TB_SoDinhDanh"))
    card_is_declarant = not is_org and _same_name(card_name, name)
    person_id = notice_id or (card_id if card_is_declarant else None)
    if card_is_declarant and card_id and notice_id and card_id != notice_id:
        warnings.append(f"Số định danh trên Thông báo ({notice_id}) khác số trên CCCD ({card_id}) — kiểm tra lại.")

    # === Khối TÀI KHOẢN: chỉ khi CCCD trong hồ sơ khớp tài khoản đăng nhập ===
    anchor = _account_anchor(options)
    if card_name or card_id:
        if not any(anchor):
            warnings.append("Chưa đọc được tài khoản đăng nhập trên form — không điền khối thông tin tài khoản.")
        elif not _matches_account(card_name, card_id, anchor):
            warnings.append("CCCD trong hồ sơ không khớp tài khoản đăng nhập — không điền khối thông tin tài khoản.")
        else:
            residence = _area(values.get("Cccd_NoiCuTru"))
            add("data[fullname]", card_name)
            add("data[identityNumber]", card_id)
            add("data[identityDate]", _date(values.get("Cccd_NgayCap")))
            add("data[birthday]", _date(values.get("Cccd_NgaySinh")))
            if residence:
                add("data[province]", _area_label(residence.get("tinh")))
                add("data[district]", _area_label(residence.get("xa")))
                add("data[address]", _text(residence.get("diaChi")))
    add("data[noidungyeucaugiaiquyet]", _REQUEST)

    # === Địa chỉ người đứng tên: Thông báo; cá nhân thiếu thì lùi về nơi cư trú trên CCCD ===
    phone = _phone(values.get("TB_DienThoai"))
    if values.get("TB_DienThoai") and not phone:
        warnings.append(f"Số điện thoại đọc được \"{_text(values.get('TB_DienThoai'))}\" không hợp lệ — vui lòng "
                        "nhập tay.")
    raw_address = values.get("TB_DiaChi")
    address = _area(raw_address)
    address_guessed = False
    if not address and card_is_declarant:
        raw_address = values.get("Cccd_NoiCuTru")
        address = _area(raw_address)
        address_guessed = bool(address)
        if address_guessed:
            warnings.append("Thông báo không ghi địa chỉ — tạm lấy nơi cư trú trên CCCD, vui lòng kiểm tra lại.")

    # === Khối CHỦ HỒ SƠ ===
    declarant_is_account = (not is_org and any(anchor)
                            and _matches_account(name, person_id, anchor))
    if declarant_is_account:
        # Tích sau cùng (extension xếp thứ tự) → cổng chép khối tài khoản sang chủ hồ sơ.
        add("data[isOwnerDossier]", True)
        add("data[phoneNumber]", phone)
    else:
        add("data[isOwnerDossier]", False)
        add("data[ownerFullname]", name.upper() if name and not is_org else name)
        # Cổng điền sẵn CCCD chủ hồ sơ = CCCD tài khoản; tổ chức thì ghi RỖNG để xóa số cá nhân thừa.
        out.append({
            "name": "data[ownerIdentityNumber]",
            "comp": UI_COMP_BY_NAME["data[ownerIdentityNumber]"],
            "value": "" if is_org else (person_id or ""),
        })
        seen.add("data[ownerIdentityNumber]")
        add("data[ownertaxCode]", tax)
        add("data[ownerPhoneNumber]", phone)
        add("data[ownerAddress]", _full_address(raw_address, address), default=address_guessed)

    # === Tờ khai: đầu đơn ===
    kinh_gui = _text(values.get("TB_KinhGui"))
    province = (
        _submission_province(kinh_gui)
        or _province(values.get("TB_DiaDanh"))
        or _province((address or {}).get("tinh"))
    )
    add("data[pn3][tinhThanhPhoNopDon]", province)
    if not province:
        warnings.append("Không xác định được tỉnh nộp đơn — vui lòng chọn tay 'Tỉnh / Thành Phố nộp đơn'.")
    add("data[pn3][ngayNopDon]", _date(values.get("TB_NgayLap")))
    # Chọn panel TRƯỚC các ô của panel (cổng mặc định Cá nhân; Tổ chức phải đổi mới hiện ô).
    add("data[pn3][loaiDoiTuong]", TO_CHUC if is_org else CA_NHAN)

    # === Panel Cá nhân / Tổ chức ===
    ward = (address or {}).get("xa")
    add(key("kinhGui"), kinh_gui or (f"UBND {ward}" if ward else None), default=not kinh_gui)
    add(key("ten"), name.upper() if name and not is_org else name)
    if address:
        add(key("tinh"), _area_label(address.get("tinh")), default=address_guessed)
        add(key("xa"), _area_label(ward), default=address_guessed)
        add(key("diaChi"), _text(address.get("diaChi")), default=address_guessed)
    add(key("dienThoai"), phone)
    if phone and phone.startswith("02") and len(phone) == 11:
        warnings.append("Số điện thoại là số cố định — chọn 'CĐ' ở ô loại điện thoại của tờ khai.")
    add(key("email"), _text(values.get("TB_Email")))
    add(key("maKhachHang"), re.sub(r"\s+", "", _text(values.get("TB_MaKhachHang")) or "").upper())

    location = _text(values.get("TB_ViTriLapDat"))
    add(key("viTri"), location or _DEFAULT_LOCATION, default=not location)
    add(key("ketCau"), _text(values.get("TB_KetCau")))
    add(key("chieuCao"), _with_unit(values.get("TB_ChieuCao"), "m"))
    add(key("dienTichMai"), _with_unit(values.get("TB_DienTichMai"), "m²"))

    for logic, notice_field, drawing_field, unit, label in (
        ("congSuatPV", "TB_CongSuatPV", "BanVe_CongSuatPV", "kWp", "Tổng công suất tấm quang điện"),
        ("luuTru", "TB_LuuTru", "BanVe_LuuTru", "kWh", "Tổng sản lượng điện lưu trữ"),
        ("inverter", "TB_Inverter", "BanVe_Inverter", "kW", "Tổng công suất inverter"),
    ):
        notice_value, drawing_value = values.get(notice_field), values.get(drawing_field)
        if notice_value not in (None, ""):
            add(key(logic), _with_unit(notice_value, unit))
        else:
            add(key(logic), _with_unit(drawing_value, unit), default=True)
        a, b = _number(notice_value), _number(drawing_value)
        if a is not None and b is not None and abs(a - b) > 1e-6:
            warnings.append(f"{label}: Thông báo ghi {_text(notice_value)}, Bản vẽ thiết kế ghi {_text(drawing_value)} "
                            f"({unit}) — kiểm tra lại trước khi nộp.")

    option = _surplus_option(values.get("TB_PhuongAn"))
    if option:
        add(key("phuongAn"), True, extra={"optionValue": option, "optionLabel": SURPLUS_OPTIONS[option]})
    else:
        warnings.append("Chưa xác định được phương án xử lý sản lượng điện dư (mục 5) — vui lòng tích tay.")
    add(key("thoiGian"), _text(values.get("TB_ThoiGianDuKien")))

    # === III. Cam kết + người ký ===
    commit_name = _text(values.get("TB_TenCamKet")) or name
    signer = _text(values.get("TB_NguoiKy"))
    if is_org:
        add(key("camKet"), commit_name)
        add(key("nguoiKy"), _title_name(signer))
    else:
        add(key("camKet"), _title_name(commit_name))
        add(key("nguoiKy"), _title_name(signer or name), default=not signer)

    investor = _text(values.get("BanVe_ChuDauTu"))
    if investor and name and not _same_name(investor, name):
        warnings.append(f"Bản vẽ thiết kế ghi chủ đầu tư \"{investor}\" khác người đứng tên Thông báo \"{name}\" — "
                        "cần thống nhất tư cách (cá nhân/tổ chức) trước khi nộp.")

    return out, warnings
