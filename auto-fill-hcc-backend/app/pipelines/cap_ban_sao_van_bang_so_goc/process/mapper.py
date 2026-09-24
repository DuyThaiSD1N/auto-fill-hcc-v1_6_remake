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
from app.pipelines._shared.area_remap import remap_area
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


def _huyen_from_ocr(xa: Any, ocr_text: str) -> str | None:
    """Tìm cấp huyện cũ đứng NGAY SAU tên xã trong OCR ("Tuy Lộc, Thành phố Yên Bái, Yên Bái") — dự phòng khi
    LLM bỏ khoá "huyen". Chỉ nhận khi sau đoạn huyện còn ít nhất 1 đoạn (tỉnh), tránh lấy nhầm tên tỉnh."""
    target = _fold(_strip_admin_prefix(xa))
    if not target or not ocr_text:
        return None
    segments = [s.strip() for s in re.split(r"[,\n]", ocr_text)]
    for i, seg in enumerate(segments[:-2]):
        if _fold(_strip_admin_prefix(seg)) == target and segments[i + 1]:
            return segments[i + 1]
    return None


def _remap(area: dict, ocr_text: str = "") -> dict:
    """Địa chỉ CCCD/phiếu hay là địa danh CŨ (trước sáp nhập) → quy về tỉnh/xã hiện hành cho khớp option
    cổng. Khoá "huyen" (cấp huyện cũ) là gợi ý để chọn đúng xã mới khi tên xã trùng ở nhiều huyện."""
    if not area:
        return {}
    base = {
        "quocGia": area.get("quocGia") or "Việt Nam",
        # remap_area không nhận tên tỉnh CŨ có tiền tố ("Tỉnh Yên Bái") → bỏ tiền tố; _province_label thêm lại.
        "tinh": _strip_admin_prefix(area.get("tinh") or area.get("tinhThanh") or ""),
        "xa": area.get("xa") or area.get("phuong") or "",
        "diaChi": area.get("diaChi") or area.get("chiTiet") or "",
    }
    hint = _text(area.get("huyen") or area.get("quanHuyen")) or None
    out = remap_area(dict(base), huyen_hint=hint) or base
    if base["xa"] and not out.get("xa") and not hint:
        # Tên xã trùng ở nhiều huyện → remap bỏ trống xã khi thiếu gợi ý huyện. Thử lấy huyện từ OCR.
        ocr_hint = _huyen_from_ocr(base["xa"], ocr_text)
        if ocr_hint:
            retry = remap_area(dict(base), huyen_hint=ocr_hint) or {}
            if retry.get("xa"):
                out = retry
    return out


def _ten_van_bang(loai: Any) -> str | None:
    """Tên văn bằng cho ô 'Đã được cấp' khi Phiếu không ghi rõ — suy từ loại tốt nghiệp."""
    lf = _fold(loai)
    if not lf:
        return None
    if "bo tuc" in lf:
        return "Bằng tốt nghiệp bổ túc THPT"
    if "thpt" in lf or "trung hoc pho thong" in lf:
        return "Bằng tốt nghiệp THPT"
    if "thcs" in lf or "trung hoc co so" in lf:
        return "Bằng tốt nghiệp THCS"
    return _text(loai)


def _thong_tin_khac(values: dict) -> str | None:
    """Dòng 'Thông tin khác' = tên trường + năm tốt nghiệp (khi Phiếu không có sẵn cụm này)."""
    truong = _text(values.get("VanBang_Truong"))
    nam = _year(values.get("VanBang_KhoaThi")) or _year(values.get("VanBang_NamSinh"))
    parts = [p for p in (truong, nam) if p]
    return ", ".join(parts) or None


def _lien_he(phone: Any, tt: Any) -> str | None:
    """Cụm 'SĐT, email, địa chỉ' khi Phiếu không có sẵn — ghép điện thoại + địa chỉ thường trú."""
    addr = _text(tt)
    parts = [p for p in (_text(phone), addr) if p]
    return ", ".join(parts) or None


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
    # ĐỊA CHỈ chủ: ưu tiên CCCD chủ (địa chỉ HIỆN TẠI). Phiếu BM04 hay ghi địa chỉ LÚC DỰ THI (cũ) →
    # VanBang_ThuongTru chỉ là dự phòng, và bỏ hẳn nếu nó chính là địa chỉ dự thi. Sau đó remap địa danh cũ.
    vb_tt = _area(values.get("VanBang_ThuongTru"))

    def _addr_key(v: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", _fold(_text(v)))

    du_thi = _addr_key(values.get("VanBang_DiaChiDuThi"))
    if vb_tt and du_thi and _addr_key(vb_tt) == du_thi:
        vb_tt = {}
    chu_tt = _remap((_area(chu["tt"]) if chu_cccd_valid else {}) or vb_tt, ocr_text)
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
    p1_tt = _remap(_area(p1.get("tt")), ocr_text)
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

    # ===== Panel "Phieu" (Phiếu đề nghị BM04) — chép gần nguyên văn phiếu =====
    # Form ĐÃ ĐỔI (2026-09): panel granular "Thongtincanhan" cũ bị thay bằng panel "Phieu".
    add("data[Kinhgui]", _text(values.get("Phieu_KinhGui")))
    add("data[ToiTen]", chu_name or org_name)
    add("data[sinhNam]", chu_dob)                          # ô hidden "Sinh ngày" = ngày sinh chủ
    add("data[Sodinhdanh]", chu_id)
    add("data[Duoccap]", _text(values.get("Phieu_TenVanBang")) or _ten_van_bang(values.get("VanBang_LoaiTotNghiep")))
    add("data[do]", _text(values.get("Phieu_CoQuanCapVanBang")))
    add("data[Sohieu]", _text(values.get("Phieu_SoHieu")))
    add("data[requestQty]", _identity(values.get("Phieu_SoLuongBanSao")) or "1")
    check("data[sogoc]", True)                             # thủ tục = cấp BẢN SAO TỪ SỔ GỐC
    add("data[lydo]", _text(values.get("Phieu_LyDo")))
    add("data[thongtinkhac]", _text(values.get("Phieu_ThongTinKhac")) or _thong_tin_khac(values))
    add("data[lienhe]", _text(values.get("Phieu_LienHe")) or _lien_he(chu_phone, chu_tt))
    add("data[ngay]", _date(values.get("Phieu_NgayLap")))
    add("data[nguoidenghi]", _text(values.get("Phieu_NguoiViet")) or chu_name or org_name)

    return out, warnings
