"""Hồ sơ Auto Fill: một cú bấm nộp tới thành nhiều sự kiện chỉ đếm một; rảnh quá 30 phút thì lượt sau mở hồ sơ mới."""
import asyncio
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app.dossiers import repo


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)

    async def insert_one(self, *a, **kw):
        return self._c.insert_one(*a, **kw)

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)

    async def update_many(self, *a, **kw):
        return self._c.update_many(*a, **kw)

    async def delete_one(self, *a, **kw):
        return self._c.delete_one(*a, **kw)


class _Db:
    def __init__(self):
        self.raw = mongomock.MongoClient().db
        self.dossiers = _AsyncColl(self.raw.dossiers)
        self.traces = _AsyncColl(self.raw.traces)


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(repo, "get_db", lambda: fake)
    return fake


NOW = datetime.now(timezone.utc).replace(microsecond=0)


async def _start(dossier_id="d1", at=NOW, experience="autofill"):
    await repo.upsert_started(dossier_id=dossier_id, user_id="u1", username="cb", name="Cán bộ", procedure="ket-hon",
                              procedure_label="Kết hôn", province="T", ward="X", started_at=at, experience=experience)


def _age(db, dossier_id, minutes):
    """Đẩy lượt làm việc cuối của hồ sơ về quá khứ."""
    db.raw.dossiers.update_one({"_id": dossier_id}, {"$set": {"updated_at": NOW - timedelta(minutes=minutes),
                                                             "started_at": NOW - timedelta(minutes=minutes)}})


async def test_mot_cu_bam_toi_nhieu_ban_sao_chi_dem_mot(db):
    await _start()
    clicked = NOW
    # 25 bộ nghe cú bấm cùng gửi một lúc, mỗi bộ một click_id, giờ bấm lệch nhau vài ms.
    await asyncio.gather(*(repo.add_submit_event(dossier_id="d1", clicked_at=clicked + timedelta(milliseconds=i),
                                                 click_id=f"c{i}", source="click", owner_user_id="u1")
                           for i in range(25)))
    doc = db.raw.dossiers.find_one({"_id": "d1"})
    assert doc["submit_count"] == 1 and len(doc["submit_events"]) == 1


async def test_hai_lan_bam_cach_xa_van_la_hai_lan_nop(db):
    # Chứng thực tách nhiều tab: mỗi tab một cú bấm thật — chuyển tab rồi bấm nhanh nhất cũng gần một giây.
    await _start()
    for i, ms in enumerate((0, 800, 1600, 40000)):
        await repo.add_submit_event(dossier_id="d1", clicked_at=NOW + timedelta(milliseconds=ms), click_id=f"c{i}",
                                    source="click", owner_user_id="u1")
    assert db.raw.dossiers.find_one({"_id": "d1"})["submit_count"] == 4


async def test_moc_do_chu_ngay_sau_cu_bam_khong_bi_chan_boi_luat_cu_bam(db):
    await _start()
    await repo.add_submit_event(dossier_id="d1", clicked_at=NOW, click_id="c1", source="click", owner_user_id="u1")
    await repo.add_submit_event(dossier_id="d1", clicked_at=NOW + timedelta(seconds=1), source="text",
                                owner_user_id="u1", text_dedupe_window=False)
    assert db.raw.dossiers.find_one({"_id": "d1"})["submit_count"] == 2


async def test_ranh_qua_30_phut_luot_sau_mo_ho_so_moi_ho_so_cu_lam_do(db):
    await _start()
    _age(db, "d1", 107)
    old_trace_at = NOW - timedelta(minutes=108)
    db.raw.traces.insert_many([{"_id": "t-cu", "dossier_id": "d1", "created_at": old_trace_at},
                               {"_id": "t-moi", "dossier_id": "d1", "created_at": NOW}])
    await _start(at=NOW)
    new = db.raw.dossiers.find_one({"_id": "d1"})
    assert repo._utc(new["started_at"]) == NOW and "closed_at" not in new
    archived = [d for d in db.raw.dossiers.find() if d["_id"] != "d1"]
    assert len(archived) == 1 and archived[0]["_id"].startswith("d1~")
    assert archived[0]["close_reason"] == "idle" and archived[0].get("submit_clicked_at") is None
    assert repo._utc(archived[0]["closed_at"]) == NOW - timedelta(minutes=107) + repo.AUTOFILL_IDLE
    assert db.raw.traces.find_one({"_id": "t-cu"})["dossier_id"] == archived[0]["_id"]
    assert db.raw.traces.find_one({"_id": "t-moi"})["dossier_id"] == "d1"


async def test_chua_toi_30_phut_hoac_da_nop_hoac_handfree_thi_giu_nguyen(db):
    await _start()
    _age(db, "d1", 29)
    await _start()
    assert db.raw.dossiers.count_documents({}) == 1
    # Đã nộp: extension tự xoay khóa ở lượt sau, BE không tách.
    await _start("d2")
    await repo.add_submit_event(dossier_id="d2", clicked_at=NOW, click_id="c", source="click", owner_user_id="u1")
    _age(db, "d2", 90)
    await _start("d2")
    assert db.raw.dossiers.count_documents({"_id": {"$regex": "^d2~"}}) == 0
    # Handfree có luồng rảnh riêng (xoá phiên) — không tách ở đây.
    await _start("h1", experience="handfree")
    _age(db, "h1", 90)
    await _start("h1", experience="handfree")
    assert db.raw.dossiers.count_documents({"_id": {"$regex": "^h1~"}}) == 0


async def test_hai_luot_song_song_sau_quang_ranh_chi_tach_mot_lan(db):
    await _start()
    _age(db, "d1", 60)
    await asyncio.gather(_start(), _start())
    assert db.raw.dossiers.count_documents({"_id": {"$regex": "^d1~"}}) == 1
    assert db.raw.dossiers.count_documents({"_id": "d1"}) == 1
