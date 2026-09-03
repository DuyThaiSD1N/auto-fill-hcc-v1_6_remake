"""Map compact ATTP-cấp facts → Form.io fields (cổng Bộ Công Thương). Tái dùng helper của
cap_lai_an_toan_thuc_pham (#42) nhưng form CẤP LẦN ĐẦU: kê khai cơ sở SXKD (Mẫu 01a), 4 checkbox loại
hình, và field-key TRÙNG Phần I (tài khoản) / Phần IV (cơ sở) → dùng OCCURRENCE 0/1.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_gcn_attp_cong_thuong.process.schema import UI_COMP_BY_NAME


@dataclass
class Person:
    name: str | None = None
    identity: str | None = None
    birthday: str | None = None
    issue_date: str | None = None
    issuer: str | None = None
    residence: Any = None
    phone: str | None = None
    email: str | None = None
    tax: str | None = None


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


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
        return _text(value)
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "thonXom", "soNha"),
        _field(value, "xa", "phuongXa", "phuong"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _norm_identity(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _same_person(a_id: Any, a_name: Any, b_id: Any, b_name: Any) -> bool:
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _fold(a_name), _fold(b_name)
    return bool(an and bn and an == bn)


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        parts = [p.strip(" .") for p in re.split(r"[,;\n-]+", value) if p.strip(" .")]
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
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _area_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    changed = True
    prefixes = ("Thành phố", "Tỉnh", "Thị trấn", "Thị xã", "Phường", "Xã", "Huyện", "Quận", "TP.")
    while changed:
        changed = False
        norm_text = _fold(text)
        for prefix in prefixes:
            norm_prefix = _fold(prefix)
            if norm_text == norm_prefix:
                return None
            if norm_text.startswith(norm_prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = text.upper().replace("O", "0").replace("S", "5")
    digits = re.sub(r"\D+", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _identity(value: Any) -> str | None:
    digits = _norm_identity(value)
    return digits or None


def _issuer(place: Any, issue_date: Any) -> str | None:
    normalized = normalize_issuer(place)
    if normalized:
        return normalized
    d = normalize_date(str(issue_date)) if issue_date else ""
    return default_issuer(d) if d else None


def _person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = normalize_date(values.get(f"{prefix}_NgayCap"))
    return Person(
        name=name,
        identity=identity,
        birthday=normalize_date(values.get(f"{prefix}_NgaySinh")),
        issue_date=issue_date,
        issuer=_issuer(values.get(f"{prefix}_NoiCap"), issue_date),
        residence=values.get(f"{prefix}_NoiCuTru"),
        phone=_phone(values.get(f"{prefix}_DienThoai")),
        email=_text(values.get(f"{prefix}_Email")),
        tax=_identity(values.get(f"{prefix}_MaSoThue")),
    )


def _auth_person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = normalize_date(values.get(f"{prefix}_NgayCap"))
    return Person(
        name=name,
        identity=identity,
        issue_date=issue_date,
        issuer=_issuer(values.get(f"{prefix}_NoiCap"), issue_date),
    )


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _pick_requester(values: dict, options: dict | None) -> Person | None:
    context = _form_context(options)
    candidates = [
        _person(values, "Applicant"),
        _auth_person(values, "UyQuyen_BenDuocUyQuyen"),
        _auth_person(values, "UyQuyen_BenUyQuyen"),
        Person(name=values.get("CoSo_NguoiDaiDien")) if values.get("CoSo_NguoiDaiDien") else None,
    ]
    people = [p for p in candidates if p]
    if not people:
        return None
    # Nếu biết tài khoản đăng nhập và khớp ĐÚNG một ứng viên → ưu tiên người đó (chọn đúng người nộp
    # trong hồ sơ nhiều người: chủ cơ sở / người được ủy quyền / đại diện).
    matches = [
        p for p in people
        if _same_person(p.identity, p.name, context.get("applicant_identity"), context.get("applicant_name"))
    ]
    if len(matches) == 1:
        return matches[0]
    # KHÔNG khớp tài khoản (tài khoản đăng nhập khác người trong hồ sơ — vd tài khoản test, hoặc chính
    # chủ chưa liên kết VNeID) → VẪN điền Phần I từ người CHÍNH trong hồ sơ (Applicant/CCCD). Ô Phần I
    # sửa được; nếu cổng đã tự điền từ VNeID thì cũng chỉ ghi đè bằng đúng dữ liệu người nộp. KHÁC #42
    # (cấp lại) bỏ trống khi lệch — ở đây người nộp = chủ cơ sở nên luôn nên điền.
    return people[0]


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


_ORG_MARKERS = ("ho kinh doanh", "cong ty", "chi nhanh", "dia diem kinh doanh", "doanh nghiep",
                "hop tac xa", "htx", "co so", "tnhh", "co phan")


def _looks_organization(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


# Loại hình cơ sở → (checkbox key, cụm mô tả cho nội dung yêu cầu).
_LOAI_HINH = {
    "san_xuat": ("data[CoSoSanXuatChon]", "sản xuất"),
    "kinh_doanh": ("data[CoSoKinhDoanh]", "kinh doanh"),
    "vua_sx_vua_kd": ("data[CoSoKinhDoanh1]", "vừa sản xuất vừa kinh doanh"),
    "chuoi": ("data[ChuoiCoSo]", "chuỗi cơ sở kinh doanh thực phẩm"),
}


def _loai_hinh_key(value: Any) -> str:
    f = _fold(value)
    if "chuoi" in f:
        return "chuoi"
    if "vua" in f or ("san xuat" in f and "kinh doanh" in f):
        return "vua_sx_vua_kd"
    if "kinh doanh" in f:
        return "kinh_doanh"
    if "san xuat" in f:
        return "san_xuat"
    return ""


_DINH_KEM_DEFAULT = (
    "1. Đơn đề nghị cấp Giấy chứng nhận (Mẫu 01a); "
    "2. Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ (Mẫu 02a/02b); "
    "3. Bản sao Giấy chứng nhận đăng ký kinh doanh/doanh nghiệp; "
    "4. Giấy xác nhận tập huấn kiến thức an toàn thực phẩm; "
    "5. Danh sách/Giấy xác nhận đủ sức khỏe."
)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None, default: bool = False) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
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
        seen.add(seen_key)

    def add_area(province_name, ward_name, address_name, area, *, occurrence=None) -> None:
        if not area:
            return
        add(province_name, _area_label(area.get("tinh")), occurrence=occurrence)
        add(ward_name, _area_label(area.get("xa")))
        add(address_name, _text(area.get("diaChi")), occurrence=occurrence)

    # === Facts cơ sở SXKD (chủ hồ sơ) — tính trước để Phần I dùng làm fallback ===
    coso_name = _text(values.get("CoSo_Ten"))
    coso_is_to_chuc = _looks_organization(values.get("CoSo_LoaiChuThe"), coso_name)
    coso_ma = _identity(values.get("CoSo_MaSo"))
    coso_id_chu = _identity(values.get("CoSo_SoDinhDanhChuCoSo"))
    coso_phone = _phone(values.get("CoSo_DienThoai"))
    coso_area = _area(values.get("CoSo_DiaChi"))
    coso_diachi_full = _full_address(values.get("CoSo_DiaChi"))

    # === Phần I: TÀI KHOẢN NỘP HỒ SƠ (occurrence 0 cho key trùng) ===
    requester = _pick_requester(values, options)
    if requester:
        add("data[fullname]", _text(requester.name))
        add("data[identityNumber]", _identity(requester.identity))
        add("data[identityDate]", requester.issue_date)
        add("data[birthday]", requester.birthday)
        # Điện thoại tài khoản (bắt buộc): CCCD không in SĐT → fallback SĐT cơ sở khi người nộp là chủ cơ sở.
        add("data[phoneNumber]", requester.phone or coso_phone, occurrence=0)
        add("data[email]", requester.email)
        add("data[taxCode]", requester.tax)
        add_area("data[province]", "data[district]", "data[address]", _area(requester.residence), occurrence=0)
    else:
        warnings.append("Không xác định được người nộp (CCCD/ủy quyền) — Phần I có thể để trống.")

    if not coso_name:
        warnings.append("Không đọc được tên cơ sở sản xuất, kinh doanh.")

    # === Phần II: CHỦ HỒ SƠ (bỏ tích isOwnerDossier, điền cơ sở tường minh) ===
    add("data[isOwnerDossier]", False)
    add("data[ownerFullname]", coso_name)
    if coso_is_to_chuc:
        add("data[ownertaxCode]", coso_ma)
    else:
        add("data[ownerIdentityNumber]", coso_id_chu or coso_ma)
    add("data[ownerPhoneNumber]", coso_phone)
    add("data[ownerAddress]", coso_diachi_full)

    # === Phần III: ĐƠN ĐỀ NGHỊ (header) ===
    add("data[noiLapDon]", _area_label(values.get("Don_DiaDanh")))
    # Ngày lập đơn = ngày ghi trên Đơn 01a (khớp bản giấy đã ký); thiếu → ngày hôm nay (server).
    add("data[ngayLap]", normalize_date(values.get("Don_NgayLap")) or date.today().strftime("%d/%m/%Y"))
    add("data[KinhGui]", _text(values.get("Don_KinhGui")))

    # === Phần IV: CƠ SỞ SXKD (occurrence 1 cho key trùng) ===
    add("data[organization]", coso_name)
    add_area("data[province]", "data[village]", "data[address]", coso_area, occurrence=1)
    add("data[phoneNumber]", coso_phone, occurrence=1)
    add("data[nganhNghe]", _text(values.get("CoSo_NganhNghe")))

    # === Phần V: LOẠI HÌNH CƠ SỞ (tích đúng 1 checkbox) ===
    loai = _loai_hinh_key(values.get("Don_LoaiHinh"))
    loai_desc = ""
    if loai:
        key, loai_desc = _LOAI_HINH[loai]
        add(key, True)
        if loai == "chuoi":
            add("data[tencoso11]", _text(values.get("Don_TenChuoi")))

    # Nội dung yêu cầu = "Đề nghị cấp GCN … cho cơ sở [loại hình]: [tên cơ sở]".
    if coso_name:
        noi_dung = "Đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm cho cơ sở"
        if loai_desc:
            noi_dung += f" {loai_desc}"
        noi_dung += f": {coso_name}"
        add("data[noidungyeucaugiaiquyet]", noi_dung)

    # Hồ sơ gửi kèm (textarea, tùy chọn) — danh mục chuẩn để cán bộ đối chiếu nhanh (mặc định vàng).
    add("data[DinhKem]", _DINH_KEM_DEFAULT, default=True)

    return out, warnings
