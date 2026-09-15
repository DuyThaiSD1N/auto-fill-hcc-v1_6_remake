"""Map compact source facts → Form.io data[...] cho [Lâm Đồng] đăng ký, cấp GCN với thửa đất có
DIỆN TÍCH TĂNG THÊM do thay đổi ranh giới / toàn bộ diện tích đang sử dụng (1.116356).

Form GIỐNG HỆT thủ tục 1.116365 (đã đối chiếu 35 ô data[...]: cùng tag, cùng nhãn, cùng cờ bắt
buộc) nên mapper là bản sao có chủ đích; khác biệt của thủ tục nằm ở NGUỒN dữ liệu (Đơn Mẫu 18 thay
vì đơn Mẫu 02/03/4a/4b) và ở bảng đính kèm 6 dòng.

Điền 4 khối: Người nộp (Phần I) · Thửa đất (Phần II) · Chủ hồ sơ (Phần III) · Chi tiết GCN (Phần IV).
Không cần `occurrence` — mọi tên field trên form là DUY NHẤT (province/province1/province2,
district/district1/village2 khác nhau).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME

# Ô người mà extension CHỊU TRÁCH NHIỆM điền từ CCCD/đơn. Không có dữ liệu → phát "dom-expect" để FE
# TÔ ĐỎ (không điền), dù form không đánh dấu ô đó bắt buộc.
_EXPECT_APPLICANT = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)
_EXPECT_OWNER = (
    "data[ownerFullname]", "data[ownerBirthday]", "data[gender1]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[ownerPhoneNumber]",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return _full_address(value)
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _field(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        raw = value.get(key)
        if raw not in (None, "", {}, []):
            return _text(raw)
    return None


def _full_address(value: Any) -> str | None:
    if isinstance(value, str):
        return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "soNha", "thonXom"),
        _field(value, "xa", "phuongXa", "phuong"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


def _parse_area_text(value: str) -> dict | None:
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
    """Object địa chỉ + chuẩn hóa địa giới CŨ → MỚI (CCCD in trước sáp nhập hay ghi tên cũ; select
    trên cổng chỉ có tên hiện hành nên giữ tên cũ là chọn trượt)."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        out = None
    return remap_area(out) if out else None


# province_label() của _shared chỉ bỏ được tiền tố khi SAU nó có khoảng trắng ("TP. Hồ Chí Minh").
# GCN/CCCD hay in dính "TP.Hồ Chí Minh" → không bỏ được, ra nhãn sai "Tỉnh TP.Hồ Chí Minh" và select
# Choices.js trượt option. Gỡ tiền tố tại đây trước khi gắn lại đúng loại đơn vị.
_PROVINCE_PREFIX_RE = re.compile(r"^(?:tỉnh|thành phố|tp)\s*\.?\s*", re.IGNORECASE)


def _province(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _PROVINCE_PREFIX_RE.sub("", text).strip()
    return province_label(bare or text)


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
    if not m:
        return None
    return normalize_date(m.group(0))


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _normalize_serial(prefix: str, number: str) -> str | None:
    prefix = re.sub(r"[^A-Z]", "", (prefix or "").upper())
    number = re.sub(r"\D", "", number or "")
    if not prefix or not number:
        return None
    if prefix.startswith("SO") and len(prefix) > 2:
        prefix = prefix[2:]
    elif prefix.startswith("S") and len(prefix) > 1:
        prefix = prefix[1:]
    if not 1 <= len(prefix) <= 3 or not 5 <= len(number) <= 8:
        return None
    return f"{prefix} {number}"


def _serial(value: Any) -> str | None:
    """Số phát hành GCN: '2 chữ cái + số'. Bỏ đuôi 'số vào sổ' nếu OCR dính vào."""
    text = _text(value)
    if not text:
        return None
    text = re.split(r"\(|số\s+vào\s+sổ|so\s+vao\s+so", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = " ".join(text.split()).strip(" :;,-")
    match = re.search(r"\b([A-Z]{1,5})\s*[-.]?\s*(\d{5,8})\b", text.upper())
    if match:
        serial = _normalize_serial(match.group(1), match.group(2))
        if serial:
            return serial
    return text or None


# Chức danh trong khối chữ ký của GCN. Khối này có HAI dạng: chức danh đứng TRƯỚC tên cơ quan
# ("KT. GIÁM ĐỐC Chi nhánh VPĐK…") hoặc đứng SAU ("CHI NHÁNH VPĐK… (KT. GIÁM ĐỐC – PHÓ GIÁM ĐỐC …)").
# Cắt một chiều là mất luôn tên cơ quan ở dạng còn lại → xử lý cả hai chiều.
_TITLE_LEAD_RE = re.compile(r"^(?:TM|KT|THỪA\s*LỆNH)\.?|^(?:PHÓ\s*)?(?:CHỦ\s*TỊCH|GIÁM\s*ĐỐC)", re.IGNORECASE)
_TITLE_CUT_RE = re.compile(r"[(\[]?\s*(?:TM\.|KT\.|(?:PHÓ\s*)?(?:CHỦ\s*TỊCH|GIÁM\s*ĐỐC))", re.IGNORECASE)
_STRIP_CHARS = " (:;,-/."


def _agency(value: Any) -> str | None:
    """Đơn vị cấp GCN: bỏ chức danh ký thay ('TM.'/'KT.'/'CHỦ TỊCH'/'GIÁM ĐỐC'), ỦY BAN NHÂN DÂN → UBND."""
    text = _text(value)
    if not text:
        return None
    previous = None
    while previous != text:
        previous = text
        text = _TITLE_LEAD_RE.sub("", text, count=1).strip(_STRIP_CHARS)
    # Chức danh đứng SAU tên cơ quan → cắt đuôi, nhưng chỉ nhận nếu còn tên cơ quan ở phía trước.
    head = _TITLE_CUT_RE.split(text, maxsplit=1)[0].strip(_STRIP_CHARS)
    text = head or text
    text = re.sub(r"ỦY\s*BAN\s*NHÂN\s*DÂN", "UBND", text, flags=re.IGNORECASE)
    return text or None


def _cccd_issuer(value: Any, ngay_cap: Any) -> str | None:
    text = _text(value)
    if text:
        return normalize_issuer(text)
    d = _date(ngay_cap)
    return default_issuer(d) if d else None


def _date_ymd(value: Any) -> str | None:
    """Định dạng yyyy/mm/dd — RIÊNG các ô ngày Phần IV (Ngày cấp/hiệu lực/hết hạn của GCN) dùng
    flatpickr format yyyy/mm/dd, KHÁC các ô người (dd/MM/yyyy). FE type thẳng chuỗi vào flatpickr
    nên phải gửi đúng thứ tự, không thì bị parse lệch."""
    d = _date(value)
    if not d:
        return None
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}/{mm}/{dd}"


def _expiration(value: Any) -> str | None:
    """Thời hạn 'Lâu dài' → không có ngày hết hạn (trống). Ngược lại parse ngày về yyyy/mm/dd."""
    text = _text(value)
    if not text or "lau dai" in _fold(text):
        return None
    return _date_ymd(text)


def _ghi_chu(values: dict, owner_name: str | None, has_uy_quyen: bool) -> str | None:
    """Ô "Ghi Chú:" — form KHÔNG có ô riêng cho "Nội dung biến động" của Đơn Mẫu 18 nên nội dung đó
    được ghi vào đây, kèm định vị thửa đất + diện tích tăng thêm; có ủy quyền thì ghi rõ đang nộp
    thay. Mọi vế đều suy TẤT ĐỊNH từ fact đã đọc được, không thêm chi tiết nào không có trong hồ sơ."""
    parts: list[str] = []
    noi_dung = _text(values.get("Don_NoiDungDeNghi"))
    if noi_dung:
        parts.append(noi_dung)
    # Diện tích tăng thêm chỉ ghi khi giấy tờ ghi SẴN con số (schema cấm tự trừ hai số để suy ra).
    tang_them = _text(values.get("DienTich_TangThem"))
    if tang_them and (not noi_dung or _fold(tang_them) not in _fold(noi_dung)):
        parts.append(f"Diện tích tăng thêm: {tang_them}.")
    thua = _text(values.get("ThuaDat_So"))
    to_ban_do = _text(values.get("ThuaDat_ToBanDo"))
    if thua and to_ban_do:
        locator = f"Thửa đất số {thua}, tờ bản đồ số {to_ban_do}."
    elif thua:
        locator = f"Thửa đất số {thua}."
    else:
        locator = ""
    # Đơn đã ghi sẵn thửa/tờ bản đồ trong nội dung → không lặp lại.
    if locator and not (noi_dung and thua and f"thua {_fold(thua)}" in _fold(noi_dung)):
        parts.append(locator)
    if has_uy_quyen and owner_name:
        parts.append(f"Nộp thay chủ hồ sơ {owner_name} theo giấy ủy quyền.")
    return " ".join(parts) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
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

    def expect(names: tuple[str, ...]) -> None:
        # Ô extension chịu trách nhiệm nhưng thiếu dữ liệu → FE tô đỏ (không điền).
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    # HAI NGƯỜI khi có ủy quyền:
    #  - Chủ hồ sơ (Phần III) = người sử dụng đất đứng tên GCN/Đơn (Nguoi_*).
    #  - Người nộp (Phần I) = người ĐƯỢC ủy quyền. ƯU TIÊN object NguoiDuocUyQuyen (LLM trích gộp 1 lần,
    #    đặt ĐẦU schema nên điền chắc hơn 10 field DaiDien_* rời); fallback DaiDien_* nếu LLM điền kiểu cũ.
    _rep = values.get("NguoiDuocUyQuyen")
    _rep = _rep if isinstance(_rep, dict) else {}

    def _dd(obj_key: str, flat_key: str):
        v = _rep.get(obj_key)
        return v if v not in (None, "", {}, []) else values.get(flat_key)

    daidien_hoten = _dd("hoTen", "DaiDien_HoTen")
    daidien_identity = _dd("soDinhDanh", "DaiDien_SoDinhDanh")
    has_uy_quyen = bool(_text(daidien_hoten) or _identity(daidien_identity))

    owner_name = _text(values.get("Nguoi_HoTen"))
    owner_identity = _identity(values.get("Nguoi_SoDinhDanh"))
    owner_birthday = _date(values.get("Nguoi_NgaySinh"))
    owner_gender = _text(values.get("Nguoi_GioiTinh"))
    owner_phone = _phone(values.get("Nguoi_DienThoai"))
    owner_email = _text(values.get("Nguoi_Email"))
    owner_id_date = _date(values.get("Nguoi_NgayCapCccd"))
    owner_id_agency = _cccd_issuer(values.get("Nguoi_NoiCapCccd"), values.get("Nguoi_NgayCapCccd"))
    owner_residence = _area(values.get("Nguoi_ThuongTru"))

    if has_uy_quyen:
        # Đại diện và chủ hồ sơ là HAI người KHÁC nhau → KHÔNG fallback SĐT/email/nơi ở sang chủ hồ sơ
        # (số điện thoại ghi trong Đơn là của người đề nghị, không phải của người đi nộp thay).
        sub_name = _text(daidien_hoten)
        sub_identity = _identity(daidien_identity)
        sub_birthday = _date(_dd("ngaySinh", "DaiDien_NgaySinh"))
        sub_gender = _text(_dd("gioiTinh", "DaiDien_GioiTinh"))
        sub_phone = _phone(values.get("DaiDien_DienThoai"))
        sub_email = _text(values.get("DaiDien_Email"))
        sub_id_date = _date(_dd("ngayCapCccd", "DaiDien_NgayCapCccd"))
        sub_id_agency = _cccd_issuer(_dd("noiCapCccd", "DaiDien_NoiCapCccd"), _dd("ngayCapCccd", "DaiDien_NgayCapCccd"))
        sub_residence = _area(_dd("thuongTru", "DaiDien_ThuongTru"))
    else:
        sub_name, sub_identity, sub_birthday, sub_gender = owner_name, owner_identity, owner_birthday, owner_gender
        sub_phone, sub_email, sub_id_date, sub_id_agency = owner_phone, owner_email, owner_id_date, owner_id_agency
        sub_residence = owner_residence

    # ---- Phần I: Thông tin người nộp ----
    add("data[fullname]", sub_name)
    add("data[birthday]", sub_birthday)
    add("data[gender]", sub_gender)
    add("data[phoneNumber]", sub_phone)
    add("data[email]", sub_email)
    # "Cơ quan/ tổ chức" CHỈ dành cho hồ sơ PHÁP NHÂN; hồ sơ cá nhân/hộ gia đình để TRỐNG — không lấy
    # họ tên người dân làm tên tổ chức (sai bản chất pháp lý của hồ sơ).
    add("data[organization]", _text(values.get("ToChuc_Ten")))
    add("data[identityNumber]", sub_identity)
    add("data[identityDate]", sub_id_date)
    add("data[identityAgency]", sub_id_agency)
    add("data[nation]", "Việt Nam" if sub_name or sub_identity else None)
    if sub_residence:
        add("data[province]", _province(sub_residence.get("tinh")))
        # Giữ nguyên nhãn phường/xã (đã remap về tên hiện hành); FE khớp option theo text đã fold.
        add("data[district]", _text(sub_residence.get("xa")))
        add("data[address]", _text(sub_residence.get("diaChi")))
    expect(_EXPECT_APPLICANT)

    add("data[ghiChu]", _ghi_chu(values, owner_name, has_uy_quyen))

    # ---- Phần II: Thông tin thửa đất ----
    land = _area(values.get("ThuaDat_DiaChi"))
    if land:
        add("data[province2]", _province(land.get("tinh")))
        add("data[village2]", _text(land.get("xa")))

    # ---- Phần III: Thông tin chủ hồ sơ (người sử dụng đất) ----
    # Tự nộp (KHÔNG ủy quyền → người nộp CHÍNH LÀ chủ hồ sơ) → BẤM nút "Người nộp là chủ hồ sơ"
    # (data[BUTTON3]) để form tự copy toàn bộ Phần I xuống Phần III, đúng UX form và tránh lệch cascade.
    # Có ủy quyền (2 người khác nhau) → KHÔNG bấm nút, fill Phần III trực tiếp bằng thông tin chủ hồ sơ.
    if not has_uy_quyen:
        add("data[BUTTON3]", True)
    else:
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", owner_birthday)
        add("data[gender1]", owner_gender)
        add("data[ownerPhoneNumber]", owner_phone)
        add("data[ownerEmail]", owner_email)
        add("data[ownerIdentityNumber]", owner_identity)
        add("data[ownerIdentityDate]", owner_id_date)
        add("data[ownerIdentityAgency]", owner_id_agency)
        add("data[nation1]", "Việt Nam" if owner_name or owner_identity else None)
        if owner_residence:
            add("data[province1]", _province(owner_residence.get("tinh")))
            add("data[district1]", _text(owner_residence.get("xa")))
            add("data[ownerAddress]", _text(owner_residence.get("diaChi")))
        expect(_EXPECT_OWNER)

    # ---- Phần IV: Chi tiết Giấy chứng nhận đã cấp ----
    # Ngày cấp/hiệu lực/hết hạn dùng flatpickr yyyy/mm/dd (KHÁC các ô người dd/MM/yyyy) → _date_ymd.
    gcn_date = _date_ymd(values.get("Gcn_NgayCap"))
    add("data[licenseCode]", _serial(values.get("Gcn_SoPhatHanh")))
    add("data[licenseDate]", gcn_date)
    add("data[licensingPlace]", _agency(values.get("Gcn_DonViCap")))
    add("data[licensingAgency]", _text(values.get("Gcn_NoiCap")))
    # Ngày hiệu lực: GCN không có ô riêng → dùng chính ngày cấp GCN. Ngày hết hạn: 'Lâu dài' → trống.
    add("data[effectiveDate]", gcn_date)
    add("data[expirationDate]", _expiration(values.get("Gcn_ThoiHan")))

    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh chủ hồ sơ (người sử dụng đất) từ CCCD hoặc Đơn.")
    if not values.get("Gcn_SoPhatHanh") and not values.get("Gcn_NgayCap"):
        warnings.append("Chưa đọc được số phát hành/ngày cấp Giấy chứng nhận đã cấp (Phần IV).")
    return out, warnings
