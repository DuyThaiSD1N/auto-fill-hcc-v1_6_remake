"""Consent v1.3: entry tự đủ nghĩa (statements/location/acc), lượt đồng ý sinh PDF
biên bản ra {storage_dir}/consent/, endpoint admin tải PDF."""
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.channels.handfree.chat import consent
from app.config import settings
from app.consents.router import router as consents_router
from app.core.deps import require_admin

CONV = {
    "_id": "conv-1",
    "procedure_key": "khai-sinh",
    "location": {"province": "Tỉnh Lai Châu", "ward": "Phường Tân Phong"},
    "auth_user": {"id": "u1", "username": "hcctanphong", "name": "Phường Tân Phong"},
}
PROC = {"label": "Đăng ký khai sinh", "requiredDocs": [{"name": "CCCD"}, {"name": "Giấy chứng sinh"}]}


def test_entry_tu_du_nghia():
    e = consent.build_entry(CONV, PROC, accepted=True, checks=[True, True])
    assert e["version"] == "1.3"
    assert len(e["statements"]) == 2 and "đồng ý" in e["statements"][0].lower()
    assert e["location"]["ward"] == "Phường Tân Phong"
    assert e["auth_username"] == "hcctanphong"
    assert "chia sẻ dữ liệu đã trích xuất lên Cổng Dịch vụ công" in e["scope"]
    # Chưa nhận ra tài khoản VNeID trên cổng → không có chủ thể, biên bản gắn theo mã phiên.
    assert e["principal_cccd"] is None and e["principal_name"] is None


def test_entry_chu_the_vneid_tu_cong():
    conv = dict(CONV, portal_principal={"cccd": "012345678901", "name": "Nguyễn Văn A"})
    e = consent.build_entry(conv, PROC, accepted=True, checks=[True, True])
    assert e["principal_cccd"] == "012345678901" and e["principal_name"] == "Nguyễn Văn A"


async def test_flow_luu_principal_tu_page_status():
    from app.channels.handfree.chat import flow
    from app.channels.handfree.chat.intents import Intent

    conv = {"_id": "c1", "state": "greet", "history": []}
    r = await flow.handle_turn(conv, Intent("event", "page_status",
                                            {"loggedIn": True,
                                             "principal": {"cccd": "012345678901", "name": "Nguyễn Văn A"}}))
    assert conv["portal_principal"]["cccd"] == "012345678901"
    assert not r.display_md  # ngoài guide_login/attaching → bot im lặng như cũ


def test_pdf_hien_chu_the_vneid(tmp_path, monkeypatch):
    from app.channels.handfree.chat.consent_pdf import build_consent_pdf

    conv = dict(CONV, portal_principal={"cccd": "012345678901", "name": "Nguyễn Văn A"})
    e = consent.build_entry(conv, PROC, accepted=True, checks=[True, True])
    text = fitz.open(stream=build_consent_pdf(e), filetype="pdf")[0].get_text()
    assert "Chủ thể dữ liệu (VNeID)" in text and "012345678901" in text and "Nguyễn Văn A" in text


def _mock_db():
    db = MagicMock()
    db.consent_logs.insert_one = AsyncMock()
    return db


async def test_persist_dong_y_sinh_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    entry = consent.build_entry(CONV, PROC, accepted=True, checks=[True, True])
    db = _mock_db()
    with patch.object(consent, "get_db", return_value=db):
        await consent.persist(entry)
    doc = db.consent_logs.insert_one.call_args.args[0]
    assert doc["pdf_path"] == f"consent/{entry['_id']}.pdf"
    pdf_file = tmp_path / "consent" / f"{entry['_id']}.pdf"
    assert pdf_file.is_file()
    text = fitz.open(pdf_file)[0].get_text()
    assert entry["_id"] in text and "ĐỒNG Ý" in text and "Phường Tân Phong" in text
    assert "91/2025/QH15" in text
    # Không nhận ra VNeID → biên bản ghi trung thực là gắn theo mã phiên.
    assert "Không xác định được từ cổng" in text


async def test_persist_tu_choi_khong_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    entry = consent.build_entry(CONV, PROC, accepted=False, method="verbal")
    db = _mock_db()
    with patch.object(consent, "get_db", return_value=db):
        await consent.persist(entry)
    doc = db.consent_logs.insert_one.call_args.args[0]
    assert "pdf_path" not in doc
    assert not (tmp_path / "consent").exists()


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_):
        return self

    def skip(self, *_):
        return self

    def limit(self, *_):
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def test_endpoint_list_consents():
    from datetime import datetime, timezone

    from app.consents import router as consents_mod

    docs = [{
        "_id": "TLND-AB12", "at": datetime(2026, 8, 7, tzinfo=timezone.utc),
        "at_display": "10:00 ngày 07/08/2026", "procedure_key": "khai-sinh",
        "procedure_label": "Đăng ký khai sinh", "accepted": True, "method": "chip",
        "version": "1.3", "location": {"province": "Tỉnh Lai Châu", "ward": "Phường Tân Phong"},
        "auth_username": "hcctanphong", "conversation_id": "c1", "pdf_path": "consent/TLND-AB12.pdf",
    }, {
        "_id": "TLND-OLD1", "at": None, "accepted": False,  # log v1.0 thiếu field mới
    }]
    db = MagicMock()
    db.consent_logs.count_documents = AsyncMock(return_value=2)
    db.consent_logs.find = MagicMock(return_value=_FakeCursor(docs))
    app = FastAPI()
    app.include_router(consents_router)
    app.dependency_overrides[require_admin] = lambda: {"id": "a", "role": "admin"}
    with patch.object(consents_mod, "get_db", return_value=db):
        r = TestClient(app).get("/api/v1/consents?accepted=true")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and len(body["items"]) == 2
    assert body["items"][0]["has_pdf"] is True and body["items"][0]["auth_username"] == "hcctanphong"
    assert body["items"][1]["has_pdf"] is False and body["items"][1]["location"] == {}
    assert db.consent_logs.find.call_args.args[0] == {"accepted": True}


def test_endpoint_admin_tai_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    (tmp_path / "consent").mkdir()
    (tmp_path / "consent" / "TLND-AB12.pdf").write_bytes(b"%PDF-1.4 fake")
    app = FastAPI()
    app.include_router(consents_router)
    app.dependency_overrides[require_admin] = lambda: {"id": "a", "role": "admin"}
    c = TestClient(app)
    ok = c.get("/api/v1/consents/TLND-AB12/pdf")
    assert ok.status_code == 200 and ok.headers["content-type"] == "application/pdf"
    assert c.get("/api/v1/consents/TLND-XXXX/pdf").status_code == 404
    assert c.get("/api/v1/consents/..no.hack../pdf").status_code == 404
