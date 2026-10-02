"""Map compact source facts → Form.io data[...] fields cho "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước
giao đất để quản lý" (1.012756, cổng Đà Nẵng).

Theo mapping của thủ tục:
- data[fullname] / data[birthday] / data[identityNumber]: cổng đổ sẵn từ tài khoản → KHÔNG phát.
- CHỦ HỒ SƠ = tổ chức đứng tên Đơn Mẫu 15 (tên theo GCN đăng ký doanh nghiệp) → data[organization] +
  data[taxCode] (mã số doanh nghiệp), data[chonDoiTuong] = loại chủ hồ sơ. data[ownerFullname] là ô của NGƯỜI:
  tổ chức → NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT trên GCN đăng ký doanh nghiệp (tài liệu BA; không đọc được người đại
  diện thì ghi tên tổ chức). Cá nhân → họ tên.
- data[isOwnerDossier]: tích khi người ở data[ownerFullname] khớp tài khoản; khác người → bỏ tích.
- data[gender] / data[identityDate] / data[identityAgency]: (1) thẻ CCCD khớp tài khoản → (2) người đại diện theo
  pháp luật khớp tài khoản → (3) bên được ủy quyền khớp tài khoản → (4) chủ hồ sơ tổ chức mà tài khoản không khớp
  ai: theo NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT trên GCN đăng ký doanh nghiệp (tài liệu BA). Khớp tài khoản mà thiếu giới
  tính thì suy từ số định danh 12 số của tài khoản.
- data[phoneNumber]: người nộp là bên được ủy quyền → SĐT trên giấy UQ; không thì SĐT Đơn Mẫu 15 / tờ khai.
- Địa chỉ: trụ sở ở Đà Nẵng → Tỉnh/TP + Phường/Xã + địa chỉ chi tiết theo trụ sở (đơn vị MỚI); trụ sở ngoài Đà
  Nẵng (cổng không chọn được tỉnh khác) → cả ba ô lấy theo ĐỊA CHỈ THỬA ĐẤT; không có thì ghi đủ địa chỉ trụ sở
  vào data[address].
- data[noidungyeucaugiaiquyet]: câu khung của cổng "ÔNG/BÀ: … (người ở data[ownerFullname]) ĐỀ NGHỊ GIẢI QUYẾT …" + các đề nghị
  được đánh dấu ở Đơn mục 4 (vd "Đề nghị cấp Giấy chứng nhận").
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _email,
    _fold,
    _full_address,
    _gender,
    _gender_from_identity,
    _identity,
    _in_da_nang,
    _is_to_chuc,
    _issuer,
    _parse_area_text,
    _person_matches,
    _phone,
    _province_label,
    _same_name,
    _text,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process.schema import UI_COMP_BY_NAME

_PROC_TITLE = "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản lý"

# Ký hiệu ô đánh dấu + nhãn mục ở đầu dòng: "☑ b) ", "[x] ", "x b. ". Chữ x trơn phải có khoảng trắng theo sau để
# không ăn mất chữ đầu của "Xác nhận …".
_CHECK_MARK_RE = re.compile(r"^\s*(?:[☑☒✓✔]\s*|\[[xX ]?\]\s*|[xX]\s+)?(?:[a-dđ]\s*[).]\s*)?(?:[☑☒✓✔]\s*)?")
_TINH_PREFIX_RE = re.compile(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", re.IGNORECASE)


def _area_moi(value: Any) -> dict | None:
    """Địa chỉ → đơn vị hành chính hiện hành. remap_area chỉ tra được bảng sáp nhập khi tên tỉnh KHÔNG có tiền tố
    ("Tỉnh Quảng Nam" + "Xã Điện Hòa" trượt, "Quảng Nam" thì khớp) → bỏ tiền tố tỉnh trước; _province_label gắn
    lại khi điền."""
    if isinstance(value, str):
        value = _parse_area_text(value)
    if isinstance(value, dict) and value.get("tinh"):
        value = {**value, "tinh": _TINH_PREFIX_RE.sub("", " ".join(str(value["tinh"]).split()))}
    return _area(value)


def _gender_from_title(value: Any) -> str | None:
    """GCN đăng ký doanh nghiệp ghi "Nam"/"Nữ"; quyết định/hợp đồng chỉ có danh xưng "Ông"/"Bà"."""
    folded = _fold(value)
    if folded in {"ong", "mr"}:
        return "Nam"
    if folded in {"ba", "mrs", "ms"}:
        return "Nữ"
    return _gender(value)


def _de_nghi(value: Any) -> str | None:
    """Các đề nghị được đánh dấu ở Đơn mục 4 → "Đề nghị cấp Giấy chứng nhận. Đề nghị …" (bỏ ký hiệu ô, a) b))."""
    items = value if isinstance(value, list) else [value] if value not in (None, "") else []
    lines: list[str] = []
    for item in items:
        for line in re.split(r"\s*[\n;]\s*", _text(item) or ""):
            line = _CHECK_MARK_RE.sub("", line).strip(" .:")
            line = re.sub(r"\.{3,}|…+|\(\s*nếu\s+có\s*\)", "", line, flags=re.IGNORECASE).strip(" .:")
            # "d) Đề nghị khác (nếu có): ……" để trống → không phải đề nghị.
            if _fold(line) == "de nghi khac":
                continue
            if line and _fold(line) not in {_fold(x) for x in lines}:
                lines.append(line[:1].upper() + line[1:])
    return ". ".join(lines) or None


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

    # --- CHỦ HỒ SƠ ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_area = _area_moi(values.get("ChuHoSo_DiaChi"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))
    de_nghi = _de_nghi(values.get("Don_DeNghi"))

    dd_name = _text(values.get("DaiDien_HoTen")) if owner_is_tc else None
    dd_id = _identity(values.get("DaiDien_SoDinhDanh")) if owner_is_tc else None
    # Ô "Họ và tên chủ hồ sơ" là ô của NGƯỜI: tổ chức → người đại diện theo pháp luật (tài liệu BA).
    owner_display = (dd_name or owner_name) if owner_is_tc else owner_name

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    def matches_account(name: str | None, identity: str | None) -> bool:
        return has_ctx and bool(name or identity) and _person_matches(name, identity, ctx_name, ctx_identity)

    # NGƯỜI NỘP: thẻ CCCD khớp tài khoản.
    nop_ok = matches_account(_text(values.get("NguoiNop_HoTen")), _identity(values.get("NguoiNop_SoDinhDanh")))
    # NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT khớp tài khoản → người nộp chính là người đại diện.
    dd_ok = owner_is_tc and matches_account(dd_name, dd_id)
    # BÊN ĐƯỢC ỦY QUYỀN khớp tài khoản → người nộp chính là người được ủy quyền.
    uq_name = _text(values.get("UyQuyen_HoTen"))
    uq_ok = matches_account(uq_name, _identity(values.get("UyQuyen_SoDinhDanh")))

    # Người ở ô ownerFullname (tổ chức: người đại diện; cá nhân: chủ hồ sơ) cũng là người nộp?
    self_submit: bool | None = None
    if owner_is_tc:
        self_submit = dd_ok
    elif owner_name and has_ctx:
        if ctx_identity and owner_id and len(owner_id) >= 9:
            self_submit = owner_id == ctx_identity
        else:
            self_submit = bool(ctx_name) and _same_name(owner_name, ctx_name)

    # --- Chủ hồ sơ ---
    if owner_name:
        add("data[chonDoiTuong]", "Tổ chức" if owner_is_tc else "Cá nhân")
    if self_submit is not None:
        add("data[isOwnerDossier]", self_submit)
    add("data[ownerFullname]", owner_display)
    if owner_is_tc:
        add("data[organization]", owner_name)
        add("data[taxCode]", owner_id)

    # --- Nhân thân người nộp (ô không khoá): CCCD → người đại diện theo pháp luật → giấy ủy quyền ---
    gender_guessed = False
    if nop_ok:
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
    if dd_ok:
        add("data[gender]", _gender_from_title(values.get("DaiDien_GioiTinh")))
        add("data[identityDate]", _date(values.get("DaiDien_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("DaiDien_NoiCap")))
    if uq_ok:
        add("data[identityDate]", _date(values.get("UyQuyen_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("UyQuyen_NoiCap")))
    if (nop_ok or dd_ok or uq_ok) and "data[gender]" not in seen:
        guessed = _gender_from_identity(ctx_identity)
        add("data[gender]", guessed)
        gender_guessed = bool(guessed)
    # Tài khoản không khớp ai trong hồ sơ → theo người đại diện trên GCN đăng ký doanh nghiệp (tài liệu BA).
    dd_fallback = owner_is_tc and bool(dd_name) and not (nop_ok or dd_ok or uq_ok)
    if dd_fallback:
        add("data[gender]", _gender_from_title(values.get("DaiDien_GioiTinh")))
        add("data[identityDate]", _date(values.get("DaiDien_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("DaiDien_NoiCap")))

    # --- Liên hệ: SĐT người được ủy quyền khi họ là người nộp, không thì SĐT Đơn Mẫu 15 / tờ khai ---
    uq_phone = _phone(values.get("UyQuyen_DienThoai")) if uq_ok and not dd_ok else None
    add("data[phoneNumber]", uq_phone or owner_phone)
    add("data[email]", _email(values.get("ChuHoSo_Email")))

    # Ô Tỉnh/TP của cổng Đà Nẵng không chọn được tỉnh khác → trụ sở ngoài Đà Nẵng thì Phường/Xã + địa chỉ chi tiết
    # lấy theo THỬA ĐẤT; không đọc được thửa đất ở Đà Nẵng thì ghi đủ địa chỉ trụ sở vào ô chi tiết.
    owner_outside_dn = bool(owner_area) and not _in_da_nang(owner_area)
    land_area = _area_moi(values.get("ThuaDat_DiaChi"))
    if land_area and not (_in_da_nang(land_area) and land_area.get("xa")):
        land_area = None
    area_source = "owner"
    if owner_area and not owner_outside_dn:
        area = owner_area
    elif land_area:
        area, area_source = land_area, "land"
    else:
        area = None
    if area:
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    elif owner_outside_dn:
        add("data[address]", _full_address(owner_area))

    if owner_display:
        request = f"ÔNG/BÀ: {owner_display} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}."
        if de_nghi:
            request += f" {de_nghi}."
        add("data[noidungyeucaugiaiquyet]", request)

    # --- Cảnh báo ---
    if not owner_name:
        warnings.append("Không đọc được tên chủ hồ sơ (người đứng tên Đơn Mẫu 15 / GCN đăng ký doanh nghiệp) — vui "
                        "lòng nhập tay.")
    if owner_is_tc and not owner_id:
        warnings.append("Chưa có mã số doanh nghiệp của chủ hồ sơ (GCN đăng ký doanh nghiệp / Đơn mục 1b) — vui "
                        "lòng nhập tay ô Mã định danh tổ chức, doanh nghiệp.")
    if owner_is_tc and not dd_name:
        warnings.append("Không đọc được người đại diện theo pháp luật trên GCN đăng ký doanh nghiệp — ô Họ và tên "
                        "chủ hồ sơ đang ghi tên tổ chức, chưa điền giới tính, ngày cấp, nơi cấp; kiểm tra lại.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Không tìm thấy số điện thoại (Đơn Mẫu 15 / tờ khai / giấy ủy quyền) — bắt buộc, vui lòng "
                        "nhập tay.")
    if owner_outside_dn and area_source == "land":
        warnings.append(f"Trụ sở chủ hồ sơ ngoài Đà Nẵng ({_full_address(owner_area)}) — cổng không chọn được "
                        "tỉnh khác nên Tỉnh/TP, Phường/Xã, địa chỉ chi tiết điền theo địa chỉ thửa đất.")
    elif owner_outside_dn:
        warnings.append("Trụ sở chủ hồ sơ ngoài Đà Nẵng và không đọc được địa chỉ thửa đất — đã ghi đủ địa chỉ trụ "
                        "sở vào ô Địa chỉ chi tiết; ô Phường/Xã (bắt buộc) vui lòng tự chọn.")
    if owner_name and not owner_area and not area:
        warnings.append("Không đọc được địa chỉ trụ sở chủ hồ sơ trên Đơn Mẫu 15 — vui lòng chọn Tỉnh/TP, "
                        "Phường/Xã và nhập địa chỉ chi tiết.")
    if owner_name and not de_nghi:
        warnings.append("Không đọc được ô đề nghị được đánh dấu ở Đơn mục 4 — Nội dung yêu cầu chỉ có câu khung, "
                        "kiểm tra lại.")
    # dd_fallback: đã điền theo người đại diện theo pháp luật → không báo thiếu; cảnh báo nộp thay ở dưới.
    if not has_ctx and not dd_fallback:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền giới tính, ngày cấp, nơi cấp của người nộp."
        )
    elif has_ctx and not (nop_ok or dd_ok or uq_ok or dd_fallback):
        warnings.append(
            "Tài khoản người nộp không khớp CCCD, người đại diện theo pháp luật hay bên được ủy quyền trong hồ sơ — "
            "vui lòng tự nhập giới tính, ngày cấp, nơi cấp."
        )
    if gender_guessed:
        warnings.append("Giới tính người nộp suy từ số định danh của tài khoản (hồ sơ không ghi) — kiểm tra lại.")
    if owner_is_tc and has_ctx and not dd_ok and not uq_ok:
        who = f" ({dd_name})" if dd_name else ""
        warnings.append(
            f"Người nộp (tài khoản) không phải người đại diện theo pháp luật của tổ chức{who} — nếu nộp thay cần "
            "giấy ủy quyền (đính chung dòng 1)."
            + (" Giới tính, ngày cấp, nơi cấp đang điền theo người đại diện trên GCN đăng ký doanh nghiệp."
               if dd_fallback else "")
        )
    elif uq_name and has_ctx and not uq_ok and not dd_ok:
        warnings.append(
            f"Bên được ủy quyền trên giấy ủy quyền ({uq_name}) khác tài khoản đang nộp — kiểm tra lại tư cách người "
            "nộp."
        )
    return out, warnings
