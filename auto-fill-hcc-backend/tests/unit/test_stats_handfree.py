import pytest

from app.traces import router as traces_router


@pytest.mark.asyncio
async def test_stats_route_proxies_handfree_source(monkeypatch):
    captured = {}
    expected = {"scope": "official", "wards": [], "procedures": [], "totalDossiers": 4}

    async def fake_handfree(*, scope, date_from, date_to):
        captured.update({"scope": scope, "date_from": date_from, "date_to": date_to})
        return expected

    monkeypatch.setattr(traces_router, "fetch_handfree_dashboard_stats", fake_handfree)
    result = await traces_router.stats(
        {},
        dateFrom="2026-08-18",
        dateTo="2026-08-18",
        scope="official",
        source="handfree",
    )

    assert result is expected
    assert captured == {
        "scope": "official",
        "date_from": "2026-08-18",
        "date_to": "2026-08-18",
    }


@pytest.mark.asyncio
async def test_stats_route_keeps_local_source_behavior(monkeypatch):
    captured = {}
    expected = {"scope": "all", "wards": [], "procedures": [], "totalDossiers": 2}

    async def fake_local(*, date_from, date_to, scope):
        captured.update({"date_from": date_from, "date_to": date_to, "scope": scope})
        return expected

    monkeypatch.setattr(traces_router.repo, "stats", fake_local)
    result = await traces_router.stats(
        {},
        dateFrom="2026-08-18",
        dateTo="2026-08-18",
        scope="all",
        source="autofill",
    )

    assert result is expected
    assert captured["scope"] == "all"
    assert captured["date_from"].isoformat() == "2026-08-17T17:00:00+00:00"
    assert captured["date_to"].isoformat() == "2026-08-18T17:00:00+00:00"
