"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp GCN khóa cập nhật kiến thức HDV du lịch.

Mỗi field emit {name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế], after=[nhãn ô mốc]};
nhãn LẶP giữa các khối (Ngày cấp/Nơi cấp của CCCD người nộp và của thẻ HDV) nên `section` là bắt buộc.

Người nộp theo mốc tài khoản đăng nhập (formContext) so với người đăng ký trên đơn — so SỐ CCCD khi cả hai bên đều đọc
được số thật; đơn để số mẫu/không đọc đủ số thì so HỌ TÊN (bỏ dấu, không phân biệt hoa thường):
  - CÙNG người (tự nộp): điền nhân thân vào khối "Thông tin người nộp hồ sơ" (Tên + CMND cổng khoá sẵn).
  - KHÁC người (nộp thay): khối người nộp giữ thông tin tài khoản; tích "Thông tin người ủy quyền" rồi điền người đăng
    ký vào khối đó. Ô bắt buộc giấy tờ không có (số định danh thật, SĐT…) để TRỐNG cho cổng tô đỏ + cảnh báo.
  - Không có mốc tài khoản / không có gì để so: không đụng hai khối trên, chỉ điền khối "Thông tin đơn đề nghị".

Đơn Mẫu 06 hay là bản điền mẫu (số định danh / điện thoại toàn số 0, email @example.com) → coi như chưa có, cảnh báo.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_ui_date
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.schema import (
    AFTER_BY_UI,
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_GIOI_TINH,
    LABEL_LOAI_THE,
    LABEL_NGAY_BAT_DAU,
    LABEL_NGAY_CAP_THE,
    LABEL_NGAY_KET_THUC,
    LABEL_NGAY_THONG_BAO,
    LABEL_NOI_CAP_THE,
    LABEL_SO_THE,
    LABEL_THONG_BAO_SO,
    S_DON,
    S_NOP,
    S_UQ,
    UY_QUYEN_CHECKBOX,
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# Tên miền dành riêng cho ví dụ (RFC 2606) — đơn điền mẫu hay dùng, không ai nhận thư thật ở đây.
_EMAIL_MAU_RE = re.compile(r"@example\.(com|org|net)$", re.IGNORECASE)
_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue", "bac ninh", "quang ninh"}
_LOAI_THE = (("noi dia", "Nội địa"), ("quoc te", "Quốc tế"), ("tai diem", "Tại điểm"))


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


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value) or "")


def _is_placeholder_digits(digits: str) -> bool:
    """Dãy toàn số 0 (đơn điền mẫu '000000000000') — không phải số thật."""
    return bool(digits) and set(digits) == {"0"}


def _identity(digits: str) -> str | None:
    """Chỉ nhận số định danh ĐỦ (CMND 9 số / CCCD 12 số), bỏ dãy điền mẫu."""
    return digits if len(digits) in (9, 12) and not _is_placeholder_digits(digits) else None


def _date(value: Any) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm; gộp dấu cách thừa quanh dấu phân cách ('22/10 /2026')."""
    text = _text(value)
    if not text:
        return None
    normalized = normalize_ui_date(re.sub(r"\s*([/\-.])\s*", r"\1", text))
    return normalized if isinstance(normalized, str) and re.fullmatch(r"\d{2}/\d{2}/\d{4}", normalized) else None


def _parse(value: str | None) -> date | None:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date() if value else None
    except ValueError:
        return None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    if _is_placeholder_digits(digits):
        return None
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _email(value: Any) -> str | None:
    text = re.sub(r"^e-?mail\s*:?\s*", "", (_text(value) or ""), flags=re.IGNORECASE).replace(" ", "")
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


def _gender(value: Any, identity: str | None) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "m"}:
        return "Nam"
    if folded in {"nu", "female", "f"}:
        return "Nữ"
    # Chữ số thứ 4 của CCCD 12 số mã hoá thế kỷ + giới tính: chẵn = nam, lẻ = nữ.
    if identity and len(identity) == 12:
        return "Nữ" if int(identity[3]) % 2 else "Nam"
    return None


def _loai_the(value: Any) -> str | None:
    folded = _fold(value)
    return next((label for key, label in _LOAI_THE if key in folded), None)


def _so_hieu(value: Any) -> str | None:
    """Số thẻ / số công văn: gộp dấu cách thừa quanh '/' và '-' ('8 /SVHTTDL- QLDL' → '8/SVHTTDL-QLDL')."""
    text = _text(value)
    return re.sub(r"\s*([/\-])\s*", r"\1", text) if text else None


def enrich(
    fields: list[dict], options: dict | None = None, today: date | None = None,
) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    today = today or date.today()
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        item = {"name": label, "comp": comp, "value": value, "section": section}
        aliases = ALIASES_BY_UI.get((section, label))
        if aliases:
            item["aliases"] = aliases
        after = AFTER_BY_UI.get((section, label))
        if after:
            item["after"] = after
        out.append(item)

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
    noi_cap = _issuer(values.get("NguoiDeNghi_NoiCap"))
    raw_phone = _digits(values.get("NguoiDeNghi_DienThoai"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))

    # Email: ô đầu (cạnh Điện thoại) trước; ô đầu là email mẫu @example.* mà đơn còn email thật thì dùng email thật.
    emails = [e for e in (_email(values.get("NguoiDeNghi_Email")), _email(values.get("NguoiDeNghi_EmailKhac"))) if e]
    emails = list(dict.fromkeys(emails))
    that = [e for e in emails if not _EMAIL_MAU_RE.search(e)]
    email = (that or emails or [None])[0]

    area = _area(values.get("NguoiDeNghi_DiaChi"))
    xa = _commune_label(area.get("xa")) if area else None
    tinh = _province_label(area.get("tinh")) if area else None
    hanh_chinh = f"{xa}, {tinh}" if xa and tinh else None
    chi_tiet = _text(area.get("diaChi")) if area else None

    # Ô chi tiết bắt buộc: đơn chỉ ghi tới phường/xã thì ghi lại đủ "<xã>, <tỉnh>" cho khớp ô hành chính vừa chọn, không
    # để chi tiết cũ của tài khoản (có thể thuộc xã khác) nằm cạnh xã mới.
    chi_tiet_dien = chi_tiet or hanh_chinh

    # ---- Người nộp: cùng người với tài khoản đăng nhập (tự nộp) hay nộp thay ----
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(_digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")))
    if ctx_identity and identity:
        cung_nguoi: bool | None = ctx_identity == identity
        so_theo = "số CCCD"
    elif ctx_name and ho_ten:
        cung_nguoi = _fold(ctx_name) == _fold(ho_ten)
        so_theo = "họ tên (đơn chưa có số định danh thật)"
    else:
        cung_nguoi, so_theo = None, ""
    thieu_dia_chi = bool(hanh_chinh and not chi_tiet)

    if cung_nguoi:
        put(S_NOP, "Ngày sinh", ngay_sinh)
        put(S_NOP, "Ngày cấp", ngay_cap)
        put(S_NOP, "Nơi cấp", noi_cap)
        put(S_NOP, "Số điện thoại", phone)
        put(S_NOP, "Email", email)
        put(S_NOP, "Địa chỉ hành chính", hanh_chinh)
        put(S_NOP, "Địa chỉ chi tiết", chi_tiet_dien)
        thieu = [label for label, value in (
            ("Số điện thoại", phone), ("Email", email), ("Địa chỉ hành chính", hanh_chinh),
        ) if not value]
        if thieu:
            warnings.append(
                "Khối \"Thông tin người nộp hồ sơ\" còn trống ô bắt buộc: " + ", ".join(thieu)
                + " — giấy tờ không ghi hoặc ghi giá trị mẫu, cán bộ nhập tay."
            )
    elif cung_nguoi is False:
        # Tích TRƯỚC: khối chỉ render sau khi tích, engine dựng lại chỉ mục rồi mới tìm ô bên dưới.
        out.append({"name": UY_QUYEN_CHECKBOX, "comp": "liz-checkbox", "value": True, "section": ""})
        put(S_UQ, "Tên người / Tên đơn vị ủy quyền", ho_ten.upper() if ho_ten else None)
        put(S_UQ, "Ngày sinh", ngay_sinh)
        put(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", identity)
        put(S_UQ, "Ngày cấp", ngay_cap)
        put(S_UQ, "Nơi cấp", noi_cap)
        put(S_UQ, "Số điện thoại", phone)
        put(S_UQ, "Email", email)
        put(S_UQ, "Địa chỉ hành chính", hanh_chinh)
        put(S_UQ, "Địa chỉ chi tiết", chi_tiet_dien)
        warnings.append(
            f"Tài khoản đăng nhập ({ctx_name or ctx_identity}) khác người đăng ký ({ho_ten or identity}) theo {so_theo} "
            "→ coi là nộp thay: khối \"Thông tin người nộp hồ sơ\" giữ thông tin tài khoản, đã tích \"Thông tin người "
            "ủy quyền\" và điền người đăng ký vào đó."
        )
        thieu = [label for label, value in (
            ("Tên người ủy quyền", ho_ten), ("CMND/Hộ chiếu", identity), ("Số điện thoại", phone),
            ("Email", email), ("Địa chỉ hành chính", hanh_chinh),
        ) if not value]
        if thieu:
            warnings.append(
                "Khối \"Thông tin người ủy quyền\" còn trống ô bắt buộc: " + ", ".join(thieu)
                + " — giấy tờ không ghi hoặc ghi giá trị mẫu, cán bộ nhập tay theo CCCD/đơn của người đăng ký."
            )
    else:
        thieu_dia_chi = False
        ly_do = ("chưa có thông tin tài khoản đang đăng nhập" if not (ctx_name or ctx_identity)
                 else "chưa đọc được họ tên hoặc số định danh trên Đơn Mẫu 06")
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" / \"Thông tin người ủy quyền\" vì {ly_do} — chỉ điền khối "
            "\"Thông tin đơn đề nghị\". Nộp thay thì cán bộ tự tích \"Thông tin người ủy quyền\" và nhập người đăng ký."
        )
    if thieu_dia_chi:
        warnings.append(
            "Địa chỉ liên lạc trên đơn chỉ ghi tới phường/xã — ô \"Địa chỉ chi tiết\" tạm ghi \"" + str(hanh_chinh)
            + "\", cán bộ bổ sung số nhà/đường/thôn nếu có."
        )

    # ---- Khối "Thông tin đơn đề nghị" (Mẫu 06) ----
    loai_the = _loai_the(values.get("The_Loai"))
    so_the = _so_hieu(values.get("The_So"))
    noi_cap_the = _text(values.get("The_NoiCap"))
    noi_cap_the_khac = _text(values.get("The_NoiCapKhac"))
    ngay_cap_the_doc = [d for d in (_date(values.get("The_NgayCap")), _date(values.get("The_NgayCapKhac"))) if d]
    # Ngày cấp thẻ sau hôm nay là số liệu sót/nhầm (thẻ chưa thể được cấp) → lấy ngày hợp lệ đầu tiên.
    ngay_cap_the = next((d for d in ngay_cap_the_doc if (_parse(d) or today) <= today), None)
    thong_bao_so = _so_hieu(values.get("CongVan_So"))
    ngay_thong_bao = _date(values.get("CongVan_Ngay"))
    tu_ngay = _date(values.get("Khoa_TuNgay"))
    den_ngay = _date(values.get("Khoa_DenNgay"))

    put(S_DON, LABEL_LOAI_THE, loai_the)
    put(S_DON, LABEL_GIOI_TINH, _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_DON, LABEL_SO_THE, so_the)
    put(S_DON, LABEL_NOI_CAP_THE, noi_cap_the or noi_cap_the_khac)
    put(S_DON, LABEL_NGAY_CAP_THE, ngay_cap_the)
    put(S_DON, LABEL_THONG_BAO_SO, thong_bao_so)
    put(S_DON, LABEL_NGAY_THONG_BAO, ngay_thong_bao)
    put(S_DON, LABEL_NGAY_BAT_DAU, tu_ngay)
    put(S_DON, LABEL_NGAY_KET_THUC, den_ngay)

    # ---- Cảnh báo ----
    mau = []
    if _is_placeholder_digits(raw_identity):
        mau.append(f"số định danh \"{raw_identity}\"")
    if _is_placeholder_digits(raw_phone):
        mau.append(f"điện thoại \"{raw_phone}\"")
    mau.extend(f"email \"{e}\"" for e in emails if _EMAIL_MAU_RE.search(e))
    if mau:
        warnings.append(
            "Đơn ghi giá trị điền MẪU: " + ", ".join(mau) + " — không dùng các giá trị này; cán bộ nhập số/email thật "
            "của người đăng ký và đính bản đơn đã sửa, đã ký."
        )
    elif raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — cán bộ đối chiếu CCCD/VNeID "
            "của người đăng ký."
        )
    if len(emails) > 1:
        warnings.append(
            f"Đơn ghi hai email khác nhau ({', '.join(emails)}) — đã dùng \"{email}\", cán bộ hỏi lại người đăng ký email "
            "nhận thông báo."
        )
    if noi_cap_the_khac and noi_cap_the and _fold(noi_cap_the_khac) != _fold(noi_cap_the):
        warnings.append(
            f"Dòng thẻ hướng dẫn viên ghi hai nơi cấp (\"{noi_cap_the}\" và \"{noi_cap_the_khac}\") — đã điền nơi cấp "
            "cùng dòng Số thẻ, cán bộ đối chiếu thẻ HDV thật."
        )
    tuong_lai = [d for d in ngay_cap_the_doc if (_parse(d) or today) > today]
    if tuong_lai:
        warnings.append(
            f"Ngày cấp thẻ hướng dẫn viên trên đơn ({', '.join(tuong_lai)}) là ngày trong tương lai — không điền ngày đó"
            + (f", đã điền {ngay_cap_the}" if ngay_cap_the else "") + "; cán bộ đối chiếu thẻ HDV thật."
        )
    elif len(set(ngay_cap_the_doc)) > 1:
        warnings.append(
            f"Dòng thẻ hướng dẫn viên ghi hai ngày cấp ({', '.join(ngay_cap_the_doc)}) — đã điền {ngay_cap_the}, cán bộ "
            "đối chiếu thẻ HDV thật."
        )
    if loai_the == "Tại điểm":
        warnings.append(
            "Đơn đánh dấu thẻ hướng dẫn viên TẠI ĐIỂM — khóa cập nhật kiến thức của thủ tục này dành cho hướng dẫn viên "
            "nội địa và quốc tế, cán bộ kiểm tra lại loại thẻ."
        )
    bat_dau, ket_thuc = _parse(tu_ngay), _parse(den_ngay)
    if bat_dau and ket_thuc and ket_thuc < bat_dau:
        warnings.append(f"Ngày kết thúc khóa ({den_ngay}) trước ngày bắt đầu ({tu_ngay}) — cán bộ kiểm tra lại đơn.")
    thieu_don = [label for label, value in (
        ("Loại thẻ", loai_the), ("Số thẻ", so_the), ("Căn cứ Thông báo số", thong_bao_so),
        ("Ngày thông báo", ngay_thong_bao), ("Ngày bắt đầu", tu_ngay), ("Ngày kết thúc", den_ngay),
    ) if not value]
    if thieu_don:
        warnings.append(
            "Chưa đọc được trên Đơn Mẫu 06: " + ", ".join(thieu_don) + " — cán bộ nhập tay theo đơn."
        )
    kinh_gui = _text(values.get("Don_CoQuanNhan"))
    if kinh_gui:
        warnings.append(
            f"Đơn gửi \"{kinh_gui}\" — ô \"Cơ quan giải quyết\" cổng khoá theo link nộp, kiểm tra đúng Sở này trước "
            "khi nộp."
        )
    return out, warnings
