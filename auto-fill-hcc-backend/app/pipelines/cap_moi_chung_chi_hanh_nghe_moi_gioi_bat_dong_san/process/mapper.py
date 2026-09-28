"""Map compact source facts → Form.io data[...] fields cho "Cấp mới chứng chỉ hành nghề môi giới bất động sản"
(1.012906).

Theo mapping của thủ tục (sheet Cá nhân + Tổ chức):
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] cổng đổ từ tài khoản → KHÔNG phát. Giới
  tính, ngày cấp, nơi cấp, SĐT, địa chỉ: người đề nghị chính là tài khoản → lấy của người đề nghị; nộp thay → chỉ
  lấy từ CCCD KHỚP tài khoản; không có thẻ thì giới tính suy từ số định danh của tài khoản.
- Phần I-b doanh nghiệp: chỉ khi hồ sơ có giấy tờ của tổ chức → data[chonDoiTuong] = "Tổ chức" + panel doanh
  nghiệp. "Đơn vị công tác" trên đơn cá nhân không đủ căn cứ.
- Phần II Đơn đăng ký dự thi sát hạch = người đề nghị. data[birthday] trùng key Phần I → gắn DON_SCOPE.
  data[dateTime] cổng tự điền ngày nộp (disabled) → bỏ.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.mapper import _date
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process.schema import (
    DON_SCOPE,
    DON_SCOPE_NEAR,
    DON_SCOPED_FIELDS,
    ID_TYPE_LABELS,
    NGUOI_NOP_MARKERS,
    UI_COMP_BY_NAME,
)
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _person_matches
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _email,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _text,
)

_PROVINCE_PREFIX_RE = re.compile(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", re.IGNORECASE)


def _province(value: Any) -> str | None:
    """Nhãn option tỉnh/TP (34 tỉnh): lấy phần CUỐI của chuỗi địa danh ("Xã A, huyện B, Đà nẵng" → "Thành phố Đà
    Nẵng"), bỏ tiền tố TP/T.P rồi viết hoa chữ đầu mỗi từ để khớp option."""
    text = _text(value)
    if not text:
        return None
    last = [p for p in re.split(r"\s*[,;]\s*|\s+-\s+", text) if p.strip(" .")][-1].strip(" .")
    bare = _PROVINCE_PREFIX_RE.sub("", last).strip()
    if not bare:
        return None
    return province_label(" ".join(w[:1].upper() + w[1:] for w in bare.split()))


# Tỉnh cũ đã nhập trước 2025 mà bảng remap không có (quê quán trên CCCD vẫn hay ghi).
_OLD_PROVINCES = {"ha tay": "Hà Nội"}


def _noi_sinh_province(value: Any) -> str | None:
    """Quê quán / nơi đăng ký khai sinh trên CCCD ("Tân Phú, Phú Ninh, Quảng Nam") → tỉnh/TP HIỆN HÀNH trong danh mục
    34 tỉnh ("Thành phố Đà Nẵng"). Chỉ remap theo tỉnh — xã/huyện cũ không cần cho ô này."""
    text = _text(value)
    if not text:
        return None
    last = [p for p in re.split(r"\s*[,;]\s*|\s+-\s+", text) if p.strip(" .")][-1].strip(" .")
    bare = _PROVINCE_PREFIX_RE.sub("", last).strip()
    if not bare:
        return None
    tinh = _OLD_PROVINCES.get(_fold(bare))
    if not tinh:
        remapped = remap_area({"quocGia": "Việt Nam", "tinh": bare, "xa": "", "diaChi": ""},
                              allow_diachi_fallback=False)
        tinh = (remapped or {}).get("tinh") or bare
    return _province(tinh)


def _kinh_gui_province(value: Any) -> str | None:
    """"Sở Xây dựng thành phố Đà Nẵng" → "Thành phố Đà Nẵng"."""
    m = re.search(r"\b(tỉnh|thành\s*phố|tp\.?)\s+(.+)$", _text(value) or "", re.IGNORECASE)
    return _province(m.group(2)) if m else None


def _id_type(value: Any, number: str | None) -> str | None:
    folded = _fold(value)
    if "chieu" in folded or "passport" in folded:
        return ID_TYPE_LABELS["ho_chieu"]
    if "cmnd" in folded or "chung minh" in folded:
        return ID_TYPE_LABELS["cmnd"]
    # "Thẻ Căn cước công dân" là CCCD; "Thẻ căn cước" trơn là mẫu từ 01/7/2024.
    if "cccd" in folded or "can cuoc cong dan" in folded:
        return ID_TYPE_LABELS["cccd"]
    if "can cuoc" in folded:
        return ID_TYPE_LABELS["the_can_cuoc"]
    if number and number.isdigit():
        return ID_TYPE_LABELS["cccd"] if len(number) == 12 else ID_TYPE_LABELS["cmnd"] if len(number) == 9 else None
    return None


def _id_number(value: Any) -> str | None:
    """CCCD/CMND chỉ chữ số; hộ chiếu giữ chữ cái đầu (vd "C1234567")."""
    text = re.sub(r"\s+", "", _text(value) or "").upper()
    if re.fullmatch(r"[A-Z]{1,2}\d{6,8}", text):
        return text
    return _identity(text)


def _van_bang(value: Any) -> str | None:
    items = value if isinstance(value, list) else [value] if value not in (None, "") else []
    lines: list[str] = []
    for item in items:
        for line in re.split(r"\s*[\n;]\s*", _text(item) or ""):
            line = re.sub(r"^\s*(?:\d{1,2}\s*[).:-]|[-–•+])\s*", "", line).strip()
            folded = _fold(line)
            if line and "can cuoc" not in folded and "cccd" not in folded and line not in lines:
                lines.append(line)
    return "\n".join(lines) or None


def _yes(value: Any) -> bool:
    return _fold(value) in {"co", "true", "1", "yes", "x"}


def _full_address(value: Any, area: dict | None) -> str | None:
    text = _text(value)
    if text:
        return text
    if not area:
        return None
    parts = [_text(area.get(k)) for k in ("diaChi", "xa", "tinh")]
    return ", ".join(p for p in parts if p) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in DON_SCOPED_FIELDS:
            field["scope"] = DON_SCOPE
            field["scopeNear"] = DON_SCOPE_NEAR
            field["scopeAway"] = list(NGUOI_NOP_MARKERS)
        out.append(field)
        seen.add(name)

    def add_area(province_key: str, district_key: str, address_key: str, area: dict | None) -> bool:
        if not area:
            return False
        add(province_key, _province(area.get("tinh")))
        add(district_key, _text(area.get("xa")))
        add(address_key, _text(area.get("diaChi")))
        return True

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    name = _text(values.get("NguoiDeNghi_HoTen"))
    id_number = _id_number(values.get("NguoiDeNghi_SoGiayTo"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    self_submit = has_ctx and bool(name or id_number) and _person_matches(name, id_number, ctx_name, ctx_identity)

    # --- Phần I-b: tổ chức nộp hồ sơ (chỉ khi có giấy tờ của tổ chức) ---
    org_name = _text(values.get("ToChuc_Ten"))
    org_tax = _identity(values.get("ToChuc_MaSoThue"))
    is_to_chuc = bool(org_name or org_tax)
    if is_to_chuc:
        # Đổi đối tượng TRƯỚC để cổng mở panel doanh nghiệp rồi mới điền.
        add("data[chonDoiTuong]", "Tổ chức")

    # --- Phần I: người nộp ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_ok = has_ctx and bool(nop_name or nop_id) and _person_matches(nop_name, nop_id, ctx_name, ctx_identity)
    nop_area_filled = False
    if self_submit:
        add("data[gender]", _gender(values.get("NguoiDeNghi_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiDeNghi_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiDeNghi_NoiCap")))
        add("data[email]", _email(values.get("NguoiDeNghi_Email")))
        nop_area_filled = add_area("data[province]", "data[district]", "data[address]", residence)
    if nop_ok:
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        nop_area_filled = add_area("data[province]", "data[district]", "data[address]",
                                   _area(values.get("NguoiNop_DiaChi"))) or nop_area_filled
    if nop_area_filled:
        add("data[nation]", "Việt Nam")
    add("data[gender]", _gender_from_identity(ctx_identity))
    nop_phone = _phone(values.get("NguoiNop_DienThoai")) if has_ctx else None
    add("data[phoneNumber]", (phone if self_submit else None) or nop_phone)

    if is_to_chuc:
        add("data[organization]", org_name)
        add("data[taxCode]", org_tax)
        add("data[organizationPhoneNumber]", _phone(values.get("ToChuc_DienThoai")))
        org_area = _area(values.get("ToChuc_DiaChi"))
        if org_area:
            add("data[nation1]", "Việt Nam")
            add_area("data[province1]", "data[district1]", "data[address1]", org_area)

    # --- Phần II: Đơn đăng ký dự thi sát hạch = người đề nghị ---
    kinh_gui = _text(values.get("Don_KinhGui"))
    tai = (
        _province(values.get("Don_DiaDanh"))
        or _kinh_gui_province(kinh_gui)
        or (_province(residence.get("tinh")) if residence else None)
    )
    add("data[TinTTTe1]", tai)
    add("data[recipient]", kinh_gui)
    add("data[fullName]", name)
    add("data[birthday]", _date(values.get("NguoiDeNghi_NgaySinh")))
    noi_sinh = _noi_sinh_province(values.get("NguoiDeNghi_NoiSinh"))
    add("data[provincenoisinh]", noi_sinh)
    nation = _text(values.get("NguoiDeNghi_QuocTich"))
    add("data[nationality]", "Việt Nam" if not nation or "viet nam" in _fold(nation) or _fold(nation) == "vnm"
        else nation)
    add("data[idType]", _id_type(values.get("NguoiDeNghi_LoaiGiayTo"), id_number))
    add("data[idNumber]", id_number)
    add("data[CapNGay]", _date(values.get("NguoiDeNghi_NgayCap")))
    add("data[idIssuePlace]", _issuer(values.get("NguoiDeNghi_NoiCap")))
    add("data[permanentAddress]", _full_address(values.get("NguoiDeNghi_DiaChiThuongTru"), residence))
    add("data[contactPhone]", phone)
    van_bang = _van_bang(values.get("NguoiDeNghi_VanBang"))
    add("data[educationCertificates]", van_bang)
    if _yes(values.get("Don_CamKet")):
        add("data[commitment]", True)
    add("data[KyGhiRoHoTen]", _text(values.get("Don_NguoiLamDon")) or name)

    # --- Cảnh báo ---
    loai_don = _fold(values.get("Don_Loai"))
    if "cap_lai" in loai_don.replace(" ", "_"):
        warnings.append("Hồ sơ là ĐƠN XIN CẤP LẠI chứng chỉ hành nghề môi giới BĐS, trong khi thủ tục đang chọn là CẤP "
                        "MỚI (Đơn đăng ký dự thi sát hạch theo Phụ lục XXI NĐ 96/2024/NĐ-CP) — kiểm tra lại thủ tục. "
                        "Đã điền các mục nhân thân trùng nghĩa.")
    elif not loai_don:
        warnings.append("Không thấy Đơn đăng ký dự thi sát hạch trong hồ sơ — kiểm tra lại các mục của đơn.")
    if not name:
        warnings.append("Không đọc được họ tên người đề nghị (CCCD / đơn) — vui lòng nhập tay mục Họ và tên của đơn.")
    if not id_number:
        warnings.append("Chưa có số giấy tờ tùy thân của người đề nghị — vui lòng nhập tay ô Số.")
    if not noi_sinh:
        warnings.append("Chưa đọc được Nơi sinh (bắt buộc) từ CCCD (Quê quán / Nơi đăng ký khai sinh) — vui lòng chọn "
                        "tay tỉnh/thành phố.")
    if not van_bang:
        warnings.append("Chưa có văn bằng, chứng chỉ (tốt nghiệp THPT trở lên) — nhập tay mục Văn bằng, chứng chỉ đã "
                        "được cấp.")
    if not tai:
        warnings.append("Chưa xác định được tỉnh/TP nơi làm đơn (ô 'Tại', bắt buộc) — vui lòng chọn tay.")
    if not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền nhân thân người nộp (Phần I), "
                        "vui lòng nhập tay.")
    elif not self_submit and not nop_ok:
        warnings.append("Người nộp (tài khoản đăng nhập) khác người đề nghị và hồ sơ không có CCCD của người nộp — "
                        "vui lòng tự nhập ngày cấp, nơi cấp, địa chỉ của người nộp.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Hồ sơ không ghi số điện thoại của người nộp — ô Số điện thoại Phần I (bắt buộc) vui lòng "
                        "nhập tay.")
    if is_to_chuc:
        warnings.append("Hồ sơ có giấy tờ của tổ chức — đã chọn đối tượng 'Tổ chức' và điền thông tin doanh nghiệp, "
                        "kiểm tra lại.")
    return out, warnings
