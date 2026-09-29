"""Map compact source facts → Form.io data[...] fields cho "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh".

CHỦ HỒ SƠ = CƠ SỞ KCB (tổ chức) + NGƯỜI ĐẠI DIỆN (người ký Đơn). data[chonDoiTuong] = loại tổ chức phát ĐẦU
TIÊN: ô tên tổ chức (organization / ownerOrganizationFullname) chỉ hiện sau khi chọn.

Hai chế độ người nộp:
  · THEO TÀI KHOẢN (FE gửi họ tên/CCCD tài khoản trong formContext): tài khoản khớp người đại diện (CCCD,
    hoặc họ tên bỏ dấu) → TỰ NỘP; không khớp → NỘP THAY.
  · NGƯỜI NỘP = CHỦ HỒ SƠ (submitterMode="owner_as_submitter", hoặc FE không gửi mốc — extension đời
    cũ): luôn TỰ NỘP.
TỰ NỘP: Phần I = cơ sở (tên tổ chức, địa chỉ, SĐT, fax, email) + nhân thân người đại diện, tích
data[isOwnerDossierCheck] → cổng tự nhân bản sang Phần II.
NỘP THAY: Phần I = người nộp (cổng đổ họ tên + CCCD từ tài khoản; nhân thân khác chỉ từ CCCD người nộp khớp
tài khoản) + tên tổ chức; BỎ TÍCH rồi điền Phần II = cơ sở + người đại diện.
Chế độ theo tài khoản không ghi đè ô Phần I cổng đổ sẵn (họ tên, CCCD); chế độ người nộp = chủ hồ sơ thì ghi
đè bằng người đại diện để cả khối là một người.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.process.schema import UI_COMP_BY_NAME


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


def _account_anchor(options: dict | None) -> dict | None:
    """Mốc tài khoản cho chế độ THEO TÀI KHOẢN; None → chế độ người nộp = chủ hồ sơ.

    FE đời cũ không gửi formContext → mốc rỗng → coi là tự nộp thay vì đoán người nộp.
    """
    options = options or {}
    if str(options.get("submitterMode") or "") == "owner_as_submitter":
        return None
    context = options.get("formContext") or {}
    name = _text(context.get("applicantFullname"))
    identity = _identity(context.get("applicantIdentityNumber"))
    if not name and not identity:
        return None
    return {"name": name, "identity": identity}


def _matches_account(person: dict, anchor: dict) -> bool:
    # Có CCCD cả hai phía thì CCCD quyết: hai người trùng họ tên bỏ dấu chỉ tách được bằng CCCD.
    if anchor["identity"] and person.get("identity"):
        return person["identity"] == anchor["identity"]
    return bool(anchor["name"] and person.get("name") and _fold(person["name"]) == _fold(anchor["name"]))


def _org_type(value) -> str | None:
    folded = _fold(value)
    if "co quan" in folded:
        return "Cơ quan nhà nước"
    if "to chuc" in folded or "doanh nghiep" in folded:
        return "Tổ chức/Doanh nghiệp"
    return None


def _person(values: dict, prefix: str) -> dict:
    return {
        "name": _text(values.get(f"{prefix}HoTen")),
        "identity": _identity(values.get(f"{prefix}SoDinhDanh")),
        "birthday": _date(values.get(f"{prefix}NgaySinh")),
        "gender": _text(values.get(f"{prefix}GioiTinh")),
        "id_date": _date(values.get(f"{prefix}NgayCap")),
        "issuer": _issuer(values.get(f"{prefix}NoiCap")),
    }


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    anchor = _account_anchor(options)

    # Theo tài khoản: ô Phần I cổng đã đổ sẵn từ tài khoản VNeID (bị khoá) là đúng người nộp → KHÔNG điền
    # đè; giá trị OCR chỉ làm sai dấu. Theo tờ khai (anchor None) người nộp là người trong hồ sơ, KHÁC tài
    # khoản → phải ghi đè họ tên + CCCD, không thì khối thành nửa tài khoản nửa người trong hồ sơ.
    ctx = (options or {}).get("formContext") or {}
    portal_prefilled = {
        key
        for key, ctx_key in (
            ("data[fullname]", "applicantFullname"),
            ("data[identityNumber]", "applicantIdentityNumber"),
        )
        if anchor is not None and _text(ctx.get(ctx_key))
    }

    def add(name: str, value, *, default: bool = False) -> None:
        if name in seen or name in portal_prefilled or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _commune_label(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    def add_person(prefix: str, person: dict) -> None:
        keys = ("fullname", "birthday", "gender", "identityNumber", "identityDate", "idIssuePlace")
        if prefix:
            keys = ("Fullname", "Birthday", "Gender", "IdentityNumber", "IdentityDate", "IdIssuePlace")
        for key, attr in zip(keys, ("name", "birthday", "gender", "identity", "id_date", "issuer")):
            add(f"data[{prefix}{key}]", person.get(attr))

    org_name = _text(values.get("CoSo_Ten"))
    org_type = _org_type(values.get("CoSo_LoaiDoiTuong"))
    org_area = remap_area(_area(values.get("CoSo_DiaChi")))
    org_phone = _phone(values.get("CoSo_DienThoai"))
    org_fax = _text(values.get("CoSo_Fax"))
    org_email = _text(values.get("CoSo_Email"))
    rep = _person(values, "DaiDien_")

    if not org_name:
        warnings.append("Thiếu tên cơ sở khám bệnh, chữa bệnh từ Đơn Mẫu 02 / giấy phép hoạt động.")
    if org_type:
        add("data[chonDoiTuong]", org_type)
    elif org_name:
        # Không rõ công lập hay tư nhân: vẫn phải chọn loại tổ chức để ô tên tổ chức hiện ra.
        add("data[chonDoiTuong]", "Tổ chức/Doanh nghiệp", default=True)
        warnings.append("Chưa xác định cơ sở là cơ quan nhà nước hay tổ chức/doanh nghiệp — đã chọn "
                        "'Tổ chức/Doanh nghiệp', cán bộ kiểm tra lại ô Đối tượng nộp hồ sơ.")
    add("data[organization]", org_name)

    if anchor is None or _matches_account(rep, anchor):
        # === TỰ NỘP: Phần I = cơ sở + người đại diện, tích ô → cổng tự nhân bản sang Phần II. ===
        add("data[isOwnerDossierCheck]", True)
        add_person("", rep)
        add_area("data[province]", "data[district]", "data[address]", org_area)
        add("data[phoneNumber]", org_phone)
        add("data[email]", org_email)
        add("data[fax]", org_fax)
        return out, warnings

    # === NỘP THAY: Phần I = người nộp; nhân thân chỉ từ CCCD người nộp khớp tài khoản. ===
    submitter = _person(values, "NguoiNop_")
    if (submitter["name"] or submitter["identity"]) and _matches_account(submitter, anchor):
        add_person("", submitter)
    # Bỏ tích để cổng mở Phần II cho cơ sở.
    add("data[isOwnerDossierCheck]", False)

    add("data[ownerOrganizationFullname]", org_name)
    add_person("owner", rep)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", org_area)
    add("data[ownerPhoneNumber]", org_phone)
    add("data[ownerEmail]", org_email)
    add("data[ownerFax]", org_fax)
    add("data[ownerNation]", "Việt Nam" if org_name else None)
    missing = [label for label, key in (("ngày sinh", "birthday"), ("giới tính", "gender"), ("số CCCD", "identity"))
               if not rep.get(key)]
    if missing:
        warnings.append("Hồ sơ không có CCCD của người đại diện ký Đơn — thiếu " + ", ".join(missing)
                        + " ở Phần 2 (chủ hồ sơ), cán bộ nhập tay.")
    return out, warnings
