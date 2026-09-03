from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.core.errors import AppError
from app.channels.handfree.documents import router
from app.channels.handfree.chat import store as conversation_store
from app.upload_session import access, store, streaming
from app.channels.handfree.documents.mobile_page import render_mobile_page


class _TrackingBytesIO(BytesIO):
    def __init__(self, value: bytes):
        super().__init__(value)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


@pytest.fixture(autouse=True)
def _secure_capability_secret(monkeypatch):
    # Test không phụ thuộc secret máy chạy; production lấy từ UPLOAD_CAPABILITY_SECRET.
    monkeypatch.setattr(access.settings, "upload_capability_secret", "ab" * 32)


def _request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
        "scheme": "http",
    })


@pytest.mark.asyncio
async def test_mobile_capability_chi_mo_dung_session(monkeypatch):
    sid = "HS-0011223344556677"
    sess = {"_id": sid, "files": []}
    monkeypatch.setattr(store, "get", AsyncMock(return_value=sess))
    token = access.create_upload_capability(sid)

    granted = await access.require_upload_session_access(
        sid,
        _request([(b"x-upload-token", token.encode())]),
        None,
    )
    assert granted is sess
    assert access.verify_upload_capability("HS-KHAC", token) is False


@pytest.mark.asyncio
async def test_session_khong_token_bi_401_truoc_khi_do_sid(monkeypatch):
    get_session = AsyncMock()
    monkeypatch.setattr(store, "get", get_session)

    with pytest.raises(AppError) as exc:
        await access.require_upload_session_access("HS-UNKNOWN", _request(), None)

    assert exc.value.code == 401
    get_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_bearer_khong_duoc_doc_session_tai_khoan_khac(monkeypatch):
    sid = "HS-0011223344556677"
    monkeypatch.setattr(store, "get", AsyncMock(return_value={
        "_id": sid,
        "owner_user_id": "owner-user",
    }))
    monkeypatch.setattr(access, "require_auth", AsyncMock(return_value={"id": "other-user"}))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")

    with pytest.raises(AppError) as exc:
        await access.require_upload_session_access(sid, _request(), creds)

    assert exc.value.code == 403


def test_mobile_url_giu_capability_trong_fragment(monkeypatch):
    monkeypatch.setattr(router, "mobile_base", lambda: "https://mobile.example")
    url = router.mobile_session_url("HS-0011223344556677")

    assert url.startswith("https://mobile.example/m/handfree/HS-0011223344556677#token=")
    assert "?token=" not in url
    assert len(url.rsplit("#token=", 1)[1]) == 64


def test_mobile_page_gui_capability_qua_header_va_ws_subprotocol():
    html = render_mobile_page("HS-0011223344556677")

    assert 'location.hash.slice(1)' in html
    assert 'headers.set("X-Upload-Token", UPLOAD_TOKEN)' in html
    assert '["tlnd-upload", `tlnd-token.${UPLOAD_TOKEN}`]' in html
    assert "?token=" not in html


def test_session_id_64_bit_va_co_owner():
    sess = store.new_session(
        "conversation-1",
        "ket-hon",
        [{"key": "cccd", "name": "CCCD", "sides": 1}],
        owner_user_id="user-1",
    )

    assert sess["_id"].startswith("HS-")
    assert len(sess["_id"]) == 19  # "HS-" + 16 hex = 64 bit
    assert sess["owner_user_id"] == "user-1"


@pytest.mark.asyncio
async def test_tao_document_session_bi_chan_neu_conversation_thuoc_tai_khoan_khac(monkeypatch):
    monkeypatch.setattr(conversation_store, "get", AsyncMock(return_value={
        "_id": "c-other",
        "auth_user": {"id": "other-user"},
        "procedure_key": "ket-hon",
    }))

    with pytest.raises(AppError) as exc:
        await router.create_session(
            router.CreateSessionRequest(
                conversation_id="c-other",
                procedure_key="ket-hon",
            ),
            {"id": "current-user"},
        )

    assert exc.value.error == "CONVERSATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_quota_tinh_ca_file_da_co_va_dung_truoc_ocr(monkeypatch, tmp_path):
    sess = {
        "_id": "HS-QUOTA",
        "required_docs": [{"key": "khac", "name": "Khác", "sides": 1}],
        "files": [{"fid": "old", "size": 900_000}],
        "complete": False,
    }
    monkeypatch.setattr(router.settings, "max_total_payload_mb", 1)
    monkeypatch.setattr(router.settings, "storage_dir", str(tmp_path))
    classify_files = AsyncMock()
    monkeypatch.setattr(router.classify, "classify_files", classify_files)
    upload = UploadFile(filename="new.pdf", file=BytesIO(b"x" * 200_000))

    with pytest.raises(HTTPException) as exc:
        await router.upload_files("HS-QUOTA", [upload], "", sess)

    assert exc.value.status_code == 413
    classify_files.assert_not_awaited()


@pytest.mark.asyncio
async def test_khong_gioi_han_so_luong_neu_tong_byte_hop_le(monkeypatch, tmp_path):
    sess = {
        "_id": "HS-MANY",
        "procedure_key": "test",
        "required_docs": [{"key": "khac", "name": "Khác", "sides": 1, "optional": True}],
        "files": [],
        "complete": False,
    }
    uploads = [UploadFile(filename=f"{i}.jpg", file=BytesIO(b"x")) for i in range(125)]
    monkeypatch.setattr(router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(router.classify, "classify_files", AsyncMock(return_value=[
        {"doc_key": "khac", "side": None, "note": "ok"} for _ in uploads
    ]))
    monkeypatch.setattr(store, "append_files_with_limit", AsyncMock(side_effect=lambda _s, metas, _m: {
        **sess, "files": metas,
    }))
    monkeypatch.setattr(router, "broadcast", AsyncMock())

    result = await router.upload_files("HS-MANY", uploads, "", sess)

    assert len(result["accepted"]) == 125
    assert result["progress"]["files_count"] == 125


@pytest.mark.asyncio
async def test_upload_ghi_chunk_va_classify_bang_path_khong_tao_data_url(monkeypatch, tmp_path):
    content = b"a" * (streaming.UPLOAD_CHUNK_BYTES * 2 + 123)
    source = _TrackingBytesIO(content)
    upload = UploadFile(filename="hoso.pdf", file=source)
    sess = {
        "_id": "HS-STREAM",
        "procedure_key": "test",
        "required_docs": [{"key": "khac", "name": "Khác", "sides": 1, "optional": True}],
        "files": [],
        "complete": False,
    }
    monkeypatch.setattr(router.settings, "storage_dir", str(tmp_path))

    async def classify_from_path(payloads, *_args, **_kwargs):
        assert len(payloads) == 1
        assert "dataUrl" not in payloads[0]
        assert Path(payloads[0]["path"]).read_bytes() == content
        return [{"doc_key": "khac", "side": None, "note": "ok"}]

    monkeypatch.setattr(router.classify, "classify_files", classify_from_path)
    monkeypatch.setattr(store, "append_files_with_limit", AsyncMock(side_effect=lambda _s, metas, _m: {
        **sess, "files": metas,
    }))
    monkeypatch.setattr(router, "broadcast", AsyncMock())

    result = await router.upload_files("HS-STREAM", [upload], "", sess)

    fid = result["accepted"][0]["fid"]
    assert store.read_file_bytes("HS-STREAM", fid) == content
    assert source.read_sizes == [streaming.UPLOAD_CHUNK_BYTES] * 4
    assert not any(path.name.startswith(".upload-") for path in (tmp_path / "upload_sessions" / "HS-STREAM").iterdir())


@pytest.mark.asyncio
async def test_classify_loi_thi_xoa_file_tam(monkeypatch, tmp_path):
    sess = {
        "_id": "HS-CLASSIFY-FAIL",
        "procedure_key": "test",
        "required_docs": [{"key": "a", "name": "A", "sides": 1}, {"key": "b", "name": "B", "sides": 1}],
        "files": [],
        "complete": False,
    }
    monkeypatch.setattr(router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(
        router.classify,
        "classify_files",
        AsyncMock(side_effect=RuntimeError("classification failed")),
    )

    with pytest.raises(RuntimeError, match="classification failed"):
        await router.upload_files(
            sess["_id"],
            [UploadFile(filename="a.pdf", file=BytesIO(b"abc"))],
            "",
            sess,
        )

    session_dir = tmp_path / "upload_sessions" / sess["_id"]
    assert list(session_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_atomic_append_that_bai_thi_xoa_file_da_commit(monkeypatch, tmp_path):
    sess = {
        "_id": "HS-APPEND-FAIL",
        "procedure_key": "test",
        "required_docs": [{"key": "khac", "name": "Khác", "sides": 1, "optional": True}],
        "files": [],
        "complete": False,
    }
    monkeypatch.setattr(router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(router.classify, "classify_files", AsyncMock(return_value=[
        {"doc_key": "khac", "side": None, "note": "ok"},
    ]))
    monkeypatch.setattr(store, "append_files_with_limit", AsyncMock(return_value=None))
    monkeypatch.setattr(store, "get", AsyncMock(return_value=sess))

    with pytest.raises(HTTPException) as exc:
        await router.upload_files(
            sess["_id"],
            [UploadFile(filename="a.pdf", file=BytesIO(b"abc"))],
            "",
            sess,
        )

    assert exc.value.status_code == 413
    session_dir = tmp_path / "upload_sessions" / sess["_id"]
    assert list(session_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_atomic_append_dat_quota_trong_cung_filter_mongo(monkeypatch):
    captured = {}

    class Collection:
        async def find_one_and_update(self, query, update, **kwargs):
            captured.update(query=query, update=update, kwargs=kwargs)
            return {"_id": "HS-ATOMIC"}

    class Database:
        upload_sessions = Collection()

    monkeypatch.setattr(store, "get_db", lambda: Database())
    await store.append_files_with_limit(
        "HS-ATOMIC",
        [{"fid": "f1", "size": 12}, {"fid": "f2", "size": 30}],
        100,
    )

    assert captured["query"]["complete"] == {"$ne": True}
    add_operands = captured["query"]["$expr"]["$lte"][0]["$add"]
    assert add_operands[1] == 42
    assert captured["query"]["$expr"]["$lte"][1] == 100


@pytest.mark.asyncio
async def test_review_bat_buoc_capability_dung_request(monkeypatch):
    from app.review import access as review_access
    from app.review import router as review_router
    request_id = "req_001122334455"
    monkeypatch.setattr(review_router.store, "load_sources", lambda _rid: {"fields": {}})

    with pytest.raises(AppError) as exc:
        await review_router.get_sources(request_id, "")
    assert exc.value.code == 401

    token = review_access.create_review_capability(request_id)
    assert await review_router.get_sources(request_id, token) == {"fields": {}}
    assert review_access.verify_review_capability("req_khac", token) is False


def test_review_capability_het_han(monkeypatch):
    from app.review import access as review_access

    monkeypatch.setattr(review_access.time, "time", lambda: 1_000)
    token = review_access.create_review_capability("req_expire")
    expired_at = 1_000 + review_access.settings.review_capability_ttl_seconds + 1
    monkeypatch.setattr(review_access.time, "time", lambda: expired_at)
    assert review_access.verify_review_capability("req_expire", token) is False


def test_capability_gia_khong_lam_loi_500_khi_deployment_thieu_secret(monkeypatch):
    from app.review import access as review_access

    monkeypatch.setattr(access.settings, "upload_capability_secret", "")
    monkeypatch.setattr(access.settings, "jwt_refresh_secret", "short")

    assert access.verify_upload_capability("HS-UNKNOWN", "fake") is False
    assert review_access.verify_review_capability(
        "req_unknown",
        "9999999999.fake",
    ) is False
