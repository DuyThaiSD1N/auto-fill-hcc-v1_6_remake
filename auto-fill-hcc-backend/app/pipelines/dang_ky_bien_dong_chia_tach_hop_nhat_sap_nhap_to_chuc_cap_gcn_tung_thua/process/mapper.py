"""Map compact source facts → Form.io data[...] fields cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập
tổ chức..." (1.013977, cổng Đà Nẵng).

Theo mapping của thủ tục:
- data[fullname] / data[birthday] / data[identityNumber]: cổng đổ sẵn từ tài khoản → KHÔNG phát.
- CHỦ HỒ SƠ = tổ chức theo TÊN MỚI (GCN ĐKDN / Đơn Mẫu 18 mục 1) → data[ownerFullname] + data[organization] +
  data[taxCode], data[chonDoiTuong] = loại chủ hồ sơ; email/địa chỉ (trụ sở) lấy của chủ hồ sơ.
- data[isOwnerDossier]: tích khi chủ hồ sơ CÁ NHÂN trùng tài khoản; tổ chức hoặc người khác → bỏ tích.
- data[gender] / data[identityDate] / data[identityAgency] theo NGƯỜI NỘP THỰC TẾ (khớp tài khoản):
  (1) thẻ CCCD khớp tài khoản → (2) giấy ủy quyền mà BÊN ĐƯỢC ỦY QUYỀN khớp tài khoản (ngày cấp, nơi cấp; giấy
  UQ không ghi giới tính → suy từ mã thế kỷ/giới tính trong số định danh 12 số của tài khoản).
- data[phoneNumber]: người nộp là bên được ủy quyền → SĐT trên giấy UQ; không thì SĐT Đơn Mẫu 18 (của tổ chức).
- Địa chỉ: trụ sở ở Đà Nẵng → Tỉnh/TP + Phường/Xã + địa chỉ chi tiết theo trụ sở; trụ sở ngoài Đà Nẵng (cổng
  không chọn được tỉnh khác) → theo mapping, cả ba ô lấy theo ĐỊA CHỈ THỬA ĐẤT (Đà Nẵng); không có thửa đất thì
  ghi đủ địa chỉ trụ sở vào data[address].
- data[noidungyeucaugiaiquyet]: câu khung của cổng ("ÔNG/BÀ: … ĐỀ NGHỊ GIẢI QUYẾT …") điền tên chủ hồ sơ,
  nối thêm nội dung biến động ghi ở Đơn mục 2.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.schema import (
    UI_COMP_BY_NAME,
)

_PROC_TITLE = (
    "Đăng ký biến động thay đổi quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do chia, tách, hợp "
    "nhất, sáp nhập tổ chức hoặc chuyển đổi mô hình tổ chức, chuyển đổi loại hình doanh nghiệp theo quy định "
    "của pháp luật về doanh nghiệp; điều chỉnh quy hoạch xây dựng chi tiết; cấp Giấy chứng nhận cho từng thửa "
    "đất theo quy hoạch xây dựng chi tiết cho chủ đầu tư dự án có nhu cầu"
)

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")
_MOBILE_PREFIX = re.compile(r"^0[35789]\d{8}$")


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


def _same_name(a: Any, b: Any) -> bool:
    key_a = re.sub(r"[^a-z]+", "", _fold(a))
    key_b = re.sub(r"[^a-z]+", "", _fold(b))
    return bool(key_a) and key_a == key_b


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def _province_label(value: Any) -> str | None:
    """Nhãn option select Tỉnh/TP: "Thành phố Đà Nẵng" / "Tỉnh Quảng Nam"."""
    text = " ".join(str(_text(value) or "").split())
    bare = re.sub(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    if not bare:
        return None
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _commune_label(value: Any) -> str | None:
    """Mở rộng viết tắt trên Đơn viết tay: "P. Liên Chiểu" → "Phường Liên Chiểu"."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^p\.\s*", "Phường ", text, flags=re.IGNORECASE)
    text = re.sub(r"^x\.\s*", "Xã ", text, flags=re.IGNORECASE)
    text = re.sub(r"^phường\s+", "Phường ", text, flags=re.IGNORECASE)
    text = re.sub(r"^xã\s+", "Xã ", text, flags=re.IGNORECASE)
    return text


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
    """Parse + mở rộng "P./X." + remap xã/phường cũ (trước sáp nhập) sang đơn vị hiện hành."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or "",
            "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
        }
    else:
        return None
    if not out or not any(out.get(k) for k in ("tinh", "xa", "diaChi")):
        return None
    out["xa"] = _commune_label(out.get("xa")) or ""
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


def _one_phone(value: str) -> str | None:
    digits = re.sub(r"\D+", "", value.upper().replace("O", "0"))
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _phone(value: Any) -> str | None:
    """Đơn hay ghi 2 số (di động + cố định) → ưu tiên số DI ĐỘNG, không có thì lấy số hợp lệ đầu tiên."""
    text = _text(value)
    if not text:
        return None
    parts = re.split(r"[/;,|]|\s-\s|\bvà\b|\bhoặc\b|\s{2,}", text, flags=re.IGNORECASE)
    phones = [p for p in (_one_phone(part) for part in parts) if p]
    if not phones:
        return None
    return next((p for p in phones if _MOBILE_PREFIX.match(p)), phones[0])


def _email(value: Any) -> str | None:
    text = (_text(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) else None


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _gender_from_identity(identity: str | None) -> str | None:
    """Số định danh 12 số: chữ số thứ 4 là mã thế kỷ + giới tính (chẵn = Nam, lẻ = Nữ)."""
    if not identity or len(identity) != 12:
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


def _in_da_nang(area: dict) -> bool:
    return "da nang" in _fold(area.get("tinh"))


def _full_address(area: dict) -> str | None:
    """"600A Điện Biên Phủ, Phường Thạnh Mỹ Tây, Thành phố Hồ Chí Minh" — đủ số nhà, phường/xã, tỉnh."""
    parts = [_text(area.get("diaChi")), _text(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _person_matches(name: str | None, identity: str | None, ctx_name: str | None, ctx_identity: str | None) -> bool:
    """Khớp tài khoản: có số ở cả 2 phía thì so số, không thì so tên."""
    if ctx_identity and identity:
        return identity == ctx_identity
    return bool(ctx_name and name and _same_name(name, ctx_name))


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

    # --- CHỦ HỒ SƠ ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_area = _area(values.get("ChuHoSo_DiaChi"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))
    noi_dung = _text(values.get("NoiDungBienDong"))

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    # NGƯỜI NỘP: thẻ CCCD khớp tài khoản.
    nop_ok = has_ctx and _person_matches(
        _text(values.get("NguoiNop_HoTen")), _identity(values.get("NguoiNop_SoDinhDanh")), ctx_name, ctx_identity
    )
    # BÊN ĐƯỢC ỦY QUYỀN khớp tài khoản → người nộp chính là người được ủy quyền.
    uq_name = _text(values.get("UyQuyen_HoTen"))
    uq_ok = has_ctx and bool(uq_name or values.get("UyQuyen_SoDinhDanh")) and _person_matches(
        uq_name, _identity(values.get("UyQuyen_SoDinhDanh")), ctx_name, ctx_identity
    )

    # Chủ hồ sơ CÁ NHÂN trùng tài khoản → tự nộp.
    self_submit: bool | None = None
    if owner_name and has_ctx:
        if owner_is_tc:
            self_submit = False
        elif ctx_identity and owner_id and len(owner_id) >= 9:
            self_submit = owner_id == ctx_identity
        else:
            self_submit = bool(ctx_name) and _same_name(owner_name, ctx_name)
    elif owner_is_tc:
        self_submit = False

    # --- Chủ hồ sơ ---
    if owner_name:
        add("data[chonDoiTuong]", "Tổ chức" if owner_is_tc else "Cá nhân")
    if self_submit is not None:
        add("data[isOwnerDossier]", self_submit)
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
        add("data[taxCode]", owner_id)

    # --- Nhân thân người nộp (ô không khoá): CCCD khớp tài khoản → giấy ủy quyền khớp tài khoản ---
    gender_guessed = False
    if nop_ok:
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
    if uq_ok:
        add("data[identityDate]", _date(values.get("UyQuyen_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("UyQuyen_NoiCap")))
    if (nop_ok or uq_ok) and "data[gender]" not in seen:
        guessed = _gender_from_identity(ctx_identity)
        add("data[gender]", guessed)
        gender_guessed = bool(guessed)

    # --- Liên hệ: SĐT người được ủy quyền khi họ là người nộp, không thì SĐT Đơn Mẫu 18 ---
    uq_phone = _phone(values.get("UyQuyen_DienThoai")) if uq_ok else None
    add("data[phoneNumber]", uq_phone or owner_phone)
    add("data[email]", _email(values.get("ChuHoSo_Email")))
    # Ô Tỉnh/TP của cổng Đà Nẵng mặc định "Thành phố Đà Nẵng" và không chọn được tỉnh khác (thử "Thành phố Hồ
    # Chí Minh" không lên) → trụ sở ngoài Đà Nẵng thì theo mapping: giữ Tỉnh/TP Đà Nẵng, Phường/Xã + địa chỉ chi
    # tiết lấy theo THỬA ĐẤT. Không đọc được thửa đất ở Đà Nẵng thì ghi đủ địa chỉ trụ sở vào ô chi tiết.
    owner_outside_dn = bool(owner_area) and not _in_da_nang(owner_area)
    land_area = _area(values.get("ThuaDat_DiaChi"))
    if land_area and not (_in_da_nang(land_area) and land_area.get("xa")):
        land_area = None
    area_source = "owner"
    if owner_area and not owner_outside_dn:
        area = owner_area
    elif land_area:
        area, area_source = land_area, "land"
    else:
        area = None
    if area:
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    elif owner_outside_dn:
        add("data[address]", _full_address(owner_area))

    if owner_name:
        request = f"ÔNG/BÀ: {owner_name} ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}"
        if noi_dung:
            request += f". Nội dung biến động: {noi_dung}"
        add("data[noidungyeucaugiaiquyet]", request)

    # --- Cảnh báo ---
    if not owner_name:
        warnings.append("Không đọc được tên chủ hồ sơ (tổ chức theo tên mới) từ Đơn Mẫu 18 / GCN đăng ký doanh "
                        "nghiệp — vui lòng nhập tay.")
    if owner_is_tc and not owner_id:
        warnings.append("Chưa có mã số doanh nghiệp của chủ hồ sơ (GCN đăng ký doanh nghiệp / Đơn mục 1b) — vui "
                        "lòng nhập tay ô Mã định danh tổ chức.")
    if not (uq_phone or owner_phone):
        warnings.append("Không tìm thấy số điện thoại (giấy ủy quyền / Đơn Mẫu 18) — bắt buộc, vui lòng nhập tay.")
    if owner_outside_dn and area_source == "land":
        warnings.append(f"Trụ sở chủ hồ sơ ngoài Đà Nẵng ({_full_address(owner_area)}) — cổng không chọn được "
                        "tỉnh khác nên Tỉnh/TP, Phường/Xã, địa chỉ chi tiết điền theo địa chỉ thửa đất.")
    elif owner_outside_dn:
        warnings.append("Trụ sở chủ hồ sơ ngoài Đà Nẵng và không đọc được địa chỉ thửa đất — đã ghi đủ địa chỉ trụ "
                        "sở vào ô Địa chỉ chi tiết; ô Phường/Xã (bắt buộc) vui lòng tự chọn.")
    if owner_name and not owner_area:
        warnings.append("Không đọc được địa chỉ trụ sở chủ hồ sơ trên Đơn Mẫu 18 — vui lòng chọn Tỉnh/TP, "
                        "Phường/Xã và nhập địa chỉ chi tiết.")
    if owner_name and not noi_dung:
        warnings.append("Không đọc được mục 2 'Nội dung biến động' trên Đơn — Nội dung yêu cầu chỉ có câu khung.")
    if not has_ctx:
        warnings.append(
            "Không đọc được tài khoản đang đăng nhập trên form — chưa điền giới tính, ngày cấp, nơi cấp của người nộp."
        )
    elif not (nop_ok or uq_ok):
        warnings.append(
            "Hồ sơ không có CCCD hay giấy ủy quyền khớp tài khoản người nộp — vui lòng tự nhập giới tính, ngày "
            "cấp, nơi cấp."
        )
    if gender_guessed:
        warnings.append("Giới tính người nộp suy từ số định danh của tài khoản (hồ sơ không có thẻ CCCD) — kiểm "
                        "tra lại.")
    if self_submit is False and not uq_name:
        warnings.append(
            "Người nộp (tài khoản) khác chủ hồ sơ — nếu không phải người đại diện theo pháp luật thì cần đính kèm "
            "Văn bản về việc đại diện / giấy ủy quyền (dòng 3)."
        )
    elif uq_name and has_ctx and not uq_ok:
        warnings.append(
            f"Bên được ủy quyền trên giấy ủy quyền ({uq_name}) khác tài khoản đang nộp — kiểm tra lại tư cách "
            "người nộp."
        )

    return out, warnings
