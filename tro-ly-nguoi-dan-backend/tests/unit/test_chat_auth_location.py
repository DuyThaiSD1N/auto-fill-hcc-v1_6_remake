"""Chat đòi JWT; phiên mới auto-chọn nơi làm thủ tục từ tài khoản (tinh/xa);
trace ghi danh tính acc thật thay nặc danh."""
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.chat import store, tracing
from app.chat.router import router as chat_router
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.locations.lookup import location_for

FAKE_USER = {
    "id": "u1", "username": "hcctanphong", "name": "Phường Tân Phong",
    "role": "commune", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong",
}


def _mini_app(user: dict | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router)
    app.add_exception_handler(AppError, app_error_handler)
    if user is not None:
        app.dependency_overrides[require_auth] = lambda: user
    return app


def test_chat_thieu_token_401():
    client = TestClient(_mini_app())
    r = client.post("/api/v1/assistant/chat", json={"message": ""})
    assert r.status_code == 401


def test_phien_moi_lay_noi_tu_acc(monkeypatch):
    saved: dict = {}

    async def _save(conv):
        saved.update(conv)

    monkeypatch.setattr(store, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(store, "save", _save)
    client = TestClient(_mini_app(FAKE_USER))
    r = client.post("/api/v1/assistant/chat", json={"message": ""})
    assert r.status_code == 200
    loc = r.json()["location"]
    assert loc == {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}
    assert saved["auth_user"] == {"id": "u1", "username": "hcctanphong", "name": "Phường Tân Phong"}


def test_phien_moi_acc_cu_ten_tran(monkeypatch):
    # Acc thời nhập tay: "Lai Châu"/"Tân Phong" trần vẫn khớp ra tên đầy đủ.
    monkeypatch.setattr(store, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(store, "save", AsyncMock())
    user = dict(FAKE_USER, tinh="Lai Châu", xa="Tân Phong")
    r = TestClient(_mini_app(user)).post("/api/v1/assistant/chat", json={"message": ""})
    loc = r.json()["location"]
    assert loc["province_slug"] == "laichau" and loc["ward"] == "Phường Tân Phong"


def test_acc_khong_co_tinh_dung_mac_dinh(monkeypatch):
    monkeypatch.setattr(store, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(store, "save", AsyncMock())
    user = dict(FAKE_USER, tinh=None, xa=None)
    r = TestClient(_mini_app(user)).post("/api/v1/assistant/chat", json={"message": ""})
    assert r.json()["location"]["province_slug"] == "bacninh"  # _default_location pilot


def test_location_for_bien():
    assert location_for("Tỉnh Không Tồn Tại", "X") is None
    assert location_for("", "Phường Tân Phong") is None
    # Tỉnh khớp, xã lạ → ward rỗng bắt chọn tay.
    assert location_for("Tỉnh Lai Châu", "Phường Không Có")["ward"] == ""


def test_tracing_identity_fallback():
    assert tracing._identity({}) == ("citizen", "sidebar")
    conv = {"auth_user": {"id": "u9", "username": "hccsonla", "name": "X"}}
    assert tracing._identity(conv) == ("u9", "hccsonla")
