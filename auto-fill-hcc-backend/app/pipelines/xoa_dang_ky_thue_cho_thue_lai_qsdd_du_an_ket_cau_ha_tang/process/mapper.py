"""Map compact source facts → Form.io data[...] fields cho "Xóa đăng ký thuê, cho thuê lại QSDĐ trong dự án xây
dựng kinh doanh kết cấu hạ tầng" — cổng Đà Nẵng. Khối "Thông tin chung" như các thủ tục đất đai Đà Nẵng khác,
KHÔNG có panel thửa đất.

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (người đứng Đơn Mẫu 18) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NGƯỜI NỘP → data[fullname]/birthday/gender/identityNumber/.../province/district/address, data[chonDoiTuong].
- data[isOwnerDossier]: True khi tự nộp (mặc định); False khi ỦY QUYỀN (điền cả 2 vai).
- data[noidungyeucaugiaiquyet] = câu khung "ÔNG/BÀ: {chủ hồ sơ} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}"
  (cổng tự sinh câu này theo tài khoản đăng nhập nên phải ghi lại theo chủ hồ sơ) + dòng căn cứ: mục II của
  Đơn, hoặc văn bản chấm dứt thuê khi Đơn để trống mục II.
- data[note]: để trống theo mapping.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process.schema import UI_COMP_BY_NAME

_PROC_TITLE = "Xóa đăng ký thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng"


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
    """Giữ NGUYÊN xuống dòng (cho textarea nội dung yêu cầu): gộp khoảng trắng thừa mỗi dòng, bỏ dòng rỗng."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(v) for v in value)
    lines = [" ".join(str(line).split()) for line in str(value).replace("\r", "").split("\n")]
    lines = [line.strip(" .") for line in lines if line.strip(" .")]
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
    # Chuẩn hóa phường/xã sau sáp nhập (vd phường cũ của quận Sơn Trà → phường mới) để khớp SELECT. ⚠
    # remap_area build key bằng tỉnh KHÔNG prefix ("da nang" ≠ "thanh pho da nang") → strip prefix TRƯỚC.
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


def _gender_from_identity(identity: str | None) -> str | None:
    """Chữ số thứ 4 của số định danh 12 số mã hóa thế kỷ + giới tính: chẵn → Nam, lẻ → Nữ."""
    if not identity or len(identity) != 12:
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "ong"}:
        return "Nam"
    if folded in {"nu", "female", "ba"}:
        return "Nữ"
    return None


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
    # CHỈ có NĂM → BỎ TRỐNG thay vì để ô flatpickr tự suy ra ngày sai.
    if re.fullmatch(r"\d{4}", text.strip()):
        return None
    return normalize_date(text)


def _issuer(value: Any, identity: str | None, issue_date: str | None) -> str | None:
    """Nơi cấp ghi trên CCCD; hồ sơ chỉ có văn bản công chứng (không ghi nơi cấp) thì suy theo ngày cấp của
    thẻ 12 số — trước 01/7/2024 là Cục Cảnh sát QLHC về TTXH, từ đó là Bộ Công an."""
    text = _text(value)
    if text:
        return normalize_issuer(text)
    if identity and len(identity) == 12 and issue_date:
        return default_issuer(issue_date)
    return None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang", "mtv")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def _noi_dung(owner_name: str | None, owner_is_tc: bool, noi_dung_don: str | None, van_ban: str | None) -> str:
    """Câu khung giống câu cổng tự sinh, ghi lại theo chủ hồ sơ; dòng sau là căn cứ xóa đăng ký thuê."""
    if owner_name:
        subject = owner_name if owner_is_tc else f"ÔNG/BÀ: {owner_name}"
        head = f"{subject} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}"
    else:
        head = _PROC_TITLE
    if noi_dung_don:
        return f"{head}\n{noi_dung_don}"
    if van_ban:
        return f"{head}\nXóa đăng ký cho thuê quyền sử dụng đất theo {van_ban.rstrip('.')}"
    return head


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

    def add_area(area) -> None:
        if not area:
            return
        xa = _text(area.get("xa"))
        dia_chi = _text(area.get("diaChi"))
        # Chỉ có tỉnh, thiếu cả phường/xã lẫn chi tiết → nhiều khả năng LLM suy từ địa chỉ thửa; bỏ cả cụm.
        if not xa and not dia_chi:
            return
        # data[nation] cổng đặt sẵn "Việt Nam" — không chọn lại để khỏi kích hoạt reset tỉnh/phường.
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", xa)
        add("data[address]", dia_chi)

    # --- CHỦ HỒ SƠ ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_area = _area(values.get("ChuHoSo_DiaChi"))
    owner_mst = _identity(values.get("ChuHoSo_MaSoThue"))

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))
    nop_birthday = _date(values.get("NguoiNop_NgaySinh"))
    nop_issue_date = _date(values.get("NguoiNop_NgayCap"))

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người sử dụng đất đứng tên Đơn đăng ký biến động Mẫu số 18).")

    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))
    is_tc = nop_is_tc if is_uy_quyen else (nop_is_tc or owner_is_tc)
    mst = nop_mst if is_uy_quyen else (nop_mst or owner_mst)

    # CMND cũ 9 số chỉ để đối chiếu — ô 'CMND/CCCD/MST/Mã định danh' nhập số định danh 12 số.
    if nop_id and not is_tc and len(nop_id) == 9:
        warnings.append(
            "Chỉ đọc được số CMND 9 số của người nộp. Ô 'CMND/CCCD/MST/Mã định danh' cần số định danh 12 số — "
            "cán bộ đối chiếu CCCD rồi nhập lại."
        )
        nop_id = None

    # --- Chủ hồ sơ ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    add("data[noidungyeucaugiaiquyet]", _noi_dung(
        owner_name, owner_is_tc, _multiline_text(values.get("NoiDungYeuCau")), _text(values.get("VanBanXoaThue"))))

    # --- Người nộp ---
    add("data[isOwnerDossier]", not is_uy_quyen)
    add("data[fullname]", nop_name or owner_name)
    add("data[birthday]", nop_birthday)
    add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")) or _gender_from_identity(nop_id))
    add("data[identityNumber]", (mst or nop_id) if is_tc else nop_id)
    add("data[identityDate]", nop_issue_date)
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap"), nop_id, nop_issue_date))
    # Tự nộp: ưu tiên địa chỉ ghi trên Đơn (chủ hồ sơ) hơn CCCD hay còn địa danh cũ.
    add_area(nop_area if is_uy_quyen else (owner_area or nop_area))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    add("data[email]", _text(values.get("NguoiNop_Email")))
    add("data[chonDoiTuong]", "Tổ chức" if is_tc else "Cá nhân")
    if is_tc:
        add("data[taxCode]", mst)

    if not nop_birthday and not is_tc:
        warnings.append(
            "Hồ sơ không có ngày sinh đầy đủ của người nộp. Ô 'Ngày sinh' có thể đang mang sẵn ngày sinh của "
            "tài khoản đăng nhập — cán bộ sửa theo CCCD trước khi nộp."
        )
    if "data[phoneNumber]" not in seen:
        warnings.append("Không đọc được số điện thoại trên Đơn — ô 'Số điện thoại' (bắt buộc) cần nhập tay.")

    return out, warnings
