from types import SimpleNamespace

import pytest

from scripts import cleanup_ocr_cache


class _Cursor:
    def __init__(self, collection):
        self.collection = collection

    def sort(self, *_args):
        return self

    def limit(self, _value):
        return self

    async def to_list(self, *, length):
        assert length > 0
        if not self.collection.batches:
            return []
        return self.collection.batches.pop(0)


class _IndexCursor:
    def __init__(self, indexes):
        self.indexes = indexes

    async def to_list(self, *, length):
        assert length is None
        return self.indexes


class _Collection:
    name = "ocr_cache"

    def __init__(self, counts, batches=None, indexes=None):
        self.counts = list(counts)
        self.batches = list(batches or [])
        self.delete_queries = []
        self.indexes = indexes if indexes is not None else [
            {
                "name": "created_at_1",
                "key": {"created_at": 1},
                "expireAfterSeconds": 7 * 86400,
            }
        ]
        self.created_indexes = []

    async def count_documents(self, _query):
        return self.counts.pop(0)

    def find(self, *_args):
        return _Cursor(self)

    async def delete_many(self, query):
        self.delete_queries.append(query)
        return SimpleNamespace(deleted_count=len(query["_id"]["$in"]))

    def list_indexes(self):
        return _IndexCursor(self.indexes)

    async def create_index(self, key, **options):
        self.created_indexes.append((key, options))


def _patch_db(monkeypatch, collection):
    class _Db(SimpleNamespace):
        async def command(self, command):
            self.commands.append(command)

    db = _Db(name="autofill_hcc", ocr_cache=collection, commands=[])
    monkeypatch.setattr(cleanup_ocr_cache, "connect", lambda: None)
    monkeypatch.setattr(cleanup_ocr_cache, "get_db", lambda: db)
    return db


def test_parse_args_is_safe_by_default():
    args = cleanup_ocr_cache._parse_args([])
    assert args.older_than_hours == 12
    assert args.batch_size == 1000
    assert args.pause_ms == 100
    assert args.apply is False


@pytest.mark.asyncio
async def test_dry_run_only_counts(monkeypatch):
    collection = _Collection(counts=[25, 2])
    db = _patch_db(monkeypatch, collection)

    code = await cleanup_ocr_cache.cleanup(
        older_than_hours=12, batch_size=1000, pause_ms=0, apply=False,
    )

    assert code == 0
    assert collection.delete_queries == []
    assert db.commands == []


@pytest.mark.asyncio
async def test_apply_deletes_in_batches_and_keeps_cutoff_guard(monkeypatch):
    collection = _Collection(
        counts=[3, 0, 0],
        batches=[[{"_id": "a"}, {"_id": "b"}], [{"_id": "c"}]],
    )
    db = _patch_db(monkeypatch, collection)

    code = await cleanup_ocr_cache.cleanup(
        older_than_hours=12, batch_size=2, pause_ms=0, apply=True,
    )

    assert code == 0
    assert [query["_id"]["$in"] for query in collection.delete_queries] == [["a", "b"], ["c"]]
    assert all("created_at" in query for query in collection.delete_queries)
    assert db.commands == [{
        "collMod": "ocr_cache",
        "index": {"name": "created_at_1", "expireAfterSeconds": 12 * 3600},
    }]


@pytest.mark.asyncio
async def test_apply_creates_ttl_index_when_missing(monkeypatch):
    collection = _Collection(
        counts=[0, 0, 0],
        indexes=[{"name": "_id_", "key": {"_id": 1}}],
    )
    db = _patch_db(monkeypatch, collection)

    code = await cleanup_ocr_cache.cleanup(
        older_than_hours=12, batch_size=1000, pause_ms=0, apply=True,
    )

    assert code == 0
    assert collection.created_indexes == [
        ("created_at", {"expireAfterSeconds": 12 * 3600})
    ]
    assert db.commands == []


@pytest.mark.asyncio
async def test_apply_does_not_change_ttl_while_expired_cache_remains(monkeypatch):
    collection = _Collection(
        counts=[1, 0, 1],
        batches=[],
    )
    db = _patch_db(monkeypatch, collection)

    code = await cleanup_ocr_cache.cleanup(
        older_than_hours=12, batch_size=1000, pause_ms=0, apply=True,
    )

    assert code == 2
    assert db.commands == []
    assert collection.created_indexes == []
