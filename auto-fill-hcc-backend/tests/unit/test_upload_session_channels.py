from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from starlette.responses import Response

from app.channels.handfree.documents import router as handfree_router
from app.upload_session import router as upload_router
from app.upload_session import store, streaming
from app.upload_session.access import upload_session_experience


@pytest.fixture(autouse=True)
def _secure_capability_secret(monkeypatch):
    monkeypatch.setattr(upload_router.settings, "upload_capability_secret", "ab" * 32)


class _TrackingBytesIO(BytesIO):
    def __init__(self, value: bytes):
        super().__init__(value)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


def test_session_experience_supports_documents_created_before_channel_field():
    assert upload_session_experience({"user_id": "u1", "files": []}) == "autofill"
    assert upload_session_experience({
        "conversation_id": "c1",
        "procedure_key": "ket-hon",
        "required_docs": [],
    }) == "handfree"


@pytest.mark.asyncio
async def test_legacy_get_returns_handfree_contract_and_disables_cache(monkeypatch):
    monkeypatch.setattr(upload_router.settings, "handfree_enabled", True)
    sess = {
        "_id": "HS-LEGACY",
        "conversation_id": "c1",
        "procedure_key": "ket-hon",
        "required_docs": [{"key": "cccd", "name": "CCCD", "sides": 1}],
        "files": [],
        "complete": False,
    }
    response = Response()

    result = await upload_router.get_session(sess["_id"], response, sess)

    assert result["procedure_key"] == "ket-hon"
    assert result["progress"]["files_count"] == 0
    assert response.headers["Cache-Control"] == "no-store, max-age=0"


@pytest.mark.asyncio
async def test_legacy_upload_dispatches_to_same_handfree_implementation(monkeypatch):
    monkeypatch.setattr(upload_router.settings, "handfree_enabled", True)
    sess = {
        "_id": "HS-HANDFREE",
        "experience": "handfree",
        "procedure_key": "ket-hon",
        "required_docs": [],
        "files": [],
    }
    delegated = AsyncMock(return_value={"accepted": [], "progress": {"files_count": 0}})
    monkeypatch.setattr(handfree_router, "upload_files", delegated)
    files = [UploadFile(filename="a.pdf", file=BytesIO(b"a"))]

    result = await upload_router.upload_files(sess["_id"], files, "cccd", sess)

    assert result["progress"]["files_count"] == 0
    delegated.assert_awaited_once_with(sess["_id"], files, "cccd", sess)


@pytest.mark.asyncio
async def test_autofill_upload_is_streamed_and_committed_atomically(monkeypatch, tmp_path):
    content = b"a" * (streaming.UPLOAD_CHUNK_BYTES + 17)
    source = _TrackingBytesIO(content)
    sess = {
        "_id": "HS-AUTOFILL",
        "experience": "autofill",
        "owner_user_id": "u1",
        "files": [],
    }
    monkeypatch.setattr(upload_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(
        store,
        "append_files_with_limit",
        AsyncMock(side_effect=lambda _sid, metas, _limit: {**sess, "files": metas}),
    )
    monkeypatch.setattr(upload_router, "broadcast", AsyncMock())

    result = await upload_router.upload_files(
        sess["_id"],
        [UploadFile(filename="hoso.pdf", file=source)],
        "",
        sess,
    )

    fid = result["accepted"][0]["fid"]
    assert store.read_file_bytes(sess["_id"], fid) == content
    assert source.read_sizes == [streaming.UPLOAD_CHUNK_BYTES] * 3
    session_dir = tmp_path / "upload_sessions" / sess["_id"]
    assert not any(path.name.startswith(".upload-") for path in session_dir.iterdir())
