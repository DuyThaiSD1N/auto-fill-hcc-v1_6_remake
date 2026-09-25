"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp thẻ HDV du lịch nội địa.

Mỗi field emit {name=<mat-label>, comp, value, section=<cụm group-header>, aliases=[nhãn thay thế]};
nhãn LẶP giữa các section (Ngày sinh/Ngày cấp/Nơi cấp/Email/Địa chỉ…) nên `section` là bắt buộc.

Phần II "Thông tin người nộp hồ sơ" là của TÀI KHOẢN đang đăng nhập (tên + số định danh cổng tự điền).
Chỉ đổ nhân thân người đề nghị vào đó khi số CCCD tài khoản (formContext) TRÙNG ĐỦ số CCCD trên đơn.
Không trùng / không đọc đủ số / không có formContext → bỏ hẳn Phần II, chỉ điền phần "Cấp thẻ…" bên
dưới. Không điền khối "Thông tin ủy quyền": khối này ẩn tới khi tick ô, engine không thấy ô sẽ rơi về
khớp theo nhãn duy nhất và đổ nhầm ngày sinh/SĐT/địa chỉ của đơn vào Phần II của tài khoản.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    S_NOP,
    S_THE,
)

_LABEL_NGOAI_NGU = "Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế)"
_LABEL_DIEM_DU_LICH = "Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm"

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# LLM hay chép cả câu đề nghị "…cấp thẻ hướng dẫn viên du lịch tại điểm <tên điểm> cho tôi".
_DIEM_PREFIX = re.compile(
    r"^.*?(?:hướng dẫn viên du lịch\s+)?tại điểm\s*[:\-]?\s*", re.IGNORECASE,
)
_DIEM_SUFFIX = re.compile(r"\s*cho tôi\s*[./]*$", re.IGNORECASE)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _ten_diem(value: Any) -> str | None:
    """Tên điểm du lịch — bỏ phần câu đề nghị bị chép kèm; dòng 'Hướng dẫn ghi' in sẵn không phải giá trị."""
    text = _text(value)
    if not text:
        return None
    text = _DIEM_SUFFIX.sub("", _DIEM_PREFIX.sub("", text)).strip(" .:;,-")
    folded = _fold(text)
    if not text or folded.startswith("ten diem du lich") or "doi voi truong hop" in folded:
        return None
    return text


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
    folded = _fold(text)
    return normalize_issuer(text) if ("canh sat" in folded or "cong an" in folded) else text


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


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã|đặc khu)\s+",
        "", text, flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        text = _text(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _is_tourism_major(major: Any) -> bool:
    folded = _fold(major)
    return "du lich" in folded or "lu hanh" in folded


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value, hint: str | None = None) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        item = {"name": label, "comp": comp, "value": value, "section": section}
        aliases = ALIASES_BY_UI.get((section, label))
        if aliases:
            item["aliases"] = aliases
        if hint:
            item["hint"] = hint
        out.append(item)

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
    noi_cap = _issuer(values.get("NguoiDeNghi_NoiCap"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    email = _email(values.get("NguoiDeNghi_Email"))
    area = _area(values.get("NguoiDeNghi_DiaChi"))
    xa = _text(area.get("xa")) if area else None
    tinh = _province_label(area.get("tinh")) if area else None
    dia_chi_chi_tiet = _text(area.get("diaChi")) if area else None

    # ---- Phần II chỉ điền khi CCCD tài khoản đăng nhập TRÙNG CCCD trên đơn ----
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    tu_nop = bool(ctx_identity and identity and ctx_identity == identity)

    if tu_nop:
        put(S_NOP, "Ngày sinh", ngay_sinh)
        put(S_NOP, "Ngày cấp", ngay_cap)
        put(S_NOP, "Nơi cấp", noi_cap)
        put(S_NOP, "Số điện thoại", phone)
        put(S_NOP, "Email", email)
        # Ô hành chính là MỘT mat-select gộp Tỉnh–Xã; gửi tên xã, kèm tỉnh làm gợi ý để engine chọn đúng
        # dòng khi tên xã trùng ở nhiều tỉnh.
        put(S_NOP, "Địa chỉ hành chính", xa or tinh, hint=tinh if xa else None)
        put(S_NOP, "Địa chỉ chi tiết", dia_chi_chi_tiet)

    # ---- Phần IV: nội dung Đơn Mẫu 04 ----
    trinh_do = _text(values.get("NguoiDeNghi_TrinhDoChuyenMon")) or _text(values.get("VanBang_TrinhDo"))
    put(S_THE, "Giới tính", _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_THE, "Trình độ chuyên môn nghiệp vụ", trinh_do)
    put(S_THE, _LABEL_NGOAI_NGU, _text(values.get("NguoiDeNghi_TrinhDoNgoaiNgu")))
    put(S_THE, "Email", email)
    put(S_THE, _LABEL_DIEM_DU_LICH, _ten_diem(values.get("NguoiDeNghi_TenDiemDuLich")))

    # ---- Cảnh báo ----
    if not tu_nop:
        if not ctx_identity:
            ly_do = "chưa đọc được số CCCD của tài khoản đang đăng nhập"
        elif not identity:
            ly_do = "chưa đọc được đủ số CCCD trên Đơn Mẫu 04"
        else:
            ly_do = (
                f"số CCCD tài khoản đang đăng nhập ({ctx_name or ctx_identity}) KHÁC số CCCD của người "
                f"đề nghị cấp thẻ ({ho_ten or 'theo Đơn Mẫu 04'})"
            )
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" vì {ly_do} — khối này giữ thông tin tài khoản, "
            "cán bộ tự kiểm tra Ngày sinh, Số điện thoại, Email, Địa chỉ. Chỉ điền phần \"Cấp thẻ hướng "
            "dẫn viên du lịch\" theo đơn."
        )
    else:
        thieu = [
            label for label, value in (
                ("Số điện thoại", phone), ("E-mail", email),
                ("Địa chỉ hành chính", xa or tinh), ("Địa chỉ chi tiết", dia_chi_chi_tiet),
            ) if not value
        ]
        if thieu:
            warnings.append(
                "Chưa đọc được đầy đủ các ô bắt buộc của khối \"Thông tin người nộp hồ sơ\": "
                f"{', '.join(thieu)} — bản scan có thể bị che/mờ, cán bộ nhập tay theo Đơn Mẫu 04 hoặc CCCD."
            )
    if raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — không điền, cán "
            "bộ đối chiếu CCCD/VNeID của người đề nghị."
        )

    loai_the = _fold(values.get("Don_LoaiThe"))
    if "quoc te" in loai_the or "tai diem" in loai_the:
        warnings.append(
            f"Đơn Mẫu 04 ghi đề nghị cấp thẻ hướng dẫn viên du lịch {values.get('Don_LoaiThe')} — thủ tục "
            "đang chọn là thẻ NỘI ĐỊA. Kiểm tra lại loại thẻ/Dịch vụ công trước khi nộp."
        )
    major = _text(values.get("VanBang_ChuyenNganh"))
    if major and not _is_tourism_major(major) and not _text(values.get("ChungChi_Ten")):
        warnings.append(
            f"Văn bằng chuyên ngành \"{major}\" không phải chuyên ngành hướng dẫn du lịch nên phải nộp "
            "KÈM Chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa — hồ sơ chưa thấy chứng chỉ này."
        )
    return out, warnings
