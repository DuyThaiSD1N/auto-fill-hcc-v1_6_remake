"""Map compact source facts → Form.io data[...] fields cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh
dược (Sở Y tế)".

Phần I "Thông tin người nộp hồ sơ" = tài khoản đăng nhập. Họ tên + CC/CCCD + Đối tượng bị KHOÁ theo tài
khoản → không bao giờ phát. Các ô còn lại quyết định theo formContext (tên + số định danh tài khoản) SO với
chủ hồ sơ:
  - TỰ NỘP (tài khoản = chủ cơ sở): Phần I = nhân thân chủ hồ sơ (kể cả SĐT/email của cơ sở).
  - NỘP THAY: Phần I CHỈ lấy từ CCCD khớp tài khoản (NguoiNop_*); không có thẻ thì để cổng tự điền. SĐT
    trên Đơn là của cơ sở → không đổ sang người nộp thay.
  - Không đọc được tài khoản: không đụng Phần I (tránh ghi nhân thân người khác lên ô của người nộp).

Phần II "Thông tin chủ hồ sơ": cổng đổ sẵn tên + CCCD TÀI KHOẢN vào đây → LUÔN bỏ tích "Người nộp hồ sơ là
chủ hồ sơ" và ghi đè tường minh bằng chủ cơ sở; data[ghiChu] = nội dung xin điều chỉnh / lý do cấp lại.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.schema import (
    UI_COMP_BY_NAME,
)

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}

# Tiền tố trình độ đứng trước tên người phụ trách chuyên môn trên Đơn / GPP ("DSĐH. Trần Thị Bích").
_TITLE_PREFIX = re.compile(
    r"^(?:(?:dược\s*sĩ(?:\s*(?:đại\s*học|trung\s*học|cao\s*đẳng|chuyên\s*khoa\s*[12i]+))?|"
    r"ds\s*(?:đh|dh|th|cđ|cd|ck\s*[12i]+)?|bác\s*sĩ|bs|ths|ts)(?:\.|\b)\s*)+",
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
    """So họ tên bỏ dấu, bỏ khoảng trắng/ký tự lạ — chịu được IN HOA, tiền tố "DSĐH." và OCR dính chữ."""
    key_a = re.sub(r"[^a-z]+", "", _fold(_person_name(a)))
    key_b = re.sub(r"[^a-z]+", "", _fold(_person_name(b)))
    return bool(key_a) and key_a == key_b


def _province_label(value: Any) -> str | None:
    """Nhãn option select Tỉnh/Thành phố: "Tỉnh Hưng Yên" / "Thành phố Đà Nẵng"."""
    text = " ".join(str(_text(value) or "").split())
    bare = re.sub(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    if not bare:
        return None
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _parse_area_text(value: str) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if parts and _fold(parts[-1]) in {"viet nam", "vietnam"}:
        parts = parts[:-1]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district = re.compile(r"^(huyện|quận|thị\s*xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district.match(parts[-2]):
        out.update(tinh=parts[-1], xa=parts[-3], diaChi=", ".join(parts[:-3]))
    elif len(parts) >= 3:
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
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    return normalize_date(f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else text) or None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "m"}:
        return "Nam"
    if folded in {"nu", "female", "f"}:
        return "Nữ"
    return None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _issuer(value: Any) -> str | None:
    """Nơi cấp CCCD. Đơn có dòng "Số CCHN Dược … Nơi cấp: Sở Y tế …" — lọt sang đây thì bỏ, không điền."""
    text = _text(value)
    if not text or "y te" in _fold(text):
        return None
    return normalize_issuer(text) or None


def _email(value: Any) -> str | None:
    text = (_text(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) else None


def _person(values: dict, prefix: str) -> dict:
    return {key: values.get(f"{prefix}{key}") for key in _PERSON_KEYS}


def _has_person(person: dict) -> bool:
    return bool(_text(person.get("HoTen")) or _identity(person.get("SoDinhDanh")))


def _matches(person: dict, name: str | None, identity: str | None) -> bool:
    """So một người với mốc (tên, số định danh): có số ở cả hai phía thì so số, không thì so tên."""
    p_identity = _identity(person.get("SoDinhDanh"))
    if identity and p_identity:
        return identity == p_identity
    return bool(name) and _same_person(person.get("HoTen"), name)


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

    def add_area(province_name: str, district_name: str, address_name: str, area: dict | None) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _text(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    owner = _person(values, "ChuHoSo_")
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))
    owner_email = _email(values.get("ChuHoSo_Email"))
    noi_dung = _text(values.get("NoiDungDeNghi"))

    # --- Mốc tài khoản đăng nhập (extension gửi formContext). ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    # NGƯỜI NỘP: chỉ nhận CCCD khớp tài khoản.
    nop = _person(values, "NguoiNop_")
    if not (has_ctx and _has_person(nop) and _matches(nop, ctx_name, ctx_identity)):
        nop = {}

    self_submit = None
    if has_ctx and _has_person(owner):
        self_submit = _matches(owner, ctx_name, ctx_identity)
    elif has_ctx and nop and not _has_person(owner):
        # Không đọc được chủ hồ sơ từ Đơn/GCN nhưng có CCCD tài khoản → coi CCCD đó là chủ hồ sơ tự nộp.
        self_submit = True
    if self_submit and nop:
        # Tự nộp: CCCD tài khoản CŨNG là CCCD chủ hồ sơ → vá các ô chủ hồ sơ còn thiếu (ngày/nơi cấp...).
        owner = {key: owner.get(key) or nop.get(key) for key in _PERSON_KEYS}

    owner_name = _person_name(owner.get("HoTen"))
    owner_identity = _identity(owner.get("SoDinhDanh"))
    owner_area = _area(owner.get("ThuongTru"))

    # === Phần I — người nộp (ô khoá theo tài khoản không phát) ===
    if self_submit:
        add("data[birthday]", _date(owner.get("NgaySinh")))
        add("data[gender]", _gender(owner.get("GioiTinh")))
        add("data[identityDate]", _date(owner.get("NgayCap")))
        add("data[idIssuePlace]", _issuer(owner.get("NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", owner_area)
        add("data[phoneNumber]", owner_phone)
        add("data[email]", owner_email)
    elif nop:
        add("data[birthday]", _date(nop.get("NgaySinh")))
        add("data[gender]", _gender(nop.get("GioiTinh")))
        add("data[identityDate]", _date(nop.get("NgayCap")))
        add("data[idIssuePlace]", _issuer(nop.get("NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", _area(nop.get("ThuongTru")))

    # === Phần II — chủ hồ sơ (luôn bỏ tích rồi ghi đè) ===
    add("data[isOwnerDossierCheck]", False)
    add("data[ownerFullname]", owner_name)
    add("data[ownerBirthday]", _date(owner.get("NgaySinh")))
    add("data[ownerGender]", _gender(owner.get("GioiTinh")))
    add("data[ownerIdentityNumber]", owner_identity)
    add("data[ownerIdentityDate]", _date(owner.get("NgayCap")))
    add("data[ownerIdIssuePlace]", _issuer(owner.get("NoiCap")))
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", owner_area)
    add("data[ownerPhoneNumber]", owner_phone)
    add("data[ownerEmail]", owner_email)
    add("data[ownerNation]", "Việt Nam" if owner_name or owner_identity else None)
    add("data[ghiChu]", noi_dung)

    # --- Cảnh báo ---
    if not has_ctx:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền mục Thông tin người nộp hồ sơ, vui "
            "lòng kiểm tra ngày sinh, giới tính, địa chỉ, số điện thoại người nộp."
        )
    elif self_submit is False:
        if not nop:
            warnings.append(
                "Người nộp (tài khoản đăng nhập) khác chủ hồ sơ nhưng hồ sơ không có CCCD của người nộp — mục "
                "Thông tin người nộp giữ nguyên thông tin cổng tự điền, vui lòng bổ sung giới tính, địa chỉ nếu "
                "còn trống."
            )
        warnings.append("Nộp thay: số điện thoại người nộp (bắt buộc) không có trong giấy tờ — vui lòng nhập tay.")
    if not owner_name:
        warnings.append(
            "Không đọc được họ tên chủ cơ sở từ Đơn đề nghị / GCN đăng ký hộ kinh doanh / CCCD — mục Thông tin "
            "chủ hồ sơ còn trống."
        )
    if owner_name and not owner_identity:
        warnings.append(f"Chưa có số CCCD của chủ hồ sơ ({owner_name}) — vui lòng nhập tay ô CC/CCCD/CMND.")
    if owner_name and not owner_area:
        warnings.append(
            "Không đọc được nơi thường trú của chủ hồ sơ — vui lòng chọn Tỉnh/Phường xã và nhập địa chỉ chi tiết."
        )
    if owner_name and not owner_phone:
        warnings.append("Không tìm thấy số điện thoại của cơ sở / chủ hồ sơ (bắt buộc) — vui lòng nhập tay.")

    return out, warnings
