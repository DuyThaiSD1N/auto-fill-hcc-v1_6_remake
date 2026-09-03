"""Map compact source facts → Form.io data[...] fields cho "Giao đất, cho thuê đất, chuyển mục đích SDĐ;
giao/cho thuê rừng; gia hạn SDĐ" (cổng Đà Nẵng). CÙNG contact block với #75/chuyen_muc_dich/tach_hop_thua
+ THÊM panel thửa đất (Số thửa/Số tờ/Địa chỉ thửa đất + province2/district2/nation2).

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (người đề nghị giao/thuê/chuyển mục đích) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NGƯỜI NỘP           → data[fullname]/birthday/gender/identityNumber/.../province/district/address,
  data[chonDoiTuong] (loại người nộp), data[taxCode] (khi người nộp là tổ chức).
- data[isOwnerDossier]: True khi chủ hồ sơ = người nộp (tự nộp) → cổng tự đổ; False khi ỦY QUYỀN (điền cả 2).
- data[noidungyeucaugiaiquyet] = nội dung đề nghị (chép đầy đủ) hoặc câu khung khi trống.
- Thửa đất: data[SoThuaDat]/[SoToBanDo]/[diaChiThuaDat]/[province2]/[district2]/[nation2].
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.process.schema import UI_COMP_BY_NAME

# Văn bản "Nội dung yêu cầu giải quyết" fallback: "{tên chủ hồ sơ} ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}".
_PROC_TITLE = (
    "giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, cho thuê rừng, gia hạn sử dụng đất"
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
            value.get("tinh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _multiline_text(value: Any) -> str | None:
    """Giữ NGUYÊN xuống dòng (cho textarea nội dung yêu cầu): chỉ gộp khoảng trắng thừa mỗi dòng, bỏ dòng rỗng."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(v) for v in value)
    lines = [" ".join(str(line).split()) for line in str(value).replace("\r", "").split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines) or None


def _digits_only(value: Any) -> str | None:
    """Chỉ giữ chữ số/ký hiệu thửa; bỏ chữ dẫn 'thửa đất số'/'tờ bản đồ số'."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?i)\b(thửa\s*đất\s*số|thửa\s*số|số\s*thửa|tờ\s*bản\s*đồ\s*số|số\s*tờ)\b", "", text)
    return text.strip(" :;.,-") or None


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


def _commune_label(value: Any) -> str | None:
    return _text(value)


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
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        return None
    # Chuẩn hóa phường/xã sau sáp nhập (vd CCCD/giấy tờ cũ "Phước Mỹ" → "Phường An Hải") để khớp SELECT
    # trên form (cả địa chỉ NGƯỜI lẫn địa chỉ THỬA ĐẤT). ⚠ remap_area build key bằng tỉnh KHÔNG prefix
    # ("da nang" ≠ "thanh pho da nang") → strip prefix tỉnh TRƯỚC; _province_label gắn lại "Thành phố" sau.
    if not out:
        return None
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


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
    # CHỈ có NĂM (giấy tờ đất hay ghi "sinh năm 19xx", thiếu ngày/tháng) → BỎ TRỐNG thay vì điền rác (ô
    # ngày flatpickr nhận "1987" sẽ suy ra ngày sai).
    if re.fullmatch(r"\d{4}", text.strip()):
        return None
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value) -> None:
        if name in {s[0] for s in seen} or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add((name, None))

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        xa = _commune_label(area.get("xa"))
        dia_chi = _text(area.get("diaChi"))
        # Chống địa chỉ ĐOÁN: nếu chỉ có tỉnh mà thiếu CẢ phường/xã LẪN số nhà/chi tiết → nhiều khả năng
        # LLM suy từ thửa đất/trụ sở tổ chức (không phải nơi thường trú thật của người nộp). Thường trú
        # trên CCCD luôn có đủ xã + số nhà → bỏ cả cụm để không điền lệch mỗi ô Tỉnh.
        if not xa and not dia_chi:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, xa)
        add(address_name, dia_chi)

    # --- CHỦ HỒ SƠ (subject) ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_area = _area(values.get("ChuHoSo_DiaChi"))

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người đề nghị giao/thuê đất, chuyển mục đích).")

    # ỦY QUYỀN nếu người nộp KHÁC chủ hồ sơ; TỰ NỘP nếu trùng (hoặc thiếu người nộp).
    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))

    # --- Chủ hồ sơ (luôn điền) ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    # Nội dung yêu cầu: chép ĐẦY ĐỦ nội dung đề nghị từ Đơn Mẫu 01 (GIỮ xuống dòng); CHỈ khi trống mới
    # fallback câu khung "{tên chủ hồ sơ} ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}".
    noi_dung = _multiline_text(values.get("NoiDungYeuCau"))
    if noi_dung:
        add("data[noidungyeucaugiaiquyet]", noi_dung)
    elif owner_name:
        add("data[noidungyeucaugiaiquyet]", f"{owner_name} ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}")

    # --- Thông tin thửa đất (nghiệp vụ — điền độc lập vai trò) ---
    add("data[SoThuaDat]", _digits_only(values.get("ThuaDat_SoThua")))
    add("data[SoToBanDo]", _digits_only(values.get("ThuaDat_SoTo")))
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    if parcel_area:
        # KHÔNG áp guard "bỏ nếu chỉ có tỉnh": thửa đất có thể chỉ ghi tới cấp phường + tỉnh (không số nhà).
        add("data[province2]", _province_label(parcel_area.get("tinh")))
        add("data[district2]", _commune_label(parcel_area.get("xa")))
        add("data[diaChiThuaDat]", _text(parcel_area.get("diaChi")))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam")

    if is_uy_quyen:
        # === ỦY QUYỀN: chủ hồ sơ ≠ người nộp → BỎ TÍCH, điền cả 2 vai. ===
        add("data[isOwnerDossier]", False)
        add("data[fullname]", nop_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", nop_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add("data[chonDoiTuong]", "Tổ chức" if nop_is_tc else "Cá nhân")
        if nop_is_tc:
            add("data[taxCode]", nop_mst)
    else:
        # === TỰ NỘP: người nộp = chủ hồ sơ → TICH, điền phần người nộp bằng chính chủ hồ sơ. ===
        add("data[isOwnerDossier]", True)
        add("data[fullname]", nop_name or owner_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        # Tự nộp: địa chỉ người nộp = địa chỉ chủ hồ sơ → ưu tiên NguoiNop_DiaChi, thiếu thì lấy ChuHoSo_DiaChi.
        add_area("data[province]", "data[district]", "data[address]", nop_area or owner_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add("data[chonDoiTuong]", "Tổ chức" if (nop_is_tc or owner_is_tc) else "Cá nhân")
        if nop_is_tc or owner_is_tc:
            add("data[taxCode]", nop_mst)

    return out, warnings
