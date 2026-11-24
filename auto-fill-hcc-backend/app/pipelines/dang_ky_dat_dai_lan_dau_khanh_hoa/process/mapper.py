"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đăng ký đất đai, cấp GCN lần đầu, 1.013978).

Ba khối tách riêng (xem schema.py):
- Phần I  người nộp   -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                          province/village/address + data[noidungyeucaugiaiquyet].
- Phần II chủ hồ sơ   -> data[chonDoiTuong]/ownerFullname/ownerPhoneNumber/ownerBirthday/ownerEmail/
                          ownerIdentityNumber/ownerIdentityDate/ownerIdentityAgency/province1/village1/ownerAddress.
- Phần III thửa đất   -> data[diaChiThuaDat]/SoThuaDat/SoToBanDo/province2/village2/nation2.
Không có văn bản ủy quyền (tên người nộp trùng chủ hồ sơ) thì hai vai là MỘT người: thuộc tính thiếu ở vai này
được lấy từ vai kia. Có ủy quyền thì mỗi khối chỉ dùng facts của đúng vai, không mượn chéo.
⚑ Cờ theo tài khoản `ownerAsApplicant` (phường Nam Nha Trang, xem with_account_process_options): Phần I khai luôn
chủ hồ sơ (người ủy quyền / người đứng Đơn), kể cả khi hồ sơ có văn bản ủy quyền.
⚑ Cài đặt "Lấy người nộp theo tờ khai" (`options.submitterMode="owner_as_submitter"`, xem submitter_is_declarant): như
cờ Nam Nha Trang nhưng cho mọi tài khoản và cả 7 thủ tục Khánh Hòa; chủ hồ sơ là tổ chức thì giữ mặc định.
Ô chữ/ngày giấy tờ không có dữ liệu thì trả về TRỐNG (clear_blank_fields), không bỏ qua — dùng chung cho cả 5 thủ tục
Khánh Hòa cùng template.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, canonical_ward, province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME

_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


# Cấu hình theo tài khoản (người dùng chốt 20/11/2026): phường Nam Nha Trang khai PHẦN I NGƯỜI NỘP bằng chính chủ hồ
# sơ — người ủy quyền / người đứng Đơn đăng ký đất đai — không lấy bên được ủy quyền như mặc định. Mapper không biết
# tài khoản nên router (Auto Fill) và pipeline_runner (trợ lý) gọi with_account_process_options để server tự đặt cờ;
# cờ luôn bị ghi đè theo tài khoản, client không tự bật được cho phường khác. Chỉ thủ tục này (các thủ tục Khánh Hòa
# dùng chung hàm của mapper này không nhận cờ).
PROCEDURE_KEY = "dang-ky-dat-dai-lan-dau-khanh-hoa"
OWNER_AS_APPLICANT_OPTION = "ownerAsApplicant"
_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")
# (tỉnh, phường) đã bỏ dấu + bỏ tiền tố, khớp ĐÚNG tên phường (Nam Nha Trang không kéo theo phường Nha Trang).
_OWNER_AS_APPLICANT_WARDS = (
    ("khanh hoa", "nam nha trang"),  # 2026-11-20
)


def is_owner_as_applicant_account(user: dict | None) -> bool:
    if not user:
        return False
    tinh = _fold(user.get("tinh"))
    xa = _fold(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return any(tinh_key in tinh and xa == xa_key for tinh_key, xa_key in _OWNER_AS_APPLICANT_WARDS)


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ ownerAsApplicant do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(OWNER_AS_APPLICANT_OPTION, None)
    if procedure == PROCEDURE_KEY and is_owner_as_applicant_account(user):
        result[OWNER_AS_APPLICANT_OPTION] = True
    return result


def owner_as_applicant(options: dict | None) -> bool:
    return (options or {}).get(OWNER_AS_APPLICANT_OPTION) is True


# Cài đặt "Lấy người nộp theo tờ khai" (Auto Fill: settings.html của extension; trợ lý: cài đặt tài khoản
# submitterFromDeclaration) → options.submitterMode. Bảy thủ tục Khánh Hòa vốn không so khớp tài khoản (Phần I luôn theo
# hồ sơ, mặc định là bên được ủy quyền), nên bật cài đặt nghĩa là Phần I khai NGƯỜI ĐỨNG ĐƠN — như cờ Nam Nha Trang — bỏ
# bên được ủy quyền (theo yêu cầu người dùng 23/11/2026). Tổ chức không đứng Phần I được (form đòi ngày sinh, CCCD) →
# giữ mặc định.
SUBMITTER_MODE_OPTION = "submitterMode"
SUBMITTER_FROM_DECLARATION = "owner_as_submitter"


def submitter_from_declaration(options: dict | None) -> bool:
    return str((options or {}).get(SUBMITTER_MODE_OPTION) or "") == SUBMITTER_FROM_DECLARATION


def submitter_is_declarant(options: dict | None, declarant_name: Any, declarant_kind: Any = None) -> bool:
    """Bật "Lấy người nộp theo tờ khai" và người đứng Đơn là CÁ NHÂN có tên → Phần I khai chính người đó."""
    return (submitter_from_declaration(options) and bool(_text(declarant_name))
            and not _is_to_chuc(declarant_kind, declarant_name))


# Đơn Mẫu 19 mục 1 ghi chung nhiều người cùng sử dụng đất trên một dòng ("A SN: … – B SN: …", "b) <số A> - <số B>").
# LLM có lượt chép nguyên dòng: gom hết chữ số thì ra một số 24 ký tự, nối hai tên thì lẹo hai người vào một khối.
_MULTI_SEP = r"\s*[-–—,;/]\s*|\s+và\s+"


def _first_number(value: Any) -> str:
    """Chuỗi kê nhiều số ("<số A> - <số B>") -> cụm của người đầu; một số viết tách nhóm ("056 175 012 345",
    "056.175.012.345", "056-175-012-345") giữ nguyên để gom chữ số như cũ."""
    text = _text(value) or ""
    groups = [part for part in re.split(_MULTI_SEP, text) if len(re.sub(r"\D+", "", part)) >= 9]
    return groups[0] if len(groups) > 1 else text


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _first_number(value))
    # Hai CCCD 12 số đã bị nối liền (không còn dấu ngăn) -> số của người đầu.
    if len(digits) == 24:
        digits = digits[:12]
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _first_number((_text(value) or "").upper().replace("O", "0").replace("S", "5")))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    # Chỉ có NĂM sinh (hợp đồng cũ ghi "Sinh năm 19xx") -> bỏ trống, ô flatpickr nhận năm trơn sẽ ra ngày sai.
    return normalize_date(f"{match.group(1)}/{match.group(2)}/{match.group(3)}") if match else None


def _parcel_number(value: Any) -> str | None:
    """Số thửa/số tờ: bỏ chữ dẫn ("nay là tờ bản đồ số 99" -> "99") và mã mảnh trong ngoặc ("12 (123456-7-a)" -> "12")."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(
        r"(?i)^.*?\b(thửa\s*đất\s*số|thửa\s*số|số\s*thửa|tờ\s*bản\s*đồ\s*số|tờ\s*số|số\s*tờ)\s*:?\s*", "", text
    )
    match = re.match(r"[^\s(,;]+", text)
    if not match:
        return None
    return match.group(0).strip(" .:-") or None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or value.get("chiTiet") or "",
    }
    if not any((area["tinh"], area["xa"], area["diaChi"])):
        return None
    return remap_area(area, allow_diachi_fallback=True)


def _province(area: dict) -> str | None:
    tinh = _text(area.get("tinh"))
    if not tinh:
        return None
    return province_label(canonical_province(tinh) or tinh)


def _ward(area: dict) -> str | None:
    xa = _text(area.get("xa"))
    if not xa:
        return None
    return canonical_ward(area.get("tinh"), xa) or xa


# Mọi ô CHỮ / NGÀY của ba khối (dùng chung cho 5 thủ tục Khánh Hòa cùng template). Giấy tờ không có dữ liệu thì TRẢ VỀ
# TRỐNG (clear) chứ không bỏ qua: Phần I cổng đổ sẵn theo tài khoản đăng nhập (ngày sinh, CCCD… của người khác khi nộp
# thay), để nguyên là ghép thông tin hai người vào một khối. Ô chọn Tỉnh/Phường-xã không xoá: cổng chỉ để sẵn Tỉnh Khánh
# Hòa (mặc định của cổng, không theo tài khoản), Phường/xã để trống; engine trợ lý cũng chưa bỏ chọn được ô Choices.
BLANK_PART_ONE = ("data[fullname]", "data[phoneNumber]", "data[birthday]", "data[email]", "data[identityNumber]",
                  "data[identityDate]", "data[identityAgency_text]", "data[address]")
BLANK_PART_TWO = ("data[ownerFullname]", "data[ownerPhoneNumber]", "data[ownerBirthday]", "data[ownerEmail]",
                  "data[ownerIdentityNumber]", "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[ownerAddress]")
BLANK_PART_THREE = ("data[diaChiThuaDat]", "data[SoThuaDat]", "data[SoToBanDo]")
# Ô có dấu bắt buộc trên form: trả trống thì tô đỏ (markEmpty) để cán bộ nhập.
REQUIRED_BLANK = ("data[fullname]", "data[phoneNumber]", "data[birthday]", "data[identityNumber]", "data[ownerFullname]",
                  "data[ownerPhoneNumber]", "data[ownerBirthday]", "data[ownerIdentityNumber]")


def account_is_applicant(options: dict | None, identity: Any) -> bool:
    """Tài khoản đăng nhập CHÍNH LÀ người nộp (extension gửi formContext, số định danh trùng) → Phần I cổng đổ sẵn đúng
    người, ô giấy tờ thiếu giữ giá trị cổng thay vì xoá."""
    context = (options or {}).get("formContext") or {}
    account = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    return bool(account and identity and account == _identity(identity))


def clear_blank_fields(out: list[dict], seen: set[str], options: dict | None, applicant_identity: Any) -> bool:
    """Trả mọi ô chữ/ngày còn thiếu của ba khối về TRỐNG (clear; ô bắt buộc tô đỏ). Trả True khi giữ Phần I của cổng
    (tài khoản là người nộp)."""
    keep_part_one = account_is_applicant(options, applicant_identity)
    for name in BLANK_PART_ONE + BLANK_PART_TWO + BLANK_PART_THREE:
        if name in seen or (keep_part_one and name in BLANK_PART_ONE):
            continue
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True}
        if name in REQUIRED_BLANK:
            item["markEmpty"] = True
        out.append(item)
        seen.add(name)
    return keep_part_one


# Ô "Nội dung yêu cầu giải quyết" ghi theo cách cán bộ Khánh Hòa nhập (người dùng chốt 18/11/2026):
# "<tên thủ tục> tại TĐ <số thửa> TBĐ <số tờ> địa chỉ <địa chỉ thửa> - <HỌ TÊN CHỦ HỒ SƠ IN HOA>".
# Mapper tự ghép từ các ô đã đọc, không để LLM viết; chỉ ghi MỘT người (chủ hồ sơ), Đơn có nhiều người cùng sử dụng đất
# cũng chỉ lấy người đầu.
NOI_DUNG_THU_TUC = (
    "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền "
    "với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài"
)


def _first_person(name: str | None) -> str | None:
    """"Phạm Văn A – Nguyễn Thị B" / "A, B" / "A và B" -> "Phạm Văn A"."""
    if not name:
        return None
    first = re.split(r"\s+[-–—]\s+|\s*[,;]\s*|\s+và\s+", name, maxsplit=1)[0]
    # "Phạm Văn A SN: 11/3/1988" / "… sinh năm 1988": bỏ phần ngày sinh viết liền sau tên.
    first = re.split(r"(?i)\s*\b(?:SN|sinh\s+năm|sinh\s+ngày|năm\s+sinh)\b\s*:?.*$", first, maxsplit=1)[0]
    return _text(first)


def _noi_dung_yeu_cau(so_thua: str | None, so_to: str | None, dia_chi: str | None, owner: str | None) -> str:
    parts = [NOI_DUNG_THU_TUC]
    vi_tri = " ".join(part for part in (f"TĐ {so_thua}" if so_thua else "", f"TBĐ {so_to}" if so_to else "") if part)
    if vi_tri:
        parts.append(f"tại {vi_tri}")
    if dia_chi:
        parts.append(f"địa chỉ {dia_chi}")
    text = " ".join(parts)
    person = _first_person(owner)
    return f"{text} - {person.upper()}" if person else text


def _is_to_chuc(loai: Any, name: Any) -> bool:
    folded = _fold(loai)
    if "to chuc" in folded:
        return True
    if "ca nhan" in folded:
        return False
    return any(marker in _fold(name) for marker in _ORG_MARKERS)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_person_area(province_name: str, ward_name: str, address_name: str, area: dict | None) -> None:
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán (từ thửa đất, nơi cấp...)
        # chứ không phải nơi thường trú thật -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province_name, _province(area))
        add(ward_name, _ward(area))
        add(address_name, _text(area.get("diaChi")))

    # Đơn đứng chung nhiều người: mỗi khối chỉ MỘT người (người đầu), không nối tên người cùng sử dụng đất. Tên tổ
    # chức ("Công ty … - Chi nhánh …") giữ nguyên.
    owner_raw = _text(values.get("ChuHoSo_HoTen"))
    owner_is_org = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_raw)
    owner_name = owner_raw if owner_is_org else _first_person(owner_raw)
    applicant_raw = _text(values.get("NguoiNop_HoTen"))
    applicant_name = (applicant_raw if _is_to_chuc(None, applicant_raw) else _first_person(applicant_raw)) or owner_name
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    def owner_val(key: str) -> Any:
        value = values.get(f"ChuHoSo_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"NguoiNop_{key}")
        return value

    def applicant_val(key: str) -> Any:
        value = values.get(f"NguoiNop_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"ChuHoSo_{key}")
        return value

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người sử dụng đất đứng Đơn đăng ký đất đai).")

    # Phường Nam Nha Trang (cờ ownerAsApplicant) hoặc bật "Lấy người nộp theo tờ khai" (options.submitterMode, chủ hồ sơ
    # cá nhân): Phần I chép đúng chủ hồ sơ như Phần II, bỏ bên được ủy quyền. Thiếu tên chủ hồ sơ thì giữ cách mặc định.
    owner_applicant = bool(owner_name) and (
        owner_as_applicant(options) or submitter_is_declarant(options, owner_name, values.get("ChuHoSo_LoaiChuThe")))
    person_val = owner_val if owner_applicant else applicant_val

    # --- Phần I: người nộp ---
    add("data[fullname]", owner_name if owner_applicant else applicant_name)
    add("data[phoneNumber]", _phone(person_val("DienThoai")))
    add("data[birthday]", _date(person_val("NgaySinh")))
    add("data[email]", _text(person_val("Email")))
    add("data[identityNumber]", _identity(person_val("SoDinhDanh")))
    add("data[identityDate]", _date(person_val("NgayCap")))
    applicant_issuer = _text(person_val("NoiCap"))
    add("data[identityAgency_text]", normalize_issuer(applicant_issuer) if applicant_issuer else None)
    # Tự nộp: địa chỉ CHỦ HỒ SƠ (đọc từ Đơn) đứng trước — NguoiNop_DiaChi hay bị LLM lấy từ CCCD/giấy tờ cũ.
    if owner_applicant:
        applicant_area = _area(owner_val("DiaChi"))
    elif authorized:
        applicant_area = _area(applicant_val("DiaChi"))
    else:
        applicant_area = _area(values.get("ChuHoSo_DiaChi")) or _area(values.get("NguoiNop_DiaChi"))
    add_person_area("data[province]", "data[village]", "data[address]", applicant_area)

    # --- Phần II: chủ hồ sơ ---
    if owner_is_org:
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[ownerFullname]", owner_name)
    add("data[ownerPhoneNumber]", _phone(owner_val("DienThoai")))
    add("data[ownerBirthday]", _date(owner_val("NgaySinh")))
    add("data[ownerEmail]", _text(owner_val("Email")))
    add("data[ownerIdentityNumber]", _identity(owner_val("SoDinhDanh")))
    add("data[ownerIdentityDate]", _date(owner_val("NgayCap")))
    owner_issuer = _text(owner_val("NoiCap"))
    add("data[ownerIdentityAgency]", normalize_issuer(owner_issuer) if owner_issuer else None)
    add_person_area("data[province1]", "data[village1]", "data[ownerAddress]", _area(owner_val("DiaChi")))

    # --- Phần III: thửa đất — chỉ từ nguồn thửa đất riêng, KHÔNG bao giờ lấy nơi cư trú thay thế ---
    so_thua = _parcel_number(values.get("ThuaDat_SoThua"))
    so_to = _parcel_number(values.get("ThuaDat_SoTo"))
    add("data[SoThuaDat]", so_thua)
    add("data[SoToBanDo]", so_to)
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    detail = None
    if parcel_area:
        parcel_ward = _ward(parcel_area)
        # Ô "Địa chỉ thửa đất/ địa chỉ xây dựng" là textarea: ghi chi tiết + phường/xã như dòng địa chỉ trên Đơn.
        detail = ", ".join(part for part in (_text(parcel_area.get("diaChi")), parcel_ward) if part) or None
        add("data[diaChiThuaDat]", detail)
        add("data[province2]", _province(parcel_area))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)
        add("data[village2]", parcel_ward)

    # Ô Nội dung yêu cầu (Phần I) ghép sau khi đã có thửa đất; thứ tự trong `out` không ảnh hưởng điền.
    add("data[noidungyeucaugiaiquyet]", _noi_dung_yeu_cau(so_thua, so_to, detail, owner_name))

    clear_blank_fields(out, seen, options, person_val("SoDinhDanh"))
    return out, warnings
