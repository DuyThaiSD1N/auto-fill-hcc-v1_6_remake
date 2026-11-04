"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp CCHN bảo quản, tu bổ, phục hồi di tích.

Mỗi field emit {name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế]}; nhãn LẶP
giữa các khối (Ngày sinh/Ngày cấp/Nơi cấp/Địa chỉ… và cả nhãn Mẫu 51 trùng hai biểu mẫu thủ tục khác) nên
`section` là bắt buộc.

Người nộp theo số CCCD tài khoản đăng nhập (formContext) so với số định danh của người đề nghị:
  - TRÙNG (tự nộp): điền nhân thân vào khối "Thông tin người nộp hồ sơ" (Tên + CMND cổng khoá sẵn).
  - KHÁC (nộp thay): khối người nộp giữ thông tin tài khoản; tích "Thông tin người ủy quyền" rồi điền người đề
    nghị vào khối đó (người ủy quyền = chủ hồ sơ). Chỉ tích khi có đủ tên, số định danh và địa chỉ chi tiết —
    tích mà thiếu ô bắt buộc thì cổng báo đỏ và khoá nút nộp. SĐT không có trên giấy tờ → cảnh báo nhập tay.
  - Không có mốc tài khoản / không đọc đủ số: không đụng hai khối trên, chỉ điền Đơn Mẫu 51.
Đơn Mẫu 51 luôn được điền. Khối biên lai không điền (nhập một ô phải đủ cả 5, hồ sơ không có SĐT/email).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_DIA_CHI_LIEN_HE,
    LABEL_HO_TEN,
    LABEL_HOAT_DONG,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_SINH,
    LABEL_SO_DINH_DANH,
    LABEL_TRINH_DO,
    S_DON,
    S_NOP,
    S_UQ,
    UY_QUYEN_CHECKBOX,
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue", "bac ninh", "quang ninh"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, (dict, list)):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _items(value: Any) -> list[str]:
    """Mảng LLM trả, hoặc chuỗi nhiều dòng → từng mục đã gọn khoảng trắng."""
    if isinstance(value, list):
        raw = [v for v in value if isinstance(v, (str, int, float))]
    elif isinstance(value, str):
        raw = value.splitlines()
    else:
        return []
    return [" ".join(str(v).split()) for v in raw if str(v).strip()]


def _kinh_nghiem(value: Any) -> str | None:
    """Ô trên cổng là input MỘT dòng (trình duyệt xoá ký tự xuống dòng) → các mục a., b.… nối bằng dấu cách."""
    items = _items(value)
    return " ".join(items) or None


def _hoat_dong(value: Any) -> str | None:
    """Từng hoạt động bỏ gạch đầu dòng / dấu chấm cuối, nối bằng "; " cho ô một dòng."""
    items = [re.sub(r"^[-–•+*\s]+", "", item).rstrip(" .;,") for item in _items(value)]
    return "; ".join(item for item in items if item) or None


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value) or "")


def _identity(value: Any) -> str | None:
    """Chỉ nhận số định danh ĐỦ (CMND 9 số / CCCD 12 số) — bản scan bị che chỉ còn vài số đầu thì bỏ."""
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _date(value: Any) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm — chỉ có năm thì bỏ, không ghép 01/01."""
    text = _text(value)
    if not text:
        return None
    normalized = normalize_date(text)
    return normalized if normalized and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


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


def _issuer(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^do\s+|\s+cấp$", "", text, flags=re.IGNORECASE).strip()
    folded = _fold(text)
    return normalize_issuer(text) if ("canh sat" in folded or "cong an" in folded) else text


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
    """Ô 'Địa chỉ hành chính' (mat-select) gộp xã + tỉnh trong một option: 'Phường …, Tỉnh …'."""
    if not area:
        return None
    xa, tinh = _commune_label(area.get("xa")), _province_label(area.get("tinh"))
    return f"{xa}, {tinh}" if xa and tinh else None


def _trinh_do(values: dict) -> str | None:
    """Mục 2 của Đơn; đơn để trống thì ghép từ văn bằng: '<trường> – ngành: <ngành>'."""
    tren_don = _text(values.get("NguoiDeNghi_TrinhDoChuyenMon"))
    if tren_don:
        return tren_don
    truong, nganh = _text(values.get("VanBang_CoSoDaoTao")), _text(values.get("VanBang_Nganh"))
    if truong and nganh:
        return f"{truong} – ngành: {nganh}"
    return f"Ngành: {nganh}" if nganh else truong


def _het_han(value: Any, today: date) -> list[str]:
    """Chứng chỉ có ngày 'đến' đã qua → '<tên> <số> (hết hạn dd/mm/yyyy)'."""
    out: list[str] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        den = _date(item.get("denNgay"))
        if not den:
            continue
        try:
            han = datetime.strptime(den, "%d/%m/%Y").date()
        except ValueError:
            continue
        if han < today:
            ten = " ".join(p for p in (_text(item.get("ten")), _text(item.get("so"))) if p) or "Chứng chỉ hành nghề"
            out.append(f"{ten} (hết hạn {den})")
    return out


def _put(out: list[dict], section: str, label: str, value, comp_by_ui: dict, aliases_by_ui: dict) -> None:
    if value in (None, "", {}, []):
        return
    comp = comp_by_ui.get((section, label))
    if not comp:
        return
    item = {"name": label, "comp": comp, "value": value, "section": section}
    aliases = aliases_by_ui.get((section, label))
    if aliases:
        item["aliases"] = aliases
    out.append(item)


def nguoi_nop_fields(
    ho_ten: str | None, identity: str | None, ngay_sinh: str | None, ngay_cap: str | None, noi_cap: str | None,
    phone: str | None, email: str | None, hanh_chinh: str | None, chi_tiet: str | None, options: dict | None,
) -> tuple[list[dict], list[str]]:
    """Khối "Thông tin người nộp hồ sơ" / "Thông tin người ủy quyền" theo mốc tài khoản — thủ tục cấp lại
    (1.002003) cùng trang liz dùng lại nguyên khối này."""
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        _put(out, section, label, value, COMP_BY_UI, ALIASES_BY_UI)

    ho_ten_hoa = ho_ten.upper() if ho_ten else None
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    tu_nop = bool(ctx_identity and identity and ctx_identity == identity)
    nop_thay = bool(ctx_identity and identity and ctx_identity != identity)

    if tu_nop:
        put(S_NOP, "Ngày sinh", ngay_sinh)
        put(S_NOP, "Ngày cấp", ngay_cap)
        put(S_NOP, "Nơi cấp", noi_cap)
        put(S_NOP, "Số điện thoại", phone)
        put(S_NOP, "Email", email)
        put(S_NOP, "Địa chỉ hành chính", hanh_chinh)
        put(S_NOP, "Địa chỉ chi tiết", chi_tiet)
        thieu = [label for label, value in (
            ("Số điện thoại", phone), ("Email", email),
            ("Địa chỉ hành chính", hanh_chinh), ("Địa chỉ chi tiết", chi_tiet),
        ) if not value]
        if thieu:
            warnings.append(
                "Khối \"Thông tin người nộp hồ sơ\" còn trống ô bắt buộc: " + ", ".join(thieu)
                + " — giấy tờ không ghi, cán bộ nhập tay."
            )
    elif nop_thay:
        thieu_uq = [label for label, value in (
            ("Tên người ủy quyền", ho_ten), ("Số định danh", identity), ("Địa chỉ chi tiết", chi_tiet),
        ) if not value]
        if thieu_uq:
            warnings.append(
                f"Tài khoản đăng nhập ({ctx_name or ctx_identity}) khác người đề nghị nhưng không tích \"Thông tin "
                f"người ủy quyền\" vì thiếu: {', '.join(thieu_uq)} — cán bộ tự tích và nhập theo Đơn Mẫu 51."
            )
        else:
            # Tích TRƯỚC: khối chỉ render sau khi tích, engine dựng lại chỉ mục rồi mới tìm ô bên dưới.
            out.append({"name": UY_QUYEN_CHECKBOX, "comp": "liz-checkbox", "value": True, "section": ""})
            put(S_UQ, "Tên người / Tên đơn vị ủy quyền", ho_ten_hoa)
            put(S_UQ, "Ngày sinh", ngay_sinh)
            put(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", identity)
            put(S_UQ, "Ngày cấp", ngay_cap)
            put(S_UQ, "Nơi cấp", noi_cap)
            put(S_UQ, "Số điện thoại", phone)
            put(S_UQ, "Email", email)
            put(S_UQ, "Địa chỉ hành chính", hanh_chinh)
            put(S_UQ, "Địa chỉ chi tiết", chi_tiet)
            warnings.append(
                f"Tài khoản đăng nhập ({ctx_name or ctx_identity}) khác người đề nghị ({ho_ten}) → coi là nộp thay: "
                "khối \"Thông tin người nộp hồ sơ\" giữ thông tin tài khoản, đã tích \"Thông tin người ủy quyền\" và "
                "điền người đề nghị vào đó."
                + ("" if phone else " Giấy tờ không có số điện thoại — cán bộ nhập Số điện thoại của khối ủy quyền.")
            )
    else:
        ly_do = ("chưa đọc được số CCCD của tài khoản đang đăng nhập" if not ctx_identity
                 else "chưa đọc được đủ số định danh trên Đơn Mẫu 51")
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" / \"Thông tin người ủy quyền\" vì {ly_do} — chỉ điền Đơn "
            "Mẫu 51. Nộp thay thì cán bộ tự tích \"Thông tin người ủy quyền\" và nhập người đề nghị."
        )
    return out, warnings


def enrich(
    fields: list[dict], options: dict | None = None, today: date | None = None,
) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)

    def put(section: str, label: str, value) -> None:
        _put(out, section, label, value, COMP_BY_UI, ALIASES_BY_UI)

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    ho_ten_hoa = ho_ten.upper() if ho_ten else None
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
    noi_cap = _issuer(values.get("NguoiDeNghi_NoiCap"))
    area = _area(values.get("NguoiDeNghi_DiaChiHienNay"))
    chi_tiet = _text(area.get("diaChi")) if area else None
    lien_he = _text(values.get("NguoiDeNghi_DiaChiLienHe"))

    out, warnings = nguoi_nop_fields(
        ho_ten, identity, ngay_sinh, ngay_cap, noi_cap,
        _phone(values.get("NguoiDeNghi_DienThoai")), _email(values.get("NguoiDeNghi_Email")),
        _admin_select(area), chi_tiet, options,
    )

    # ---- Đơn Mẫu 51 ----
    # Số định danh điền số trần như bản cấp lại — không ghép "cấp ngày … do … cấp".
    put(S_DON, LABEL_HO_TEN, ho_ten_hoa)
    put(S_DON, LABEL_SO_DINH_DANH, identity)
    put(S_DON, LABEL_NGAY_SINH, ngay_sinh)
    put(S_DON, LABEL_DIA_CHI_LIEN_HE, lien_he or ", ".join(
        p for p in (chi_tiet, _commune_label(area.get("xa")) if area else None,
                    _province_label(area.get("tinh")) if area else None) if p
    ))
    trinh_do = _trinh_do(values)
    kinh_nghiem = _kinh_nghiem(values.get("NguoiDeNghi_KinhNghiem"))
    hoat_dong = _hoat_dong(values.get("Don_HoatDongDeNghi"))
    put(S_DON, LABEL_TRINH_DO, trinh_do)
    put(S_DON, LABEL_KINH_NGHIEM, kinh_nghiem)
    put(S_DON, LABEL_HOAT_DONG, hoat_dong)

    # ---- Cảnh báo ----
    if raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — không điền, cán bộ đối "
            "chiếu CCCD/VNeID của người đề nghị."
        )
    thieu_don = [label for label, value in (
        ("Trình độ chuyên môn", trinh_do), ("Kinh nghiệm chuyên môn", kinh_nghiem),
        ("Các hoạt động đề nghị cấp chứng chỉ", hoat_dong),
    ) if not value]
    if thieu_don:
        warnings.append(
            "Chưa đọc được nội dung Đơn Mẫu 51: " + ", ".join(thieu_don) + " — cán bộ nhập tay theo đơn."
        )
    het_han = _het_han(values.get("ChungChi_ThoiHan"), today or date.today())
    if het_han:
        warnings.append(
            "Chứng chỉ hành nghề trong hồ sơ đã hết hạn: " + "; ".join(het_han)
            + " — kiểm tra lại điều kiện khoản 2 Điều 72 NĐ 308/2025/NĐ-CP trước khi nộp."
        )
    return out, warnings
