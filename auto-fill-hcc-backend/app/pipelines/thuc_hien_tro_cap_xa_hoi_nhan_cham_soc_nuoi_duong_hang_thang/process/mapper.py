"""Map compact source facts → Form.io data[...] fields cho thủ tục "Thực hiện trợ cấp xã hội và nhận chăm
sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm sóc, nuôi dưỡng hằng tháng" (NĐ 335/2026/NĐ-CP).

HAI vai:
  Phần 1 (data[fullname...])   — NGƯỜI NỘP, 2 chế độ (như tro_cap_xa_hoi_hang_thang):
      · THEO TÀI KHOẢN (FE gửi họ tên/CCCD tài khoản trong formContext): chọn người khai thay hoặc đối tượng
        khớp tài khoản (CCCD, hoặc họ tên bỏ dấu); họ tên + CCCD LUÔN lấy của tài khoản vì cổng đã điền sẵn
        theo định danh điện tử.
      · THEO TỜ KHAI (submitterMode="owner_as_submitter", hoặc FE không gửi mốc): người khai thay (người
        giám hộ mục I.2 / người nhận thay mục III.1 / người khai Mẫu 02); không có → dùng đối tượng.
  Phần 2 (data[owner*])        — CHỦ HỒ SƠ = ĐỐI TƯỢNG hưởng trợ cấp. LUÔN bỏ tích isOwnerDossierCheck +
                                 điền tường minh. SĐT đối tượng trống (trẻ em) → dùng SĐT người khai thay vì
                                 ô SĐT chủ hồ sơ là bắt buộc.
  data[ghiChu]                 — "Người nộp là người giám hộ (<quan hệ>) của chủ hồ sơ" khi người nộp là
                                 người khai thay và tờ khai ghi quan hệ.
Cờ subjectAsSubmitter (phường Yên Bái): Phần I = ĐỐI TƯỢNG (bỏ qua người khai thay lẫn mốc tài khoản), TÍCH
isOwnerDossierCheck để cổng tự đổ Phần I → Phần II, KHÔNG điền owner_* và ghiChu. Đối tượng không có SĐT → dùng
SĐT người khai thay vì ô SĐT người nộp bắt buộc. Runner kèm enableInput cho họ tên + CCCD Phần I.
Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, ISSUER_CUC, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.schema import UI_COMP_BY_NAME


# Cấu hình theo tài khoản: phường Yên Bái (Lào Cai) khai ĐỐI TƯỢNG hưởng trợ cấp vừa là người nộp vừa là chủ
# hồ sơ, kể cả khi tờ khai có người giám hộ; nơi khác giữ nguyên logic. Mapper không biết tài khoản nên router
# (Auto Fill) và pipeline_runner (Handfree) gọi with_account_process_options để server tự đặt cờ; cờ luôn bị
# ghi đè theo tài khoản, client không tự bật được cho xã khác.
PROCEDURE_KEY = "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang"
SUBJECT_AS_SUBMITTER_OPTION = "subjectAsSubmitter"


def is_lao_cai_yen_bai(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Yên Bái, tỉnh Lào Cai (khớp tỉnh và ĐÚNG tên phường)."""
    if not user:
        return False
    return "lao cai" in _fold(user.get("tinh")) and _locality_key(user.get("xa")) == "yen bai"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ theo tài khoản do server quyết (đối tượng vừa nộp vừa là chủ hồ sơ)."""
    result = dict(options or {})
    result.pop(SUBJECT_AS_SUBMITTER_OPTION, None)
    if procedure == PROCEDURE_KEY and is_lao_cai_yen_bai(user):
        result[SUBJECT_AS_SUBMITTER_OPTION] = True
    return result


def subject_as_submitter(options: dict | None) -> bool:
    return (options or {}).get(SUBJECT_AS_SUBMITTER_OPTION) is True


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
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã|đặc khu)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("thanh pho ", "tp ")):
        return text
    folded = _fold(_strip_admin_prefix(text))
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue", "bac ninh"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _locality_key(value: Any) -> str:
    """Khóa so xã/phường, chịu được tiền tố Phường/P./Xã và khác biệt dấu câu."""
    text = re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()
    return re.sub(r"^(?:phuong|p|xa|thi tran|tt|dac khu)\s+", "", text).strip()


def _complete_missing_provinces(*areas: dict | None) -> None:
    """Bổ sung tỉnh khi cùng xã/phường chỉ ánh xạ tới đúng một tỉnh trong chính hồ sơ.

    Tỉnh đã có không bao giờ bị ghi đè; tên xã trùng nhiều tỉnh thì giữ trống.
    """
    province_by_locality: dict[str, dict[str, str]] = {}
    for area in areas:
        if not area:
            continue
        locality = _locality_key(area.get("xa"))
        province = _text(area.get("tinh"))
        if not locality or not province:
            continue
        province_key = _fold(_strip_admin_prefix(province))
        if province_key:
            province_by_locality.setdefault(locality, {}).setdefault(province_key, province)

    for area in areas:
        if not area or _text(area.get("tinh")):
            continue
        candidates = province_by_locality.get(_locality_key(area.get("xa")), {})
        if len(candidates) == 1:
            area["tinh"] = next(iter(candidates.values()))


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


def _validated_submitter_identity(value: Any) -> str | None:
    """Người khai thay chỉ được điền CMND 9 số hoặc CCCD 12 số; không sửa đoán OCR sai."""
    digits = _identity(value)
    return digits if digits and len(digits) in {9, 12} else None


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


def _issuer(value: Any, id_date: str | None = None, identity: str | None = None) -> str | None:
    """Nơi cấp căn cước. Thẻ 12 số có ngày cấp thì ngày cấp quyết định: từ 01/07/2024 là thẻ Căn cước (Bộ
    Công an), 2021 → 30/06/2024 là CCCD gắn chip (Cục Cảnh sát QLHC về TTXH). Tờ khai hay ghi chung "Bộ
    Công an" cho cả CCCD gắn chip, và một tờ khai có thể ghi hai nơi cấp khác nhau cho cùng một người."""
    text = _text(value)
    issuer = normalize_issuer(text) if text else None
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", id_date or "")
    if not m or not identity or len(identity) != 12:
        return issuer
    ymd = (int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if ymd >= (2024, 7, 1):
        return ISSUER_BO_CONG_AN
    if ymd >= (2021, 1, 1) and issuer in (None, ISSUER_BO_CONG_AN):
        return ISSUER_CUC
    return issuer


def _relation(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text[:1].upper() + text[1:]


def _account_anchor(options: dict | None) -> dict | None:
    """Mốc tài khoản cho chế độ THEO TÀI KHOẢN; None → chạy chế độ tờ khai."""
    options = options or {}
    if str(options.get("submitterMode") or "") == "owner_as_submitter":
        return None
    context = options.get("formContext") or {}
    name = _text(context.get("applicantFullname"))
    identity = _identity(context.get("applicantIdentityNumber"))
    if not name and not identity:
        return None
    return {"name": name, "identity": identity}


def _account_submitter(candidates: list[dict], anchor: dict) -> dict | None:
    # Khớp CCCD trước: hai người trong hồ sơ trùng họ tên bỏ dấu thì CCCD mới tách được.
    for person in candidates:
        if anchor["identity"] and person.get("identity") == anchor["identity"]:
            return person
    for person in candidates:
        if anchor["name"] and person.get("name") and _fold(person["name"]) == _fold(anchor["name"]):
            return person
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    anchor = _account_anchor(options)
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

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _text(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    # --- ĐỐI TƯỢNG hưởng trợ cấp = chủ hồ sơ ---
    subject = {
        "name": _text(values.get("DoiTuong_HoTen")),
        "identity": _identity(values.get("DoiTuong_SoDinhDanh")),
        "birthday": _date(values.get("DoiTuong_NgaySinh")),
        "gender": _text(values.get("DoiTuong_GioiTinh")),
        "id_date": _date(values.get("DoiTuong_NgayCap")),
        "issuer": None,
        "residence": _area(values.get("DoiTuong_NoiCuTru")),
        "phone": _phone(values.get("DoiTuong_DienThoai")),
        "email": _text(values.get("DoiTuong_Email")),
    }
    if not subject["name"]:
        warnings.append("Thiếu họ tên đối tượng hưởng trợ cấp từ Tờ khai/CCCD/Giấy khai sinh.")

    # --- NGƯỜI KHAI THAY (người giám hộ / người nhận thay / người khai Mẫu 02) ---
    declarant = {
        "name": _text(values.get("NguoiNop_HoTen")),
        "identity": _validated_submitter_identity(values.get("NguoiNop_SoDinhDanh")),
        "birthday": _date(values.get("NguoiNop_NgaySinh")),
        "gender": _text(values.get("NguoiNop_GioiTinh")),
        "id_date": _date(values.get("NguoiNop_NgayCap")),
        "issuer": None,
        "residence": _area(values.get("NguoiNop_NoiCuTru")),
        "phone": _phone(values.get("NguoiNop_DienThoai")),
        "email": _text(values.get("NguoiNop_Email")),
    }
    subject["issuer"] = _issuer(values.get("DoiTuong_NoiCap"), subject["id_date"], subject["identity"])
    declarant["issuer"] = _issuer(values.get("NguoiNop_NoiCap"), declarant["id_date"], declarant["identity"])
    has_declarant = bool(declarant["name"] or declarant["identity"])

    subject_submits = subject_as_submitter(options) and bool(subject["name"] or subject["identity"])
    if subject_submits:
        # Yên Bái: đối tượng tự đứng tên cả hai phần; SĐT trống thì mượn SĐT người khai thay (ô bắt buộc).
        submitter = {**subject, "phone": subject["phone"] or declarant["phone"]}
        submitter_is_declarant = False
    elif anchor:
        candidates = [declarant, subject] if has_declarant else [subject]
        matched = _account_submitter(candidates, anchor)
        if matched is None:
            # Người đăng nhập không có trong hồ sơ: chỉ họ tên + CCCD tài khoản là chắc chắn của họ.
            submitter = {"name": anchor["name"], "identity": anchor["identity"]}
            warnings.append(
                "Không tìm thấy người nộp khớp tài khoản "
                f"({anchor['identity'] or anchor['name']}) trong tờ khai/giấy tờ; "
                "chỉ điền họ tên và số định danh của tài khoản."
            )
        else:
            submitter = {
                **matched,
                "name": anchor["name"] or matched.get("name"),
                "identity": anchor["identity"] or matched.get("identity"),
            }
        submitter_is_declarant = matched is declarant
    else:
        submitter = declarant if has_declarant else subject
        submitter_is_declarant = has_declarant

    residence = subject["residence"]
    nop_residence = submitter.get("residence")
    _complete_missing_provinces(residence, nop_residence, declarant["residence"])

    # Remap phường/xã theo bảng sáp nhập; chạy SAU _complete_missing_provinces vì lookup cần có tỉnh.
    residence = remap_area(residence)
    nop_residence = remap_area(nop_residence)

    add("data[chonDoiTuong]", "Cá nhân")
    add("data[fullname]", submitter.get("name"))
    add("data[birthday]", submitter.get("birthday"))
    add("data[gender]", submitter.get("gender"))
    add("data[identityNumber]", submitter.get("identity"))
    add("data[identityDate]", submitter.get("id_date"))
    add("data[idIssuePlace]", submitter.get("issuer"))
    add_area("data[province]", "data[district]", "data[address]", nop_residence)
    add("data[phoneNumber]", submitter.get("phone"))
    add("data[email]", submitter.get("email"))
    if "data[email]" not in seen:
        # Cổng nhớ email của lượt nộp trước và tự điền lại → hồ sơ không có email người nộp thì XOÁ ô.
        out.append({"name": "data[email]", "comp": UI_COMP_BY_NAME["data[email]"], "value": "", "clear": True})
        seen.add("data[email]")

    if subject_submits:
        # Người nộp là chủ hồ sơ: tích để cổng tự đổ Phần I → Phần II, không đè owner_*.
        add("data[isOwnerDossierCheck]", True)
        return out, warnings

    # --- Mở khoá Phần II: BỎ TÍCH "Người nộp là chủ hồ sơ" ---
    add("data[isOwnerDossierCheck]", False)

    # --- Phần II: chủ hồ sơ = ĐỐI TƯỢNG hưởng trợ cấp ---
    add("data[ownerFullname]", subject["name"])
    add("data[ownerBirthday]", subject["birthday"])
    add("data[ownerGender]", subject["gender"])
    add("data[ownerIdentityNumber]", subject["identity"])
    add("data[ownerIdentityDate]", subject["id_date"])
    add("data[ownerIdIssuePlace]", subject["issuer"])
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    # Ô SĐT chủ hồ sơ bắt buộc; đối tượng (thường là trẻ em) không có SĐT → dùng SĐT người khai thay.
    add("data[ownerPhoneNumber]", subject["phone"] or declarant["phone"])
    add("data[ownerEmail]", subject["email"])
    add("data[ownerNation]", "Việt Nam" if subject["name"] or subject["identity"] else None)

    relation = _relation(values.get("NguoiNop_QuanHe"))
    if submitter_is_declarant and relation:
        add("data[ghiChu]", f"Người nộp là người giám hộ ({relation}) của chủ hồ sơ")

    return out, warnings
