"""Chỉnh nơi làm / đối tượng ngay trên card xác nhận thủ tục → câu hỏi đổi TẠI CHỖ.

Trước đây mỗi lần đổi tỉnh/xã là một bong bóng + card mới rơi xuống dưới; đổi đối tượng thì câu
hỏi đứng nguyên chữ cũ (câu có ghi "…cho bản thân — đúng không ạ?"). Client khai
`supportsReplaceLast`: BE trả câu mới kèm `replace_last`, không đọc lại, và history thay câu bot
cũ thay vì thêm — khôi phục phiên không dựng lại các câu hỏi chồng nhau. Client cũ: như cũ.
"""
import json
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.channels.handfree.chat import flow, router as chat_router_mod, store
from app.channels.handfree.chat.router import router as chat_router
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler

NEW = {"supportsReplaceLast": True, "supportsProcedureFirst": True}
OLD = {"supportsProcedureFirst": True}
USER = {"id": "u1", "username": "hcchaichau", "name": "UBND Hải Châu", "role": "commune",
        "tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu"}


def _conv(caps):
    conv = {
        "_id": "t-confirm", "state": "greet", "history": [], "milestones": [],
        "auth_user": {"id": USER["id"]},  # router chỉ cho chủ phiên đi tiếp
        "client_capabilities": dict(caps),
        "location": {"province": "Thành phố Đà Nẵng", "province_slug": "danang", "ward": "Phường Hải Châu"},
    }
    first = flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    conv["history"].append({"role": "bot", "text": first.display_md, "state": conv["state"]})
    return conv


# ── Tầng flow ──

def test_doi_noi_client_moi_sua_tai_cho_khong_doc_lai():
    conv = _conv(NEW)
    r = flow._apply_location(conv, {"province_slug": "hanoi", "ward": "Phường Ngọc Hà"})
    assert r.replace_last is True
    assert r.tts_text == "", "công dân vừa tự bấm dropdown — đọc lại mỗi lần chọn là ồn"
    assert "Phường Ngọc Hà" in r.display_md


def test_doi_noi_client_cu_giu_nguyen_ve_them():
    conv = _conv(OLD)
    r = flow._apply_location(conv, {"province_slug": "hanoi", "ward": "Phường Ngọc Hà"})
    assert r.replace_last is False
    assert r.tts_text, "bản trên chợ giữ nguyên hành vi cũ"


def test_doi_doi_tuong_client_moi_sua_cau_theo():
    conv = _conv(NEW)
    r = flow._apply_execution_subject(conv, {"key": "authorized_person"})
    assert r.replace_last is True
    assert "do người khác ủy quyền" in r.display_md


def test_doi_doi_tuong_client_cu_van_im_lang():
    """Client cũ không sửa tại chỗ được: trả câu mới là mỗi lần đổi lại thêm một bong bóng."""
    conv = _conv(OLD)
    r = flow._apply_execution_subject(conv, {"key": "authorized_person"})
    assert not r.display_md and not r.cards and r.replace_last is False


# ── Tầng router: history phải khớp màn hình ──

def _client(conv, monkeypatch):
    monkeypatch.setattr(store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(store, "save", AsyncMock())
    monkeypatch.setattr(chat_router_mod, "_sync_dossier", AsyncMock())
    app = FastAPI()
    app.include_router(chat_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[require_auth] = lambda: USER
    return TestClient(app)


def _pick_ward(client, caps):
    return client.post("/api/v1/assistant/chat", json={
        "conversation_id": "t-confirm",
        "message": "__action:set_location:" + json.dumps({"province_slug": "hanoi", "ward": "Phường Ngọc Hà"}),
        "display_message": "Chọn nơi làm thủ tục: Phường Ngọc Hà, Thành phố Hà Nội",
        "source": "chip",
        "client_context": {"capabilities": caps},
    })


def test_router_thay_cau_bot_cu_trong_history(monkeypatch):
    conv = _conv(NEW)
    res = _pick_ward(_client(conv, monkeypatch), NEW)
    assert res.status_code == 200, res.text
    assert res.json()["replace_last"] is True
    bots = [h for h in conv["history"] if h["role"] == "bot"]
    users = [h for h in conv["history"] if h["role"] == "user"]
    assert len(bots) == 1, "phải THAY câu hỏi cũ, không thêm câu thứ hai"
    assert "Phường Ngọc Hà" in bots[0]["text"]
    assert not users, "chỉnh dropdown không phải một câu công dân nói — không lưu vào history"


def test_router_client_cu_van_them_nhu_truoc(monkeypatch):
    conv = _conv(OLD)
    res = _pick_ward(_client(conv, monkeypatch), OLD)
    assert res.json()["replace_last"] is False
    assert len([h for h in conv["history"] if h["role"] == "bot"]) == 2
