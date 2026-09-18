"""Map source facts → Form.io data[...] cho "Cấp điều chỉnh giấy phép xây dựng" (cổng Bộ Xây dựng).

Tái sử dụng khối NGƯỜI NỘP / CHỦ HỘ-CHỦ ĐẦU TƯ / ĐỊA ĐIỂM của cap_giay_phep_xay_dung; BỎ phần loại/cấp
công trình + thiết kế/thẩm tra; THÊM khối GPXD đã cấp + nội dung điều chỉnh + khối tổ chức người nộp.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process.schema import UI_COMP_BY_NAME

# Ô nhân thân người nộp mà extension chịu trách nhiệm điền; thiếu dữ liệu → phát "dom-expect" (FE tô đỏ).
_EXPECT_PERSON_FIELDS = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return _full_address(value)
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _multiline_text(value: Any) -> str | None:
    """Giữ NGUYÊN xuống dòng (cho textarea nội dung điều chỉnh): gộp khoảng trắng mỗi dòng, bỏ dòng rỗng."""
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


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+",
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
    prefix = "Thành phố" if folded in city_markers else "Tỉnh"
    return f"{prefix} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _field(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        raw = value.get(key)
        if raw not in (None, "", {}, []):
            return _text(raw)
    return None


def _full_address(value: Any) -> str | None:
    if isinstance(value, str):
        return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "soNha", "thonXom"),
        _field(value, "xa", "phuongXa", "phuong"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


def _parse_area_text(value: str) -> dict | None:
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
        res = _parse_area_text(value)
        return remap_area(res) if res else None
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out)


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
    if not m:
        return None
    return normalize_date(m.group(0))


def _extract_info_from_cccd(identity_num: str | None) -> dict[str, str]:
    """Trích năm sinh & giới tính từ số CCCD 12 số chuẩn Việt Nam (số thứ 4 = giới tính+thế kỷ, 5-6 = YY)."""
    if not identity_num:
        return {}
    digits = re.sub(r"\D+", "", str(identity_num))
    if len(digits) != 12:
        return {}
    gender_digit = int(digits[3])
    yy = digits[4:6]
    gender = "Nam" if gender_digit % 2 == 0 else "Nữ"
    century = 1900 + (gender_digit // 2) * 100
    return {"year": str(century + int(yy)), "gender": gender}


def _birthday_from_year(ngay_sinh_val: Any, nam_sinh_val: Any, identity_val: Any = None) -> str | None:
    """Ngày sinh để điền vào form — CHỈ khi đọc được NGÀY/THÁNG/NĂM đầy đủ trên giấy tờ.

    - Có ngày đầy đủ: nếu năm lệch với năm mã hoá trong CCCD 12 số thì giữ ngày/tháng đã đọc và chỉnh
      lại NĂM theo CCCD (năm là dữ liệu tất định trong số định danh, không phải suy đoán).
    - ⚠ TUYỆT ĐỐI KHÔNG ghép "01/01/<năm>" khi chỉ biết NĂM SINH (từ Applicant_NamSinh hoặc từ 3 chữ
      số đầu của CCCD): ngày và tháng lúc đó là BỊA. Hồ sơ thật CCCD 026077005820 từng bị điền
      "01/01/1977" trong khi không giấy tờ nào ghi ngày sinh. Chỉ biết năm → trả None, mapper phát
      "dom-expect" để extension tô đỏ ô Ngày sinh cho cán bộ tự nhập.
      (Cùng fix đã áp cho cap_giay_phep_xay_dung — xem [[gpxd-khong-bia-ngay-sinh-va-chu-nhiem-thiet-ke]].)
    """
    cccd_year = _extract_info_from_cccd(_identity(identity_val)).get("year")

    full = _date(ngay_sinh_val)
    if not full:
        return None

    parts = full.split("/")
    m_year = re.search(r"\b(19|20)\d{2}\b", full)
    if m_year and cccd_year and m_year.group(0) != cccd_year and len(parts) == 3:
        return normalize_date(f"{parts[0]}/{parts[1]}/{cccd_year}")
    return full


def _number(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:[,.]\d+)?", text)
    if not m:
        return None
    num = m.group(0).replace("+", "").replace(",", ".")
    if "." in num:
        num = num.rstrip("0").rstrip(".")
    elif re.fullmatch(r"-?\d+", num):
        num = str(int(num))
    return num or None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _ma_so_doanh_nghiep(value: Any) -> str | None:
    """Chỉ nhận mã số DN hợp lệ: 10 chữ số hoặc 10 số-3 số; loại mã chứng chỉ năng lực (form validate)."""
    text = _text(value)
    if not text:
        return None
    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d{10}", compact) or re.fullmatch(r"\d{10}-\d{3}", compact):
        return compact
    return None


def _same_person(doc_id: Any, doc_name: Any, ctx_id: Any, ctx_name: Any) -> bool:
    did, cid = _identity(doc_id), _identity(ctx_id)
    if did and cid:
        return did == cid
    dname, cname = _fold(doc_name), _fold(ctx_name)
    return bool(dname and cname and dname == cname)


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _infer_gender_from_title(ocr_text: str, name: str | None) -> str | None:
    if not ocr_text:
        return None
    if name:
        last_name = (_fold(name).split() or [""])[-1]
        for line in re.split(r"[\n;]", ocr_text):
            lf = _fold(line)
            if last_name and last_name in lf:
                if re.search(r"\b(ong|cac ong)\b", lf):
                    return "Nam"
                if re.search(r"\b(ba|cac ba)\b", lf):
                    return "Nữ"
    return None


def _looks_individual_owner(values: dict) -> bool:
    kind = _fold(values.get("ChuDauTu_Loai"))
    if "chu ho" in kind or "ca nhan" in kind:
        return True
    if "chu dau tu" in kind and any(values.get(k) for k in ("ChuDauTu_TenToChuc", "ChuDauTu_MaSoDoanhNghiep")):
        return False
    owner_name = _text(_pick(values.get("ChuHo_HoTen"), values.get("Applicant_HoTen")))
    return bool(owner_name and not any(m in _fold(owner_name) for m in ("cong ty", "doanh nghiep", "ubnd")))


def _build_land_lot(values: dict) -> str | None:
    thua = _text(values.get("Dat_ThuaDatSo"))
    to = _text(values.get("Dat_ToBanDoSo"))
    if thua and to:
        return f"{thua} (tờ bản đồ số {to})"
    return thua


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()
    context = _form_context(options)

    def add(name: str, value, occurrence: int | None = None) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        out.append(item)
        seen.add(key)

    # NGƯỜI NỘP (khối thông tin chung) vs CHỦ HỘ/CHỦ ĐẦU TƯ (đứng tên công trình).
    submitter_name = _text(_pick(values.get("Applicant_HoTen"), values.get("ChuHo_HoTen")))
    submitter_identity = _identity(_pick(values.get("Applicant_SoDinhDanh"), values.get("ChuHo_SoDinhDanh")))
    submitter_phone = _phone(_pick(values.get("Applicant_DienThoai"), values.get("ChuHo_DienThoai")))
    submitter_residence = _area(_pick(values.get("Applicant_NoiCuTru"), values.get("Dat_DiaDiemXayDung")))

    owner_name = _text(_pick(values.get("ChuHo_HoTen"), values.get("Applicant_HoTen")))
    owner_identity = _identity(_pick(values.get("ChuHo_SoDinhDanh"), values.get("Applicant_SoDinhDanh")))
    owner_phone = _phone(_pick(values.get("ChuHo_DienThoai"), values.get("Applicant_DienThoai")))

    # Người nộp là tổ chức CHỈ khi chủ đầu tư cũng là tổ chức (không phải chủ hộ cá nhân). Chặn bẫy: đơn
    # vị THIẾT KẾ/tư vấn (luôn xuất hiện trong hồ sơ thiết kế) hay bị LLM nhét vào ToChucNop_* → nếu chủ
    # đầu tư là cá nhân/hộ gia đình thì BỎ khối tổ chức, ép chonDoiTuong='Cá nhân'.
    owner_is_individual = _looks_individual_owner(values)
    org_name = _text(values.get("ToChucNop_Ten"))
    org_tax = _ma_so_doanh_nghiep(values.get("ToChucNop_MaSoThue")) or _identity(values.get("ToChucNop_MaSoThue"))
    is_org_submitter = bool(org_name or org_tax) and not owner_is_individual

    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(submitter_identity, submitter_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    area_occ = 0
    if can_fill_applicant:
        add("data[chonDoiTuong]", "Tổ chức" if is_org_submitter else "Cá nhân")
        add("data[fullname]", submitter_name)
        add("data[birthday]", _birthday_from_year(values.get("Applicant_NgaySinh"), values.get("Applicant_NamSinh"), submitter_identity))
        cccd_info = _extract_info_from_cccd(submitter_identity)
        gender = (
            _text(values.get("Applicant_GioiTinh"))
            or cccd_info.get("gender")
            or _infer_gender_from_title((options or {}).get("_ocr_text", "") or "", submitter_name)
        )
        if gender:
            g = _fold(gender)
            gender = "Nữ" if "nu" in g else ("Nam" if "nam" in g else None)
        add("data[gender]", gender)
        add("data[email]", _text(values.get("Applicant_Email")))
        add("data[identityNumber]", submitter_identity)
        add("data[identityDate]", _date(values.get("Applicant_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("Applicant_NoiCap")))
        add("data[phoneNumber]", submitter_phone)
        add("data[nation]", "Việt Nam" if submitter_name or submitter_identity else None)
        if submitter_residence:
            add("data[province]", _province_label(submitter_residence.get("tinh")), occurrence=area_occ)
            add("data[district]", _commune_label(submitter_residence.get("xa")), occurrence=area_occ)
            add("data[address]", _text(submitter_residence.get("diaChi")))
            area_occ += 1
        # Ô nhân thân người nộp không bóc tách được → phát dom-expect (FE tô đỏ ô trống, nhắc điền tay).
        for _name in _EXPECT_PERSON_FIELDS:
            if (_name, None) not in seen:
                out.append({"name": _name, "comp": "dom-expect", "value": ""})
                seen.add((_name, None))

    # Khối TỔ CHỨC người nộp (chỉ khi Phần I chọn 'Tổ chức').
    if is_org_submitter:
        add("data[organization]", org_name)
        add("data[taxCode]", org_tax)
        add("data[organizationPhoneNumber]", _phone(values.get("ToChucNop_DienThoai")))
        org_area = _area(values.get("ToChucNop_DiaChi"))
        if org_area:
            add("data[nation1]", "Việt Nam")
            add("data[province1]", _province_label(org_area.get("tinh")), occurrence=area_occ)
            add("data[district1]", _commune_label(org_area.get("xa")), occurrence=area_occ)
            add("data[address1]", _text(org_area.get("diaChi")))
            area_occ += 1

    # Khối CHỦ HỘ / CHỦ ĐẦU TƯ.
    if owner_is_individual:
        add("data[loaiHinhChuDauTu]", "chuHo")
        add("data[tenChuHo]", owner_name)
        add("data[soDinhDanhChuHo]", owner_identity)
        add("data[soDienThoaiChuHo]", owner_phone)
    else:
        add("data[loaiHinhChuDauTu]", "chuDauTu")
        add("data[tenChuDauTu]", _text(_pick(values.get("ChuDauTu_TenToChuc"), owner_name)))
        add("data[nguoiDaiDien]", _text(values.get("ChuDauTu_NguoiDaiDien")))
        add("data[chucVu]", _text(values.get("ChuDauTu_ChucVu")))
        add("data[maSoDoanhNghiepCDT]", _ma_so_doanh_nghiep(values.get("ChuDauTu_MaSoDoanhNghiep")))
        add("data[soDinhDanhNguoiDaiDien]", owner_identity)
        add("data[soDienThoaiNguoiDaiDien]", owner_phone)

    # Địa điểm xây dựng.
    add("data[loDatSo]", _build_land_lot(values))
    add("data[dienTichLoDat]", _number(values.get("Dat_DienTich")))
    land_area = _area(values.get("Dat_DiaDiemXayDung"))
    if land_area:
        add("data[province]", _province_label(land_area.get("tinh")), occurrence=area_occ)
        add("data[district]", _commune_label(land_area.get("xa")), occurrence=area_occ)
        area_occ += 1
    add("data[soNha]", _text(values.get("Dat_SoNha")))
    add("data[duongPho]", _text(_pick(values.get("Dat_DuongPho"), land_area.get("diaChi") if land_area else None)))

    # GPXD đã cấp + nội dung điều chỉnh.
    add("data[tenCongTrinh]", _text(values.get("CongTrinh_Ten")))
    add("data[maSoThongTinCongTrinh]", _text(values.get("CongTrinh_MaSoThongTin")))
    add("data[noiDungDeNghiDieuChinh]", _multiline_text(values.get("DieuChinh_NoiDung")))
    add("data[thoiGianDuKienHoanThanh]", _text(values.get("CongTrinh_ThoiGianDuKienHoanThanh")))
    gpxd_so = _text(values.get("GPXD_So"))
    if gpxd_so:
        # Ghi chú hồ sơ (tự nhập) tham chiếu GPXD đang xin điều chỉnh — mặc định vàng để cán bộ soát.
        add("data[tenHoSo]", f"Điều chỉnh Giấy phép xây dựng số {gpxd_so}")

    if not owner_name:
        warnings.append("Thiếu tên chủ đầu tư/chủ hộ đứng tên công trình.")
    if not _multiline_text(values.get("DieuChinh_NoiDung")):
        warnings.append("Chưa bóc tách được Nội dung đề nghị điều chỉnh — vui lòng kiểm tra Đơn (Mẫu số 02).")

    return out, warnings
