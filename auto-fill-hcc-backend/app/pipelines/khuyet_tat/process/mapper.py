"""Map compact disability-procedure facts to Form.io DOM fields."""

import re
import unicodedata

from app.pipelines._shared.area_remap import is_current_area, province_for_ward, remap_area
from app.pipelines.khuyet_tat.process.schema import (
    DISABILITY_RADIO_FIELDS,
    MUC_DO_RADIO_FIELDS,
    UI_COMP_BY_NAME,
)

_VALID_MUC_DO = {"THD", "CTG", "KTHD", "KXD"}

# Cấu hình theo tài khoản: tỉnh Khánh Hòa ghi sẵn ô "Ghi chú" (data[ghiChu]) bằng câu cố định; nơi khác để cổng/cán
# bộ tự ghi. Mapper không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi
# with_account_process_options để server tự đặt cờ; cờ luôn bị ghi đè theo tài khoản, client không tự bật được.
# Chỉ thủ tục 1.001699: "Đổi, cấp lại Giấy xác nhận khuyết tật" dùng chung mapper này nhưng không nhận cờ.
PROCEDURE_KEYS = ("xac-dinh-muc-do-khuyet-tat",)
KHANH_HOA_GHI_CHU_OPTION = "khanhHoaGhiChu"
KHANH_HOA_GHI_CHU = "Xác định mức độ khuyết tật và cấp giấy xác nhận khuyết tật"


def is_khanh_hoa(user: dict | None) -> bool:
    """True khi tài khoản thuộc tỉnh Khánh Hòa (mọi xã/phường; "Hòa"/"Hoà" đều khớp)."""
    return bool(user) and "khanh hoa" in _norm_text(user.get("tinh"))


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ ghi chú Khánh Hòa do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(KHANH_HOA_GHI_CHU_OPTION, None)
    if procedure in PROCEDURE_KEYS and is_khanh_hoa(user):
        result[KHANH_HOA_GHI_CHU_OPTION] = True
    return result


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


def _selectable(area: dict) -> bool:
    """Cặp tỉnh/xã chọn được trên cổng. Tỉnh trống thì không có gì để kiểm → coi như chọn được."""
    return is_current_area(str(area.get("tinh") or ""), str(area.get("xa") or ""))


def _ward_from_ocr(area: dict, read_ward: str, ocr_text: str) -> dict | None:
    """LLM cắt cụt tên phường/xã mới ("Phường Bắc Nha Trang" → xã "Bắc"): tìm trên giấy cụm có nhãn xã/phường bắt
    đầu bằng tên đã đọc, cụm dài nhất ra đơn vị hiện hành (cùng tỉnh nếu đã biết tỉnh) là xã thật."""
    name = " ".join(str(read_ward or "").split())
    if not name or not ocr_text:
        return None
    pattern = re.compile(
        rf"(?<!\w)(?:xã|phường|thị trấn)\s+({re.escape(name)}(?:[ \t]+[^\s,;.:()\-–]+){{0,3}})",
        re.IGNORECASE,
    )
    province = str(area.get("tinh") or "")
    for match in pattern.finditer(unicodedata.normalize("NFC", ocr_text)):
        words = match.group(1).split()
        for size in range(len(words), len(name.split()), -1):
            candidate = " ".join(words[:size])
            if province:
                found = remap_area({**area, "xa": candidate})
                if (isinstance(found, dict) and found.get("xa") and _selectable(found)
                        and _norm_text(found.get("tinh")) == _norm_text(province)):
                    return {**area, "tinh": found["tinh"], "xa": found["xa"]}
            else:
                hit = province_for_ward(candidate)
                if hit:
                    return {**area, "tinh": hit[0], "xa": hit[1]}
    return None


def _area(value, ocr_text: str = ""):
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
    remapped = remap_area(out)
    if not isinstance(remapped, dict) or _norm_text(remapped.get("quocGia")) not in ("viet nam", "vn"):
        return remapped
    # Ô tỉnh ghi thành phố/huyện cũ ("Nha Trang", "NT - KH") hay phường/xã viết tắt: remap_area() chung đã đổi.
    xa = out["xa"]
    if not remapped.get("tinh") and remapped.get("xa"):
        # Giấy chỉ ghi phường/xã → tỉnh DUY NHẤT có đơn vị tên này; lấy đủ nhãn danh mục để khớp option.
        found = province_for_ward(remapped["xa"])
        if found:
            remapped = {**remapped, "tinh": found[0], "xa": found[1]}
    if xa and (not remapped.get("tinh") or not _selectable(remapped)):
        remapped = _ward_from_ocr(remapped, xa, ocr_text) or remapped
    # Xã không có trong danh mục hiện hành: extension để trống hoặc vớ nhầm option gần giống ("Vĩnh Hải" cũ của
    # Nha Trang trúng "Xã Vĩnh Hải" của Ninh Thuận cũ). Bỏ trống xã, giữ tên đã đọc ở cuối địa chỉ chi tiết, tô vàng.
    ward = str(remapped.get("xa") or "")
    if ward and not _selectable(remapped):
        detail = str(remapped.get("diaChi") or "").strip()
        if _norm_text(ward) not in _norm_text(detail):
            detail = f"{detail}, {ward}" if detail else ward
        remapped = {**remapped, "xa": "", "diaChi": detail, "_xaChuaChon": True}
    return remapped


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


def _full_date(value) -> str | None:
    """Ô ngày sinh cổng cần đủ ngày/tháng/năm: chỉ có năm (LLM hay suy năm từ số CCCD) là ghi đè sai ngày tài
    khoản đổ sẵn → bỏ."""
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", text) else None


def _gender_from_identity(identity: str | None) -> str | None:
    """Chữ số thứ 4 của số định danh 12 số mã hóa thế kỷ + giới tính: chẵn → Nam, lẻ → Nữ (TT 59/2021/TT-BCA).

    Đơn Mẫu số 01 không có dòng giới tính người đại diện, hồ sơ thường không kèm CCCD của người này → đây là nguồn
    giới tính còn lại."""
    if not identity or len(identity) != 12 or not identity.isdigit():
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


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


def _owner_profile(values: dict, ocr_text: str = "") -> dict:
    """Hồ sơ CHỦ HỒ SƠ = người được xác định mức độ khuyết tật (mục I Mẫu số 01).

    LLM có lúc chỉ trả ``Nkt_*`` mà bỏ trống nhóm ``ChuHoSo_*`` vì thấy thông tin đã có
    ở mục I. Thiếu chủ hồ sơ thì mapper KHÔNG phát ``data[isOwnerDossierCheck]``, cổng
    giữ nguyên tích "Người nộp hồ sơ là chủ hồ sơ" và khối chủ hồ sơ bị khoá theo tài
    khoản đang đăng nhập → suy ngược từ mục I. Người đại diện (mục II) không bao giờ là
    chủ hồ sơ nên không dùng làm dự phòng.
    """
    profile = {
        "name": values.get("ChuHoSo_HoTen"),
        "identity": _identity(values.get("ChuHoSo_SoDinhDanh")),
        "birthday": values.get("ChuHoSo_NgaySinh"),
        "gender": values.get("ChuHoSo_GioiTinh"),
        "identityDate": values.get("ChuHoSo_NgayCap"),
        "issuer": values.get("ChuHoSo_NoiCap"),
        "area": _area(values.get("ChuHoSo_NoiCuTru"), ocr_text),
        "phone": values.get("ChuHoSo_DienThoai"),
        "nation": values.get("ChuHoSo_QuocTich"),
    }
    if profile["name"] or profile["identity"]:
        return profile

    nkt_identity = _identity(values.get("Nkt_SoDinhDanh"))
    if values.get("Nkt_HoTen") or nkt_identity:
        profile["name"] = values.get("Nkt_HoTen")
        profile["identity"] = nkt_identity
        profile["birthday"] = profile["birthday"] or values.get("Nkt_NgaySinh")
        profile["gender"] = profile["gender"] or values.get("Nkt_GioiTinh")
        profile["area"] = profile["area"] or _area(values.get("Nkt_ThuongTru"), ocr_text)

    return profile


def _representative_profile(values: dict, ocr_text: str = "") -> dict | None:
    """Người đại diện hợp pháp (mục II) — người nộp ở chế độ theo tờ khai."""
    name = values.get("Ndd_HoTen")
    identity = _identity(values.get("Ndd_SoDinhDanh"))
    if not name and not identity:
        return None
    return {
        "name": name,
        "identity": identity,
        "birthday": values.get("Ndd_NgaySinh"),
        "gender": values.get("Ndd_GioiTinh"),
        "identityDate": values.get("Ndd_NgayCap"),
        "issuer": values.get("Ndd_NoiCap"),
        "area": _area(values.get("Ndd_NoiCuTru"), ocr_text),
        "phone": values.get("Ndd_SoDienThoai"),
    }


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

    def add_area(province: str, ward: str, detail: str, area: dict | None) -> None:
        if not area:
            return
        add(province, area.get("tinh"))
        add(ward, area.get("xa"))
        # Phường/xã bỏ trống vì không có trong danh mục: tên đã đọc nằm cuối địa chỉ chi tiết, tô vàng để cán bộ chọn.
        add(detail, area.get("diaChi"), default=bool(area.get("_xaChuaChon")))

    ocr_text = str((options or {}).get("_ocr_text") or "")
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
        _area(values.get("NguoiNop_NoiCuTru"), ocr_text)
        if requester_matches_applicant
        else None
    )

    owner = _owner_profile(values, ocr_text)
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

    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    if theo_to_khai:
        # THEO TỜ KHAI: bỏ mỏ neo tài khoản. Người nộp = người đại diện hợp pháp (mục II);
        # mục II trống tức người khuyết tật tự đứng đơn → người nộp là chủ hồ sơ.
        submitter = _representative_profile(values, ocr_text)
        self_submit = submitter is None
        if self_submit:
            submitter = owner if owner_present else None
        # Checkbox trước hai khối (cổng copy/reset Chủ hồ sơ khi đổi checkbox).
        if submitter is not None:
            # Họ tên + CCCD Phần I cổng khoá (disabled) theo tài khoản VNeID; người nộp theo tờ khai là người
            # khác nên kèm enableInput để extension bỏ disabled trước khi ghi, cán bộ còn sửa được khi OCR sai.
            unlock = {"enableInput": True}
            add("data[isOwnerDossierCheck]", self_submit)
            add("data[fullname]", submitter["name"], extra=unlock)
            if _full_date(submitter["birthday"]):
                add("data[birthday]", _full_date(submitter["birthday"]))
            else:
                # Cổng đổ sẵn ngày sinh tài khoản VNeID, không phải của người nộp theo tờ khai → xoá + tô đỏ.
                out.append({"name": "data[birthday]", "comp": UI_COMP_BY_NAME["data[birthday]"], "value": "",
                            "clear": True, "markEmpty": True, **unlock})
                seen.add("data[birthday]")
            add("data[gender]", submitter["gender"] or _gender_from_identity(submitter["identity"]))
            add("data[identityNumber]", submitter["identity"], extra=unlock)
            add("data[identityDate]", submitter["identityDate"])
            add("data[idIssuePlace]", submitter["issuer"])
            add_area("data[province]", "data[district]", "data[address]", submitter["area"])
            add("data[phoneNumber]", _phone(submitter["phone"]))
    else:
        # Checkbox phải phát trước hai khối. Cổng có side effect copy/reset Chủ hồ sơ
        # khi đổi checkbox, nên mọi field phụ thuộc luôn được gửi sau action này.
        if owner_present:
            add("data[isOwnerDossierCheck]", bool(owner_matches_applicant))

        # Tên + CCCD UI là mỏ neo có thẩm quyền. Các field nhân thân còn lại chỉ
        # được nhận từ NguoiNop_* sau khi LLM trả lại đúng cả hai mỏ neo OCR.
        add("data[fullname]", applicant_name or (requester_name if requester_matches_applicant else None))
        add("data[identityNumber]", applicant_identity or (requester_identity if requester_matches_applicant else None))
    if requester_matches_applicant and not theo_to_khai:
        add("data[birthday]", _full_date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", values.get("NguoiNop_GioiTinh"))
        add("data[identityDate]", values.get("NguoiNop_NgayCap"))
        add("data[idIssuePlace]", values.get("NguoiNop_NoiCap"))
        add_area("data[province]", "data[district]", "data[address]", requester_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    if not theo_to_khai:
        # Giấy tờ không ghi giới tính người nộp → suy từ số định danh tài khoản (mỏ neo UI có thẩm quyền).
        add("data[gender]", _gender_from_identity(applicant_identity))

    if owner_present:
        # Luôn phát Chủ hồ sơ tường minh, kể cả tự nộp. Một số Form.io không copy
        # ngày sinh/ngày cấp sau khi tick nên không được phụ thuộc vào mirror của cổng.
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", owner["birthday"])
        add("data[ownerGender]", owner["gender"])
        add("data[ownerIdentityNumber]", owner_identity)
        add("data[ownerIdentityDate]", owner["identityDate"])
        add("data[ownerIdIssuePlace]", owner_issuer)
        add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", owner_area)
        add("data[ownerPhoneNumber]", _phone(owner["phone"]))
        add("data[ownerNation]", owner["nation"] or "Việt Nam")

    # Phát sau checkbox chủ hồ sơ: đổi checkbox thì cổng copy/reset khối chủ hồ sơ.
    if (options or {}).get(KHANH_HOA_GHI_CHU_OPTION) is True:
        add("data[ghiChu]", KHANH_HOA_GHI_CHU)

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

    nkt_tt = _area(values.get("Nkt_ThuongTru"), ocr_text)
    if not nkt_tt and owner_is_nkt:
        nkt_tt = owner_area
    add_area("data[NktMaTinh]", "data[NktMaXa]", "data[NktDiachi]", nkt_tt)

    nkt_now = _area(values.get("Nkt_NoiOHienNay"), ocr_text) or nkt_tt
    add_area("data[NktNOHTMaTinh]", "data[NktNOHTMaXa]", "data[NktNOHTDiaChi]", nkt_now)

    # II. Người đại diện hợp pháp. Cùng số định danh với tài khoản VNeID đang nộp → họ tên theo tài khoản (chữ viết
    # tay mục II hay mất dấu khi OCR).
    ndd_is_applicant = bool(applicant_identity) and _identity(values.get("Ndd_SoDinhDanh")) == applicant_identity
    add("data[NddHoTen]", (applicant_name if ndd_is_applicant else None) or values.get("Ndd_HoTen"))
    add("data[NddSoDinhdanh]", values.get("Ndd_SoDinhDanh"))
    add("data[NddQuanheNkt]", _relation(values.get("Ndd_QuanHe")))
    add("data[NddSodienthoai]", phone)
    add_area("data[NddMaTinh]", "data[NddMaXa]", "data[NddDiachi]", _area(values.get("Ndd_NoiCuTru"), ocr_text))

    # III. Dạng khuyết tật: parent trước child để Form.io mở các radio con.
    categories = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_DanhMuc"))}
    details = {_compact_code(v) for v in _as_list(values.get("KhuyetTat_ChiTiet"))}
    categories.update(code.split("_", 1)[0] for code in details if "_" in code)
    # Đơn có ít nhất một dòng "Có" thì mọi radio đang hiện phải có giá trị: nhóm không "Có" → "Không" ở dòng
    # nhóm (radio con ẩn, không tích); nhóm "Có" → dòng con không "Có" (trống hoặc "Không") tích "Không".
    # Không dòng nào "Có" (Mục III bỏ trống) → không tích gì.
    if categories:
        for code, name in sorted(DISABILITY_RADIO_FIELDS.items()):
            if "_" not in code:
                add(name, "co" if code in categories else "khong")
        for code, name in sorted(DISABILITY_RADIO_FIELDS.items()):
            if "_" in code and code.split("_", 1)[0] in categories:
                add(name, "co" if code in details else "khong")

    muc_do = values.get("MucDo_HoatDong")
    if isinstance(muc_do, dict):
        for idx in sorted(MUC_DO_RADIO_FIELDS, key=lambda x: int(x)):
            value = str(muc_do.get(idx) or muc_do.get(int(idx)) or "").strip().upper()
            if value in _VALID_MUC_DO:
                add(MUC_DO_RADIO_FIELDS[idx], value)

    return out
