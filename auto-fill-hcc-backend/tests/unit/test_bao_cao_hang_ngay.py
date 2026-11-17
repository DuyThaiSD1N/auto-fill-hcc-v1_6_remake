"""Báo cáo hằng ngày trên web thống kê: quyền theo vai trò, 1 báo cáo/ngày, sửa trong ngày, lọc, đơn vị chưa gửi, Excel."""
import io
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.core.deps import require_dashboard
from app.core.errors import AppError, app_error_handler
from app.daily_reports import repo, rules
from app.daily_reports import router as daily_router
from app.users import tdp_rollup
from tests.unit.test_bug_reports import ADMIN, PROVINCE, TDP, WARD_A, WARD_B, WARD_C, _Db, _scope

TODAY = "2026-11-13"


@pytest.fixture()
def as_user(monkeypatch):
    fake = _Db()
    for module in (repo, tdp_rollup):
        monkeypatch.setattr(module, "get_db", lambda: fake)

    async def _links():
        return {"ut": {"parentId": "ua", "parentName": WARD_A["name"]}}

    async def _resolve(user):
        return _scope(user)

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", _links)
    monkeypatch.setattr(daily_router, "resolve_dashboard_scope", _resolve)
    monkeypatch.setattr(rules, "today_vn", lambda now=None: TODAY)
    current = {"user": WARD_A}
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(daily_router.router)
    app.dependency_overrides[require_dashboard] = lambda: current["user"]
    client = TestClient(app)

    def _switch(user):
        current["user"] = user
        return client

    _switch.db = fake
    return _switch


def _send(client, tl=10, tt=12, good="Thuận lợi", bad=""):
    return client.put("/api/v1/daily-reports/today",
                      json={"assistantCount": tl, "actualCount": tt, "advantages": good, "difficulties": bad})


def _seed(db, user, day, tl, tt, unit_id=None, province="Tỉnh T"):
    at = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    db.raw.daily_reports.insert_one({
        "user_id": user["_id"], "unit_id": unit_id or user["_id"], "unit_name": user.get("xa"), "province": province,
        "date": day, "assistant_count": tl, "actual_count": tt, "advantages": "", "difficulties": "",
        "created_at": at, "updated_at": at, "log": [],
    })


def test_ngay_bao_cao_theo_gio_viet_nam():
    assert rules.today_vn(datetime(2026, 11, 12, 17, 30, tzinfo=timezone.utc)) == "2026-11-13"


def test_don_vi_gui_roi_sua_trong_ngay_khong_tao_ban_thu_hai(as_user):
    client = as_user(WARD_A)
    assert client.get("/api/v1/daily-reports/today").json() == {"date": TODAY, "report": None}
    first = _send(client).json()
    assert first["date"] == TODAY and first["assistantCount"] == 10 and first["editable"] is True
    assert first["updatedAt"] is None
    second = _send(client, tl=11, tt=11, bad="Mạng chậm").json()
    assert second["id"] == first["id"] and second["difficulties"] == "Mạng chậm"
    assert as_user.db.raw.daily_reports.count_documents({}) == 1
    log = as_user.db.raw.daily_reports.find_one({})["log"]
    assert [e["action"] for e in log] == ["create", "update"]
    assert client.get("/api/v1/daily-reports/summary").json()["sentToday"] is True


def test_kiem_so_lieu(as_user):
    client = as_user(WARD_A)
    assert _send(client, tl=-1).status_code == 400
    assert _send(client, tl=1, tt=1, good="x" * (rules.MAX_TEXT + 1)).status_code == 400
    assert _send(client, tl=rules.MAX_COUNT + 1).status_code == 400
    assert as_user.db.raw.daily_reports.count_documents({}) == 0


def test_bao_cao_cu_khoa_va_chi_thay_cua_minh(as_user):
    _seed(as_user.db, WARD_A, "2026-11-12", 5, 6)
    _seed(as_user.db, WARD_B, "2026-11-12", 7, 7)
    body = as_user(WARD_A).get("/api/v1/daily-reports").json()
    assert body["access"] == "reporter" and body["total"] == 1
    assert body["items"][0]["editable"] is False
    assert "missingToday" not in body


def test_tinh_khong_gui_duoc_va_chi_xem_don_vi_trong_tinh(as_user):
    _seed(as_user.db, WARD_A, TODAY, 5, 6)
    _seed(as_user.db, WARD_C, TODAY, 9, 9, province="Tỉnh K")
    client = as_user(PROVINCE)
    assert _send(client).status_code == 403
    body = client.get("/api/v1/daily-reports").json()
    assert [i["unitId"] for i in body["items"]] == ["ua"]
    assert body["unitCount"] == 2 and [u["unitId"] for u in body["missingToday"]] == ["ub"]
    assert body["totals"] == {"reports": 1, "assistant": 5, "actual": 6, "units": 1, "firstDate": TODAY}
    assert client.get("/api/v1/daily-reports", params={"unit": "uc"}).status_code == 403


def test_to_dan_pho_gan_vao_xa_cha(as_user):
    _send(as_user(TDP))
    body = as_user(PROVINCE).get("/api/v1/daily-reports").json()
    assert body["items"][0]["unitId"] == "ua"


def test_admin_loc_ngay_tinh_don_vi(as_user):
    _seed(as_user.db, WARD_A, "2026-11-10", 1, 2)
    _seed(as_user.db, WARD_A, "2026-11-12", 3, 4)
    _seed(as_user.db, WARD_C, "2026-11-12", 5, 5, province="Tỉnh K")
    client = as_user(ADMIN)
    body = client.get("/api/v1/daily-reports", params={"dateFrom": "2026-11-11", "dateTo": "2026-11-12"}).json()
    assert body["total"] == 2 and body["byDay"] == [{"date": "2026-11-12", "reports": 2, "assistant": 8, "actual": 9}]
    assert client.get("/api/v1/daily-reports", params={"unit": "uc"}).json()["total"] == 1
    assert client.get("/api/v1/daily-reports", params={"unit": "ua,uc"}).json()["total"] == 3
    assert client.get("/api/v1/daily-reports", params={"dateFrom": "13/11/2026"}).status_code == 400
    assert _send(client).status_code == 403


def test_xuat_excel(as_user):
    _seed(as_user.db, WARD_A, "2026-11-12", 3, 4)
    res = as_user(PROVINCE).get("/api/v1/daily-reports/export")
    assert res.status_code == 200
    wb = load_workbook(io.BytesIO(res.content))
    assert wb.sheetnames == ["Báo cáo", "Theo đơn vị"]
    row = [c.value for c in wb["Báo cáo"][2]]
    assert row[1] == "12/11/2026" and row[6:9] == [3, 4, 1]
    units = {r[1]: r for r in wb["Theo đơn vị"].iter_rows(min_row=2, values_only=True)}
    assert units["Phường Bắc Giang"][2:] == (1, 3, 4, 1, 75)
    own = load_workbook(io.BytesIO(as_user(WARD_A).get("/api/v1/daily-reports/export").content))
    assert own.sheetnames == ["Báo cáo"]


def test_chua_bao_cao_gop_tai_khoan_cung_xa_va_bo_tai_khoan_khoa(as_user, monkeypatch):
    """Xã có 2 tài khoản: một tài khoản gửi là xã đã báo cáo. Tài khoản tạm khoá không bị nhắc."""
    twin = {**_scope(WARD_A)["self"], "unitId": "ua2"}
    locked = {"unitId": "ul", "name": "HCC Xã Khoá", "xa": "Xã Khoá", "tinh": "Tỉnh T", "role": "commune",
              "accessDisabled": True}

    async def _resolve(user):
        scope = _scope(user)
        return {**scope, "units": scope["units"] + [twin, locked]} if user is PROVINCE else scope

    monkeypatch.setattr(daily_router, "resolve_dashboard_scope", _resolve)
    _send(as_user(WARD_A))
    client = as_user(PROVINCE)
    body = client.get("/api/v1/daily-reports").json()
    assert body["unitCount"] == 2, "Bắc Giang (2 tài khoản) + Phú Bình; bỏ tài khoản khoá"
    assert [u["unitIds"] for u in body["missingToday"]] == [["ub"]]
    summary = client.get("/api/v1/daily-reports/summary").json()
    assert (summary["unitCount"], summary["reportedToday"]) == (2, 1)

