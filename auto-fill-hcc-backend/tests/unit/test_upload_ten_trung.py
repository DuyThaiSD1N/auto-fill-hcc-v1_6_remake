"""Tệp cùng tên trong một phiên tải ảnh được đổi thành image-2.jpg…

Planner đính kèm tra kết quả OCR THEO TÊN tệp: iPhone đặt mọi ảnh chụp từ camera là image.jpg, hai
giấy khác nhau mà cùng tên thì nhận chung chữ OCR của tệp sau → phân loại sai giấy.
"""
import io
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.channels.handfree.documents import router as handfree_router
from app.upload_session import router as upload_router
from app.upload_session import store


def test_dat_ten_khong_trung():
    assert store.unique_file_name("image.jpg", set()) == "image.jpg"
    assert store.unique_file_name("image.jpg", {"image.jpg"}) == "image-2.jpg"
    assert store.unique_file_name("image.jpg", {"image.jpg", "image-2.jpg"}) == "image-3.jpg"
    assert store.unique_file_name("anh", {"anh"}) == "anh-2"
    assert store.unique_file_name(".jpg", {".jpg"}) == ".jpg-2"
    assert store.unique_file_name("a.b.pdf", {"a.b.pdf"}) == "a.b-2.pdf"


@pytest.fixture(autouse=True)
def _secure_capability_secret(monkeypatch):
    monkeypatch.setattr(upload_router.settings, "upload_capability_secret", "ab" * 32)


def _uploads(*names):
    return [UploadFile(filename=n, file=io.BytesIO(f"noi-dung-{i}".encode())) for i, n in enumerate(names)]


async def test_auto_fill_doi_ten_trung_trong_lo_va_voi_tep_da_co(monkeypatch, tmp_path):
    sess = {"_id": "HS-TRUNG", "experience": "autofill", "owner_user_id": "u1",
            "files": [{"fid": "f0.jpg", "name": "image.jpg", "size": 1}]}
    monkeypatch.setattr(upload_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(store, "append_files_with_limit",
                        AsyncMock(side_effect=lambda _sid, metas, _limit: {**sess, "files": sess["files"] + metas}))
    monkeypatch.setattr(upload_router, "broadcast", AsyncMock())
    monkeypatch.setattr(upload_router.audit, "log_uploaded", AsyncMock())
    monkeypatch.setattr(store, "extend_autofill_expiry", AsyncMock())

    result = await upload_router.upload_files(
        sess["_id"], _uploads("image.jpg", "image.jpg", "IMG_0002.jpg"), "", sess)

    assert [m["name"] for m in result["accepted"]] == ["image-2.jpg", "image-3.jpg", "IMG_0002.jpg"]


async def test_handfree_doi_ten_truoc_khi_phan_loai(monkeypatch, tmp_path):
    sess = {"_id": "HS-HF-TRUNG", "procedure_key": "test", "complete": False,
            "required_docs": [{"key": "khac", "name": "Khác", "sides": 1, "optional": True}],
            "files": [{"fid": "f0.jpg", "name": "image.jpg", "size": 1, "doc_key": "khac"}]}
    seen = {}

    async def classify(payloads, *_a, **_k):
        seen["names"] = [p["name"] for p in payloads]
        return [{"doc_key": "khac", "side": None, "note": "ok"} for _ in payloads]

    monkeypatch.setattr(handfree_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(handfree_router.classify, "classify_files", classify)
    monkeypatch.setattr(store, "append_files_with_limit",
                        AsyncMock(side_effect=lambda _s, metas, _m: {**sess, "files": sess["files"] + metas}))
    monkeypatch.setattr(handfree_router, "broadcast", AsyncMock())
    monkeypatch.setattr(handfree_router.audit, "log_uploaded", AsyncMock())

    result = await handfree_router.upload_files(sess["_id"], _uploads("image.jpg", "image.jpg"), "", sess)

    assert seen["names"] == ["image-2.jpg", "image-3.jpg"]
    assert [m["name"] for m in result["accepted"]] == ["image-2.jpg", "image-3.jpg"]


async def test_lap_ke_hoach_dinh_kem_doi_ten_trung_truoc_khi_vao_planner(monkeypatch):
    from app.attachments import router as attach_router
    from app.attachments.schemas import AttachmentPlanReq

    body = AttachmentPlanReq(procedure="chung-thuc-ban-sao", files=[
        {"name": "image.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA==", "role": "doc"},
        {"name": "image.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AQ==", "role": "doc"},
        {"name": "giay.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA==", "role": "doc"},
    ])
    monkeypatch.setattr(attach_router, "get_procedure", lambda _k: {"mode": "attach"})
    await attach_router._prepare_attach(body, {"id": "u1"})
    assert [f.name for f in body.files] == ["image.jpg", "image-2.jpg", "giay.pdf"]


def test_ten_doi_van_la_ten_chung_chung_cho_extension():
    """Extension (isGenericDocumentNameForPlan) chỉ thay tên tài liệu bằng loại giấy khi tên là dạng
    chung chung — "image-2" còn khớp, "image (2)" thì không."""
    import re
    generic = re.compile(r"^(\d+|img|image|photo|scan|screenshot|zalo|z\d+|file|document|tai lieu)([\s_:-]*\d*)?$")
    assert generic.match(store.unique_file_name("image.jpg", {"image.jpg"}).rsplit(".", 1)[0])
