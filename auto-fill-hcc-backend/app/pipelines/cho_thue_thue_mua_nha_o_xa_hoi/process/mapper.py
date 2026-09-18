"""Map compact source facts → Form.io data[...] fields cho "Cho thuê, cho thuê mua nhà ở xã hội…" (cổng
Bộ Xây dựng). Field-key data[...] FLAT, nhưng NHIỀU key TRÙNG giữa Phần I và Phần III → dùng OCCURRENCE.

- Phần I    (occ0) : người nộp — fullname/CCCD/thường trú + chonDoiTuong + nation.
- Phần I.1         : doanh nghiệp (khi Tổ chức) — organization/taxCode/nation1.
- Phần II          : checkbox mua/thuemua/thue (đúng 1 ô theo hình thức đơn).
- Phần III  (occ1) : người viết đơn — nhân thân (occ1) + job/workPlace/thuocDoiTuong + nơi ở hiện tại
                     (province/district/address occ1) + thường trú (province1/district1/address1).
- Phần III.1       : datagrid thành viên gia đình dtgrid1[i].
- Phần III.2       : thucTrang (select) + checkBox cam đoan.
- Phần III.3       : TinTTTe (nơi ký) + TDTTK (ngày ký) + nguoiLamDon (họ tên).

⚠ 7 key trùng (fullname/identityNumber/identityDate/identityAgency/province/district/address): Phần I
điền occurrence=0, Phần III điền occurrence=1. FE fillFormStandard chọn ô thứ N (ưu tiên visible).

Hai địa chỉ suy lẫn nhau khi đơn chỉ ghi một: thiếu nơi ở hiện tại → dùng thường trú; thiếu thường trú →
dùng nơi ở hiện tại. Không suy thì địa chỉ trống hàng loạt vì cả Phần I lẫn province1 đều lấy thường trú.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.schema import UI_COMP_BY_NAME, _MAX_TV


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
    # Chuẩn hóa phường/xã sau sáp nhập để khớp SELECT trên form (địa chỉ CCCD ghi tên phường CŨ).
    # ⚠ remap_area build key bằng tỉnh CÓ prefix ("thanh pho da nang") ≠ bảng remap ("da nang") → strip
    # prefix tỉnh TRƯỚC khi remap; _province_label gắn lại "Thành phố/Tỉnh" sau.
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


def _gender_from_cccd(value: Any) -> str | None:
    """Giới tính suy từ CCCD 12 số (chữ số thứ 4 mã hoá thế kỷ + giới tính: chẵn=Nam, lẻ=Nữ).

    Đây là DỮ LIỆU TẤT ĐỊNH nằm sẵn trong số định danh, không phải suy đoán từ tên.
    """
    digits = _identity(value) or ""
    if len(digits) != 12:
        return None
    return "Nam" if int(digits[3]) % 2 == 0 else "Nữ"


# Dòng (a) mục 9 của đơn in sẵn nhãn "Họ và tên vợ (hoặc chồng)" — người dân KHÔNG viết quan hệ ở dòng
# này, nên mọi giá trị "Vợ"/"Chồng" đọc ra chỉ là một nửa nhãn in sẵn, không phải bằng chứng.
_QUANHE_VO_CHONG_MO_HO = {"vo", "chong", "vo (hoac chong)", "vo hoac chong", "vo/chong", "vo chong"}
_QUANHE_LABEL_GOC = "Vợ (hoặc chồng)"


def _quan_he_vo_chong(member_identity: Any, applicant_identity: Any) -> str:
    """Chốt "Vợ" hay "Chồng" cho dòng (a) bằng CCCD, không đoán theo tên đệm.

    Ưu tiên CCCD của CHÍNH thành viên đó; không đọc được thì lấy CCCD người viết đơn rồi đảo vai. Cả hai
    đều không có → trả nguyên nhãn in trên đơn để cán bộ tự chọn, TUYỆT ĐỐI không mặc định "Vợ".
    """
    gender = _gender_from_cccd(member_identity)
    if gender:
        return "Chồng" if gender == "Nam" else "Vợ"
    applicant_gender = _gender_from_cccd(applicant_identity)
    if applicant_gender:
        return "Vợ" if applicant_gender == "Nam" else "Chồng"
    return _QUANHE_LABEL_GOC


def _resolve_quan_he(raw: str | None, member_identity: Any, applicant_identity: Any) -> str | None:
    """Chỉ can thiệp dòng vợ/chồng; "Con", "Con dâu", "Cháu"… do người dân tự viết nên giữ nguyên."""
    text = _text(raw)
    if not text:
        return None
    if _fold(text) in _QUANHE_VO_CHONG_MO_HO:
        return _quan_he_vo_chong(member_identity, applicant_identity)
    return text


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


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


# Hình thức đơn → key checkbox tương ứng.
_HINH_THUC_KEY = {"mua": "data[mua]", "thue mua": "data[thuemua]", "thue": "data[thue]"}


def _hinh_thuc_key(value: Any) -> str:
    f = _fold(value)
    if "thue mua" in f:
        return "data[thuemua]"
    if "mua" in f and "thue" not in f:
        return "data[mua]"
    if "thue" in f:
        return "data[thue]"
    return "data[thue]"  # mặc định THUÊ (đúng loại thủ tục phổ biến nhất).


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return _text(item)
    for k in keys:
        if item.get(k) not in (None, "", {}, []):
            return _text(item.get(k))
    return None


def _thuc_trang(value: Any) -> str | None:
    """Chuẩn hóa 'Thực trạng nhà ở' về ĐÚNG option select trên form. Option tĩnh thấy trong HTML: 'Chưa có
    nhà ở thuộc sở hữu của mình'. Đơn hay ghi 'Chưa có quyền sở hữu nhà ở…' (khác chữ) → không khớp fuzzy."""
    text = _text(value)
    if not text:
        return None
    h = _fold(text)
    # Trường hợp phổ biến nhất: chưa có nhà/chưa có quyền sở hữu nhà ở.
    if "chua co" in h and ("nha o" in h or "so huu" in h):
        return "Chưa có nhà ở thuộc sở hữu của mình"
    # Trường hợp khác (diện tích chật, nhà chung…) → giữ nguyên, FE khớp mờ với option API.
    return text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence: int | None = None, default: bool = False) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        if default:
            item["default"] = True
        out.append(item)
        seen.add(seen_key)

    def add_area(province_name, district_name, address_name, area, *, occurrence=None) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
        add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
        add(address_name, _text(area.get("diaChi")), occurrence=occurrence)

    # --- Nhân thân (chính chủ: người nộp = người viết đơn) ---
    name = _text(values.get("NguoiNop_HoTen"))
    identity = _identity(values.get("NguoiNop_SoDinhDanh"))
    birthday = _date(values.get("NguoiNop_NgaySinh"))
    gender = _text(values.get("NguoiNop_GioiTinh"))
    issue_date = _date(values.get("NguoiNop_NgayCap"))
    issue_agency = _issuer(values.get("NguoiNop_NoiCap"))
    phone = _phone(values.get("NguoiNop_DienThoai"))
    thuong_tru = _area(values.get("NguoiNop_ThuongTru"))
    noi_o_hien_tai = _area(values.get("NguoiNop_NoiOHienTai"))
    # Đơn viết tay RẤT hay bỏ trống mục 6 (đăng ký thường trú) mà chỉ ghi mục 5 (nơi ở hiện tại), và hồ sơ
    # nhiều khi không kèm bản scan CCCD → NguoiNop_ThuongTru rỗng. Không có fallback thì CẢ HAI nhóm địa chỉ
    # lấy từ thường trú (Phần I province/district/address occ0 và Phần III province1/district1/address1) bỏ
    # trống — nhìn như "không điền được địa chỉ". Suy ngược từ nơi ở hiện tại (đối xứng với fallback occ1).
    if not thuong_tru:
        thuong_tru = noi_o_hien_tai

    if not name:
        warnings.append("Thiếu họ tên người viết đơn.")
    if not identity:
        warnings.append("Thiếu số CCCD/định danh người viết đơn.")
    if not thuong_tru:
        warnings.append("Thiếu địa chỉ (thường trú và nơi ở hiện tại đều không đọc được).")

    org_name = _text(values.get("DoanhNghiep_Ten"))
    is_to_chuc = _is_to_chuc(values.get("ChonDoiTuong"), org_name) or bool(org_name)

    # === Phần I: NGƯỜI NỘP (occurrence 0 cho các key trùng) ===
    add("data[chonDoiTuong]", "Tổ chức" if is_to_chuc else "Cá nhân", default=True)
    add("data[fullname]", name, occurrence=0)
    add("data[birthday]", birthday)
    add("data[gender]", gender)
    add("data[identityNumber]", identity, occurrence=0)
    add("data[identityDate]", issue_date, occurrence=0)
    add("data[identityAgency]", issue_agency, occurrence=0)
    add("data[phoneNumber]", phone)
    add("data[nation]", "Việt Nam", default=True)
    add_area("data[province]", "data[district]", "data[address]", thuong_tru, occurrence=0)

    # === Phần I.1: DOANH NGHIỆP (chỉ khi Tổ chức) ===
    if is_to_chuc:
        add("data[organization]", org_name)
        add("data[taxCode]", _identity(values.get("DoanhNghiep_MaSoThue")))
        add("data[nation1]", "Việt Nam", default=True)

    # === Phần II: HÌNH THỨC (checkbox — đúng 1 ô) ===
    add(_hinh_thuc_key(values.get("Don_HinhThuc")), True, default=True)

    # === Phần III: NGƯỜI VIẾT ĐƠN (occurrence 1 cho các key trùng) ===
    add("data[fullname]", name, occurrence=1)
    add("data[identityNumber]", identity, occurrence=1)
    add("data[identityDate]", issue_date, occurrence=1)
    add("data[identityAgency]", issue_agency, occurrence=1)
    add("data[job]", _text(values.get("NguoiNop_NgheNghiep")))
    add("data[workPlace]", _text(values.get("NguoiNop_NoiLamViec")))
    add("data[thuocDoiTuong]", _text(values.get("NguoiNop_ThuocDoiTuong")))
    # Nơi ở hiện tại (occ1) — nếu đơn không tách riêng thì suy từ thường trú (2 nơi thường trùng).
    add_area("data[province]", "data[district]", "data[address]", noi_o_hien_tai or thuong_tru, occurrence=1)
    # Thường trú/tạm trú (key riêng province1/district1/address1).
    add_area("data[province1]", "data[district1]", "data[address1]", thuong_tru)

    # === Phần III.1: DATAGRID thành viên gia đình ===
    tv_list = values.get("ThanhVienGiaDinh")
    if isinstance(tv_list, list):
        for idx, tv in enumerate(tv_list[:_MAX_TV]):
            base = f"data[dtgrid1][{idx}]"
            tv_identity = _identity(_item_text(tv, "soCccd", "identityNumber", "cccd"))
            add(f"{base}[fullname1]", _item_text(tv, "hoTen", "fullname", "hoVaTen"))
            add(f"{base}[identityNumber1]", tv_identity)
            add(f"{base}[identityDate]", _date(_item_text(tv, "ngayCap", "identityDate")))
            add(f"{base}[namsanxuat]", _item_text(tv, "noiCap", "namsanxuat"))         # ⚠ = Nơi cấp.
            # ⚠ = Quan hệ. Dòng vợ/chồng chốt lại bằng CCCD (xem _quan_he_vo_chong).
            add(f"{base}[namsanxuat1]", _resolve_quan_he(
                _item_text(tv, "quanHe", "moiQuanHe", "namsanxuat1"), tv_identity, identity
            ))

    # === Phần III.2: thực trạng nhà ở + cam đoan ===
    add("data[thucTrang]", _thuc_trang(values.get("Don_ThucTrangNhaO")))
    add("data[checkBox]", True, default=True)  # cam đoan chưa từng hưởng chính sách NOXH.

    # === Phần III.3: ký ===
    noi_ky = _text(values.get("Don_NoiKy"))
    add("data[TinTTTe]", _province_label(noi_ky) if noi_ky else None)
    add("data[TDTTK]", _date(values.get("Don_NgayKy")))
    add("data[nguoiLamDon]", name)

    return out, warnings
