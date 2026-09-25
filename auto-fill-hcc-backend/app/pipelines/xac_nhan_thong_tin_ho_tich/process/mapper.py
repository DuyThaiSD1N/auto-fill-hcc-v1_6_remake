"""Đổi facts của hai người sang ô trên cổng — HAI bộ ô, mỗi bộ một frame.

Nguồn theo bảng mapping nghiệp vụ:
  NGƯỜI YÊU CẦU: tờ khai (TkNyc_*) ưu tiên, CCCD (Nyc_*) bù ngày sinh/giới tính và ô tờ khai bỏ trống.
  NGƯỜI ĐƯỢC XÁC NHẬN: tờ khai / giấy khai sinh (Dt_*) ưu tiên, CCCD/CMND của chính người đó (ChuThe_*)
  bù; địa chỉ ưu tiên thẻ của đối tượng như mapping ("theo thẻ đối tượng").

Bộ 1 — trang "Thông tin chủ hồ sơ" (Form.io data[...]): Phần 1 người nộp, Phần 2 chủ hồ sơ.
Bộ 2 — eForm hộ tịch (iframe, x-*): radio quan hệ, Mục I, Mục II, nội dung + lý do xác nhận.
Extension (content.js) tách bộ theo loại form của frame nên hai bộ không giẫm lên nhau.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.formatting import normalize_date, upper_person_name
from app.pipelines.trich_luc.process.mapper import _ethnicity_for_form
from app.pipelines.xac_nhan_thong_tin_ho_tich.process.schema import (
    EFORM_ALIASES,
    EFORM_COMP_BY_NAME,
    UI_COMP_BY_NAME,
)

_ALL_COMP_BY_NAME = {**UI_COMP_BY_NAME, **EFORM_COMP_BY_NAME}

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, (dict, list)):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    return normalize_date(f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else text) or None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "m"}:
        return "Nam"
    if folded in {"nu", "female", "f"}:
        return "Nữ"
    return None


def _person_name(value: Any) -> str | None:
    """Họ tên dạng "Nguyễn Bật Vấn" — CCCD in hoa toàn bộ, tờ khai viết thường."""
    text = _text(value)
    if not text:
        return None
    return " ".join(word[:1].upper() + word[1:].lower() for word in text.split())


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _province_label(value: Any) -> str | None:
    bare = _strip_admin_prefix(_text(value) or "")
    if not bare:
        return None
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not any(out[k] for k in ("tinh", "xa", "diaChi")):
        return None
    return remap_area(out, allow_diachi_fallback=True) or out


def _same_person(name_a: Any, id_a: Any, name_b: Any, id_b: Any) -> bool:
    """Số giấy tờ quyết định khi cả hai bên có; thiếu số mới so họ tên bỏ dấu."""
    digits_a, digits_b = _digits(id_a), _digits(id_b)
    if digits_a and digits_b:
        return digits_a == digits_b
    key_a, key_b = _fold(name_a).replace(" ", ""), _fold(name_b).replace(" ", "")
    return bool(key_a) and key_a == key_b


def _first(*values: Any) -> Any:
    return next((v for v in values if v not in (None, "", {}, [])), None)


def _requester(values: dict) -> dict:
    return {
        "name": _first(values.get("TkNyc_HoTen"), values.get("Nyc_HoTen")),
        "birthday": values.get("Nyc_NgaySinh"),
        "gender": values.get("Nyc_GioiTinh"),
        "identity": _first(values.get("TkNyc_SoGiayToTuyThan"), values.get("Nyc_SoDinhDanh")),
        "issue_date": _first(values.get("TkNyc_NgayCapGiayToTuyThan"), values.get("Nyc_NgayCap")),
        "issuer": _first(values.get("TkNyc_NoiCapGiayToTuyThan"), values.get("Nyc_NoiCap")),
        "area": _area(_first(values.get("TkNyc_NoiCuTru"), values.get("Nyc_NoiCuTru"))),
    }


def _skeleton(value: Any) -> str:
    """Bỏ dấu + khoảng trắng: "Nguyễn Bất Văn" và "NGUYỄN BẬT VẤN" cùng một khung chữ."""
    return _fold(value).replace(" ", "")


def _printed_name(handwritten: Any, printed: Any) -> Any:
    """Tên IN trên giấy khai sinh thắng tên VIẾT TAY trên tờ khai khi chỉ lệch dấu (lỗi OCR chữ viết)."""
    if printed and (not handwritten or _skeleton(handwritten) == _skeleton(printed)):
        return printed
    return handwritten


def _subject(values: dict) -> dict:
    return {
        "name": _first(_printed_name(values.get("Dt_HoTen"), values.get("Gks_HoTen")), values.get("ChuThe_HoTen")),
        "birthday": _first(values.get("Dt_NgaySinh"), values.get("Gks_NgaySinh"), values.get("ChuThe_NgaySinh")),
        "gender": _first(values.get("Dt_GioiTinh"), values.get("Gks_GioiTinh"), values.get("ChuThe_GioiTinh")),
        "ethnicity": _first(values.get("Dt_DanToc"), values.get("Gks_DanToc")),
        "nationality": _first(values.get("Dt_QuocTich"), values.get("Gks_QuocTich")),
        "identity": _first(values.get("Dt_SoGiayToTuyThan"), values.get("ChuThe_SoDinhDanh")),
        "issue_date": _first(values.get("Dt_NgayCapGiayToTuyThan"), values.get("ChuThe_NgayCap")),
        "issuer": _first(values.get("Dt_NoiCapGiayToTuyThan"), values.get("ChuThe_NoiCap")),
        # Mapping: tỉnh/xã/địa chỉ chủ hồ sơ "điền theo CCCD/CMND của đối tượng".
        "area": _area(_first(values.get("ChuThe_NoiCuTru"), values.get("Dt_NoiCuTru"))),
    }


def _drop_impossible_cmnd_date(person: dict, who: str, warnings: list[str]) -> None:
    """CMND 9 số ngừng cấp từ 2021 (chuyển sang CCCD gắn chip). Ngày cấp sau đó là OCR đọc nhầm — thường
    lấy nhầm ngày ký tờ khai ("Làm tại ..., ngày ... năm 2026") — nên bỏ, không điền sai."""
    date = _date(person.get("issue_date"))
    m = re.search(r"(\d{4})$", date or "")
    if len(_digits(person.get("identity"))) == 9 and m and int(m.group(1)) > 2021:
        person["issue_date"] = None
        warnings.append(
            f"Ngày cấp CMND của {who} đọc được là {date} — CMND 9 số không còn cấp sau năm 2021 nên chưa điền, "
            "vui lòng nhập tay."
        )


def _one_edit_apart(a: str, b: str) -> bool:
    """Hai chuỗi lệch đúng MỘT ký tự (thay/thêm/bớt) — kiểu OCR đọc "Nỷ" thành "Mỹ", "Xưa" thành "Sủa"."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _same_name_ocr(words: list[str], printed_words: list[str]) -> bool:
    """Khung chữ trùng hết, hoặc tên ≥ 3 chữ chỉ lệch MỘT ký tự ở MỘT chữ."""
    left = [_skeleton(w) for w in words]
    right = [_skeleton(w) for w in printed_words]
    if left == right:
        return True
    diffs = [(x, y) for x, y in zip(left, right) if x != y]
    return len(printed_words) >= 3 and len(diffs) == 1 and _one_edit_apart(*diffs[0])


def _fix_names_in_text(text: str | None, printed_names: list[Any], warnings: list[str] | None = None) -> str | None:
    """Sửa tên người trong đoạn VIẾT TAY theo chính tả IN trên giấy khai sinh (người được khai sinh, mẹ, cha)."""
    if not text:
        return text
    words = text.split()
    for printed in filter(None, printed_names):
        proper = _person_name(printed)
        printed_words = proper.split()
        size = len(printed_words)
        for start in range(len(words) - size + 1):
            window = words[start:start + size]
            trailing = re.search(r"[,.;:]+$", window[-1])
            bare = window[:-1] + [window[-1].rstrip(",.;:")]
            if not _same_name_ocr(bare, printed_words):
                continue
            if _skeleton(" ".join(bare)) != _skeleton(proper) and warnings is not None:
                warnings.append(
                    f"Nội dung xác nhận: đã sửa '{' '.join(bare)}' thành '{proper}' theo giấy khai sinh — vui lòng "
                    "kiểm tra lại."
                )
            words[start:start + size] = printed_words[:-1] + [printed_words[-1] + (trailing.group(0) if trailing else "")]
    return " ".join(words)


def _eform_area(area: dict | None) -> dict | None:
    """x-select-area của eForm hộ tịch nhận tỉnh/xã TRẦN (không tiền tố), như trích lục."""
    if not area:
        return None
    xa = re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", str(area.get("xa") or "").strip(), flags=re.IGNORECASE)
    return {
        "quocGia": area.get("quocGia") or "Việt Nam",
        "tinh": _strip_admin_prefix(area.get("tinh")),
        "xa": xa.strip(),
        "diaChi": _text(area.get("diaChi")) or "",
    }


def _id_doc_type(number: Any, issuer: str) -> str | None:
    """9 số → CMND; 12 số → "Căn cước công dân" (cổng gộp CCCD cũ và Căn cước mới)."""
    digits = _digits(number)
    if not digits:
        return None
    if len(digits) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type("Căn cước", issuer)


def _self_relation(value: Any) -> bool:
    return _fold(value) in {"ban than", "chinh minh", "tu ban than"}


def _nation(value: Any) -> str:
    text = _text(value)
    if not text or _fold(text) in {"viet nam", "vietnam", "vn"}:
        return "Việt Nam"
    return text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    _ = options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = _ALL_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in EFORM_ALIASES:
            field["aliases"] = EFORM_ALIASES[name]
        out.append(field)
        seen.add(name)

    requester = _requester(values)
    subject = _subject(values)
    _drop_impossible_cmnd_date(requester, "người yêu cầu", warnings)
    _drop_impossible_cmnd_date(subject, "người được xác nhận", warnings)
    values["ToKhai_NoiDung"] = _fix_names_in_text(
        _text(values.get("ToKhai_NoiDung")),
        [values.get("Gks_HoTen"), values.get("Gks_HoTenMe"), values.get("Gks_HoTenCha")],
        warnings,
    )

    # Người yêu cầu tự xin xác nhận cho mình: phần tờ khai hay CCCD đều cùng một người.
    self_request = bool(subject["name"] or subject["identity"]) and _same_person(
        requester["name"], requester["identity"], subject["name"], subject["identity"],
    )
    if self_request:
        for key in set(requester) | set(subject):
            if requester.get(key) in (None, "", {}, []):
                requester[key] = subject.get(key)
            if subject.get(key) in (None, "", {}, []):
                subject[key] = requester.get(key)

    if requester["name"] or requester["identity"]:
        if not requester["birthday"] or not requester["gender"]:
            warnings.append(
                "Hồ sơ không có CCCD của người yêu cầu — ngày sinh, giới tính ở mục Thông tin người nộp hồ sơ "
                "còn trống, vui lòng nhập tay."
            )
        add("data[fullname]", _person_name(requester["name"]))
        add("data[birthday]", _date(requester["birthday"]))
        add("data[gender]", _gender(requester["gender"]))
        add("data[identityNumber]", _digits(requester["identity"]) or None)
        add("data[identityDate]", _date(requester["issue_date"]))
        add("data[idIssuePlace]", normalize_issuer(requester["issuer"]) or None)
        if requester["area"]:
            add("data[province]", _province_label(requester["area"].get("tinh")))
            add("data[district]", _text(requester["area"].get("xa")))
            add("data[address]", _text(requester["area"].get("diaChi")))
    else:
        warnings.append(
            "Không đọc được người yêu cầu (tờ khai hoặc CCCD) — vui lòng điền tay mục Thông tin người nộp hồ sơ."
        )

    if self_request:
        add("data[isOwnerDossierCheck]", True)
    elif subject["name"] or subject["identity"]:
        add("data[isOwnerDossierCheck]", False)
        add("data[ownerFullname]", _person_name(subject["name"]))
        add("data[ownerBirthday]", _date(subject["birthday"]))
        add("data[ownerGender]", _gender(subject["gender"]))
        add("data[ownerDanToc]", _text(subject["ethnicity"]))
        add("data[ownerNation]", _nation(subject["nationality"]))
        add("data[ownerIdentityNumber]", _digits(subject["identity"]) or None)
        add("data[ownerIdentityDate]", _date(subject["issue_date"]))
        add("data[ownerIdIssuePlace]", normalize_issuer(subject["issuer"]) or None)
        if subject["area"]:
            add("data[ownerProvince]", _province_label(subject["area"].get("tinh")))
            add("data[ownerDistrict]", _text(subject["area"].get("xa")))
            add("data[ownerAddress]", _text(subject["area"].get("diaChi")))
        else:
            warnings.append(
                "Hồ sơ không có CCCD/CMND hay nơi cư trú của người được xác nhận — vui lòng chọn Tỉnh, "
                "Phường/Xã và nhập địa chỉ ở mục Thông tin chủ hồ sơ."
            )
        if not subject["identity"]:
            warnings.append(
                "Không đọc được số CMND/CCCD của người được xác nhận (bắt buộc) — vui lòng nhập tay."
            )
    else:
        warnings.append(
            "Không đọc được người được xác nhận thông tin hộ tịch (tờ khai hoặc giấy khai sinh) — vui lòng "
            "điền tay mục Thông tin chủ hồ sơ."
        )

    _add_eform(add, requester, subject, values, self_request)

    warnings.append("Số điện thoại người nộp hồ sơ (bắt buộc) không có trong giấy tờ — vui lòng nhập tay.")
    return out, warnings


def _add_eform(add, requester: dict, subject: dict, values: dict, self_request: bool) -> None:
    """Bộ ô eForm hộ tịch. Radio quan hệ đi TRƯỚC vì đổi option làm cổng dựng lại khối nhân thân."""
    has_requester = bool(requester["name"] or requester["identity"])
    has_subject = bool(subject["name"] or subject["identity"])
    if not has_requester and not has_subject:
        return

    add("doiTuongYeuCau", "Cá nhân")
    if self_request or (not has_subject and _self_relation(values.get("ToKhai_QuanHe"))):
        add("nycQuanHe", "Bản thân")
    elif has_requester and has_subject:
        add("nycQuanHe", "Khác")
        relation = _text(values.get("ToKhai_QuanHe"))
        if relation and not _self_relation(relation):
            # Ô nhập chỉ có tác dụng sau khi tick "Khác" → phát NGAY SAU radio. "con đẻ" → "Con đẻ".
            add("nycQuanHeKhac", relation[:1].upper() + relation[1:])

    if has_requester:
        issuer = normalize_issuer(requester["issuer"]) or default_issuer(_date(requester["issue_date"]))
        number = _digits(requester["identity"]) or None
        add("HoVaTenC", upper_person_name(requester["name"]))
        add("SoDinhDanhC", number if number and len(number) == 12 else None)
        add("LoaiGiayToDinhDanhC", _id_doc_type(number, issuer))
        add("SoGiayToTuyThanC", number)
        add("NgayCapDDC", _date(requester["issue_date"]))
        add("NoiCapDDC", issuer if number else None)
        area = _eform_area(requester["area"])
        if area:
            add("nycLoaiCuTru", "Thường trú")
            add("nycNoiCuTru", "Trong nước")
            add("nycNoiCuTru_TruongNuoc", area)

    person = subject
    if has_subject:
        number = _digits(person["identity"]) or None
        issuer = normalize_issuer(person["issuer"]) or (default_issuer(_date(person["issue_date"])) if number else "")
        add("hoTenNguoiDuocXN", upper_person_name(person["name"]))
        add("ngaySinhNguoiDuocXN", _date(person["birthday"]))
        add("duocXNGioiTinh", _gender(person["gender"]))
        ethnicity, other_ethnicity = _ethnicity_for_form(_text(person.get("ethnicity")) or "")
        add("danTocNguoiDuocXN", ethnicity)
        add("danTocKhacNguoiDuocXN", other_ethnicity)
        add("quocTichNguoiDuocXN", _nation(person.get("nationality")))
        add("duocXNDDCN", number if number and len(number) == 12 else None)
        add("duocXNLoaiGiayToTuyThan", _id_doc_type(number, issuer))
        add("duocXNSoGiayToTuyThan", number)
        add("duocXNNgayCapGiayToTuyThan", _date(person["issue_date"]))
        add("duocXNNoiCapGiayToTuyThan", issuer or None)
        area = _eform_area(person["area"])
        if area:
            add("duocXNLoaiCuTru", "Thường trú")
            add("duocXNNoiCuTru", "Trong nước")
            add("duocXNNoiCuTru_TrongNuoc", area)

    add("noiDungXacNhan", _text(values.get("ToKhai_NoiDung")))
    add("lyDoXacNhan", _text(values.get("ToKhai_LyDo")))
