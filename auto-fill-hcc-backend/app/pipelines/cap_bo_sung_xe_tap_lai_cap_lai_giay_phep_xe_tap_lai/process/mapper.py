"""Map compact source facts → Form.io data[...] fields cho "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe
tập lái".

- Phần I   Người nộp (data[...] phẳng): CHỈ khi có CCCD người nộp; không có → để tài khoản VNeID tự đổ, chỉ bổ
           sung email nhận kết quả của cơ sở đào tạo (DS đề nghị).
- Phần II  data[organization1/organization2/organization] — cơ quan chủ quản / cơ sở đào tạo / trường.
- Phần II.a DATAGRID data[tbantest][i][...] — mỗi xe 1 dòng (FE tự bấm "Thêm dòng"). Hai cột BẮT BUỘC "Xe của
           cơ sở đào tạo" (trongtai) / "Xe hợp đồng" (namsanxuat): cột đúng loại ghi "X", cột còn lại "-".
- Phần II.b data[TinTTTe] (tỉnh nơi ký, mặc định form là Đà Nẵng → phải đổi) + data[kyTenDongDau].
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.process.schema import (
    UI_COMP_BY_NAME,
    _MAX_XE,
)

_GRID = "data[tbantest]"
_KIEM_DINH_CAP = "ngayCapGiayChungNhanKiemDinhAtktBvmt"
_KIEM_DINH_HET = "ngayCapGiayChungNhanKiemDinhAtktBvmt1"
# Biển số VN đầy đủ: mã tỉnh 2 số + seri 1-2 chữ (có thể kèm 1 số) + 4-5 số (vd 38A-123.45, 29LD-012.34).
_FULL_PLATE = re.compile(r"^\d{2}[A-Z]{1,2}\d?-?\d{3}\.?\d{2}\b")


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


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


def _province_from_kinh_gui(value: Any) -> str | None:
    """'Sở Xây dựng Quảng Trị' / 'Sở Xây dựng tỉnh Quảng Trị' → 'Quảng Trị' (dự phòng khi thiếu địa danh)."""
    text = _text(value)
    if not text:
        return None
    m = re.search(r"sở\s+xây\s+dựng\s+(.+)$", text, flags=re.IGNORECASE)
    rest = _strip_admin_prefix(m.group(1)) if m else ""
    return rest or None


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


def _parse_date(value: str | None) -> _dt.date | None:
    if not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _plate(value: Any) -> str | None:
    """Biển số giữ đúng định dạng giấy tờ (vd '38A-123.45 (T)'), chỉ chuẩn hoá HOA + khoảng trắng."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s*-\s*", "-", text.upper())
    text = re.sub(r"\s*\.\s*", ".", text)
    return " ".join(text.split()) or None


def _plate_complete(plate: str) -> bool:
    return bool(_FULL_PLATE.match(plate.replace(" ", ""))) and not re.search(r"[_…*?]", plate)


def _code(value: Any) -> str | None:
    """Số máy / số khung: bỏ khoảng trắng OCR chèn giữa, viết HOA."""
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text).upper() or None


def _sentence_case(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text[0].upper() + text[1:]


def _ownership(item: dict) -> str | None:
    """'hop_dong' | 'co_so' | None — từ khoá loaiSoHuu (LLM có thể trả mô tả tự do)."""
    raw = _fold(item.get("loaiSoHuu") or item.get("loai") or "")
    if not raw:
        if _truthy(item.get("xeHopDong")):
            return "hop_dong"
        if _truthy(item.get("xeCoSo")):
            return "co_so"
        return None
    if "hop" in raw or "thue" in raw:
        return "hop_dong"
    if "co_so" in raw or "co so" in raw or "dao tao" in raw or "so huu" in raw:
        return "co_so"
    return None


def _truthy(value: Any) -> bool:
    return value is True or _fold(value) in {"x", "true", "1", "co", "yes"}


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

    # ===== Phần I: NGƯỜI NỘP (chỉ khi có CCCD) =====
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    if nop_name or nop_id:
        add("data[chonDoiTuong]", "Cá nhân")
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
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    # Email: của người nộp nếu có; không thì hòm thư nhận kết quả của cơ sở đào tạo ghi trên DS đề nghị.
    add("data[email]", _email(values.get("NguoiNop_Email")) or _email(values.get("CoSo_Email")))

    # ===== Phần II: CƠ SỞ ĐÀO TẠO =====
    co_so = _text(values.get("CoSo_Ten"))
    if not co_so:
        warnings.append("Thiếu tên cơ sở đào tạo (DS đề nghị) — vui lòng nhập tay ô 'Cơ sở đào tạo'.")
    add("data[organization1]", _text(values.get("CoSo_CoQuanChuQuan")))
    add("data[organization2]", co_so)
    add("data[organization]", _text(values.get("CoSo_TenTrongCau")) or co_so)

    # ===== Phần II.a: DATAGRID bảng xe =====
    cars = _vehicles(values.get("XeTapLai"))
    if not cars:
        warnings.append("Không trích được bảng xe tập lái — vui lòng nhập tay danh sách xe.")
    if len(cars) > _MAX_XE:
        warnings.append(f"Hồ sơ có {len(cars)} xe, chỉ điền tự động {_MAX_XE} xe đầu.")
    today = _dt.date.today()
    for idx, car in enumerate(cars[:_MAX_XE]):
        base = f"{_GRID}[{idx}]"
        stt = _item_text(car, "stt", "tt")
        add(f"{base}[stt]", stt if stt and stt.isdigit() else str(idx + 1))

        plate = _plate(_item_text(car, "bienSo", "bienSoXe", "bienKiemSoat"))
        add(f"{base}[biensoxe]", plate)
        label = plate or f"dòng {idx + 1}"
        if not plate:
            warnings.append(f"Xe {label}: thiếu biển số đăng ký.")
        elif not _plate_complete(plate):
            warnings.append(f"Xe {label}: biển số có thể thiếu/mờ ký tự — đối chiếu bản gốc GCN đăng ký xe.")

        # Hai cột BẮT BUỘC, loại trừ nhau: đúng loại → "X", còn lại "-" (như ô không đánh dấu trên DS).
        kind = _ownership(car)
        if kind == "hop_dong":
            add(f"{base}[trongtai]", "-")
            add(f"{base}[namsanxuat]", "X")
        elif kind == "co_so":
            add(f"{base}[trongtai]", "X")
            add(f"{base}[namsanxuat]", "-")
        else:
            warnings.append(f"Xe {label}: chưa xác định xe của cơ sở đào tạo hay xe hợp đồng — vui lòng đánh dấu.")

        add(f"{base}[nhanhieu]", _item_text(car, "nhanHieu"))
        add(f"{base}[sokhung]", _sentence_case(_item_text(car, "loaiXe")))  # key sokhung = cột "Loại xe"
        so_may = _code(_item_text(car, "soDongCo", "soMay"))
        so_khung = _code(_item_text(car, "soKhung"))
        add(f"{base}[somay]", so_may)
        add(f"{base}[mauson]", so_khung)  # key mauson = cột "Số khung"
        if not so_may or not so_khung:
            warnings.append(f"Xe {label}: thiếu số động cơ hoặc số khung.")
        elif len(so_khung) < 17:
            # Số khung (VIN) chuẩn 17 ký tự; ngắn hơn thường do DS ghi rút gọn / bản scan bị cắt.
            warnings.append(f"Xe {label}: số khung '{so_khung}' ngắn hơn 17 ký tự — đối chiếu GCN đăng ký xe.")

        ngay_cap = _date(_item_text(car, "ngayCapKiemDinh", "ngayKiemDinh"))
        ngay_het = _date(_item_text(car, "ngayHetHanKiemDinh", "hieuLucDen"))
        add(f"{base}[{_KIEM_DINH_CAP}]", ngay_cap)
        add(f"{base}[{_KIEM_DINH_HET}]", ngay_het)
        het = _parse_date(ngay_het)
        if het and het < today:
            warnings.append(f"Xe {label}: giấy chứng nhận kiểm định đã hết hạn ({ngay_het}).")
        add(f"{base}[cuakhaunhapxuat]", _item_text(car, "ghiChu"))  # key cuakhaunhapxuat = cột "Ghi chú"

    # ===== Phần II.b: KÝ =====
    dia_danh = _text(values.get("DeNghi_DiaDanh")) or _province_from_kinh_gui(values.get("DeNghi_KinhGui"))
    add("data[TinTTTe]", _province_label(dia_danh) if dia_danh else None)
    # Chức danh ký hay xuống dòng ("KT. HIỆU TRƯỞNG\nPHÓ HIỆU TRƯỞNG") → nối bằng " - " cho dễ đọc.
    chuc_danh_raw = values.get("DeNghi_ChucDanhKy")
    if isinstance(chuc_danh_raw, str):
        chuc_danh_raw = " - ".join(p.strip(" -–") for p in chuc_danh_raw.splitlines() if p.strip(" -–"))
    chuc_danh = _text(chuc_danh_raw)
    nguoi_ky = _text(values.get("DeNghi_NguoiKy"))
    add("data[kyTenDongDau]", " ".join(p for p in (chuc_danh, nguoi_ky) if p) or None)

    return out, warnings
