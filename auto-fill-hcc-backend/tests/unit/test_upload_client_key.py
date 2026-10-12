"""Điện thoại gửi lại cùng tệp (4G làm lỡ câu trả lời dù máy chủ đã lưu) → không lưu bản trùng.

Mỗi tệp mang `client_key` do điện thoại sinh một lần và giữ qua mọi lần gửi lại.
"""
import io
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.upload_session import router as upload_router
from app.upload_session import store


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(upload_router.settings, "upload_capability_secret", "ab" * 32)
    monkeypatch.setattr(upload_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(upload_router, "broadcast", AsyncMock())
    monkeypatch.setattr(upload_router.audit, "log_uploaded", AsyncMock())
    monkeypatch.setattr(store, "extend_autofill_expiry", AsyncMock())


def _sess(files=None):
    return {"_id": "HS-KEY", "experience": "autofill", "owner_user_id": "u1", "files": files or []}


def _up(name="a.pdf"):
    return [UploadFile(filename=name, file=io.BytesIO(b"%PDF-noi-dung"))]


async def test_lan_dau_luu_kem_ma_va_kiem_trong_cung_thao_tac_ghi(monkeypatch):
    sess = _sess()
    append = AsyncMock(side_effect=lambda _sid, metas, _limit, **_k: {**sess, "files": metas})
    monkeypatch.setattr(store, "append_files_with_limit", append)

    result = await upload_router.upload_files("HS-KEY", _up(), "", sess, client_key="k-1")

    assert result["accepted"][0]["client_key"] == "k-1"
    assert append.await_args.kwargs == {"client_key": "k-1"}
    assert "duplicate" not in result


async def test_gui_lai_ma_da_co_tra_tep_cu_khong_luu_them(monkeypatch):
    sess = _sess([{"fid": "f1.pdf", "name": "a.pdf", "type": "application/pdf", "size": 12, "client_key": "k-1"}])
    append = AsyncMock()
    monkeypatch.setattr(store, "append_files_with_limit", append)

    result = await upload_router.upload_files("HS-KEY", _up(), "", sess, client_key="k-1")

    assert result == {"accepted": [{"fid": "f1.pdf", "name": "a.pdf", "type": "application/pdf", "size": 12}],
                      "received": 1, "duplicate": True}
    append.assert_not_awaited()
    upload_router.broadcast.assert_not_awaited()


async def test_hai_lan_gui_song_song_lan_sau_bo_bytes_cua_minh(monkeypatch, tmp_path):
    winner = {"fid": "f-truoc.pdf", "name": "a.pdf", "type": "application/pdf", "size": 12, "client_key": "k-2"}
    monkeypatch.setattr(store, "append_files_with_limit", AsyncMock(return_value=None))
    monkeypatch.setattr(store, "get", AsyncMock(return_value=_sess([winner])))

    result = await upload_router.upload_files("HS-KEY", _up(), "", _sess(), client_key="k-2")

    assert result["duplicate"] is True and result["accepted"][0]["fid"] == "f-truoc.pdf"
    saved = list((tmp_path / "upload_sessions" / "HS-KEY").glob("*")) if (tmp_path / "upload_sessions").exists() else []
    assert not [p for p in saved if p.name != "f-truoc.pdf"], "bytes của lượt trùng phải bị dọn"


async def test_khong_co_ma_van_chay_nhu_cu(monkeypatch):
    sess = _sess()
    append = AsyncMock(side_effect=lambda _sid, metas, _limit, **_k: {**sess, "files": metas})
    monkeypatch.setattr(store, "append_files_with_limit", append)

    result = await upload_router.upload_files("HS-KEY", _up(), "", sess, client_key="")

    assert "client_key" not in result["accepted"][0]
    assert append.await_args.kwargs == {}, "không mã thì gọi y như cũ"


async def test_dieu_kien_chong_trung_nam_trong_lenh_ghi(monkeypatch):
    seen = []

    class Coll:
        async def find_one_and_update(self, query, update, **_k):
            seen.append(query)
            return {"_id": "HS-KEY"}

    monkeypatch.setattr(store, "get_db", lambda: type("Db", (), {"upload_sessions": Coll()})())
    await store.append_files_with_limit("HS-KEY", [{"size": 1}], 10, client_key="k-9")
    await store.append_files_with_limit("HS-KEY", [{"size": 1}], 10)
    assert seen[0]["files.client_key"] == {"$ne": "k-9"}
    assert "files.client_key" not in seen[1]
