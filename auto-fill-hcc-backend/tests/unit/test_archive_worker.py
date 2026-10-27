import asyncio
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app.archive import worker as worker_mod
from app.archive.worker import Archiver
from app.archive.config import archive_settings

T0 = datetime(2026, 10, 24, 2, 0, tzinfo=timezone.utc)


class _Cursor:
    def __init__(self, cur):
        self._cur = cur

    def sort(self, *a, **kw):
        self._cur = self._cur.sort(*a, **kw)
        return self

    def limit(self, n):
        self._cur = self._cur.limit(n)
        return self

    def __aiter__(self):
        self._it = iter(list(self._cur))
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None

    async def to_list(self, length=None):
        return list(self._cur)


class _Coll:
    def __init__(self, coll):
        self._c = coll

    def find(self, *a, **kw):
        return _Cursor(self._c.find(*a, **kw))

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)

    async def update_many(self, *a, **kw):
        return self._c.update_many(*a, **kw)

    async def delete_one(self, *a, **kw):
        return self._c.delete_one(*a, **kw)


class _Db:
    def __init__(self):
        self._raw = mongomock.MongoClient(tz_aware=True).db

    def __getitem__(self, name):
        return _Coll(self._raw[name])

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return _Coll(self._raw[name])


class _Vault:
    def __init__(self):
        self.bundles: list[dict] = []
        self.files: dict[str, bytes] = {}
        self.fail = False

    async def send(self, bundle, files):
        if self.fail:
            raise ConnectionError("vault không phản hồi")
        self.bundles.append(bundle)
        for sha, path in files.items():
            self.files[sha] = path.read_bytes()
        return "id"


class _Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(archive_settings, "vault_url", "http://vault.test")
    monkeypatch.setattr(archive_settings, "archive_hmac_key", "khoa-thu")
    monkeypatch.setattr(archive_settings, "archive_after_minutes", 30)
    monkeypatch.setattr(archive_settings, "archive_send_delay_seconds", 90)
    monkeypatch.setattr(archive_settings, "archive_since", None)
    monkeypatch.setattr(archive_settings, "archive_require_ack_before", None)
    db, vault, clock = _Db(), _Vault(), _Clock()
    archiver = Archiver(db=db, client=vault, now=clock, storage_dir=str(tmp_path))
    return db, vault, clock, archiver, tmp_path


def _seed_request(db, root, *, rid="req-1", at=T0, pending=True):
    flag = {"archive_pending": True} if pending else {}
    day = root / at.strftime("%Y-%m-%d") / rid
    day.mkdir(parents=True)
    (day / "00_cccd.jpg").write_bytes(b"anh-cccd")
    (day / "01_dup.jpg").write_bytes(b"anh-cccd")
    review = root / "review" / rid
    review.mkdir(parents=True)
    (review / "0.jpg").write_bytes(b"anh-ra-soat")
    (review / "sources.json").write_text('{"fields": {"HoTen": "NGUYEN VAN A"}}', encoding="utf-8")
    db.traces._c.insert_one({
        "request_id": rid, "user_id": "u1", "username": "hccx", "name": "Xã X", "procedure": "khai-sinh",
        "kind": "autofill", "experience": "autofill", "created_at": at, "applicant_name": "NGUYỄN VĂN A",
        "ocr_text": "CĂN CƯỚC 001099012345", "llm_output": {"HoTen": "NGUYỄN VĂN A"},
        "attachments": [{"name": "CCCD Nguyễn Văn A.jpg", "role": "", "sha256": "s1", "uses": 1}],
        "timing": {"wall": 1200}, "key_fields_total": 5, "key_fields_filled": 4, **flag})
    db.trace_steps._c.insert_one({
        "_id": f"{rid}:autofill", "request_id": rid, "kind": "autofill", "created_at": at,
        "meta": {"user_id": "u1", "name": "Xã X", "procedure": "khai-sinh"},
        "llm": [{"n": 1, "purpose": "extract", "ms": 900, "tokens_in": 10, "raw": "{\"HoTen\":\"A\"}",
                 "parsed": {"HoTen": "A"}, "tries": [{"target": "primary", "ms": 900, "ok": True,
                                                      "error": "x"}]}],
        "ocr": [{"idx": 0, "name": "CCCD Nguyễn Văn A.jpg", "sha256": "sha-ocr", "chars": 20, "text": "x"}],
        "outputs": {"response": {"fields": [{"name": "HoTen", "value": "A"}]}},
        "spans": [{"i": 1, "n": "pre.receive", "ms": 3, "a": {"files": 1, "name": "CCCD.jpg"}}],
        "errors": ["LLM lỗi với HoTen=A"], **flag})
    db.process_requests._c.insert_one({
        "request_id": rid, "user_id": "u1", "procedure": "khai-sinh", "created_at": at,
        "options": {"formContext": {"applicantFullname": "NGUYỄN VĂN A"}},
        "fields": [{"name": "HoTen", "value": "A"}], "extracted": {"HoTen": "A"},
        "files": [{"name": "CCCD Nguyễn Văn A.jpg", "type": "image/jpeg", "role": "", "size": 8,
                   "path": f"{at:%Y-%m-%d}/{rid}/00_cccd.jpg"},
                  {"name": "bản sao.jpg", "type": "image/jpeg", "role": "", "size": 8,
                   "path": f"{at:%Y-%m-%d}/{rid}/01_dup.jpg"}], **flag})
    db.ocr_texts._c.insert_one({"_id": "sha-ocr", "text": "CĂN CƯỚC 001099012345", "created_at": at})
    return day, review


@pytest.mark.asyncio
async def test_gui_som_roi_xoa_dung_han_giu_metadata(env):
    db, vault, clock, archiver, root = env
    day, review = _seed_request(db, root)

    clock.now = T0 + timedelta(minutes=2)
    await archiver.run_once()
    assert len(vault.bundles) == 1
    bundle = vault.bundles[0]
    assert bundle["type"] == "request" and bundle["request_id"] == "req-1"
    assert bundle["traces"][0]["applicant_name"] == "NGUYỄN VĂN A"
    assert bundle["ocr_texts"] == {"sha-ocr": "CĂN CƯỚC 001099012345"}
    assert {f["role"] for f in bundle["files"]} == {"original", "review"}
    assert b"anh-cccd" in vault.files.values() and b"anh-ra-soat" in vault.files.values()
    assert db.traces._c.find_one()["applicant_name"] == "NGUYỄN VĂN A"
    assert (day / "00_cccd.jpg").exists()

    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    assert len(vault.bundles) == 1

    trace = db.traces._c.find_one()
    for key in ("applicant_name", "ocr_text", "llm_output"):
        assert key not in trace
    att = trace["attachments"][0]
    assert "name" not in att and att["sha256"] == "s1" and att["nk"].startswith("k:")
    assert trace["timing"] == {"wall": 1200} and trace["key_fields_filled"] == 4
    assert trace["archive_pending"] is False and "archive_failed" not in trace

    steps = db.trace_steps._c.find_one()
    assert steps["llm"] == [{"n": 1, "purpose": "extract", "ms": 900, "tokens_in": 10,
                             "tries": [{"target": "primary", "ms": 900, "ok": True}]}]
    assert steps["ocr"] == [{"idx": 0, "sha256": "sha-ocr", "chars": 20}]
    assert steps["spans"][0]["a"] == {"files": 1}
    assert "outputs" not in steps and "errors" not in steps and steps["errors_count"] == 1

    preq = db.process_requests._c.find_one()
    assert "options" not in preq and "fields" not in preq and "extracted" not in preq
    assert all("name" not in f and "path" not in f for f in preq["files"])

    assert not day.exists() and not review.exists()
    assert db.archive_state._c.count_documents({}) == 0

    await archiver.run_once()
    assert db.ocr_texts._c.count_documents({}) == 0
    assert len(vault.bundles) == 1


@pytest.mark.asyncio
async def test_vault_loi_van_xoa_khi_qua_han_va_danh_dau(env):
    db, vault, clock, archiver, root = env
    day, _ = _seed_request(db, root)
    vault.fail = True
    clock.now = T0 + timedelta(minutes=5)
    await archiver.run_once()
    assert db.traces._c.find_one()["applicant_name"]

    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    trace = db.traces._c.find_one()
    assert "applicant_name" not in trace and trace["archive_failed"] is True
    assert not day.exists()


@pytest.mark.asyncio
async def test_du_lieu_cu_chi_xoa_khi_vault_da_nhan(env, monkeypatch):
    db, vault, clock, archiver, root = env
    day, _ = _seed_request(db, root)
    monkeypatch.setattr(archive_settings, "archive_require_ack_before", T0 + timedelta(days=1))
    vault.fail = True
    clock.now = T0 + timedelta(hours=5)
    await archiver.run_once()
    assert db.traces._c.find_one()["applicant_name"] == "NGUYỄN VĂN A"
    assert day.exists()

    vault.fail = False
    await archiver.run_once()
    assert "applicant_name" not in db.traces._c.find_one()
    assert not day.exists()


@pytest.mark.asyncio
async def test_ban_ghi_khong_co_co_khong_bi_dung(env):
    db, vault, clock, archiver, root = env
    day, _ = _seed_request(db, root, pending=False)
    clock.now = T0 + timedelta(hours=2)
    await archiver.run_once()
    assert vault.bundles == []
    assert db.traces._c.find_one()["applicant_name"] == "NGUYỄN VĂN A"
    assert day.exists()


@pytest.mark.asyncio
async def test_bao_cao_den_sau_khi_da_luu_tru(env):
    db, vault, clock, archiver, root = env
    _seed_request(db, root)
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    db.traces._c.update_one({}, {"$set": {"report": {"filled": 7}, "archive_pending": True}})
    await archiver.run_once()
    assert vault.bundles[-1]["traces"][0]["report"] == {"filled": 7}
    assert "report" not in db.traces._c.find_one()


@pytest.mark.asyncio
async def test_hoi_thoai_qua_han_gui_roi_xoa_vault_loi_cho_them_5_phut(env):
    db, vault, clock, archiver, root = env
    db.conversations._c.insert_one({"_id": "c1", "updated_at": T0, "history": [{"text": "tên tôi là A"}],
                                    "auth_user": {"id": "u1", "username": "kiosk"}})
    review = root / "review" / "c1"
    review.mkdir(parents=True)
    (review / "0.jpg").write_bytes(b"x")
    vault.fail = True
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    assert db.conversations._c.count_documents({}) == 1

    clock.now = T0 + timedelta(minutes=36)
    await archiver.run_once()
    assert db.conversations._c.count_documents({}) == 0 and not review.exists()


@pytest.mark.asyncio
async def test_hoi_thoai_dang_dung_khong_bi_xoa(env):
    db, vault, clock, archiver, _ = env
    db.conversations._c.insert_one({"_id": "c1", "updated_at": T0 + timedelta(minutes=20)})
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    assert db.conversations._c.count_documents({}) == 1 and vault.bundles == []


@pytest.mark.asyncio
async def test_phien_tai_anh_het_han_gui_tep_roi_xoa(env):
    db, vault, clock, archiver, root = env
    d = root / "upload_sessions" / "s1"
    d.mkdir(parents=True)
    (d / "f1").write_bytes(b"anh-dien-thoai")
    db.upload_sessions._c.insert_one({"_id": "s1", "experience": "autofill", "files": [{"name": "a.jpg"}],
                                      "created_at": T0, "updated_at": T0,
                                      "expires_at": T0 + timedelta(minutes=30)})
    clock.now = T0 + timedelta(minutes=29)
    await archiver.run_once()
    assert d.exists()
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    assert not d.exists() and db.upload_sessions._c.count_documents({}) == 0
    assert vault.bundles[0]["type"] == "upload_session"
    assert b"anh-dien-thoai" in vault.files.values()


@pytest.mark.asyncio
async def test_ho_so_xoa_ten_va_ma_cong_giu_danh_gia(env):
    db, vault, clock, archiver, _ = env
    db.dossiers._c.insert_one({
        "_id": "d1", "user_id": "u1", "procedure": "khai-sinh", "updated_at": T0, "archive_pending": True,
        "applicant_name": "NGUYỄN VĂN A", "portal_dossier_ref": "H12.99-261024-0001",
        "submit_events": [{"at": T0, "ref": "H12.99-261024-0001", "host": "dvc"}],
        "rating": {"level": 5, "note": "nhanh"}, "submit_clicked_at": T0})
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    doc = db.dossiers._c.find_one()
    assert "applicant_name" not in doc and "portal_dossier_ref" not in doc
    assert doc["submit_events"] == [{"at": T0, "host": "dvc"}]
    assert doc["rating"] == {"level": 5, "note": "nhanh"} and doc["submit_clicked_at"] == T0
    assert vault.bundles[0]["data"]["applicant_name"] == "NGUYỄN VĂN A"


@pytest.mark.asyncio
async def test_chay_thu_khong_gui_khong_xoa(env):
    db, vault, clock, _, root = env
    day, _ = _seed_request(db, root)
    archiver = Archiver(db=db, client=vault, now=clock, storage_dir=str(root), dry_run=True)
    clock.now = T0 + timedelta(hours=1)
    counts = await archiver.run_once()
    assert counts.get("would_send", 0) >= 1
    assert vault.bundles == [] and day.exists()
    assert db.traces._c.find_one()["applicant_name"] == "NGUYỄN VĂN A"


@pytest.mark.asyncio
async def test_thu_muc_mo_coi_xoa_sau_khi_luu_chua_dat_since_thi_can_vault_nhan(env):
    db, vault, clock, archiver, root = env
    orphan = root / "upload_sessions" / "mat-ban-ghi"
    orphan.mkdir(parents=True)
    (orphan / "f").write_bytes(b"anh")
    clock.now = datetime.now(timezone.utc) + timedelta(hours=1)
    vault.fail = True
    await archiver.run_once()
    assert orphan.exists()

    vault.fail = False
    archiver.loops = 0
    await archiver.run_once()
    assert not orphan.exists()
    assert vault.bundles[-1]["type"] == "orphan_upload_session"


@pytest.mark.asyncio
async def test_them_khoa_bam_cho_trace_cu_giu_nguyen_ten(env):
    db, *_ = env
    db.traces._c.insert_many([
        {"_id": 1, "attachments": [{"name": "CCCD.jpg", "role": ""}, {"name": "Đơn.pdf", "role": ""}]},
        {"_id": 2, "attachments": []},
        {"_id": 3, "attachments": [{"name": "a.pdf", "role": "", "nk": "k:co-san", "sk": "k:x", "idd": False}]},
    ])
    assert await worker_mod.backfill_trace_keys(db, batch=1) == 1
    first = db.traces._c.find_one({"_id": 1})["attachments"]
    assert [a["name"] for a in first] == ["CCCD.jpg", "Đơn.pdf"]
    assert all(a["nk"].startswith("k:") for a in first) and first[0]["idd"] is True
    assert db.traces._c.find_one({"_id": 3})["attachments"][0]["nk"] == "k:co-san"
    assert await worker_mod.backfill_trace_keys(db) == 0


@pytest.mark.asyncio
async def test_luot_moi_khong_phai_xep_sau_hang_ton(env, monkeypatch):
    db, vault, clock, archiver, _ = env
    monkeypatch.setattr(archive_settings, "archive_batch", 5)
    monkeypatch.setattr(archive_settings, "archive_require_ack_before", T0)
    for i in range(60):
        db.traces._c.insert_one({"request_id": f"cu-{i}", "created_at": T0 - timedelta(days=30, minutes=i),
                                 "applicant_name": "A", "archive_pending": True})
    clock.now = T0 + timedelta(minutes=3)
    db.traces._c.insert_one({"request_id": "moi", "created_at": T0, "applicant_name": "B",
                             "archive_pending": True})
    await archiver.run_once()
    sent = [b["request_id"] for b in vault.bundles]
    assert sent[0] == "moi" and len(sent) == 6
    assert db.traces._c.find_one({"request_id": "moi"})["applicant_name"] == "B"
    assert db.traces._c.count_documents({"archive_pending": True}) == 61 - 5

    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    assert "applicant_name" not in db.traces._c.find_one({"request_id": "moi"})
    assert db.traces._c.count_documents({"archive_pending": True}) == 61 - 5 - 1 - 5


async def test_gui_song_song_va_mot_luot_loi_khong_chan_luot_khac(env, monkeypatch):
    db, vault, clock, archiver, _ = env
    monkeypatch.setattr(archive_settings, "archive_batch", 20)
    monkeypatch.setattr(archive_settings, "archive_concurrency", 4)
    monkeypatch.setattr(archive_settings, "archive_require_ack_before", T0)
    for i in range(12):
        db.traces._c.insert_one({"request_id": f"r{i}", "created_at": T0 - timedelta(days=1, minutes=i),
                                 "applicant_name": "A", "archive_pending": True})
    state = {"now": 0, "max": 0}
    send = vault.send

    async def slow_send(bundle, files):
        if bundle["request_id"] == "r3":
            raise RuntimeError("hỏng")
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return await send(bundle, files)

    monkeypatch.setattr(vault, "send", slow_send)
    await archiver.run_once()
    assert state["max"] == 4
    assert len(vault.bundles) == 11
    assert db.traces._c.find_one({"request_id": "r3"})["archive_pending"] is True


async def test_vong_luot_moi_tach_khoi_vong_hang_ton(env, monkeypatch):
    db, vault, clock, archiver, _ = env
    monkeypatch.setattr(archive_settings, "archive_send_delay_seconds", 10)
    monkeypatch.setattr(archive_settings, "archive_require_ack_before", T0)
    for i in range(30):
        db.traces._c.insert_one({"request_id": f"cu-{i}", "created_at": T0 - timedelta(days=3, minutes=i),
                                 "applicant_name": "A", "archive_pending": True})
    db.traces._c.insert_one({"request_id": "moi", "created_at": T0, "applicant_name": "B",
                             "archive_pending": True})
    db.dossiers._c.insert_one({"_id": "hs-cu", "updated_at": T0 - timedelta(days=3), "applicant_name": "A",
                               "archive_pending": True})

    clock.now = T0 + timedelta(seconds=15)
    await archiver.run_once("recent")
    assert [b["request_id"] for b in vault.bundles] == ["moi"]
    assert db.traces._c.find_one({"request_id": "moi"})["applicant_name"] == "B"

    vault.bundles.clear()
    await archiver.run_once("backlog")
    sent = {b.get("request_id") or b.get("id") for b in vault.bundles}
    assert "moi" not in sent and "cu-0" in sent and "hs-cu" in sent

    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once("recent")
    assert "applicant_name" not in db.traces._c.find_one({"request_id": "moi"})


async def test_mot_luot_khong_xu_ly_dong_thoi_hai_lan(env):
    db, vault, clock, archiver, _ = env
    worker_mod._BUSY.add("dang-chay")
    try:
        db.traces._c.insert_one({"request_id": "dang-chay", "created_at": T0, "applicant_name": "A",
                                 "archive_pending": True})
        clock.now = T0 + timedelta(minutes=5)
        await archiver.run_once("recent")
        assert vault.bundles == []
    finally:
        worker_mod._BUSY.discard("dang-chay")


@pytest.mark.asyncio
async def test_goi_kem_phan_khong_nhay_cam_de_dung_lai_luot(env):
    db, vault, clock, archiver, root = env
    _seed_request(db, root)
    db.traces._c.update_one({}, {"$set": {"procedure_label": "Đăng ký khai sinh"}})
    clock.now = T0 + timedelta(minutes=31)
    await archiver.run_once()
    bundle = vault.bundles[-1]
    assert bundle["procedure_label"] == "Đăng ký khai sinh"
    pub_trace = bundle["public"]["traces"][0]
    assert "applicant_name" not in pub_trace and pub_trace["timing"] == {"wall": 1200}
    assert pub_trace["created_at"].endswith("+00:00") and "archive_pending" not in pub_trace
    assert "name" not in pub_trace["attachments"][0]
    pub_steps = bundle["public"]["trace_steps"][0]
    assert pub_steps["spans"][0]["a"] == {"files": 1} and "outputs" not in pub_steps
    assert "raw" not in pub_steps["llm"][0] and "text" not in pub_steps["ocr"][0]
    assert db.traces._c.find_one()["archive_meta_sent"] is True


@pytest.mark.asyncio
async def test_gui_bu_phan_khong_nhay_cam_cho_luot_cu(env):
    db, vault, clock, archiver, _ = env
    for rid, pending in (("cu-1", False), ("cu-2", False), ("dang-cho", True)):
        db.traces._c.insert_one({"request_id": rid, "created_at": T0, "procedure": "khai-sinh",
                                 "procedure_label": "Khai sinh", "timing": {"wall": 1},
                                 "archived_at": T0, "archive_pending": pending})
        db.trace_steps._c.insert_one({"_id": f"{rid}:autofill", "request_id": rid, "created_at": T0,
                                      "spans": [{"i": 0, "a": {"files": 1}}], "archived_at": T0,
                                      "archive_pending": pending})
    db.traces._c.update_one({"request_id": "cu-2"}, {"$set": {"archive_meta_sent": True}})
    db.trace_steps._c.update_one({"request_id": "cu-2"}, {"$set": {"archive_meta_sent": True}})

    result = await archiver.send_meta()
    assert result == {"sent": 1, "failed": 0}
    (bundle,) = vault.bundles
    assert bundle["type"] == "request_meta" and bundle["request_id"] == "cu-1"
    assert bundle["procedure_label"] == "Khai sinh" and bundle["files"] == []
    assert bundle["public"]["traces"][0]["timing"] == {"wall": 1}
    assert "archived_at" not in bundle["public"]["trace_steps"][0]
    assert db.traces._c.find_one({"request_id": "cu-1"})["archive_meta_sent"] is True
    assert "archive_meta_sent" not in db.traces._c.find_one({"request_id": "dang-cho"})
    assert await archiver.send_meta() == {"sent": 0, "failed": 0}


def test_khong_bat_khi_thieu_vault(monkeypatch):
    monkeypatch.setattr(archive_settings, "vault_url", "")
    assert archive_settings.enabled is False
    assert archive_settings.cap_ttl(12 * 3600) == 12 * 3600
    monkeypatch.setattr(archive_settings, "vault_url", "http://v")
    monkeypatch.setattr(archive_settings, "archive_after_minutes", 30)
    assert archive_settings.cap_ttl(12 * 3600) == 1800
    assert worker_mod._SESSION_GRACE == timedelta(minutes=5)


async def test_form_snapshot_cho_gui_lai_va_xoa_sau_han(env):
    db, vault, clock, archiver, _ = env
    db.form_snapshots._c.insert_many([
        {"_id": "s1", "bundle": {"type": "form_snapshot", "id": "s1"}, "created_at": T0},
        {"_id": "s2", "bundle": {"type": "form_snapshot", "id": "s2"}, "created_at": T0 - timedelta(hours=1)},
    ])
    vault.fail = True
    await archiver.run_once("recent")
    assert [d["_id"] for d in db.form_snapshots._c.find()] == ["s1"]
    vault.fail = False
    await archiver.run_once("recent")
    assert db.form_snapshots._c.count_documents({}) == 0
    assert [b["id"] for b in vault.bundles] == ["s1"]
