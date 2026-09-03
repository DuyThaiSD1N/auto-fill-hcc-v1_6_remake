from datetime import datetime, timezone

import pytest

from app.traces import repo


class _Cursor:
    def __init__(self, docs):
        self.docs = docs
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.docs):
            raise StopAsyncIteration
        doc = self.docs[self.index]
        self.index += 1
        return doc


def _trace(request_id: str, name: str, created_at: datetime) -> dict:
    return {
        "request_id": request_id,
        "user_id": "u1",
        "name": "Phường 1",
        "procedure": "khai-tu",
        "procedure_label": "Khai tử",
        "attachments": [{"name": name}],
        "created_at": created_at,
    }


def test_stem_rule_starts_exactly_at_vietnam_midnight():
    assert not repo._uses_stem_rule(datetime(2026, 8, 24, 16, 59, 59))
    assert repo._uses_stem_rule(datetime(2026, 8, 24, 17, 0, 0))
    assert repo._uses_stem_rule(datetime(2026, 8, 24, 17, 0, tzinfo=timezone.utc))


def test_retry_sets_are_deduplicated_but_empty_requests_stay_separate():
    same = frozenset({"cccd"})

    assert repo._count_distinct_dossiers([same, same, same]) == 1
    assert repo._count_distinct_dossiers([frozenset(), frozenset()]) == 2


@pytest.mark.asyncio
async def test_stats_preserves_old_names_then_uses_stems_without_ocr(monkeypatch):
    docs = [
        # Trước mốc: tên đầy đủ khác đuôi vẫn là hai hồ sơ như rule cũ.
        _trace("old-jpg", "CCCD.jpg", datetime(2026, 8, 24, 15, tzinfo=timezone.utc)),
        _trace("old-pdf", "CCCD.pdf", datetime(2026, 8, 24, 16, tzinfo=timezone.utc)),
        # Từ mốc: bỏ đuôi nên hai lượt này là một hồ sơ.
        _trace("new-jpg", "Tờ khai.jpg", datetime(2026, 8, 24, 17, tzinfo=timezone.utc)),
        _trace("new-pdf", "Tờ khai.pdf", datetime(2026, 8, 24, 18, tzinfo=timezone.utc)),
    ]
    captured: dict = {}

    class _Traces:
        def find(self, query, projection):
            captured["projection"] = projection
            return _Cursor(docs)

    class _Database:
        traces = _Traces()

    monkeypatch.setattr(repo, "get_db", lambda: _Database())

    result = await repo._stats_for_query({})

    assert "ocr_text" not in captured["projection"]
    assert result["totalDossiers"] == 3
    assert result["totalRequests"] == 4
