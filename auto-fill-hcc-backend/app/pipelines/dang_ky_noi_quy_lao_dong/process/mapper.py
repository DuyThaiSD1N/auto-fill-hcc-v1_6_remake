"""Map compact source facts → Form.io data[...] fields cho "Đăng ký nội quy lao động của doanh nghiệp" (2.001955,
cổng DVCQG — Bộ Nội vụ).

Theo Mapping_DangKy_NoiQuyLaoDong_BoNoiVu.xlsx:
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá theo tài
  khoản → KHÔNG phát. Giới tính, ngày cấp, nơi cấp, địa chỉ, SĐT chỉ lấy từ giấy tờ KHỚP tài khoản (Bên B Giấy ủy
  quyền / CCCD); tài khoản chính là người đại diện thì lấy nhân thân người đại diện. Giới tính không có nguồn thì suy
  từ số định danh của tài khoản (DOM hay chọn sẵn sai).
- Phần II chủ hồ sơ = DOANH NGHIỆP, luôn khác người nộp (cá nhân) → BỎ tích data[isOwnerDossierCheck], chọn
  data[chonDoiTuong1] = "Tổ chức/Doanh nghiệp" rồi điền tên + mã số thuế; Họ tên / CCCD... là của NGƯỜI ĐẠI DIỆN
  THEO PHÁP LUẬT; Tỉnh / Phường / Địa chỉ / SĐT theo TRỤ SỞ doanh nghiệp.
- data[ghiChu] = "Đăng ký Nội quy lao động ban hành theo Quyết định số ... ngày ...".
- Phần III datagrid "Hồ sơ kèm theo gồm": mỗi giấy tờ trong hồ sơ một dòng, Loại bản "Bản chính".
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _paper_names, _person_matches
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date as _date_slash,
    _email,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _text,
)
from app.pipelines.dang_ky_noi_quy_lao_dong.process.schema import CHON_TO_CHUC, MAX_HO_SO_ROWS, UI_COMP_BY_NAME

_VN_DATE_RE = re.compile(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE)
_MOBILE_RE = re.compile(r"^0[35789]\d{8}$")


def _date(value: Any) -> str | None:
    """dd/mm/yyyy; văn bản hành chính hay ghi "ngày 05 tháng 8 năm 2026"."""
    m = _VN_DATE_RE.search(_text(value) or "")
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    return _date_slash(value)


def _tax_code(value: Any) -> str | None:
    """Mã số doanh nghiệp 10 số, chi nhánh 13 số ("0100000001-001")."""
    digits = re.sub(r"\D+", "", _text(value) or "")
    if len(digits) == 10:
        return digits
    if len(digits) == 13:
        return f"{digits[:10]}-{digits[10:]}"
    return None


def _org_name(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _person_name(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^(ông|bà|ong|ba)\s+", "", text, flags=re.IGNORECASE)
    return text.upper()


def _ghi_chu(values: dict) -> str | None:
    so = _text(values.get("QuyetDinh_So"))
    ngay = _date(values.get("QuyetDinh_Ngay"))
    if not so and not ngay:
        return None
    text = "Đăng ký Nội quy lao động ban hành theo Quyết định"
    if so:
        text += f" số {so}"
    if ngay:
        text += f" ngày {ngay}"
    return text


def _person(values: dict, prefix: str) -> dict:
    return {
        "name": _text(values.get(f"{prefix}HoTen")),
        "identity": _identity(values.get(f"{prefix}SoDinhDanh")),
        "id_date": _date(values.get(f"{prefix}NgayCap")),
        "issuer": _issuer(values.get(f"{prefix}NoiCap")),
        "gender": _gender(values.get(f"{prefix}GioiTinh")),
        "birthday": _date(values.get(f"{prefix}NgaySinh")),
    }


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

    rep = _person(values, "DaiDien_")
    submitter = _person(values, "NguoiNop_")

    def matches_account(person: dict) -> bool:
        return has_ctx and bool(person["name"] or person["identity"]) and _person_matches(
            person["name"], person["identity"], ctx_name, ctx_identity)

    # --- Phần I: người nộp — chỉ từ giấy tờ khớp tài khoản (không có tài khoản: không điền) ---
    nop = submitter if matches_account(submitter) else rep if matches_account(rep) else None
    if nop:
        add("data[gender]", nop["gender"])
        add("data[identityDate]", nop["id_date"])
        add("data[idIssuePlace]", nop["issuer"])
        if nop is submitter:
            nop_area = _area(values.get("NguoiNop_DiaChi"))
            if nop_area:
                add("data[province]", province_label(nop_area.get("tinh")))
                add("data[district]", _text(nop_area.get("xa")))
                add("data[address]", _text(nop_area.get("diaChi")))
    add("data[gender]", _gender_from_identity(ctx_identity))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")) if nop is submitter else None)

    # --- Phần II: chủ hồ sơ = doanh nghiệp ---
    org_name = _org_name(values.get("DoanhNghiep_Ten"))
    org_tax = _tax_code(values.get("DoanhNghiep_MaSo"))
    org_area = _area(values.get("DoanhNghiep_DiaChi"))
    org_phone = _phone(values.get("DoanhNghiep_DienThoai"))
    # Bỏ tích TRƯỚC (FE sắp lên đầu) để cổng mở khoá Phần II, rồi đổi loại chủ hồ sơ cho ô tên tổ chức hiện ra.
    add("data[isOwnerDossierCheck]", False)
    add("data[chonDoiTuong1]", CHON_TO_CHUC)
    add("data[ownerOrganizationFullname]", org_name)
    add("data[ownerTaxCode]", org_tax)
    add("data[ownerFullname]", _person_name(rep["name"]))
    add("data[ownerBirthday]", rep["birthday"])
    add("data[ownerGender]", rep["gender"] or _gender_from_identity(rep["identity"]))
    add("data[ownerIdentityNumber]", rep["identity"])
    add("data[ownerIdentityDate]", rep["id_date"])
    add("data[ownerIdIssuePlace]", rep["issuer"])
    if org_area:
        add("data[ownerProvince]", province_label(org_area.get("tinh")))
        add("data[ownerDistrict]", _text(org_area.get("xa")))
        add("data[ownerAddress]", _text(org_area.get("diaChi")))
    add("data[ownerPhoneNumber]", org_phone)
    add("data[ownerEmail]", _email(values.get("DoanhNghiep_Email")))
    add("data[ownerFax]", _text(values.get("DoanhNghiep_Fax")))
    add("data[ownerNation]", "Việt Nam")
    add("data[ghiChu]", _ghi_chu(values))

    # --- Phần III: datagrid hồ sơ kèm theo ---
    papers = _paper_names(values.get("DanhMucHoSo"))
    for i, paper in enumerate(papers[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{i}][textField1]", paper)
        add(f"data[hoSoDinhKem][{i}][textField2]", "Bản chính")

    # --- Cảnh báo ---
    if not org_name:
        warnings.append("Không đọc được tên doanh nghiệp (công văn đề nghị / quyết định ban hành) — vui lòng nhập tay "
                        "Tên tổ chức/doanh nghiệp ở Phần II.")
    if not org_tax:
        warnings.append("Chưa có mã số doanh nghiệp (mã số thuế) — vui lòng nhập tay ở Phần II.")
    if not org_area:
        warnings.append("Không đọc được địa chỉ trụ sở doanh nghiệp — vui lòng chọn Tỉnh/TP, Phường/xã và nhập địa chỉ "
                        "chi tiết ở Phần II.")
    if not org_phone:
        warnings.append("Hồ sơ không ghi số điện thoại doanh nghiệp — ô SĐT Phần II (bắt buộc) vui lòng nhập tay.")
    elif not _MOBILE_RE.match(org_phone):
        warnings.append(f"SĐT doanh nghiệp {org_phone} là số cố định, cổng ghi 'Không sử dụng SĐT bàn' — đổi sang số "
                        "di động của doanh nghiệp nếu cổng không nhận.")
    if not rep["name"]:
        warnings.append("Không đọc được người đại diện theo pháp luật — vui lòng nhập tay Họ tên, CCCD ở Phần II.")
    else:
        missing = [label for label, key in (("ngày sinh", "birthday"), ("số CCCD", "identity"))
                   if not rep.get(key)]
        if missing:
            warnings.append("Hồ sơ không có CCCD của người đại diện theo pháp luật — thiếu " + ", ".join(missing)
                            + " ở Phần II, vui lòng nhập tay.")
    if not has_ctx:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — chưa điền nhân thân người nộp (Phần I), "
                        "vui lòng nhập tay.")
    elif not nop:
        warnings.append("Hồ sơ không có Giấy ủy quyền / CCCD khớp người nộp — vui lòng tự nhập ngày cấp, nơi cấp, địa "
                        "chỉ của người nộp.")
    elif nop is not submitter or not _area(values.get("NguoiNop_DiaChi")):
        warnings.append("Hồ sơ không ghi nơi cư trú của người nộp — vui lòng chọn Tỉnh/TP, Phường/Xã và nhập địa chỉ "
                        "ở Phần I.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Hồ sơ không ghi số điện thoại của người nộp — ô SĐT Phần I (bắt buộc) vui lòng nhập tay.")
    if not papers:
        warnings.append("Không lập được danh mục 'Hồ sơ kèm theo gồm' — vui lòng nhập tay từng giấy tờ.")
    elif len(papers) > MAX_HO_SO_ROWS:
        warnings.append(f"Hồ sơ có {len(papers)} giấy tờ, chỉ điền {MAX_HO_SO_ROWS} dòng đầu vào 'Hồ sơ kèm theo "
                        "gồm' — nhập thêm phần còn lại.")
    return out, warnings
