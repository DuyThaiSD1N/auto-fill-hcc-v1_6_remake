"""Map fact Đơn Mẫu 18 + CCCD + Bằng TQGC sang field Form.io của thủ tục Trợ cấp thờ cúng liệt sĩ.

- Field dùng chung Phần 1 (người nộp) và Phần 4 (chi tiết mẫu khai) điền cùng formcontrolname nhưng
  khác occurrence (0 = Phần 1, 1 = Phần 4): fullname/birthday/gender/identityNumber/identityDate/
  phoneNumber/province/address.
- Phần 4: Quê quán = province/village/address (occ 1); Nơi thường trú = province1/village1/address1.
- Quê quán liệt sĩ = address2 (1 ô text tự do). Tên liệt sĩ = UqTcLs. Bảng thân nhân = DataGrid.
- Cư trú/quê quán ưu tiên TỜ KHAI; số định danh/ngày cấp ưu tiên CCCD.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.tro_cap_tho_cung_liet_si.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    # Đã có tiền tố hành chính rồi → trả nguyên
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    # Các thành phố trực thuộc Trung ương (bao gồm sau sáp nhập 2025)
    city_set = {
        "ha noi", "hai phong", "da nang", "can tho",
        "ho chi minh", "tp ho chi minh",
        # Huế trở thành thành phố trực thuộc TW từ 01/01/2025
        "hue",
    }
    bare = _fold(_strip_admin_prefix(text))
    is_city = bare in city_set or folded in city_set
    return f"{'Thành phố' if is_city else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = parts[-1]
        out["xa"] = parts[-3]
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = parts[-1]
        out["xa"] = parts[-2]
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = parts[-1]
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        if not any(out.values()):
            out = None
    else:
        out = None
    if out and (out.get("tinh") or out.get("xa")):
        out = remap_area(out)
    return out


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _year(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", text)
    return m.group(1) if m else text


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _matches_context(person: dict, context: dict) -> bool:
    """Có cả tên và CCCD trên UI thì bắt buộc cùng khớp."""
    context_name = _fold(context.get("applicant_name"))
    context_identity = _identity(context.get("applicant_identity"))
    person_name = _fold(person.get("name"))
    person_identity = _identity(person.get("identity"))

    if context_name and context_identity:
        return person_name == context_name and person_identity == context_identity
    if context_identity:
        return bool(person_identity and person_identity == context_identity)
    return bool(context_name and person_name == context_name)


def _role(values: dict, prefix: str) -> dict | None:
    name = _text(values.get(f"{prefix}_HoTen"))
    identity = _identity(values.get(f"{prefix}_SoDinhDanh"))
    if not name and not identity:
        return None
    return {
        "name": name,
        "birthday": values.get(f"{prefix}_NgaySinh"),
        "gender": values.get(f"{prefix}_GioiTinh"),
        "identity": identity,
        "issue_date": values.get(f"{prefix}_NgayCap"),
        "issue_place": values.get(f"{prefix}_NoiCap"),
        "residence": values.get(f"{prefix}_NoiCuTru"),
        "phone": values.get(f"{prefix}_DienThoai"),
        "nationality": values.get(f"{prefix}_QuocTich") or "Việt Nam",
        "origin": values.get(f"{prefix}_QueQuan"),
    }


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(k) for k in keys)))


def _joined_names(value: Any) -> str | None:
    """Form chỉ có một ô text; LLM lỡ trả list thì nối tên ổn định bằng 'và'."""
    if not isinstance(value, list):
        return _text(value)
    names: list[str] = []
    seen: set[str] = set()
    for item in value:
        name = _text(item)
        folded = _fold(name)
        if not name or not folded or folded in seen:
            continue
        names.append(name)
        seen.add(folded)
    return " và ".join(names) or None


def _dedupe_relatives(value: Any) -> list[dict]:
    """Gộp dòng OCR trùng tên khi năm sinh không mâu thuẫn, giữ thứ tự đầu tiên."""
    out: list[dict] = []
    for raw in _list(value):
        if not isinstance(raw, dict):
            continue
        item = {
            "hoTen": _item_text(raw, "hoTen", "hoVaTen"),
            "namSinh": _year(_item_text(raw, "namSinh", "ngaySinh")),
            "namMat": _year(_item_text(raw, "namMat", "ngayMat")),
            "noiThuongTru": _item_text(raw, "noiThuongTru", "diaChi"),
            "moiQuanHe": _item_text(raw, "moiQuanHe", "mqh", "quanHe"),
        }
        if not item["hoTen"]:
            continue
        folded_name = _fold(item["hoTen"])
        duplicate = next(
            (
                existing
                for existing in out
                if _fold(existing.get("hoTen")) == folded_name
                and (
                    not existing.get("namSinh")
                    or not item.get("namSinh")
                    or existing.get("namSinh") == item.get("namSinh")
                )
            ),
            None,
        )
        if duplicate is None:
            out.append(item)
            continue
        for key in ("namSinh", "namMat", "noiThuongTru", "moiQuanHe"):
            if not duplicate.get(key) and item.get(key):
                duplicate[key] = item[key]
    return out


def _add_area(add, province_name, district_name, address_name, value, *, occurrence=None) -> None:
    area = _area(value)
    if not area:
        return
    add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
    add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
    add(address_name, _text(area.get("diaChi")), occurrence=occurrence)


def _add_person_block(
    add,
    prefix: str,
    *,
    name,
    birthday,
    gender,
    identity,
    issue_date,
    issue_place,
    residence,
    phone,
    occurrence=None,
) -> None:
    owner = prefix == "owner"
    add(f"data[{prefix}Fullname]" if owner else "data[fullname]", _text(name), occurrence=occurrence)
    add(f"data[{prefix}Birthday]" if owner else "data[birthday]", _date(birthday), occurrence=occurrence)
    add(f"data[{prefix}Gender]" if owner else "data[gender]", _text(gender), occurrence=occurrence)
    add(f"data[{prefix}IdentityNumber]" if owner else "data[identityNumber]", _identity(identity), occurrence=occurrence)
    add(f"data[{prefix}IdentityDate]" if owner else "data[identityDate]", _date(issue_date), occurrence=occurrence)
    add(
        f"data[{prefix}IdIssuePlace]" if owner else "data[idIssuePlace]",
        _issuer(issue_place) or _text(issue_place),
        occurrence=occurrence,
    )
    if owner:
        _add_area(add, "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
        add("data[ownerPhoneNumber]", _phone(phone))
        add("data[ownerNation]", "Việt Nam")
    else:
        _add_area(add, "data[province]", "data[district]", "data[address]", residence, occurrence=occurrence)
        add("data[phoneNumber]", _phone(phone), occurrence=occurrence)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    """Map hai vai trò đầu form và luôn dùng chủ hồ sơ cho chi tiết Mẫu 18."""
    values = _by_name(fields)
    owner = _role(values, "ChuHoSo")
    requester = _role(values, "NguoiNop")
    context = _form_context(options)

    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence=None) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(seen_key)

    # Toggle "Người nộp = chủ hồ sơ" (owner_as_submitter): LUÔN lấy chủ hồ sơ cho occ0, tick, bỏ mỏ neo UI.
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    owner_matches = bool(owner and _matches_context(owner, context))
    requester_matches = bool(requester and _matches_context(requester, context))

    # occ0 = NGƯỜI NỘP. Chọn ai + trạng thái checkbox theo mode.
    if owner_mode:
        submitter, is_owner = (owner or requester), True
    elif owner_matches and owner:
        submitter, is_owner = owner, True
    elif requester_matches and requester:
        submitter, is_owner = requester, False
    else:
        submitter, is_owner = None, False

    # Checkbox phải phát trước để portal render/clear đúng khối chủ hồ sơ.
    if owner or requester:
        add("data[isOwnerDossierCheck]", is_owner)

    if submitter:
        add("data[chonDoiTuong]", "Cá nhân")
        _add_person_block(
            add,
            "",
            name=submitter.get("name"),
            birthday=submitter.get("birthday"),
            gender=submitter.get("gender"),
            identity=submitter.get("identity"),
            issue_date=submitter.get("issue_date"),
            issue_place=submitter.get("issue_place"),
            residence=submitter.get("residence"),
            phone=submitter.get("phone"),
            occurrence=0,
        )
    elif not owner_mode and _has_context_anchor(context) and owner:
        anchor = context.get("applicant_identity") or context.get("applicant_name")
        warnings.append(
            "Không xác định được người nộp khớp thông tin trên form "
            f"({anchor}); không điền phần người nộp."
        )

    # Chủ hồ sơ luôn là người đề nghị/được ủy quyền thờ cúng, không phải người
    # đăng nhập. Điền rõ cả ngày sinh và ngày cấp vì portal sao chép không ổn định.
    if owner:
        add("data[chonDoiTuong1]", "Cá nhân")
        _add_person_block(
            add,
            "owner",
            name=owner.get("name"),
            birthday=owner.get("birthday"),
            gender=owner.get("gender"),
            identity=owner.get("identity"),
            issue_date=owner.get("issue_date"),
            issue_place=owner.get("issue_place"),
            residence=owner.get("residence"),
            phone=owner.get("phone"),
        )
    else:
        warnings.append("Chưa đọc được chủ hồ sơ từ mục 1 Đơn Mẫu 18/giấy ủy quyền.")

    # Chi tiết Mẫu 18 luôn theo chủ hồ sơ, kể cả người nộp UI là người khác.
    if owner:
        add("data[fullname]", owner.get("name"), occurrence=1)
        add("data[birthday]", _date(owner.get("birthday")), occurrence=1)
        add("data[gender]", _text(owner.get("gender")), occurrence=1)
        add("data[identityNumber]", _identity(owner.get("identity")), occurrence=1)
        add("data[identityDate]", _date(owner.get("issue_date")), occurrence=1)
        add(
            "data[identityAgency]",
            _issuer(owner.get("issue_place")) or _text(owner.get("issue_place")),
        )
        add("data[phoneNumber]", _phone(owner.get("phone")), occurrence=1)

        origin = _area(owner.get("origin"))
        if origin:
            add("data[province]", _province_label(origin.get("tinh")), occurrence=1)
            add("data[village]", _commune_label(origin.get("xa")))
            add("data[address]", _text(origin.get("diaChi")), occurrence=1)
        _add_area(
            add,
            "data[province1]",
            "data[village1]",
            "data[address1]",
            owner.get("residence"),
        )

    add("data[MqhVls1]", _text(values.get("ToKhai_MoiQuanHeVoiLietSi")))
    add("data[UqTcLs]", _joined_names(values.get("ToKhai_LietSiThoCung")))

    # Thông tin liệt sĩ + Bằng TQGC.
    add("data[address2]", _text(values.get("LietSi_QueQuan")))
    add("data[SoBtqGc]", _text(values.get("LietSi_SoBang")))
    add("data[SoQd]", _text(values.get("LietSi_SoQuyetDinh")))
    add("data[NgayQd]", _date(values.get("LietSi_NgayQuyetDinh")))

    # Bảng thân nhân liệt sĩ.
    than_nhan = _dedupe_relatives(values.get("ToKhai_ThanNhan"))
    for idx, item in enumerate(than_nhan[:8]):
        add(f"data[DataGrid][{idx}][Ht]", _item_text(item, "hoTen", "hoVaTen"))
        add(f"data[DataGrid][{idx}][Ns]", _year(_item_text(item, "namSinh", "ngaySinh")))
        add(f"data[DataGrid][{idx}][Nm]", _year(_item_text(item, "namMat", "ngayMat")))
        add(f"data[DataGrid][{idx}][Ntt]", _item_text(item, "noiThuongTru", "diaChi"))
        add(f"data[DataGrid][{idx}][MqhVls]", _item_text(item, "moiQuanHe", "mqh", "quanHe"))

    add(
        "data[hoSoDinhKem][0][textField1]",
        "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18)",
    )
    add("data[hoSoDinhKem][0][textField2]", "Bản chính")

    if not values.get("ToKhai_LietSiThoCung"):
        warnings.append("Chưa đọc được họ tên liệt sĩ được thờ cúng trong Đơn Mẫu 18.")
    return out, warnings
