"""Khối "Chọn cơ quan thực hiện" của Cổng DVC quốc gia còn ghi tên tỉnh CŨ.

Bắc Ninh đã lên "Thành phố Bắc Ninh" (danh mục, tài khoản, biểu mẫu kê khai đều đổi), nhưng
dropdown Tỉnh/Thành phố ở khối chọn cơ quan của dichvucong.gov.vn vẫn là "Tỉnh Bắc Ninh".
Extension gõ nguyên chuỗi vào ô tìm → lệnh select_agency phải mang tên cổng đang dùng, còn câu
thoại/địa bàn phiên vẫn là tên hiện hành.
"""
from app.channels.handfree.chat import flow
from app.channels.handfree.procedure_registry import get_procedure
from app.locations.catalog import portal_agency_province

KEY = "dieu-chinh-huu-tri-xa-hoi"


def test_ten_tinh_cho_khoi_chon_co_quan():
    assert portal_agency_province("Thành phố Bắc Ninh") == "Tỉnh Bắc Ninh"
    assert portal_agency_province("Bắc Ninh") == "Tỉnh Bắc Ninh"
    assert portal_agency_province("bacninh") == "Tỉnh Bắc Ninh"
    # Tỉnh không có ngoại lệ: giữ nguyên chuỗi đang có.
    assert portal_agency_province("Thành phố Đà Nẵng") == "Thành phố Đà Nẵng"
    assert portal_agency_province("Tỉnh Lai Châu") == "Tỉnh Lai Châu"
    assert portal_agency_province("") == ""


def test_lenh_select_agency_mang_ten_tinh_cua_cong():
    loc = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Bắc Giang"}
    conv = {
        "_id": "t-bn", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": KEY, "client_capabilities": {}, "location": dict(loc),
    }
    r = flow._guide_login_on_page(conv, get_procedure(KEY) or {}, dict(loc), {"agencyBlock": True})
    assert len(r.actions) == 1
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Tỉnh Bắc Ninh"
    assert action["ward"] == "Phường Bắc Giang"
    assert conv["location"]["province"] == "Thành phố Bắc Ninh"
