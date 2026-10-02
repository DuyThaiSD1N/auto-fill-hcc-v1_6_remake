"""Map facts "Đăng ký hoạt động khuyến mại mang tính may rủi trên địa bàn 01 tỉnh" → Form.io data[...] (cổng
Bộ Công Thương).

Field-key TRÙNG giữa form tài khoản và tờ khai Mẫu 02 ĐP (fullname/phoneNumber/province/district/address/
taxCode/email) → occurrence 0 = khối tài khoản, 1 = tờ khai. Khối tài khoản CHỈ điền khi giấy tờ trong hồ sơ
khớp tài khoản đang đăng nhập (options.formContext: họ tên + số định danh); không có mốc thì để nguyên cho cổng.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, remap_area
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_khuyen_mai_may_rui.process.schema import UI_COMP_BY_NAME

_ACCOUNT = 0
_DECLARATION = 1
_DEFAULT_REQUEST = "Đăng ký thực hiện khuyến mại"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _date(value: Any) -> str | None:
    text = normalize_date(str(value or "")) if value else ""
    return text if text and re.fullmatch(r"\d{2}/\d{2}/\d{4}", text) else None


def _phone(value: Any) -> str | None:
    """Số điện thoại 10–11 số bắt đầu bằng 0; Đơn hay ghi dạng mã quốc gia "84…" → đổi về "0…"."""
    digits = _digits(value)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _tax_code(value: Any) -> str | None:
    """MST 10 số hoặc 10 số + "-" + 3 số (đơn vị phụ thuộc); thiếu số thì KHÔNG điền."""
    text = re.sub(r"\s+", "", str(value or ""))
    match = re.fullmatch(r"(\d{10})(?:-?(\d{3}))?", text)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}" if match.group(2) else match.group(1)


def _identity(value: Any) -> str | None:
    """Số CCCD 12 số / CMND 9 số; đọc thiếu số thì coi như không có."""
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or value.get("phuongXa") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not any((area["tinh"], area["xa"], area["diaChi"])):
        return None
    # Bảng sáp nhập 2025: địa chỉ cũ còn cấp huyện/tên xã cũ → đơn vị hiện hành mà select cổng có.
    return remap_area(area) or area


def _full_address(value: Any, area: dict | None) -> str | None:
    if isinstance(value, dict):
        direct = _text(value.get("fullText") or value.get("full"))
        if direct:
            return direct
    if not area:
        return None
    return ", ".join(p for p in (_text(area.get("diaChi")), _text(area.get("xa")), _text(area.get("tinh"))) if p) or None


def _area_label(value: Any) -> str | None:
    """Tên trần (bỏ "Tỉnh/Thành phố/Phường/Xã…"): select Choices.js của cổng khớp theo phần tên."""
    text = _text(value)
    if not text:
        return None
    prefixes = ("thanh pho", "tinh", "tp.", "tp", "thi tran", "thi xa", "phuong", "xa")
    changed = True
    while changed:
        changed = False
        folded = _fold(text)
        for prefix in prefixes:
            if folded == prefix:
                return None
            if folded.startswith(prefix + " "):
                text = text[len(prefix):].strip(" .")
                changed = True
                break
    return text or None


def _province(value: Any) -> str | None:
    """Tên trần theo danh mục ("TP. HCM" → "Hồ Chí Minh"); không nhận ra thì bóc tiền tố."""
    text = _text(value)
    return (canonical_province(text) or _area_label(text)) if text else None


def _submission_province(kinh_gui: Any) -> str | None:
    """Tỉnh nộp đơn chỉ khi "Kính gửi" nêu ĐÚNG MỘT tỉnh/thành ("Sở Công Thương tỉnh X")."""
    text = _text(kinh_gui)
    if not text:
        return None
    folded = _fold(text)
    if "cac tinh" in folded or "toan quoc" in folded or folded.count("tinh ") + folded.count("thanh pho ") != 1:
        return None
    match = re.search(r"(?:tỉnh|thành phố|tp\.?)\s+(.+)$", text, flags=re.IGNORECASE)
    return _province(match.group(0)) if match else None


def _account_anchor(options: dict | None) -> tuple[str, str]:
    context = (options or {}).get("formContext") or {}
    return (
        _fold(context.get("applicantFullname")),
        _digits(context.get("applicantIdentityNumber")),
    )


def _matches_account(name: Any, identity: Any, anchor: tuple[str, str]) -> bool:
    """Tài khoản có đủ tên + số định danh và giấy tờ cũng đủ → phải khớp CẢ HAI; thiếu vế nào thì so vế còn lại."""
    anchor_name, anchor_id = anchor
    person_name, person_id = _fold(name), _digits(identity)
    checks = []
    if anchor_id and person_id:
        checks.append(person_id == anchor_id)
    if anchor_name and person_name:
        checks.append(person_name == anchor_name)
    return bool(checks) and all(checks)


def _request_content(so: str | None, ngay: str | None, trader: str | None, promotion: str | None) -> str | None:
    """Ô "Nội dung yêu cầu giải quyết": số, ngày văn bản đề nghị + tên chương trình, ghép từ facts đã đọc."""
    if not (so or ngay or promotion):
        return None
    head = "Văn bản" + (f" số {so}" if so else "") + (f" ngày {ngay}" if ngay else "")
    if trader:
        head += f" của {trader}"
    head += " về việc đăng ký thực hiện khuyến mại"
    return head + (f" chương trình \"{promotion}\"" if promotion else "")


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None, default: bool = False) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        if default:
            item["default"] = True
        out.append(item)
        seen.add(key)

    def warn_unreadable(label: str, raw: Any, parsed: Any) -> None:
        if raw not in (None, "") and not parsed:
            warnings.append(f"{label} đọc được \"{_text(raw)}\" nhưng không đủ chữ số — vui lòng nhập tay.")

    # === Facts thương nhân (chủ hồ sơ + thông tin doanh nghiệp trên tờ khai) ===
    trader = _text(values.get("ThuongNhan_Ten"))
    tax = _tax_code(values.get("ThuongNhan_MaSoThue"))
    trader_id = _identity(values.get("ThuongNhan_SoCanCuoc"))
    phone = _phone(values.get("ThuongNhan_DienThoai"))
    fax = _phone(values.get("ThuongNhan_Fax"))
    contact = _text(values.get("ThuongNhan_NguoiLienHe"))
    contact_phone = _phone(values.get("ThuongNhan_DienThoaiLienHe"))
    raw_area = values.get("ThuongNhan_DiaChi")
    head_office = _area(raw_area)
    warn_unreadable("Mã số thuế", values.get("ThuongNhan_MaSoThue"), tax)
    warn_unreadable("Điện thoại thương nhân", values.get("ThuongNhan_DienThoai"), phone)
    warn_unreadable("Fax", values.get("ThuongNhan_Fax"), fax)
    warn_unreadable("Điện thoại người liên hệ", values.get("ThuongNhan_DienThoaiLienHe"), contact_phone)
    if not trader:
        warnings.append("Không đọc được tên thương nhân trên Đăng ký thực hiện khuyến mại.")

    # === Khối TÀI KHOẢN: chỉ lấy từ giấy tờ khớp tài khoản đăng nhập (tên + số định danh) ===
    anchor = _account_anchor(options)
    person_name = _text(values.get("NguoiNop_HoTen"))
    person_id = _digits(values.get("NguoiNop_SoDinhDanh")) or None
    if not any(anchor):
        if person_name or person_id:
            warnings.append("Chưa đọc được tài khoản đăng nhập trên form — không điền khối thông tin tài khoản.")
    else:
        if person_name or person_id:
            if _matches_account(person_name, person_id, anchor):
                residence = _area(values.get("NguoiNop_NoiCuTru"))
                add("data[fullname]", person_name, occurrence=_ACCOUNT)
                add("data[identityNumber]", person_id)
                add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
                add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
                if residence:
                    add("data[province]", _area_label(residence.get("tinh")), occurrence=_ACCOUNT)
                    add("data[district]", _area_label(residence.get("xa")), occurrence=_ACCOUNT)
                    add("data[address]", _text(residence.get("diaChi")), occurrence=_ACCOUNT)
            else:
                warnings.append(
                    "CCCD trong hồ sơ không khớp tài khoản đăng nhập — không lấy CCCD đó cho khối thông tin tài khoản."
                )
        # CCCD không in SĐT → SĐT tài khoản chỉ lấy khi tài khoản chính là người liên hệ trên Đơn, hoặc là
        # chủ hộ kinh doanh có số căn cước in trên Đơn (SĐT thương nhân là của chủ hộ).
        if contact_phone and anchor[0] and _fold(contact) == anchor[0]:
            add("data[phoneNumber]", contact_phone, occurrence=_ACCOUNT)
        elif phone and trader_id and _matches_account(None, trader_id, anchor):
            add("data[phoneNumber]", phone, occurrence=_ACCOUNT)

    so = _text(values.get("Don_So"))
    ngay = _date(values.get("Don_NgayLap"))
    promotion = _text(values.get("CTKM_Ten"))
    request = _request_content(so, ngay, trader, promotion)
    add("data[noidungyeucaugiaiquyet]", request or _DEFAULT_REQUEST, default=not request)

    # === Khối CHỦ HỒ SƠ = thương nhân; bỏ tích để mở khối, điền tường minh ===
    add("data[isOwnerDossier]", False)
    add("data[ownerFullname]", trader)
    # Cổng điền sẵn CCCD chủ hồ sơ = CCCD tài khoản đăng nhập. Chủ hồ sơ là thương nhân: chỉ giữ số căn cước
    # in trên Đơn (chủ hộ kinh doanh); không có thì ghi RỖNG để không nộp CCCD người đăng nhập dưới tên
    # thương nhân.
    out.append({
        "name": "data[ownerIdentityNumber]",
        "comp": UI_COMP_BY_NAME["data[ownerIdentityNumber]"],
        "value": trader_id or "",
    })
    add("data[ownertaxCode]", tax)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerAddress]", _full_address(raw_area, head_office))

    # === Tờ khai Mẫu 02 ĐP: đầu đơn ===
    add("data[soDon]", so)
    # Kính gửi nêu đúng một tỉnh > địa danh dòng ngày lập > tỉnh trụ sở chính.
    province_of_submission = (
        _submission_province(values.get("Don_KinhGui"))
        or _province(values.get("Don_DiaDanh"))
        or _province((head_office or {}).get("tinh"))
    )
    add("data[tinhThanhPhoNopDon]", province_of_submission)
    if not province_of_submission:
        warnings.append("Không xác định được tỉnh nộp đơn — vui lòng chọn tay 'Tỉnh / Thành Phố nộp đơn'.")
    add("data[ngayNopDon]", ngay)
    add("data[kinhGui]", _text(values.get("Don_KinhGui")))

    # === Tờ khai: thông tin doanh nghiệp (occurrence 1 cho key trùng) ===
    add("data[fullname]", trader, occurrence=_DECLARATION)
    if head_office:
        add("data[province]", _area_label(head_office.get("tinh")), occurrence=_DECLARATION)
        add("data[district]", _area_label(head_office.get("xa")), occurrence=_DECLARATION)
        add("data[address]", _text(head_office.get("diaChi")), occurrence=_DECLARATION)
        if head_office.get("tinh") and not head_office.get("xa"):
            warnings.append("Không xác định được phường/xã trụ sở chính (có thể là tên trước sáp nhập) — vui lòng chọn tay.")
    add("data[phoneNumber]", phone, occurrence=_DECLARATION)
    add("data[fax]", fax)
    add("data[email]", _text(values.get("ThuongNhan_Email")), occurrence=_DECLARATION)
    add("data[fullname1]", contact)
    add("data[phoneNumber1]", contact_phone)
    add("data[taxCode]", tax, occurrence=_DECLARATION)

    # === Tờ khai: chương trình khuyến mại ===
    add("data[tenkm]", promotion)
    start, end = _date(values.get("CTKM_TuNgay")), _date(values.get("CTKM_DenNgay"))
    add("data[ngayvb1]", start)
    if start and end:
        warnings.append(
            f"Ô 'Thời gian khuyến mại' chỉ có một ngày — đã điền ngày bắt đầu {start}; chương trình kéo dài đến "
            f"{end}, vui lòng kiểm tra lại."
        )
    add("data[hhkm]", _text(values.get("CTKM_HangHoaKhuyenMai")))
    add("data[slhh]", _text(values.get("CTKM_SoLuongHangHoa")))
    add("data[dvkm]", _text(values.get("CTKM_HangHoaDungKhuyenMai")))
    add("data[pvkm]", _text(values.get("CTKM_DiaBan")))
    add("data[htkm]", _text(values.get("CTKM_HinhThuc")))
    add("data[khkm]", _text(values.get("CTKM_KhachHang")))
    add("data[tgtkm]", _text(values.get("CTKM_TongGiaTri")))
    add("data[daiDienPhapLuat]", _text(values.get("ThuongNhan_DaiDien")))

    return out, warnings
