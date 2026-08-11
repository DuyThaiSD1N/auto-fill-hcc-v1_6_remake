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


def test_submitter_with_different_name_is_marked_as_authorized_when_no_id_available():
    fields = [
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHo_SoDinhDanh", "value": "123456789"},
        {"name": "NguoiNop_HoTen", "value": "Trần Thị B"},
        {"name": "NguoiNop_SoDinhDanh", "value": ""},
    ]

    out = mapper.enrich(fields, page="nguoi-nop-ho-so")
    role = next(f for f in out if f["name"] == "ctl00$C$PERS_SUBGroup")

    assert role["value"] == "Người được ủy quyền"


def _submitter_page(fields: list[dict]) -> tuple[dict, dict]:
    out = mapper.enrich(fields, page="nguoi-nop-ho-so")
    by_name = {f["name"]: f["value"] for f in out}
    plan = by_name.get("__applicantAddress") or {}
    return by_name, plan


def _addr(tinh: str, xa: str, dia_chi: str) -> dict:
    return {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": dia_chi}


def test_submitter_is_owner_uses_application_address():
    # Người nộp chính là chủ hộ → lấy thẳng địa chỉ cá nhân trên đơn, bỏ qua địa chỉ CCCD.
    by_name, plan = _submitter_page([
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHo_SoDinhDanh", "value": "001199000111"},
        {"name": "ChuHo_DiaChi", "value": _addr("Lâm Đồng", "Đoàn Kết", "SN 300 Tổ 11")},
        {"name": "NguoiNop_DiaChiCCCD", "value": _addr("Lâm Đồng", "Tân Phong", "SN 1 Tổ 2")},
    ])

    assert by_name["ctl00$C$PERS_SUBGroup"] == "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh"
    assert by_name["ctl00$C$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "SN 300 Tổ 11"
    assert plan["role"] == "self"
    assert plan["self"]["diaChi"] == "SN 300 Tổ 11"


def test_authorized_submitter_prefers_authorization_letter_address():
    # Người nộp khác chủ hộ → giấy ủy quyền thắng cả địa chỉ trên đơn lẫn CCCD.
    by_name, plan = _submitter_page([
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHo_SoDinhDanh", "value": "001199000111"},
        {"name": "ChuHo_DiaChi", "value": _addr("Lâm Đồng", "Đoàn Kết", "SN 300 Tổ 11")},
        {"name": "NguoiNop_HoTen", "value": "Trần Thị B"},
        {"name": "NguoiNop_SoDinhDanh", "value": "001199000222"},
        {"name": "NguoiNop_DiaChiUyQuyen", "value": _addr("Lâm Đồng", "Tân Phong", "SN 7 Tổ 3")},
        {"name": "NguoiNop_DiaChi", "value": _addr("Lâm Đồng", "Tân Phong", "SN 8 Tổ 4")},
        {"name": "NguoiNop_DiaChiCCCD", "value": _addr("Lâm Đồng", "Tân Phong", "SN 9 Tổ 5")},
    ])

    assert by_name["ctl00$C$PERS_SUBGroup"] == "Người được ủy quyền"
    assert by_name["ctl00$C$PERSCtl$FULL_NAMEFld"] == "Trần Thị B"
    assert by_name["ctl00$C$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "SN 7 Tổ 3"
    assert plan["role"] == "authorized"
    # FE nhận đủ chuỗi ưu tiên để chọn lại khi cổng tick vai trò khác dự đoán của mapper.
    assert [key for key in plan["authorized"]] == ["uyQuyen", "donDeNghi", "cccd"]
    assert plan["self"]["diaChi"] == "SN 300 Tổ 11"


def test_authorized_submitter_falls_back_to_identity_card_address():
    _, plan = _submitter_page([
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHo_DiaChi", "value": _addr("Lâm Đồng", "Đoàn Kết", "SN 300 Tổ 11")},
        {"name": "HasMultipleCCCD", "value": True},
        {"name": "NguoiNop_DiaChiCCCD", "value": _addr("Lâm Đồng", "Tân Phong", "SN 9 Tổ 5")},
    ])

    assert plan["role"] == "authorized"
    assert list(plan["authorized"]) == ["cccd"]
    assert plan["authorized"]["cccd"]["diaChi"] == "SN 9 Tổ 5"


def test_empty_address_object_is_not_treated_as_a_source():
    # OCR trả object rỗng → không được coi là có địa chỉ (nếu không FE chỉ điền mỗi "Việt Nam").
    by_name, plan = _submitter_page([
        {"name": "ChuHo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "HasMultipleCCCD", "value": True},
        {"name": "NguoiNop_DiaChiUyQuyen", "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}},
        {"name": "NguoiNop_DiaChiCCCD", "value": _addr("Lâm Đồng", "Tân Phong", "SN 9 Tổ 5")},
    ])

    assert list(plan["authorized"]) == ["cccd"]
    assert by_name["ctl00$C$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "SN 9 Tổ 5"


def test_business_schema_and_prompt_only_define_three_phone_sources():
    names = {field["name"] for field in FIELDS}

    assert {"TruSo_DienThoai", "ChuHo_DienThoai", "Thue_DienThoai"} <= names
    assert "NguoiNop_DienThoai" not in names
    assert "CHỈ có 3 nhóm liên hệ cần trích từ hồ sơ" in EXTRA_RULES
    assert "KHÔNG lấy liên hệ người nộp thay cho trụ sở, chủ hộ hoặc thuế" in EXTRA_RULES
