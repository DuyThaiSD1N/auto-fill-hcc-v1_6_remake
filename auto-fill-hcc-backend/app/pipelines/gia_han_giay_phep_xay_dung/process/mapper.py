"""Map source facts → Form.io data[...] cho "Gia hạn giấy phép xây dựng" (mã 1.013227, cổng Bộ Xây dựng).

Khối NGƯỜI NỘP / TỔ CHỨC NGƯỜI NỘP / CHỦ HỘ-CHỦ ĐẦU TƯ giống hệt thủ tục điều chỉnh GPXD cùng cổng → dùng lại
helper chuẩn hoá của dieu_chinh_giay_phep_xay_dung. Phần tờ đơn (địa điểm, GPXD đã cấp, loại đề nghị, lý do
gia hạn, cam kết, ký đơn) dùng field-key riêng của form gia hạn — xem schema.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.dieu_chinh_giay_phep_xay_dung.process.mapper import (
    _area,
    _birthday_from_year,
    _commune_label,
    _date,
    _extract_info_from_cccd,
    _fold,
    _form_context,
    _has_context_anchor,
    _identity,
    _infer_gender_from_title,
    _issuer,
    _looks_individual_owner,
    _ma_so_doanh_nghiep,
    _multiline_text,
    _number,
    _phone,
    _pick,
    _province_label,
    _same_person,
    _text,
)
from app.pipelines.gia_han_giay_phep_xay_dung.process.schema import REQUEST_TYPE_GIA_HAN, UI_COMP_BY_NAME

# Ô nhân thân người nộp mà extension chịu trách nhiệm điền; thiếu dữ liệu → phát "dom-expect" (FE tô đỏ).
_EXPECT_PERSON_FIELDS = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)

# data[province] xuất hiện HAI lần trên form: lần 0 = nơi cư trú người nộp, lần 1 = tỉnh của lô đất.
_PROVINCE_NGUOI_NOP = 0
_PROVINCE_LO_DAT = 1

# Mục 4 Đơn thường chỉ ghi cụt "Gia hạn giấy phép" — ô Lý do gia hạn bắt buộc nên ghép thêm GPXD tham chiếu.
_GENERIC_REASONS = {"gia han", "gia han giay phep", "gia han giay phep xay dung", "gia han gpxd"}

_PERSON_SPLIT = re.compile(r"\s+-\s+|\s*[;,]\s*|\s+và\s+|\s+&\s+", re.IGNORECASE)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _first_person(value: Any) -> str | None:
    """Đơn đứng tên hai vợ chồng ('A - B') nhưng form chỉ có MỘT ô người nộp → người đứng đầu."""
    text = _text(value)
    if not text:
        return None
    return next((p.strip() for p in _PERSON_SPLIT.split(text) if p.strip()), None)


def _identities(value: Any) -> list[str]:
    """Tách các số định danh trong một chuỗi ('0xx - 0yy', 'A: 0xx; B: 0yy'). Bỏ nhóm dưới 9 chữ số."""
    text = _text(value)
    if not text:
        return []
    out: list[str] = []
    for part in re.split(r"\s+-\s+|[;,/]|\s+và\s+", text):
        digits = re.sub(r"\D+", "", part)
        if len(digits) >= 9 and digits not in out:
            out.append(digits)
    if not out:
        digits = _identity(text)
        return [digits] if digits else []
    return out


def _months(value: Any) -> str | None:
    """Ô 'Dự kiến thời gian hoàn thành' chỉ nhận số tháng ('12 tháng' → '12')."""
    return _number(value)


def _land_location(thua: str | None, to: str | None, duong: str | None) -> tuple[str | None, str | None]:
    """(data[locationAt], data[street]). Thửa đất không có tên đường thì Đơn ghi tờ bản đồ vào ô 'đường'."""
    location = None
    if thua:
        location = thua if _fold(thua).startswith("thua") else f"Thửa đất số {thua}"
    if duong:
        if location and to:
            location = f"{location}, tờ bản đồ số {to}"
        return location, duong
    return location, f"Tờ bản đồ số {to}" if to else None


def _extension_reason(raw: Any, gpxd_so: str | None, gpxd_ngay: str | None, gpxd_cq: str | None) -> str | None:
    reason = _multiline_text(raw)
    if reason and re.sub(r"[^a-z ]+", "", _fold(reason)).strip() not in _GENERIC_REASONS:
        return reason
    if not gpxd_so:
        return reason
    ref = f"Giấy phép xây dựng số {gpxd_so}"
    if gpxd_ngay:
        ref += f" ngày {gpxd_ngay}"
    if gpxd_cq:
        ref += f" của {gpxd_cq}"
    return f"Đề nghị gia hạn {ref}."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()
    context = _form_context(options)

    def add(name: str, value, occurrence: int | None = None) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        out.append(item)
        seen.add(key)

    owner_name = _text(_pick(values.get("ChuHo_HoTen"), values.get("Applicant_HoTen")))
    owner_ids = _identities(_pick(values.get("ChuHo_SoDinhDanh"), values.get("Applicant_SoDinhDanh")))
    owner_identity = " - ".join(owner_ids) or None
    owner_phone = _phone(_pick(values.get("ChuHo_DienThoai"), values.get("Applicant_DienThoai")))

    # NGƯỜI NỘP = MỘT người: thiếu Applicant_* thì lấy người ĐỨNG ĐẦU của chủ hộ (tên + số đầu tiên).
    submitter_name = _text(values.get("Applicant_HoTen")) or _first_person(values.get("ChuHo_HoTen"))
    submitter_ids = _identities(values.get("Applicant_SoDinhDanh")) or owner_ids[:1]
    submitter_identity = submitter_ids[0] if submitter_ids else None
    submitter_phone = _phone(_pick(values.get("Applicant_DienThoai"), values.get("ChuHo_DienThoai")))
    submitter_residence = _area(values.get("Applicant_NoiCuTru"))

    # Người nộp là tổ chức CHỈ khi chủ đầu tư cũng là tổ chức — chặn LLM nhét đơn vị thiết kế/tư vấn vào.
    owner_is_individual = _looks_individual_owner(values)
    org_name = _text(values.get("ToChucNop_Ten"))
    org_tax = _ma_so_doanh_nghiep(values.get("ToChucNop_MaSoThue")) or _identity(values.get("ToChucNop_MaSoThue"))
    is_org_submitter = bool(org_name or org_tax) and not owner_is_individual

    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(submitter_identity, submitter_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    if can_fill_applicant:
        add("data[chonDoiTuong]", "Tổ chức" if is_org_submitter else "Cá nhân")
        add("data[fullname]", submitter_name)
        add("data[birthday]", _birthday_from_year(values.get("Applicant_NgaySinh"), values.get("Applicant_NamSinh"), submitter_identity))
        gender = (
            _text(values.get("Applicant_GioiTinh"))
            or _extract_info_from_cccd(submitter_identity).get("gender")
            or _infer_gender_from_title((options or {}).get("_ocr_text", "") or "", submitter_name)
        )
        if gender:
            g = _fold(gender)
            gender = "Nữ" if "nu" in g else ("Nam" if "nam" in g else None)
        add("data[gender]", gender)
        add("data[email]", _text(values.get("Applicant_Email")))
        add("data[identityNumber]", submitter_identity)
        add("data[identityDate]", _date(values.get("Applicant_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("Applicant_NoiCap")))
        add("data[phoneNumber]", submitter_phone)
        add("data[nation]", "Việt Nam" if submitter_name or submitter_identity else None)
        if submitter_residence:
            add("data[province]", _province_label(submitter_residence.get("tinh")), occurrence=_PROVINCE_NGUOI_NOP)
            add("data[district]", _commune_label(submitter_residence.get("xa")), occurrence=_PROVINCE_NGUOI_NOP)
            add("data[address]", _text(submitter_residence.get("diaChi")))
        for _name in _EXPECT_PERSON_FIELDS:
            if (_name, None) not in seen:
                out.append({"name": _name, "comp": "dom-expect", "value": ""})
                seen.add((_name, None))

    # Tổ chức người nộp (Phần II, chỉ hiện khi chọn 'Tổ chức').
    if is_org_submitter:
        add("data[organization]", org_name)
        add("data[taxCode]", org_tax)
        add("data[organizationPhoneNumber]", _phone(values.get("ToChucNop_DienThoai")))
        org_area = _area(values.get("ToChucNop_DiaChi"))
        if org_area:
            add("data[nation1]", "Việt Nam")
            add("data[province1]", _province_label(org_area.get("tinh")))
            add("data[district1]", _commune_label(org_area.get("xa")))
            add("data[address1]", _text(org_area.get("diaChi")))

    # GPXD đã cấp — đọc trước để dùng cho Kính gửi / lý do gia hạn.
    gpxd_so = _text(values.get("GPXD_So"))
    gpxd_ngay = _date(values.get("GPXD_NgayCap"))
    gpxd_cq = _text(values.get("GPXD_CoQuanCap"))
    kinh_gui = _text(values.get("Don_KinhGui"))

    add("data[recipient]", kinh_gui or gpxd_cq)

    # Chủ hộ (cá nhân/hộ gia đình) hoặc chủ đầu tư (tổ chức). Radio đứng trước để fieldset con kịp hiện.
    if owner_is_individual:
        add("data[loaiHinhChuDauTu]", "chuHo")
        add("data[tenChuHo]", owner_name)
        add("data[soDinhDanhChuHo]", owner_identity)
        add("data[soDienThoaiChuHo]", owner_phone)
    else:
        add("data[loaiHinhChuDauTu]", "chuDauTu")
        add("data[tenChuDauTu]", _text(_pick(values.get("ChuDauTu_TenToChuc"), owner_name)))
        add("data[nguoiDaiDien]", _text(values.get("ChuDauTu_NguoiDaiDien")))
        add("data[chucVu]", _text(values.get("ChuDauTu_ChucVu")))
        add("data[maSoDoanhNghiepCDT]", _ma_so_doanh_nghiep(values.get("ChuDauTu_MaSoDoanhNghiep")))
        add("data[soDinhDanhNguoiDaiDien]", owner_identity)
        add("data[soDienThoaiNguoiDaiDien]", owner_phone)

    # Địa điểm xây dựng.
    add("data[lotNumber]", _text(values.get("Dat_LoDatSo")))
    add("data[landArea]", _number(values.get("Dat_DienTich")))
    location_at, street = _land_location(
        _text(values.get("Dat_ThuaDatSo")), _text(values.get("Dat_ToBanDoSo")), _text(values.get("Dat_DuongPho")),
    )
    add("data[locationAt]", location_at)
    add("data[street]", street)
    land_area = _area(values.get("Dat_DiaDiemXayDung"))
    land_province = _province_label(land_area.get("tinh")) if land_area else None
    if land_area:
        add("data[province]", land_province, occurrence=_PROVINCE_LO_DAT)
        add("data[phuongxaaa]", _commune_label(land_area.get("xa")))

    # GPXD đã được cấp.
    add("data[existingPermitNumber]", gpxd_so)
    add("data[NgayCap]", gpxd_ngay)
    add("data[existingPermitAuthority]", gpxd_cq or kinh_gui)
    add("data[existingPermitContent]", _multiline_text(values.get("GPXD_NoiDung")))

    # Loại đề nghị PHẢI chọn trước để cổng mở ô Lý do đề nghị gia hạn.
    add("data[requestType]", REQUEST_TYPE_GIA_HAN)
    add("data[extensionReason]", _extension_reason(values.get("GiaHan_LyDo"), gpxd_so, gpxd_ngay, gpxd_cq))
    add("data[estimatedCompletionMonths]", _months(values.get("CongTrinh_ThoiGianDuKienHoanThanh")))
    add("data[commitment]", True)

    # Ký đơn: Tỉnh nơi làm đơn theo lô đất (cơ quan cấp phép ở đó), thiếu thì theo nơi cư trú người nộp.
    residence_province = _province_label(submitter_residence.get("tinh")) if submitter_residence else None
    add("data[tinhthanhqwaasa]", land_province or residence_province)
    add("data[KyGhiRoHoTen]", _text(values.get("Don_NguoiKy")) or owner_name)
    if gpxd_so:
        add("data[tenHoSo]", f"Gia hạn Giấy phép xây dựng số {gpxd_so}")

    if not owner_name:
        warnings.append("Thiếu tên chủ đầu tư/chủ hộ đứng tên công trình.")
    if not gpxd_so:
        warnings.append("Chưa đọc được số Giấy phép xây dựng đã cấp — vui lòng kiểm tra GPXD/Đơn (mục 3).")
    if not _multiline_text(values.get("GPXD_NoiDung")):
        warnings.append("Chưa bóc tách được Nội dung Giấy phép đã cấp — ô bắt buộc, vui lòng nhập tay.")
    if not _months(values.get("CongTrinh_ThoiGianDuKienHoanThanh")):
        warnings.append("Chưa đọc được Dự kiến thời gian hoàn thành (số tháng) ở mục 5 Đơn.")

    return out, warnings
