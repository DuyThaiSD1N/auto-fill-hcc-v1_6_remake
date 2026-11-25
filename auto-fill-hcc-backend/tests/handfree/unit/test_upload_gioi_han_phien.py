"""Chặn client gửi dồn hàng trăm tệp vào MỘT phiên tải handfree (mỗi lượt là một lần OCR + LLM phân loại)."""
import asyncio

import pytest
from fastapi import HTTPException

from app.channels.handfree.documents import router as documents_router


@pytest.fixture(autouse=True)
def _sach(monkeypatch):
    monkeypatch.setattr(documents_router, "_session_slots", {})


async def test_toi_da_3_luot_chay_cung_luc_hang_cho_day_thi_429_khong_phan_loai(monkeypatch):
    monkeypatch.setattr(documents_router, "_SESSION_MAX_PENDING", 5)
    dang_chay, dinh, goi = 0, 0, 0
    nha = asyncio.Event()

    async def fake_upload(sid, files, doc_key, sess):
        nonlocal dang_chay, dinh, goi
        goi += 1
        dang_chay += 1
        dinh = max(dinh, dang_chay)
        await nha.wait()
        dang_chay -= 1
        return {"accepted": []}

    async def fake_get(sid):
        return {"files": [], "complete": False}

    monkeypatch.setattr(documents_router, "_upload_files", fake_upload)
    monkeypatch.setattr(documents_router.store, "get", fake_get)
    tasks = [asyncio.create_task(documents_router._upload_files_limited("HS-1", [], "", {})) for _ in range(5)]
    await asyncio.sleep(0)
    with pytest.raises(HTTPException) as err:
        await documents_router._upload_files_limited("HS-1", [], "", {})
    assert err.value.status_code == 429
    nha.set()
    await asyncio.gather(*tasks)
    assert dinh == 3, "không quá 3 lượt OCR cùng lúc cho một phiên"
    assert goi == 5, "lượt bị 429 không chạy phân loại"
    assert documents_router._session_slots == {}, "xong hết thì dọn chỗ của phiên"


async def test_luot_phai_cho_doc_lai_phien_moi_nhat(monkeypatch):
    nha = asyncio.Event()
    thay = []

    async def fake_upload(sid, files, doc_key, sess):
        thay.append(sess.get("complete"))
        await nha.wait()
        return {}

    async def fake_get(sid):
        return {"files": [], "complete": True}  # cán bộ đã chốt phiên trong lúc lượt này chờ

    monkeypatch.setattr(documents_router, "_upload_files", fake_upload)
    monkeypatch.setattr(documents_router.store, "get", fake_get)
    snap = {"files": [], "complete": False}
    tasks = [asyncio.create_task(documents_router._upload_files_limited("HS-2", [], "", snap)) for _ in range(4)]
    await asyncio.sleep(0)
    nha.set()
    await asyncio.gather(*tasks)
    assert thay == [False, False, False, True], "lượt không chờ dùng ảnh chụp; lượt xếp hàng đọc lại phiên"
