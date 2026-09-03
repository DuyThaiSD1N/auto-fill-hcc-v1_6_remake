import pytest

from app.reports import handfree_client
from app.reports.schemas import ExcelExportRequest


@pytest.mark.asyncio
async def test_handfree_stats_uses_merged_user_id_and_source_filter(monkeypatch):
    captured = {}

    async def fake_stats(**kwargs):
        captured.update(kwargs)
        return {"wards": [{
            "userId": "merged-user",
            "procedures": [{"key": "ket-hon", "count": 5}],
        }]}

    monkeypatch.setattr(handfree_client.traces_repo, "stats_by_user_ids", fake_stats)
    body = ExcelExportRequest(
        dateFrom="2026-08-18",
        dateTo="2026-08-18",
        selectionMode="accounts",
        accountIds=["merged-user"],
        includeHandfree=True,
    )
    result = await handfree_client.fetch_handfree_stats([{
        "_id": "merged-user",
        "username": "hcctanphong",
        "tinh": "Tỉnh Lai Châu",
        "xa": "Phường Tân Phong",
    }], body)

    assert captured["user_ids"] == ["merged-user"]
    assert captured["experience"] == "handfree"
    assert result["units"][0]["procedures"][0]["count"] == 5


@pytest.mark.asyncio
async def test_handfree_dashboard_reads_local_source(monkeypatch):
    captured = {}
    expected = {"source": "handfree", "wards": [], "totalDossiers": 12}

    async def fake_stats(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(handfree_client.traces_repo, "stats", fake_stats)
    result = await handfree_client.fetch_handfree_dashboard_stats(
        scope="official",
        date_from="2026-08-18",
        date_to="2026-08-18",
    )

    assert result is expected
    assert captured["scope"] == "official"
    assert captured["experience"] == "handfree"
    assert captured["date_from"].isoformat() == "2026-08-17T17:00:00+00:00"
    assert captured["date_to"].isoformat() == "2026-08-18T17:00:00+00:00"
