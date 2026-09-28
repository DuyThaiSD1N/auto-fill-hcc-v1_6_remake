"""Map compact source facts → Form.io data[...] fields cho "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm
kỳ, đại hội bất thường của hội (cấp tỉnh)" (1.012942, cổng DVCQG).

Theo mapping của thủ tục:
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá / mặc định
  → KHÔNG phát. Giới tính, ngày cấp, nơi cấp, địa chỉ chỉ lấy từ CCCD KHỚP tài khoản; không có thẻ thì giới tính
  suy từ số định danh của tài khoản (DOM hay chọn sẵn sai giới tính).
- Phần II chủ hồ sơ = nhân sự dự kiến Chủ tịch (CCCD → Phiếu LLTP số 1 → Sơ yếu lý lịch). data[isOwnerDossierCheck]
  tích khi chủ hồ sơ chính là người nộp. data[ghiChu] = "Báo cáo tổ chức Đại hội <tên hội> nhiệm kỳ ...".
- Phần III datagrid "Hồ sơ kèm theo gồm": mỗi giấy tờ trong hồ sơ một dòng, Loại bản "Bản chính".
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.schema import MAX_HO_SO_ROWS, UI_COMP_BY_NAME
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _paper_names, _person_matches
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date as _date_slash,
    _email,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _text,
)


_VN_DATE_RE = re.compile(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE)


def _date(value: Any) -> str | None:
    """dd/mm/yyyy; Sơ yếu lý lịch / Phiếu LLTP hay ghi "11 tháng 08 năm 1961"."""
    m = _VN_DATE_RE.search(_text(value) or "")
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    return _date_slash(value)


def _loai_dai_hoi(value: Any) -> str:
    """"nhiem_ky" / "bat_thuong" / "thanh_lap"; không rõ → nhiệm kỳ (trường hợp phổ biến nhất)."""
    folded = _fold(value)
    if "bat thuong" in folded:
        return "bat_thuong"
    if "thanh lap" in folded:
        return "thanh_lap"
    return "nhiem_ky"


def _nhiem_ky(value: Any) -> str | None:
    m = re.search(r"(\d{4})\D{1,5}(\d{4})", _text(value) or "")
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _ghi_chu(values: dict) -> str | None:
    """"Báo cáo tổ chức Đại hội Hội X nhiệm kỳ 2026-2031 (Đại hội đại biểu lần thứ VII)"."""
    ten_hoi = _text(values.get("TenHoi"))
    loai = _loai_dai_hoi(values.get("LoaiDaiHoi"))
    nhiem_ky = _nhiem_ky(values.get("NhiemKy"))
    ten_dai_hoi = _text(values.get("TenDaiHoi"))
    if not ten_hoi and not nhiem_ky:
        return None
    if loai == "bat_thuong":
        text = "Báo cáo tổ chức Đại hội bất thường" + (f" của {ten_hoi}" if ten_hoi else "")
    elif loai == "thanh_lap":
        text = "Báo cáo tổ chức Đại hội thành lập" + (f" {ten_hoi}" if ten_hoi else " hội")
    else:
        text = "Báo cáo tổ chức Đại hội" + (f" {ten_hoi}" if ten_hoi else "")
    if nhiem_ky:
        text += f" nhiệm kỳ {nhiem_ky}"
    if ten_dai_hoi:
        text += f" ({ten_dai_hoi})"
    return text


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
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))
    if has_ctx:
        self_submit = bool(owner_name or owner_id) and _person_matches(owner_name, owner_id, ctx_name, ctx_identity)
    else:
        self_submit = False

    # --- Phần I: người nộp — chỉ từ CCCD khớp tài khoản (không có tài khoản: không điền) ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_ok = has_ctx and bool(nop_name or nop_id) and _person_matches(nop_name, nop_id, ctx_name, ctx_identity)
    if nop_ok:
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get("NguoiNop_NoiCap")))
        nop_area = _area(values.get("NguoiNop_DiaChi"))
        if nop_area:
            add("data[province]", province_label(nop_area.get("tinh")))
            add("data[district]", _text(nop_area.get("xa")))
            add("data[address]", _text(nop_area.get("diaChi")))
    elif self_submit:
        # Chủ hồ sơ tự nộp nhưng không có thẻ CCCD riêng: dùng nhân thân của Phiếu LLTP / SYLL.
        add("data[gender]", _gender(values.get("ChuHoSo_GioiTinh")))
        add("data[identityDate]", _date(values.get("ChuHoSo_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get("ChuHoSo_NoiCap")))
        owner_area = _area(values.get("ChuHoSo_DiaChi"))
        if owner_area:
            add("data[province]", province_label(owner_area.get("tinh")))
            add("data[district]", _text(owner_area.get("xa")))
            add("data[address]", _text(owner_area.get("diaChi")))
    add("data[gender]", _gender_from_identity(ctx_identity))
    nop_phone = _phone(values.get("NguoiNop_DienThoai")) if has_ctx else None
    add("data[phoneNumber]", nop_phone or (owner_phone if self_submit else None))

    # --- Phần II: chủ hồ sơ = nhân sự dự kiến Chủ tịch ---
    if owner_name:
        add("data[isOwnerDossierCheck]", self_submit)
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", _date(values.get("ChuHoSo_NgaySinh")))
        add("data[ownerGender]", _gender(values.get("ChuHoSo_GioiTinh")) or _gender_from_identity(owner_id))
        add("data[ownerIdentityNumber]", owner_id)
        add("data[ownerIdentityDate]", _date(values.get("ChuHoSo_NgayCap")))
        add("data[ownerIdIssuePlace]", _issuer(values.get("ChuHoSo_NoiCap")))
        owner_area = _area(values.get("ChuHoSo_DiaChi"))
        if owner_area:
            add("data[ownerProvince]", province_label(owner_area.get("tinh")))
            add("data[ownerDistrict]", _text(owner_area.get("xa")))
            add("data[ownerAddress]", _text(owner_area.get("diaChi")))
        add("data[ownerPhoneNumber]", owner_phone)
        add("data[ownerEmail]", _email(values.get("ChuHoSo_Email")))
        nation = _text(values.get("ChuHoSo_QuocTich"))
        add("data[ownerNation]", "Việt Nam" if not nation or "viet nam" in _fold(nation) else nation)
    add("data[ghiChu]", _ghi_chu(values))

    # --- Phần III: datagrid hồ sơ kèm theo ---
    papers = _paper_names(values.get("DanhMucHoSo"))
    for i, paper in enumerate(papers[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{i}][textField1]", paper)
        add(f"data[hoSoDinhKem][{i}][textField2]", "Bản chính")

    # --- Cảnh báo ---
    if not owner_name:
        warnings.append("Không đọc được nhân sự dự kiến Chủ tịch hội (Sơ yếu lý lịch / Phiếu LLTP số 1) — vui lòng "
                        "nhập tay thông tin chủ hồ sơ.")
    else:
        if not owner_id:
            warnings.append("Chưa có số CCCD của chủ hồ sơ (CCCD / Phiếu LLTP mục 8) — vui lòng nhập tay.")
        if not _area(values.get("ChuHoSo_DiaChi")):
            warnings.append("Không đọc được nơi thường trú của chủ hồ sơ — vui lòng chọn Tỉnh/TP, Phường/xã và nhập "
                            "địa chỉ chi tiết ở Phần II.")
        if not owner_phone:
            warnings.append("Hồ sơ không ghi số điện thoại của chủ hồ sơ — ô SĐT Phần II (bắt buộc) vui lòng nhập tay.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Hồ sơ không ghi số điện thoại của người nộp — ô SĐT Phần I (bắt buộc) vui lòng nhập tay.")
    if not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền nhân thân người nộp (Phần I), "
                        "vui lòng nhập tay.")
    elif not nop_ok and not self_submit:
        warnings.append("Hồ sơ không có CCCD khớp người nộp — vui lòng tự nhập ngày cấp, nơi cấp, địa chỉ của người "
                        "nộp.")
    if not papers:
        warnings.append("Không lập được danh mục 'Hồ sơ kèm theo gồm' — vui lòng nhập tay từng giấy tờ.")
    elif len(papers) > MAX_HO_SO_ROWS:
        warnings.append(f"Hồ sơ có {len(papers)} giấy tờ, chỉ điền {MAX_HO_SO_ROWS} dòng đầu vào 'Hồ sơ kèm theo "
                        "gồm' — nhập thêm phần còn lại.")
    return out, warnings
