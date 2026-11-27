"""Auto Fill: tệp lấy từ Ví cá nhân (options.walletFiles) được đính bằng nút "Chọn" của ví (app/attachments/wallet_pick.py)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.attachments import router as attach_router
from app.attachments import wallet_pick
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler


def _item(index, **extra):
    return {"fileIndex": index, "fileName": f"f{index}.pdf", "documentName": "Giấy tờ", "componentName": "Bản chính",
            "target": "existing", "componentIndex": 1, "needsAddComponent": False, **extra}


async def fake_planner(files, options, session=None):
    return {"attachments": [_item(0), _item(1)], "extracted": {}, "errors": []}


@pytest.fixture
def client(monkeypatch):
    async def noop(*a, **k):
        return None

    monkeypatch.setattr(attach_router, "get_procedure", lambda key: {"label": "Chứng thực", "mode": "attach"})
    monkeypatch.setattr(attach_router, "get_attach_pipeline", lambda key: fake_planner)
    monkeypatch.setattr(attach_router, "save_request_files", lambda *a, **k: [])
    monkeypatch.setattr(attach_router.requests_repo, "create_request", noop)
    monkeypatch.setattr(attach_router.dossiers_repo, "upsert_started", noop)
    monkeypatch.setattr(attach_router.traces_repo, "create_trace", noop)
    monkeypatch.setattr(attach_router.monitor_persist, "schedule", lambda *a: None)
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(attach_router.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "username": "phuong", "name": "Phường A"}
    return TestClient(app)


def _body(options):
    file = {"type": "application/pdf", "role": "doc", "dataUrl": "data:application/pdf;base64,QUJD"}
    return {"procedure": "chung-thuc-ban-sao", "options": options,
            "files": [{**file, "name": "scan.pdf"}, {**file, "name": "Bằng cử nhân.pdf"}]}


def test_tep_lay_tu_vi_gan_lenh_chon(client):
    wallet = [{"index": 1, "id": "w9", "name": "Bằng cử nhân.pdf", "tab": "issued"}]
    items = client.post("/api/v1/attachments/plan", json=_body({"walletFiles": wallet})).json()["attachments"]
    assert items[0].get("walletPick") is None
    assert items[1]["walletPick"] == {"id": "w9", "name": "Bằng cử nhân.pdf", "tab": "issued"}


def test_ban_cu_khong_gui_wallet_files_thi_ke_hoach_nhu_cu(client):
    items = client.post("/api/v1/attachments/plan", json=_body({})).json()["attachments"]
    assert all(item.get("walletPick") is None for item in items)


def test_wallet_files_sai_dang_bi_bo_qua():
    raw = [{"index": 5, "id": "x"}, {"index": True, "id": "y"}, {"index": 0, "id": ""}, "lạ",
           {"index": 1, "id": "w1", "tab": "khác"}]
    assert wallet_pick.from_options({"walletFiles": raw}, 2) == {1: {"id": "w1", "name": "", "tab": "uploaded"}}


def test_tep_vi_gop_cung_tep_scan_thi_tach_khong_mat_tep():
    item = _item(0, sourceFileIndexes=[0, 1], documentName="Căn cước công dân")
    out = wallet_pick.apply_wallet_picks([item], {1: {"id": "w1", "name": "CCCD.pdf", "tab": "uploaded"}})
    assert sorted(o["fileIndex"] for o in out) == [0, 1]
    assert next(o for o in out if o["fileIndex"] == 1)["walletPick"]["id"] == "w1"
    assert "walletPick" not in next(o for o in out if o["fileIndex"] == 0)
