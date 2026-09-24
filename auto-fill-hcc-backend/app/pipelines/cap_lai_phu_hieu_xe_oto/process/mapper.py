"""Map compact source facts → Form.io data[...] fields cho "Cấp, cấp lại Phù hiệu cho xe ô tô, xe bốn bánh có
gắn động cơ kinh doanh vận tải" (TTHC 2.002288).

- Phần I   Người nộp (data[...] phẳng): CHỈ khi có CCCD người nộp; không có → để tài khoản VNeID tự đổ. Ô "Số
           điện thoại" BẮT BUỘC mà tài khoản không đổ → lấy SĐT người nộp, không có thì SĐT đơn vị KDVT.
- Phần II  Doanh nghiệp của người nộp + Phần IV Đơn vị KDVT: cùng một đơn vị (Giấy đề nghị → HĐ → GCN/GPKDVT).
- Phần III Giấy đề nghị: số văn bản, tại (tỉnh), ngày, kính gửi, dịch vụ (suy từ loại phù hiệu).
- Phần V   Thẩm định: số lượng nộp lại (ô chỉ nhận số: "Không" → 0), đề nghị được cấp.
- Phần VI-VII Phương tiện: phát nút dom-click "Thêm phương tiện" rồi các ô panel của xe ĐẦU TIÊN (panel chỉ
           nhập một xe mỗi lần). Chủ xe khác đơn vị KDVT → radio "Xe thuê/xe hợp tác kinh doanh/xe của thành
           viên HTX" + khối hợp đồng; trùng → radio "Xe thuộc sở hữu của ĐVKDVT" + khối đăng ký xe.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_phu_hieu_xe_oto.process.schema import UI_COMP_BY_NAME

_DV = "data[T_DonViKinhDoanh]"
_GP = f"{_DV}[HoatDongKinhDoanh][GiayCapPhepKinhDoanh]"
_PT = "data[ThamDinh][ThemPhuongTienRaw]"

# Nhãn 2 radio "THÔNG TIN NGƯỜI SỞ HỮU" đúng như web (FE khớp theo nhãn).
_RADIO_SO_HUU = "Xe thuộc sở hữu của ĐVKDVT"
_RADIO_THUE = "Xe thuê/xe hợp tác kinh doanh/xe của thành viên HTX"

# Option "Loại hình cho thuê" đúng như web.
_CHO_THUE = {
    "thanh_vien_htx": "Xe của thành viên HTX",
    "thue": "Xe thuê",
    "hop_tac": "Xe hợp tác kinh doanh",
}

_DICH_VU_TAI = "Xe ô tô tải kinh doanh vận tải hàng hóa thông thường và xe taxi tải"
_KD_HANG_HOA = "Kinh doanh vận tải hàng hóa bằng xe ô tô"

# Danh mục "Nước sản xuất" của cổng dùng tên TIẾNG ANH. "Viet" khớp cả "Vietnam" lẫn "Viet Nam".
_NUOC_SX = {
    "viet nam": "Viet",
    "han quoc": "Korea",
    "nhat ban": "Japan",
    "trung quoc": "China",
    "thai lan": "Thailand",
    "duc": "Germany",
    "my": "United States",
    "hoa ky": "United States",
    "nga": "Russia",
    "an do": "India",
    "phap": "France",
    "y": "Italy",
    "thuy dien": "Sweden",
    "ha lan": "Netherlands",
    "indonesia": "Indonesia",
    "malaysia": "Malaysia",
}

# Tiền tố loại hình trong tên đơn vị — bỏ khi so tên chủ xe với tên đơn vị KDVT.
_ORG_PREFIX = re.compile(
    r"\b(hop tac xa|htx|dich vu|dv|cong ty|cty|co phan|cp|tnhh|mtv|mot thanh vien|doanh nghiep tu nhan|dntn|"
    r"ho kinh doanh|hkd|van tai|kinh doanh)\b"
)


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
    # Chuỗi dấu chấm điền chỗ trống trên mẫu ("......") là Ô TRỐNG, không phải dữ liệu.
    text = " ".join(re.sub(r"[.…]{2,}", " ", text).split()).strip(" .…:;,-")
    return text or None


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    for k in keys:
        v = _text(item.get(k))
        if v:
            return v
    return None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _place_name(value: str) -> str:
    """Địa danh IN HOA trên văn bản ('QUẢNG TRỊ') → 'Quảng Trị' như option web."""
    return value.title() if value.isupper() else value


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _place_name(_strip_admin_prefix(text))
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _one_phone(text: str) -> str | None:
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _phone(value: Any) -> str | None:
    """Giấy tờ hay ghi nhiều số ('0912.345.678 - 0987.654.321') → lấy số ĐẦU TIÊN hợp lệ."""
    text = _text(value)
    if not text:
        return None
    for part in re.split(r"\s+[-–]\s+|[,;/]|\bvà\b", text):
        phone = _one_phone(part)
        if phone:
            return phone
    return _one_phone(text)


def _phone_read(value: Any) -> tuple[str | None, bool]:
    """(số điện thoại, đủ chữ số?). Bản scan che số cuối ('0919.460.') → vẫn trả phần chữ số đọc được của số
    ĐẦU TIÊN để ô không bỏ trắng; complete=False để mapper cảnh báo nhập nốt."""
    full = _phone(value)
    if full:
        return full, True
    text = _text(value)
    if not text:
        return None, False
    first = re.split(r"\s+[-–]\s+|[,;/]|\bvà\b", text)[0]
    return re.sub(r"\D+", "", first) or None, False


def _email(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text.replace(" ", ""))
    return m.group(0) if m else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    if m:
        return normalize_date(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _tax_code(value: Any) -> str | None:
    """MST 10 số (hoặc 13 số kèm mã chi nhánh '-xxx'). Thiếu chữ số (bản scan bị che) → None."""
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\d[\d\s.]*\d(?:\s*-\s*\d{3})?", text)
    if not m:
        return None
    main, _, branch = m.group(0).partition("-")
    main = re.sub(r"\D+", "", main)
    branch = re.sub(r"\D+", "", branch)
    if len(main) != 10:
        return None
    return f"{main}-{branch}" if len(branch) == 3 else main


def _tax_read(value: Any) -> tuple[str | None, bool]:
    """(mã số thuế, đủ 10 số?). Bị che → phần chữ số đọc được, complete=False (như số khung bị che)."""
    full = _tax_code(value)
    if full:
        return full, True
    return _identity(value), False


def _full_token_from_ocr(value: str | None, ocr_text: str) -> str | None:
    """LLM hay cắt hậu tố số văn bản ('…/GĐN-HTX' trong khi giấy ghi '…/GĐN-HTXĐH'). Tìm trong OCR token bắt
    đầu bằng đúng giá trị LLM trả và DÀI hơn → lấy nguyên token."""
    if not value or not ocr_text:
        return value
    want = _fold(value)
    for token in ocr_text.split():
        token = token.strip(" .,;:()")
        folded = _fold(token)
        if len(folded) > len(want) and folded.startswith(want):
            return token
    return value


def _digits(value: Any) -> str | None:
    """'6.750 KG' → '6750'; '02' → '2'; 'Không' → '0'."""
    text = _text(value)
    if not text:
        return None
    if _fold(text) in {"khong", "0", "khong co"}:
        return "0"
    m = re.search(r"\d[\d.,\s]*", text)
    if not m:
        return None
    digits = re.sub(r"\D+", "", m.group(0))
    return str(int(digits)) if digits else None


def _year(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    return years[-1] if years else None


def _plate(value: Any) -> str | None:
    """Biển số theo định dạng giấy tờ ('37C-123.45'); bỏ ký hiệu nhỏ in cạnh như '(V)'/'(T)'."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s*-\s*", "-", text.upper())
    text = re.sub(r"\s*\.\s*", ".", text)
    m = re.search(r"\d{2}[A-Z]{1,2}\d?-(?:\d{3}\.\d{2}|\d{4,5})", text)
    if m:
        return m.group(0)
    text = re.sub(r"\([^)]*\)", "", text)
    return " ".join(text.split()) or None


def _code(value: Any) -> str | None:
    """Số máy / số khung: bỏ khoảng trắng OCR chèn giữa, viết HOA."""
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text).upper() or None


def _so_xay_dung(value: Any) -> str | None:
    """'Sở Xây dựng tỉnh Quảng Trị' → 'Quảng Trị' (option web 'Sở Xây dựng tỉnh …' CHỨA tên tỉnh; FE chấm
    điểm option chứa giá trị). Cục Đường bộ giữ nguyên văn."""
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if "cuc duong bo" in folded:
        return "Cục Đường bộ Việt Nam"
    m = re.search(r"sở\s+(?:xây\s+dựng|giao\s+thông\s+vận\s+tải|gtvt)\s+(.+)$", text, flags=re.IGNORECASE)
    if m:
        return _place_name(_strip_admin_prefix(m.group(1))) or None
    return text


def _loai_hinh_dn(value: Any, ten: str | None) -> str | None:
    f = _fold(value) or _fold(ten)
    if not f:
        return None
    if "hop tac xa" in f or re.search(r"\bhtx\b", f):
        return "Hợp tác xã"
    if "lien doanh" in f:
        return "Công ty liên doanh"
    if "nha nuoc" in f:
        return "Doanh nghiệp nhà nước"
    if "tu nhan" in f or re.search(r"\bdntn\b", f):
        return "Doanh nghiệp tư nhân"
    if "ho kinh doanh" in f or re.search(r"\bhkd\b", f):
        return "Hộ kinh doanh"
    if "cong ty" in f or re.search(r"\b(cty|tnhh|co phan)\b", f):
        return "Công ty Cổ phần, TNHH, TNHH MTV"
    return None


def _dich_vu(loai_phu_hieu: str) -> str | None:
    """Loại phù hiệu (Giấy đề nghị) → option "Dịch vụ". Loại không có option tương ứng (đầu kéo, du lịch…) →
    None để người dùng tự chọn."""
    f = loai_phu_hieu
    if not f:
        return None
    if "tai" in f.split() or "taxi tai" in f:
        return _DICH_VU_TAI
    if "tuyen co dinh" in f or re.search(r"\btuyen cd\b", f):
        return "Xe ô tô theo tuyến cố định"
    if "taxi" in f:
        return "Xe taxi"
    if "buyt" in f:
        return "Xe buýt"
    if "hop dong" in f:
        return "Xe hợp đồng"
    if "trung chuyen" in f:
        return "Xe trung chuyển"
    return None


def _loai_hinh_kd(loai_phu_hieu: str) -> str | None:
    f = loai_phu_hieu
    if not f:
        return None
    if "tai" in f.split() or "dau keo" in f or "container" in f or "cho hang" in f:
        return _KD_HANG_HOA
    if "tuyen co dinh" in f:
        return "Kinh doanh vận tải hành khách theo tuyến cố định"
    if "taxi" in f:
        return "Kinh doanh vận tải hành khách bằng xe taxi"
    if "buyt" in f:
        return "Kinh doanh vận tải hành khách công cộng bằng xe buýt"
    if "hop dong" in f or "du lich" in f:
        return "Kinh doanh vận tải hành khách theo hợp đồng"
    return None


def _loai_phuong_tien(loai_xe: str, loai_phu_hieu: str, so_cho: str | None) -> str | None:
    """Loại xe (Chứng nhận đăng ký) → option "Loại phương tiện". Xét 'tải' TRƯỚC 'chuyên dùng' vì giấy đăng ký
    hay ghi 'Tải chở xe máy c.dụng' (xe tải, không phải ô tô chuyên dùng)."""
    f = f"{loai_xe} {loai_phu_hieu}".strip()
    if not f:
        return None
    if "giuong nam" in f:
        return "Ô tô khách có giường nằm"
    if "dau keo" in f:
        return "Ô tô đầu kéo"
    if "container" in f or "cong ten no" in f or "cong-ten-no" in f:
        return "Ô tô chở container"
    if "bon banh" in f:
        return "Xe chở người bốn bánh có gắn động cơ"
    if re.search(r"\btai\b", f):
        return "Ô tô tải"
    if "keo ro mooc" in f or "keo ro-mooc" in f:
        return "Ô tô kéo rơ moóc"
    if "chuyen dung" in f:
        return "Ô tô chuyên dùng"
    if "o to con" in f or re.search(r"\bcon\b", loai_xe):
        return "Ô tô con"
    if "khach" in f or "cho nguoi" in f:
        seats = int(so_cho) if so_cho and so_cho.isdigit() else 0
        return "Ô tô con" if 0 < seats <= 9 else "Ô tô khách"
    return None


def _is_cargo(loai_xe: str, loai_phu_hieu: str) -> bool:
    f = f"{loai_xe} {loai_phu_hieu}"
    return bool(re.search(r"\btai\b", f)) or any(k in f for k in ("dau keo", "container", "cho hang"))


def _org_core(value: Any) -> str:
    return " ".join(_ORG_PREFIX.sub(" ", _fold(value)).split())


def _owned_by_unit(chu_xe: str | None, don_vi: str | None) -> bool | None:
    """Chủ xe trên Chứng nhận đăng ký có phải chính đơn vị KDVT không. None khi thiếu dữ liệu để so."""
    if not chu_xe or not don_vi:
        return None
    a, b = _org_core(chu_xe), _org_core(don_vi)
    if not a or not b:
        return None
    return a == b or a in b or b in a


def _ownership_kind(value: Any) -> str | None:
    f = _fold(value).replace(" ", "_")
    if not f:
        return None
    if "thanh_vien" in f or "xa_vien" in f or "htx" in f:
        return "thanh_vien_htx"
    if "hop_tac" in f:
        return "hop_tac"
    if "thue" in f:
        return "thue"
    return None


def _vehicles(value: Any) -> list[dict]:
    """LLM có thể trả list[dict], dict lẻ hoặc chuỗi JSON."""
    raw = value
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def enrich(fields: list[dict], options: dict | None = None, ocr_text: str = "") -> tuple[list[dict], list[str]]:
    _ = options
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

    cars = _vehicles(values.get("PhuongTien"))
    car = cars[0] if cars else {}
    loai_phu_hieu = _fold(_item_text(car, "loaiPhuHieu"))
    loai_xe = _fold(_item_text(car, "loaiXe"))
    plate = _plate(_item_text(car, "bienSo", "bienKiemSoat"))

    don_vi = _text(values.get("DonVi_Ten"))
    dv_phone, dv_phone_ok = _phone_read(values.get("DonVi_DienThoai"))
    if dv_phone and not dv_phone_ok:
        warnings.append(f"Số điện thoại đơn vị KDVT trên giấy tờ bị che/mờ, mới đọc được '{dv_phone}' — vui lòng "
                        "nhập nốt các chữ số còn thiếu.")

    # ===== Phần I: NGƯỜI NỘP (chỉ khi có CCCD) =====
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    if nop_name or nop_id:
        add("data[fullname]", nop_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        add("data[nation]", _text(values.get("NguoiNop_QuocTich")) or "Việt Nam")
        nop_area = _area(values.get("NguoiNop_ThuongTru"))
        if nop_area:
            add("data[province]", _province_label(nop_area.get("tinh")))
            add("data[district]", _text(nop_area.get("xa")))
            add("data[address]", _text(nop_area.get("diaChi")))
    add("data[email]", _email(values.get("NguoiNop_Email")))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")) or dv_phone)

    # Ghi chú (data[tenHoSo]): tên hồ sơ gợi ý, vd "Cấp lại phù hiệu xe tải 37C-123.45".
    cap_lai = "cap_lai" in _fold(values.get("DeNghi_LoaiDeNghi")).replace(" ", "_") or "cap lai" in _fold(
        values.get("DeNghi_DuocCap"))
    action = "Cấp lại" if cap_lai else "Cấp"
    loai_label = _item_text(car, "loaiPhuHieu")
    if len(cars) > 1:
        add("data[tenHoSo]", f"{action} {len(cars)} phù hiệu" + (f" {loai_label.lower()}" if loai_label else ""))
    elif plate:
        add("data[tenHoSo]", " ".join(p for p in (action, "phù hiệu", loai_label.lower() if loai_label else "",
                                                   plate) if p))

    # ===== Phần II: THÔNG TIN DOANH NGHIỆP CỦA NGƯỜI NỘP =====
    dv_area = _area(values.get("DonVi_DiaChi"))
    mst_raw = values.get("DonVi_MaSoThue")
    mst, mst_ok = _tax_read(mst_raw)
    if mst and not mst_ok:
        warnings.append(f"Mã số doanh nghiệp trên giấy tờ bị che/mờ, mới đọc được '{mst}' — vui lòng nhập nốt theo "
                        "GCN đăng ký doanh nghiệp/HTX.")
    elif not mst_raw:
        warnings.append("Thiếu mã số doanh nghiệp (ô bắt buộc) — vui lòng nhập tay.")
    add("data[organization]", don_vi)
    add("data[nation1]", "Việt Nam" if (don_vi or dv_area) else None)
    add("data[taxCode]", mst)
    add("data[organizationPhoneNumber]", dv_phone)
    if dv_area:
        add("data[address1]", _text(dv_area.get("diaChi")))
        add("data[province1]", _province_label(dv_area.get("tinh")))
        add("data[district1]", _text(dv_area.get("xa")))

    # ===== Phần III: GIẤY ĐỀ NGHỊ =====
    add("data[SoVanBan]", _full_token_from_ocr(_text(values.get("DeNghi_SoVanBan")), ocr_text))
    dia_danh = _text(values.get("DeNghi_DiaDanh")) or _so_xay_dung(values.get("DeNghi_KinhGui"))
    add("data[TinhThanh]", _province_label(dia_danh) if dia_danh else None)
    add("data[DT]", _date(values.get("DeNghi_NgayLap")))
    add("data[T_CoQuan]", _so_xay_dung(values.get("DeNghi_KinhGui")))
    dich_vu = _dich_vu(loai_phu_hieu)
    add("data[dichVu]", dich_vu)
    if loai_phu_hieu and not dich_vu:
        warnings.append(f"Loại phù hiệu '{loai_label}' không có mục 'Dịch vụ' tương ứng — vui lòng chọn tay.")

    # ===== Phần IV: ĐƠN VỊ KINH DOANH VẬN TẢI =====
    add(f"{_DV}[LoaiHinhDoanhNghiep]", _loai_hinh_dn(values.get("DonVi_LoaiHinh"), don_vi))
    add(f"{_DV}[NguoiDaiDien.HoVaTen]", _text(values.get("DonVi_NguoiDaiDien")))
    add(f"{_DV}[TenCoSoToChuc]", don_vi)
    add(f"{_DV}[MaSoDoanhNghiep]", mst)
    add(f"{_DV}[TenTiengAnh]", _text(values.get("DonVi_TenQuocTe")))
    if dv_area:
        add(f"{_DV}[DiaChiHoatDong][TinhThanh]", _province_label(dv_area.get("tinh")))
        add(f"{_DV}[DiaChiHoatDong][XaPhuong]", _text(dv_area.get("xa")))
        add(f"{_DV}[DiaChiHoatDong][SoNhaChiTiet]", _text(dv_area.get("diaChi")))
    add(f"{_DV}[DanhBaLienLac][SoDienThoai]", dv_phone)
    dv_email = _email(values.get("DonVi_Email"))
    add(f"{_DV}[DanhBaLienLac][ThuDienTu]", dv_email)
    if not dv_email:
        warnings.append("Thiếu email liên hệ của đơn vị KDVT (ô bắt buộc) — vui lòng nhập tay.")
    add(f"{_DV}[DanhBaLienLac][Fax]", _text(values.get("DonVi_Fax")))
    # GCN đăng ký DN/HTX: số giấy chính là mã số doanh nghiệp khi hồ sơ không kèm GCN.
    add(f"{_DV}[GiayDangKyToChuc][SoGiay]", _text(values.get("GCNDK_SoGiay")) or mst)
    add(f"{_DV}[GiayDangKyToChuc][CoQuanCap][TenCoSoToChuc]", _text(values.get("GCNDK_CoQuanCap")))
    add(f"{_DV}[GiayDangKyToChuc][NgayCap]", _date(values.get("GCNDK_NgayCap")))
    gp_so = _text(values.get("GPKD_SoGiay"))
    add(f"{_GP}[SoGiay]", gp_so)
    add(f"{_GP}[NgayCap]", _date(values.get("GPKD_NgayCap")))
    add(f"{_GP}[CapLanThu]", _digits(values.get("GPKD_CapLanThu")))
    add(f"{_GP}[CoQuanCap]", _so_xay_dung(values.get("GPKD_CoQuanCap")))
    if not gp_so:
        warnings.append("Hồ sơ chưa có Giấy phép kinh doanh vận tải — nhập tay Số GPKDVT, ngày cấp, cơ quan cấp "
                        "và đính kèm GPKDVT trong tờ khai.")
    # Mặc định form là "Bị thu hồi" — đơn vị đang xin phù hiệu thì GPKDVT phải còn hiệu lực.
    add(f"{_GP}[HieuLucGiayToVanBan]", "Còn hiệu lực")
    # Select NHIỀU, form chọn sẵn "…bằng xe buýt" — FE (fillStandardMultiSelect) tự xoá mục mặc định sai.
    add(f"{_DV}[HoatDongKinhDoanh][LoaiHinhKinhDoanh]", _loai_hinh_kd(loai_phu_hieu))

    # ===== Phần V: THẨM ĐỊNH =====
    add("data[ThamDinh][SoLuongNopLai]", _digits(values.get("DeNghi_SoLuongNopLai")))
    add("data[ThamDinh][DeNghiDuocCap]", _text(values.get("DeNghi_DuocCap")))

    # ===== Phần VI-VII: PHƯƠNG TIỆN (panel "Thêm phương tiện", xe đầu tiên) =====
    if not cars:
        warnings.append("Không trích được thông tin phương tiện — vui lòng bấm 'Thêm phương tiện' và nhập tay.")
        return out, warnings
    if len(cars) > 1:
        others = ", ".join(_plate(_item_text(c, "bienSo")) or "?" for c in cars[1:])
        warnings.append(f"Hồ sơ có {len(cars)} xe — chỉ điền sẵn xe đầu tiên; các xe còn lại ({others}) bấm "
                        "'Thêm phương tiện' nhập tiếp.")

    # Nút "Thêm phương tiện": FE bấm rồi chờ ô Biển đăng ký của panel hiện ra (waitName) mới điền tiếp.
    out.append({
        "name": "data[ThamDinh][themPhuongTien]",
        "comp": "dom-click",
        "value": True,
        "buttonKey": "themPhuongTien",
        "waitName": f"{_PT}[BienDangKy]",
    })

    # Chủ xe khác đơn vị KDVT (xe của xã viên / xe thuê) → nhánh VII-B; trùng → VII-A.
    kind = _ownership_kind(car.get("loaiHopDong"))
    chu_xe = _item_text(car, "chuXe")
    owned = _owned_by_unit(chu_xe, don_vi)
    if kind or owned is False:
        add(f"{_PT}[DVKDVT]", _RADIO_THUE)
    elif owned:
        add(f"{_PT}[DVKDVT]", _RADIO_SO_HUU)
    else:
        warnings.append("Chưa xác định xe thuộc sở hữu đơn vị hay xe thuê/xe thành viên HTX — vui lòng chọn "
                        "'Thông tin người sở hữu'.")

    add(f"{_PT}[BienDangKy]", plate)
    add(f"{_PT}[BienSoXe]", plate)
    if not plate:
        warnings.append("Thiếu biển số xe — vui lòng nhập tay.")
    so_khung = _code(_item_text(car, "soKhung"))
    so_may = _code(_item_text(car, "soMay", "soDongCo"))
    add(f"{_PT}[SoKhung]", so_khung)
    add(f"{_PT}[SoMay]", so_may)
    label = plate or "đầu tiên"
    if so_khung and len(so_khung) < 17:
        # Số khung (VIN) chuẩn 17 ký tự; ngắn hơn thường do bản scan bị che/cắt.
        warnings.append(f"Xe {label}: số khung '{so_khung}' ngắn hơn 17 ký tự — đối chiếu Chứng nhận đăng ký xe.")
    if not so_khung or not so_may:
        warnings.append(f"Xe {label}: thiếu số khung hoặc số máy — vui lòng nhập tay.")
    add(f"{_PT}[NienHan]", _year(_item_text(car, "nienHan")))

    so_cho = _digits(_item_text(car, "soCho"))
    add(f"{_PT}[PhanLoaiXeCoGioi]", _loai_phuong_tien(loai_xe, loai_phu_hieu, so_cho))
    nuoc = _fold(_item_text(car, "nuocSanXuat"))
    add(f"{_PT}[NuocSanXuat]", _NUOC_SX.get(nuoc))
    # Xe chở hàng → trọng tải (kg, chỉ số); xe chở người → số chỗ.
    if _is_cargo(loai_xe, loai_phu_hieu):
        add(f"{_PT}[SoChoNgoi]", _digits(_item_text(car, "trongTai")) or so_cho)
    else:
        add(f"{_PT}[SoChoNgoi]", so_cho or _digits(_item_text(car, "trongTai")))
    add(f"{_PT}[MauSon]", _item_text(car, "mauSon"))
    add(f"{_PT}[NamSanXuat]", _year(_item_text(car, "namSanXuat")))
    add(f"{_PT}[NhanHieu]", _item_text(car, "nhanHieu"))
    add(f"{_PT}[TinhTrangPhuongTien]", "Đang hoạt động")
    warnings.append("Chọn 'Màu phù hiệu' theo loại phù hiệu, kiểm tra thông tin xe rồi bấm 'Thêm' để đưa xe vào "
                    "danh sách phương tiện.")

    if kind or owned is False:
        add(f"{_PT}[ChuPhuongTienThue.HoVaTen]", chu_xe)
        add(f"{_PT}[HopDongThueMuon][LoaiHinhChoThue]", _CHO_THUE.get(kind or ""))
        add(f"{_PT}[HopDongThueMuon][ThoiGianBatDauThue]", _date(_item_text(car, "hopDongTuNgay")))
        add(f"{_PT}[HopDongThueMuon][ThoiGianHetHanThue]", _date(_item_text(car, "hopDongDenNgay")))
        if not kind:
            warnings.append(f"Xe {label}: chủ xe khác đơn vị KDVT nhưng không thấy hợp đồng thuê/dịch vụ — chọn "
                            "'Loại hình cho thuê' và bổ sung hợp đồng.")
    elif owned:
        add(f"{_PT}[ChuPhuongTien.HoVaTen]", don_vi)
        add(f"{_PT}[GiayDangKyPhuongTien.NgayCap]", _date(_item_text(car, "ngayDangKy")))

    return out, warnings
