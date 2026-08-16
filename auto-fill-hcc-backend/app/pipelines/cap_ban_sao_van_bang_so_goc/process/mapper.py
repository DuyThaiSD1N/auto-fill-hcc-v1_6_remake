"""Map compact source facts → Form.io data[...] fields cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc".

ĐỊNH TUYẾN TẤT ĐỊNH theo NEO = tên chủ văn bằng (VanBang_HoTen). Có thể có 2 người: chủ văn bằng vs người
nộp thay (mỗi người 1 CCCD). CCCD khớp tên văn bằng → CHỦ HỒ SƠ; CCCD khác tên → NGƯỜI NỘP (Phần I). Nếu
LLM gán nhầm, mapper HOÁN ĐỔI theo khớp tên (không tin LLM phân nhóm).

- Phần I  Người nộp (flat): từ NguoiNop_* (CCCD người nộp) hoặc tài khoản (formContext).
- Phần II data[ChuHS]: loại chủ hồ sơ.
- Phần III-V data[owner...]: chủ văn bằng (nhân thân từ VĂN BẰNG, CCCD số/ngày cấp/nơi cấp/thường trú khớp tên).
- Phần VIII: nội dung kê khai của CHỦ VĂN BẰNG theo Phiếu BM04.
Nút "Người nộp là chủ hồ sơ" (data[isOwnerDossier]) KHÔNG tick.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    default_issuer,
    normalize_issuer,
)
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_ban_sao_van_bang_so_goc.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    # Bỏ chuỗi dấu chấm điền chỗ trống trên mẫu giấy (vd "......") — DẤU HIỆU Ô TRỐNG, không phải dữ liệu.
    text = " ".join(re.sub(r"[.…]{2,}", " ", text).split()).strip(" .…:;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _same_name(a: Any, b: Any) -> bool:
    fa, fb = _fold(_text(a)), _fold(_text(b))
    return bool(fa and fb and fa == fb)


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


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
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _year(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return m.group(0) if m else None


def _issue_place(value: Any, loai: Any = "", ngay_cap: Any = None) -> str | None:
    """Ô "Nơi cấp giấy tờ tùy thân" chỉ có 2 option: Cục Cảnh sát QLHC về TTXH / Bộ Công an. LLM hay đọc
    nhầm (vd "Công chứng viên" từ dòng công chứng bản sao) → ÉP về đúng 1 trong 2 theo loại giấy tờ + ngày
    cấp. CCCD gắn chip cũ ("Căn cước công dân") → Cục Cảnh sát; thẻ Căn cước mới → Bộ Công an."""
    norm = normalize_issuer(_text(value)) if _text(value) else ""
    if norm in (ISSUER_CUC, ISSUER_BO_CONG_AN):
        return norm
    lf = _fold(loai)
    if "cong dan" in lf or "cccd" in lf:  # "Căn cước công dân" (chip cũ)
        return ISSUER_CUC
    if "the can cuoc" in lf or ("can cuoc" in lf and "cong dan" not in lf):  # thẻ Căn cước mới
        return ISSUER_BO_CONG_AN
    if _text(value) or ngay_cap:  # có tín hiệu nhưng không rõ loại → theo ngày cấp
        return default_issuer(ngay_cap)
    return None


def _id_doc_type_by_len(id_digits: Any) -> str:
    """Loại giấy tờ theo ĐỘ DÀI số định danh: 12 chữ số → Căn cước công dân; 9 → CMND. Khác → '' (không rõ,
    không suy từ nhãn form)."""
    digits = re.sub(r"\D+", "", str(id_digits or ""))
    if len(digits) == 12:
        return "Căn cước công dân"
    if len(digits) == 9:
        return "Chứng minh nhân dân"
    return ""


def _gender(value: Any) -> str | None:
    raw = str(value or "").lower()
    if "nữ" in raw or _fold(value).startswith("nu"):
        return "Nữ"
    if _fold(value).startswith("nam"):
        return "Nam"
    return None


def _area(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _infer_tot_nghiep(ocr_text: str) -> str:
    """Suy loại tốt nghiệp TẤT ĐỊNH từ TÊN văn bằng trong OCR (dự phòng khi LLM bỏ sót)."""
    h = _fold(ocr_text)
    if not h:
        return ""
    if ("tot nghiep" in h) and ("bo tuc" in h or "giao duc thuong xuyen" in h) and (
        "trung hoc pho thong" in h or "thpt" in h
    ):
        return "Bổ túc THPT"
    if "tot nghiep trung hoc pho thong" in h:
        return "THPT"
    if "tot nghiep trung hoc co so" in h:
        return "THCS"
    return ""


def enrich(fields: list[dict], options: dict | None = None, ocr_text: str = "") -> tuple[list[dict], list[str]]:
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

    def check(name: str, on: bool) -> None:
        if on:
            add(name, True)

    # ===== NEO: tên chủ văn bằng (từ chính VĂN BẰNG / BM04) =====
    anchor = _text(values.get("VanBang_HoTen"))

    def _person(prefix: str) -> dict:
        return {
            "name": _text(values.get(f"{prefix}HoTen")),
            "id": _identity(values.get(f"{prefix}SoGiayTo") or values.get(f"{prefix}SoDinhDanh")),
            "dob": _date(values.get(f"{prefix}NgaySinh")),
            "gender": _gender(values.get(f"{prefix}GioiTinh")),
            "ngaycap": _date(values.get(f"{prefix}NgayCap")),
            "noicap": values.get(f"{prefix}NoiCap"),
            "quoctich": _text(values.get(f"{prefix}QuocTich")),
            "phone": _phone(values.get(f"{prefix}DienThoai")),
            "email": _text(values.get(f"{prefix}Email")),
            "tt": _area(values.get(f"{prefix}ThuongTru")),
        }

    # Hai "ứng viên CCCD" LLM trích (cùng cấu trúc để hoán đổi sạch).
    chu = _person("ChuHoSo_")
    nop = _person("NguoiNop_")
    empty = {k: (None if k != "tt" else {}) for k in chu}

    # ĐỊNH TUYẾN TẤT ĐỊNH: CCCD khớp NEO (tên văn bằng) là của chủ; CCCD khác tên là của người nộp.
    if anchor:
        chu_ok = _same_name(chu["name"], anchor)
        nop_ok = _same_name(nop["name"], anchor)
        if not chu_ok and nop_ok:
            chu, nop = nop, chu  # LLM đảo vai → hoán đổi.
        elif not chu_ok and chu["name"] and not nop["name"]:
            # "chủ" LLM trích thực ra là người nộp (CCCD khác tên văn bằng); chủ chưa có CCCD khớp.
            nop = chu
            chu = dict(empty)
            warnings.append("CCCD tải lên không khớp tên chủ văn bằng — coi là CCCD người nộp; chủ hồ sơ "
                            "lấy nhân thân theo văn bằng, số CCCD chủ có thể trống.")

    # Có người nộp thay riêng? (CCCD mang tên KHÁC chủ văn bằng). Quyết định độ tin của CCCD slot "chu".
    distinct_nop = bool(nop.get("name") or nop.get("id"))

    # ===== Nhân thân CHỦ HỒ SƠ: nhân thân ưu tiên VĂN BẰNG (đúng người), CCCD bổ sung/dự phòng =====
    loai = _fold(values.get("ChuHoSo_LoaiChuThe"))
    is_org = "to chuc" in loai or "doanh nghiep" in loai or "co quan" in loai
    is_dn = "doanh nghiep" in loai
    org_name = _text(values.get("ChuHoSo_TenToChuc"))
    tax = _identity(values.get("ChuHoSo_MaSoThue"))
    # CCCD slot "chu" chỉ thuộc CHỦ VĂN BẰNG khi tên khớp NEO; nếu có văn bằng mà tên CCCD khác → CCCD đó là
    # của NGƯỜI KHÁC (người nộp), KHÔNG dùng số/địa chỉ/ngày cấp của nó cho chủ. Không có neo (không văn
    # bằng) mà chỉ 1 người → coi CCCD là của chủ.
    chu_cccd_valid = _same_name(chu["name"], anchor) if anchor else (not distinct_nop)

    chu_name = anchor or (chu["name"] if chu_cccd_valid else None)
    chu_gender = _gender(values.get("VanBang_GioiTinh")) or (chu["gender"] if chu_cccd_valid else None)
    chu_dob = _date(values.get("VanBang_NgaySinh")) or (chu["dob"] if chu_cccd_valid else None)
    # Số/ngày cấp/địa chỉ/điện thoại chủ: ưu tiên BM04 (VanBang_*), rồi tới CCCD chủ (nếu hợp lệ).
    chu_id = _identity(values.get("VanBang_SoGiayTo")) or (chu["id"] if chu_cccd_valid else None)
    chu_ngaycap = _date(values.get("VanBang_NgayCap")) or (chu["ngaycap"] if chu_cccd_valid else None)
    chu_phone = _phone(values.get("VanBang_DienThoai")) or (chu["phone"] if chu_cccd_valid else None)
    chu_quoctich = (_text(chu["quoctich"]) if chu_cccd_valid else None) or "Việt Nam"
    chu_tt = _area(values.get("VanBang_ThuongTru")) or (_area(chu["tt"]) if chu_cccd_valid else {})
    chu_tinh = _province_label(chu_tt.get("tinh") or chu_tt.get("tinhThanh"))
    chu_xa = _text(chu_tt.get("xa") or chu_tt.get("phuong"))
    chu_diachi = _text(chu_tt.get("diaChi") or chu_tt.get("chiTiet"))
    # Loại giấy tờ theo ĐỘ DÀI số định danh (12→CCCD, 9→CMND), KHÔNG tin nhãn form; nơi cấp suy theo đó.
    chu_loai_gt = _id_doc_type_by_len(chu_id) or _text(values.get("VanBang_LoaiGiayTo")) or ""
    chu_noicap = _issue_place((chu["noicap"] if chu_cccd_valid else None), chu_loai_gt or "Căn cước công dân", chu_ngaycap)

    if not (chu_name or org_name):
        warnings.append("Thiếu tên chủ văn bằng (chủ hồ sơ).")

    # ===== TỰ NỘP? Chủ hồ sơ TRÙNG người nộp (khớp tài khoản formContext) và KHÔNG có người nộp thay riêng
    # → tick "Người nộp là chủ hồ sơ", điền Phần I bằng chính CCCD chủ (form tự copy Phần I → chủ hồ sơ). =====
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_id = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    chu_has_ident = bool(chu_id or chu_name)
    chu_matches_ctx = bool((chu_id and ctx_id and chu_id == ctx_id) or _same_name(chu_name, ctx_name))
    self_submit = (not distinct_nop) and (ctx_id or ctx_name) and (chu_matches_ctx or not chu_has_ident)

    # ===== Phần I: NGƯỜI NỘP (tự nộp → lấy chính CCCD chủ; nộp thay → CCCD người nộp) =====
    p1 = chu if self_submit else nop
    p1_tt = _area(p1.get("tt"))
    add("data[chonDoiTuong]", "Cá nhân")
    if self_submit:
        add("data[isOwnerDossier]", True)  # tick → form copy Phần I sang chủ hồ sơ (Phần II-VI).
    add("data[fullname]", _text(p1.get("name")) or (chu_name if self_submit else ctx_name))
    add("data[identityNumber]", p1.get("id") or ctx_id)
    add("data[birthday]", p1.get("dob"))
    add("data[gender]", p1.get("gender"))
    add("data[identityDate]", p1.get("ngaycap"))
    add("data[idIssuePlace]", _issue_place(p1.get("noicap"), chu_loai_gt if self_submit else "", p1.get("ngaycap")))
    add("data[province]", _province_label(p1_tt.get("tinh") or p1_tt.get("tinhThanh")))
    add("data[district]", _text(p1_tt.get("xa") or p1_tt.get("phuong")))
    add("data[address]", _text(p1_tt.get("diaChi") or p1_tt.get("chiTiet")))
    add("data[phoneNumber]", p1.get("phone"))
    add("data[email]", p1.get("email"))

    # ===== Phần II: loại chủ hồ sơ =====
    add("data[ChuHS]", "Doanh nghiệp" if is_dn else ("Tổ chức" if is_org else "Cá nhân"))

    # ===== Phần III-V: CHỦ HỒ SƠ =====
    if is_org:
        add("data[ownerOrganizationFullname]", org_name)
        add("data[ownerTaxCode]", tax)
        if not is_dn:  # Doanh nghiệp ẩn ownerBirthday + ownerIdentityAgency22.
            add("data[ownerBirthday]", chu_dob)
            add("data[ownerIdentityAgency22]", chu_noicap)
    else:
        add("data[ownerFullname]", chu_name)
        add("data[ownerGender]", chu_gender)
        add("data[ownerIdentityNumber]", chu_id)
        add("data[ownerBirthday]", chu_dob)
        add("data[ownerIdentityAgency22]", chu_noicap)
    add("data[ownerIdentityDate]", chu_ngaycap)
    add("data[ownerNation]", chu_quoctich)
    add("data[ownerPhoneNumber]", chu_phone)
    add("data[ownerProvince]", chu_tinh)
    add("data[ownerDistrict]", chu_xa)
    add("data[ownerAddress]", chu_diachi)

    # ===== Phần VIII: NỘI DUNG KÊ KHAI (của CHỦ VĂN BẰNG) =====
    add("data[ToiTen]", chu_name or org_name)
    check("data[Nam]", chu_gender == "Nam")
    check("data[Nu]", chu_gender == "Nữ")
    add("data[ngaySinh]", chu_dob)
    add("data[sinhNam]", _year(values.get("VanBang_NamSinh")) or _year(chu_dob))
    add("data[NoiSinh]", _text(values.get("VanBang_NoiSinh")))
    add("data[DanTocKhaiSinh1]", _text(values.get("VanBang_DanToc")))
    add("data[DaHocLop12]", _text(values.get("VanBang_Truong")))
    truong = _area(values.get("VanBang_TruongDiaChi"))
    add("data[TinhTP]", _province_label(truong.get("tinh") or truong.get("tinhThanh")))
    add("data[PX1]", _text(truong.get("xa") or truong.get("phuong")))

    # Loại tốt nghiệp: LLM → thiếu thì suy TẤT ĐỊNH từ TÊN văn bằng trong OCR.
    tot_nghiep = _fold(values.get("VanBang_LoaiTotNghiep")) or _fold(_infer_tot_nghiep(ocr_text))
    check("data[THPT1]", "bo tuc" in tot_nghiep)
    check("data[THCS]", "trung hoc co so" in tot_nghiep or tot_nghiep.startswith("thcs"))
    check("data[THPT]", "thpt" in tot_nghiep and "bo tuc" not in tot_nghiep and "co so" not in tot_nghiep)

    add("data[KhoaThi]", _text(values.get("VanBang_KhoaThi")))
    add("data[HoiDongThi]", _text(values.get("VanBang_HoiDongThi")))
    add("data[LoaiGiayTo]", chu_loai_gt or None)  # trống nếu không xác định được (không đoán bừa từ nhãn).
    add("data[SoGiayTo]", chu_id)
    add("data[NgayCap]", chu_ngaycap)
    add("data[identityAgency]", chu_noicap)
    add("data[TinhThanhPho]", chu_tinh)
    add("data[QuanHuyen]", chu_xa)
    add("data[SoNhaDuong]", chu_diachi)
    add("data[DienThoai]", chu_phone)
    add("data[requestQty]", _identity(values.get("Phieu_SoLuongBanSao")) or "1")
    add("data[select]", _province_label(values.get("Phieu_NoiLap")))
    add("data[ten1]", _text(values.get("Phieu_NguoiViet")) or chu_name)

    return out, warnings
