"""Map household business source facts to one requested WebForms page."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines.dang_ky_kinh_doanh.process.schema import DEFAULT_PAGE, PAGES
from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.area_remap import remap_area


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def _fold_vi(value: Any) -> str:
    text = _compact_text(value).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _clean_ward(value: Any) -> str:
    text = _compact_text(value)
    if not text:
        return ""

    # Form HkdOnline tự có tiền tố trong option ("Phường ...", "Xã ...").
    # Mapper chỉ trả phần tên riêng để FE hiện tại match được cả option có/không có tiền tố.
    text = re.sub(r"\s*[-–—‐‑]+\s*", " - ", text).strip()
    text = re.sub(
        r"^\s*(?:phường|phuong|ph\.?|xã|xa|thị\s+trấn|thi\s+tran|đặc\s+khu|dac\s+khu|tt\.?|p\s*\.?)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    folded = _fold_vi(text)
    packed = folded.replace(" ", "")
    if "tan" in packed and ("phong" in packed or "phon" in packed or "phony" in packed):
        return "Tân Phong"
    if ("doan" in packed or "oan" in packed) and "ket" in packed:
        return "Đoàn Kết"

    # KHÔNG fuzzy-match tên xã sang danh sách cứng: FE đã khớp theo option THẬT trên cổng
    # (substring, đã fold dấu). Fuzzy trước đây map nhầm "Xuân Hương" → "Tân Phong" (ratio ≥ .68)
    # → cổng không có option "Tân Phong" nên không điền được. Chỉ trả tên đã bỏ tiền tố.
    return text


def _clean_phone(value: Any) -> str:
    text = _compact_text(value)
    if not text:
        return ""
    text = text.translate(str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "I": "1", "l": "1"}))
    prefix = "+" if text.strip().startswith("+") else ""
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8:
        return ""
    # Khôi phục số 0 đứng đầu cho số VN khi OCR làm rớt (số di động 10 chữ số bắt đầu bằng 0).
    if not prefix:
        if digits.startswith("84") and len(digits) in (11, 12):
            digits = "0" + digits[2:]
        elif len(digits) == 9 and digits[0] in "35789":
            digits = "0" + digits
    return prefix + digits


def _clean_email(value: Any) -> str:
    text = _compact_text(value).lower()
    if not text:
        return ""
    match = re.search(r"[a-z0-9._%+-]*@[a-z0-9.-]+\.[a-z]{2,}", text)
    if not match:
        return ""
    email = match.group(0)
    local, _, domain = email.partition("@")
    if not local or not re.search(r"[a-z0-9]", local) or not domain:
        return ""
    return email


def _currency(value: Any) -> str:
    text = _compact_text(value)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if not digits:
        return text
    return f"{int(digits):,}".replace(",", ".")


def _gender_code(value: Any) -> str:
    folded = _compact_text(value).lower()
    if not folded:
        return ""
    if folded.startswith("nữ") or folded.startswith("nu"):
        return "F"
    return "M"


def _tax_method_code(value: Any) -> str:
    text = _compact_text(value).lower()
    if not text or "kê khai" in text or "ke khai" in text:
        return "DEC"
    return text


def _proper_name(value: Any) -> str:
    """Chuẩn hóa họ tên về dạng viết hoa chữ đầu mỗi từ (giấy thường ghi IN HOA)."""
    text = _compact_text(value)
    if not text:
        return ""
    return " ".join(word.capitalize() for word in text.split())


def _is_same_person(submitter: Any, owner: Any) -> bool:
    """Xác định có phải cùng một người hay không.

    Ưu tiên so sánh số định danh khi có đủ dữ liệu. Nếu không có số định danh,
    dùng tên đã chuẩn hóa. Nếu cả hai đều không có, trả False để tránh nhầm thành
    người tự nộp khi hồ sơ rõ ràng là người nộp thay mặt chủ hộ.
    """
    submitter_id = re.sub(r"\D", "", str(submitter or ""))
    owner_id = re.sub(r"\D", "", str(owner or ""))
    if submitter_id and owner_id:
        return submitter_id == owner_id

    submitter_name = _fold_vi(submitter)
    owner_name = _fold_vi(owner)
    if submitter_name and owner_name:
        return submitter_name == owner_name

    return False


_PERS_SUB_SELF_LABEL = "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh"
_PERS_SUB_AUTHORIZED_LABEL = "Người được ủy quyền"


def _strip_household_prefix(value: Any) -> str:
    text = _compact_text(value)
    return re.sub(r"^\s*hộ\s+kinh\s+doanh\s+", "", text, flags=re.IGNORECASE).strip()


def _clean_business_code(value: Any) -> str:
    """Mã ngành VSIC trên HkdOnline phải là đúng 4 chữ số liền nhau.

    OCR/LLM có thể tách mã viết tay thành "56 10" hoặc "56.10"; cổng chỉ nhận "5610".
    Nếu không thu được đúng 4 chữ số thì bỏ mã, không gửi chuỗi lỗi sang FE.
    """
    digits = re.sub(r"\D", "", _compact_text(value))
    return digits if len(digits) == 4 else ""


def _addr(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        out = {
            "quocGia": _compact_text(value.get("quocGia") or value.get("quoc_gia") or "Việt Nam"),
            "tinh": _compact_text(value.get("tinh") or value.get("province")),
            "xa": _clean_ward(value.get("xa") or value.get("phuongXa") or value.get("ward")),
            "diaChi": _compact_text(value.get("diaChi") or value.get("dia_chi") or value.get("address")),
        }
        # Normalize phường/xã theo bảng sáp nhập đơn vị hành chính
        remapped = remap_area(out)
        if remapped:
            # _clean_ward lại vì remap_area có thể trả tên có tiền tố (vd "Phường Cam Ly")
            xa_remapped = _clean_ward(remapped.get("xa") or out.get("xa") or "")
            out = {**remapped, "xa": xa_remapped}
        return out
    text = _compact_text(value)
    if not text:
        return {}
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) >= 3:
        return {"quocGia": "Việt Nam", "tinh": parts[-1], "xa": _clean_ward(parts[-2]), "diaChi": ", ".join(parts[:-2])}
    if len(parts) == 2:
        return {"quocGia": "Việt Nam", "tinh": parts[-1], "diaChi": parts[0]}
    return {"quocGia": "Việt Nam", "diaChi": text}


def _same_address(a: Any, b: Any) -> bool:
    """Địa chỉ nhận thông báo thuế có trùng địa chỉ trụ sở không.

    - Không kê khai địa chỉ thuế riêng (rỗng) → coi như giống trụ sở.
    - Có kê khai → so khớp tỉnh + xã + diaChi (đã chuẩn hóa). Lệch một phần → coi là khác
      (an toàn hơn: thà điền địa chỉ còn hơn bỏ sót).
    """
    aa = _addr(a)
    if not aa:
        return True
    bb = _addr(b)
    if not bb:
        return False
    return all(_fold_vi(aa.get(k)) == _fold_vi(bb.get(k)) for k in ("tinh", "xa", "diaChi"))


def _business_line_text(values: dict[str, Any]) -> str:
    rows = values.get("NganhNghe_DanhSach")
    if isinstance(rows, list):
        lines: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                item = _compact_text(row)
            else:
                ma = _clean_business_code(row.get("ma"))
                ten = _compact_text(row.get("ten"))
                item = f"{ma} - {ten}" if ma and ten else (ma or ten)
            if item:
                lines.append(item)
        if lines:
            return "\n".join(lines)
    ma = _clean_business_code(values.get("NganhNghe_MaChinh"))
    ten = _compact_text(values.get("NganhNghe_TenChinh"))
    return f"{ma} - {ten}" if ma and ten else (ma or ten)


def _all_business_codes(values: dict[str, Any]) -> list[str]:
    """Tất cả MÃ ngành (giữ thứ tự, bỏ trùng). Mã chính đứng đầu nếu chưa có trong danh sách."""
    out: list[str] = []
    rows = values.get("NganhNghe_DanhSach")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                ma = _clean_business_code(row.get("ma"))
                if ma and ma not in out:
                    out.append(ma)
    direct = _clean_business_code(values.get("NganhNghe_MaChinh"))
    if direct and direct not in out:
        out.insert(0, direct)
    return out


def _business_line_items(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Danh sách ngành kèm tên OCR để FE bổ sung mô tả khi tên chính thức của mã quá chung.

    Cổng HkdOnline thêm ngành theo MÃ VSIC. Sau khi thêm, portal tự hiển thị tên chuẩn theo mã.
    Nếu giấy ghi tên cụ thể hơn (vd "Dịch vụ phục vụ đồ uống (cà phê)" cho mã 5630),
    extension cần giữ tên OCR này để điền vào ô mô tả của dòng ngành tương ứng.
    """
    out: list[dict[str, Any]] = []
    by_code: dict[str, dict[str, Any]] = {}

    rows = values.get("NganhNghe_DanhSach")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = _clean_business_code(row.get("ma"))
            if not code or code in by_code:
                continue
            item = {
                "code": code,
                "name": _compact_text(row.get("ten")),
                "main": bool(row.get("chinh")),
            }
            out.append(item)
            by_code[code] = item

    direct = _clean_business_code(values.get("NganhNghe_MaChinh"))
    direct_name = _compact_text(values.get("NganhNghe_TenChinh"))
    if direct:
        if direct in by_code:
            if direct_name and not by_code[direct].get("name"):
                by_code[direct]["name"] = direct_name
            by_code[direct]["main"] = True
        else:
            out.insert(0, {"code": direct, "name": direct_name, "main": True})

    return out


def _main_business_code(values: dict[str, Any]) -> str:
    direct = _clean_business_code(values.get("NganhNghe_MaChinh"))
    if direct:
        return direct
    rows = values.get("NganhNghe_DanhSach")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = _clean_business_code(row.get("ma"))
            if row.get("chinh") and code:
                return code
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = _clean_business_code(row.get("ma"))
            if code:
                return code
    return ""


def enrich(fields: list[dict], *, page: str | None = None) -> list[dict]:
    values = _by_name(fields)
    selected_page = page or DEFAULT_PAGE
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, comp: str, value: Any) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_address(prefix: str, value: Any) -> None:
        address = _addr(value)
        if not address:
            return
        add(f"{prefix}$COUNTRY_IDFld", "dom-select", address.get("quocGia") or "Việt Nam")
        add(f"{prefix}$CITY_IDFld", "dom-select", address.get("tinh"))
        add(f"{prefix}$WARD_IDFld", "dom-select", address.get("xa"))
        add(f"{prefix}$STREET_NUMBERFld", "dom-input", address.get("diaChi"))

    if selected_page == "hinh-thuc-dang-ky":
        add("ctl00$C$REORGCtl$REORG_TYPE_IDFld", "dom-select", values.get("HinhThucDangKy") or "Thành lập mới")

    elif selected_page == "dia-chi":
        add_address("ctl00$C$ADDRCtl", values.get("TruSo_DiaChi"))
        add("ctl00$C$DCONTClt$HO_PHONEFld", "dom-input", _clean_phone(values.get("TruSo_DienThoai")))
        add("ctl00$C$DCONTClt$HO_FAXFld", "dom-input", values.get("TruSo_Fax"))
        add("ctl00$C$DCONTClt$HO_EMAILFld", "dom-input", _clean_email(values.get("TruSo_Email")))
        add("ctl00$C$DCONTClt$HO_URLFld", "dom-input", values.get("TruSo_Website"))

    elif selected_page == "nganh-nghe-kinh-doanh":
        items = _business_line_items(values)
        codes = [item["code"] for item in items] or _all_business_codes(values)
        main_code = _main_business_code(values)
        # Fill-tất-cả (extension) đọc __businessLines để thêm LẦN LƯỢT mọi mã + set ngành chính.
        # `items` giữ tên ngành trên giấy để FE điền mô tả nếu tên portal theo mã không trùng.
        if codes:
            add("__businessLines", "raw", {"codes": codes, "main": main_code, "items": items})
        # Giữ cho luồng fill-từng-trang cũ: điền 1 mã chính vào ô nhập.
        if main_code:
            add("ctl00$C$newBusinessLineCode", "dom-input", main_code)
        elif not codes:
            add("ctl00$C$BUSINESS_ACT_TEXTFld", "dom-input", _business_line_text(values))

    elif selected_page == "ten-ho-kinh-doanh":
        add("ctl00$C$DROP_NAME_TYPE", "dom-select", "HỘ KINH DOANH")
        # Tên hộ kinh doanh nằm sau "HỘ KINH DOANH" trên giấy; nếu trống thì thường là tên chủ hộ.
        ten_ho = _strip_household_prefix(values.get("HoKinhDoanh_Ten")) or _compact_text(values.get("ChuHo_HoTen")).upper()
        add("ctl00$C$NAMEFld", "dom-input", ten_ho)
        add("ctl00$C$NAME_FFld", "dom-input", values.get("HoKinhDoanh_TenNuocNgoai"))
        add("ctl00$C$SHORT_NAMEFld", "dom-input", values.get("HoKinhDoanh_TenVietTat"))

    elif selected_page == "chu-ho-kinh-doanh":
        add("ctl00$C$OWNER_TYPE_RbBox", "dom-radio", "P")
        add("ctl00$C$OWN_PCtl$PERSCtl$FULL_NAMEFld", "dom-input", _proper_name(values.get("ChuHo_HoTen")))
        add("ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld", "dom-radio", _gender_code(values.get("ChuHo_GioiTinh")))
        add("ctl00$C$OWN_PCtl$PERSCtl$DATE_OF_BIRTHFld", "dom-date", normalize_date(values.get("ChuHo_NgaySinh")))
        add("ctl00$C$OWN_PCtl$PERSCtl$PERS_DOC_NOFld", "dom-input", values.get("ChuHo_SoDinhDanh"))
        add_address("ctl00$C$OWN_PCtl$PERSCtl$ADDRCCtl", values.get("ChuHo_DiaChi"))
        add("ctl00$C$OWN_PCtl$PERSCtl$PHONEFld", "dom-input", _clean_phone(values.get("ChuHo_DienThoai")))
        add("ctl00$C$OWN_PCtl$PERSCtl$FAXFld", "dom-input", values.get("ChuHo_Fax"))
        add("ctl00$C$OWN_PCtl$PERSCtl$EMAILFld", "dom-input", _clean_email(values.get("ChuHo_Email")))
        add("ctl00$C$OWN_PCtl$PERSCtl$URLFld", "dom-input", values.get("ChuHo_Website"))

    elif selected_page == "thong-tin-ve-von":
        add("ctl00$C$CPT_CHARTER_AMOUNTFld", "dom-input", _currency(values.get("Von_SoTien")))

    elif selected_page == "thong-tin-ve-thue":
        # Địa chỉ nhận thông báo thuế:
        # - Giống địa chỉ trụ sở (hoặc không kê khai riêng) → chọn radio "Giống địa chỉ trụ sở
        #   chính" (value "1"), KHÔNG điền khối địa chỉ (form sẽ tự ẩn).
        # - Khác → radio "Địa chỉ khác" (value "0", form check sẵn) + điền khối địa chỉ.
        # Điện thoại/email luôn điền bình thường ở dưới.
        tax_addr = values.get("Thue_DiaChiNhanThongBao")
        if _same_address(tax_addr, values.get("TruSo_DiaChi")):
            add("ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld", "dom-radio", "1")
        else:
            add("ctl00$C$UC_DW_TAXEditCtl$REP_RECV_ADDR_TYPEFld", "dom-radio", "0")
            add_address("ctl00$C$UC_DW_TAXEditCtl$ADDRCtl", tax_addr)
        add("ctl00$C$UC_DW_TAXEditCtl$REP_RECEIVER_PHONEFld", "dom-input", _clean_phone(values.get("Thue_DienThoai")))
        add("ctl00$C$UC_DW_TAXEditCtl$REP_RECEIVER_FAXFld", "dom-input", values.get("Thue_Fax"))
        add("ctl00$C$UC_DW_TAXEditCtl$REP_RECEIVER_EMAILFld", "dom-input", _clean_email(values.get("Thue_Email")))
        add("ctl00$C$UC_DW_TAXEditCtl$BUSINESS_START_DATEFld", "dom-date", normalize_date(values.get("Thue_NgayBatDau")))
        add("ctl00$C$UC_DW_TAXEditCtl$TOTAL_OF_LABORSFld", "dom-input", values.get("Thue_SoLaoDong"))
        add("ctl00$C$UC_DW_TAXEditCtl$TAX_CAL_METHOD_IDRbBox", "dom-radio", _tax_method_code(values.get("Thue_PhuongPhapTinh")))

    elif selected_page == "nguoi-nop-ho-so":
        # Xác định vai trò người nộp
        has_multiple_cccd = values.get("HasMultipleCCCD", False)
        is_self = not has_multiple_cccd
        
        pers_sub_role = _PERS_SUB_SELF_LABEL if is_self else _PERS_SUB_AUTHORIZED_LABEL
        add("ctl00$C$PERS_SUBGroup", "dom-radio", pers_sub_role)
        
        # Điền thông tin chủ hộ
        add("ctl00$C$PERSCtl$FULL_NAMEFld", "dom-input", _proper_name(values.get("ChuHo_HoTen")))
        add("ctl00$C$PERSCtl$DATE_OF_BIRTHFld", "dom-date", normalize_date(values.get("ChuHo_NgaySinh")))
        add("ctl00$C$PERSCtl$PERS_DOC_NOFld", "dom-input", values.get("ChuHo_SoDinhDanh"))
        
        # SĐT/email để extension tự điền khi user click "Sao chép tài khoản"

    return out


def enrich_all(fields: list[dict]) -> dict[str, list[dict]]:
    """Map 1 bộ compact facts thành field cho TẤT CẢ trang (fill 8 trang trong 1 lần).

    Trả {page_key: [ui_fields]} theo đúng thứ tự PAGES để extension lặp: fill → lưu → sang trang.
    """
    return {p["key"]: enrich(fields, page=p["key"]) for p in PAGES}
