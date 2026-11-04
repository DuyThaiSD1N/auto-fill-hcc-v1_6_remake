"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — tổ chức biểu diễn nghệ thuật.

Mỗi field emit {name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế]}; nhãn "Ngày cấp/
Nơi cấp/Số điện thoại/Địa chỉ…" LẶP giữa khối người nộp và khối ủy quyền nên `section` là bắt buộc.

  - Khối "Thông tin người nộp hồ sơ": KHÔNG điền (cổng đổ từ tài khoản định danh; hồ sơ là của tổ chức).
  - Khối "Thông tin người ủy quyền" = tổ chức đề nghị: tích khi đọc được tên + mã số doanh nghiệp đủ 10 số. Ô bắt
    buộc còn trống (SĐT, địa chỉ chi tiết — văn bản đề nghị không ghi) thì cảnh báo nhập tay. Tài khoản đăng nhập
    chính là tổ chức (trùng mã số/tên) thì không tích.
  - Khối đề nghị: luôn điền theo Văn bản đề nghị, thiếu mục thì bù từ Kịch bản. Ô ngày chỉ nhận MỘT ngày → điền ngày
    đầu, nhiều ngày thì cảnh báo.
Khối biên lai không điền (nhập một ô phải đủ cả 5, hồ sơ không có SĐT/email).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_DIA_DIEM,
    LABEL_DUYET_DIA_DIEM,
    LABEL_DUYET_THOI_GIAN,
    LABEL_LIEN_KET,
    LABEL_NGUOI_CHIU_TN,
    LABEL_TAI_LIEU,
    LABEL_TEN_CT,
    LABEL_THOI_GIAN,
    LABEL_TON_VINH,
    S_DN,
    S_UQ,
    UY_QUYEN_CHECKBOX,
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue", "bac ninh", "quang ninh"}
# "20/11/2026", "20-11-2026" | "ngày 20, 21 tháng 11 năm 2026", "ngày 20 đến ngày 22 tháng 11 năm 2026" (đã fold).
_DMY_RE = re.compile(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(?!\d)")
_DAY_LIST_RE = re.compile(
    r"ngay\s+((?:\d{1,2}\s*(?:,|va|-|den|toi)\s*(?:ngay\s+)?)*\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})"
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, (dict, list)):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def _dates(value: Any) -> list[str]:
    """Mọi ngày ĐỦ ngày/tháng/năm trong câu, theo thứ tự xuất hiện, dạng dd/mm/yyyy."""
    text = _fold(value)
    found: list[tuple[int, str]] = []
    for match in _DMY_RE.finditer(text):
        found.append((match.start(), f"{int(match[1]):02d}/{int(match[2]):02d}/{match[3]}"))
    for match in _DAY_LIST_RE.finditer(text):
        for day in re.findall(r"\d{1,2}", match[1]):
            found.append((match.start(), f"{int(day):02d}/{int(match[2]):02d}/{match[3]}"))
    out: list[str] = []
    for _pos, day in sorted(found, key=lambda item: item[0]):
        if day not in out and 1 <= int(day[:2]) <= 31 and 1 <= int(day[3:5]) <= 12:
            out.append(day)
    return out


def _none_text(value: Any) -> str | None:
    """Mục 6 ghi "(Không có)" → "Không có" (bỏ ngoặc bao ngoài)."""
    text = _text(value)
    if text and text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return text or None


def _tai_lieu(value: Any) -> str | None:
    """Từng tài liệu bỏ gạch đầu dòng / dấu chấm cuối, nối bằng "; " — an toàn cả khi ô là input một dòng."""
    raw = value if isinstance(value, list) else str(value or "").splitlines()
    items = [re.sub(r"^[-–•+*\s]+", "", " ".join(str(v).split())).rstrip(" .;,") for v in raw if isinstance(v, str)]
    return "; ".join(item for item in items if item) or None


def _enterprise_code(value: Any) -> str | None:
    """Mã số doanh nghiệp 10 số (đơn vị phụ thuộc thêm "-xxx"); thiếu số thì KHÔNG điền."""
    match = re.fullmatch(r"(\d{10})(?:-?(\d{3}))?", re.sub(r"[\s.]+", "", str(value or "")))
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}" if match.group(2) else match.group(1)


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _email(value: Any) -> str | None:
    text = (_text(value) or "").replace(" ", "")
    return text if _EMAIL_RE.match(text) else None


def _date(value: Any) -> str | None:
    found = _dates(value)
    return found[0] if found else None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tỉnh|thành phố|tp\.?|đặc khu)\s+", "", text, flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if _fold(text).startswith("thanh pho "):
        return text
    bare = _strip_admin_prefix(text)
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    for prefix, label in (("xa ", "Xã"), ("phuong ", "Phường"), ("thi tran ", "Thị trấn"), ("dac khu ", "Đặc khu")):
        if folded.startswith(prefix):
            return f"{label} {_strip_admin_prefix(text)}"
    return f"Xã {text}"


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    # Địa chỉ trước sáp nhập 2025 → đơn vị hiện hành mà danh sách "Địa chỉ hành chính" của cổng có.
    return remap_area(out) or out


def _admin_select(area: dict | None) -> str | None:
    """Ô 'Địa chỉ hành chính' (mat-select) gộp xã + tỉnh trong một option: 'Phường …, Thành phố …'."""
    if not area:
        return None
    xa, tinh = _commune_label(area.get("xa")), _province_label(area.get("tinh"))
    return f"{xa}, {tinh}" if xa and tinh else None


def _put(out: list[dict], section: str, label: str, value) -> None:
    if value in (None, "", {}, []):
        return
    comp = COMP_BY_UI.get((section, label))
    if not comp:
        return
    item = {"name": label, "comp": comp, "value": value, "section": section}
    aliases = ALIASES_BY_UI.get((section, label))
    if aliases:
        item["aliases"] = aliases
    out.append(item)


def _uy_quyen_fields(values: dict, options: dict | None) -> tuple[list[dict], list[str]]:
    """Khối "Thông tin người ủy quyền" = tổ chức đề nghị. Tích TRƯỚC: khối chỉ render sau khi tích."""
    out: list[dict] = []
    warnings: list[str] = []
    name = _text(values.get("DonVi_Ten"))
    code = _enterprise_code(values.get("DonVi_MaSo"))
    seal_code = None if code else _enterprise_code(values.get("DonVi_MaSoConDau"))
    raw_code = _text(values.get("DonVi_MaSo")) or _text(values.get("DonVi_MaSoConDau"))
    phone = _phone(values.get("DonVi_DienThoai"))
    head_office = _area(values.get("DonVi_TruSo"))
    hanh_chinh = _admin_select(head_office)
    chi_tiet = _text(head_office.get("diaChi")) if head_office else None

    ctx =(options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_digits = re.sub(r"\D", "", str(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or ""))
    ma_so = code or seal_code
    if (ma_so and ctx_digits and ctx_digits == ma_so.replace("-", "")) or (
        name and ctx_name and _fold(ctx_name) == _fold(name)
    ):
        warnings.append(
            f"Tài khoản đăng nhập là chính tổ chức đề nghị ({ctx_name or ctx_digits}) — không tích \"Thông tin người "
            "ủy quyền\"."
        )
        return out, warnings

    if not (name and ma_so):
        thieu = [label for label, value in (("Tên tổ chức", name), ("Mã số doanh nghiệp", ma_so)) if not value]
        doc_duoc = f" (đọc được \"{raw_code}\", không đủ 10 số)" if raw_code and not ma_so else ""
        warnings.append(
            "Không tích \"Thông tin người ủy quyền\" vì thiếu: " + ", ".join(thieu) + doc_duoc
            + " — cán bộ tự tích và nhập tổ chức đề nghị theo Giấy chứng nhận đăng ký doanh nghiệp."
        )
        return out, warnings

    out.append({"name": UY_QUYEN_CHECKBOX, "comp": "liz-checkbox", "value": True, "section": ""})
    _put(out, S_UQ, "Tên người / Tên đơn vị ủy quyền", name)
    _put(out, S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", ma_so)
    _put(out, S_UQ, "Ngày cấp", _date(values.get("DonVi_NgayCap")))
    _put(out, S_UQ, "Nơi cấp", _text(values.get("DonVi_NoiCap")))
    _put(out, S_UQ, "Số điện thoại", phone)
    _put(out, S_UQ, "Email", _email(values.get("DonVi_Email")))
    _put(out, S_UQ, "Địa chỉ hành chính", hanh_chinh)
    _put(out, S_UQ, "Địa chỉ chi tiết", chi_tiet)
    if seal_code:
        warnings.append(
            f"Mã số doanh nghiệp {seal_code} đọc từ con dấu (hồ sơ chưa có Giấy chứng nhận đăng ký doanh nghiệp) — "
            "cán bộ đối chiếu lại."
        )
    thieu = [label for label, value in (
        ("Số điện thoại", phone), ("Địa chỉ hành chính", hanh_chinh), ("Địa chỉ chi tiết", chi_tiet),
    ) if not value]
    if thieu:
        warnings.append(
            "Đã tích \"Thông tin người ủy quyền\" và điền tổ chức đề nghị; còn trống: " + ", ".join(thieu)
            + " — giấy tờ không ghi, cán bộ nhập tay (thiếu ô bắt buộc thì cổng khoá nút nộp)."
        )
    return out, warnings


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out, warnings = _uy_quyen_fields(values, options)

    def put(label: str, value) -> None:
        _put(out, S_DN, label, value)

    # ---- Khối đề nghị: Văn bản đề nghị trước, Kịch bản bù khi thiếu ----
    vb_thoi_gian = _text(values.get("DeNghi_ThoiGian"))
    kb_thoi_gian = _text(values.get("KichBan_ThoiGian"))
    vb_ngay, kb_ngay = _dates(vb_thoi_gian), _dates(kb_thoi_gian)
    ngay = vb_ngay or kb_ngay
    ten = _text(values.get("DeNghi_TenChuongTrinh")) or _text(values.get("KichBan_TenChuongTrinh"))
    dia_diem = _text(values.get("DeNghi_DiaDiem")) or _text(values.get("KichBan_DiaDiem"))
    tai_lieu = _tai_lieu(values.get("DeNghi_TaiLieuKemTheo"))

    put(LABEL_TEN_CT, ten)
    put(LABEL_DIA_DIEM, dia_diem)
    put(LABEL_DUYET_THOI_GIAN, _date(values.get("DeNghi_DuyetThoiGian")))
    put(LABEL_DUYET_DIA_DIEM, _text(values.get("DeNghi_DuyetDiaDiem")))
    put(LABEL_NGUOI_CHIU_TN, _text(values.get("DeNghi_NguoiChiuTrachNhiem")))
    put(LABEL_THOI_GIAN, ngay[0] if ngay else None)
    put(LABEL_LIEN_KET, _none_text(values.get("DeNghi_LienKet")))
    put(LABEL_TON_VINH, _none_text(values.get("DeNghi_TonVinh")))
    put(LABEL_TAI_LIEU, tai_lieu)

    # ---- Cảnh báo ----
    if len(ngay) > 1:
        warnings.append(
            f"Thời gian tổ chức \"{vb_thoi_gian or kb_thoi_gian}\" có {len(ngay)} ngày nhưng ô \"Thời gian tổ chức\" "
            f"chỉ nhận một ngày — đã điền ngày đầu {ngay[0]}, cán bộ kiểm tra lại."
        )
    if vb_ngay and kb_ngay and not set(kb_ngay) <= set(vb_ngay):
        warnings.append(
            f"Kịch bản ghi thời gian \"{kb_thoi_gian}\" khác Văn bản đề nghị \"{vb_thoi_gian}\" — đã điền theo Văn bản "
            "đề nghị, cán bộ đối chiếu."
        )
    thieu = [label for label, value in (
        ("Tên chương trình", ten), ("Địa điểm tổ chức", dia_diem), ("Thời gian tổ chức", ngay),
        ("Tài liệu kèm theo", tai_lieu),
    ) if not value]
    if thieu:
        warnings.append("Chưa đọc được: " + ", ".join(thieu) + " — cán bộ nhập tay theo Văn bản đề nghị.")
    kinh_gui = _text(values.get("DeNghi_KinhGui"))
    if kinh_gui:
        warnings.append(
            f"Văn bản đề nghị gửi \"{kinh_gui}\" — ô \"Cơ quan giải quyết\" cổng khoá theo link nộp, kiểm tra đúng Sở "
            "này trước khi nộp."
        )
    return out, warnings
