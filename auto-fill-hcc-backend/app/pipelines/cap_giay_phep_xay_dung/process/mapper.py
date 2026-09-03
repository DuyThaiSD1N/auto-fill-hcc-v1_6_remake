"""Map construction-permit source facts to Form.io fields."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_giay_phep_xay_dung.process.schema import UI_COMP_BY_NAME

# Ô person mà extension CHỊU TRÁCH NHIỆM điền từ CCCD/đơn của người nộp. Nếu không có dữ liệu để điền
# → phát comp "dom-expect" để FE TÔ ĐỎ (không điền), dù form không đánh dấu ô đó bắt buộc.
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
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("xa ", "phuong ", "thi tran ", "tt ")):
        return text
    # Với form mới sau sáp nhập, đa số địa bàn mẫu là phường; nếu giấy ghi rõ thì giữ nguyên ở nhánh trên.
    return text


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
        return _text(value)
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
    """Trích xuất năm sinh & giới tính từ số CCCD/Căn cước 12 số chuẩn Việt Nam.

    Cấu trúc CCCD 12 số:
    - 3 số đầu: Mã tỉnh/TP
    - Số thứ 4: Giới tính & Thế kỷ (0: Nam 19xx, 1: Nữ 19xx, 2: Nam 20xx, 3: Nữ 20xx,...)
    - Số thứ 5-6: 2 số cuối năm sinh (YY)
    """
    if not identity_num:
        return {}
    digits = re.sub(r"\D+", "", str(identity_num))
    if len(digits) != 12:
        return {}
    gender_digit = int(digits[3])
    yy = digits[4:6]
    gender = "Nam" if gender_digit % 2 == 0 else "Nữ"
    century = 1900 + (gender_digit // 2) * 100
    year = str(century + int(yy))
    return {"year": year, "gender": gender}


def _birthday_from_year(ngay_sinh_val: Any, nam_sinh_val: Any, identity_val: Any = None) -> str | None:
    """Trả ngày sinh để điền vào form:

    - Ưu tiên ngày sinh đầy đủ (dd/mm/yyyy) từ Applicant_NgaySinh (kiểm tra đối chiếu năm với CCCD 12 số nếu có).
    - Nếu năm trong ngay_sinh_val bị sai/lệch so với CCCD 12 số → tự động điều chỉnh năm theo CCCD.
    - Fallback: dùng Applicant_NamSinh hoặc năm trích xuất từ CCCD 12 số (ghép 01/01/YYYY).
    """
    cccd_info = _extract_info_from_cccd(_identity(identity_val))
    cccd_year = cccd_info.get("year")

    full = _date(ngay_sinh_val)
    if full:
        m_year = re.search(r"\b(19|20)\d{2}\b", full)
        if m_year and cccd_year:
            if m_year.group(0) == cccd_year:
                return full
            else:
                # Đọc nhầm năm sinh từ tài liệu khác → thay bằng năm chuẩn trích từ CCCD
                parts = full.split("/")
                if len(parts) == 3:
                    return normalize_date(f"{parts[0]}/{parts[1]}/{cccd_year}")
                return normalize_date(f"01/01/{cccd_year}")
        return full

    # Fallback 1: chỉ có năm sinh Applicant_NamSinh
    nam_text = _text(nam_sinh_val)
    if nam_text:
        m = re.search(r"\b(19|20)\d{2}\b", nam_text)
        if m:
            return normalize_date(f"01/01/{m.group(0)}")

    # Fallback 2: trích năm sinh trực tiếp từ CCCD 12 số
    if cccd_year:
        return normalize_date(f"01/01/{cccd_year}")

    return None


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
    """Chỉ nhận MÃ SỐ DOANH NGHIỆP hợp lệ: 10 chữ số, hoặc mã chi nhánh 10 số-3 số. Loại bỏ mã chứng
    chỉ năng lực (vd 'LAD 00038424') vì form validate theo đúng định dạng này."""
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
    """Suy giới tính từ xưng hô 'Ông'/'Bà' trong OCR text.

    Tìm pattern 'Ông <tên>' hoặc 'Bà <tên>' gần với tên người nộp hồ sơ.
    Nếu tìm thấy → trả 'Nam' hoặc 'Nữ'. Không tìm thấy → None.
    """
    if not ocr_text:
        return None
    text = " ".join(ocr_text.split())
    # Tìm trực tiếp pattern xưng hô kèm tên người nộp
    if name:
        name_folded = _fold(name)
        # Chia tên thành các token để so khớp linh hoạt (họ tên đầy đủ hoặc họ đệm tên)
        name_tokens = name_folded.split()
        last_name = name_tokens[-1] if name_tokens else ""
        for line in re.split(r"[\n;]", ocr_text):
            line_folded = _fold(line)
            if last_name and last_name in line_folded:
                if re.search(r"\b(ong|cac ong)\b", line_folded):
                    return "Nam"
                if re.search(r"\b(ba|cac ba)\b", line_folded):
                    return "Nữ"
    # Fallback: tìm pattern chung nhất — "Ông/Bà:" hoặc "Họ và tên: Ông/Bà ..."
    # trong các dòng khai thông tin người nộp
    patterns_nam = [
        r"(?:ho\s+va\s+ten|ten|nguoi\s+nop|nguoi\s+dai\s+dien)[^\n]{0,30}\bong\b",
        r"\bong\b[^\n]{0,5}(?:" + _fold(name or "") + r")",
        r"kính gởi[^\n]{0,100}\bông\b",
    ]
    patterns_nu = [
        r"(?:ho\s+va\s+ten|ten|nguoi\s+nop|nguoi\s+dai\s+dien)[^\n]{0,30}\bba\b",
        r"\bba\b[^\n]{0,5}(?:" + _fold(name or "") + r")",
        r"kính gởi[^\n]{0,100}\bbà\b",
    ]
    text_folded = _fold(text)
    for pat in patterns_nam:
        if re.search(pat, text_folded):
            return "Nam"
    for pat in patterns_nu:
        if re.search(pat, text_folded):
            return "Nữ"
    # Fallback cuối: đếm tần suất xưng hô Ông/Bà toàn văn bản (loại trừ các từ ghép)
    count_ong = len(re.findall(r"(?<![a-z])ong(?![a-z])", text_folded))
    count_ba = len(re.findall(r"(?<![a-z])ba(?![a-z])", text_folded))
    if count_ong > count_ba and count_ong >= 2:
        return "Nam"
    if count_ba > count_ong and count_ba >= 2:
        return "Nữ"
    return None


def _cap(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if re.search(r"\biii\b", folded):
        return "III"
    if re.search(r"\biv\b", folded):
        return "IV"
    return text.replace("Cấp", "").replace("cấp", "").strip() or text


def _looks_individual_owner(values: dict) -> bool:
    kind = _fold(values.get("ChuDauTu_Loai"))
    if "chu ho" in kind or "ca nhan" in kind:
        return True
    if "chu dau tu" in kind and any(values.get(k) for k in ("ChuDauTu_TenToChuc", "ChuDauTu_MaSoDoanhNghiep")):
        return False
    owner_name = _text(_pick(values.get("ChuHo_HoTen"), values.get("Applicant_HoTen")))
    return bool(owner_name and not any(marker in _fold(owner_name) for marker in ("cong ty", "doanh nghiep", "ubnd")))


def _build_land_lot(values: dict) -> str | None:
    thua = _text(values.get("Dat_ThuaDatSo"))
    to = _text(values.get("Dat_ToBanDoSo"))
    if thua and to:
        return f"{thua} (tờ bản đồ số {to})"
    return thua


def _construction_subtype_value(values: dict) -> str | None:
    """Map child 'Loại công trình' under the fixed non-route top-level group."""
    explicit = _fold(values.get("CongTrinh_Loai"))
    if explicit:
        if "nha o rieng le" in explicit:
            return "Nhà ở riêng lẻ"
        if "nha o" in explicit:
            return "Công trình nhà ở"
        if "ton giao" in explicit or "tin nguong" in explicit:
            return "Công trình tôn giáo, tín ngưỡng"
        if "dan dung" in explicit:
            return "Công trình dân dụng"

    fallback = _fold(values.get("CongTrinh_Ten"))
    if "nha o rieng le" in fallback or "nha o gia dinh" in fallback:
        return "Nhà ở riêng lẻ"
    if "dan dung" in fallback:
        return "Công trình dân dụng"
    if "nha o" in fallback:
        return "Công trình nhà ở"
    return _text(values.get("CongTrinh_Loai"))


def _construction_branch(values: dict, options: dict | None = None) -> str | None:
    """Xác định panel Form.io từ bằng chứng cụ thể, không dùng default cứng.

    Mẫu số 01 có thể liệt kê tất cả loại công trình ở đầu đơn; vì vậy chỉ cụm tiêu đề
    "Sử dụng cho công trình: Nhà ở riêng lẻ" hoặc mục 4.4 có dữ liệu mới đủ mạnh.
    """
    # ƯU TIÊN CAO NHẤT: biến thể do CỔNG/quy trình quyết định (vd thủ tục sửa chữa có 2 form riêng —
    # nhà ở riêng lẻ ↔ công trình — dùng bộ element khác nhau). Nhánh phải khớp FORM đang mở, không chỉ
    # suy từ giấy tờ. options["constructionVariant"] rỗng → auto-detect như cũ (không phá thủ tục cấp mới).
    forced = _fold((options or {}).get("constructionVariant"))
    if forced in {"nha_o_rieng_le", "nha o rieng le", "nha o"}:
        return "nha_o_rieng_le"
    if forced in {"khong_theo_tuyen", "khong theo tuyen"}:
        return "khong_theo_tuyen"

    explicit = _fold(values.get("CongTrinh_Nhanh"))
    if explicit in {"nha_o_rieng_le", "nha o rieng le", "nha o"}:
        return "nha_o_rieng_le"
    if explicit in {"khong_theo_tuyen", "khong theo tuyen", "khong theo tuyen tin nguong ton giao"}:
        return "khong_theo_tuyen"

    kind = _fold(values.get("CongTrinh_Loai"))
    if "nha o rieng le" in kind or "nha o" in kind:
        return "nha_o_rieng_le"
    if any(token in kind for token in ("dan dung", "ton giao", "tin nguong", "khong theo tuyen")):
        return "khong_theo_tuyen"

    ocr = _fold((options or {}).get("_ocr_text", ""))
    if re.search(r"su dung cho cong trinh\s*:\s*nha o rieng le", ocr):
        return "nha_o_rieng_le"
    # OCR có thể mất dấu/chấm ở "4.4." nhưng vẫn giữ cụm nhãn và giá trị sau đó.
    if re.search(r"4\s*[.]?\s*4\s*[.]?\s+doi voi cong trinh nha o rieng le", ocr):
        return "nha_o_rieng_le"
    if "cong trinh khong theo tuyen" in ocr and "doi voi cong trinh nha o rieng le" not in ocr:
        return "khong_theo_tuyen"
    return None


_DESIGN_LEAD_UI_RE = re.compile(
    r"^data\[thietKeXayDung\]\[\d+\]\["
    r"(?:boMonChuTriThietKe|hoVaTenChuTriThietKe|maSoChungChiHanhNgheChuTriThietKe)\]$"
)


def _ui_comp(name: str) -> str | None:
    """Nhận diện field DataGrid động vì số dòng chủ trì không cố định."""
    if _DESIGN_LEAD_UI_RE.fullmatch(name):
        return "dom-input"
    return UI_COMP_BY_NAME.get(name)


def _design_leads(values: dict) -> list[dict[str, str | None]]:
    """Chuẩn hóa và gộp dòng trùng từ danh sách chủ trì do LLM trả về."""
    raw = values.get("ThietKe_ChuTri_DanhSach")
    rows: list[dict[str, str | None]] = []
    row_by_key: dict[tuple[str, str], dict[str, str | None]] = {}

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            row = {
                "boMon": _text(_pick(item.get("boMon"), item.get("bo_mon"), item.get("boMonThietKe"))),
                "hoTen": _text(_pick(item.get("hoTen"), item.get("ho_ten"), item.get("hoVaTen"))),
                "chungChi": _text(_pick(item.get("chungChi"), item.get("maSoChungChi"), item.get("soChungChi"))),
            }
            # Không tạo dòng Form.io vô danh vì sẽ sinh thêm một hàng bắt buộc nhưng không xác định được người.
            if not row["hoTen"]:
                continue
            key = (_fold(row["boMon"]), _fold(row["hoTen"]))
            existing = row_by_key.get(key)
            if existing:
                # Cùng bộ môn + cùng người ở nhiều giấy tờ: chỉ bổ sung phần còn thiếu, không nhân đôi dòng.
                existing["chungChi"] = existing["chungChi"] or row["chungChi"]
                continue
            row_by_key[key] = row
            rows.append(row)

    if rows:
        return rows

    # Chỉ tương thích bộ field CHỦ TRÌ cũ; không được tự nâng CHỦ NHIỆM thành chủ trì một bộ môn.
    legacy_name = _text(values.get("ThietKe_ChuTri_HoTen"))
    legacy_certificate = _text(values.get("ThietKe_ChuTri_ChungChi"))
    if legacy_name:
        return [{
            "boMon": _text(values.get("ThietKe_ChuTri_BoMon")),
            "hoTen": legacy_name,
            "chungChi": legacy_certificate,
        }]
    return []


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    _ = options or {}
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    context = _form_context(options)

    def add(name: str, value, occurrence: int | None = None) -> None:
        # occurrence: khi 1 tên field xuất hiện NHIỀU LẦN trên form (vd data[province]/data[district]
        # có ở CẢ khối người nộp lẫn khối công trình) → FE điền đúng ô thứ <occurrence> theo DOM.
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = _ui_comp(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        out.append(item)
        seen.add(key)

    # HAI NGƯỜI KHÁC NHAU khi có ủy quyền:
    #  - NGƯỜI NỘP HỒ SƠ (khối "thông tin chung": data[fullname]/identity*/phone/address) = người đi
    #    nộp = NGƯỜI ĐƯỢC ỦY QUYỀN (Applicant_*). Không có ủy quyền → chính chủ hộ.
    #  - CHỦ HỘ / CHỦ ĐẦU TƯ (data[tenChuHo]…) = chủ sở hữu công trình (ChuHo_*).
    # (Trước đây gộp cả 2 vào owner_name=ChuHo → điền nhầm chủ hộ vào ô "Họ và tên người nộp".)
    submitter_name = _text(_pick(values.get("Applicant_HoTen"), values.get("ChuHo_HoTen")))
    submitter_identity = _identity(_pick(values.get("Applicant_SoDinhDanh"), values.get("ChuHo_SoDinhDanh")))
    submitter_phone = _phone(_pick(values.get("Applicant_DienThoai"), values.get("ChuHo_DienThoai")))
    submitter_residence = _area(_pick(values.get("Applicant_NoiCuTru"), values.get("Dat_DiaDiemXayDung")))

    owner_name = _text(_pick(values.get("ChuHo_HoTen"), values.get("Applicant_HoTen")))
    owner_identity = _identity(_pick(values.get("ChuHo_SoDinhDanh"), values.get("Applicant_SoDinhDanh")))
    owner_phone = _phone(_pick(values.get("ChuHo_DienThoai"), values.get("Applicant_DienThoai")))

    # Chỉ điền khối người nộp khi trùng tài khoản đăng nhập (tránh đè thông tin người đang đăng nhập).
    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(submitter_identity, submitter_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    area_occ = 0
    if can_fill_applicant:
        add("data[chonDoiTuong]", "Cá nhân" if _looks_individual_owner(values) else "Tổ chức")
        add("data[fullname]", submitter_name)
        # Ngày sinh: ưu tiên ngày đầy đủ (đối chiếu chuẩn năm theo CCCD 12 số); fallback sang CCCD/năm sinh.
        add("data[birthday]", _birthday_from_year(values.get("Applicant_NgaySinh"), values.get("Applicant_NamSinh"), submitter_identity))
        # Giới tính: ưu tiên giá trị LLM; fallback trích từ số CCCD 12 số hoặc từ xưng hô Ông/Bà trong OCR text.
        _cccd_info = _extract_info_from_cccd(submitter_identity)
        _gender_llm = _text(values.get("Applicant_GioiTinh"))
        _gender_inferred = (
            _gender_llm
            or _cccd_info.get("gender")
            or _infer_gender_from_title(
                (options or {}).get("_ocr_text", "") or "",
                submitter_name,
            )
        )
        # Chuẩn hoá giá trị → chỉ chấp nhận "Nam" hoặc "Nữ" (form dropdown)
        if _gender_inferred:
            _g = _fold(_gender_inferred)
            if "nu" in _g or "nu" in _g or _g in ("nu", "n"):
                _gender_inferred = "Nữ"
            elif "nam" in _g or _g == "m":
                _gender_inferred = "Nam"
            else:
                _gender_inferred = None
        add("data[gender]", _gender_inferred)
        add("data[email]", _text(values.get("Applicant_Email")))
        add("data[identityNumber]", submitter_identity)
        add("data[identityDate]", _date(values.get("Applicant_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("Applicant_NoiCap")))
        add("data[phoneNumber]", submitter_phone)
        add("data[nation]", "Việt Nam" if submitter_name or submitter_identity else None)
        if submitter_residence:
            # NƠI CƯ TRÚ NGƯỜI NỘP (khác hoàn toàn địa điểm công trình). data[province]/data[district]
            # xuất hiện 2 lần trên form → occurrence đầu tiên cho KHỐI NGƯỜI NỘP.
            add("data[province]", _province_label(submitter_residence.get("tinh")), occurrence=area_occ)
            add("data[district]", _commune_label(submitter_residence.get("xa")), occurrence=area_occ)
            add("data[address]", _text(submitter_residence.get("diaChi")))
            area_occ += 1

        # Ô person mà EXTENSION CHỊU TRÁCH NHIỆM điền nhưng giấy tờ KHÔNG có dữ liệu (vd giới tính, ngày
        # sinh không đọc được) → phát sentinel comp "dom-expect": FE KHÔNG điền, chỉ TÔ ĐỎ nếu ô đang
        # trống (để user biết phải điền tay) — dù form không đánh dấu ô đó bắt buộc.
        for _name in _EXPECT_PERSON_FIELDS:
            if (_name, None) not in seen:
                out.append({"name": _name, "comp": "dom-expect", "value": ""})
                seen.add((_name, None))

    add("data[kinhGui]", _text(values.get("Don_KinhGui")))

    if _looks_individual_owner(values):
        add("data[loaiHinhChuDauTu]", "chuHo")
        add("data[tenChuHo]", owner_name)
        add("data[soDinhDanhChuHo]", owner_identity)
        add("data[soDienThoaiChuHo]", owner_phone)
    else:
        add("data[loaiHinhChuDauTu]", "chuDauTu")
        add("data[tenChuDauTu]", _text(values.get("ChuDauTu_TenToChuc")))
        add("data[nguoiDaiDien]", _text(values.get("ChuDauTu_NguoiDaiDien")))
        add("data[chucVu]", _text(values.get("ChuDauTu_ChucVu")))
        add("data[maSoDoanhNghiepCDT]", _text(values.get("ChuDauTu_MaSoDoanhNghiep")))
        add("data[soDinhDanhNguoiDaiDien]", owner_identity)
        add("data[soDienThoaiNguoiDaiDien]", owner_phone)

    add("data[loDatSo]", _build_land_lot(values))
    add("data[dienTichLoDat]", _number(values.get("Dat_DienTich")))
    land_area = _area(values.get("Dat_DiaDiemXayDung"))
    if land_area:
        # ĐỊA ĐIỂM CÔNG TRÌNH = cặp Tỉnh/Phường kế tiếp theo thứ tự occurrence.
        add("data[province]", _province_label(land_area.get("tinh")), occurrence=area_occ)
        add("data[district]", _commune_label(land_area.get("xa")), occurrence=area_occ)
        area_occ += 1
    # soNha CHỈ lấy số nhà rõ ràng (Dat_SoNha) — KHÔNG fallback sang diaChi vì diaChi là tên đường
    # ("Đường Vạn Hạnh") sẽ nhồi cả đường vào ô Số nhà (trùng duongPho). Đường/phố lấy diaChi.
    add("data[soNha]", _text(values.get("Dat_SoNha")))
    add("data[duongPho]", _text(_pick(values.get("Dat_DuongPho"), land_area.get("diaChi") if land_area else None)))
    add("data[thoiGianDuKienHoanThanh]", _number(values.get("CongTrinh_ThoiGianDuKienHoanThanh")))

    design_kind = _fold(values.get("LapThietKe_Loai"))
    has_design_org = bool(values.get("ThietKe_ToChuc_Ten") or values.get("ThietKe_ToChuc_MaSo")) or "to chuc" in design_kind
    if has_design_org:
        add("data[toChucCaNhanLapThietKe]", "toChuc")
        add("data[tenDoanhNghiepLapThietKe]", _text(values.get("ThietKe_ToChuc_Ten")))
        # Chỉ điền nếu là MSDN hợp lệ (10 số / 10-3); mã năng lực "LAD…" → bỏ, ô bắt buộc sẽ tô đỏ.
        add("data[maSoDoanhNghiepLapThietKe]", _ma_so_doanh_nghiep(values.get("ThietKe_ToChuc_MaSo")))
        add("data[tenChuNhiemThietKe]", _text(values.get("ThietKe_ChuNhiem_HoTen")))
        add("data[maSoChungChiChuNhiemThietKe]", _text(values.get("ThietKe_ChuNhiem_ChungChi")))
        for index, lead in enumerate(_design_leads(values)):
            add(f"data[thietKeXayDung][{index}][boMonChuTriThietKe]", lead.get("boMon"))
            add(f"data[thietKeXayDung][{index}][hoVaTenChuTriThietKe]", lead.get("hoTen"))
            add(
                f"data[thietKeXayDung][{index}][maSoChungChiHanhNgheChuTriThietKe]",
                lead.get("chungChi"),
            )
    elif values.get("ThietKe_CaNhan_HoTen") or values.get("ThietKe_CaNhan_ChungChi"):
        add("data[toChucCaNhanLapThietKe]", "caNhan")
        add("data[tenCaNhanLapThietKe]", _text(values.get("ThietKe_CaNhan_HoTen")))
        add("data[maSoChungChiCaNhanLapThietKe]", _text(values.get("ThietKe_CaNhan_ChungChi")))

    appraisal_kind = _fold(values.get("ThamTra_Loai"))
    if values.get("ThamTra_ToChuc_Ten") or values.get("ThamTra_ToChuc_MaSo") or "to chuc" in appraisal_kind:
        add("data[toChucCaNhanThamTraThietKe]", "toChuc")
        add("data[tenDoanhNghiepThamTraThietKe]", _text(values.get("ThamTra_ToChuc_Ten")))
        add("data[maSoDoanhNghiepThamTraThietKe]", _text(values.get("ThamTra_ToChuc_MaSo")))
        add("data[tenChuNhiemThamTraThietKeThietKe]", _text(values.get("ThamTra_ChuNhiem_HoTen")))
        add("data[maSoChungChiChuNhiemThamTraThietKe]", _text(values.get("ThamTra_ChuNhiem_ChungChi")))
    elif values.get("ThamTra_CaNhan_HoTen") or values.get("ThamTra_CaNhan_ChungChi"):
        add("data[toChucCaNhanThamTraThietKe]", "caNhan")
        add("data[tenCaNhanThamTraThietKe]", _text(values.get("ThamTra_CaNhan_HoTen")))
        add("data[maSoChungChiCaNhanThamTraThietKe]", _text(values.get("ThamTra_CaNhan_ChungChi")))
    else:
        # Giấy tờ KHÔNG có thông tin thẩm tra (nhà ở riêng lẻ thường không bắt buộc thẩm tra) →
        # mặc định chọn "Cá nhân": nhánh cá nhân không bắt buộc điền tên/mã số chứng chỉ nên vẫn
        # qua được bước sau; nếu để trống radio thì form chặn validate.
        add("data[toChucCaNhanThamTraThietKe]", "caNhan")

    # Top-level "Loại hình công trình" không còn được mặc định. Hai panel có bộ
    # field khác nhau nên phải xác định nhánh trước khi phát mapping.
    construction_branch = _construction_branch(values, options)
    if construction_branch == "nha_o_rieng_le":
        # Select Choices.js LỌC option theo NHÃN (không theo value): FE gõ vào ô search rồi chọn option
        # hiện ra. Phát MÃ số ("7") → search "7" không khớp nhãn nào → "No results found". Phải phát ĐÚNG
        # NHÃN option "Nhà ở riêng lẻ" (value 7) để FE lọc & chọn được.
        add("data[loaiCongTrinh]", "Nhà ở riêng lẻ")
        add("data[tenCongTrinhNhaO]", _text(values.get("CongTrinh_Ten")) or "Nhà ở riêng lẻ")
        add("data[capCongTrinhNhaO]", _cap(values.get("CongTrinh_Cap")))
        add("data[khoangLuiNhaO]", _number(values.get("CongTrinh_KhoangLui")))
        add("data[cotXayDungNhaO]", _number(values.get("CongTrinh_CotXayDung")))
        add("data[dienTichXayDungTang1NhaO]", _number(values.get("CongTrinh_DienTichXayDung")))
        add("data[tongDienTichSanNhaO]", _number(values.get("CongTrinh_TongDienTichSan")))
        add("data[chiTietDienTichSanNhaO]", _text(values.get("CongTrinh_ChiTietDienTichSan")))
        add("data[chieuCaoCongTrinhNhaO]", _number(values.get("CongTrinh_ChieuCao")))
        add("data[chiTietChieuCaoNhaO]", _text(values.get("CongTrinh_ChiTietChieuCao")))
        add("data[soTangNhaO]", _text(values.get("CongTrinh_SoTang")))
        add("data[chiTietSoTangNhaO]", _text(values.get("CongTrinh_ChiTietSoTang")))
    elif construction_branch == "khong_theo_tuyen":
        # Phát NHÃN option (value 1) thay vì mã "1" — lý do như nhánh nhà ở riêng lẻ ở trên.
        add("data[loaiCongTrinh]", "Công trình không theo tuyến, tín ngưỡng, tôn giáo")
        add("data[tenCongTrinhKhongTheoTuyen]", _text(values.get("CongTrinh_Ten")))
        add("data[loaiCongTrinhKhongTheoTuyen]", _construction_subtype_value(values))
        add("data[capCongTrinhKhongTheoTuyen]", _cap(values.get("CongTrinh_Cap")))
        add("data[dienTichXayDungKhongTheoTuyen]", _number(values.get("CongTrinh_DienTichXayDung")))
        add("data[cotXayDungKhongTheoTuyen]", _number(values.get("CongTrinh_CotXayDung")))
        add("data[khoangLuiKhongTheoTuyen]", _number(values.get("CongTrinh_KhoangLui")))
        add("data[tongDienTichSanKhongTheoTuyen]", _number(values.get("CongTrinh_TongDienTichSan")))
        add("data[chiTietDienTichSanKhongTheoTuyen]", _text(values.get("CongTrinh_ChiTietDienTichSan")))
        add("data[chieuCaoCongTrinhKhongTheoTuyen]", _number(values.get("CongTrinh_ChieuCao")))
        add("data[chiTietChieuCaoCongTrinhKhongTheoTuyen]", _text(values.get("CongTrinh_ChiTietChieuCao")))
        add("data[soTangCongTrinhKhongTheoTuyen]", _number(values.get("CongTrinh_SoTang")))
        add("data[chiTietSoTangKhongTheoTuyen]", _text(values.get("CongTrinh_ChiTietSoTang")))
    else:
        warnings.append("Chưa xác định được nhánh loại hình công trình; không tự chọn mặc định.")

    if not owner_name or not owner_identity:
        warnings.append("Thiếu thông tin chủ hộ/người nộp từ đơn hoặc CCCD.")
    if not values.get("CongTrinh_DienTichXayDung") and not values.get("CongTrinh_TongDienTichSan"):
        warnings.append("Chưa đọc được thông số xây dựng chính từ đơn/bản vẽ.")
    return out, warnings
