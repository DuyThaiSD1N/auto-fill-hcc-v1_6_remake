"""Regression tests cho mapper Đăng ký kinh doanh hộ kinh doanh.

Khóa lại 3 chuẩn hóa xác định (deterministic) từ OCR "Giấy đề nghị":
- Số điện thoại: khôi phục số 0 đứng đầu cho số di động VN.
- Họ tên: viết hoa chữ đầu mỗi từ (giấy ghi IN HOA).
- Trang chủ hộ: gom đúng các field UI.
"""

from app.pipelines.dang_ky_kinh_doanh.process import mapper
from app.pipelines.dang_ky_kinh_doanh.process.mapper import (
    _clean_business_code,
    _clean_phone,
    _clean_ward,
    _proper_name,
)
from app.pipelines.dang_ky_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_kinh_doanh.process.schema import FIELDS


def test_clean_phone_restores_leading_zero():
    assert _clean_phone("974455009") == "0974455009"      # OCR rớt số 0 đứng đầu
    assert _clean_phone("097445S009") == "0974455009"     # S -> 5
    assert _clean_phone("0974455 009") == "0974455009"    # bỏ dấu cách
    assert _clean_phone("84974455009") == "0974455009"    # mã quốc gia 84 -> 0
    assert _clean_phone("0974455009") == "0974455009"     # đã đúng, giữ nguyên
    assert _clean_phone("+84974455009") == "+84974455009"  # có dấu +, giữ nguyên
    assert _clean_phone("123") == ""                       # quá ngắn -> bỏ


def test_proper_name_title_cases():
    assert _proper_name("Vũ THÁNH CHUNG") == "Vũ Thánh Chung"
    assert _proper_name("VŨ THÁNH CHUNG") == "Vũ Thánh Chung"
    assert _proper_name("Nguyễn Văn A") == "Nguyễn Văn A"
    assert _proper_name("") == ""


def test_clean_ward_removes_common_prefixes_for_hkdonline_options():
    assert _clean_ward("P.Lâm Viên - Đà Lạt") == "Lâm Viên - Đà Lạt"
    assert _clean_ward("P Lâm Viên - Đà Lạt") == "Lâm Viên - Đà Lạt"
    assert _clean_ward("phường Lâm Viên – Đà Lạt") == "Lâm Viên - Đà Lạt"
    assert _clean_ward("Xã Nam Ban Lâm Hà") == "Nam Ban Lâm Hà"
    assert _clean_ward("Đặc khu Phú Quý") == "Phú Quý"


def test_clean_ward_khong_cat_chu_dau_ten_xa_tran():
    # Tên trần bắt đầu bằng "Ph"/"P": không được coi chữ đầu là tiền tố viết tắt.
    assert _clean_ward("phúc lợi") == "phúc lợi"
    assert _clean_ward("Phù Khê") == "Phù Khê"
    assert _clean_ward("Pá Tần") == "Pá Tần"
    assert _clean_ward("TT Chờ") == "Chờ"
    # "Phương" là tên riêng của phường Phương Liễu, OCR hay đọc thành tiền tố "Phường".
    assert _clean_ward("Phường Liễu") == "Phương Liễu"
    assert _clean_ward("phuong lieu") == "Phương Liễu"
    assert _clean_ward("Phường Phương Liễu") == "Phương Liễu"
    assert mapper._addr({"tinh": "Bắc Ninh", "xa": "phương liễu", "diaChi": "Tổ dân phố 1"})["xa"] == "Phương Liễu"


def test_clean_business_code_requires_four_contiguous_digits():
    assert _clean_business_code("56 10") == "5610"
    assert _clean_business_code("56.10") == "5610"
    assert _clean_business_code("5610") == "5610"
    assert _clean_business_code("561") == ""
    assert _clean_business_code("56100") == ""


def test_enrich_address_page_outputs_ward_without_prefix():
    fields = [
        {
            "name": "TruSo_DiaChi",
            "value": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "P.Lâm Viên - Đà Lạt",
                "diaChi": "58 Trang Trình",
            },
        }
    ]
    out = {f["name"].split("$")[-1]: f["value"] for f in mapper.enrich(fields, page="dia-chi")}
    assert out["CITY_IDFld"] == "Lâm Đồng"
    assert out["WARD_IDFld"] == "Lâm Viên - Đà Lạt"
    assert out["STREET_NUMBERFld"] == "58 Trang Trình"


def test_business_lines_keep_extracted_name_for_description_fill():
    fields = [
        {
            "name": "NganhNghe_DanhSach",
            "value": [{"ma": "5630", "ten": "Dịch vụ phục vụ đồ uống (cà phê)", "chinh": True}],
        },
        {"name": "NganhNghe_MaChinh", "value": "5630"},
        {"name": "NganhNghe_TenChinh", "value": "Dịch vụ phục vụ đồ uống (cà phê)"},
    ]

    raw = next(f for f in mapper.enrich(fields, page="nganh-nghe-kinh-doanh") if f["name"] == "__businessLines")

    assert raw["value"]["codes"] == ["5630"]
    assert raw["value"]["main"] == "5630"
    assert raw["value"]["items"] == [
        {"code": "5630", "name": "Dịch vụ phục vụ đồ uống (cà phê)", "main": True}
    ]


def test_business_line_codes_strip_spaces_before_extension_fill():
    fields = [
        {
            "name": "NganhNghe_DanhSach",
            "value": [{"ma": "56 10", "ten": "Ăn uống", "chinh": True}],
        },
        {"name": "NganhNghe_MaChinh", "value": "56 10"},
        {"name": "NganhNghe_TenChinh", "value": "Ăn uống"},
    ]

    out = mapper.enrich(fields, page="nganh-nghe-kinh-doanh")
    raw = next(f for f in out if f["name"] == "__businessLines")
    main_input = next(f for f in out if f["name"] == "ctl00$C$newBusinessLineCode")

    assert raw["value"]["codes"] == ["5610"]
    assert raw["value"]["main"] == "5610"
    assert raw["value"]["items"] == [{"code": "5610", "name": "Ăn uống", "main": True}]
    assert main_input["value"] == "5610"


def _tax_fields(out):
    by = {f["name"].split("$")[-1]: f["value"] for f in out}
    radio = by.get("REP_RECV_ADDR_TYPEFld")
    has_addr = any("ADDRCtl" in f["name"] for f in out)
    has_phone = any(f["name"].endswith("REP_RECEIVER_PHONEFld") for f in out)
    return radio, has_addr, has_phone


_HQ = {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Tân Phong", "diaChi": "038"}


def test_tax_address_same_as_hq_picks_giong_radio_no_address():
    fields = [
        {"name": "TruSo_DiaChi", "value": _HQ},
        {"name": "Thue_DiaChiNhanThongBao", "value": dict(_HQ)},
        {"name": "Thue_DienThoai", "value": "0974455009"},
    ]
    radio, has_addr, has_phone = _tax_fields(mapper.enrich(fields, page="thong-tin-ve-thue"))
    assert radio == "1"          # Giống địa chỉ trụ sở chính
    assert has_addr is False     # không điền khối địa chỉ
    assert has_phone is True     # điện thoại vẫn điền


def test_tax_address_missing_treated_as_same():
    fields = [{"name": "TruSo_DiaChi", "value": _HQ}, {"name": "Thue_DienThoai", "value": "0974455009"}]
    radio, has_addr, _ = _tax_fields(mapper.enrich(fields, page="thong-tin-ve-thue"))
    assert radio == "1"
    assert has_addr is False


def test_tax_address_va_tru_so_deu_trong_thi_khong_tu_chon_giong():
    """"Giống trụ sở" chỉ tự chọn khi trụ sở có địa chỉ — cả hai trống thì không đụng ô (trợ lý hỏi / cán bộ chọn)."""
    for fields in ([{"name": "Thue_DienThoai", "value": "0974455009"}],
                   [{"name": "TruSo_DiaChi", "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}},
                    {"name": "Thue_DiaChiNhanThongBao", "value": {}}]):
        radio, has_addr, _ = _tax_fields(mapper.enrich(fields, page="thong-tin-ve-thue"))
        assert radio is None and has_addr is False


def test_tax_address_different_picks_khac_radio_and_fills_address():
    fields = [
        {"name": "TruSo_DiaChi", "value": _HQ},
        {"name": "Thue_DiaChiNhanThongBao",
         "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "53"}},
        {"name": "Thue_DienThoai", "value": "0974455009"},
    ]
    radio, has_addr, has_phone = _tax_fields(mapper.enrich(fields, page="thong-tin-ve-thue"))
    assert radio == "0"          # Địa chỉ khác
    assert has_addr is True      # điền khối địa chỉ thuế
    assert has_phone is True


def test_enrich_chu_ho_page_normalizes_name_and_phone():
    fields = [
        {"name": "ChuHo_HoTen", "value": "Vũ THÁNH CHUNG"},
        {"name": "ChuHo_DienThoai", "value": "974455009"},
        {"name": "ChuHo_NgaySinh", "value": "07/1989"},
    ]
    out = {f["name"].split("$")[-1]: f["value"] for f in mapper.enrich(fields, page="chu-ho-kinh-doanh")}
    assert out["FULL_NAMEFld"] == "Vũ Thánh Chung"
    assert out["PHONEFld"] == "0974455009"
    # Ngày sinh chỉ có tháng/năm thì giữ nguyên, không bịa ngày.
    assert out["DATE_OF_BIRTHFld"] == "07/1989"


def test_business_contact_sources_are_independent_and_submitter_has_no_contact_field():
    fields = [
        {"name": "TruSo_DienThoai", "value": "0901000001"},
        {"name": "ChuHo_DienThoai", "value": "0902000002"},
        {"name": "Thue_DienThoai", "value": "0903000003"},
        # Khóa hồi quy: kể cả dữ liệu compact cũ còn key này, mapper cũng không đưa sang trang người nộp.
        {"name": "NguoiNop_DienThoai", "value": "0904000004"},
    ]

    pages = mapper.enrich_all(fields)
    address_values = {f["name"]: f["value"] for f in pages["dia-chi"]}
    owner_values = {f["name"]: f["value"] for f in pages["chu-ho-kinh-doanh"]}
    tax_values = {f["name"]: f["value"] for f in pages["thong-tin-ve-thue"]}
    submitter_names = {f["name"] for f in pages["nguoi-nop-ho-so"]}

    assert address_values["ctl00$C$DCONTClt$HO_PHONEFld"] == "0901000001"
    assert owner_values["ctl00$C$OWN_PCtl$PERSCtl$PHONEFld"] == "0902000002"
    assert tax_values["ctl00$C$UC_DW_TAXEditCtl$REP_RECEIVER_PHONEFld"] == "0903000003"
    assert "ctl00$C$PERSCtl$PHONEFld" not in submitter_names


def test_business_schema_and_prompt_only_define_three_phone_sources():
    names = {field["name"] for field in FIELDS}

    assert {"TruSo_DienThoai", "ChuHo_DienThoai", "Thue_DienThoai"} <= names
    assert "NguoiNop_DienThoai" not in names
    assert "CHỈ có 3 nhóm liên hệ cần trích từ hồ sơ" in EXTRA_RULES
    assert "KHÔNG lấy liên hệ người nộp thay cho trụ sở, chủ hộ hoặc thuế" in EXTRA_RULES


# ── Trụ sở / địa chỉ thuế bỏ trống tỉnh-xã: không giữ tỉnh/xã CCCD mà LLM tự thêm (12/11/2026) ──────
def _ocr_don(tru_so_xa="....", tru_so_tinh="....", kinh_gui="Kính gửi: UBND phường Xuân Hương – Đà Lạt",
             thue_xa="Xuân Hương", thue_tinh=""):
    return "\n".join([
        "Nơi thường trú / Place of residence: 12 Lê Lợi, Tân Lợi, BMT, Đắk Lắk",
        kinh_gui,
        "Mẫu số 1",
        "Tôi là (ghi họ tên bằng chữ in hoa): NGUYỄN VĂN A",
        "2. Trụ sở của hộ kinh doanh:",
        "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn:",
        "10 Đường Mẫu",
        f"Xã/Phường/Đặc khu: {tru_so_xa}",
        f"Tỉnh/Thành phố trực thuộc trung ương: {tru_so_tinh}",
        "Điện thoại: 0900000001 Fax (nếu có): ....",
        "3. Ngành, nghề kinh doanh:",
        "5.1. Địa chỉ nhận thông báo thuế (chỉ kê khai nếu địa chỉ nhận thông báo thuế khác địa chỉ trụ sở):",
        "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ap/thôn:",
        "10 Đường Mẫu",
        f"Xã/Phường/Đặc khu: {thue_xa}",
        f"Tỉnh/Thành phố trực thuộc trung ương:{thue_tinh}",
        "Điện thoại (nếu có): 0900000001 Thư điện tử (nếu có):",
        "5.2. Ngày bắt đầu hoạt động: ……/……/……..",
    ])


def _llm_cop_tinh_cccd():
    """LLM chép tỉnh/xã nơi thường trú trên CCCD vào trụ sở + thuế dù Đơn bỏ trống."""
    cccd = {"quocGia": "Việt Nam", "tinh": "Đắk Lắk", "xa": "Tân Lợi", "diaChi": "10 Đường Mẫu"}
    return [
        {"name": "TruSo_DiaChi", "value": dict(cccd)},
        {"name": "Thue_DiaChiNhanThongBao", "value": dict(cccd, xa="Xuân Hương")},
        {"name": "ChuHo_DiaChi", "value": dict(cccd, diaChi="12 Lê Lợi")},
    ]


def _page_values(fields, page):
    return {f["name"].split("$")[-1]: f["value"] for f in mapper.enrich(fields, page=page)}


def test_tru_so_bo_trong_tinh_xa_lay_theo_kinh_gui_khong_lay_cccd():
    fields = _llm_cop_tinh_cccd()
    assert mapper.fix_addresses_from_ocr(fields, _ocr_don()) == ["TruSo_DiaChi", "Thue_DiaChiNhanThongBao"]

    dia_chi = _page_values(fields, "dia-chi")
    assert dia_chi["CITY_IDFld"] == "Lâm Đồng"
    assert dia_chi["WARD_IDFld"] == "Xuân Hương - Đà Lạt"
    assert dia_chi["STREET_NUMBERFld"] == "10 Đường Mẫu"
    # 5.1 ghi "Xuân Hương" bỏ trống tỉnh → tỉnh theo trụ sở, ra cùng nơi → "Giống địa chỉ trụ sở".
    thue = _page_values(fields, "thong-tin-ve-thue")
    assert thue["REP_RECV_ADDR_TYPEFld"] == "1"
    assert "CITY_IDFld" not in thue
    # Địa chỉ chủ hộ (CCCD) không bị đụng.
    chu_ho = _page_values(fields, "chu-ho-kinh-doanh")
    assert chu_ho["CITY_IDFld"] == "Đắk Lắk"


def test_don_ghi_du_tinh_xa_thi_giu_ket_qua_llm():
    fields = _llm_cop_tinh_cccd()
    ocr = _ocr_don(tru_so_xa="Tân Lợi", tru_so_tinh="Đắk Lắk", thue_xa="Xuân Hương", thue_tinh=" Đắk Lắk")
    assert mapper.fix_addresses_from_ocr(fields, ocr) == []
    assert fields[0]["value"]["tinh"] == "Đắk Lắk" and fields[0]["value"]["xa"] == "Tân Lợi"


def test_tru_so_bo_trong_khong_co_kinh_gui_thi_de_trong_tinh_xa():
    fields = _llm_cop_tinh_cccd()
    mapper.fix_addresses_from_ocr(fields, _ocr_don(kinh_gui="Kính gửi: Cơ quan đăng ký kinh doanh"))
    dia_chi = _page_values(fields, "dia-chi")
    assert "CITY_IDFld" not in dia_chi and "WARD_IDFld" not in dia_chi
    assert dia_chi["STREET_NUMBERFld"] == "10 Đường Mẫu"


def test_kinh_gui_thi_xa_khong_bi_coi_la_ten_xa():
    fields = _llm_cop_tinh_cccd()
    mapper.fix_addresses_from_ocr(fields, _ocr_don(kinh_gui="Kính gửi: UBND thị xã Mẫu Sơn"))
    assert fields[0]["value"]["tinh"] == "" and fields[0]["value"]["xa"] == ""


def test_gia_tri_xa_viet_xuong_dong_duoi_nhan():
    block = "Xã/Phường/Đặc khu:\nXuân Hương\nTỉnh/Thành phố trực thuộc trung ương:\nĐiện thoại: 0900000001"
    assert mapper._ocr_line_value(block, mapper._OCR_WARD_LABEL) == "Xuân Hương"
    assert mapper._ocr_line_value(block, mapper._OCR_PROVINCE_LABEL) == ""


def test_khong_thay_khoi_tru_so_thi_khong_dung():
    fields = _llm_cop_tinh_cccd()
    assert mapper.fix_addresses_from_ocr(fields, "Giấy tờ khác không có mục trụ sở") == []
    assert fields[0]["value"]["xa"] == "Tân Lợi"
