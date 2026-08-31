"""Map facts "thành lập công ty TNHH hai thành viên trở lên" sang field UI của MỘT trang WebForms.

Tên control lấy nguyên văn từ cột `formcontrolname / field-key` của bảng đặc tả 9 sheet (đọc từ HTML
thật của cổng dangkyquamang.dkkd.gov.vn). Bảng ghi theo dạng ID (`C_MEM_PCtl_PERSCtl_FULL_NAMEFld`),
còn extension khớp theo NAME nên ở đây đổi sang `ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld`: mỗi đoạn
container ngăn bằng `$`, phần đuôi `..._IDFld`/`..._NAMEFld` giữ nguyên dấu gạch dưới.

LƯU Ý khi đối chiếu với pipeline công ty cổ phần:
  - khối liên hệ trụ sở là `DCONTCtl` (HkdOnline viết `DCONTClt`);
  - các bảng lặp dùng chỉ số `ctl02..ctlNN` theo ĐÚNG thứ tự dòng in trên form, dòng cuối là "Tổng"
    do cổng tự cộng (disabled) nên KHÔNG bao giờ điền;
  - ba ô checkbox của trang thuế ở bảng đặc tả này là `..._IDId` (bản CTCP chép thành `IDIdl`/`IDld`/
    `IDIdd`); dùng theo bảng đặc tả và khai thêm alias để không hụt ô nếu cổng render kiểu kia.

Radio: extension khớp theo VALUE hoặc theo NHÃN hiển thị. Ô nào bảng đặc tả không cho biết value
(vd "Giống địa chỉ trụ sở chính") thì gửi thẳng NHÃN tiếng Việt — an toàn hơn là đoán mã 0/1.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.schema import DEFAULT_PAGE, PAGES


# --------------------------------------------------------------------------- helpers
def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {f.get("name"): f.get("value") for f in fields or [] if f.get("name")}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value if value is not None else "")).strip()


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", _text(value).lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").strip()


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value))


def _number(value: Any) -> str:
    """Số tiền/số lượng → chuỗi chỉ chữ số. Cổng tự chèn dấu phân cách khi hiển thị."""
    text = _text(value)
    if not text:
        return ""
    # "2.000.000.000" / "2,000,000,000" / "2000000000 đồng" → "2000000000"
    return re.sub(r"\D", "", text.split(",")[0] if text.count(",") == 1 and text.count(".") > 1 else text)


def _ratio(value: Any) -> str:
    """Tỷ lệ % → chuỗi số, giữ tối đa 3 chữ số thập phân theo ràng buộc của form."""
    text = _text(value).replace("%", "").strip()
    if not text:
        return ""
    text = text.replace(".", "").replace(",", ".") if text.count(",") == 1 else text
    try:
        return f"{float(text):g}"
    except ValueError:
        return ""


def _phone(value: Any) -> str:
    digits = _digits(value)
    return digits if 8 <= len(digits) <= 15 else ""


def _email(value: Any) -> str:
    text = _text(value).replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) else ""


def _clean_ward(value: Any) -> str:
    return re.sub(r"^\s*(?:phường|xã|thị trấn|đặc khu)\s+", "", _text(value), flags=re.IGNORECASE).strip()


def _clean_city(value: Any) -> str:
    return re.sub(r"^\s*(?:TP\.?|T\.P\.?|Thành\s+phố|Tỉnh)\s+", "", _text(value), flags=re.IGNORECASE).strip()


def _addr(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        out = {
            "quocGia": _text(value.get("quocGia") or value.get("quoc_gia") or "Việt Nam"),
            "tinh": _clean_city(value.get("tinh") or value.get("province")),
            "xa": _clean_ward(value.get("xa") or value.get("phuongXa") or value.get("ward")),
            "diaChi": _text(value.get("diaChi") or value.get("dia_chi") or value.get("address")),
        }
        remapped = remap_area(out)
        if remapped:
            out = {
                **remapped,
                "xa": _clean_ward(remapped.get("xa") or out.get("xa") or ""),
                "tinh": _clean_city(remapped.get("tinh") or out.get("tinh") or ""),
            }
        return out
    text = _text(value)
    if not text:
        return {}
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) >= 3:
        return {"quocGia": "Việt Nam", "tinh": _clean_city(parts[-1]),
                "xa": _clean_ward(parts[-2]), "diaChi": ", ".join(parts[:-2])}
    if len(parts) == 2:
        return {"quocGia": "Việt Nam", "tinh": _clean_city(parts[-1]), "diaChi": parts[0]}
    return {"quocGia": "Việt Nam", "diaChi": text}


def _has_address(value: Any) -> bool:
    address = _addr(value)
    return any(address.get(key) for key in ("tinh", "xa", "diaChi"))


def _same_address(a: Any, b: Any) -> bool:
    left, right = _addr(a), _addr(b)
    if not left or not right:
        return False
    return all(_fold(left.get(k)) == _fold(right.get(k)) for k in ("tinh", "xa", "diaChi"))


def _rows(value: Any) -> list[dict]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _row_by_kind(rows: list[dict], kind: str) -> dict:
    for row in rows:
        if _fold(row.get("loai")) == kind:
            return row
    return {}


def _gender_code(value: Any) -> str:
    gender = _fold(value)
    return "M" if gender == "nam" else ("F" if gender == "nu" else "")


# Thứ tự dòng của các bảng lặp trên form (ctl02 là dòng đầu tiên). Đổi thứ tự ở đây là đổi ánh xạ.
_CAPITAL_SOURCE_ROWS = ["ngan_sach", "tu_nhan", "nuoc_ngoai", "khac"]
_CAPITAL_ASSET_ROWS = ["dong_vn", "ngoai_te", "vang", "quyen_su_dung_dat", "so_huu_tri_tue", "khac"]

_TAX_METHOD_BY_LABEL = {
    "khau tru": "DED",
    "truc tiep tren gtgt": "DAT",
    "truc tiep tren doanh so": "DIR",
    "khong phai nop thue gtgt": "NAT",
}

_ZONE_FIELD_BY_LABEL = {
    "khu cong nghiep": "HO_IN_IZFld",
    "khu che xuat": "HO_IN_EPZFld",
    "khu kinh te": "HO_IN_EZFld",
    "khu cong nghe cao": "HO_IN_HTPFld",
}


def _business_line_items(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Chuẩn hoá bảng ngành nghề: mã 4 chữ số, đánh dấu ngành chính."""
    items: list[dict[str, Any]] = []
    main_code = _digits(values.get("NganhNghe_MaChinh"))
    for row in _rows(values.get("NganhNghe_DanhSach")):
        code = _digits(row.get("ma"))
        name = _text(row.get("ten"))
        if not code and not name:
            continue
        items.append({
            "code": code if len(code) == 4 else "",
            "name": name,
            "main": bool(row.get("chinh")) or (len(code) == 4 and code == main_code),
        })
    if not any(item["main"] for item in items):
        for item in items:
            if item["code"] and item["code"] == main_code:
                item["main"] = True
                break
    return items


def _main_business_code(values: dict[str, Any]) -> str:
    code = _digits(values.get("NganhNghe_MaChinh"))
    if len(code) == 4:
        return code
    for item in _business_line_items(values):
        if item["main"] and item["code"]:
            return item["code"]
    return ""


def _identity_candidates(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Mọi CCCD trong hồ sơ → extension chọn đúng thẻ của tài khoản đang đăng nhập."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in _rows(values.get("Cccd_DanhSach")):
        doc_no = _digits(card.get("soDinhDanh"))
        if not doc_no or doc_no in seen:
            continue
        seen.add(doc_no)
        out.append({
            "fullName": _text(card.get("hoTen")),
            "gender": _text(card.get("gioiTinh")),
            "birthDate": normalize_date(card.get("ngaySinh")) or "",
            "docNo": doc_no,
            "address": _addr(card.get("diaChi")),
        })
    return out


def _address_fields(prefix: str, value: Any) -> list[dict[str, Any]]:
    """Bốn ô địa chỉ của cổng (Quốc gia / Tỉnh / Xã / Số nhà) dưới cùng một container."""
    address = _addr(value)
    if not address:
        return []
    return [
        {"name": f"{prefix}$COUNTRY_IDFld", "comp": "dom-select", "value": address.get("quocGia") or "Việt Nam"},
        {"name": f"{prefix}$CITY_IDFld", "comp": "dom-select", "value": address.get("tinh")},
        {"name": f"{prefix}$WARD_IDFld", "comp": "dom-select", "value": address.get("xa")},
        {"name": f"{prefix}$STREET_NUMBERFld", "comp": "dom-input", "value": address.get("diaChi")},
    ]


def _member_fields(member: dict[str, Any]) -> list[dict[str, Any]]:
    """Field UI cho MỘT thành viên trên form InformationOfMembers.aspx.

    Tách riêng vì cổng nhập mỗi lần MỘT thành viên: extension bấm "Tạo mới" → điền bộ field này →
    Lưu → quay lại danh sách → lặp cho người kế. Mọi tên control vẫn chỉ nằm ở file này.
    """
    base = "ctl00$C$MEM_PCtl"
    person = f"{base}$PERSCtl"
    rows: list[dict[str, Any]] = [
        {"name": f"{person}$FULL_NAMEFld", "comp": "dom-input", "value": member.get("fullName")},
        {"name": f"{person}$GENDER_IDFld", "comp": "dom-radio", "value": member.get("gender")},
        {"name": f"{person}$DATE_OF_BIRTHFld", "comp": "dom-date", "value": member.get("birthDate")},
        {"name": f"{person}$PERS_DOC_NOFld", "comp": "dom-input", "value": member.get("docNo")},
        {"name": f"{person}$NATIONALITY_IDFld", "comp": "dom-select", "value": member.get("nationality")},
        {"name": f"{person}$ETHNIC_IDFld", "comp": "dom-select", "value": member.get("ethnic")},
        # KHÔNG đụng $SET_AUTO_ADRESSFld: cổng để sẵn "Trùng địa chỉ thường trú" (bảng đặc tả cột
        # "Đã điền sẵn"). Chỉ điền bốn ô địa chỉ bên dưới.
        *_address_fields(f"{person}$ADDRCCtl", member.get("address")),
        {"name": f"{person}$PHONEFld", "comp": "dom-input", "value": member.get("phone")},
        {"name": f"{person}$FAXFld", "comp": "dom-input", "value": member.get("fax")},
        {"name": f"{person}$URLFld", "comp": "dom-input", "value": member.get("website")},
        {"name": f"{person}$EMAILFld", "comp": "dom-input", "value": member.get("email")},
        # Vốn góp: rblSetAutoCalAmount để nguyên mặc định "Tự động tính vốn và tỉ lệ" — điền một
        # trong hai ô là cổng tự tính ô kia; ghi đè cả hai chỉ gây lệch khi cổng tính lại.
        {"name": f"{base}$CPT_CONTR_AMOUNTFld", "comp": "dom-input", "value": member.get("capitalAmount")},
        {"name": f"{base}$CPT_OWNERSHP_PERCENTFld", "comp": "dom-input", "value": member.get("ownershipPercent")},
    ]
    # Thời hạn góp vốn: hồ sơ ghi "trong vòng N ngày" → chọn "Thời hạn" + số ngày; ghi một NGÀY cụ
    # thể → chọn "Ngày cụ thể" + ô ngày. Không có căn cứ thì không đụng radio.
    if member.get("durationDays"):
        rows.append({"name": f"{base}$CPT_CONTR_TIME_TYPEFld", "comp": "dom-radio", "value": "Thời hạn"})
        rows.append({"name": f"{base}$DURATIONFld", "comp": "dom-input", "value": member.get("durationDays")})
    elif member.get("contributionDate"):
        rows.append({"name": f"{base}$CPT_CONTR_TIME_TYPEFld", "comp": "dom-radio", "value": "Ngày cụ thể"})
        rows.append({"name": f"{base}$CPT_CONTR_TIMEFld", "comp": "dom-date", "value": member.get("contributionDate")})
    rows.append({"name": f"{base}$NOTEFld", "comp": "dom-input", "value": member.get("note")})
    return [row for row in rows if row["value"] not in (None, "", {}, [])]


def _members(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Danh sách thành viên đã chuẩn hoá, GIỮ NGUYÊN thứ tự đọc từ Danh sách thành viên."""
    out: list[dict[str, Any]] = []
    for row in _rows(values.get("ThanhVien_DanhSach")):
        member = {
            "fullName": _text(row.get("hoTen")).upper(),
            "gender": _gender_code(row.get("gioiTinh")),
            "birthDate": normalize_date(row.get("ngaySinh")) or "",
            "docNo": _digits(row.get("soGiayToPhapLy")),
            "nationality": _text(row.get("quocTich")),
            "ethnic": _text(row.get("danToc")),
            "address": _addr(row.get("diaChiLienLac")),
            "phone": _phone(row.get("dienThoai")),
            "fax": _text(row.get("fax")),
            "website": _text(row.get("website")),
            "email": _email(row.get("email")),
            "capitalAmount": _number(row.get("vonGop")),
            "ownershipPercent": _ratio(row.get("tyLeSoHuu")),
            "durationDays": _digits(row.get("soNgayGopVon")),
            "contributionDate": normalize_date(row.get("ngayGopVonCuThe")) or "",
            "note": _text(row.get("ghiChu")),
        }
        if member["fullName"] or member["docNo"]:
            out.append(member)
    return out


# --------------------------------------------------------------------------- mapping
def enrich(fields: list[dict], *, page: str | None = None) -> list[dict]:
    values = _by_name(fields)
    selected_page = page or DEFAULT_PAGE
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, comp: str, value: Any, aliases: list[str] | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        item: dict[str, Any] = {"name": name, "comp": comp, "value": value}
        if aliases:
            item["aliases"] = aliases
        out.append(item)
        seen.add(name)

    def add_address(prefix: str, value: Any) -> None:
        for field in _address_fields(prefix, value):
            add(field["name"], field["comp"], field["value"])

    if selected_page == "hinh-thuc-dang-ky":
        # Trang đầu của khối dữ liệu (DW_REORGANIZATIONEdit.aspx): cổng đã chọn sẵn "Thành lập mới",
        # việc cần làm chỉ là bấm Lưu để mở sang các trang sau. Vẫn phát select cho chắc — sai tên thì
        # chỉ là không tìm thấy ô, vô hại, vì trang vẫn được Lưu nhờ giá trị mặc định của cổng.
        add("ctl00$C$REORGCtl$REORG_TYPE_IDFld", "dom-select", "Thành lập mới")

    elif selected_page == "dia-chi":
        add_address("ctl00$C$ADDRCtl", values.get("TruSo_DiaChi"))
        # Chỉ tích ô khu vực khi giấy tờ ghi rõ; tích thừa là đổi thẩm quyền nộp hồ sơ.
        zones = values.get("TruSo_KhuVuc")
        for zone in (zones if isinstance(zones, list) else [zones]):
            field = _ZONE_FIELD_BY_LABEL.get(_fold(zone))
            if field:
                add(f"ctl00$C$ZONECtl${field}", "dom-checkbox", True)
        add("ctl00$C$DCONTCtl$HO_PHONEFld", "dom-input", _phone(values.get("TruSo_DienThoai")))
        add("ctl00$C$DCONTCtl$HO_FAXFld", "dom-input", _text(values.get("TruSo_Fax")))
        add("ctl00$C$DCONTCtl$HO_EMAILFld", "dom-input", _email(values.get("TruSo_Email")))
        add("ctl00$C$DCONTCtl$HO_URLFld", "dom-input", _text(values.get("TruSo_Website")))

    elif selected_page == "nganh-nghe-kinh-doanh":
        items = _business_line_items(values)
        codes = [item["code"] for item in items if item["code"]]
        main_code = _main_business_code(values)
        # Bảng ngành nghề là GridView dựng bằng postback: extension đọc __businessLines để thêm LẦN
        # LƯỢT từng mã rồi đánh dấu ngành chính; không có control tĩnh nào để điền thẳng.
        if codes:
            add("__businessLines", "raw", {"codes": codes, "main": main_code, "items": items})
        if main_code:
            add("ctl00$C$newBusinessLineCode", "dom-input", main_code)
        add("ctl00$C$BUSINESS_ACT_TEXTFld", "dom-input", _text(values.get("NganhNghe_NgoaiHeThong")))

    elif selected_page == "ten-doanh-nghiep":
        name_type = _text(values.get("DoanhNghiep_TenLoaiHinh")).upper()
        # Dropdown tiền tố CHỈ có các loại hình hai thành viên trở lên; mặc định "CÔNG TY TNHH" chứ
        # tuyệt đối không rơi về "MTV" (một thành viên) khi giấy tờ ghi mờ.
        add("ctl00$C$DROP_NAME_TYPE", "dom-select", name_type or "CÔNG TY TNHH")
        add("ctl00$C$NAMEFld", "dom-input", _text(values.get("DoanhNghiep_TenRieng")).upper())
        add("ctl00$C$NAME_FFld", "dom-input", _text(values.get("DoanhNghiep_TenNuocNgoai")))
        add("ctl00$C$SHORT_NAMEFld", "dom-input", _text(values.get("DoanhNghiep_TenVietTat")))

    elif selected_page == "thong-tin-ve-von":
        base = "ctl00$C$UC_DW_CAPITALEditCtl"
        add(f"{base}$CPT_CHARTER_AMOUNTFld", "dom-input", _number(values.get("Von_DieuLe")))
        add(f"{base}$WwWebTextBox1", "dom-input", _number(values.get("Von_NgoaiTe_GiaTri")))
        add(f"{base}$CL_CURRENCY_IDFld", "dom-select", _text(values.get("Von_NgoaiTe_LoaiTien")).upper())
        source_rows = _rows(values.get("Von_NguonVon"))
        for index, kind in enumerate(_CAPITAL_SOURCE_ROWS, start=2):
            row = _row_by_kind(source_rows, kind)
            slot = f"{base}$CtlSourceList$ctl{index:02d}"
            add(f"{slot}$RATIO_PERCENTFld", "dom-input", _ratio(row.get("tyLe")))
            add(f"{slot}$AMOUNTFld", "dom-input", _number(row.get("soTien")))
        asset_rows = _rows(values.get("Von_TaiSanGopVon"))
        for index, kind in enumerate(_CAPITAL_ASSET_ROWS, start=2):
            row = _row_by_kind(asset_rows, kind)
            slot = f"{base}$CtlList$ctl{index:02d}"
            add(f"{slot}$ASSET_RATIO_PERCENTFld", "dom-input", _ratio(row.get("tyLe")))
            add(f"{slot}$ASSET_AMOUNTFld", "dom-input", _number(row.get("giaTri")))

    elif selected_page == "thong-tin-thanh-vien":
        # Mục menu trỏ tới DANH SÁCH thành viên (DW_MEMBER_VWListing.aspx); mỗi thành viên là MỘT
        # lượt "Tạo mới" → form InformationOfMembers.aspx → Lưu. Vì vậy gửi kèm __members có sẵn bộ
        # field của TỪNG người để extension chỉ việc lặp, không phải biết tên control nào.
        members = _members(values)
        if members:
            add("__members", "raw", [
                {
                    "fullName": member.get("fullName"),
                    "docNo": member.get("docNo"),
                    "fields": _member_fields(member),
                }
                for member in members
            ])
        # Field tĩnh của thành viên ĐẦU TIÊN: lưới đỡ cho trường hợp cán bộ đang đứng sẵn ở form chi
        # tiết (engine điền thẳng thay vì đi qua danh sách).
        for field in _member_fields(members[0] if members else {}):
            add(field["name"], field["comp"], field["value"])

    elif selected_page == "nguoi-dai-dien-phap-luat":
        base = "ctl00$C$REPCtl"
        person = f"{base}$PERSCtl"
        add(f"{person}$FULL_NAMEFld", "dom-input", _text(values.get("NguoiDaiDien_HoTen")).upper())
        add(f"{person}$GENDER_IDFld", "dom-radio", _gender_code(values.get("NguoiDaiDien_GioiTinh")))
        add(f"{person}$DATE_OF_BIRTHFld", "dom-date", normalize_date(values.get("NguoiDaiDien_NgaySinh")))
        add(f"{person}$PERS_DOC_NOFld", "dom-input", _digits(values.get("NguoiDaiDien_SoDinhDanh")))
        # $SET_AUTO_ADRESSFld giữ mặc định "Trùng địa chỉ thường trú" (xem chú thích trang thành viên).
        add_address(f"{person}$ADDRCCtl", values.get("NguoiDaiDien_DiaChi"))
        add(f"{person}$PHONEFld", "dom-input", _phone(values.get("NguoiDaiDien_DienThoai")))
        add(f"{person}$FAXFld", "dom-input", _text(values.get("NguoiDaiDien_Fax")))
        add(f"{person}$URLFld", "dom-input", _text(values.get("NguoiDaiDien_Website")))
        add(f"{person}$EMAILFld", "dom-input", _email(values.get("NguoiDaiDien_Email")))
        # Bảng đặc tả ghi id ô Quyền hạn là "C_REPCtl_POWERSId"; khai alias "POWERSFld" theo lối đặt
        # tên của mọi ô khác trên cổng để không hụt ô nếu bản render khác.
        add(f"{base}$POWERSId", "dom-input", _text(values.get("NguoiDaiDien_QuyenHan")),
            aliases=[f"{base}$POWERSFld"])

    elif selected_page == "thong-tin-ve-thue":
        base = "ctl00$C$UC_DW_TAXEditCtl"
        # Hai GridView đầu trang (Giám đốc/Tổng giám đốc, Kế toán trưởng) KHÔNG map ở đây: bảng đặc tả
        # ghi Giám đốc đã được cổng điền sẵn từ bước Người đại diện theo pháp luật, còn Kế toán trưởng
        # để trống. Cần thêm dòng thì phải bấm "Tạo mới" (postback) — việc của extension, không phải
        # của mapper.
        tax_addr = values.get("Thue_DiaChiNhanThongBao")
        if not _has_address(tax_addr) or _same_address(tax_addr, values.get("TruSo_DiaChi")):
            add(f"{base}$REP_RECV_ADDR_TYPEFld", "dom-radio", "Giống địa chỉ trụ sở chính")
        else:
            add(f"{base}$REP_RECV_ADDR_TYPEFld", "dom-radio", "Địa chỉ khác")
            add_address(f"{base}$ADDRCtl", tax_addr)
        add(f"{base}$REP_RECEIVER_PHONEFld", "dom-input", _phone(values.get("Thue_DienThoai")))
        add(f"{base}$REP_RECEIVER_FAXFld", "dom-input", _text(values.get("Thue_Fax")))
        add(f"{base}$REP_RECEIVER_EMAILFld", "dom-input", _email(values.get("Thue_Email")))
        add(f"{base}$TAX_ACCOUNTING_IDFld", "dom-select", _text(values.get("Thue_HinhThucHachToan")))
        if values.get("Thue_CoBaoCaoHopNhat") is True:
            add(f"{base}$CONSOLIDATED_FINANCIAL_YN_IDId", "dom-checkbox", True,
                aliases=[f"{base}$CONSOLIDATED_FINANCIAL_YN_IDIdl"])
        fiscal = values.get("Thue_NamTaiChinh") if isinstance(values.get("Thue_NamTaiChinh"), dict) else {}
        add(f"{base}$FIN_YEAR_START_DAYFld", "dom-select", _digits(fiscal.get("ngayBatDau")))
        add(f"{base}$FIN_YEAR_START_MONTHFld", "dom-select", _digits(fiscal.get("thangBatDau")))
        add(f"{base}$FIN_YEAR_END_DAYFld", "dom-select", _digits(fiscal.get("ngayKetThuc")))
        add(f"{base}$FIN_YEAR_END_MONTHFld", "dom-select", _digits(fiscal.get("thangKetThuc")))
        add(f"{base}$BUSINESS_START_DATEFld", "dom-date", normalize_date(values.get("Thue_NgayBatDauHoatDong")))
        add(f"{base}$TOTAL_OF_LABORSFld", "dom-input", _digits(values.get("Thue_SoLaoDong")))
        # Ô "doanh nghiệp nằm trong khu..." của trang thuế phải KHỚP với 4 ô đã tích ở trang Địa chỉ.
        if values.get("TruSo_KhuVuc"):
            add(f"{base}$INDZONE_EXPZONE_YESNO_IDId", "dom-checkbox", True,
                aliases=[f"{base}$INDZONE_EXPZONE_YESNO_IDld"])
        add(f"{base}$TAX_CAL_METHOD_IDRbBox", "dom-radio",
            _TAX_METHOD_BY_LABEL.get(_fold(values.get("Thue_PhuongPhapGTGT")), ""))
        if values.get("Thue_DuAnBOT") is True:
            add("ctl00$C$IS_BOT_BT_ID_YESNO_IDId", "dom-checkbox", True,
                aliases=["ctl00$C$IS_BOT_BT_ID_YESNO_IDIdd"])
        # Mục 10 (phương thức đóng BHXH) và mục 11 (doanh nghiệp có chủ sở hữu hưởng lợi) có trên
        # Giấy đề nghị nhưng bảng đặc tả KHÔNG tìm được control tương ứng trong HTML → không map.

    elif selected_page == "nguoi-nop-ho-so":
        base = "ctl00$C$PERSCtl"
        role = _fold(values.get("NguoiNop_VaiTro"))
        # Form check sẵn "Người có thẩm quyền ký"; chỉ đổi sang uỷ quyền khi giấy tờ ghi rõ, vì chọn
        # nhầm nhánh này bắt buộc phải kê khai thêm cả khối "Thông tin Ủy quyền".
        add("ctl00$C$PERS_SUBGroup", "dom-radio",
            "IS_AUTHORIZED_BUTTON" if "uy quyen" in role else "IS_REPRESENTATIVE_BUTTON")
        add(f"{base}$FULL_NAMEFld", "dom-input", _text(values.get("NguoiNop_HoTen")).upper())
        add(f"{base}$GENDER_IDFld", "dom-radio", _gender_code(values.get("NguoiNop_GioiTinh")))
        add(f"{base}$DATE_OF_BIRTHFld", "dom-date", normalize_date(values.get("NguoiNop_NgaySinh")))
        add(f"{base}$PERS_DOC_NOFld", "dom-input", _digits(values.get("NguoiNop_SoDinhDanh")))
        add_address(f"{base}$ADDRCCtl", values.get("NguoiNop_DiaChi"))
        add(f"{base}$PHONEFld", "dom-input", _phone(values.get("NguoiNop_DienThoai")))
        add(f"{base}$FAXFld", "dom-input", _text(values.get("NguoiNop_Fax")))
        add(f"{base}$EMAILFld", "dom-input", _email(values.get("NguoiNop_Email")))
        add("ctl00$C$POSTAL_SERVICEFld", "dom-input", _text(values.get("NguoiNop_DiaChiNhanKetQua")))
        # Nhân thân NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT — để engine đối chiếu với tài khoản ĐKKD đang
        # đăng nhập, ĐÚNG cách thủ tục hộ kinh doanh đối chiếu tài khoản với CHỦ HỘ: người này là
        # "người có thẩm quyền ký Giấy đề nghị", ai khác đi nộp thì là "người được ủy quyền".
        # Quan trọng: dữ liệu này đọc từ Giấy đề nghị/Điều lệ nên LUÔN CÓ, không phụ thuộc việc cán
        # bộ có kèm ảnh CCCD hay không — chính chỗ mà lối đối chiếu theo CCCD bên dưới bị hụt.
        legal_rep = {
            "fullName": _text(values.get("NguoiDaiDien_HoTen")),
            "docNo": _digits(values.get("NguoiDaiDien_SoDinhDanh")),
        }
        if legal_rep["fullName"] or legal_rep["docNo"]:
            add("__legalRep", "raw", legal_rep)
        # Extension đối chiếu với tài khoản ĐKKD đang đăng nhập rồi ghi đè nhân thân + địa chỉ cho
        # đúng người đang nộp (nút "Sao chép thông tin đăng ký tài khoản" của cổng không có địa chỉ).
        candidates = _identity_candidates(values)
        if candidates:
            add("__identityCandidates", "raw", candidates)

    return out


def enrich_all(fields: list[dict]) -> dict[str, list[dict]]:
    """Map 1 bộ facts thành field cho TẤT CẢ trang đã có đặc tả (extension lặp: fill → Lưu → trang kế)."""
    return {p["key"]: enrich(fields, page=p["key"]) for p in PAGES}
