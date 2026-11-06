"""Map compact facts sang Form.io của thủ tục Hòa giải tranh chấp đất đai (1.012812).

- ``data[chonDoiTuong]``: "Cá nhân" (người viết đơn là một người), "Tổ chức/Doanh nghiệp" hoặc "Cơ quan nhà nước"
  khi Đơn do tổ chức/cơ quan đứng tên. Form.io ẩn/hiện các ô còn lại theo lựa chọn này nên chọn trước.
- Phần I người nộp: họ tên, ngày sinh, CC/CCCD cổng đổ sẵn theo TÀI KHOẢN (CCCD khoá). Giới tính, Tỉnh, Phường/Xã,
  Địa chỉ chi tiết là ô bắt buộc mà cổng để trống.
  * TỰ NỘP (người viết đơn khớp họ tên tài khoản, khớp cả số căn cước nếu hai bên cùng có số 12 chữ số): điền Phần I
    theo giấy tờ + tích "Người nộp hồ sơ là chủ hồ sơ" để cổng tự chép sang Phần II.
  * NỘP THAY: giữ Phần I theo tài khoản, chỉ bổ sung giới tính/ngày cấp/nơi cấp/địa chỉ từ thẻ CCCD khớp tài khoản;
    Phần II điền người viết đơn, ô giấy tờ không có thì xoá trắng (không để lại số của người khác).
  * THEO TỜ KHAI (cài đặt "Lấy người nộp theo tờ khai" → ``options.submitterMode="owner_as_submitter"``): bỏ so khớp
    tài khoản, Phần I = người viết đơn kể cả họ tên/ngày sinh/CC/CCCD (ô khoá, phát kèm ``enableInput``; Đơn không
    có thì xoá + tô đỏ) + tích chủ hồ sơ. Đơn của cơ quan nhà nước: Phần I = người ký đơn, Phần II = cơ quan.
- ``data[ghiChu]``: nguyên văn thân Đơn (file mapping).
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.cccd import id_gender
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.hoa_giai_tranh_chap_dat_dai.process.schema import UI_COMP_BY_NAME
from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.process.mapper import _cap_prefix, _gender, _phone
from app.pipelines.xoa_dang_ky_tau_ca.process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _identity,
    _issuer,
    _province_label,
    _text,
)

_INDIVIDUAL = "Cá nhân"
_ORGANIZATION = "Tổ chức/Doanh nghiệp"
_STATE_AGENCY = "Cơ quan nhà nước"
_CARD_PARTS = ("HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "NgayCap", "NoiCap", "ThuongTru")
_FULL_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")


def _full_date(value: Any) -> str | None:
    """Chỉ nhận đủ ngày-tháng-năm: "Sinh năm 1980" của giấy tờ cũ không điền được ô ngày."""
    date = _date(value)
    return date if date and _FULL_DATE.fullmatch(date) else None


def _email(value: Any) -> str | None:
    text = _text(value)
    return text if text and "@" in text else None


def _same_identity(left: str | None, right: str | None) -> bool:
    """Hai số chỉ so được khi cùng loại: căn cước 12 số trên Đơn với CMND 9 số cũ là cùng người, không phải lệch."""
    if not left or not right or len(left) != len(right):
        return True
    return left == right


def _cards(values: dict) -> list[dict]:
    cards = []
    for prefix in ("Cccd1", "Cccd2"):
        card = {part: values.get(f"{prefix}_{part}") for part in _CARD_PARTS}
        card["HoTen"] = _text(card["HoTen"])
        card["SoDinhDanh"] = _identity(card["SoDinhDanh"])
        if card["HoTen"] or card["SoDinhDanh"]:
            cards.append(card)
    return cards


def _match_card(cards: list[dict], name: str | None, identity: str | None) -> dict | None:
    if not name:
        return None
    for card in cards:
        if card["HoTen"] and _fold(card["HoTen"]) == _fold(name) and _same_identity(card["SoDinhDanh"], identity):
            return card
    return None


def _card_issue(card: dict, identity: str | None) -> tuple[str | None, str | None]:
    """Ngày cấp/nơi cấp của thẻ chỉ dùng cho ĐÚNG số đang điền (thẻ CMND cũ không mang ngày cấp của căn cước mới)."""
    if identity and card.get("SoDinhDanh") and card["SoDinhDanh"] != identity:
        return None, None
    return _full_date(card.get("NgayCap")), _issuer(card.get("NoiCap"))


def _default_issuer(identity: str | None, issue_date: str | None) -> str | None:
    # Đơn ghi "Căn cước … cấp ngày …" mà không ghi nơi cấp: thẻ căn cước 12 số suy được cơ quan cấp theo ngày cấp.
    return default_issuer(issue_date) if identity and len(identity) == 12 and issue_date else None


def _requester(values: dict, cards: list[dict]) -> dict:
    name = _text(values.get("NguoiYeuCau_HoTen"))
    identity = _identity(values.get("NguoiYeuCau_SoDinhDanh"))
    card = _match_card(cards, name, identity) or {}
    card_identity = card.get("SoDinhDanh")
    if card_identity and (not identity or (len(identity) == 9 and len(card_identity) == 12)):
        identity = card_identity
    card_date, card_issuer = _card_issue(card, identity)
    issue_date = _full_date(values.get("NguoiYeuCau_NgayCap")) or card_date
    issuer = (_issuer(values.get("NguoiYeuCau_NoiCap")) or card_issuer
              or _default_issuer(identity, issue_date))
    return {
        "name": name,
        "identity": identity,
        "birthday": _full_date(values.get("NguoiYeuCau_NgaySinh")) or _full_date(card.get("NgaySinh")),
        "gender": (_gender(values.get("NguoiYeuCau_GioiTinh")) or _gender(card.get("GioiTinh"))
                   or _gender(None, values.get("NguoiYeuCau_DanhXung")) or id_gender(identity) or None),
        "issue_date": issue_date,
        "issuer": issuer,
        "residence": _area(values.get("NguoiYeuCau_DiaChi")) or _area(card.get("ThuongTru")),
        "phone": _phone(values.get("NguoiYeuCau_DienThoai")),
        "email": _email(values.get("NguoiYeuCau_Email")),
    }


def _subject(values: dict) -> str:
    kind = _fold(values.get("NguoiYeuCau_LoaiChuThe"))
    if not _text(values.get("NguoiYeuCau_TenToChuc")):
        return _INDIVIDUAL
    if "co quan" in kind or "nha nuoc" in kind:
        return _STATE_AGENCY
    if "to chuc" in kind or "doanh nghiep" in kind or "hop tac xa" in kind:
        return _ORGANIZATION
    return _INDIVIDUAL


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def put(name: str, value: Any) -> None:
        """Ô chủ hồ sơ khi nộp thay: giấy tờ không có dữ liệu thì yêu cầu extension XOÁ TRẮNG thay vì giữ giá trị cũ."""
        if value not in (None, "", {}, []):
            add(name, value)
            return
        comp = UI_COMP_BY_NAME.get(name)
        if name in seen or comp not in ("dom-input", "dom-date"):
            return
        out.append({"name": name, "comp": comp, "value": "", "clear": True})
        seen.add(name)

    def add_area(province: str, ward: str, detail: str, area: dict | None) -> bool:
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán → bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return False
        add(province, _cap_prefix(_province_label(area.get("tinh"))))
        add(ward, _cap_prefix(area.get("xa")))
        add(detail, _text(area.get("diaChi")))
        return True

    cards = _cards(values)
    person = _requester(values, cards)
    subject = _subject(values)
    org_name = _text(values.get("NguoiYeuCau_TenToChuc"))
    org_tax = _identity(values.get("NguoiYeuCau_MaSoThue"))
    context = (options or {}).get("formContext") or {}
    ctx_name = _text(context.get("applicantFullname") or context.get("fullname"))
    ctx_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))

    if not person["name"] and not org_name:
        warnings.append("Thiếu họ tên người yêu cầu hòa giải (người viết đơn) — kiểm tra lại Đơn.")

    add("data[chonDoiTuong]", subject)

    if subject == _ORGANIZATION:
        # Tổ chức đứng đơn: Phần I và Phần II đều là tổ chức (DOM Tổ chức/DN không có ô họ tên người nộp).
        add("data[organization]", org_name)
        add("data[taxCode]", org_tax)
        add_area("data[province]", "data[district]", "data[address]", person["residence"])
        add("data[phoneNumber]", person["phone"])
        add("data[email]", person["email"])
        add("data[ownerOrganizationFullname]", org_name)
        add("data[ownerTaxCode]", org_tax)
        add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", person["residence"])
        add("data[ownerPhoneNumber]", person["phone"])
        add("data[ownerEmail]", person["email"])
        add("data[ownerNation]", "Việt Nam")
        if not org_tax:
            warnings.append("Đơn không ghi mã số thuế/mã số doanh nghiệp của tổ chức — ô bắt buộc, cán bộ nhập tay.")
    else:
        def requester_part_one(with_issue: bool) -> None:
            add("data[gender]", person["gender"])
            if with_issue:
                add("data[identityDate]", person["issue_date"])
                add("data[idIssuePlace]", person["issuer"])
            has_area = add_area("data[province]", "data[district]", "data[address]", person["residence"])
            add("data[phoneNumber]", person["phone"])
            add("data[email]", person["email"])
            if not person["gender"] or not has_area:
                warnings.append("Giới tính và địa chỉ người nộp là ô bắt buộc nhưng hồ sơ không đủ thông tin — cán "
                                "bộ nhập tay.")

        # Cài đặt "Lấy người nộp theo tờ khai" (options.submitterMode, cả Auto Fill lẫn trợ lý): Phần I = người viết
        # đơn, KHÔNG so khớp tài khoản đăng nhập.
        declaration_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
        if declaration_mode and not person["name"]:
            declaration_mode = False
            warnings.append("Bật cài đặt \"Lấy người nộp theo tờ khai\" nhưng chưa đọc được người viết đơn — phần "
                            "người nộp giữ theo tài khoản đăng nhập.")
        self_submit = (
            not declaration_mode and subject == _INDIVIDUAL and bool(person["name"] and ctx_name)
            and _fold(person["name"]) == _fold(ctx_name) and _same_identity(person["identity"], ctx_identity)
        )
        if declaration_mode:
            # Ba ô cổng khoá theo tài khoản VNeID: extension bỏ disabled rồi ghi. Đơn không có thì XOÁ + tô đỏ, không
            # để lại ngày sinh/CCCD của tài khoản (người khác) dưới tên người viết đơn.
            for name, value in (("data[fullname]", person["name"]), ("data[birthday]", person["birthday"]),
                                ("data[identityNumber]", person["identity"])):
                item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value or "", "enableInput": True}
                if not value:
                    item.update({"clear": True, "markEmpty": True})
                out.append(item)
                seen.add(name)
            requester_part_one(with_issue=True)
            missing = [label for label, value in (("ngày sinh", person["birthday"]), ("số CC/CCCD", person["identity"]))
                       if not value]
            if missing:
                warnings.append(f"Lấy người nộp theo tờ khai: Đơn không có {', '.join(missing)} của người viết đơn — "
                                "đã xoá ô theo tài khoản ở Phần I, cán bộ nhập tay.")
        elif self_submit:
            add("data[fullname]", ctx_name)
            add("data[birthday]", person["birthday"])
            # Ô CC/CCCD khoá theo tài khoản: ngày cấp/nơi cấp của giấy tờ chỉ điền khi đúng số đó (CMND 9 số cũ thì không).
            requester_part_one(
                with_issue=not (person["identity"] and ctx_identity) or person["identity"] == ctx_identity
            )

        if (declaration_mode or self_submit) and subject == _INDIVIDUAL:
            # Phần I đã là người viết đơn → tích để cổng tự chép sang Phần II.
            add("data[isOwnerDossierCheck]", True)
        else:
            if not declaration_mode:
                # Nộp thay: Phần I giữ tài khoản, chỉ bổ sung ô trống bắt buộc từ CCCD đúng người nộp.
                applicant = _match_card(cards, ctx_name, ctx_identity)
                if applicant:
                    add("data[gender]",
                        _gender(applicant.get("GioiTinh")) or id_gender(applicant["SoDinhDanh"]) or None)
                    card_date, card_issuer = _card_issue(applicant, ctx_identity)
                    add("data[identityDate]", card_date)
                    add("data[idIssuePlace]", card_issuer or _default_issuer(ctx_identity, card_date))
                    add_area("data[province]", "data[district]", "data[address]", _area(applicant.get("ThuongTru")))
                elif ctx_name:
                    warnings.append(
                        "Tài khoản nộp khác người viết đơn: Phần I giữ theo tài khoản, hồ sơ không có CCCD của người "
                        "nộp nên Giới tính và địa chỉ người nộp (ô bắt buộc) cán bộ nhập tay. Người nộp theo tờ khai "
                        "thì bật cài đặt \"Lấy người nộp theo tờ khai\"."
                    )
                else:
                    warnings.append("Không đọc được họ tên tài khoản nộp trên biểu mẫu; giữ nguyên Phần I, điền người "
                                    "yêu cầu hòa giải ở Phần II (chủ hồ sơ).")
            add("data[isOwnerDossierCheck]", False)
            if subject == _STATE_AGENCY:
                add("data[ownerOrganizationFullname]", org_name)
                add("data[ownerTaxCode]", org_tax)
                add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", person["residence"])
                add("data[ownerPhoneNumber]", person["phone"])
                add("data[ownerEmail]", person["email"])
                if not org_tax:
                    warnings.append("Đơn không ghi mã số thuế của cơ quan đứng đơn — ô bắt buộc, cán bộ nhập tay.")
            else:
                put("data[ownerFullname]", person["name"])
                put("data[ownerBirthday]", person["birthday"])
                add("data[ownerGender]", person["gender"])
                put("data[ownerIdentityNumber]", person["identity"])
                put("data[ownerIdentityDate]", person["issue_date"])
                put("data[ownerIdIssuePlace]", person["issuer"])
                if not add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]",
                                person["residence"]):
                    put("data[ownerAddress]", None)
                put("data[ownerPhoneNumber]", person["phone"])
                put("data[ownerEmail]", person["email"])
                add("data[ownerNation]", "Việt Nam" if person["name"] else None)
                missing = [label for label, value in (
                    ("ngày sinh", person["birthday"]), ("giới tính", person["gender"]),
                    ("số CC/CCCD", person["identity"]),
                ) if not value]
                if person["name"] and missing:
                    warnings.append(f"Hồ sơ không có {', '.join(missing)} của người yêu cầu hòa giải — đã để trống ở "
                                    "Phần II (chủ hồ sơ), cán bộ nhập tay.")

    content = _text(values.get("Don_NoiDung"))
    if content:
        add("data[ghiChu]", content)
    else:
        warnings.append("Không đọc được nội dung Đơn yêu cầu hòa giải — ô Ghi chú để trống.")

    return out, warnings
