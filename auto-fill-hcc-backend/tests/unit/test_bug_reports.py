"""Báo lỗi trên web thống kê: quyền theo vai trò, mã lỗi, ảnh, xoá mềm, nhật ký xử lý."""
import io
from datetime import datetime, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.bug_reports import repo, rules
from app.bug_reports import router as bug_router
from app.config import settings
from app.core.deps import require_dashboard
from app.core.errors import AppError, app_error_handler
from app.dossiers import repo as dossiers_repo
from app.users import tdp_rollup

WARD_A = {"_id": "ua", "username": "pbg", "name": "HCC Phường Bắc Giang", "role": "commune",
          "tinh": "Tỉnh T", "xa": "Phường Bắc Giang"}
WARD_B = {"_id": "ub", "username": "xpb", "name": "HCC Xã Phú Bình", "role": "commune",
          "tinh": "Tỉnh T", "xa": "Xã Phú Bình"}
WARD_C = {"_id": "uc", "username": "xpba", "name": "HCC Xã Phú Bài", "role": "commune",
          "tinh": "Tỉnh K", "xa": "Xã Phú Bài"}
TDP = {"_id": "ut", "username": "tdp1", "name": "Tổ 1", "role": "tdp", "parent_id": "ua",
       "tinh": "Tỉnh T", "xa": "Phường Bắc Giang"}
PROVINCE = {"_id": "pt", "username": "tinh", "name": "Tỉnh T", "role": "province_admin", "tinh": "Tỉnh T"}
ADMIN = {"_id": "ad", "username": "admin", "name": "Admin", "role": "admin"}


def _unit(user):
    return {"unitId": user["_id"], "name": user["name"], "xa": user.get("xa"), "tinh": user.get("tinh"),
            "role": user["role"]}


def _scope(user):
    if user["role"] == "admin":
        return {"scopeKind": "all", "units": [_unit(u) for u in (WARD_A, WARD_B, WARD_C)], "self": _unit(user)}
    if user["role"] == "province_admin":
        return {"scopeKind": "province", "units": [_unit(WARD_A), _unit(WARD_B)], "self": _unit(user)}
    return {"scopeKind": "unit", "units": [_unit(user)], "self": _unit(user)}


class _Cursor:
    def __init__(self, cursor):
        self._c = cursor

    def sort(self, *a, **kw):
        self._c = self._c.sort(*a, **kw)
        return self

    def skip(self, n):
        self._c = self._c.skip(n)
        return self

    def limit(self, n):
        self._c = self._c.limit(n)
        return self

    async def to_list(self, length=None):
        return list(self._c)

    def __aiter__(self):
        self._it = iter(self._c)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None


class _Coll:
    def __init__(self, coll):
        self._c = coll

    def find(self, *a, **kw):
        return _Cursor(self._c.find(*a, **kw))

    def aggregate(self, pipeline):
        return _Cursor(iter(self._c.aggregate(pipeline)))

    def __getattr__(self, name):
        method = getattr(self._c, name)

        async def call(*a, **kw):
            return method(*a, **kw)

        return call


class _Db:
    def __init__(self):
        self.raw = mongomock.MongoClient(tz_aware=True).db

    def __getattr__(self, name):
        return _Coll(self.raw[name])


@pytest.fixture()
def db(monkeypatch, tmp_path):
    fake = _Db()
    for module in (repo, dossiers_repo, tdp_rollup):
        monkeypatch.setattr(module, "get_db", lambda: fake)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    async def _links():
        return {"ut": {"parentId": "ua", "parentName": WARD_A["name"]}}

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", _links)
    fake.raw.dossiers.insert_many([
        {"_id": "d-a1", "user_id": "ua", "procedure": "khai_sinh", "procedure_label": "Đăng ký khai sinh",
         "started_at": datetime(2026, 11, 3, 2, 0, tzinfo=timezone.utc), "experience": "autofill"},
        {"_id": "d-t1", "user_id": "ut", "procedure": "ket_hon", "procedure_label": "Đăng ký kết hôn",
         "started_at": datetime(2026, 11, 4, 2, 0, tzinfo=timezone.utc), "experience": "handfree"},
        {"_id": "d-b1", "user_id": "ub", "procedure": "khai_tu", "procedure_label": "Đăng ký khai tử",
         "started_at": datetime(2026, 11, 4, 3, 0, tzinfo=timezone.utc), "experience": "autofill"},
    ])
    fake.raw.traces.insert_one({"dossier_id": "d-a1", "request_id": "req_123", "kind": "autofill",
                                "created_at": datetime(2026, 11, 3, 2, 1, tzinfo=timezone.utc)})
    return fake


@pytest.fixture()
def as_user(db, monkeypatch):
    current = {"user": WARD_A}

    async def _resolve(user):
        return _scope(user)

    monkeypatch.setattr(bug_router, "resolve_dashboard_scope", _resolve)
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(bug_router.router)
    app.dependency_overrides[require_dashboard] = lambda: current["user"]
    client = TestClient(app)

    def _switch(user):
        current["user"] = user
        return client

    return _switch


def _png(color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(buf, format="PNG")
    return buf.getvalue()


def _send(client, text="Nộp hồ sơ bị lỗi 500. Thử lại vẫn vậy.", dossier=None, images=()):
    data = {"text": text}
    if dossier:
        data["dossierId"] = dossier
    files = [("files", (f"a{i}.png", raw, "image/png")) for i, raw in enumerate(images)]
    return client.post("/api/v1/bug-reports", data=data, files=files or None)


def test_ma_loi_lay_chu_dau_ten_xa_bo_cap_hanh_chinh():
    assert rules.code_prefix("Phường Bắc Giang") == "BG"
    assert rules.code_prefix("Xã Phú Bình") == "PB"
    assert rules.code_prefix("Thị trấn Đông Anh") == "DA"
    assert rules.code_prefix(None, None) == "HCC"
    assert rules.format_code("BG", 3) == "BG-03"


def test_ten_loi_la_cau_dau_cat_gon():
    assert rules.make_title("Biểu đồ trống. Các tháng khác vẫn có.", None) == "Biểu đồ trống"
    long = "Danh sách nhật ký hồ sơ tải rất lâu vào đầu giờ chiều có lúc không hiện gì cả trên máy"
    title = rules.make_title(long, None)
    assert title.endswith("...") and len(title) <= 73 and not title[:-3].endswith(" ")
    assert rules.make_title("", "Đăng ký khai sinh") == "Lỗi thủ tục Đăng ký khai sinh"
    assert rules.make_title("", None) == "Lỗi kèm ảnh"


def test_phuong_xa_gui_loi_kem_anh_va_ho_so(as_user):
    client = as_user(WARD_A)
    res = _send(client, dossier="d-a1", images=[_png(), _png((0, 0, 200))])
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["code"] == "BG-01"
    assert body["title"] == "Nộp hồ sơ bị lỗi 500"
    assert body["status"] == "new"
    assert body["imageCount"] == 2
    assert body["dossier"]["procedureLabel"] == "Đăng ký khai sinh"
    img = client.get(f"/api/v1/bug-reports/{body['id']}/images/1")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert _send(client).json()["code"] == "BG-02"


def test_hai_xa_trung_chu_dau_khong_trung_ma(as_user):
    assert _send(as_user(WARD_B)).json()["code"] == "PB-01"
    assert _send(as_user(WARD_C)).json()["code"] == "PB-02"


def test_ho_so_cua_to_dan_pho_gan_duoc_va_loi_tinh_ve_xa_cha(as_user, db):
    assert _send(as_user(WARD_A), dossier="d-t1").status_code == 200
    res = _send(as_user(TDP))
    assert res.status_code == 200
    assert db.raw.bug_reports.find_one({"code": res.json()["code"]})["unit_id"] == "ua"


def test_ho_so_cua_don_vi_khac_bi_tu_choi(as_user):
    res = _send(as_user(WARD_A), dossier="d-b1")
    assert res.status_code == 400
    assert res.json()["error"] == "BUG_DOSSIER_NOT_FOUND"


@pytest.mark.parametrize("kwargs,error", [
    ({"text": "  ", "images": ()}, "BUG_EMPTY"),
    ({"images": [b"not an image"]}, "BUG_IMAGE_INVALID"),
    ({"images": [_png()] * 11}, "BUG_TOO_MANY_IMAGES"),
])
def test_tu_choi_gui_sai(as_user, db, kwargs, error):
    res = _send(as_user(WARD_A), **kwargs)
    assert res.status_code == 400
    assert res.json()["error"] == error
    assert db.raw.bug_reports.count_documents({}) == 0


def test_ho_so_gan_nhat_chi_cua_minh_va_to_dan_pho(as_user):
    items = as_user(WARD_A).get("/api/v1/bug-reports/recent-dossiers").json()["items"]
    assert [i["dossierId"] for i in items] == ["d-t1", "d-a1"]
    assert as_user(PROVINCE).get("/api/v1/bug-reports/recent-dossiers").status_code == 403


def test_tinh_chi_xem_danh_sach_rut_gon_trong_tinh(as_user):
    _send(as_user(WARD_A), dossier="d-a1", images=[_png()])
    _send(as_user(WARD_C))
    client = as_user(PROVINCE)
    body = client.get("/api/v1/bug-reports").json()
    assert body["access"] == "viewer"
    assert [i["code"] for i in body["items"]] == ["BG-01"]
    assert set(body["items"][0]) == {"id", "code", "title", "status", "createdAt", "procedureLabel", "unitName"}
    report_id = body["items"][0]["id"]
    assert client.get(f"/api/v1/bug-reports/{report_id}").status_code == 403
    assert client.get(f"/api/v1/bug-reports/{report_id}/images/0").status_code == 403
    assert client.patch(f"/api/v1/bug-reports/{report_id}", json={"status": "done"}).status_code == 403
    assert _send(client).status_code == 403


def test_phuong_xa_khong_xem_duoc_loi_cua_xa_khac(as_user):
    report_id = _send(as_user(WARD_A), images=[_png()]).json()["id"]
    client = as_user(WARD_B)
    assert client.get("/api/v1/bug-reports").json()["items"] == []
    assert client.get(f"/api/v1/bug-reports/{report_id}").status_code == 404
    assert client.get(f"/api/v1/bug-reports/{report_id}/images/0").status_code == 404
    assert client.delete(f"/api/v1/bug-reports/{report_id}").status_code == 404


def test_admin_doi_trang_thai_sua_ten_co_nhat_ky(as_user):
    report_id = _send(as_user(WARD_A), dossier="d-a1").json()["id"]
    client = as_user(ADMIN)
    res = client.patch(f"/api/v1/bug-reports/{report_id}", json={"status": "doing", "title": "Lỗi 500 khi nộp"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "doing" and body["title"] == "Lỗi 500 khi nộp"
    assert [e["action"] for e in body["log"]] == ["create", "title", "status"]
    assert body["log"][-1]["to"] == "doing" and body["log"][-1]["by"] == "Admin"
    assert body["requests"] == [{"requestId": "req_123", "kind": "autofill", "at": "2026-11-03T02:01:00+00:00"}]
    assert body["unitName"] == "Phường Bắc Giang" and body["province"]
    assert client.patch(f"/api/v1/bug-reports/{report_id}", json={"title": "  "}).status_code == 400
    # Phường/xã không đổi được trạng thái.
    assert as_user(WARD_A).patch(f"/api/v1/bug-reports/{report_id}", json={"status": "done"}).status_code == 403


def test_admin_loc_theo_tinh_trang_thai_va_tu_khoa(as_user):
    _send(as_user(WARD_A), text="Biểu đồ trống")
    _send(as_user(WARD_C), text="Không tải được tệp")
    client = as_user(ADMIN)
    body = client.get("/api/v1/bug-reports").json()
    assert body["total"] == 2
    assert {p["count"] for p in body["counts"]["provinces"]} == {1}
    province = next(i["province"] for i in body["items"] if i["code"] == "PB-01")
    only = client.get("/api/v1/bug-reports", params={"province": province}).json()
    assert [i["code"] for i in only["items"]] == ["PB-01"]
    assert only["counts"]["status"] == {"new": 1, "doing": 0, "done": 0}
    assert client.get("/api/v1/bug-reports", params={"q": "tệp"}).json()["total"] == 1
    assert client.get("/api/v1/bug-reports", params={"status": "done"}).json()["total"] == 0


def test_xoa_mem_moi_trang_thai_va_an_khoi_moi_danh_sach(as_user, db):
    report_id = _send(as_user(WARD_A), images=[_png()]).json()["id"]
    as_user(ADMIN).patch(f"/api/v1/bug-reports/{report_id}", json={"status": "done"})
    client = as_user(WARD_A)
    assert client.delete(f"/api/v1/bug-reports/{report_id}").status_code == 200
    assert client.get("/api/v1/bug-reports").json()["total"] == 0
    assert as_user(ADMIN).get("/api/v1/bug-reports").json()["total"] == 0
    doc = db.raw.bug_reports.find_one({})
    assert doc["deleted_at"] is not None and doc["log"][-1]["action"] == "delete"
    assert len(doc["images"]) == 1, "ảnh giữ lại sau khi xoá"


def test_so_tren_menu_theo_vai_tro(as_user):
    first = _send(as_user(WARD_A)).json()["id"]
    _send(as_user(WARD_A))
    as_user(ADMIN).patch(f"/api/v1/bug-reports/{first}", json={"status": "done"})
    assert as_user(WARD_A).get("/api/v1/bug-reports/summary").json() == {
        "access": "reporter", "total": 2, "open": 1, "new": 1}
    assert as_user(PROVINCE).get("/api/v1/bug-reports/summary").json()["access"] == "viewer"
    assert as_user(ADMIN).get("/api/v1/bug-reports/summary").json()["new"] == 1
