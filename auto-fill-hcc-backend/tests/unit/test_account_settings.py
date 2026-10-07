"""Cài đặt theo tài khoản (GET/PATCH /api/v1/account/settings).

Điểm sống còn: tài khoản CHƯA từng lưu phải nhận giá trị mặc định = hành vi cũ (đổi tên tệp),
và PATCH chỉ ghi khoá đã khai báo — không để client ghi tuỳ ý vào document user.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.account_settings import service
from app.account_settings.router import router
from app.core.deps import require_auth

USER_ID = "64b000000000000000000001"


class _FakeUsers:
    def __init__(self, doc: dict):
        self.doc = doc
        self.calls: list[dict] = []

    async def find_one_and_update(self, flt, update, projection=None, return_document=None):
        self.calls.append(update)
        for path, value in update["$set"].items():
            head, key = path.split(".", 1)
            self.doc.setdefault(head, {})[key] = value
        return self.doc


@pytest.fixture()
def make_client(monkeypatch):
    def _make(user: dict):
        users = _FakeUsers(dict(user))

        class _Db:
            pass

        db = _Db()
        db.users = users
        monkeypatch.setattr(service, "get_db", lambda: db)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_auth] = lambda: {"id": USER_ID, **user}
        return TestClient(app), users

    return _make


def test_tai_khoan_chua_luu_nhan_mac_dinh_doi_ten(make_client):
    c, _ = make_client({"username": "a"})
    assert c.get("/api/v1/account/settings").json() == {"renameAttachmentFiles": True, "submitterFromDeclaration": False}


def test_gia_tri_da_luu_duoc_tra_ve(make_client):
    c, _ = make_client({"username": "a", "account_settings": {"renameAttachmentFiles": False}})
    assert c.get("/api/v1/account/settings").json() == {"renameAttachmentFiles": False, "submitterFromDeclaration": False}


def test_patch_ghi_dung_khoa_va_tra_ve_ban_day_du(make_client):
    c, users = make_client({"username": "a"})
    r = c.patch("/api/v1/account/settings", json={"renameAttachmentFiles": False})
    assert r.status_code == 200 and r.json() == {"renameAttachmentFiles": False, "submitterFromDeclaration": False}
    assert users.calls == [{"$set": {"account_settings.renameAttachmentFiles": False}}]


def test_patch_khoa_la_bi_bo_qua(make_client):
    c, users = make_client({"username": "a"})
    r = c.patch("/api/v1/account/settings", json={"role": "admin", "xyz": 1})
    assert r.status_code == 200 and r.json() == {"renameAttachmentFiles": True, "submitterFromDeclaration": False}
    assert users.calls == [], "không có khoá hợp lệ thì không ghi DB"


def test_patch_sai_kieu_bi_tu_choi(make_client):
    c, users = make_client({"username": "a"})
    r = c.patch("/api/v1/account/settings", json={"renameAttachmentFiles": "khong"})
    assert r.status_code == 422 and users.calls == []


def test_lay_nguoi_nop_theo_to_khai_mac_dinh_tat_va_luu_duoc(make_client):
    c, users = make_client({"username": "a"})
    assert c.get("/api/v1/account/settings").json()["submitterFromDeclaration"] is False
    r = c.patch("/api/v1/account/settings", json={"submitterFromDeclaration": True})
    assert r.status_code == 200 and r.json()["submitterFromDeclaration"] is True
    assert users.calls == [{"$set": {"account_settings.submitterFromDeclaration": True}}]
