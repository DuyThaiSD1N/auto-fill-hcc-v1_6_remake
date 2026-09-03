import pytest

from scripts import backfill_autofill_experience as backfill


@pytest.mark.asyncio
async def test_backfill_only_updates_missing_or_null_experience(monkeypatch):
    updates = []

    class Result:
        modified_count = 3

    class Collection:
        async def count_documents(self, query):
            if query == {}:
                return 10
            if query == backfill.LEGACY_FILTER:
                return 3
            return 0

        async def update_many(self, query, update):
            updates.append((query, update))
            return Result()

    class Database:
        def __getitem__(self, _name):
            return Collection()

    monkeypatch.setattr(backfill, "get_db", lambda: Database())
    result = await backfill.execute(apply=True)

    assert result["legacyTotal"] == 12
    assert result["modifiedTotal"] == 12
    assert len(updates) == 4
    assert all(query == backfill.LEGACY_FILTER for query, _update in updates)
    assert all(update == {"$set": {"experience": "autofill"}} for _query, update in updates)
