"""Map compact source facts → Form.io data[...] fields cho "Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng
đất, tài sản gắn liền với đất" (1.011442, cổng Đà Nẵng).

Theo mapping của thủ tục:
- data[fullname] / data[birthday] / data[identityNumber]: cổng đổ sẵn từ tài khoản → KHÔNG phát.
- CHỦ HỒ SƠ = người yêu cầu đăng ký thay đổi. Tổ chức → data[organization] = tên tổ chức, data[taxCode] = mã số
  doanh nghiệp, data[ownerFullname] = NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (dữ liệu mẫu của mapping; không đọc được người
  đại diện thì ghi tên tổ chức). Cá nhân → data[ownerFullname] = họ tên. data[chonDoiTuong] = loại chủ hồ sơ.
- data[isOwnerDossier]: tích khi người mang tên ở data[ownerFullname] khớp tài khoản; khác người → bỏ tích; không
  có mốc tài khoản → không đụng.
- data[gender] / data[identityDate] / data[identityAgency] theo NGƯỜI NỘP THỰC TẾ (khớp tài khoản):
  (1) thẻ CCCD khớp tài khoản → (2) người đại diện theo pháp luật khớp tài khoản → (3) bên được ủy quyền khớp tài
  khoản. Thiếu giới tính thì suy từ số định danh 12 số của tài khoản.
- data[phoneNumber] / data[email]: của chủ hồ sơ (Phiếu 02a mục 1 / GCN đăng ký doanh nghiệp); thiếu SĐT mà người
  nộp là bên được ủy quyền thì lấy SĐT trên giấy ủy quyền.
- Địa chỉ: trụ sở (tổ chức) / thường trú (cá nhân) của chủ hồ sơ, remap sang đơn vị hành chính hiện hành. Ô Tỉnh/TP
  của thủ tục này có đủ 34 tỉnh nên không cần đổi sang địa chỉ thửa đất như 1.012756.
- data[noidungyeucaugiaiquyet]: câu khung của cổng "ÔNG/BÀ: … (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT …" + "đối với: (1) Thửa
  đất số …, Giấy chứng nhận số phát hành …; (2) …" + "Nội dung thay đổi: …" (Phiếu 02a mục 3).
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _by_name,
    _date,
    _email,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _is_to_chuc,
    _issuer,
    _person_matches,
    _phone,
    _province_label,
    _text,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process.mapper import (
    _area_moi,
    _gender_from_title,
)
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process.schema import UI_COMP_BY_NAME

_PROC_TITLE = "Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất"

_THUA_PREFIX_RE = re.compile(r"^(?:thửa(?:\s+đất)?(?:\s+số)?)\s*:?\s*", re.IGNORECASE)
_TO_BAN_DO_PREFIX_RE = re.compile(r"^(?:tờ(?:\s+bản\s+đồ)?(?:\s+số)?)\s*:?\s*", re.IGNORECASE)
_DIEN_TICH_PREFIX_RE = re.compile(r"^(?:diện\s+tích)\s*:?\s*", re.IGNORECASE)
_SO_VAO_SO_PREFIX_RE = re.compile(r"^(?:số\s+vào\s+sổ(?:\s+cấp\s+GCN)?)\s*:?\s*", re.IGNORECASE)
_SERIAL_RE = re.compile(r"^([A-Z]{2})\s*(\d{6})$")


def _serial(value: Any) -> str | None:
    """Số phát hành GCN: "cb246904" → "CB 246904"; dạng khác giữ nguyên chữ."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^(?:số\s+phát\s+hành|số\s+seri|seri)\s*:?\s*", "", text, flags=re.IGNORECASE)
    m = _SERIAL_RE.match(text.upper().replace(".", "").strip())
    return f"{m.group(1)} {m.group(2)}" if m else text


def _area_size(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = _DIEN_TICH_PREFIX_RE.sub("", text)
    folded = _fold(text)
    if not re.search(r"m\s*2|m²|\bha\b|met vuong", folded):
        text = f"{text} m²"
    return text


def _tai_san_lines(value: Any) -> list[str]:
    """Mỗi Giấy chứng nhận → "Thửa đất số …, tờ bản đồ số …, địa chỉ: …, diện tích …, Giấy chứng nhận số phát
    hành …, số vào sổ cấp GCN: …". Trùng số phát hành (trang bổ sung LLM tách riêng) chỉ giữ một dòng."""
    items = value if isinstance(value, list) else [value] if value not in (None, "", {}) else []
    lines: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            so_thua = _THUA_PREFIX_RE.sub("", _text(item.get("soThua") or item.get("thuaDatSo")) or "")
            to_ban_do = _TO_BAN_DO_PREFIX_RE.sub("", _text(item.get("toBanDo") or item.get("toBanDoSo")) or "")
            dia_chi = _text(item.get("diaChi"))
            dien_tich = _area_size(item.get("dienTich"))
            so_phat_hanh = _serial(item.get("soPhatHanh") or item.get("soGCN"))
            so_vao_so = _SO_VAO_SO_PREFIX_RE.sub("", _text(item.get("soVaoSo")) or "")
            parts = []
            if so_thua:
                parts.append(f"Thửa đất số {so_thua}")
            if to_ban_do:
                parts.append(f"tờ bản đồ số {to_ban_do}")
            if dia_chi:
                parts.append(f"địa chỉ: {dia_chi}")
            if dien_tich:
                parts.append(f"diện tích {dien_tich}")
            if so_phat_hanh:
                parts.append(f"Giấy chứng nhận số phát hành {so_phat_hanh}")
            if so_vao_so:
                parts.append(f"số vào sổ cấp GCN: {so_vao_so}")
            line = ", ".join(parts)
            key = re.sub(r"[^a-z0-9]+", "", _fold(so_phat_hanh)) or _fold(line)
        else:
            line = _text(item) or ""
            key = _fold(line)
        line = line.strip(" .;")
        if line and key not in seen:
            seen.add(key)
            lines.append(line)
    return lines


def _noi_dung(owner_display: str, tai_san: list[str], thay_doi: str | None) -> str:
    request = f"ÔNG/BÀ: {owner_display} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}"
    if len(tai_san) == 1:
        request += f" đối với: {tai_san[0]}"
    elif tai_san:
        request += " đối với: " + "; ".join(f"({i}) {line}" for i, line in enumerate(tai_san, start=1))
    request += "."
    if thay_doi:
        thay_doi = thay_doi.strip()
        request += f" Nội dung thay đổi: {thay_doi}" + ("" if thay_doi.endswith((".", "!", "?")) else ".")
    return request


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
    tai_san = _tai_san_lines(values.get("TaiSan_DanhSach"))
    thay_doi = _text(values.get("Don_NoiDungThayDoi"))

    dd_name = _text(values.get("DaiDien_HoTen")) if owner_is_tc else None
    dd_id = _identity(values.get("DaiDien_SoDinhDanh")) if owner_is_tc else None
    # Ô "Họ và tên chủ hồ sơ" là ô của NGƯỜI: tổ chức → người đại diện theo pháp luật (mẫu của mapping).
    owner_display = (dd_name or owner_name) if owner_is_tc else owner_name

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    def matches_account(name: str | None, identity: str | None) -> bool:
        return has_ctx and bool(name or identity) and _person_matches(name, identity, ctx_name, ctx_identity)

    nop_ok = matches_account(_text(values.get("NguoiNop_HoTen")), _identity(values.get("NguoiNop_SoDinhDanh")))
    dd_ok = owner_is_tc and matches_account(dd_name, dd_id)
    uq_name = _text(values.get("UyQuyen_HoTen"))
    uq_ok = matches_account(uq_name, _identity(values.get("UyQuyen_SoDinhDanh")))

    # Chủ hồ sơ (người ở ô ownerFullname) cũng là người nộp?
    self_submit: bool | None = None
    if has_ctx and owner_name:
        if owner_is_tc:
            self_submit = dd_ok
        elif ctx_identity and owner_id and len(owner_id) >= 9:
            self_submit = owner_id == ctx_identity
        else:
            self_submit = matches_account(owner_name, None)

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
        add("data[gender]", _gender_from_title(values.get("UyQuyen_GioiTinh")))
        add("data[identityDate]", _date(values.get("UyQuyen_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("UyQuyen_NoiCap")))
    if (nop_ok or dd_ok or uq_ok) and "data[gender]" not in seen:
        guessed = _gender_from_identity(ctx_identity)
        add("data[gender]", guessed)
        gender_guessed = bool(guessed)

    # --- Liên hệ ---
    uq_phone = _phone(values.get("UyQuyen_DienThoai")) if uq_ok else None
    add("data[phoneNumber]", owner_phone or uq_phone)
    add("data[email]", _email(values.get("ChuHoSo_Email")))

    # --- Địa chỉ chủ hồ sơ ---
    if owner_area:
        add("data[province]", _province_label(owner_area.get("tinh")))
        add("data[district]", _text(owner_area.get("xa")))
        add("data[address]", _text(owner_area.get("diaChi")))

    if owner_display:
        add("data[noidungyeucaugiaiquyet]", _noi_dung(owner_display, tai_san, thay_doi))

    # --- Cảnh báo ---
    if not owner_name:
        warnings.append("Không đọc được tên chủ hồ sơ (người yêu cầu đăng ký ở Phiếu 02a / GCN đăng ký doanh "
                        "nghiệp) — vui lòng nhập tay.")
    if owner_is_tc and not owner_id:
        warnings.append("Chưa có mã số doanh nghiệp của chủ hồ sơ (GCN đăng ký doanh nghiệp) — vui lòng nhập tay ô "
                        "Mã định danh tổ chức, doanh nghiệp.")
    if owner_is_tc and not dd_name:
        warnings.append("Không đọc được người đại diện theo pháp luật của tổ chức — ô Họ và tên chủ hồ sơ đang ghi "
                        "tên tổ chức, kiểm tra lại.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Không tìm thấy số điện thoại (Phiếu 02a / GCN đăng ký doanh nghiệp / giấy ủy quyền) — bắt "
                        "buộc, vui lòng nhập tay.")
    if owner_name and not (owner_area and owner_area.get("xa")):
        warnings.append("Không đọc được đủ địa chỉ trụ sở/thường trú của chủ hồ sơ — vui lòng chọn Tỉnh/TP, "
                        "Phường/Xã và nhập địa chỉ chi tiết.")
    if owner_name and not tai_san:
        warnings.append("Không đọc được tài sản bảo đảm (thửa đất, số phát hành Giấy chứng nhận) — Nội dung yêu cầu "
                        "giải quyết chưa ghi tài sản, kiểm tra lại.")
    if owner_name and not thay_doi:
        warnings.append("Chưa có nội dung thay đổi từ Phiếu yêu cầu Mẫu số 02a (phiếu bắt buộc) — bổ sung phiếu và "
                        "kiểm tra Nội dung yêu cầu giải quyết.")
    if not has_ctx:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền giới tính, ngày cấp, nơi cấp của người nộp."
        )
    elif not (nop_ok or dd_ok or uq_ok):
        warnings.append(
            "Tài khoản người nộp không khớp CCCD, người đại diện theo pháp luật hay bên được ủy quyền trong hồ sơ — "
            "vui lòng tự nhập giới tính, ngày cấp, nơi cấp."
        )
    if gender_guessed:
        warnings.append("Giới tính người nộp suy từ số định danh của tài khoản (hồ sơ không ghi) — kiểm tra lại.")
    if owner_is_tc and has_ctx and not dd_ok and not uq_ok:
        who = f" ({dd_name})" if dd_name else ""
        warnings.append(
            f"Người nộp (tài khoản) không phải người đại diện theo pháp luật của tổ chức{who} — cần văn bản ủy quyền "
            "(đính chung dòng 'thông qua người đại diện')."
        )
    elif uq_name and has_ctx and not uq_ok and not dd_ok:
        warnings.append(
            f"Bên được ủy quyền trên giấy ủy quyền ({uq_name}) khác tài khoản đang nộp — kiểm tra lại tư cách người "
            "nộp."
        )
    return out, warnings
