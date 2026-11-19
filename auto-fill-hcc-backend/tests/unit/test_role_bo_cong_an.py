"""Role Hành chính công Bộ Công an ("bca"): nhóm thống kê riêng, không cộng vào tỉnh nào; chỉ thủ tục Bộ Công an."""
import mongomock
import pytest

from app.core.deps import require_dashboard
from app.dashboard import procedures as dashboard_procedures
from app.dashboard import scope as dashboard_scope
from app.procedures.bca import bca_keys, for_role
from app.reports.schemas import ExcelExportRequest
from app.reports.service import select_accounts
from app.users.roles import BCA_GROUP, stats_province
from app.users.schemas import UserCreate
from app.work_minutes import rules as minutes_rules

USERS = [
    {"_id": "c1", "username": "hcc-a", "name": "HCC Xã A", "role": "commune", "tinh": "Lai Châu", "xa": "Xã Pa Tần"},
    {"_id": "p1", "username": "hcc-t", "name": "HCC tỉnh", "role": "province", "tinh": "Lai Châu"},
    # Cùng tỉnh + xã với HCC xã: số liệu vẫn không được lẫn sang nhau.
    {"_id": "b1", "username": "bca-a", "name": "Công an xã Pa Tần", "role": "bca", "tinh": "Lai Châu", "xa": "Xã Pa Tần"},
    {"_id": "b2", "username": "bca-b", "name": "Công an tỉnh", "role": "bca", "tinh": "Lai Châu"},
    {"_id": "u1", "username": "khac", "role": "user", "tinh": "Lai Châu", "xa": "Xã Pa Tần"},
    {"_id": "t1", "username": "test-bca", "role": "bca_tester", "tinh": "Lai Châu", "xa": "Xã Pa Tần"},
]


async def _dashboard_gate(user):
    import inspect
    out = require_dashboard(user)
    return await out if inspect.isawaitable(out) else out


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return list(self.docs)


class _Users:
    def __init__(self):
        self.coll = mongomock.MongoClient().db.users
        self.coll.insert_many([dict(u) for u in USERS])

    def find(self, query, projection=None):
        return _Cursor(self.coll.find(query, projection))


class _Db:
    users = _Users()


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    fake.users = _Users()
    monkeypatch.setattr(dashboard_scope, "get_db", lambda: fake)
    return fake


async def test_admin_thay_nhom_bo_cong_an_rieng(db):
    scope = await dashboard_scope.resolve_dashboard_scope({"_id": "ad", "role": "admin"})
    units = {u["unitId"]: u for u in scope["units"]}
    assert set(units) == {"c1", "p1", "b1", "b2"}
    assert units["b1"]["tinh"] == BCA_GROUP and units["b1"]["accountTinh"] == "Lai Châu"
    options = {o["name"]: o["unitCount"] for o in dashboard_scope.province_options(scope["units"])}
    assert options == {"Tỉnh Lai Châu": 2, BCA_GROUP: 2}
    bca = dashboard_scope.narrow_to_province(scope, BCA_GROUP)
    assert {u["unitId"] for u in bca["units"]} == {"b1", "b2"}
    lai_chau = dashboard_scope.narrow_to_province(scope, "Lai Châu")
    assert {u["unitId"] for u in lai_chau["units"]} == {"c1", "p1"}


async def test_tai_khoan_tinh_khong_thay_bo_cong_an(db):
    scope = await dashboard_scope.resolve_dashboard_scope({"_id": "pa", "role": "province_admin", "tinh": "Lai Châu"})
    assert {u["unitId"] for u in scope["units"]} == {"c1", "p1"}


async def test_tai_khoan_bo_cong_an_tu_xem_minh_khong_can_xa(db):
    user = {"_id": "b2", "role": "bca", "tinh": "Lai Châu"}
    assert await _dashboard_gate(user) is user
    scope = await dashboard_scope.resolve_dashboard_scope(user)
    assert scope["scopeKind"] == "unit" and scope["province"] == BCA_GROUP
    assert [u["unitId"] for u in scope["units"]] == ["b2"] and scope["self"]["tinh"] == BCA_GROUP


def test_bao_cao_excel_tinh_khong_lan_bo_cong_an():
    accounts = [{**u, "tinh": stats_province(u)} for u in USERS]
    body = dict(dateFrom="2026-11-01", dateTo="2026-11-19", selectionMode="province", officialOnly=True)
    lai_chau = select_accounts(accounts, ExcelExportRequest(**body, province="Lai Châu"))
    assert {a["_id"] for a in lai_chau} == {"c1", "p1"}
    bca = select_accounts(accounts, ExcelExportRequest(**body, province=BCA_GROUP))
    assert {a["_id"] for a in bca} == {"b1", "b2"}


def test_chi_thu_tuc_bo_cong_an():
    from app.channels.handfree.procedure_registry import public_list

    keys = bca_keys()
    assert {"dang-ky-thuong-tru", "cap-doi-the-can-cuoc", "thong-bao-luu-tru", "cap-ho-chieu-pho-thong-o-trong-nuoc",
            "dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc"} <= keys
    assert "ket-hon" not in keys and "chung-thuc-ban-sao" not in keys
    everything = public_list()
    assert {p["key"] for p in for_role(everything, "bca")} == {p["key"] for p in everything} & keys
    assert for_role(everything, "commune") == everything


def test_tro_ly_handfree_chi_hien_va_chi_mo_thu_tuc_bo_cong_an():
    from app.channels.handfree.chat import flow

    conv = {"auth_user": {"role": "bca", "province_slug": "laichau"}, "state": "greet"}
    assert {p["key"] for p in flow._account_procedures(conv)} <= bca_keys()
    flow._to_confirm_procedure(conv, "ket-hon")
    assert conv.get("procedure_key") != "ket-hon" and conv.get("state") != "confirm_procedure"
    others = {"auth_user": {"role": "commune", "province_slug": "laichau"}}
    assert "ket-hon" in {p["key"] for p in flow._account_procedures(others)}


def test_danh_muc_thong_ke_cua_tai_khoan_bo_cong_an():
    scope = {"scopeKind": "unit", "province": BCA_GROUP, "role": "bca", "self": {"role": "bca"}}
    keys = {i["key"] for i in dashboard_procedures.catalog(scope)["items"]}
    assert keys and keys <= bca_keys()


def test_bien_ban_ghi_tinh_that_cua_tai_khoan():
    unit = {"unitId": "b1", "xa": "Xã Pa Tần", "tinh": BCA_GROUP, "accountTinh": "Lai Châu"}
    assert minutes_rules.prov_of(unit) == "tỉnh Lai Châu"


def test_tao_tai_khoan_role_bca():
    assert UserCreate(username="bca-c", password="12345678", role="bca").role == "bca"


async def test_tester_bo_cong_an_chi_thu_tuc_bca_va_khong_la_don_vi(db):
    """Tester HCC Bộ Công an: thủ tục như tài khoản Bộ Công an, thống kê như tester (không thành đơn vị)."""
    from app.channels.handfree.chat import flow
    from app.channels.handfree.procedure_registry import public_list

    assert {p["key"] for p in for_role(public_list(), "bca_tester")} <= bca_keys()
    conv = {"auth_user": {"role": "bca_tester", "province_slug": "laichau"}, "state": "greet"}
    flow._to_confirm_procedure(conv, "ket-hon")
    assert conv.get("procedure_key") != "ket-hon"
    admin = await dashboard_scope.resolve_dashboard_scope({"_id": "ad", "role": "admin"})
    assert "t1" not in {u["unitId"] for u in admin["units"]}
    own = await dashboard_scope.resolve_dashboard_scope({"_id": "t1", "role": "bca_tester", "tinh": "Lai Châu"})
    assert own["province"] == BCA_GROUP and own["self"]["tinh"] == BCA_GROUP
    assert await _dashboard_gate({"_id": "t1", "role": "bca_tester", "tinh": "Lai Châu"})
    assert UserCreate(username="test-bca2", password="12345678", role="bca_tester").role == "bca_tester"
