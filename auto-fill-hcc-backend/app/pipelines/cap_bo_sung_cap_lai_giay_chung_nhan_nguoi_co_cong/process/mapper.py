"""Map fact Đơn M25 + CCCD + giấy chứng nhận đã cấp sang field Form.io của thủ tục 1.010814.

Theo Mapping_Cap_lai_GCN_than_nhan_liet_si_Bo_Noi_vu.xlsx:
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá theo tài
  khoản → KHÔNG phát ở occurrence 0. Giới tính (DOM hay chọn sẵn sai), ngày cấp, nơi cấp, địa chỉ, SĐT chỉ điền khi
  người làm đơn KHỚP tài khoản đăng nhập; khi đó tích "Người nộp hồ sơ là chủ hồ sơ".
- Phần II chủ hồ sơ = người làm đơn (người được cấp bổ sung/cấp lại).
- Phần III mẫu khai Đơn M25: các ô trùng tên Phần I đi occurrence 1. Quê quán → province1/village1/address1, thường
  trú → province#1 / village / address#1.
- Nguồn nhân thân: CCCD → Đơn M25. Diện, quyết định trợ cấp, lý do: Đơn M25 → giấy chứng nhận đã cấp (chỉ khi giấy
  đó đúng tên người làm đơn — mẫu thật hay là giấy của liệt sĩ, không được chép sang).
"""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process.schema import (
    MAX_HO_SO_ROWS,
    UI_COMP_BY_NAME,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _person_matches,
    _phone,
    _same_name,
    _text,
)

DEFAULT_LOAI_GCN = "Giấy chứng nhận thân nhân liệt sĩ"
DON_TITLE = "Đơn đề nghị cấp bổ sung hoặc cấp lại giấy chứng nhận (Mẫu số 25)"


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _loai_de_nghi(loai: Any, ly_do: Any) -> str | None:
    """Ô select "Loại đề nghị": "Cấp lại" khi giấy bị mất/hư hỏng, "Cấp bổ sung" khi chỉ đổi/bổ sung thông tin."""
    folded = _fold(loai)
    if "lai" in folded:
        return "Cấp lại"
    if "bo sung" in folded:
        return "Cấp bổ sung"
    reason = _fold(ly_do)
    if any(m in reason for m in ("mat", "hu hong", "rach", "chay", "ngap", "khong con doc")):
        return "Cấp lại"
    if "bo sung" in reason or "thay doi" in reason:
        return "Cấp bổ sung"
    return None


def _loai_gcn(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if text == text.upper():  # Tiêu đề in hoa trên giấy chứng nhận.
        text = text.lower()
    return text[0].upper() + text[1:]


def _street_or_area(area: dict | None) -> str | None:
    """Ô "Số nhà, đường" bắt buộc; giấy tờ chỉ ghi tới xã thì nhập lại "xã, tỉnh" như hướng dẫn mapping."""
    if not area:
        return None
    detail = _text(area.get("diaChi"))
    if detail:
        return detail
    parts = [_text(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(key)

    def add_area(province: str, commune: str, address: str, area: dict | None, *, occurrence=None,
                 commune_occurrence=None) -> None:
        if not area:
            return
        add(province, province_label(area.get("tinh")), occurrence=occurrence)
        add(commune, _text(area.get("xa")), occurrence=commune_occurrence)
        add(address, _street_or_area(area), occurrence=occurrence)

    # --- Nhân thân người làm đơn: CCCD → Đơn M25 ---
    name = _text(_pick(values.get("Person1_HoTen"), values.get("Don_HoTen")))
    identity = _identity(_pick(values.get("Person1_SoDinhDanh"), values.get("Don_SoDinhDanh")))
    birthday = _date(_pick(values.get("Person1_NgaySinh"), values.get("Don_NgaySinh")))
    gender = (
        _gender(values.get("Person1_GioiTinh")) or _gender(values.get("Don_GioiTinh"))
        or _gender_from_identity(identity)
    )
    issue_date = _date(_pick(values.get("Person1_NgayCap"), values.get("Don_NgayCap")))
    issuer_raw = _pick(values.get("Person1_NoiCap"), values.get("Don_NoiCap"))
    issuer = _issuer(issuer_raw) or _text(issuer_raw)
    cccd_area = _area(values.get("Person1_NoiCuTru"))
    don_area = _area(values.get("Don_NoiThuongTru"))
    residence = cccd_area if cccd_area and cccd_area.get("tinh") and cccd_area.get("xa") else (don_area or cccd_area)
    phone = _phone(values.get("Don_DienThoai"))

    if not name or not identity:
        warnings.append("Thiếu họ tên hoặc số CCCD của người làm đơn (Đơn Mẫu 25/CCCD).")

    # Giấy chứng nhận cũ chỉ là nguồn dự phòng khi đúng tên người làm đơn.
    gcn_name = _text(values.get("GCN_HoTen"))
    gcn_same = bool(gcn_name and name and _same_name(gcn_name, name))
    if gcn_name and name and not gcn_same:
        warnings.append(
            f"Giấy chứng nhận đã cấp ghi tên '{gcn_name}', khác người làm đơn '{name}' — không lấy số liệu từ "
            "giấy này, cần đối chiếu lại."
        )

    def gcn(key: str):
        return values.get(key) if gcn_same else None

    # --- Mốc tài khoản đăng nhập ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)
    self_submit = not has_ctx or _person_matches(name, identity, ctx_name, ctx_identity)

    # --- Phần I: người nộp (ô họ tên / ngày sinh / số CCCD khoá theo tài khoản) ---
    if self_submit:
        add("data[gender]", gender, occurrence=0)
        add("data[identityDate]", issue_date, occurrence=0)
        add("data[idIssuePlace]", issuer)
        add_area("data[province]", "data[district]", "data[address]", residence, occurrence=0)
        add("data[phoneNumber]", phone, occurrence=0)
        add("data[isOwnerDossierCheck]", True)
        ctx_birthday = _date(ctx.get("applicantBirthday"))
        if ctx_birthday and birthday and ctx_birthday != birthday:
            warnings.append(
                f"Ngày sinh tài khoản đăng nhập ({ctx_birthday}) khác CCCD/Đơn ({birthday}); ô này cổng khoá, "
                "cần kiểm tra lại tài khoản định danh."
            )
    else:
        add("data[isOwnerDossierCheck]", False)
        warnings.append(
            "Người làm đơn không khớp người nộp hồ sơ (tài khoản đang đăng nhập) — để trống phần sửa được của "
            "'Thông tin người nộp hồ sơ', vui lòng tự nhập."
        )

    # --- Phần II: chủ hồ sơ = người làm đơn ---
    add("data[chonDoiTuong1]", "Cá nhân")
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", issue_date)
    add("data[ownerIdIssuePlace]", issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerNation]", "Việt Nam")

    # --- Phần III: mẫu khai Đơn M25 ---
    ly_do = _text(values.get("Don_LyDo"))
    loai_de_nghi = _loai_de_nghi(values.get("Don_LoaiDeNghi"), ly_do)
    add("data[loaiDeNghi]", loai_de_nghi)
    if not loai_de_nghi:
        warnings.append("Chưa xác định được 'Loại đề nghị' (cấp lại/cấp bổ sung) từ Đơn — vui lòng tự chọn.")
    elif "bo sung" in _fold(values.get("Don_LoaiDeNghi")) and loai_de_nghi == "Cấp lại":
        warnings.append("Đơn đề nghị vừa cấp lại vừa cấp bổ sung — đã chọn 'Cấp lại', ghi rõ phần bổ sung ở Lý do.")
    dien = _text(values.get("Don_DienNguoiCoCong"))
    loai_gcn = (
        _loai_gcn(values.get("Don_LoaiGiayChungNhan"))
        or _loai_gcn(values.get("GCN_LoaiGiayChungNhan"))
        or (DEFAULT_LOAI_GCN if "liet si" in _fold(dien) else None)
    )
    add("data[loaiGiayChungNhan]", loai_gcn)
    add("data[fullname]", name, occurrence=1)
    add("data[birthday]", birthday, occurrence=1)
    add("data[gender]", gender, occurrence=1)
    add("data[identityNumber]", identity, occurrence=1)
    add("data[identityDate]", issue_date, occurrence=1)
    add("data[identityAgency]", issuer)
    add("data[phoneNumber]", phone, occurrence=1)
    que_quan = _area(values.get("Don_QueQuan")) or _area(gcn("GCN_QueQuan"))
    add_area("data[province1]", "data[village1]", "data[address1]", que_quan)
    add_area("data[province]", "data[village]", "data[address]", residence, occurrence=1)
    add("data[dienNguoiCoCong]", dien)

    don_qd = (values.get("Don_SoQuyetDinh"), values.get("Don_NgayQuyetDinh"), values.get("Don_CoQuanQuyetDinh"))
    gcn_qd = (gcn("GCN_SoQuyetDinh"), gcn("GCN_NgayQuyetDinh"), gcn("GCN_CoQuanQuyetDinh"))
    add("data[sqdTroCap]", _text(_pick(don_qd[0], gcn_qd[0])))
    add("data[nqdTroCap]", _date(_pick(don_qd[1], gcn_qd[1])))
    add("data[noiCap]", _text(_pick(don_qd[2], gcn_qd[2])))
    if don_qd[0] and gcn_qd[0] and _fold(don_qd[0]) != _fold(gcn_qd[0]):
        warnings.append(
            f"Số quyết định trợ cấp trên Đơn ({_text(don_qd[0])}) khác giấy chứng nhận ({_text(gcn_qd[0])}) — "
            "đã lấy theo Đơn, cần đối chiếu quyết định gốc."
        )
    add("data[lyDo]", ly_do)

    # --- Bảng "Hồ sơ kèm theo gồm" ---
    rows = [(DON_TITLE, "Bản chính")]
    if any(values.get(k) for k in ("GCN_LoaiGiayChungNhan", "GCN_HoTen", "GCN_SoQuyetDinh")):
        rows.append((f"{loai_gcn or 'Giấy chứng nhận'} đã cấp", "Bản chính"))
    if any(values.get(k) for k in ("Person1_HoTen", "Person1_SoDinhDanh")):
        rows.append(("Căn cước công dân", "Bản sao"))
    for idx, (title, kind) in enumerate(rows[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{idx}][textField1]", title)
        add(f"data[hoSoDinhKem][{idx}][textField2]", kind)

    if not dien:
        warnings.append("Chưa đọc được diện người có công (dòng 'Tôi là') trên Đơn Mẫu 25.")
    return out, warnings
