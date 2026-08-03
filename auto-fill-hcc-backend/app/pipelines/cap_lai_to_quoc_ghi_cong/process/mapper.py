"""Map fact tờ khai Mẫu 16 + CCCD sang field Form.io của thủ tục Cấp lại Bằng TQGC.

Điểm đặc thù:
- Field dùng chung giữa Phần I (người nộp) và Phần III.1 (chi tiết người đề nghị) được điền
  bằng cùng formcontrolname nhưng khác occurrence (0 = Phần I, 1 = Phần III).
- Cư trú/quê quán ƯU TIÊN TỜ KHAI vì CCCD có thể còn ghi đơn vị hành chính cũ trước sáp nhập
  (vd CCCD "Xuân Lâm, Thuận Thành" ↔ tờ khai "Phường Song Liễu"); còn số định danh/ngày cấp/nơi
  cấp thì ưu tiên CCCD.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_to_quoc_ghi_cong.process.schema import UI_COMP_BY_NAME


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
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text


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
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


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


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _same_person(doc_id: Any, doc_name: Any, ctx_id: Any, ctx_name: Any) -> bool:
    did, cid = _identity(doc_id), _identity(ctx_id)
    if did and cid:
        return did == cid
    dname, cname = _fold(doc_name), _fold(ctx_name)
    return bool(dname and cname and dname == cname)


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(k) for k in keys)))


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
    email=None,
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
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()
    context = _form_context(options)

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

    # Định danh/ngày cấp/nơi cấp ưu tiên CCCD; họ tên/ngày sinh/giới tính ưu tiên CCCD, fallback tờ khai.
    candidate_name = _text(_pick(values.get("Person1_HoTen"), values.get("ToKhai_HoTen")))
    candidate_identity = _identity(_pick(values.get("Person1_SoDinhDanh"), values.get("ToKhai_SoDinhDanh")))
    candidate_birthday = _pick(values.get("Person1_NgaySinh"), values.get("ToKhai_NgaySinh"))
    candidate_gender = _pick(values.get("Person1_GioiTinh"), values.get("ToKhai_GioiTinh"))
    candidate_issue_date = _date(_pick(values.get("Person1_NgayCap"), values.get("ToKhai_NgayCap")))
    candidate_issue_place = _pick(values.get("Person1_NoiCap"), values.get("ToKhai_NoiCap"))
    # Cư trú ưu tiên TỜ KHAI (đơn vị hành chính hiện hành), fallback CCCD.
    candidate_residence = _area(values.get("ToKhai_NoiThuongTru")) or _area(values.get("Person1_NoiCuTru"))
    candidate_phone = values.get("ToKhai_DienThoai")

    if not candidate_name or not candidate_identity:
        warnings.append("Thiếu họ tên hoặc số định danh người đề nghị từ tờ khai/CCCD.")

    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(candidate_identity, candidate_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    # --- Phần I: Thông tin người nộp hồ sơ (occurrence 0) ---
    if can_fill_applicant:
        add("data[chonDoiTuong]", "Cá nhân")
        _add_person_block(
            add,
            "",
            name=candidate_name,
            birthday=candidate_birthday,
            gender=candidate_gender,
            identity=candidate_identity,
            issue_date=candidate_issue_date,
            issue_place=candidate_issue_place,
            residence=candidate_residence,
            phone=candidate_phone,
            occurrence=0,
        )
        add("data[isOwnerDossierCheck]", True)
    else:
        add("data[isOwnerDossierCheck]", False)
        add("data[chonDoiTuong1]", "Cá nhân")

    # --- Phần II: Thông tin chủ hồ sơ (đối tượng thụ hưởng, trùng người đề nghị) ---
    _add_person_block(
        add,
        "owner",
        name=candidate_name,
        birthday=candidate_birthday,
        gender=candidate_gender,
        identity=candidate_identity,
        issue_date=candidate_issue_date,
        issue_place=candidate_issue_place,
        residence=candidate_residence,
        phone=candidate_phone,
    )

    # --- Phần III.1: Chi tiết mẫu khai — người đề nghị (occurrence 1, đồng bộ Phần I) ---
    add("data[fullname]", candidate_name, occurrence=1)
    add("data[birthday]", _date(candidate_birthday), occurrence=1)
    add("data[gender]", _text(candidate_gender), occurrence=1)
    add("data[identityNumber]", candidate_identity, occurrence=1)
    add("data[identityDate]", candidate_issue_date, occurrence=1)
    add("data[identityAgency]", _issuer(candidate_issue_place) or _text(candidate_issue_place))
    add("data[phoneNumber]", _phone(candidate_phone), occurrence=1)
    # Quê quán → province#1 / village / address#1 (ưu tiên tờ khai).
    que_quan = _area(values.get("ToKhai_QueQuan"))
    if que_quan:
        add("data[province]", _province_label(que_quan.get("tinh")), occurrence=1)
        add("data[village]", _commune_label(que_quan.get("xa")))
        add("data[address]", _text(que_quan.get("diaChi")), occurrence=1)
    # Nơi thường trú → province1 / district1 / address1.
    _add_area(add, "data[province1]", "data[district1]", "data[address1]", candidate_residence)
    add("data[MqhVls1]", _text(values.get("ToKhai_MoiQuanHeVoiLietSi")))
    add("data[denghiCap]", _text(values.get("ToKhai_DeNghiCap")) or "Cấp lại")
    add("data[lydoCap]", _text(values.get("ToKhai_LyDoCap")))

    # --- Phần III.2: Thông tin về liệt sĩ ---
    add("data[fullname1]", _text(values.get("LietSi_HoTen")))
    add("data[birthday1]", _text(values.get("LietSi_NgaySinh")))  # giữ nguyên văn, kể cả "không nhớ".
    add("data[gender1]", _text(values.get("LietSi_GioiTinh")))
    _add_area(add, "data[province2]", "data[district2]", "data[address2]", values.get("LietSi_QueQuan"))
    add("data[ngayHiSinh]", _date(values.get("LietSi_NgayHySinh")))
    add("data[capBac]", _text(values.get("LietSi_CapBac")))
    add("data[SoBtqGc]", _text(values.get("LietSi_SoBang")))
    add("data[SoQd]", _text(values.get("LietSi_SoQuyetDinh")))
    add("data[NgayQd]", _date(values.get("LietSi_NgayQuyetDinh")))
    add("data[donviCap]", _text(values.get("LietSi_DonViCapBang")))

    # --- Phần III.3: Thân nhân liệt sĩ (DataGrid) ---
    than_nhan = _list(values.get("ToKhai_ThanNhan"))
    for idx, item in enumerate(than_nhan[:6]):
        add(f"data[DataGrid][{idx}][Ht]", _item_text(item, "hoTen", "hoVaTen"))
        add(f"data[DataGrid][{idx}][Ns]", _item_text(item, "ngaySinh", "namSinh"))
        add(f"data[DataGrid][{idx}][MqhVls]", _item_text(item, "moiQuanHe", "mqh", "quanHe"))

    # --- Khai báo hồ sơ đính kèm (dòng đầu) ---
    add("data[hoSoDinhKem][0][textField1]", 'Đơn đề nghị cấp lại Bằng "Tổ quốc ghi công" (Mẫu số 16)')
    add("data[hoSoDinhKem][0][textField2]", "Bản chính")

    if not values.get("LietSi_HoTen"):
        warnings.append("Chưa đọc được họ tên liệt sĩ ở mục 2 tờ khai Mẫu 16.")
    if not than_nhan:
        warnings.append("Chưa đọc được bảng thân nhân liệt sĩ ở mục 3 tờ khai Mẫu 16.")
    return out, warnings
