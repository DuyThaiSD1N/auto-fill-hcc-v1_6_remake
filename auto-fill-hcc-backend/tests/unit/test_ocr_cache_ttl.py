from datetime import datetime, timedelta, timezone

import pytest

from app.services import ocr_cache


class _Cursor:
    def __init__(self, documents):
        self.documents = iter(documents)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.documents)
        except StopIteration as error:
            raise StopAsyncIteration from error


class _Collection:
    def __init__(self):
        self.query = None
        self.projection = None

    def find(self, query, projection):
        self.query = query
        self.projection = projection
        return _Cursor([{"_id": "v2-tiengnoi:key", "text": "OCR", "provider": "tiengnoi"}])


@pytest.mark.asyncio
async def test_get_many_rejects_documents_older_than_configured_ttl(monkeypatch):
    collection = _Collection()
    db = type("Db", (), {"ocr_cache": collection})()
    monkeypatch.setattr(ocr_cache, "get_db", lambda: db)
    monkeypatch.setattr(ocr_cache.settings, "ocr_cache_enabled", True)
    monkeypatch.setattr(ocr_cache.settings, "ocr_cache_ttl_hours", 12)

    before = datetime.now(timezone.utc) - timedelta(hours=12)
    result = await ocr_cache.get_many(["v2-tiengnoi:key"])
    after = datetime.now(timezone.utc) - timedelta(hours=12)

    # max_tokens=None: bản ghi từ bản cũ chưa ghi trần token — người gọi tự quyết có dùng được không.
    assert result == {
        "v2-tiengnoi:key": {"text": "OCR", "provider": "tiengnoi", "max_tokens": None},
    }
    assert collection.query["_id"] == {"$in": ["v2-tiengnoi:key"]}
    assert before <= collection.query["created_at"]["$gte"] <= after
    assert collection.projection == {"text": 1, "provider": 1, "max_tokens": 1}
