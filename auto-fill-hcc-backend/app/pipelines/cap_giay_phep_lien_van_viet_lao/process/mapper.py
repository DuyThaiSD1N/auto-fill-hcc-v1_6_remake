"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp, cấp lại Giấy phép liên vận
giữa Việt Nam và Lào".

MỘT người đứng đơn:
  Phần I  (data[...] phẳng)                 — người nộp.
  Phần II (data[panel_caNhanToChuc][...])   — thông tin đề nghị (dịch vụ / kính gửi / tại / người làm đơn /
                                              mục đích chuyến đi). nguoiLamDon = họ tên người nộp.
Không đụng datagrid phương tiện (nạp từ API tài khoản).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.schema import UI_COMP_BY_NAME

_PANEL = "data[panel_caNhanToChuc]"

# 8 option DỊCH VỤ ĐÚNG NHƯ TRÊN WEB (select Choices). LLM chỉ chọn 1 MÃ NGẮN (tm_moi/ptm_hethan…) →
# mapper trả nguyên văn option để FE fold-match (foldChoiceText đồng nhất dấu gạch "Việt - Lào"↔"Việt-Lào";
# choiceMatches so substring 2 chiều; tiền tố "Cấp" vs "Cấp lại" đủ phân biệt cấp mới ≠ cấp lại).
_DICHVU_CANON: dict[str, str] = {
    "tm_moi": "Cấp Giấy phép liên vận Việt - Lào cho phương tiện thương mại (áp dụng cho phương tiện kinh "
              "doanh vận tải)",
    "tm_hethan": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện thương mại áp dụng cho phương tiện "
                 "kinh doanh vận tải) do hết hạn",
    "tm_huhong": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện thương mại (áp dụng cho phương tiện "
                 "kinh doanh vận tải) do hư hỏng",
    "tm_matmat": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện thương mại (áp dụng cho phương tiện "
                 "kinh doanh vận tải) do mất mát",
    "ptm_moi": "Cấp Giấy phép liên vận Việt - Lào cho phương tiện phi thương mại; phương tiện thương mại "
               "phục vụ các công trình, dự án hoặc hoạt động kinh doanh của doanh nghiệp, hợp tác xã trên "
               "lãnh thổ Lào",
    "ptm_hethan": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện phi thương mại; phương tiện thương "
                  "mại phục vụ các công trình, dự án hoặc hoạt động kinh doanh của doanh nghiệp, hợp tác xã "
                  "trên lãnh thổ Lào do hết hạn",
    "ptm_huhong": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện phi thương mại; phương tiện thương "
                  "mại phục vụ các công trình, dự án hoặc hoạt động kinh doanh của doanh nghiệp, hợp tác xã "
                  "trên lãnh thổ Lào do hư hỏng",
    "ptm_matmat": "Cấp lại Giấy phép liên vận Việt - Lào cho phương tiện phi thương mại; phương tiện thương "
                  "mại phục vụ các công trình, dự án hoặc hoạt động kinh doanh của doanh nghiệp, hợp tác xã "
                  "trên lãnh thổ Lào do mất mát",
}


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
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
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


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _bienso(value: Any) -> str | None:
    """Biển số xe: CHỈ giữ chữ + số (bỏ dấu cách, gạch '-', chấm...). Cổng DVC KHÔNG cho lưu ký tự đặc
    biệt → '92C 12287' / '92C-12287' đều thành '92C12287'."""
    text = _text(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return cleaned or None


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


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


_VEHICLE_KEYS = (
    "bienSo", "trongTai", "namSanXuat", "nhanHieu", "soKhung", "soMay",
    "mauSon", "hinhThucHoatDong", "cuaKhau", "tuNgay", "denNgay", "nienHan", "loaiPhuongTien",
)


def _vehicles(value: Any) -> list[dict]:
    """Chuẩn hoá danh sách phương tiện. LLM có thể trả list[dict], chuỗi JSON, hoặc 1 biển số lẻ."""
    import json

    raw = value
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("[") or s.startswith("{"):
            try:
                raw = json.loads(s)
            except Exception:  # noqa: BLE001
                raw = [{"bienSo": p} for p in re.split(r"[,;\n]+", s) if p.strip()]
        else:
            raw = [{"bienSo": p.strip()} for p in re.split(r"[,;\n]+", s) if p.strip()]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            item = {"bienSo": item}
        car: dict[str, str] = {}
        for k in _VEHICLE_KEYS:
            v = _text(item.get(k))
            if k == "bienSo":
                v = _bienso(item.get(k))  # bỏ ký tự đặc biệt (cổng không cho lưu).
            elif k in ("tuNgay", "denNgay"):
                v = _date(item.get(k))
            elif k == "cuaKhau" and v and "tat ca" in _fold(v):
                v = "Tất cả cửa khẩu"  # option web KHÔNG có chữ "các"
            elif k == "trongTai" and v:
                m = re.search(r"\d+", v)
                v = m.group(0) if m else v  # "5 chỗ" → "5"
            if v:
                car[k] = v
        if car.get("bienSo") or len(car) >= 2:
            out.append(car)
    return out


def _tp(value: Any) -> str | None:
    """Đổi 'Thành phố' → 'TP' cho khớp option web (Kính gửi: 'Sở Xây dựng TP Đà Nẵng'; 'Tại': 'TP Đà Nẵng').
    Tỉnh giữ nguyên 'tỉnh …'. choiceMatches so substring 2 chiều nên phần còn lại tự khớp."""
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\bthành\s*phố\b", "TP", text, flags=re.IGNORECASE)


def _dichvu_value(value: Any) -> str | None:
    """LLM trả MÃ NGẮN (tm_moi…) hoặc mô tả tự do → chuỗi option ĐÚNG như web. Suy luận dự phòng theo
    nhóm phương tiện (phi thương mại?) + lý do cấp lại (hết hạn/hư hỏng/mất mát) nếu không phải mã sạch."""
    raw = _text(value)
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _DICHVU_CANON:
        return _DICHVU_CANON[key]
    f = _fold(raw)
    # Mã lẫn trong text (vd "ptm_moi").
    for code in _DICHVU_CANON:
        if code in f.replace(" ", "_"):
            return _DICHVU_CANON[code]
    # Suy luận từ mô tả tự do.
    is_ptm = "phi thuong mai" in f
    prefix = "ptm_" if is_ptm else "tm_"
    if "het han" in f:
        reason = "hethan"
    elif "hu hong" in f or "hu hai" in f:
        reason = "huhong"
    elif "mat mat" in f or "bi mat" in f:
        reason = "matmat"
    elif "cap lai" in f:
        reason = "hethan"  # cấp lại nhưng không nêu lý do → mặc định hết hạn.
    else:
        reason = "moi"     # "Cấp" (không "cấp lại") → cấp mới.
    return _DICHVU_CANON.get(prefix + reason, raw)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _text(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    # --- Phần I: người nộp ---
    name = _text(values.get("NguoiNop_HoTen"))
    identity = _identity(values.get("NguoiNop_SoDinhDanh"))
    residence = _area(values.get("NguoiNop_ThuongTru"))

    if not name:
        warnings.append("Thiếu họ tên người nộp từ CCCD/Giấy đề nghị.")

    add("data[chonDoiTuong]", "Cá nhân")
    add("data[fullname]", name)
    add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
    add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
    add("data[identityNumber]", identity)
    add("data[identityDate]", _date(values.get("NguoiNop_NgayCapCccd")))
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCapCccd")))
    add("data[nation]", _text(values.get("NguoiNop_QuocTich")) or ("Việt Nam" if name else None))
    add_area("data[province]", "data[district]", "data[address]", residence)
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    add("data[email]", _text(values.get("NguoiNop_Email")))

    # --- Phần II: thông tin đề nghị (key LỒNG) ---
    add(f"{_PANEL}[dichVu]", _dichvu_value(values.get("DeNghi_DichVu")))
    add(f"{_PANEL}[T_CoQuan]", _tp(values.get("DeNghi_KinhGui")))       # option web: "Sở Xây dựng TP Đà Nẵng"
    add(f"{_PANEL}[TinTTTe]", _province_label(values.get("DeNghi_Tai")))  # option web: "Thành phố Đà Nẵng" (KHÔNG rút gọn TP)
    add(f"{_PANEL}[nguoiLamDon]", name)  # Người làm đơn = người nộp.

    # Mục đích chuyến đi → tích đúng 1 checkbox (a/b/c/d).
    mucdich = _fold(values.get("DeNghi_MucDich"))
    if mucdich:
        if "cong vu" in mucdich:
            add(f"{_PANEL}[mucdich_01]", True)
        elif "ca nhan" in mucdich:
            add(f"{_PANEL}[mucdich_02]", True)
        elif "kinh doanh" in mucdich:
            add(f"{_PANEL}[mucdich_03]", True)
        else:
            add(f"{_PANEL}[mucdich_04]", True)  # Mục đích khác.

    # --- Phần III: danh sách phương tiện (comp riêng dom-vehicle-add) ---
    # FE: mỗi xe → nếu biển số CÓ trong ô "Chọn phương tiện" (BienSoXeData, nạp từ tài khoản) thì chọn +
    # bấm "Thêm" để cổng tự đổ dòng; nếu KHÔNG có thì bấm "Thêm mới" tạo dòng trống rồi ĐIỀN các ô từ dữ
    # liệu xe. value = JSON danh sách xe (mỗi xe object đầy đủ cột).
    vehicles = _vehicles(values.get("DeNghi_PhuongTien"))
    if vehicles:
        import json

        out.append({
            "name": f"{_PANEL}[BienSoXeData]",
            "comp": "dom-vehicle-add",
            "value": json.dumps(vehicles, ensure_ascii=False),
            "addButtonName": f"{_PANEL}[themxe]",
        })

    return out, warnings
