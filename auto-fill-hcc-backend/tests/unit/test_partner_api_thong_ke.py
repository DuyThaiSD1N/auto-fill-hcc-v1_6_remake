"""API thống kê cho đối tác (/partner-api/v1): API key, phạm vi, số khớp web thống kê, /daily theo đơn vị."""
import pytest
from fastapi.testclient import TestClient

from app.dashboard import router as dashboard_router
from app.partner_api import keys, router as partner_router
from app.partner_api.app import partner_app
from scripts import api_keys as cli
from tests.unit.test_bug_reports import _Db


def _unit(uid, xa, tinh="Tỉnh T"):
    return {"unitId": uid, "name": f"HCC {xa}", "xa": xa, "tinh": tinh, "role": "commune", "accessDisabled": False}


_UNITS = [_unit("1", "Xã A"), _unit("2", "Xã B"), _unit("3", "Xã C", "Tỉnh K")]
# Mỗi đơn vị, mỗi ngày: (Auto Fill, Handfree).
_DAILY = {("1", "2026-11-10"): (2, 1), ("1", "2026-11-11"): (3, 0), ("2", "2026-11-11"): (4, 2), ("3", "2026-11-10"): (5, 0)}


def _scope_for(user):
    if user.get("role") == "province_admin":
        units = [u for u in _UNITS if u["tinh"] == user["tinh"]]
        return {"role": "province_admin", "scopeKind": "province", "province": user["tinh"], "canViewUnits": True,
                "self": {}, "units": units}
    return {"role": "admin", "scopeKind": "all", "province": None, "canViewUnits": True, "self": {}, "units": _UNITS}


@pytest.fixture()
def api(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(keys, "get_db", lambda: fake)
    monkeypatch.setattr(cli, "get_db", lambda: fake)

    async def resolve_scope(user):
        return _scope_for(user)

    async def resolve(user, province):
        return dashboard_router.narrow_to_province(_scope_for(user), province)

    async def daily_counts(user_ids, date_from, date_to, experience):
        i = 0 if experience == "autofill" else 1
        return [{"userId": u, "date": d, "count": c[i]} for (u, d), c in _DAILY.items() if u in user_ids and c[i]]

    async def af_stats(user_ids, date_from, date_to, experience):
        per = {u: sum(c[0] for (x, _), c in _DAILY.items() if x == u) for u in user_ids}
        return {"wards": [{"userId": u, "requests": 9, "procedures": [{"key": "ks", "label": "Khai sinh", "count": n}]}
                          for u, n in per.items() if n],
                "procedures": [{"key": "ks", "label": "Khai sinh", "count": sum(per.values())}],
                "totalDossiers": sum(per.values()), "totalRequests": 9}

    async def hf_units(units, date_from, date_to, want_daily):
        by_key, daily = {}, {}
        for u in units:
            n = sum(c[1] for (x, _), c in _DAILY.items() if x == u["unitId"])
            by_key[dashboard_router.account_unit_key(u["tinh"], u["xa"], u["unitId"])] = {
                "procedures": [{"procedureKey": "ks", "label": "Khai sinh", "count": n}]}
            for (x, d), c in _DAILY.items():
                if x == u["unitId"] and c[1]:
                    daily[d] = daily.get(d, 0) + c[1]
        return by_key, daily, True

    monkeypatch.setattr(dashboard_router, "_resolve", resolve)
    monkeypatch.setattr(partner_router, "resolve_dashboard_scope", resolve_scope)
    monkeypatch.setattr(dashboard_router.cutover, "dossier_stats", af_stats)
    monkeypatch.setattr(dashboard_router.cutover, "daily_dossier_counts", daily_counts)
    monkeypatch.setattr(dashboard_router, "fetch_handfree", hf_units)
    client = TestClient(partner_app)
    client.db = fake
    return client


def _key(api, name="Đối tác", province=None):
    import asyncio
    return asyncio.run(cli._create(name, province, apply=True))["apiKey"]


def test_thieu_sai_hoac_thu_hoi_key_deu_401(api):
    assert api.get("/units").status_code == 401
    assert api.get("/units", headers={"X-API-Key": "hcc_stats_sai"}).json()["error"] == "INVALID_API_KEY"
    raw = _key(api)
    assert api.get("/units", headers={"X-API-Key": raw}).status_code == 200
    doc = api.db.raw.api_keys.find_one({})
    assert doc["key_hash"] != raw and raw not in str(doc), "chỉ lưu bản băm"
    assert doc["last_used_at"] is not None
    import asyncio
    asyncio.run(cli._revoke(str(doc["_id"]), apply=True))
    assert api.get("/units", headers={"X-API-Key": raw}).status_code == 401


def test_key_khong_goi_duoc_api_khac():
    from app.main import app

    res = TestClient(app).get("/api/v1/dashboard/summary", headers={"X-API-Key": "hcc_stats_bat_ky"})
    assert res.status_code == 401


def test_docs_rieng_chi_co_api_doi_tac(api):
    paths = set(api.get("/openapi.json").json()["paths"])
    assert paths == {"/units", "/stats", "/daily", "/ratings", "/dossiers"}


def test_stats_khop_cach_tinh_web_va_khong_lo_so_luot(api):
    h = {"X-API-Key": _key(api)}
    body = api.get("/stats", headers=h, params={"dateFrom": "2026-11-10", "dateTo": "2026-11-11"}).json()
    assert body["kpis"]["dossiers"] == 2 + 1 + 3 + 4 + 2 + 5
    assert "requests" not in body["kpis"] and "scope" not in body
    assert {u["unitId"]: u["dossiers"] for u in body["units"]} == {"1": 6, "2": 6, "3": 5}
    assert set(body["units"][0]) == {"unitId", "name", "ward", "province", "dossiers", "procedureTypes", "topProcedure"}


def test_daily_tung_don_vi_cong_lai_bang_theo_ngay(api):
    h = {"X-API-Key": _key(api)}
    params = {"dateFrom": "2026-11-10", "dateTo": "2026-11-11"}
    body = api.get("/daily", headers=h, params=params).json()
    by_unit = {u["unitId"]: u for u in body["units"]}
    assert by_unit["1"]["days"] == [{"date": "2026-11-10", "count": 3}, {"date": "2026-11-11", "count": 3}]
    assert by_unit["2"]["total"] == 6 and by_unit["3"]["total"] == 5
    per_day: dict[str, int] = {}
    for u in body["units"]:
        for d in u["days"]:
            per_day[d["date"]] = per_day.get(d["date"], 0) + d["count"]
    stats = api.get("/stats", headers=h, params=params).json()
    assert per_day == {d["date"]: d["count"] for d in stats["byDay"]}
    only = api.get("/daily", headers=h, params={**params, "unit": "2"}).json()
    assert [u["unitId"] for u in only["units"]] == ["2"]
    assert api.get("/daily", headers=h, params={"dateFrom": "2026-01-01", "dateTo": "2026-11-11"}).status_code == 400
    assert api.get("/daily", headers=h).status_code == 422


def test_key_khoa_tinh_chi_thay_tinh_do(api):
    h = {"X-API-Key": _key(api, province="Tỉnh K")}
    assert [u["unitId"] for u in api.get("/units", headers=h).json()["units"]] == ["3"]
    assert api.get("/stats", headers=h, params={"unit": "1"}).status_code == 403


def test_nhat_ky_va_danh_gia_bo_thong_tin_noi_bo(api, monkeypatch):
    async def fake_logs(**kw):
        return {"scope": {"self": {}}, "items": [], "total": 0, "page": kw["page"], "pageSize": kw["pageSize"]}

    async def fake_ratings(**kw):
        return {"scope": {}, "selected": None, "selectedUnits": [], "rated": 1,
                "units": [{"unitId": "1", "name": "HCC Xã A", "xa": "Xã A", "rated": 1}]}

    monkeypatch.setattr(dashboard_router, "logs", fake_logs)
    monkeypatch.setattr(dashboard_router, "ratings", fake_ratings)
    h = {"X-API-Key": _key(api)}
    logs = api.get("/dossiers", headers=h, params={"pageSize": 20}).json()
    assert "scope" not in logs and logs["pageSize"] == 20
    assert api.get("/dossiers", headers=h, params={"pageSize": 500}).status_code == 422
    rating = api.get("/ratings", headers=h).json()
    assert "scope" not in rating and rating["units"][0] == {"unitId": "1", "name": "HCC Xã A", "ward": "Xã A",
                                                            "province": "Tỉnh T", "rated": 1}
