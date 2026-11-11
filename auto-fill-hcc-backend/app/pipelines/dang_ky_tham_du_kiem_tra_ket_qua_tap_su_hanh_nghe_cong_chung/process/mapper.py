"""Map compact facts sang eForm "GIẤY ĐĂNG KÝ THAM DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG" (Mẫu TP-TSCC-10,
tokhaidientu.moj.gov.vn).

- Nhân thân: cổng đổ sẵn theo tài khoản VNeID; ghi đè bằng dữ liệu giấy tờ và cảnh báo khi tài khoản đăng nhập không
  phải người tập sự. Nơi cấp: thẻ cấp từ 01/7/2024 là Thẻ căn cước do Bộ Công an cấp.
- Quyết định công nhận: số/ngày/Sở Tư pháp lấy trên chính Quyết định, thiếu thì theo dòng khai trên Giấy đăng ký; hai
  nguồn lệch số hoặc ngày thì cảnh báo.
- Ba dropdown tỉnh của eForm dùng HAI danh mục chữ khác nhau (LamTai là danh mục cũ) → chọn đúng chữ option.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, default_issuer, id_doc_type, normalize_issuer
from app.pipelines.dang_ky_nuoi_con_nuoi_trong_nuoc.process.mapper import (
    _area,
    _by_name,
    _clean,
    _date,
    _digits,
    _fold,
    _upper_name,
)
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.schema import (
    LAM_TAI_OPTIONS,
    UI_COMP_BY_NAME,
)

_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_DEFAULT_KINH_GUI = "Bộ Tư pháp"
# Chữ in sẵn của mẫu mà LLM hay chép lẫn vào giá trị.
_KY_PREFIX = re.compile(r"^\(?\s*k[ỳy]\s+ki[ểe]m\s+tra\s+k[ếe]t\s+qu[ảa]\s+t[ậa]p\s+s[ựu]\s+h[àa]nh\s+ngh[ềe]\s+"
                        r"c[ôo]ng\s+ch[ứu]ng\s*", re.IGNORECASE)
_SO_PREFIX = re.compile(r"^\s*s[ởo]\s+t[ưu]\s+ph[áa]p\s+", re.IGNORECASE)
_PROVINCE_PREFIX = re.compile(r"^(t[ỉi]nh\s+)?(th[àa]nh\s+ph[ốo]\s+)?", re.IGNORECASE)


def _keep_text(value: Any) -> str:
    """Chép nguyên văn: chỉ gom khoảng trắng, bỏ dấu ';' / ',' / ':' thừa ở hai đầu, giữ dấu chấm cuối."""
    return re.sub(r"\s+", " ", str(value or "")).strip(" ;,:")


def _gender(value: Any) -> str:
    text = _fold(value)
    if text in {"nam", "male", "m", "ong"}:
        return "Nam"
    if text in {"nu", "female", "f", "ba"}:
        return "Nữ"
    return ""


def _date_key(value: str) -> tuple[int, int, int]:
    m = _DATE_RE.match(value or "")
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (0, 0, 0)


def _full_date(value: Any) -> str:
    text = _date(value)
    return text if _DATE_RE.match(text) else ""


def _issuer(issue_date: str, issue_place: Any) -> str:
    # Thẻ cấp từ 01/7/2024 luôn do Bộ Công an cấp; giấy hay ghi nhầm "Cục CSQLHC – TTXH BCA".
    if issue_date and _date_key(issue_date) >= (2024, 7, 1):
        return ISSUER_BO_CONG_AN
    place = re.sub(r"\(\s*đối với.*$", "", str(issue_place or ""), flags=re.IGNORECASE)
    return normalize_issuer(place) or (default_issuer(issue_date) if issue_date else "")


def _province_core(value: Any) -> str:
    """Tên tỉnh/thành không tiền tố hành chính, đã bỏ dấu — để so giữa các danh mục option."""
    return _PROVINCE_PREFIX.sub("", _fold(_clean(value))).strip()


def _province_name(value: Any) -> str:
    """"Sở Tư pháp tỉnh Khánh Hòa" / "TP. Huế" / "Khánh Hòa" → tên tỉnh chuẩn ("Khánh Hòa")."""
    text = _SO_PREFIX.sub("", _clean(value))
    return canonical_province(text) or canonical_province(_clean(value)) or ""


def _new_province_label(value: Any) -> str:
    name = _province_name(value)
    return (province_label(name) or "") if name else ""


def _lam_tai(value: Any) -> str:
    name = _province_name(value)
    if not name:
        return ""
    core = _province_core(name)
    return next((opt for opt in LAM_TAI_OPTIONS if _province_core(opt) == core), "")


def _decision(value: Any) -> dict:
    raw = value if isinstance(value, dict) else {}
    number = re.sub(r"\s*/\s*", "/", _clean(raw.get("so")))
    number = re.sub(r"^s[ốo]\s*:?\s*", "", number, flags=re.IGNORECASE)
    return {
        "so": number,
        "ngay": _full_date(raw.get("ngay")),
        "tinh": _province_name(raw.get("tinh")),
    }


def _same_number(left: str, right: str) -> bool:
    fold = lambda s: re.sub(r"[^a-z0-9]", "", _fold(s))  # noqa: E731
    return fold(left) == fold(right)


def _address(value: Any) -> dict | None:
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value.get("chiTietDuoiXa")}
    return _area(value)


def _title_name(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:].lower() for word in value.split())


def _ky_kiem_tra(value: Any) -> str:
    text = _keep_text(value)
    text = _KY_PREFIX.sub("", text).strip(" ()")
    return text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    context = (options or {}).get("formContext") or {}
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    add("KyKiemTra", _ky_kiem_tra(values.get("KyKiemTra")))
    kinh_gui = _keep_text(values.get("KinhGui"))
    add("KinhGui", kinh_gui or _DEFAULT_KINH_GUI, default=not kinh_gui)

    # ---- Nhân thân người tập sự.
    name = _clean(values.get("Ndn_HoTen"))
    id_number = _digits(values.get("Ndn_SoDinhDanh"))
    issue_date = _full_date(values.get("Ndn_NgayCap"))
    issuer = _issuer(issue_date, values.get("Ndn_NoiCap"))
    add("HoVaTenC", _upper_name(name))
    add("GioiTinhC", _gender(values.get("Ndn_GioiTinh")))
    add("NgaySinhC", _full_date(values.get("Ndn_NgaySinh")))
    if id_number:
        add("LoaiGiayToDinhDanhC", id_doc_type(_clean(values.get("Ndn_LoaiGiayTo")) or "Căn cước công dân", issuer))
        add("SoDinhDanhC", id_number)
    add("NgayCapDDC", issue_date)
    add("NoiCapDDC", issuer)

    living = _address(values.get("Ndn_NoiOHienTai"))
    if living:
        add("NO_TinhThanhC", living["tinh"])
        add("NO_PhuongXaC", living["xa"])
        add("NO_SoNhaToDanPhoC", living["diaChi"])
    add("SoDienThoai", _digits(values.get("Ndn_DienThoai")))
    add("Email", _clean(values.get("Ndn_Email")).replace(" ", ""))

    account_name = _clean(context.get("applicantFullname"))
    account_id = _digits(context.get("applicantIdentityNumber"))
    if name and account_name and (
        _fold(account_name) != _fold(name) or (account_id and id_number and account_id != id_number)
    ):
        warnings.append(
            f"Tài khoản đang đăng nhập ({account_name}) không phải người tập sự ({_upper_name(name)}) — phần nhân thân "
            "đã ghi đè theo giấy tờ; nên nộp bằng tài khoản VNeID của chính người tập sự."
        )
    if not name:
        warnings.append("Không đọc được họ tên người tập sự từ hồ sơ — vui lòng kiểm tra phần nhân thân.")

    # ---- Quá trình tập sự.
    add("ToChucTapSu", _keep_text(values.get("TapSu_ToChuc")))
    add("CongChungVienHuongDan", _keep_text(values.get("TapSu_CongChungVien")))
    start = _full_date(values.get("TapSu_TuNgay"))
    end = _full_date(values.get("TapSu_DenNgay"))
    add("NgayBatDauTapSu", start)
    add("NgayKetThucTapSu", end)
    if start and end and _date_key(start) >= _date_key(end):
        warnings.append(f"Thời gian tập sự từ {start} đến {end} không hợp lệ — vui lòng kiểm tra lại hai ngày.")
    months = _digits(values.get("TapSu_SoThang"))
    if months and months != "12":
        warnings.append(f"Giấy đăng ký ghi thời gian tập sự {months} tháng, eForm in sẵn 12 tháng — vui lòng soát lại.")

    # ---- Quyết định công nhận hoàn thành tập sự.
    decision = _decision(values.get("QD_CongNhan"))
    declared = _decision(values.get("DK_QuyetDinh"))
    add("SoQuyetDinhCongNhan", decision["so"] or declared["so"])
    add("NgayQuyetDinhCongNhan", decision["ngay"] or declared["ngay"])
    add("SoTuPhapCongNhan", _new_province_label(decision["tinh"] or declared["tinh"]))
    if decision["so"] and declared["so"] and not _same_number(decision["so"], declared["so"]):
        warnings.append(f"Số quyết định công nhận hoàn thành tập sự lệch giữa Quyết định ({decision['so']}) và Giấy "
                        f"đăng ký ({declared['so']}) — đã điền theo Quyết định, vui lòng xác minh.")
    if decision["ngay"] and declared["ngay"] and decision["ngay"] != declared["ngay"]:
        warnings.append(f"Ngày quyết định công nhận lệch giữa Quyết định ({decision['ngay']}) và Giấy đăng ký "
                        f"({declared['ngay']}) — đã điền theo Quyết định, vui lòng xác minh.")
    if "SoQuyetDinhCongNhan" not in seen:
        warnings.append("Chưa đọc được số quyết định công nhận hoàn thành tập sự — vui lòng nhập tay.")

    add("DaTungThamDuKyKiemTra", _keep_text(values.get("DaTungThamDu")))

    # ---- Địa danh, ngày làm giấy, người ký.
    made = values.get("LamDon_NoiNgay") if isinstance(values.get("LamDon_NoiNgay"), dict) else {}
    place = _lam_tai(made.get("diaDanh"))
    fallback_place = _lam_tai((living or {}).get("tinh")) or _lam_tai(decision["tinh"] or declared["tinh"])
    add("LamTai", place or fallback_place, default=not place)
    m = _DATE_RE.match(_full_date(made.get("ngay")))
    if m:
        add("Ngay", m.group(1))
        add("Thang", m.group(2))
        add("Nam", m.group(3))
    add("NguoiDeNghiKy", _title_name(name))

    return out, warnings
