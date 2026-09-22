"""Map compact disability-procedure facts to Form.io DOM fields."""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines.khuyet_tat.process.schema import (
    DISABILITY_RADIO_FIELDS,
    MUC_DO_RADIO_FIELDS,
    UI_COMP_BY_NAME,
)

_VALID_MUC_DO = {"THD", "CTG", "KTHD", "KXD"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _norm_text(value) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _strip_admin_prefix(value):
    text = str(value or "").strip()
    prefixes = (
        "thành phố",
        "tỉnh",
        "thị trấn",
        "thị xã",
        "phường",
        "xã",
        "huyện",
        "quận",
        "tp.",
        "tt.",
    )
    changed = True
    while changed:
        changed = False
        low = text.lower()
        for prefix in prefixes:
            if low == prefix:
                return ""
            if low.startswith(prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": _strip_admin_prefix(value.get("tinh") or value.get("tỉnh") or ""),
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or ""),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _phone(value) -> str:
    text = str(value or "").translate(str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "I": "1", "l": "1"}))
    digits = re.sub(r"\D+", "", text)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    elif len(digits) == 9 and digits[0] in "35789":
        digits = "0" + digits
    return digits if len(digits) in (10, 11) and digits.startswith("0") else ""


def _identity(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _same_person(context_name, context_identity, owner_name, owner_identity) -> bool:
    """Chỉ coi hai vai trùng khi mọi mỏ neo UI đang có đều khớp chủ hồ sơ."""
    ctx_name = _norm_text(context_name)
    ctx_identity = _identity(context_identity)
    if not ctx_name and not ctx_identity:
        return False
    if ctx_name and ctx_name != _norm_text(owner_name):
        return False
    if ctx_identity and ctx_identity != _identity(owner_identity):
        return False
    return True


def _relation(value) -> str:
    raw = str(value or "").strip()
    folded = _norm_text(raw)
    if any(word in folded.split() for word in ("bo", "cha")):
        return "Cha"
    if "me" in folded.split():
        return "Mẹ"
    if folded.startswith("ong") or " ong " in f" {folded} ":
        return "Ông"
    if folded.startswith("ba") or " ba " in f" {folded} ":
        return "Bà"
    for label in ("Vợ", "Chồng", "Con", "Anh", "Chị", "Em", "Cháu ruột", "Chủ hộ", "Khác"):
        if _norm_text(label) in folded:
            return label
    return raw


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;\s]+", value)
        return [p.strip() for p in parts if p.strip()]
    return []


def _compact_code(value) -> str:
    folded = _norm_text(value)
    folded = folded.replace("kt ", "kt")
    match = re.search(r"\bkt([1-6])(?:[_\-. ]?([1-7]))?\b", folded)
    if match:
        return f"kt{match.group(1)}" + (f"_{match.group(2)}" if match.group(2) else "")
    # Map ten day du / so thu tu -> ma
    _NAME_MAP = {
        "van dong": "kt1", "van": "kt1",
        "nghe noi": "kt2", "nghe": "kt2", "noi": "kt2",
        "nhin": "kt3", "mat": "kt3",
        "than kinh": "kt4", "tam than": "kt4", "than kinh tam than": "kt4",
        "tri tue": "kt5", "cham phat trien": "kt5",
        "khac": "kt6",
    }
    # So thu tu 1-6 mapping truc tiep
    num_match = re.fullmatch(r"([1-6])", folded.strip())
    if num_match:
        return f"kt{num_match.group(1)}"
    for key, code in _NAME_MAP.items():
        if key in folded:
            return code
    return folded


def _owner_profile(values: dict) -> dict:
    """Hồ sơ CHỦ HỒ SƠ = người đứng đơn trong Mẫu số 01.

    LLM nhiều lần chỉ trả ``Ndd_*``/``Nkt_*`` mà bỏ trống nhóm ``ChuHoSo_*`` vì thấy
    thông tin đã có ở mục II/mục I. Trước đây mapper coi như không có chủ hồ sơ nên
    KHÔNG phát ``data[isOwnerDossierCheck]``, cổng giữ nguyên tích "Người nộp hồ sơ
    là chủ hồ sơ" và khối chủ hồ sơ bị khoá theo tài khoản đang đăng nhập. Suy ngược
    từ mục II (người đại diện hợp pháp đứng đơn), hết mới tới mục I (người khuyết tật
    tự đề nghị), để luôn biết chủ hồ sơ là ai mà quyết định bỏ tích.
    """
    profile = {
        "name": values.get("ChuHoSo_HoTen"),
        "identity": _identity(values.get("ChuHoSo_SoDinhDanh")),
        "birthday": values.get("ChuHoSo_NgaySinh"),
        "gender": values.get("ChuHoSo_GioiTinh"),
        "identityDate": values.get("ChuHoSo_NgayCap"),
        "issuer": values.get("ChuHoSo_NoiCap"),
        "area": _area(values.get("ChuHoSo_NoiCuTru")),
        "phone": values.get("ChuHoSo_DienThoai"),
        "nation": values.get("ChuHoSo_QuocTich"),
    }
    if profile["name"] or profile["identity"]:
        return profile

    ndd_identity = _identity(values.get("Ndd_SoDinhDanh"))
    if values.get("Ndd_HoTen") or ndd_identity:
        profile["name"] = values.get("Ndd_HoTen")
        profile["identity"] = ndd_identity
        profile["area"] = profile["area"] or _area(values.get("Ndd_NoiCuTru"))
        profile["phone"] = profile["phone"] or values.get("Ndd_SoDienThoai")
        return profile

    nkt_identity = _identity(values.get("Nkt_SoDinhDanh"))
    if values.get("Nkt_HoTen") or nkt_identity:
        profile["name"] = values.get("Nkt_HoTen")
        profile["identity"] = nkt_identity
        profile["birthday"] = profile["birthday"] or values.get("Nkt_NgaySinh")
        profile["gender"] = profile["gender"] or values.get("Nkt_GioiTinh")
        profile["area"] = profile["area"] or _area(values.get("Nkt_ThuongTru"))

    return profile


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False, extra: dict | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        if extra:
            item.update(extra)
        out.append(item)
        seen.add(name)

    context = (options or {}).get("formContext") or {}
    applicant_name = str(context.get("applicantFullname") or context.get("fullname") or "").strip()
    applicant_identity = _identity(
        context.get("applicantIdentityNumber") or context.get("identityNumber")
    )

    requester_name = values.get("NguoiNop_HoTen")
    requester_identity = _identity(values.get("NguoiNop_SoDinhDanh"))
    requester_matches_applicant = _same_person(
        applicant_name,
        applicant_identity,
        requester_name,
        requester_identity,
    )
    requester_area = (
        _area(values.get("NguoiNop_NoiCuTru"))
        if requester_matches_applicant
        else None
    )

    owner = _owner_profile(values)
    owner_name = owner["name"]
    owner_identity = owner["identity"]
    owner_area = owner["area"]
    owner_issuer = owner["issuer"]
    owner_present = bool(owner_name or owner_identity)
    owner_matches_applicant = owner_present and _same_person(
        applicant_name,
        applicant_identity,
        owner_name,
        owner_identity,
    )

    # Checkbox phải phát trước hai khối. Cổng có side effect copy/reset Chủ hồ sơ
    # khi đổi checkbox, nên mọi field phụ thuộc luôn được gửi sau action này.
    if owner_present:
        add("data[isOwnerDossierCheck]", bool(owner_matches_applicant))

    # Tên + CCCD UI là mỏ neo có thẩm quyền. Các field nhân thân còn lại chỉ
    # được nhận từ NguoiNop_* sau khi LLM trả lại đúng cả hai mỏ neo OCR.
    add("data[fullname]", applicant_name or (requester_name if requester_matches_applicant else None))
    add("data[identityNumber]", applicant_identity or (requester_identity if requester_matches_applicant else None))
    if requester_matches_applicant:
        add("data[birthday]", values.get("NguoiNop_NgaySinh"))
        add("data[gender]", values.get("NguoiNop_GioiTinh"))
        add("data[identityDate]", values.get("NguoiNop_NgayCap"))
        add("data[idIssuePlace]", values.get("NguoiNop_NoiCap"))
        if requester_area:
            add("data[province]", requester_area.get("tinh"))
            add("data[district]", requester_area.get("xa"))
            add("data[address]", requester_area.get("diaChi"))
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))

    if owner_present:
        # Luôn phát Chủ hồ sơ tường minh, kể cả tự nộp. Một số Form.io không copy
        # ngày sinh/ngày cấp sau khi tick nên không được phụ thuộc vào mirror của cổng.
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", owner["birthday"])
        add("data[ownerGender]", owner["gender"])
        add("data[ownerIdentityNumber]", owner_identity)
        add("data[ownerIdentityDate]", owner["identityDate"])
        add("data[ownerIdIssuePlace]", owner_issuer)
        if owner_area:
            add("data[ownerProvince]", owner_area.get("tinh"))
            add("data[ownerDistrict]", owner_area.get("xa"))
            add("data[ownerAddress]", owner_area.get("diaChi"))
        add("data[ownerPhoneNumber]", _phone(owner["phone"]))
        add("data[ownerNation]", owner["nation"] or "Việt Nam")

    phone = _phone(values.get("Ndd_SoDienThoai"))

    if values.get("DeNghi_NoiDung") == "xac_dinh":
        add("data[chonNoiDungDeNghi][]", True, extra={"optionValue": "1"})
    elif values.get("DeNghi_NoiDung") == "xac_dinh_lai":
        add("data[chonNoiDungDeNghi][]", True, extra={"optionValue": "2"})

    # I. Người khuyết tật là khối nghiệp vụ riêng. Chỉ dùng Chủ hồ sơ để bù
    # field khi hai nhóm đã khớp tất định; không đổ CCCD người đại diện vào trẻ.
    nkt_name = values.get("Nkt_HoTen")
    nkt_identity = _identity(values.get("Nkt_SoDinhDanh"))
    owner_is_nkt = owner_present and _same_person(
        nkt_name,
        nkt_identity,
        owner_name,
        owner_identity,
    )
    add("data[NktHoTen]", nkt_name or (owner_name if owner_is_nkt else None))
    add(
        "data[NktNgaySinh]",
        values.get("Nkt_NgaySinh")
        or (owner["birthday"] if owner_is_nkt else None),
    )
    add(
        "data[NktSoDinhdanh]",
        nkt_identity or (owner_identity if owner_is_nkt else None),
    )
    add(
        "data[NktGioiTinh]",
        values.get("Nkt_GioiTinh")
        or (owner["gender"] if owner_is_nkt else None),
    )

    nkt_tt = _area(values.get("Nkt_ThuongTru"))
    if not nkt_tt and owner_is_nkt:
        nkt_tt = owner_area
    if nkt_tt:
        add("data[NktMaTinh]", nkt_tt.get("tinh"))
        add("data[NktMaXa]", nkt_tt.get("xa"))
        add("data[NktDiachi]", nkt_tt.get("diaChi"))

    nkt_now = _area(values.get("Nkt_NoiOHienNay")) or nkt_tt
    if nkt_now:
        add("data[NktNOHTMaTinh]", nkt_now.get("tinh"))
        add("data[NktNOHTMaXa]", nkt_now.get("xa"))
        add("data[NktNOHTDiaChi]", nkt_now.get("diaChi"))

    # II. Người đại diện hợp pháp.
    add("data[NddHoTen]", values.get("Ndd_HoTen"))
    add("data[NddSoDinhdanh]", values.get("Ndd_SoDinhDanh"))
    add("data[NddQuanheNkt]", _relation(values.get("Ndd_QuanHe")))
    add("data[NddSodienthoai]", phone)
    ndd_area = _area(values.get("Ndd_NoiCuTru"))
    if ndd_area:
        add("data[NddMaTinh]", ndd_area.get("tinh"))
        add("data[NddMaXa]", ndd_area.get("xa"))
        add("data[NddDiachi]", ndd_area.get("diaChi"))

    # III. Dạng khuyết tật: parent trước child để Form.io mở các radio con.
    categories = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_DanhMuc"))}
    details = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_ChiTiet"))}
    categories.update(code.split("_", 1)[0] for code in details if "_" in code)
    for code in sorted(categories):
        name = DISABILITY_RADIO_FIELDS.get(code)
        if name:
            add(name, "co")
    for code in sorted(details):
        name = DISABILITY_RADIO_FIELDS.get(code)
        if name:
            add(name, "co")

    muc_do = values.get("MucDo_HoatDong")
    if isinstance(muc_do, dict):
        for idx in sorted(MUC_DO_RADIO_FIELDS, key=lambda x: int(x)):
            value = str(muc_do.get(idx) or muc_do.get(int(idx)) or "").strip().upper()
            if value in _VALID_MUC_DO:
                add(MUC_DO_RADIO_FIELDS[idx], value)

    return out
