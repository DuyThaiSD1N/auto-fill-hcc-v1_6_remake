"""Map facts "Thông báo sửa đổi, bổ sung nội dung CTKM" → Form.io data[...] (cổng Bộ Công Thương).

Field-key TRÙNG giữa form tài khoản và tờ khai Mẫu 06 (fullname/phoneNumber/province/email/address) →
occurrence 0 = khối tài khoản, 1 = tờ khai. Khối tài khoản CHỈ điền khi CCCD trong hồ sơ khớp tài khoản
đang đăng nhập (options.formContext); không khớp hoặc không có mốc thì để nguyên cho cổng.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.thong_bao_sua_doi_ctkm.process.schema import UI_COMP_BY_NAME

_ACCOUNT = 0
_DECLARATION = 1
_DEFAULT_REQUEST = "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,")
    return text or None


def _multiline(value: Any) -> str | None:
    """Textarea giữ xuống dòng giữa các cam kết/ý; chỉ gọn khoảng trắng trong từng dòng."""
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    lines = [" ".join(line.split()) for line in str(value).splitlines()]
    text = "\n".join(line for line in lines if line).strip()
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
    digits = _digits(value)
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _tax_code(value: Any) -> str | None:
    """MST 10 số hoặc 10 số + "-" + 3 số (đơn vị phụ thuộc); thiếu số thì KHÔNG điền."""
    text = re.sub(r"\s+", "", str(value or ""))
    match = re.fullmatch(r"(\d{10})(?:-?(\d{3}))?", text)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}" if match.group(2) else match.group(1)


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


def _submission_province(kinh_gui: Any) -> str | None:
    """Tỉnh nộp đơn chỉ khi "Kính gửi" nêu ĐÚNG MỘT tỉnh/thành ("Sở Công Thương tỉnh X").

    Thông báo gửi đồng loạt ("… các Tỉnh/Thành phố trên toàn quốc") không cho biết nơi nộp → để trống.
    """
    text = _text(kinh_gui)
    if not text:
        return None
    folded = _fold(text)
    if "cac tinh" in folded or "toan quoc" in folded or folded.count("tinh ") + folded.count("thanh pho ") != 1:
        return None
    match = re.search(r"(?:tỉnh|thành phố|tp\.?)\s+(.+)$", text, flags=re.IGNORECASE)
    return _area_label(match.group(0)) if match else None


def _account_anchor(options: dict | None) -> tuple[str, str]:
    context = (options or {}).get("formContext") or {}
    return (
        _fold(context.get("applicantFullname")),
        _digits(context.get("applicantIdentityNumber")),
    )


def _matches_account(name: Any, identity: Any, anchor: tuple[str, str]) -> bool:
    anchor_name, anchor_id = anchor
    person_id = _digits(identity)
    if anchor_id and person_id:
        return person_id == anchor_id
    return bool(anchor_name and _fold(name) and _fold(name) == anchor_name)


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

    # === Khối TÀI KHOẢN: chỉ khi CCCD trong hồ sơ khớp tài khoản đăng nhập ===
    person_name = _text(values.get("NguoiNop_HoTen"))
    person_id = _digits(values.get("NguoiNop_SoDinhDanh")) or None
    anchor = _account_anchor(options)
    if person_name or person_id:
        if not any(anchor):
            warnings.append("Chưa đọc được tài khoản đăng nhập trên form — không điền khối thông tin tài khoản.")
        elif not _matches_account(person_name, person_id, anchor):
            warnings.append("CCCD trong hồ sơ không khớp tài khoản đăng nhập — không điền khối thông tin tài khoản.")
        else:
            residence = _area(values.get("NguoiNop_NoiCuTru"))
            add("data[fullname]", person_name, occurrence=_ACCOUNT)
            add("data[identityNumber]", person_id)
            add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
            add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
            if residence:
                add("data[province]", _area_label(residence.get("tinh")), occurrence=_ACCOUNT)
                add("data[district]", _area_label(residence.get("xa")))
                add("data[address]", _text(residence.get("diaChi")), occurrence=_ACCOUNT)

    # === Facts thương nhân (chủ hồ sơ + thông tin doanh nghiệp trên tờ khai) ===
    trader = _text(values.get("ThuongNhan_Ten"))
    tax = _tax_code(values.get("ThuongNhan_MaSoThue"))
    phone = _phone(values.get("ThuongNhan_DienThoai"))
    fax = _phone(values.get("ThuongNhan_Fax"))
    contact_phone = _phone(values.get("ThuongNhan_DienThoaiLienHe"))
    raw_area = values.get("ThuongNhan_DiaChi")
    head_office = _area(raw_area)
    warn_unreadable("Mã số thuế", values.get("ThuongNhan_MaSoThue"), tax)
    warn_unreadable("Điện thoại thương nhân", values.get("ThuongNhan_DienThoai"), phone)
    warn_unreadable("Fax", values.get("ThuongNhan_Fax"), fax)
    warn_unreadable("Điện thoại người liên hệ", values.get("ThuongNhan_DienThoaiLienHe"), contact_phone)
    if not trader:
        warnings.append("Không đọc được tên thương nhân trên Thông báo.")

    promotion = _text(values.get("CTKM_Ten"))
    add(
        "data[noidungyeucaugiaiquyet]",
        f"{_DEFAULT_REQUEST} \"{promotion}\"" if promotion else _DEFAULT_REQUEST,
        default=not promotion,
    )

    # === Khối CHỦ HỒ SƠ = thương nhân; bỏ tích để mở khối, điền tường minh ===
    add("data[isOwnerDossier]", False)
    add("data[ownerFullname]", trader)
    add("data[ownertaxCode]", tax)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerAddress]", _full_address(raw_area, head_office))

    # === Tờ khai Mẫu 06: đầu đơn ===
    add("data[registerNumber]", _text(values.get("ThongBao_So")))
    province_of_submission = _submission_province(values.get("ThongBao_KinhGui"))
    add("data[tinhThanhPhoNopDon]", province_of_submission)
    if not province_of_submission:
        warnings.append("Kính gửi không nêu đúng một tỉnh — vui lòng chọn tay 'Tỉnh / Thành Phố nộp đơn'.")
    add("data[ngayNopDon]", _date(values.get("ThongBao_NgayLap")))
    add("data[kinhGui]", _text(values.get("ThongBao_KinhGui")))

    # === Tờ khai: thông tin doanh nghiệp (occurrence 1 cho key trùng) ===
    add("data[fullname]", trader, occurrence=_DECLARATION)
    if head_office:
        add("data[province]", _area_label(head_office.get("tinh")), occurrence=_DECLARATION)
        add("data[village]", _area_label(head_office.get("xa")))
        add("data[address]", _text(head_office.get("diaChi")), occurrence=_DECLARATION)
    add("data[phoneNumber]", phone, occurrence=_DECLARATION)
    add("data[email]", _text(values.get("ThuongNhan_Email")), occurrence=_DECLARATION)
    add("data[fax]", fax)
    add("data[contactPerson]", _text(values.get("ThuongNhan_NguoiLienHe")))
    add("data[phone]", contact_phone)
    add("data[registerNumberSubmitted]", _text(values.get("ThongBaoGoc_So")))
    add("data[submissionDate]", _date(values.get("ThongBaoGoc_Ngay")))

    # === Tờ khai: chương trình khuyến mại ===
    add("data[promotionName]", promotion)
    add("data[startDate]", _date(values.get("CTKM_NgayBatDauSuaDoi")))
    add("data[lyDoDieuChinh]", _multiline(values.get("CTKM_LyDoDieuChinh")))
    add("data[CamKetKhac]", _multiline(values.get("CTKM_CamKet")))

    return out, warnings
