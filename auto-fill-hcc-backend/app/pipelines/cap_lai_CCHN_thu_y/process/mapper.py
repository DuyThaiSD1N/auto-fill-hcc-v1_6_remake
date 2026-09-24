"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp lại Chứng chỉ hành nghề thú y".

NGƯỜI TRONG HỒ SƠ ĐI XUỐNG PHẦN II, KHÔNG LÊN PHẦN I. Phần I "Thông tin người nộp hồ sơ" là nhân thân
TÀI KHOẢN ĐANG ĐĂNG NHẬP do chính cổng đổ vào (ô số căn cước còn bị khoá không sửa được). Ghi đè họ tên
người đề nghị lên đó là ghép tên người này với giấy tờ tùy thân người kia — nhìn vào vẫn thấy "đủ dữ
liệu" nên không ai soát ra. Vì vậy mapper KHÔNG phát bất kỳ ô nhân thân nào của Phần I; nó bỏ tích
"Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II rồi đổ người đề nghị vào data[owner*].

Mục "Đã được cấp Chứng chỉ hành nghề thú y" là selectboxes 12 option dùng chung name data[deNghi][];
mapper khớp phạm vi đọc trong Đơn với nhãn chuẩn rồi gửi optionLabel cho FE tự tick.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_CCHN_thu_y.process.schema import (
    DON_SCOPE,
    DON_SCOPE_NEAR,
    DON_SCOPED_FIELDS,
    NGUOI_NOP_MARKERS,
    PHAM_VI_FIELD_KEY,
    PHAM_VI_OPTIONS,
    UI_COMP_BY_NAME,
)


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
    # t\.?\s*p\.? bắt mọi biến thể "TP", "TP.", "T.P", "T.P." (OCR/LLM hay trả "T.P Đà Nẵng").
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị\s*trấn|t\.?\s*t\.?|huyện|quận|thị\s*xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # BỎ tiền tố (Tỉnh/Thành phố/TP/T.P) LLM/OCR trả kèm TRƯỚC, rồi phân loại theo TÊN THÔ để gắn đúng
    # tiền tố (tránh "Tỉnh T.P Đà Nẵng"). Thành phố trực thuộc TW → "Thành phố", còn lại → "Tỉnh".
    bare = _strip_admin_prefix(text)
    if not bare:
        return None
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


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
        # "Phường X - Tỉnh Y": đơn chỉ ghi tới phường/xã → phần đầu là XÃ, không phải địa chỉ chi tiết.
        if re.match(r"^(xã|phường|thị\s*trấn)\s+", parts[0], re.IGNORECASE):
            out["xa"] = parts[0]
        else:
            out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value: Any) -> dict | None:
    """Parse và remap địa chỉ để normalize xa/phuong sau sáp nhập hành chính."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
    else:
        return None

    if not out or not any(out.values()):
        return None

    # Chuẩn hóa xã/phường theo các đợt sáp nhập để khớp option của select "Phường xã".
    return remap_area(out, allow_diachi_fallback=True)


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


def _yes(value: Any) -> bool:
    """LLM trả 'Có'/'Không' (hoặc true/false) → bool. Chỉ 'Có' mới coi là bật."""
    folded = _fold(value)
    return folded in {"co", "true", "1", "yes", "co quoc tich nuoc ngoai", "nguoi nuoc ngoai"}


def _so_dang_ky(value: Any) -> str | None:
    """Ô "Số đăng ký" đã in sẵn đuôi "-CCHNTY" → chỉ điền phần đứng trước."""
    text = _text(value)
    if not text:
        return None
    text = re.split(r"[-/]?\s*CCHN", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip(" -/") or None


def _match_key(value: Any) -> str:
    """Khóa so khớp nhãn: bỏ dấu, bỏ mọi ký tự không phải chữ/số → chịu được dấu chấm, dấu phẩy, xuống dòng."""
    return re.sub(r"[^0-9a-z]+", "", _fold(value))


_PHAM_VI_BY_KEY = {_match_key(option): option for option in PHAM_VI_OPTIONS}


def _match_pham_vi(line: str) -> str | None:
    """Một dòng phạm vi đọc từ Đơn → nhãn CHUẨN trên form, hoặc None nếu không chắc.

    Khớp nguyên văn trước; không có thì mới xét chứa nhau và CHỈ nhận khi duy nhất một option khớp —
    "Buôn bán thuốc thú y" cụt đuôi khớp cả 'trên cạn' lẫn 'thủy sản' nên phải để cán bộ tự tích.
    """
    key = _match_key(line)
    if not key:
        return None
    if key in _PHAM_VI_BY_KEY:
        return _PHAM_VI_BY_KEY[key]
    hits = [option for opt_key, option in _PHAM_VI_BY_KEY.items() if key in opt_key or opt_key in key]
    return hits[0] if len(hits) == 1 else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    # Không cần formContext: người trong hồ sơ luôn xuống khối chủ hồ sơ, khối người nộp không đụng tới
    # dù tự nộp hay nộp thay — nên không phải phân xử ai đang đăng nhập.
    _ = options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None, str]] = set()

    def add(name: str, value, *, occurrence=None, option_label: str | None = None) -> None:
        seen_key = (name, occurrence, option_label or "")
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in DON_SCOPED_FIELDS:
            # scope = panel tờ đơn; scopeNear/scopeAway để extension tự thu hẹp khi panel đó bọc cả
            # hai khối nhân thân, và BỎ ô nếu vẫn không tách được — thà trống còn hơn ghi đè Phần I.
            field["scope"] = DON_SCOPE
            field["scopeNear"] = DON_SCOPE_NEAR
            field["scopeAway"] = list(NGUOI_NOP_MARKERS)
        if occurrence is not None:
            field["occurrence"] = occurrence
        if option_label is not None:
            field["optionLabel"] = option_label
        out.append(field)
        seen.add(seen_key)

    # --- NGƯỜI ĐỀ NGHỊ = CHỦ HỒ SƠ (Phần II), KHÔNG phải người nộp hồ sơ (Phần I) ---
    name = _text(values.get("NguoiDeNghi_HoTen"))
    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))

    if not name:
        warnings.append("Thiếu họ tên người đề nghị từ CCCD/Đơn 03.HNTY.")

    add("data[kinhGui]", _text(values.get("Don_KinhGui")))

    # Phần I "Thông tin người nộp hồ sơ" KHÔNG được chạm tới ô nào — kể cả "Đối tượng nộp hồ sơ": đó là
    # thuộc tính của tài khoản VNeID đang đăng nhập, cổng tự đổ.
    #
    # Bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II. Người trong hồ sơ có thể trùng tài
    # khoản đang đăng nhập, nhưng ta không đọc được ô số căn cước bị khoá của Phần I để đối chiếu chắc
    # chắn — bỏ tích rồi khai đủ Phần II thì đúng cả hai trường hợp.
    add("data[isOwnerDossierCheck]", False)

    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", _date(values.get("NguoiDeNghi_NgaySinh")))
    add("data[ownerGender]", _text(values.get("NguoiDeNghi_GioiTinh")))
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", _date(values.get("NguoiDeNghi_NgayCapCCCD")))
    add("data[ownerIdIssuePlace]", normalize_issuer(values.get("NguoiDeNghi_NoiCapCCCD")) or None)
    if residence:
        add("data[ownerProvince]", _province_label(residence.get("tinh")))
        add("data[ownerDistrict]", _commune_label(residence.get("xa")))
        add("data[ownerAddress]", _text(residence.get("diaChi")))
    add("data[ownerPhoneNumber]", _phone(values.get("NguoiDeNghi_DienThoai")))
    add("data[ownerNation]", "Việt Nam" if name or identity else None)

    # --- Mục "Thông tin chung" của TỜ ĐƠN: cũng là NGƯỜI ĐỀ NGHỊ, không phải người nộp ---
    # Cổng prefill sẵn tài khoản đang đăng nhập (và có nút "Sao chép thông tin người nộp") nên phải ghi
    # đè. Field-key trùng Phần I nên add() tự gắn scope tờ đơn — xem DON_SCOPED_FIELDS.
    add("data[fullname]", name)
    add("data[birthday]", _date(values.get("NguoiDeNghi_NgaySinh")))
    add("data[identityNumber]", identity)
    add("data[identityDate]", _date(values.get("NguoiDeNghi_NgayCapCCCD")))
    if residence:
        add("data[province]", _province_label(residence.get("tinh")))
        add("data[district]", _commune_label(residence.get("xa")))
        add("data[address]", _text(residence.get("diaChi")))
    add("data[phoneNumber]", _phone(values.get("NguoiDeNghi_DienThoai")))

    # Ô "Tôi là người nước ngoài" cổng để sẵn CHƯA tick; chỉ TICK khi giấy tờ nói rõ là người nước ngoài
    # (công dân Việt Nam mà tick nhầm thì cổng bắt khai hộ chiếu).
    if _yes(values.get("Don_LaNguoiNuocNgoai")):
        add("data[toiLaNguoiNuocNgoai]", True)
    add("data[bangCapChuyenMon]", _text(values.get("Don_BangCapChuyenMon")))

    if not identity:
        warnings.append(
            "Không đọc được số căn cước của người đề nghị (Đơn 03.HNTY không ghi và hồ sơ không có "
            "CCCD của họ) — ô số căn cước ở mục Thông tin chủ hồ sơ còn trống, vui lòng điền tay."
        )

    # --- Nội dung đơn đăng ký ---
    # Phạm vi hành nghề: mỗi dòng được tích trong Đơn → 1 checkbox, FE khớp theo nhãn chuẩn.
    pham_vi_raw = _text(values.get("Don_PhamViHanhNghe"))
    matched: list[str] = []
    unmatched: list[str] = []
    for line in re.split(r"\s*[;\n]\s*", pham_vi_raw or ""):
        line = line.strip(" .;")
        if not line:
            continue
        option = _match_pham_vi(line)
        if option:
            matched.append(option)
        else:
            unmatched.append(line)
    for option in matched:
        add(PHAM_VI_FIELD_KEY, True, option_label=option)
    if unmatched:
        warnings.append(
            "Chưa tự tích được phạm vi hành nghề sau (không khớp dòng nào trên form, vui lòng tích "
            f"tay): {'; '.join(unmatched)}."
        )
    elif not matched:
        warnings.append(
            "Chưa đọc được phạm vi hành nghề trong Đơn 03.HNTY — vui lòng tích tay mục 'Đã được cấp "
            "Chứng chỉ hành nghề thú y'."
        )

    add("data[soDK]", _so_dang_ky(values.get("CCHNCu_SoDangKy")))
    add("data[ngayCC]", _date(values.get("CCHNCu_NgayHetHan")))
    add("data[lyDo]", _text(values.get("Don_LyDoCapLai")))
    # Ô "Địa điểm" là input text tự do, ghi TÊN ĐỊA DANH trần (vd "Lai Châu") chứ không phải nhãn
    # "Tỉnh Lai Châu" như select nơi cư trú → luôn bỏ tiền tố cấp hành chính.
    dia_diem = _text(values.get("Don_DiaDiem")) or (_text(residence.get("tinh")) if residence else None)
    add("data[diaDiem]", _strip_admin_prefix(dia_diem) if dia_diem else None)
    add("data[thoiGian]", _date(values.get("Don_NgayLamDon")))
    add("data[nguoiLD]", _text(values.get("Don_NguoiLamDon")) or name)

    return out, warnings
