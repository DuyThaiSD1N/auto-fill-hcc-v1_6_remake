"""Map compact source facts → Form.io data[...] fields cho "Cấp đổi Giấy chứng nhận QSDĐ, quyền sở hữu tài
sản gắn liền với đất" (cổng Đà Nẵng). CÙNG contact block với chuyen_muc_dich/tach_hop_thua — chỉ khác
_PROC_TITLE + ghép SỐ GCN vào nội dung yêu cầu (form không có ô riêng cho số GCN).

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (người đứng tên GCN đề nghị cấp đổi; có thể đồng sở hữu vợ+chồng) → data[ownerFullname]
  (+ data[organization] khi tổ chức).
- NGƯỜI NỘP → data[fullname]/birthday/gender/identityNumber/.../province/district/address, data[chonDoiTuong],
  data[taxCode] (khi người nộp là tổ chức).
- data[isOwnerDossier]: True khi tự nộp; False khi ỦY QUYỀN (điền cả 2).
- data[noidungyeucaugiaiquyet] = "Cấp đổi Giấy chứng nhận số {GCN_So}. {NoiDungBienDong}" hoặc câu khung.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_doi_gcn_da_nang.process.schema import UI_COMP_BY_NAME

_PROC_TITLE = "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"


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
    """Giữ NGUYÊN xuống dòng (cho textarea nội dung): gộp khoảng trắng thừa mỗi dòng, bỏ dòng rỗng."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(v) for v in value)
    lines = [" ".join(str(line).split()) for line in str(value).replace("\r", "").split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines) or None


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
    # Chuẩn hóa phường/xã sau sáp nhập (vd "Nam Dương"/"Phước Ninh" → "Phường Hải Châu"; Quảng Nam cũ → Đà
    # Nẵng) để khớp SELECT. ⚠ strip prefix tỉnh TRƯỚC remap ("da nang" ≠ "thanh pho da nang").
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
    # CHỈ có NĂM (giấy tờ đất/ủy quyền hay ghi "sinh năm 1987", thiếu ngày/tháng) → KHÔNG đủ dữ liệu tạo
    # ngày hợp lệ. BỎ TRỐNG thay vì điền rác: ô ngày (flatpickr) trên form nhận "1987" sẽ suy ra ngày sai
    # (vd 19/03/2033). Cán bộ tự bổ sung ngày/tháng từ CCCD nếu cần.
    if re.fullmatch(r"\d{4}", text.strip()):
        return None
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang", "mtv")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def _noi_dung(gcn_so: str | None, noi_dung_bd: str | None, owner_name: str | None) -> str | None:
    """Ghép nội dung yêu cầu: 'Cấp đổi Giấy chứng nhận số {GCN}. {lý do biến động}' (số GCN không có ô riêng).
    Trống cả hai → câu khung '{chủ hồ sơ} ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}'."""
    gcn_clause = f"Cấp đổi Giấy chứng nhận số {gcn_so}" if gcn_so else None
    if noi_dung_bd:
        # Nếu lý do biến động chưa nhắc số GCN thì prepend mệnh đề số GCN.
        if gcn_so and _fold(gcn_so).replace(" ", "") not in _fold(noi_dung_bd).replace(" ", ""):
            return f"{gcn_clause}. {noi_dung_bd}"
        return noi_dung_bd
    if gcn_clause:
        return gcn_clause
    if owner_name:
        return f"{owner_name} ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}"
    return None


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
        # Chống địa chỉ ĐOÁN: chỉ có tỉnh mà thiếu CẢ phường/xã LẪN số nhà → nhiều khả năng LLM suy từ thửa
        # đất/trụ sở, bỏ để không điền lệch mỗi ô Tỉnh.
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
        warnings.append("Thiếu tên chủ hồ sơ (người đứng tên Giấy chứng nhận đề nghị cấp đổi).")

    # ỦY QUYỀN nếu người nộp KHÁC chủ hồ sơ; TỰ NỘP nếu trùng/là 1 phần của chủ hồ sơ (đồng sở hữu)/thiếu.
    is_uy_quyen = bool(
        nop_name and owner_name
        and _fold(nop_name) != _fold(owner_name)
        and _fold(nop_name) not in _fold(owner_name)  # đồng sở hữu: người nộp nằm trong chuỗi "A và B"
    )

    # --- Chủ hồ sơ (luôn điền) ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    add("data[noidungyeucaugiaiquyet]", _noi_dung(
        _text(values.get("GCN_So")), _multiline_text(values.get("NoiDungBienDong")), owner_name))

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
        # Tự nộp: ưu tiên NguoiNop_DiaChi, thiếu thì lấy ChuHoSo_DiaChi.
        add_area("data[province]", "data[district]", "data[address]", nop_area or owner_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add("data[chonDoiTuong]", "Tổ chức" if (nop_is_tc or owner_is_tc) else "Cá nhân")
        if nop_is_tc or owner_is_tc:
            add("data[taxCode]", nop_mst)

    return out, warnings
