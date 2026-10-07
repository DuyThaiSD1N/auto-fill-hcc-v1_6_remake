"""Map compact facts sang Form.io của thủ tục hỗ trợ thiệt hại do dịch bệnh động vật (1.013997).

- ``data[chonDoiTuong]``: "Cá nhân" (hộ chăn nuôi); chỉ chọn "Tổ chức/Doanh nghiệp" khi Đơn ghi cả tên cơ sở
  sản xuất lẫn mã số thuế.
- Phần I (người nộp) cổng khoá theo tài khoản. Chủ hộ trên giấy tờ khớp họ tên tài khoản (và khớp số định danh
  nếu cả hai bên có) thì điền nốt Phần I + tích "Người nộp hồ sơ là chủ hồ sơ" để Form.io tự chép sang Phần II.
  Không khớp thì giữ Phần I, điền Phần II theo chủ hộ.
- ``data[ghiChu]``: tóm tắt dịch bệnh + từng Biên bản tiêu hủy (đối tượng, số con, kg) + tổng cộng, vì eform
  không có ô riêng cho dữ liệu tiêu hủy.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.ho_tro_co_so_san_xuat_thiet_hai_dich_benh_dong_vat.process.schema import UI_COMP_BY_NAME
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
_CCCD_PARTS = ("HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "NgayCap", "NoiCap", "ThuongTru")


def _gender(value: Any, title: Any = None) -> str | None:
    text = _fold(value)
    if text in ("nam", "male", "m"):
        return "Nam"
    if text in ("nu", "female", "f"):
        return "Nữ"
    salutation = _fold(title)
    if salutation == "ong":
        return "Nam"
    if salutation == "ba":
        return "Nữ"
    return None


def _cap_prefix(value: Any) -> str | None:
    """Biên bản viết thường "tỉnh Lai Châu"/"xã Bình Lư"; option cổng là "Tỉnh …"/"Xã …"."""
    text = _text(value)
    if not text:
        return None
    return re.sub(r"^(tỉnh|thành phố|xã|phường|thị trấn|đặc khu)\b",
                  lambda m: m.group(1)[0].upper() + m.group(1)[1:], text, flags=re.IGNORECASE)


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits if len(digits) >= 9 else None


def _owner_card(values: dict, owner_name: str | None, options: dict | None) -> dict | None:
    """Chọn CCCD của chủ hộ trong Cccd1/Cccd2: trùng tên chủ hộ, hoặc thẻ duy nhất không phải của người nộp."""
    cards = []
    for prefix in ("Cccd1", "Cccd2"):
        card = {part: values.get(f"{prefix}_{part}") for part in _CCCD_PARTS}
        if _text(card["HoTen"]) or _identity(card["SoDinhDanh"]):
            cards.append(card)
    if owner_name:
        named = [card for card in cards if _fold(_text(card["HoTen"])) == _fold(owner_name)]
        if len(named) == 1:
            return named[0]
    context = (options or {}).get("formContext") or {}
    context_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    if len(cards) == 1 and (not owner_name or _identity(cards[0]["SoDinhDanh"]) != context_identity):
        return cards[0]
    return None


def _number(value: Any) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", _text(value) or "")
    return float(match.group(0).replace(",", ".")) if match else None


def _fmt_number(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}".replace(".", ",")


def _count_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # Biên bản ghi số con dạng "01"; giữ nguyên số đã ghi, chỉ bỏ chữ "con"/"kg" thừa.
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    return match.group(0) if match else text


def _reports(value: Any) -> list[dict]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items = item.get("doiTuong") or []
        if isinstance(items, dict):
            items = [items]
        animals = []
        for animal in items if isinstance(items, list) else []:
            if isinstance(animal, dict) and _text(animal.get("ten")):
                animals.append({
                    "ten": _text(animal.get("ten")),
                    "soLuong": _count_text(animal.get("soLuong")),
                    "khoiLuong": _count_text(animal.get("khoiLuong")),
                })
        report = {
            "so": _text(item.get("so")),
            "ngay": _date(item.get("ngay")),
            "doiTuong": animals,
            "tongSoLuong": _count_text(item.get("tongSoLuong")),
            "tongKhoiLuong": _count_text(item.get("tongKhoiLuong")),
        }
        if report["so"] or animals or report["tongSoLuong"]:
            out.append(report)
    return out


def _animal_text(name: str | None, count: str | None, weight: str | None) -> str:
    parts = [part for part in (f"{count} con" if count else None, f"{weight} kg" if weight else None) if part]
    if name and parts:
        return f"{name} {', '.join(parts)}"
    return name or ", ".join(parts)


def _report_totals(report: dict) -> tuple[float | None, float | None]:
    count = _number(report.get("tongSoLuong"))
    weight = _number(report.get("tongKhoiLuong"))
    animals = report.get("doiTuong") or []
    if count is None and animals and all(_number(a.get("soLuong")) is not None for a in animals):
        count = sum(_number(a.get("soLuong")) for a in animals)
    if weight is None and animals and all(_number(a.get("khoiLuong")) is not None for a in animals):
        weight = sum(_number(a.get("khoiLuong")) for a in animals)
    return count, weight


def _ghi_chu(disease: str | None, reports: list[dict]) -> str | None:
    pieces: list[str] = []
    for report in reports:
        head = "Biên bản tiêu hủy"
        if report.get("so"):
            head += f" số {report['so']}"
        if report.get("ngay"):
            head += f" ngày {report['ngay']}"
        animals = "; ".join(
            _animal_text(a.get("ten"), a.get("soLuong"), a.get("khoiLuong")) for a in report.get("doiTuong") or []
        )
        if not animals:
            animals = _animal_text(None, report.get("tongSoLuong"), report.get("tongKhoiLuong"))
        pieces.append(f"{head}: {animals}" if animals else head)

    if len(reports) > 1:
        totals = [_report_totals(report) for report in reports]
        if all(count is not None for count, _ in totals) and all(weight is not None for _, weight in totals):
            count = sum(count for count, _ in totals)
            weight = sum(weight for _, weight in totals)
            pieces.append(f"Cộng {len(reports)} biên bản: {_fmt_number(count):0>2} con, {_fmt_number(weight)} kg")

    if disease:
        pieces.insert(0, disease)
    return " – ".join(pieces) or None


def _requester_matches(owner_name: str | None, owner_identity: str | None, options: dict | None) -> bool:
    context = (options or {}).get("formContext") or {}
    context_name = _text(context.get("applicantFullname") or context.get("fullname"))
    context_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    if not owner_name or not context_name or _fold(owner_name) != _fold(context_name):
        return False
    # Biên bản không ghi số CCCD: khớp họ tên là đủ; có số ở cả hai bên thì phải trùng.
    return not (owner_identity and context_identity and owner_identity != context_identity)


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
        """Ô CHỦ HỒ SƠ: cổng đổ sẵn ngày sinh/CCCD của TÀI KHOẢN vào Phần II → giấy tờ không có dữ liệu thì yêu
        cầu extension XÓA TRẮNG ô đó thay vì để lại giá trị của người khác. FE chỉ xoá được ô input/date."""
        if value not in (None, "", {}, []):
            add(name, value)
            return
        comp = UI_COMP_BY_NAME.get(name)
        if name in seen or comp not in ("dom-input", "dom-date"):
            return
        out.append({"name": name, "comp": comp, "value": "", "clear": True})
        seen.add(name)

    owner_name = _text(values.get("ChuHo_HoTen"))
    card = _owner_card(values, owner_name, options) or {}
    owner_name = owner_name or _text(card.get("HoTen"))
    owner_identity = _identity(values.get("ChuHo_SoDinhDanh")) or _identity(card.get("SoDinhDanh"))
    birthday = _date(card.get("NgaySinh")) or _date(values.get("ChuHo_NgaySinh"))
    gender = _gender(card.get("GioiTinh"), values.get("ChuHo_DanhXung"))
    issue_date = _date(values.get("ChuHo_NgayCap")) or _date(card.get("NgayCap"))
    issuer = _issuer(values.get("ChuHo_NoiCap")) or _issuer(card.get("NoiCap"))
    residence = _area(values.get("ChuHo_ThuongTru")) or _area(card.get("ThuongTru"))
    phone = _phone(values.get("ChuHo_DienThoai"))

    org_name = _text(values.get("CoSo_Ten"))
    org_tax = _identity(values.get("CoSo_MaSoThue"))
    is_org = bool(org_name and org_tax)

    if not owner_name:
        warnings.append("Thiếu họ tên chủ hộ chăn nuôi từ Đơn đề nghị/Biên bản tiêu hủy.")

    is_owner = not is_org and _requester_matches(owner_name, owner_identity, options)
    context = (options or {}).get("formContext") or {}
    if owner_name and not is_owner and not is_org and _text(context.get("applicantFullname") or context.get("fullname")):
        warnings.append("Tài khoản nộp khác chủ hộ chăn nuôi trên giấy tờ; giữ nguyên Phần I, điền chủ hồ sơ ở Phần II.")

    # Chọn đối tượng trước: Form.io ẩn/hiện các ô còn lại theo lựa chọn này.
    add("data[chonDoiTuong]", _ORGANIZATION if is_org else _INDIVIDUAL)

    if is_owner:
        add("data[fullname]", _text(context.get("applicantFullname") or context.get("fullname")))
        add("data[birthday]", birthday)
        add("data[gender]", gender)
        add("data[identityNumber]", owner_identity)
        add("data[identityDate]", issue_date)
        add("data[idIssuePlace]", issuer)
        if residence:
            add("data[province]", _cap_prefix(_province_label(residence.get("tinh"))))
            add("data[district]", _cap_prefix(residence.get("xa")))
            add("data[address]", _text(residence.get("diaChi")))
        add("data[phoneNumber]", phone)
        add("data[isOwnerDossierCheck]", True)
    else:
        if is_org:
            add("data[ownerOrganizationFullname]", org_name)
            add("data[ownerTaxCode]", org_tax)
        # Phần II cổng đổ sẵn theo TÀI KHOẢN (người nộp thay) → ô nào giấy tờ chủ hộ không có thì xoá trắng.
        put("data[ownerFullname]", owner_name)
        put("data[ownerBirthday]", birthday)
        add("data[ownerGender]", gender)
        put("data[ownerIdentityNumber]", owner_identity)
        put("data[ownerIdentityDate]", issue_date)
        put("data[ownerIdIssuePlace]", issuer)
        if residence:
            add("data[ownerProvince]", _cap_prefix(_province_label(residence.get("tinh"))))
            add("data[ownerDistrict]", _cap_prefix(residence.get("xa")))
        put("data[ownerAddress]", _text(residence.get("diaChi")) if residence else None)
        put("data[ownerPhoneNumber]", phone)
        put("data[ownerEmail]", None)
        add("data[ownerNation]", "Việt Nam" if owner_name or is_org else None)
        missing = [label for label, value in (("Ngày sinh", birthday), ("CC/CCCD/CMND", owner_identity)) if not value]
        if missing:
            warnings.append(f"Hồ sơ không có {', '.join(missing)} của chủ hộ — đã để trống ô ở Phần II "
                            "(chủ hồ sơ), vui lòng nhập tay.")

    reports = _reports(values.get("BienBan_DanhSach"))
    if not reports:
        warnings.append("Không đọc được Biên bản tiêu hủy động vật — kiểm tra lại hồ sơ.")
    add("data[ghiChu]", _ghi_chu(_text(values.get("DichBenh_Ten")), reports))

    return out, warnings
