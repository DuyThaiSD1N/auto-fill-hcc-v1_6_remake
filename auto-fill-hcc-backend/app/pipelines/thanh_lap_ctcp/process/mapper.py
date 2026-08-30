"""Map facts "thành lập công ty cổ phần" sang field UI của MỘT trang WebForms.

Tên control lấy nguyên văn từ bảng đặc tả (cột `formcontrolname / field-key`) của cổng
dangkyquamang.dkkd.gov.vn. LƯU Ý khác HkdOnline:
  - khối liên hệ là `DCONTCtl` (HKD viết `DCONTClt`);
  - các bảng lặp dùng chỉ số `ctl02..ctlNN` theo ĐÚNG thứ tự dòng in trên form, dòng cuối là "Tổng"
    do cổng tự cộng (disabled) nên KHÔNG bao giờ điền.

Helper text/địa chỉ được định nghĩa tại chỗ thay vì import từ pipeline hộ kinh doanh: chúng là hàm
thuần nhỏ, giữ ở đây để pipeline này độc lập, không kéo theo rủi ro khi sửa pipeline HKD đang chạy.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.thanh_lap_ctcp.process.schema import DEFAULT_PAGE, PAGES


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
    # "5.000.000.000" / "5,000,000,000" / "5000000000 đồng" → "5000000000"
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


# Thứ tự dòng của các bảng lặp trên form (ctl02 là dòng đầu tiên). Đổi thứ tự ở đây là đổi ánh xạ.
_CAPITAL_SOURCE_ROWS = ["ngan_sach", "tu_nhan", "nuoc_ngoai", "khac"]
_CAPITAL_ASSET_ROWS = ["dong_vn", "ngoai_te", "vang", "quyen_su_dung_dat", "so_huu_tri_tue", "khac"]
_SHARE_ROWS = ["pho_thong", "uu_dai_bieu_quyet", "uu_dai_co_tuc", "uu_dai_hoan_lai", "uu_dai_khac"]

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


# --------------------------------------------------------------------------- mapping
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
        # Trang đầu của khối dữ liệu (DW_REORGANIZATIONEdit.aspx): cổng đã chọn sẵn "Thành lập mới",
        # việc cần làm chỉ là bấm Lưu để mở sang các trang sau. Vẫn phát select cho chắc — tên control
        # suy từ engine hộ kinh doanh (cùng họ ứng dụng); sai tên thì chỉ là không tìm thấy ô, vô hại,
        # vì trang vẫn được Lưu nhờ giá trị mặc định của cổng.
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
        add("ctl00$C$DROP_NAME_TYPE", "dom-select", name_type or "CÔNG TY CỔ PHẦN")
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

    elif selected_page == "thong-tin-ve-co-phan":
        base = "ctl00$C$UC_DW_OTHEREditCtl"
        add(f"{base}$VALUE_OF_EACH_SHAREFld", "dom-input", _number(values.get("CoPhan_MenhGia")))
        share_rows = _rows(values.get("CoPhan_DanhSach"))
        for index, kind in enumerate(_SHARE_ROWS, start=2):
            row = _row_by_kind(share_rows, kind)
            slot = f"{base}$CtlList$ctl{index:02d}"
            add(f"{slot}$QUANTITYFld", "dom-input", _number(row.get("soLuong")))
            add(f"{slot}$VALUEFld", "dom-input", _number(row.get("menhGia")))
            add(f"{slot}$TOTAL_VALUEFld", "dom-input", _number(row.get("giaTri")))
            add(f"{slot}$RATIO_IN_CHARTER_CPTFld", "dom-input", _ratio(row.get("tyLe")))
        sale_rows = _rows(values.get("CoPhan_ChaoBan"))
        for index, kind in enumerate(_SHARE_ROWS, start=2):
            row = _row_by_kind(sale_rows, kind)
            add(f"{base}$CtlListSales$ctl{index:02d}$QUANTITYFld", "dom-input", _number(row.get("soLuong")))

    elif selected_page == "thong-tin-ve-thue":
        base = "ctl00$C$UC_DW_TAXEditCtl"
        # Địa chỉ nhận thông báo thuế: form check sẵn "Địa chỉ khác" (value 0). Giống trụ sở (hoặc
        # không kê khai riêng) thì chọn value 1 và KHÔNG điền khối địa chỉ — cổng tự ẩn khối đó.
        tax_addr = values.get("Thue_DiaChiNhanThongBao")
        if not _has_address(tax_addr) or _same_address(tax_addr, values.get("TruSo_DiaChi")):
            add(f"{base}$REP_RECV_ADDR_TYPEFld", "dom-radio", "1")
        else:
            add(f"{base}$REP_RECV_ADDR_TYPEFld", "dom-radio", "0")
            add_address(f"{base}$ADDRCtl", tax_addr)
        add(f"{base}$REP_RECEIVER_PHONEFld", "dom-input", _phone(values.get("Thue_DienThoai")))
        add(f"{base}$REP_RECEIVER_FAXFld", "dom-input", _text(values.get("Thue_Fax")))
        add(f"{base}$REP_RECEIVER_EMAILFld", "dom-input", _email(values.get("Thue_Email")))
        add(f"{base}$TAX_ACCOUNTING_IDFld", "dom-select", _text(values.get("Thue_HinhThucHachToan")))
        if values.get("Thue_CoBaoCaoHopNhat") is True:
            add(f"{base}$CONSOLIDATED_FINANCIAL_YN_IDIdl", "dom-checkbox", True)
        fiscal = values.get("Thue_NamTaiChinh") if isinstance(values.get("Thue_NamTaiChinh"), dict) else {}
        add(f"{base}$FIN_YEAR_START_DAYFld", "dom-select", _digits(fiscal.get("ngayBatDau")))
        add(f"{base}$FIN_YEAR_START_MONTHFld", "dom-select", _digits(fiscal.get("thangBatDau")))
        add(f"{base}$FIN_YEAR_END_DAYFld", "dom-select", _digits(fiscal.get("ngayKetThuc")))
        add(f"{base}$FIN_YEAR_END_MONTHFld", "dom-select", _digits(fiscal.get("thangKetThuc")))
        add(f"{base}$BUSINESS_START_DATEFld", "dom-date", normalize_date(values.get("Thue_NgayBatDauHoatDong")))
        add(f"{base}$TOTAL_OF_LABORSFld", "dom-input", _digits(values.get("Thue_SoLaoDong")))
        # Ô "doanh nghiệp nằm trong khu..." của trang thuế phải KHỚP với 4 ô đã tích ở trang Địa chỉ.
        if _rows and values.get("TruSo_KhuVuc"):
            add(f"{base}$INDZONE_EXPZONE_YESNO_IDld", "dom-checkbox", True)
        add(f"{base}$TAX_CAL_METHOD_IDRbBox", "dom-radio",
            _TAX_METHOD_BY_LABEL.get(_fold(values.get("Thue_PhuongPhapGTGT")), ""))
        if values.get("Thue_DuAnBOT") is True:
            add("ctl00$C$IS_BOT_BT_ID_YESNO_IDIdd", "dom-checkbox", True)

    elif selected_page == "nguoi-nop-ho-so":
        base = "ctl00$C$PERSCtl"
        role = _fold(values.get("NguoiNop_VaiTro"))
        # Form check sẵn "Người có thẩm quyền ký"; chỉ đổi sang uỷ quyền khi giấy tờ ghi rõ, vì chọn
        # nhầm nhánh này bắt buộc phải kê khai thêm cả khối "Thông tin Ủy quyền".
        add("ctl00$C$PERS_SUBGroup", "dom-radio",
            "IS_AUTHORIZED_BUTTON" if "uy quyen" in role else "IS_REPRESENTATIVE_BUTTON")
        add(f"{base}$FULL_NAMEFld", "dom-input", _text(values.get("NguoiNop_HoTen")).upper())
        gender = _fold(values.get("NguoiNop_GioiTinh"))
        add(f"{base}$GENDER_IDFld", "dom-radio", "M" if gender == "nam" else ("F" if gender == "nu" else ""))
        add(f"{base}$DATE_OF_BIRTHFld", "dom-date", normalize_date(values.get("NguoiNop_NgaySinh")))
        add(f"{base}$PERS_DOC_NOFld", "dom-input", _digits(values.get("NguoiNop_SoDinhDanh")))
        add_address(f"{base}$ADDRCCtl", values.get("NguoiNop_DiaChi"))
        add(f"{base}$PHONEFld", "dom-input", _phone(values.get("NguoiNop_DienThoai")))
        add(f"{base}$FAXFld", "dom-input", _text(values.get("NguoiNop_Fax")))
        add(f"{base}$EMAILFld", "dom-input", _email(values.get("NguoiNop_Email")))
        add("ctl00$C$POSTAL_SERVICEFld", "dom-input", _text(values.get("NguoiNop_DiaChiNhanKetQua")))
        # Extension đối chiếu với tài khoản ĐKKD đang đăng nhập rồi ghi đè nhân thân + địa chỉ cho
        # đúng người đang nộp (nút "Sao chép thông tin đăng ký tài khoản" của cổng không có địa chỉ).
        candidates = _identity_candidates(values)
        if candidates:
            add("__identityCandidates", "raw", candidates)

    return out


def enrich_all(fields: list[dict]) -> dict[str, list[dict]]:
    """Map 1 bộ facts thành field cho TẤT CẢ trang đã có đặc tả (extension lặp: fill → Lưu → trang kế)."""
    return {p["key"]: enrich(fields, page=p["key"]) for p in PAGES}
