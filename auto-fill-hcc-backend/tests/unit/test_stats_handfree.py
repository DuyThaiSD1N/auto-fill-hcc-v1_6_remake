import pytest

from app.stats import cutover
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

    # Khoảng nằm trọn TRƯỚC mốc 14/9/2026 → số liệu phải y hệt cách cũ, chỉ thêm khóa
    # `counting` để màn hình biết đang đọc số kiểu nào.
    assert {k: v for k, v in result.items() if k != "counting"} == expected
    assert result["counting"]["mode"] == "legacy"
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

    assert {k: v for k, v in result.items() if k != "counting"} == expected
    assert result["counting"]["mode"] == "legacy"
    assert captured["scope"] == "all"
    assert captured["experience"] == "autofill"
    assert captured["date_from"].isoformat() == "2026-08-17T17:00:00+00:00"
    assert captured["date_to"].isoformat() == "2026-08-18T17:00:00+00:00"


@pytest.mark.asyncio
async def test_stats_route_all_sources_removes_experience_filter(monkeypatch):
    """source="all" phải bỏ lọc experience ở CẢ HAI nguồn đếm.

    Khoảng để trống = "xem tất cả" nên vắt qua mốc 14/9/2026: cách cũ chạy nửa trước, cách
    đếm hồ sơ đã nộp chạy nửa sau. Bỏ sót experience=None ở một bên là màn quản trị hiện
    thiếu hẳn một kênh mà không báo lỗi gì.
    """
    calls: list[dict] = []
    submitted: list[dict] = []

    async def fake_stats(*, scope, date_from, date_to, experience):
        calls.append({
            "scope": scope, "date_from": date_from, "date_to": date_to, "experience": experience,
        })
        return {"scope": "official", "source": "all", "wards": [], "procedures": []}

    async def fake_scope_ids(scope):
        return ["u-official"]

    async def fake_submitted(*, user_ids, date_from, date_to, experience):
        submitted.append({"user_ids": user_ids, "experience": experience})
        return [{"userId": "u-official", "procedure": "p1", "label": "P1", "name": "Phường A", "count": 6}]

    monkeypatch.setattr(traces_router.repo, "stats", fake_stats)
    monkeypatch.setattr(traces_router.repo, "stats_scope_user_ids", fake_scope_ids)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_counts", fake_submitted)
    result = await traces_router.stats(
        {}, dateFrom=None, dateTo=None, scope="official", source="all",
    )

    assert result["totalDossiers"] == 6
    assert result["source"] == "all", "các khóa ngoài số hồ sơ phải giữ nguyên"
    # Lượt đầu là toàn khoảng (lấy số lượt xử lý/tài liệu), lượt sau là nửa trước mốc.
    assert calls[0] == {
        "scope": "official", "date_from": None, "date_to": None, "experience": None,
    }
    assert calls[1]["date_to"] == cutover.SUBMITTED_COUNT_FROM
    assert all(call["experience"] is None for call in calls)
    assert submitted == [{"user_ids": ["u-official"], "experience": None}]
