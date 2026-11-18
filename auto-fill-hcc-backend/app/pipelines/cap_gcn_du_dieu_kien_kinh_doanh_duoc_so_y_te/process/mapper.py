"""Map compact source facts → Form.io data[...] fields cho "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)".

Phần I "Thông tin người nộp hồ sơ" = tài khoản đăng nhập. Họ tên + CC/CCCD + Đối tượng bị KHOÁ theo tài khoản. Các ô
còn lại quyết định theo formContext (tên + số định danh tài khoản) SO với chủ hồ sơ (người đại diện theo pháp luật):
  - TỰ NỘP (tài khoản = người đại diện): Phần I = nhân thân chủ hồ sơ (kể cả SĐT di động / email của cơ sở).
  - NỘP THAY: Phần I CHỈ lấy từ CCCD khớp tài khoản (NguoiNop_*); không có thẻ thì để cổng tự điền. SĐT trên Đơn là của
    cơ sở → không đổ sang người nộp thay.
  - Không đọc được tài khoản: không đụng Phần I.
⚑ Cài đặt "Lấy người nộp theo tờ khai" (`options.submitterMode="owner_as_submitter"`, Auto Fill + trợ lý): bỏ mốc tài
  khoản, người nộp = người đại diện đứng hồ sơ → Phần I luôn theo chủ hồ sơ. Tài khoản khác người đại diện thì Họ tên +
  CC/CCCD phát kèm enableInput (cổng khoá theo VNeID); giấy không có ngày sinh thì xoá ngày sinh của tài khoản.

Phần II "Thông tin chủ hồ sơ": cổng đổ sẵn tên + CCCD TÀI KHOẢN → LUÔN bỏ tích "Người nộp hồ sơ là chủ hồ sơ" và ghi đè
bằng người đại diện; SĐT chỉ nhận số DI ĐỘNG (ô ghi "Không sử dụng SĐT bàn"); data[ghiChu] = tóm tắt cơ sở đề nghị.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.schema import UI_COMP_BY_NAME
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.mapper import (
    _PERSON_KEYS,
    _area,
    _by_name,
    _date,
    _email,
    _gender,
    _has_person,
    _identity,
    _issuer,
    _matches,
    _person,
    _person_name,
    _province_label,
    _text,
)

OWNER_AS_SUBMITTER = "owner_as_submitter"

# Tiền tố xưng hô / chức danh trước tên người đại diện ("Ông Lê Văn A – Giám đốc").
_HONORIFIC = re.compile(r"^(?:ông|bà|anh|chị)\s+", re.IGNORECASE)
_ROLE_SUFFIX = re.compile(r"\s*[–—-]\s*(?:giám\s*đốc|tổng\s*giám\s*đốc|chủ\s*tịch|chủ\s*hộ|chủ\s*cơ\s*sở).*$",
                          re.IGNORECASE)


def _owner_name(value: Any) -> str | None:
    name = _person_name(value)
    if not name:
        return None
    name = _ROLE_SUFFIX.sub("", _HONORIFIC.sub("", name)).strip(" .,:-")
    return name or None


def _mobile(value: Any) -> str | None:
    """Số DI ĐỘNG 10 số (03/05/07/08/09). Ô SĐT cổng ghi "Không sử dụng SĐT bàn" → số bàn 02x bỏ. Chuỗi có cả số
    bàn lẫn di động ("024 3000 0000 – Di động: 0912 000 111") thì lấy số di động."""
    text = _text(value)
    if not text:
        return None
    for part in re.split(r"[;,/|:()–—]|\s-\s", text):
        digits = re.sub(r"\D+", "", part)
        if digits.startswith("84") and len(digits) == 11:
            digits = "0" + digits[2:]
        if len(digits) == 9 and digits[0] in "35789":
            digits = "0" + digits
        if re.fullmatch(r"0[35789]\d{8}", digits):
            return digits
    return None


def _fax(value: Any) -> str | None:
    text = _text(value)
    if not text or not re.search(r"\d", text):
        return None
    return " ".join(text.split())


def _note(values: dict) -> str | None:
    """Ô Ghi chú (tự do): tóm tắt cơ sở đề nghị cấp theo Đơn / GCN đăng ký doanh nghiệp."""
    name = _text(values.get("CoSo_Ten"))
    if not name:
        return None
    tax = re.sub(r"\D+", "", _text(values.get("CoSo_MaSoDoanhNghiep")) or "")
    kind = _text(values.get("CoSo_LoaiHinh"))
    place = _text(values.get("CoSo_DiaDiemKinhDoanh"))
    note = f"Đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược cho {name}"
    if tax:
        note += f" (mã số doanh nghiệp {tax})"
    if kind:
        note += f"; loại hình: {kind}"
    if place:
        note += f"; địa điểm kinh doanh: {place}"
    return note + "."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    theo_to_khai = str((options or {}).get("submitterMode") or "") == OWNER_AS_SUBMITTER

    def add(name: str, value, extra: dict | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value, **(extra or {})})
        seen.add(name)

    def clear(name: str) -> None:
        # Cổng đổ sẵn giá trị của tài khoản VNeID, không phải của người theo tờ khai → xoá trắng + tô đỏ.
        if name in seen or name not in UI_COMP_BY_NAME:
            return
        out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True, "markEmpty": True})
        seen.add(name)

    def add_area(province_name: str, district_name: str, address_name: str, area: dict | None) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _text(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    owner = _person(values, "ChuHoSo_")
    owner_phone = _mobile(values.get("ChuHoSo_DienThoai"))
    owner_email = _email(values.get("ChuHoSo_Email"))

    # --- Mốc tài khoản đăng nhập (extension gửi formContext). ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    # NGƯỜI NỘP: chỉ nhận CCCD khớp tài khoản. Chế độ theo tờ khai không xét CCCD người khác.
    nop = _person(values, "NguoiNop_")
    nop_other = _has_person(nop)
    if theo_to_khai or not (has_ctx and nop_other and _matches(nop, ctx_name, ctx_identity)):
        nop = {}

    self_submit = None
    if theo_to_khai:
        self_submit = True
    elif has_ctx and _has_person(owner):
        self_submit = _matches(owner, ctx_name, ctx_identity)
    elif has_ctx and nop and not _has_person(owner):
        # Không đọc được người đại diện nhưng có CCCD tài khoản → coi CCCD đó là chủ hồ sơ tự nộp.
        self_submit = True
    if self_submit and nop:
        # Tự nộp: CCCD tài khoản CŨNG là CCCD chủ hồ sơ → vá các ô chủ hồ sơ còn thiếu (ngày/nơi cấp...).
        owner = {key: owner.get(key) or nop.get(key) for key in _PERSON_KEYS}

    owner_name = _owner_name(owner.get("HoTen"))
    owner_identity = _identity(owner.get("SoDinhDanh"))
    owner_birthday = _date(owner.get("NgaySinh"))
    owner_area = _area(owner.get("ThuongTru"))

    # === Phần I — người nộp ===
    if self_submit:
        unlock: dict | None = None
        if theo_to_khai and (owner_name or owner_identity) and not (has_ctx and _matches(owner, ctx_name, ctx_identity)):
            # Người theo tờ khai khác tài khoản → mở khoá Họ tên + CC/CCCD và ghi đè.
            unlock = {"enableInput": True}
            add("data[fullname]", owner_name, unlock)
            add("data[identityNumber]", owner_identity, unlock)
            if has_ctx:
                warnings.append(
                    f"Đang bật \"Lấy người nộp theo tờ khai\": Thông tin người nộp ghi theo người đại diện "
                    f"({owner_name or owner_identity}), khác tài khoản đăng nhập ({ctx_name or ctx_identity}) — kiểm "
                    "tra lại trước khi nộp."
                )
        if owner_birthday or not unlock:
            add("data[birthday]", owner_birthday)
        else:
            clear("data[birthday]")
        add("data[gender]", _gender(owner.get("GioiTinh")))
        add("data[identityDate]", _date(owner.get("NgayCap")))
        add("data[idIssuePlace]", _issuer(owner.get("NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", owner_area)
        add("data[phoneNumber]", owner_phone)
        add("data[email]", owner_email)
    elif nop:
        add("data[birthday]", _date(nop.get("NgaySinh")))
        add("data[gender]", _gender(nop.get("GioiTinh")))
        add("data[identityDate]", _date(nop.get("NgayCap")))
        add("data[idIssuePlace]", _issuer(nop.get("NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", _area(nop.get("ThuongTru")))

    # === Phần II — chủ hồ sơ (luôn bỏ tích rồi ghi đè) ===
    add("data[isOwnerDossierCheck]", False)
    add("data[ownerFullname]", owner_name)
    add("data[ownerBirthday]", owner_birthday)
    add("data[ownerGender]", _gender(owner.get("GioiTinh")))
    add("data[ownerIdentityNumber]", owner_identity)
    add("data[ownerIdentityDate]", _date(owner.get("NgayCap")))
    add("data[ownerIdIssuePlace]", _issuer(owner.get("NoiCap")))
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", owner_area)
    add("data[ownerPhoneNumber]", owner_phone)
    add("data[ownerEmail]", owner_email)
    add("data[ownerFax]", _fax(values.get("ChuHoSo_Fax")))
    add("data[ownerNation]", "Việt Nam" if owner_name or owner_identity else None)
    add("data[ghiChu]", _note(values))

    # --- Cảnh báo ---
    if theo_to_khai:
        if nop_other and not _matches(_person(values, "NguoiNop_"), owner_name, owner_identity):
            warnings.append("Hồ sơ có CCCD của người khác người đại diện nhưng đang bật \"Lấy người nộp theo tờ "
                            "khai\" — Thông tin người nộp ghi theo người đại diện.")
        if not (owner_name or owner_identity):
            warnings.append("Bật \"Lấy người nộp theo tờ khai\" nhưng chưa đọc được người đại diện theo pháp luật — "
                            "Thông tin người nộp giữ nguyên theo tài khoản, vui lòng kiểm tra.")
    elif not has_ctx:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền mục Thông tin người nộp hồ sơ, vui lòng "
            "kiểm tra ngày sinh, giới tính, địa chỉ, số điện thoại người nộp."
        )
    elif self_submit is False:
        if not nop:
            warnings.append(
                "Người nộp (tài khoản đăng nhập) khác người đại diện của cơ sở nhưng hồ sơ không có CCCD của người nộp "
                "— mục Thông tin người nộp giữ nguyên thông tin cổng tự điền, vui lòng bổ sung giới tính, địa chỉ nếu "
                "còn trống."
            )
        warnings.append("Nộp thay: số điện thoại người nộp (bắt buộc) không có trong giấy tờ — vui lòng nhập tay.")
    if not owner_name:
        warnings.append(
            "Không đọc được họ tên người đại diện theo pháp luật từ CCCD / GCN đăng ký doanh nghiệp / Đơn đề nghị — "
            "mục Thông tin chủ hồ sơ còn trống."
        )
    if owner_name and not owner_identity:
        warnings.append(f"Chưa có số CCCD của chủ hồ sơ ({owner_name}) — vui lòng nhập tay ô CC/CCCD/CMND.")
    if owner_name and not owner_area:
        warnings.append(
            "Không đọc được nơi thường trú của người đại diện — vui lòng chọn Tỉnh/Phường xã và nhập địa chỉ chi tiết."
        )
    if owner_name and not owner_phone:
        warnings.append("Không tìm thấy số điện thoại DI ĐỘNG của cơ sở / người đại diện (bắt buộc, cổng không nhận số "
                        "bàn) — vui lòng nhập tay.")

    return out, warnings
