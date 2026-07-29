from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


def connect() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_dsn)


def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        connect()
    assert _client is not None
    return _client[settings.mongo_db]
