"""Trang Danh mục thủ tục (thống kê): danh sách handfree theo tỉnh của tài khoản.

Tài khoản xã/tỉnh thấy thủ tục dùng chung + riêng của tỉnh mình; không xác định được tỉnh thì chỉ
dùng chung; admin toàn hệ thống thấy hết kèm danh sách tỉnh có thủ tục riêng.
"""
import pytest

from app.dashboard import procedures as dashboard_procedures

_PROCS = [
    {"key": "chung", "label": "Thủ tục chung", "shortLabel": "Chung",
     "detect": {"urlIncludes": ["maThuTuc=1.004772"]}},
    {"key": "lien-thong", "label": "Liên thông", "keKhaiUrl": "https://x/#/ke-khai/2.000987",
     "detect": {"urlIncludes": ["#/ke-khai/2.000986", "#/ke-khai/2.000987"]}},
    {"key": "rieng-lai-chau", "label": "Riêng Lai Châu", "provinceOnly": ["laichau"]},
    {"key": "rieng-hai-tinh", "label": "Riêng hai tỉnh", "provinceOnly": ["quangtri", "danang"]},
]


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    monkeypatch.setattr(dashboard_procedures, "public_list", lambda: _PROCS)
    # _PROCS là key giả, không có dòng trong bảng hoàn thiện theo tỉnh → coi như đã hoàn thiện.
    monkeypatch.setattr(dashboard_procedures, "is_ready_in_province", lambda proc, slug: True)


def _scope(kind, province=None):
    return {"scopeKind": kind, "province": province}


def _keys(body):
    return [item["key"] for item in body["items"]]


@pytest.mark.parametrize("kind", ["unit", "province"])
def test_tai_khoan_tinh_thay_chung_va_rieng_tinh_minh(kind):
    body = dashboard_procedures.catalog(_scope(kind, "Tỉnh Lai Châu"))
    assert _keys(body) == ["chung", "lien-thong", "rieng-lai-chau"]
    assert body["province"] == {"slug": "laichau", "name": "Lai Châu"}
    assert body["provinces"] == [{"slug": "laichau", "name": "Lai Châu", "count": 1}]


def test_tai_khoan_khong_xac_dinh_tinh_chi_thay_dung_chung():
    body = dashboard_procedures.catalog(_scope("unit", None))
    assert _keys(body) == ["chung", "lien-thong"]
    assert body["province"] is None
    assert body["provinces"] == []


def test_admin_thay_het_va_co_danh_sach_tinh():
    body = dashboard_procedures.catalog(_scope("all"))
    assert _keys(body) == ["chung", "lien-thong", "rieng-lai-chau", "rieng-hai-tinh"]
    assert [p["name"] for p in body["provinces"]] == ["Đà Nẵng", "Lai Châu", "Quảng Trị"]
    hai_tinh = body["items"][3]
    assert [p["slug"] for p in hai_tinh["provinces"]] == ["danang", "quangtri"]


def test_ma_tthc_lay_tu_url_ke_khai_va_nhan_dien_khong_trung():
    items = {i["key"]: i for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    assert items["chung"]["codes"] == ["1.004772"]
    assert items["lien-thong"]["codes"] == ["2.000987", "2.000986"]
    assert items["rieng-lai-chau"]["codes"] == []


def test_khong_tra_cau_hinh_noi_bo():
    item = dashboard_procedures.catalog(_scope("all"))["items"][0]
    assert set(item) == {"key", "label", "shortLabel", "codes", "provinces"}


def test_registry_that_khop_luat_cua_tro_ly(monkeypatch):
    """Không mock: tài khoản Lai Châu thấy đúng tập mà trợ lý hiện cho tỉnh đó."""
    monkeypatch.undo()
    from app.channels.handfree.procedure_registry import public_list_for

    body = dashboard_procedures.catalog(_scope("unit", "Tỉnh Lai Châu"))
    assert _keys(body) == [p["key"] for p in public_list_for("laichau")]
