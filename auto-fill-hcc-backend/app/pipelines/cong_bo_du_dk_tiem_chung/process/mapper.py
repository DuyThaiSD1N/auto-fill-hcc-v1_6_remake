"""Map compact source facts → Form.io data[...] fields cho "Công bố cơ sở đủ điều kiện tiêm chủng".

Phần I "Thông tin người nộp hồ sơ" = tài khoản VNeID đang đăng nhập (cổng tự đổ). Mapper CHỈ bổ sung khi
hồ sơ có CCCD KHỚP tài khoản (so số định danh, không có số thì so tên với formContext) — không khớp thì
không phát ô nào của Phần I, tránh ghi đè bằng nhân thân người khác.

Phần II "Thông tin chủ hồ sơ" bỏ tích "Người nộp hồ sơ là chủ hồ sơ" rồi điền theo tờ Thông báo:
  - họ tên = người đứng đầu cơ sở; địa chỉ, SĐT, email = của cơ sở ghi trên Thông báo;
  - ngày sinh, giới tính, CCCD, ngày cấp, nơi cấp ← CCCD người đứng đầu (hoặc CCCD người nộp nếu cùng người).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cong_bo_du_dk_tiem_chung.process.schema import UI_COMP_BY_NAME

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}

# Học hàm / chức danh chuyên môn hay đứng trước tên người đứng đầu cơ sở y tế ("BS CK1 Hoàng Việt Bắc").
_TITLE_PREFIX = re.compile(
    r"^(?:(?:bác\s*sĩ|bs|bsck\s*[12i]+|ck\s*[12i]+|chuyên\s*khoa\s*[12i]+|ths|ts|pgs|gs|ds|dược\s*sĩ|y\s*sĩ|ys|"
    r"cn|kts|ks|điều\s*dưỡng|đd|hộ\s*sinh)(?:\.|\b)\s*)+",
    re.IGNORECASE,
)

_PERSON_KEYS = ("HoTen", "NgaySinh", "GioiTinh", "SoDinhDanh", "NgayCap", "NoiCap", "ThuongTru")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        return _text(direct) if direct else None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _person_name(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return _TITLE_PREFIX.sub("", text).strip(" .,:-") or text


def _same_person(a: Any, b: Any) -> bool:
    """So họ tên bỏ dấu, bỏ khoảng trắng/ký tự lạ — chịu được IN HOA và OCR dính chữ."""
    key_a = re.sub(r"[^a-z]+", "", _fold(_person_name(a)))
    key_b = re.sub(r"[^a-z]+", "", _fold(_person_name(b)))
    return bool(key_a) and key_a == key_b


def _province_label(value: Any) -> str | None:
    """Nhãn option select Tỉnh/Thành phố: "Tỉnh Lai Châu" / "Thành phố Hà Nội"."""
    text = " ".join(str(_text(value) or "").split())
    bare = re.sub(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    if not bare:
        return None
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _parse_area_text(value: str) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    if len(parts) >= 3:
        out.update(tinh=parts[-1], xa=parts[-2], diaChi=", ".join(parts[:-2]))
    elif len(parts) == 2:
        out.update(tinh=parts[-1], xa=parts[0])
    else:
        out["diaChi"] = parts[0]
    return out


def _area(value: Any) -> dict | None:
    """Parse + remap địa chỉ để xã/phường khớp option sau sáp nhập hành chính."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or "",
            "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
        }
    else:
        return None
    if not out or not any(out.get(k) for k in ("tinh", "xa", "diaChi")):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    return normalize_date(m.group(0).replace("-", "/") if m else text) or None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "m"}:
        return "Nam"
    if folded in {"nu", "female", "f"}:
        return "Nữ"
    return None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _email(value: Any) -> str | None:
    text = (_text(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) else None


def _person(values: dict, prefix: str) -> dict:
    return {key: values.get(f"{prefix}{key}") for key in _PERSON_KEYS}


def _has_person(person: dict) -> bool:
    return bool(_text(person.get("HoTen")) or _identity(person.get("SoDinhDanh")))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    co_so = _text(values.get("CoSo_Ten"))
    dung_dau = _person_name(values.get("CoSo_NguoiDungDau"))
    dia_chi_co_so = _area(values.get("CoSo_DiaChi"))
    phone_co_so = _phone(values.get("CoSo_DienThoai"))
    email_co_so = _email(values.get("CoSo_Email"))

    # --- NGƯỜI NỘP: chỉ nhận CCCD khớp tài khoản đăng nhập. So số định danh trước, không có số thì so tên. ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    nop = _person(values, "NguoiNop_")
    nop_name = _text(nop.get("HoTen"))
    nop_identity = _identity(nop.get("SoDinhDanh"))
    nop_matched = False
    if _has_person(nop):
        if ctx_identity and nop_identity:
            nop_matched = ctx_identity == nop_identity
        elif ctx_name and nop_name:
            nop_matched = _same_person(ctx_name, nop_name)
    if not nop_matched:
        nop = {}

    # --- NGƯỜI ĐỨNG ĐẦU: CCCD phải trùng tên người đứng đầu trên Thông báo; người nộp cùng người thì dùng lại. ---
    dau = _person(values, "DauCoSo_")
    rejected_dau = None
    if _has_person(dau) and dung_dau and _text(dau.get("HoTen")) and not _same_person(dau.get("HoTen"), dung_dau):
        rejected_dau = _text(dau.get("HoTen"))
        dau = {}
    if not _has_person(dau) and nop and dung_dau and _same_person(nop.get("HoTen"), dung_dau):
        dau = nop
    submitter_is_head = bool(nop and dung_dau and _same_person(nop.get("HoTen"), dung_dau))

    # === Phần I — người nộp (chỉ khi có CCCD khớp tài khoản) ===
    if nop:
        if not ctx_name:
            add("data[fullname]", nop_name)
        if not ctx_identity:
            add("data[identityNumber]", nop_identity)
        add("data[birthday]", _date(nop.get("NgaySinh")))
        add("data[gender]", _gender(nop.get("GioiTinh")))
        add("data[identityDate]", _date(nop.get("NgayCap")))
        add("data[idIssuePlace]", normalize_issuer(nop.get("NoiCap")) or None)
        thuong_tru = _area(nop.get("ThuongTru"))
        if thuong_tru:
            add("data[province]", _province_label(thuong_tru.get("tinh")))
            add("data[district]", _text(thuong_tru.get("xa")))
            add("data[address]", _text(thuong_tru.get("diaChi")))
        # SĐT/email trên Thông báo là của người đứng đầu cơ sở → chỉ đổ lên Phần I khi người nộp là người đó.
        if submitter_is_head:
            add("data[phoneNumber]", phone_co_so)
            add("data[email]", email_co_so)

    # === Phần II — chủ hồ sơ theo tờ Thông báo ===
    add("data[isOwnerDossierCheck]", False)
    owner_name = dung_dau or _text(dau.get("HoTen"))
    add("data[ownerFullname]", owner_name)
    add("data[ownerBirthday]", _date(dau.get("NgaySinh")))
    add("data[ownerGender]", _gender(dau.get("GioiTinh")))
    add("data[ownerIdentityNumber]", _identity(dau.get("SoDinhDanh")))
    add("data[ownerIdentityDate]", _date(dau.get("NgayCap")))
    add("data[ownerIdIssuePlace]", normalize_issuer(dau.get("NoiCap")) or None)
    owner_area = dia_chi_co_so
    if not owner_area and dau:
        owner_area = _area(dau.get("ThuongTru"))
        if owner_area:
            warnings.append(
                "Tờ Thông báo không có địa chỉ cơ sở — mục Thông tin chủ hồ sơ đang lấy nơi thường trú trên CCCD "
                "người đứng đầu, vui lòng kiểm tra lại."
            )
    if owner_area:
        add("data[ownerProvince]", _province_label(owner_area.get("tinh")))
        add("data[ownerDistrict]", _text(owner_area.get("xa")))
        add("data[ownerAddress]", _text(owner_area.get("diaChi")))
    add("data[ownerPhoneNumber]", phone_co_so)
    add("data[ownerEmail]", email_co_so)
    add("data[ownerNation]", "Việt Nam" if owner_name else None)

    # --- Cảnh báo ---
    if not ctx_name and not ctx_identity:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền mục Thông tin người nộp hồ sơ."
        )
    elif not nop:
        warnings.append(
            "Hồ sơ không có CCCD của người nộp (tài khoản đang đăng nhập) — mục Thông tin người nộp hồ sơ giữ "
            "nguyên thông tin cổng tự điền, vui lòng bổ sung ngày sinh, giới tính, ngày cấp nếu còn trống."
        )
    if not co_so and not dung_dau:
        warnings.append(
            "Không đọc được tờ Thông báo cơ sở đủ điều kiện tiêm chủng — mục Thông tin chủ hồ sơ còn trống."
        )
    elif not dung_dau:
        warnings.append("Tờ Thông báo không ghi người đứng đầu cơ sở — kiểm tra lại ô Họ và tên chủ hồ sơ.")
    if not owner_area:
        warnings.append(
            "Không đọc được địa chỉ cơ sở — vui lòng chọn Tỉnh/Phường xã và nhập địa chỉ chi tiết ở mục Thông "
            "tin chủ hồ sơ."
        )
    elif not _text(owner_area.get("diaChi")):
        warnings.append("Địa chỉ cơ sở chưa có phần chi tiết (thôn/số nhà) — vui lòng nhập tay.")
    if rejected_dau:
        warnings.append(
            f"CCCD trong hồ sơ là của {rejected_dau}, KHÔNG phải người đứng đầu cơ sở ({dung_dau}) — không dùng "
            "cho mục Thông tin chủ hồ sơ."
        )
    if not _identity(dau.get("SoDinhDanh")) and owner_name:
        warnings.append(
            f"Hồ sơ không có CCCD của người đứng đầu cơ sở ({owner_name}) — ngày sinh, giới tính, số CCCD ở mục "
            "Thông tin chủ hồ sơ còn trống, vui lòng điền tay."
        )
    if not phone_co_so:
        warnings.append("Tờ Thông báo không có số điện thoại — số điện thoại chủ hồ sơ (bắt buộc) vui lòng nhập tay.")
    khac = _text(values.get("CoSo_CacCoSoKhac"))
    if co_so and khac:
        warnings.append(
            f"Hồ sơ có Thông báo của nhiều cơ sở; mục Thông tin chủ hồ sơ đang điền theo {co_so}. Các cơ sở khác: "
            f"{khac}."
        )

    return out, warnings
