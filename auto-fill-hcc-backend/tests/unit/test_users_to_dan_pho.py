"""Tổ dân phố (role "tdp") — tài khoản con của một HCC xã.

Chốt:
- Bắt buộc có xã cha đúng role HCC xã, chưa xóa; tỉnh/xã CHÉP từ cha, không nhận từ form.
- Cha đổi địa bàn → con đổi theo. Cha còn con đang dùng → không xóa, không đổi vai trò.
- Số hồ sơ của tổ dân phố cộng dồn vào xã cha khi xã cha nằm trong phạm vi đếm; tự xem thì
  vẫn là số của chính nó.
Dữ liệu test là giá trị giả.
"""
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.core.errors import AppError
from app.stats import cutover
from app.users import password_vault, service, tdp_rollup
from app.users.schemas import UserCreate, UserUpdate
from app.users.tdp_rollup import TdpRollup


def _match(doc: dict, query: dict) -> bool:
    for key, cond in query.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$in" in cond and value not in cond["$in"]:
                return False
            if "$nin" in cond and value in cond["$nin"]:
                return False
            if "$ne" in cond and value == cond["$ne"]:
                return False
        elif value != cond:
            return False
    return True


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _Users:
    def __init__(self, docs=()):
        self.docs = [dict(d) for d in docs]

    def find(self, query, projection=None):
        return _Cursor(dict(d) for d in self.docs if _match(d, query))

    async def find_one(self, query):
        return next((dict(d) for d in self.docs if _match(d, query)), None)

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _match(d, query))

    async def insert_one(self, doc):
        doc = {"_id": ObjectId(), **doc}
        self.docs.append(doc)
        return type("R", (), {"inserted_id": doc["_id"]})()

    def _apply(self, doc, update):
        doc.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            doc.pop(field, None)

    async def find_one_and_update(self, query, update, return_document=True):
        doc = next((d for d in self.docs if _match(d, query)), None)
        if doc is None:
            return None
        self._apply(doc, update)
        return dict(doc)

    async def update_one(self, query, update):
        doc = next((d for d in self.docs if _match(d, query)), None)
        if doc is not None:
            self._apply(doc, update)
        return type("R", (), {"matched_count": 1 if doc else 0})()

    async def update_many(self, query, update):
        for doc in self.docs:
            if _match(doc, query):
                self._apply(doc, update)


class _Db:
    def __init__(self, users):
        self.users = users
        self.refresh_tokens = type("RT", (), {"update_many": staticmethod(_noop)})()


async def _noop(*_args, **_kwargs):
    return None


XA = ObjectId()
XA_KHAC = ObjectId()
TINH_TK = ObjectId()


@pytest.fixture()
def users(monkeypatch):
    monkeypatch.setattr(password_vault.settings, "password_vault_key", "")
    monkeypatch.setattr(password_vault, "hash_password", lambda p: f"hash::{p}")
    store = _Users([
        {"_id": XA, "username": "hccxa", "name": "HCC xã A", "role": "commune",
         "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Vũ Ninh"},
        {"_id": XA_KHAC, "username": "hccxab", "name": "HCC xã B", "role": "commune",
         "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Kinh Bắc"},
        {"_id": TINH_TK, "username": "hcctinh", "role": "province", "tinh": "Tỉnh Bắc Ninh"},
    ])
    monkeypatch.setattr(service, "get_db", lambda: _Db(store))
    return store


async def _tao_tdp(users, parent=XA, **extra):
    return await service.create_user(UserCreate(
        username="tdpcome", password="MatKhau#123", role="tdp", parent_id=str(parent), **extra,
    ))


async def test_tao_tdp_chep_dia_ban_cua_cha(users):
    out = await _tao_tdp(users, tinh="Tỉnh Khác", xa="Xã Khác")
    doc = next(d for d in users.docs if d["username"] == "tdpcome")
    assert (doc["tinh"], doc["xa"], doc["parent_id"]) == ("Tỉnh Bắc Ninh", "Phường Vũ Ninh", str(XA))
    assert out["parent"]["username"] == "hccxa"


async def test_tao_tdp_khong_co_cha_hoac_cha_sai_role(users):
    with pytest.raises(AppError) as exc:
        await service.create_user(UserCreate(username="tdp1", password="MatKhau#123", role="tdp"))
    assert exc.value.error == "TDP_PARENT_REQUIRED"
    with pytest.raises(AppError) as exc:
        await _tao_tdp(users, parent=TINH_TK)
    assert exc.value.error == "TDP_PARENT_INVALID"


async def test_role_khac_bo_qua_parent_id(users):
    out = await service.create_user(UserCreate(
        username="nguoidung", password="MatKhau#123", role="user", parent_id=str(XA),
    ))
    assert out["parent_id"] is None
    assert "parent_id" not in next(d for d in users.docs if d["username"] == "nguoidung")


async def test_cha_doi_dia_ban_thi_con_doi_theo(users, monkeypatch):
    await _tao_tdp(users)
    monkeypatch.setattr(service, "canonical_location", lambda t, x: (t, x))
    await service.update_user(str(XA), UserUpdate(xa="Phường Mới"), str(ObjectId()))
    child = next(d for d in users.docs if d["username"] == "tdpcome")
    assert child["xa"] == "Phường Mới"


async def test_doi_cha_chep_lai_dia_ban(users):
    out = await _tao_tdp(users)
    await service.update_user(out["id"], UserUpdate(parent_id=str(XA_KHAC)), str(ObjectId()))
    child = next(d for d in users.docs if d["username"] == "tdpcome")
    assert (child["parent_id"], child["xa"]) == (str(XA_KHAC), "Phường Kinh Bắc")


async def test_chan_xoa_va_doi_role_cha_khi_con_con_dung(users):
    await _tao_tdp(users)
    with pytest.raises(AppError) as exc:
        await service.delete_user(str(XA), str(ObjectId()))
    assert exc.value.error == "HAS_CHILD_ACCOUNTS"
    with pytest.raises(AppError) as exc:
        await service.update_user(str(XA), UserUpdate(role="user"), str(ObjectId()))
    assert exc.value.error == "HAS_CHILD_ACCOUNTS"


async def test_doi_tdp_sang_role_khac_go_cha(users):
    out = await _tao_tdp(users)
    result = await service.update_user(out["id"], UserUpdate(role="user"), str(ObjectId()))
    assert result["parent_id"] is None
    assert "parent_id" not in next(d for d in users.docs if d["username"] == "tdpcome")


async def test_khong_nhan_chinh_minh_lam_cha(users):
    with pytest.raises(AppError) as exc:
        await service.update_user(
            str(XA), UserUpdate(role="tdp", parent_id=str(XA)), str(ObjectId()),
        )
    assert exc.value.error == "TDP_PARENT_INVALID"


async def test_danh_sach_cha_chi_hcc_xa(users):
    items = await service.list_parent_accounts()
    assert {item["username"] for item in items} == {"hccxa", "hccxab"}


# ---------- cộng dồn số liệu ----------

LINKS = {"tdp1": {"parentId": "xa1", "parentName": "HCC xã A"}}


def test_rollup_chi_gop_khi_cha_trong_pham_vi():
    assert TdpRollup(LINKS, ["xa1"]).unit("tdp1") == "xa1"
    assert TdpRollup(LINKS, None).unit("tdp1") == "xa1"
    assert TdpRollup(LINKS, ["tdp1"]).unit("tdp1") == "tdp1"   # tổ dân phố tự xem
    assert TdpRollup(LINKS, ["xa1", "xa2"]).expand(["xa1", "xa2"]) == ["xa1", "xa2", "tdp1"]
    assert TdpRollup(LINKS, ["xa2"]).expand(["xa2"]) == ["xa2"]


def test_rollup_gop_ward_vao_cha():
    stats = {
        "wards": [
            {"userId": "tdp1", "name": "TDP", "role": "tdp", "total": 2, "exact": 2,
             "estimated": 0, "requests": 5,
             "procedures": [{"key": "khai-sinh", "label": "KS", "count": 2, "requests": 5}]},
            {"userId": "xa1", "name": "HCC xã A", "role": "commune", "total": 3, "exact": 3,
             "estimated": 0, "requests": 4,
             "procedures": [{"key": "khai-sinh", "label": "KS", "count": 1, "requests": 1},
                            {"key": "ket-hon", "label": "KH", "count": 2, "requests": 3}]},
        ],
        "totalDossiers": 5,
    }
    out = TdpRollup(LINKS, None).stats(stats)
    assert len(out["wards"]) == 1
    ward = out["wards"][0]
    assert (ward["userId"], ward["name"], ward["role"]) == ("xa1", "HCC xã A", "commune")
    assert (ward["total"], ward["requests"]) == (5, 9)
    by_key = {p["key"]: p["count"] for p in ward["procedures"]}
    assert by_key == {"khai-sinh": 3, "ket-hon": 2}
    assert out["totalDossiers"] == 5


async def test_dossier_stats_cong_don_ho_so_nop_cua_tdp(monkeypatch):
    async def links():
        return LINKS

    seen = {}

    async def fake_traces(*, user_ids, date_from, date_to, experience):
        seen.setdefault("traces", user_ids)
        return {"wards": [], "procedures": [], "totalDossiers": 0}

    async def fake_submitted(*, user_ids, date_from, date_to, experience):
        seen["submitted"] = user_ids
        rows = [
            {"userId": "xa1", "procedure": "khai-sinh", "label": "KS", "name": "HCC xã A", "count": 1},
            {"userId": "tdp1", "procedure": "khai-sinh", "label": "KS", "name": "TDP", "count": 2},
        ]
        return [row for row in rows if row["userId"] in user_ids]

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", links)
    monkeypatch.setattr(cutover.traces_repo, "stats_by_user_ids", fake_traces)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_counts", fake_submitted)
    start = datetime(2026, 9, 20, tzinfo=timezone.utc)
    end = datetime(2026, 9, 30, tzinfo=timezone.utc)

    result = await cutover.dossier_stats(user_ids=["xa1"], date_from=start, date_to=end)
    assert seen["submitted"] == ["xa1", "tdp1"]
    assert [(w["userId"], w["total"]) for w in result["wards"]] == [("xa1", 3)]
    assert result["totalDossiers"] == 3

    own = await cutover.dossier_stats(user_ids=["tdp1"], date_from=start, date_to=end)
    assert [(w["userId"], w["total"]) for w in own["wards"]] == [("tdp1", 2)]


async def test_daily_counts_cong_don(monkeypatch):
    async def links():
        return LINKS

    async def fake_daily(*, user_ids, date_from, date_to, experience):
        return [
            {"userId": "xa1", "date": "2026-09-21", "count": 1},
            {"userId": "tdp1", "date": "2026-09-21", "count": 4},
        ]

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", links)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_daily_counts", fake_daily)
    rows = await cutover.daily_dossier_counts(
        user_ids=["xa1"],
        date_from=datetime(2026, 9, 20, tzinfo=timezone.utc),
        date_to=datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    assert rows == [{"userId": "xa1", "date": "2026-09-21", "count": 5}]
