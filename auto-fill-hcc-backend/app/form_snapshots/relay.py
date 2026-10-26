from __future__ import annotations

import logging
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.archive.client import VaultClient
from app.archive.config import archive_settings
from app.db.mongo import get_db
from app.form_snapshots.schemas import FormSnapshotReq

logger = logging.getLogger("app.form_snapshots")

_client: VaultClient | None = None


def _vault() -> VaultClient:
    global _client
    if _client is None:
        _client = VaultClient()
    return _client


async def owned_request(request_id: str, user_id: str) -> dict | None:
    return await get_db().process_requests.find_one(
        {"request_id": request_id, "user_id": user_id},
        {"experience": 1, "procedure": 1, "options.conversation_id": 1},
    )


def build_bundle(body: FormSnapshotReq, user: dict, preq: dict) -> dict:
    at = datetime.fromtimestamp(body.at / 1000, tz=timezone.utc)
    return {
        "v": 1, "type": "form_snapshot", "id": body.snapshotId, "request_id": body.requestId,
        "created_at": at.isoformat(),
        "experience": preq.get("experience"),
        "procedure": preq.get("procedure"),
        "conversation_id": (preq.get("options") or {}).get("conversation_id"),
        "unit": {"user_id": str(user.get("id") or ""), "username": user.get("username"),
                 "name": user.get("name")},
        "snapshot": {"kind": body.kind, "trigger": body.trigger, "host": body.host, "path": body.path,
                     "at": body.at, "extVersion": body.extVersion,
                     "fields": [f.model_dump() for f in body.fields]},
        "files": [],
    }


async def relay(bundle: dict) -> None:
    if not archive_settings.enabled:
        return
    try:
        await _vault().send(bundle, {})
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("[form_snapshot] gửi kho %s lỗi, chờ gửi lại: %s %s",
                       bundle.get("id"), type(exc).__name__, exc)
    try:
        await get_db().form_snapshots.insert_one(
            {"_id": bundle["id"], "bundle": bundle, "created_at": datetime.now(timezone.utc)})
    except DuplicateKeyError:
        pass
