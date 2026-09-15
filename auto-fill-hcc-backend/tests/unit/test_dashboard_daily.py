"""Biểu đồ 'Diễn biến hồ sơ theo ngày' (dashboard) phải gộp CẢ Auto Fill + Handfree cho MỌI khoảng
thời gian — kể cả 'Tất cả' (range dài). Trước đây handfree daily bị cắt khi range > 92 ngày → cột
theo ngày thiếu handfree (vd hôm nay hiện 9 thay vì 49) trong khi KPI tổng vẫn cộng cả hai."""
from datetime import datetime, timedelta

from app.dashboard import combine


def _units():
    return [{"unitId": "u1", "tinh": "Bắc Ninh", "xa": "Phường Bắc Giang"}]


async def _fake_daily_stats(_accounts, _body):
    return {"units": [{"dailyCounts": [{"date": "2026-09-09", "count": 40}]}]}


async def test_handfree_daily_merged_even_on_long_range(monkeypatch):
    """Range > 92 ngày (Tất cả) vẫn phải lấy handfree daily, không trả rỗng."""
    monkeypatch.setattr(combine, "fetch_handfree_daily_stats", _fake_daily_stats)
    date_from = datetime(2025, 1, 1, tzinfo=combine.VIETNAM_TZ)
    date_to = datetime(2026, 9, 9, tzinfo=combine.VIETNAM_TZ)  # ~617 ngày > 92
    assert (date_to - date_from).days > 92
    result = await combine.fetch_handfree_daily(_units(), date_from, date_to)
    assert result == {"2026-09-09": 40}, "range dài vẫn phải gộp handfree daily (bỏ cap 92 ngày)"


async def test_handfree_daily_merged_on_short_range_unchanged(monkeypatch):
    """Range ngắn (Hôm nay) vẫn hoạt động như cũ."""
    monkeypatch.setattr(combine, "fetch_handfree_daily_stats", _fake_daily_stats)
    date_from = datetime(2026, 9, 9, tzinfo=combine.VIETNAM_TZ)
    date_to = datetime(2026, 9, 9, 23, 59, tzinfo=combine.VIETNAM_TZ)
    result = await combine.fetch_handfree_daily(_units(), date_from, date_to)
    assert result == {"2026-09-09": 40}


def test_merge_daily_sums_autofill_and_handfree_same_day():
    """byDay của 1 ngày = Auto Fill + Handfree (đúng như KPI tổng đếm cả hai nguồn)."""
    af_daily = [{"date": "2026-09-09", "count": 9}]      # No handfree (Auto Fill)
    hf_daily = {"2026-09-09": 40}                          # Handfree
    merged = combine.merge_daily(af_daily, hf_daily)
    assert merged == [{"date": "2026-09-09", "count": 49}], "hôm nay phải là 9 + 40 = 49"
