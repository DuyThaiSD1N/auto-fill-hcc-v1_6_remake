"""Khối "Chọn cơ quan thực hiện" của Cổng DVC quốc gia dùng tên tỉnh HIỆN HÀNH.

Bắc Ninh đã lên "Thành phố Bắc Ninh" và dropdown Tỉnh/Thành phố ở khối chọn cơ quan của
dichvucong.gov.vn cũng đã đổi theo. Extension gõ nguyên chuỗi vào ô tìm → lệnh select_agency phải
mang đúng tên cổng đang dùng. Cổng nào còn tên cũ thì khai ngoại lệ ở
catalog._PORTAL_AGENCY_PROVINCES (hiện trống).
"""
from app.channels.handfree.chat import flow
from app.channels.handfree.procedure_registry import get_procedure
from app.locations.catalog import portal_agency_province

KEY = "dieu-chinh-huu-tri-xa-hoi"


def test_ten_tinh_cho_khoi_chon_co_quan_giu_ten_hien_hanh():
    assert portal_agency_province("Thành phố Bắc Ninh") == "Thành phố Bắc Ninh"
    assert portal_agency_province("Thành phố Đà Nẵng") == "Thành phố Đà Nẵng"
    assert portal_agency_province("Tỉnh Lai Châu") == "Tỉnh Lai Châu"
    assert portal_agency_province("") == ""


def test_lenh_select_agency_mang_ten_thanh_pho_bac_ninh():
    loc = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Bắc Giang"}
    conv = {
        "_id": "t-bn", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": KEY, "client_capabilities": {}, "location": dict(loc),
    }
    r = flow._guide_login_on_page(conv, get_procedure(KEY) or {}, dict(loc), {"agencyBlock": True})
    assert len(r.actions) == 1
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Thành phố Bắc Ninh", "cổng đã đổi tên — không gõ 'Tỉnh Bắc Ninh' nữa"
    assert action["ward"] == "Phường Bắc Giang"
