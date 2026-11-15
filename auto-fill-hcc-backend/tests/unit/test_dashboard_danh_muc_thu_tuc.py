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
    # URL kê khai có mã thì không lấy thêm mã của biến thể chỉ dùng để nhận diện trang.
    assert items["lien-thong"]["codes"] == ["2.000987"]
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


def test_registry_that_thu_tuc_nao_co_ma_cung_tra_ma(monkeypatch):
    """Mã ở trường `code` hoặc ở link kê khai cùng key cũng phải lên danh mục, không chỉ mã trong URL."""
    monkeypatch.undo()
    items = {i["key"]: i for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    assert "1.115820" in items["dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao"]["codes"]
    assert "1.013229" in items["sua-chua-cai-tao-gpxd-nha-o-rieng-le"]["codes"]
    assert sum(1 for i in items.values() if not i["codes"]) <= 1
    assert items["khai-sinh-dang-ky"]["codes"] == ["2.000987"]


def test_xuat_excel_dung_dong_dang_loc_va_trong_pham_vi():
    import io
    from datetime import datetime, timezone

    from openpyxl import load_workbook

    from app.dashboard.export import build_catalog_workbook

    items = dashboard_procedures.catalog(_scope("unit", "Tỉnh Lai Châu"))["items"]
    by_key = {i["key"]: i for i in items}
    picked = [by_key[k] for k in ["lien-thong", "chung", "rieng-lai-chau"]]
    raw = build_catalog_workbook(picked, "Dùng chung", datetime(2026, 11, 13, tzinfo=timezone.utc))
    ws = load_workbook(io.BytesIO(raw)).active
    rows = [r for r in ws.iter_rows(min_row=4, values_only=True)]
    assert rows[0] == ("STT", "Tên thủ tục", "Mã TTHC", "Áp dụng")
    assert rows[1:] == [
        (1, "Liên thông", "2.000987", "Dùng chung"),
        (2, "Thủ tục chung", "1.004772", "Dùng chung"),
        (3, "Riêng Lai Châu", None, "Riêng · Lai Châu"),
    ]
    assert "Dùng chung" in ws["A2"].value and "3 thủ tục" in ws["A2"].value

