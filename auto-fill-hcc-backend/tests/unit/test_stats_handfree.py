import pytest

from app.traces import router as traces_router


@pytest.mark.asyncio
async def test_stats_route_filters_handfree_source_locally(monkeypatch):
    captured = {}
    expected = {"scope": "official", "wards": [], "procedures": [], "totalDossiers": 4}

    async def fake_stats(*, scope, date_from, date_to, experience):
        captured.update({
            "scope": scope,
            "date_from": date_from,
            "date_to": date_to,
            "experience": experience,
        })
        return expected

    monkeypatch.setattr(traces_router.repo, "stats", fake_stats)
    result = await traces_router.stats(
        {},
        dateFrom="2026-08-18",
        dateTo="2026-08-18",
        scope="official",
        source="handfree",
    )

    assert result is expected
    assert captured["scope"] == "official"
    assert captured["experience"] == "handfree"
    assert captured["date_from"].isoformat() == "2026-08-17T17:00:00+00:00"
    assert captured["date_to"].isoformat() == "2026-08-18T17:00:00+00:00"


@pytest.mark.asyncio
async def test_stats_route_keeps_local_source_behavior(monkeypatch):
    captured = {}
    expected = {"scope": "all", "wards": [], "procedures": [], "totalDossiers": 2}

    async def fake_local(*, date_from, date_to, scope, experience):
        captured.update({
            "date_from": date_from,
            "date_to": date_to,
            "scope": scope,
            "experience": experience,
        })
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
    assert captured["experience"] == "autofill"
    assert captured["date_from"].isoformat() == "2026-08-17T17:00:00+00:00"
    assert captured["date_to"].isoformat() == "2026-08-18T17:00:00+00:00"


@pytest.mark.asyncio
async def test_stats_route_all_sources_removes_experience_filter(monkeypatch):
    captured = {}
    expected = {"scope": "official", "source": "all", "totalDossiers": 6}

    async def fake_stats(*, scope, date_from, date_to, experience):
        captured.update({
            "scope": scope,
            "date_from": date_from,
            "date_to": date_to,
            "experience": experience,
        })
        return expected

    monkeypatch.setattr(traces_router.repo, "stats", fake_stats)
    result = await traces_router.stats(
        {}, dateFrom=None, dateTo=None, scope="official", source="all",
    )

    assert result is expected
    assert captured == {
        "scope": "official",
        "date_from": None,
        "date_to": None,
        "experience": None,
    }
