"""Map compact source facts → Form.io data[...] fields cho "Cung cấp thông tin quy hoạch".

Chỉ điền MỘT khối: Phần I "Thông tin người nộp hồ sơ". Không có khối chủ hồ sơ/thửa đất/GCN.
Guard formContext: chỉ đè Phần I khi người nộp (NguoiNop_*) TRÙNG tài khoản đăng nhập (VNeID) —
tránh đè nhầm thông tin cổng đã tự điền khi nộp thay. Không có mỏ neo → điền theo giấy tờ.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cung_cap_thong_tin_quy_hoach.process.schema import UI_COMP_BY_NAME

# Ô extension CHỊU TRÁCH NHIỆM điền từ CCCD/Đơn. Thiếu dữ liệu → phát "dom-expect" để FE TÔ ĐỎ.
_EXPECT_APPLICANT = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return _full_address(value)
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
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+",
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
    prefix = "Thành phố" if folded in city_markers else "Tỉnh"
    return f"{prefix} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    # Giữ nguyên nhãn phường/xã (đã là tên MỚI theo Đơn); FE khớp option theo text đã fold + chuẩn hóa gạch.
    return _text(value)


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


def _cccd_issuer(value: Any, ngay_cap: Any) -> str | None:
    text = _text(value)
    if text:
        return normalize_issuer(text)
    d = _date(ngay_cap)
    return default_issuer(d) if d else None


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _same_person(doc_id: Any, doc_name: Any, ctx_id: Any, ctx_name: Any) -> bool:
    did, cid = _identity(doc_id), _identity(ctx_id)
    if did and cid:
        return did == cid
    dname, cname = _fold(doc_name), _fold(ctx_name)
    return bool(dname and cname and dname == cname)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    context = _form_context(options)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def expect(names: tuple[str, ...]) -> None:
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    name = _text(values.get("NguoiNop_HoTen"))
    identity = _identity(values.get("NguoiNop_SoDinhDanh"))
    birthday = _date(values.get("NguoiNop_NgaySinh"))
    gender = _text(values.get("NguoiNop_GioiTinh"))
    phone = _phone(values.get("NguoiNop_DienThoai"))
    email = _text(values.get("NguoiNop_Email"))
    id_date = _date(values.get("NguoiNop_NgayCapCccd"))
    id_agency = _cccd_issuer(values.get("NguoiNop_NoiCapCccd"), values.get("NguoiNop_NgayCapCccd"))
    residence = _area(values.get("NguoiNop_ThuongTru"))

    # Chỉ đè Phần I khi khớp tài khoản đang đăng nhập (tránh đè nhầm thông tin người khác VNeID đã điền).
    # Không có anchor (tài khoản trống) → cứ điền theo giấy tờ.
    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(identity, name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    if can_fill_applicant and (name or identity):
        # Hồ sơ cá nhân (có CCCD) → mặc định "Cá nhân"; người dùng tự đổi sang Tổ chức nếu cần.
        add("data[chonDoiTuong]", "Cá nhân")
        add("data[fullname]", name)
        add("data[birthday]", birthday)
        add("data[gender]", gender)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        add("data[identityNumber]", identity)
        add("data[identityDate]", id_date)
        add("data[identityAgency]", id_agency)
        add("data[nation]", "Việt Nam")
        if residence:
            add("data[province]", _province_label(residence.get("tinh")))
            add("data[district]", _commune_label(residence.get("xa")))
            add("data[address]", _text(residence.get("diaChi")))
        expect(_EXPECT_APPLICANT)

    if not name or not identity:
        warnings.append("Thiếu họ tên/số định danh người nộp hồ sơ từ CCCD hoặc Đơn đề nghị.")
    return out, warnings
