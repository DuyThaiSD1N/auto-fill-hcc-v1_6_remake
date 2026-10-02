"""Mốc nộp đi được bằng NHIỀU đường mà một cú bấm vẫn chỉ là một sự kiện.

- Handfree: background extension báo thẳng (sidebar là iframe, chết theo trang khi cổng chuyển
  trang lúc bấm nộp) VÀ sidebar còn sống thì vẫn báo qua chat — hai đường mang chung `click_id`.
- Auto Fill: background gửi lại khi lần trước rớt (token hết hạn / mất mạng) — lần trước có thể
  đã tới server rồi, chỉ là client không nhận được phản hồi.
- Lưới đỡ dò chữ "nộp thành công" trên màn kết quả nói về CHÍNH lần bấm vừa rồi.
"""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.channels.handfree.chat.router as chat_router
from app.channels.handfree.chat.router import router as handfree_router
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.dossiers import repo
from app.dossiers.router import router as dossiers_router

_T0 = datetime(2026, 9, 28, 2, 8, tzinfo=timezone.utc)
USER = {"id": "u1", "username": "hccx", "name": "UBND X", "role": "commune"}


class _AsyncColl:
    """Bọc collection mongomock (đồng bộ) thành API async kiểu Motor mà repo dùng."""

    def __init__(self, coll):
        self._c = coll

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)

    async def replace_one(self, *a, **kw):
        return self._c.replace_one(*a, **kw)


class _AsyncDb:
    def __init__(self):
        raw = mongomock.MongoClient().db
        self.dossiers = _AsyncColl(raw.dossiers)
        self.conversations = _AsyncColl(raw.conversations)


@pytest.fixture()
def db(monkeypatch):
    fake = _AsyncDb()
    monkeypatch.setattr(repo, "get_db", lambda: fake)
    monkeypatch.setattr("app.db.mongo.get_db", lambda: fake)
    monkeypatch.setattr(chat_router.store, "get_db", lambda: fake)
    return fake


def _dossier(db, **extra):
    db.dossiers._c.insert_one({"_id": "d1", "user_id": "u1", "started_at": _T0, **extra})


def _events(db, dossier_id="d1"):
    return db.dossiers._c.find_one({"_id": dossier_id}).get("submit_events") or []


# ── Tầng repo ──

async def test_cung_click_id_chi_ghi_mot_su_kien(db):
    _dossier(db)
    for _ in range(3):  # background + sidebar + một lần gửi lại
        await repo.add_submit_event(dossier_id="d1", clicked_at=_T0, click_id="c-1", owner_user_id="u1")
    assert len(_events(db)) == 1
    assert db.dossiers._c.find_one({"_id": "d1"})["submit_count"] == 1


async def test_hai_cu_bam_khac_nhau_van_la_hai_su_kien(db):
    """Chứng thực tách nhiều tab: mỗi tab một cú bấm, một hồ sơ trên cổng — phải đếm đủ."""
    _dossier(db)
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0, click_id="c-1")
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0 + timedelta(minutes=2), click_id="c-2")
    assert len(_events(db)) == 2


async def test_khong_click_id_giu_hanh_vi_cu(db):
    """Extension cũ trên chợ không gửi mã → mỗi request là một sự kiện như trước."""
    _dossier(db)
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0)
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0)
    assert len(_events(db)) == 2


async def test_do_chu_ngay_sau_cu_bam_la_trung(db):
    _dossier(db)
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0, click_id="c-1")
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0 + timedelta(seconds=20), source="text")
    assert len(_events(db)) == 1


async def test_do_chu_khi_cu_bam_rot_thi_ghi(db):
    _dossier(db)
    await repo.add_submit_event(dossier_id="d1", clicked_at=_T0, source="text")
    ev = _events(db)
    assert len(ev) == 1 and ev[0]["source"] == "text"


def test_gio_client_lech_thi_lay_gio_server():
    now = datetime.now(timezone.utc)
    assert abs((repo.client_clicked_at(None) - now).total_seconds()) < 5
    assert abs((repo.client_clicked_at("rác") - now).total_seconds()) < 5
    xa_qua = (now - timedelta(days=30)).timestamp() * 1000
    assert abs((repo.client_clicked_at(xa_qua) - now).total_seconds()) < 5
    hai_gio_truoc = now - timedelta(hours=2)
    got = repo.client_clicked_at(hai_gio_truoc.timestamp() * 1000)
    assert abs((got - hai_gio_truoc).total_seconds()) < 1, "gửi lại muộn phải giữ đúng giờ bấm thật"


# ── Auto Fill: /api/v1/dossiers/submit-click ──

def _app(router):
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[require_auth] = lambda: USER
    return TestClient(app)


def test_autofill_gui_lai_cung_ma_khong_dem_doi(db):
    _dossier(db)
    client = _app(dossiers_router)
    body = {"dossierId": "d1", "portalHost": "dvc.moc.gov.vn", "clickId": "c-9",
            "clickedAt": int((datetime.now(timezone.utc) - timedelta(minutes=40)).timestamp() * 1000)}
    assert client.post("/api/v1/dossiers/submit-click", json=body).status_code == 200
    assert client.post("/api/v1/dossiers/submit-click", json=body).status_code == 200
    ev = _events(db)
    assert len(ev) == 1
    lech = datetime.now(timezone.utc) - ev[0]["at"].replace(tzinfo=timezone.utc)
    assert timedelta(minutes=39) < lech < timedelta(minutes=41), "phải ghi giờ bấm thật, không phải giờ gửi lại"


def test_autofill_ban_cu_khong_gui_truong_moi(db):
    _dossier(db)
    client = _app(dossiers_router)
    assert client.post("/api/v1/dossiers/submit-click",
                       json={"dossierId": "d1", "portalHost": "x"}).status_code == 200
    assert len(_events(db)) == 1


# ── Handfree: /api/v1/assistant/conversations/{id}/submit-click ──

def _conv(db, **extra):
    conv = {
        "_id": "conv-1", "state": "attaching", "history": [{"role": "bot", "text": "giữ nguyên"}],
        "auth_user": {"id": "u1", "username": "hccx"}, "dossier_started_at": _T0,
        "procedure_key": "chung-thuc-chu-ky", "attach_trace_request_id": "req-1",
        "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Việt Yên"},
        "client_capabilities": {"supportsRating": True}, **extra,
    }
    db.conversations._c.insert_one(conv)
    return conv


def test_handfree_background_ghi_moc_khong_dung_hoi_thoai(db):
    _conv(db)
    client = _app(handfree_router)
    res = client.post("/api/v1/assistant/conversations/conv-1/submit-click",
                      json={"click_id": "c-1", "host": "dichvucong.laichau.gov.vn"})
    assert res.status_code == 200, res.text
    assert len(_events(db, "conv-1")) == 1
    conv = db.conversations._c.find_one({"_id": "conv-1"})
    assert conv["submit_click_id"] == "c-1" and conv["submit_clicked_synced_at"]
    assert conv["state"] == "attaching" and conv["history"] == [{"role": "bot", "text": "giữ nguyên"}]
    assert conv["client_capabilities"] == {"supportsRating": True}, "không được đè capability"


async def test_handfree_hai_duong_cung_cu_bam_chi_mot_su_kien(db, monkeypatch):
    """Background báo trước, sidebar còn sống báo sau qua chat (để hiện phiếu đánh giá)."""
    _conv(db)
    client = _app(handfree_router)
    client.post("/api/v1/assistant/conversations/conv-1/submit-click", json={"click_id": "c-1"})
    # Lượt chat của sidebar đọc conv, đi qua flow như thật rồi đồng bộ sổ hồ sơ.
    conv = db.conversations._c.find_one({"_id": "conv-1"})
    chat_router.flow._record_submit_click(conv, {"host": "x", "click_id": "c-1"})
    await chat_router._sync_dossier(conv)
    assert len(_events(db, "conv-1")) == 1


def test_handfree_phien_nguoi_khac_bi_chan(db):
    _conv(db, auth_user={"id": "u-khac", "username": "khac"})
    client = _app(handfree_router)
    res = client.post("/api/v1/assistant/conversations/conv-1/submit-click", json={"click_id": "c-1"})
    assert res.status_code == 403
    assert db.dossiers._c.find_one({"_id": "conv-1"}) is None


# ── Chứng thực tách nhiều tab: CHUNG một khóa hồ sơ, mỗi tab một lần nộp ──

def test_autofill_da_tab_chu_thanh_cong_tab_2_khong_bi_tab_1_che(db):
    """Tab 1 ghi bằng cú bấm, tab 2 rớt cú bấm chỉ còn chữ "thành công" → phải đủ 2 lần nộp.
    Extension đã lọc theo TỪNG TAB; BE lọc theo cả hồ sơ là che mất tab 2."""
    _dossier(db)
    client = _app(dossiers_router)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    client.post("/api/v1/dossiers/submit-click",
                json={"dossierId": "d1", "clickId": "tab1", "clickedAt": now_ms - 60_000, "source": "click"})
    client.post("/api/v1/dossiers/submit-click",
                json={"dossierId": "d1", "clickId": "tab2-text", "clickedAt": now_ms, "source": "text"})
    assert [e.get("source") for e in _events(db)] == ["click", "text"]


def _unix_ms(dt):
    return int(dt.timestamp() * 1000)


def test_handfree_tab_goc_ghi_bang_do_chu_roi_tab_tach_bam_van_dem(db):
    """Tab gốc: cú bấm rớt, lưới dò chữ ghi mốc. Tab tách bấm nộp SAU đó = hồ sơ khác trên cổng."""
    text_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    _conv(db, submit_clicked_at=text_at, submit_clicked_source="text", submit_click_id="",
          submit_clicked_synced_at=text_at)
    db.dossiers._c.insert_one({"_id": "conv-1", "user_id": "u1", "started_at": _T0,
                               "submit_clicked_at": text_at, "submit_count": 1,
                               "submit_events": [{"at": text_at, "source": "text"}]})
    client = _app(handfree_router)
    client.post("/api/v1/assistant/conversations/conv-1/submit-click",
                json={"click_id": "tab2", "clicked_at": _unix_ms(datetime.now(timezone.utc))})
    assert len(_events(db, "conv-1")) == 2


def test_handfree_cu_bam_truoc_moc_do_chu_la_cung_lan_nop(db):
    """Cú bấm của CHÍNH lần nộp luôn sớm hơn màn kết quả → chỉ nâng nhãn, không đếm thêm."""
    text_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    _conv(db, submit_clicked_at=text_at, submit_clicked_source="text", submit_click_id="")
    db.dossiers._c.insert_one({"_id": "conv-1", "user_id": "u1", "started_at": _T0,
                               "submit_events": [{"at": text_at, "source": "text"}]})
    client = _app(handfree_router)
    client.post("/api/v1/assistant/conversations/conv-1/submit-click",
                json={"click_id": "c-goc", "clicked_at": _unix_ms(text_at - timedelta(seconds=5))})
    assert len(_events(db, "conv-1")) == 1
    assert db.conversations._c.find_one({"_id": "conv-1"})["submit_clicked_source"] == "click"


async def test_handfree_sidebar_bao_tab_tach_sau_moc_do_chu_van_dem(db):
    """Đường sidebar (flow) cùng quy tắc với endpoint background."""
    text_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    conv = _conv(db, submit_clicked_at=text_at, submit_clicked_source="text",
                 submit_clicked_synced_at=text_at, dossier_has_activity=True)
    db.dossiers._c.insert_one({"_id": "conv-1", "user_id": "u1", "started_at": _T0,
                               "submit_events": [{"at": text_at, "source": "text"}]})
    chat_router.flow._record_submit_click(conv, {"click_id": "tab2", "clicked_at": _unix_ms(datetime.now(timezone.utc))})
    await chat_router._sync_dossier(conv, persist=False)
    assert len(_events(db, "conv-1")) == 2



# ── Chỉ tính nộp khi hồ sơ đã có lượt ĐIỀN hoặc ĐÍNH KÈM ──

def _conv_rong(db):
    """Phiên Handfree đã chọn thủ tục nhưng trợ lý chưa điền/đính gì (cán bộ làm bằng Auto Fill)."""
    return _conv(db, attach_trace_request_id=None)


def test_handfree_background_bam_nop_khi_chua_dien_dinh_khong_tao_ho_so(db):
    _conv_rong(db)
    client = _app(handfree_router)
    res = client.post("/api/v1/assistant/conversations/conv-1/submit-click", json={"click_id": "c-1"})
    assert res.status_code == 200
    assert db.dossiers._c.find_one({"_id": "conv-1"}) is None, "không được đẻ hồ sơ 'đã nộp' rỗng"
    conv = db.conversations._c.find_one({"_id": "conv-1"})
    assert conv.get("submit_clicked_at") is None and not conv.get("dossier_has_activity")


async def test_handfree_bam_truoc_khi_dien_dinh_khong_ghi_bu_ve_sau(db):
    """Cú bấm lúc chưa có việc thật bị bỏ; có lượt đính kèm sau đó cũng không được ghi bù mốc cũ.
    Lần nộp thật sau đó là một cú bấm mới → một sự kiện."""
    conv = _conv_rong(db)
    chat_router.flow._record_submit_click(conv, {"click_id": "som"})
    await chat_router._sync_dossier(conv, persist=False)
    conv["attach_trace_request_id"] = "req-1"   # trợ lý đính kèm
    await chat_router._sync_dossier(conv, persist=False)
    assert _events(db, "conv-1") == []
    chat_router.flow._record_submit_click(conv, {"click_id": "that"})
    await chat_router._sync_dossier(conv, persist=False)
    assert [e["id"] for e in _events(db, "conv-1")] == ["that"]


def test_handfree_khong_hoi_danh_gia_khi_chua_dien_dinh():
    conv = {"client_capabilities": {"supportsRating": True}}
    r = chat_router.flow._record_submit_click(conv, {"click_id": "c-1"})
    assert not r.cards and not conv.get("awaiting_rating"), "không có dòng hồ sơ để lưu phiếu"
    conv["attach_trace_request_id"] = "req-1"
    r = chat_router.flow._record_submit_click(conv, {"click_id": "c-2"})
    assert r.cards and r.cards[0]["kind"] == "rating"


async def test_handfree_man_ket_thuc_khong_hoi_danh_gia_khi_chua_dien_dinh(monkeypatch):
    conv = {"state": "done", "client_capabilities": {"supportsRating": True}}
    r = await chat_router.flow._handle_done(conv, chat_router.intents.Intent("event", "submitted", {}))
    assert not any(c.get("kind") == "rating" for c in (r.cards or []))
    assert not conv.get("awaiting_rating")
