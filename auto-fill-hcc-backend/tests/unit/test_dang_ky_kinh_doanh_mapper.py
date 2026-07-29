"""Regression tests cho mapper Đăng ký kinh doanh hộ kinh doanh.

Khóa lại 3 chuẩn hóa xác định (deterministic) từ OCR "Giấy đề nghị":
- Số điện thoại: khôi phục số 0 đứng đầu cho số di động VN.
- Họ tên: viết hoa chữ đầu mỗi từ (giấy ghi IN HOA).
- Trang chủ hộ: gom đúng các field UI.
"""

from app.pipelines.dang_ky_kinh_doanh.process import mapper
from app.pipelines.dang_ky_kinh_doanh.process.mapper import _clean_phone, _clean_ward, _proper_name


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
