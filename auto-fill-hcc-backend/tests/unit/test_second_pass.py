"""Điền đợt 2: lượt điền đầu giữ nguyên, lượt soát chạy nền, extension hỏi lấy các ô cần ghi lại."""
import asyncio
from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.pipelines._shared.thanh_tra import ban_va
from app.pipelines._shared.thanh_tra.ho_so import Result
from app.pipelines.xac_nhan_tthn_dvc_moi.process import mapper
from app.pipelines.xac_nhan_tthn_dvc_moi.process import runner as hon_nhan_runner
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dot_hai
from app.process import router as process_router
from app.second_pass import router as second_pass_router
from app.second_pass import service
from app.services import ocr
from app.services.llm import client


class _AsyncColl:
    def __init__(self, coll):
        self.raw = coll

    async def insert_one(self, *a, **kw):
        return self.raw.insert_one(*a, **kw)

    async def update_one(self, *a, **kw):
        return self.raw.update_one(*a, **kw)

    async def find_one(self, *a, **kw):
        return self.raw.find_one(*a, **kw)


class _AsyncDb:
    def __init__(self):
        raw = mongomock.MongoClient().db
        self.second_pass = _AsyncColl(raw.second_pass)
        self.process_requests = _AsyncColl(raw.process_requests)


@pytest.fixture
def db(monkeypatch):
    fake = _AsyncDb()
    monkeypatch.setattr(service, "get_db", lambda: fake)
    monkeypatch.setattr(service, "_KEEP_WAIT_SECONDS", 0)
    return fake


async def _drain():
    while service._running:
        await asyncio.gather(*list(service._running), return_exceptions=True)


# ---- công tắc ----

@pytest.mark.parametrize("enabled, supports, pilot, username, expected", [
    (False, True, "", "quay1", False),
    (True, False, "", "quay1", False),
    (True, True, "", "quay1", True),
    (True, True, "quay2, quay3", "quay1", False),
    (True, True, "quay2, quay1", "quay1", True),
])
def test_chi_chay_khi_be_bat_extension_khai_va_tai_khoan_thuoc_dien_thi_diem(
        monkeypatch, enabled, supports, pilot, username, expected):
    monkeypatch.setattr(settings, "second_pass_enabled", enabled)
    monkeypatch.setattr(settings, "second_pass_usernames", pilot)
    assert service.wanted({"username": username}, supports) is expected


# ---- bản vá ----

def test_ban_va_chi_gom_o_duoc_phep_co_gia_tri_khac_luot_dau():
    before = [{"name": "a", "comp": "sjs-text", "value": "1"}, {"name": "b", "comp": "sjs-text", "value": "2"},
              {"name": "c", "comp": "sjs-text", "value": "3"}, {"name": "gone", "comp": "sjs-text", "value": "x"}]
    after = [{"name": "a", "comp": "sjs-text", "value": "1"}, {"name": "b", "comp": "sjs-text", "value": "20"},
             {"name": "c", "comp": "sjs-text", "value": "30"}, {"name": "new", "comp": "sjs-text", "value": "9"}]
    assert ban_va.diff(before, after, {"a", "b", "new", "gone"}) == [
        {"name": "b", "comp": "sjs-text", "value": "20", "from": "2"},
        {"name": "new", "comp": "sjs-text", "value": "9", "from": None},
    ]


def test_o_con_di_kem_khi_o_cha_doi():
    before = [{"name": "tinh", "value": "A"}, {"name": "xa", "value": "X"}, {"name": "chi_tiet", "value": "1"}]
    after = [{"name": "tinh", "value": "B"}, {"name": "xa", "value": "X"}, {"name": "chi_tiet", "value": "1"}]
    names = {"tinh", "xa", "chi_tiet"}
    assert [f["name"] for f in ban_va.diff(before, after, names, follows={"xa": "tinh"})] == ["tinh", "xa"]
    assert ban_va.diff(before, before, names, follows={"xa": "tinh"}) == []


_OTHER = {"formContext": {"applicantFullname": "Lê Thị Nộp Hộ", "applicantIdentityNumber": "001190000002"}}
_RAW = {
    "NguoiDuocCap_HoTen": "Trần Văn Mẫu", "NguoiDuocCap_SoDinhDanh": "001080000001",
    "NguoiDuocCap_NgaySinh": "02/03/1980", "TinhTrangHonNhan": "Vợ đã chết",
    "DeathCert_Number": "15/2024/TLKT-BS", "DeathCert_Date": "04/05/2024", "DeathCert_Agency": "UBND xã Mẫu",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _first_fill(values: dict, options: dict) -> list[dict]:
    return mapper.enrich(_fields(values), options)[0]


def _fake_review(monkeypatch, changes: dict):
    async def review(documents, context, values, options=None):
        return Result({**values, **changes}, [{"outcome": "sua"}], {"inspect_ms": 1})
    monkeypatch.setattr(dot_hai, "review", review)


async def test_o_lop_soat_sua_ra_ban_va_kem_gia_tri_luot_dau(monkeypatch):
    _fake_review(monkeypatch, {"DeathCert_Number": "07/2009", "NguoiDuocCap_HoTen": "Trần Văn Mầu"})
    base = _first_fill(_RAW, _OTHER)
    out = await dot_hai.patch([{"name": "a", "text": "x"}], "", _fields(_RAW), base, _OTHER)
    got = {f["name"]: (f["value"], f["from"]) for f in out["fields"]}
    assert got == {
        "citizenNDKHochudemtenngdccap": ("TRẦN VĂN MẦU", "TRẦN VĂN MẪU"),
        "citizenSogiaychungtuTrichluckhaituBanan": ("07/2009", "15/2024/TLKT-BS"),
    }
    assert out["fields"][0]["comp"] == "sjs-text" and out["fields"][0]["lookup"] is True
    assert [f["by"] for f in out["fields"]] == ["dinh_danh", "giay_ho_tich"]
    assert out["rulings"] == [{"outcome": "sua"}]


async def test_lop_soat_khong_doi_gi_thi_ban_va_rong(monkeypatch):
    _fake_review(monkeypatch, {})
    out = await dot_hai.patch([], "", _fields(_RAW), _first_fill(_RAW, _OTHER), _OTHER)
    assert out["fields"] == []


async def test_quan_he_doi_thi_khong_va_gi(monkeypatch):
    # Tên + số định danh sau soát trùng chủ tài khoản → mapper chuyển sang "Bản thân", form đổi bố cục.
    _fake_review(monkeypatch, {"NguoiDuocCap_HoTen": "Lê Thị Nộp Hộ", "NguoiDuocCap_SoDinhDanh": "001190000002",
                               "DeathCert_Number": "07/2009"})
    out = await dot_hai.patch([], "", _fields(_RAW), _first_fill(_RAW, _OTHER), _OTHER)
    assert out["fields"] == []


async def test_tinh_trang_hon_nhan_doi_thi_bo_cum_giay_ho_tich_nhung_van_va_o_khac(monkeypatch):
    raw = {k: v for k, v in _RAW.items() if not k.startswith("DeathCert_")} | {"TinhTrangHonNhan": "Chưa đăng ký kết hôn"}
    _fake_review(monkeypatch, {"DeathCert_Number": "07/2009", "DeathCert_Date": "01/02/2009",
                               "NguoiDuocCap_NgaySinh": "03/03/1980"})
    out = await dot_hai.patch([], "", _fields(raw), _first_fill(raw, _OTHER), _OTHER)
    assert [f["name"] for f in out["fields"]] == ["citizenNDKNgaythangnamsinh"]


# ---- chạy nền + hỏi kết quả ----

async def test_luot_soat_xong_thi_hoi_ra_ban_va_va_luu_canh_ket_qua_luot_dau(db, monkeypatch):
    monkeypatch.setattr(settings, "second_pass_max_running", 3)
    db.process_requests.raw.insert_one({"request_id": "req_1", "fields": [{"name": "a", "value": "1"}]})
    gate = asyncio.Event()

    async def run(base_fields):
        await gate.wait()
        return {"fields": [{"name": "a", "comp": "sjs-text", "value": "2", "from": base_fields[0]["value"]}],
                "rulings": [{"outcome": "sua"}], "timing": {"inspect_ms": 5}}

    assert await service.start("req_1", "u1", run, [{"name": "a", "value": "1"}]) is True
    assert await service.result("req_1", "u1") == {"status": "pending"}
    gate.set()
    await _drain()
    assert await service.result("req_1", "u1") == {
        "status": "done", "fields": [{"name": "a", "comp": "sjs-text", "value": "2", "from": "1"}]}
    assert await service.result("req_1", "u2") == {"status": "none"}  # tài khoản khác không đọc được
    kept = db.process_requests.raw.find_one({"request_id": "req_1"})
    assert kept["fields"] == [{"name": "a", "value": "1"}]  # kết quả lượt đầu giữ nguyên
    assert kept["second_pass"]["status"] == "done" and kept["second_pass"]["rulings"] == [{"outcome": "sua"}]


async def test_luot_soat_loi_hoac_qua_han_thi_coi_nhu_khong_co(db, monkeypatch):
    monkeypatch.setattr(settings, "second_pass_timeout_seconds", 0.01)

    async def broken(base_fields):
        raise RuntimeError("LLM 502")

    async def slow(base_fields):
        await asyncio.sleep(1)

    assert await service.start("req_loi", "u1", broken, [])
    assert await service.start("req_cham", "u1", slow, [])
    await _drain()
    assert await service.result("req_loi", "u1") == {"status": "none"}
    assert await service.result("req_cham", "u1") == {"status": "none"}
    assert db.second_pass.raw.find_one({"_id": "req_cham"})["reason"] == "timeout"


async def test_qua_tai_thi_bo_dot_hai_va_ban_ghi_ket_pending_thi_het_han(db, monkeypatch):
    monkeypatch.setattr(settings, "second_pass_max_running", 0)

    async def run(base_fields):
        return {"fields": []}

    assert await service.start("req_2", "u1", run, []) is False
    assert await service.result("req_2", "u1") == {"status": "none"}
    # Worker chết giữa chừng: bản ghi còn "pending" nhưng đã quá hạn chạy.
    stale = datetime.now(timezone.utc) - timedelta(seconds=settings.second_pass_timeout_seconds + 60)
    db.second_pass.raw.insert_one({"_id": "req_3", "user_id": "u1", "status": "pending", "at": stale})
    assert await service.result("req_3", "u1") == {"status": "none"}


def test_endpoint_tra_ket_qua_theo_tai_khoan_dang_nhap(db):
    db.second_pass.raw.insert_one({"_id": "req_9", "user_id": "u1", "status": "done", "at": datetime.now(timezone.utc),
                                   "fields": [{"name": "a", "value": "2", "from": "1"}], "rulings": [{"x": 1}]})
    app = FastAPI()
    app.include_router(second_pass_router.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1"}
    body = TestClient(app).get("/api/v1/process/req_9/second-pass").json()
    assert body == {"status": "done", "fields": [{"name": "a", "value": "2", "from": "1"}]}  # không lộ biên bản
    app.dependency_overrides[require_auth] = lambda: {"id": "u2"}
    assert TestClient(app).get("/api/v1/process/req_9/second-pass").json() == {"status": "none"}


# ---- /process: bản extension cũ không đổi gì ----

@pytest.fixture
def process_env(monkeypatch):
    seen = {"options": [], "started": []}

    async def pipeline(files_by_role, options):
        seen["options"].append(dict(options))
        result = {"fields": [{"name": "a", "comp": "sjs-text", "value": "1"}], "extracted": {}, "stats": {}, "errors": []}
        if options.get("_secondPass"):
            result["_second_pass"] = "lượt soát"
        return result

    async def noop(*args, **kwargs):
        return "doc-1"

    async def start(request_id, user_id, run, base_fields):
        seen["started"].append((request_id, user_id, run, base_fields))
        return True

    monkeypatch.setattr(process_router, "get_procedure", lambda key: {"label": "Thủ tục test", "mode": "agent"})
    monkeypatch.setattr(process_router, "get_pipeline", lambda key: pipeline)
    monkeypatch.setattr(process_router, "save_request_files", lambda *a, **k: [])
    monkeypatch.setattr(process_router.requests_repo, "create_request", noop)
    monkeypatch.setattr(process_router.requests_repo, "finish_request", noop)
    monkeypatch.setattr(process_router.audit, "log_request", noop)
    monkeypatch.setattr(process_router, "_touch_dossier", noop)
    monkeypatch.setattr(process_router.traces_repo, "create_trace", noop)
    monkeypatch.setattr(process_router.monitor_persist, "schedule", lambda rec, rid: None)
    monkeypatch.setattr(process_router.second_pass, "start", start)
    monkeypatch.setattr(settings, "second_pass_enabled", True)
    monkeypatch.setattr(settings, "second_pass_usernames", "")
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(process_router.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "username": "quay1", "name": "Quầy 1"}
    seen["client"] = TestClient(app)
    return seen


def _body(options: dict) -> dict:
    return {"procedure": "thu-tuc-test", "options": options,
            "files": [{"name": "cccd.png", "type": "image/png", "role": "doc", "dataUrl": "data:image/png;base64,QUJD"}]}


def test_extension_cu_khong_khai_thi_khong_chay_dot_hai_va_response_y_nguyen(process_env):
    old = process_env["client"].post("/api/v1/process", json=_body({})).json()
    # Client tự gửi khoá nội bộ cũng không bật được.
    forged = process_env["client"].post("/api/v1/process", json=_body({"_secondPass": True})).json()
    new = process_env["client"].post("/api/v1/process", json=_body({"fillSupports": ["secondPass"]})).json()
    assert [o["_secondPass"] for o in process_env["options"]] == [False, False, True]
    assert len(process_env["started"]) == 1
    request_id, user_id, run, base_fields = process_env["started"][0]
    assert (request_id, user_id, run) == (new["requestId"], "u1", "lượt soát")
    assert base_fields == [{"name": "a", "comp": "sjs-text", "value": "1"}]
    for body in (old, forged, new):
        body.pop("sessionId"), body.pop("requestId")
    assert old == forged == new  # lượt điền đầu giống hệt nhau, có hay không có đợt 2


# ---- runner hôn nhân ----

async def test_runner_hon_nhan_chi_kem_luot_soat_khi_duoc_yeu_cau(monkeypatch):
    async def fake_uncached(files, classify=False):
        return [{"name": f.get("name"), "text": "TỜ KHAI\nHọ, chữ đệm, tên: TRẦN VĂN MẪU", "provider": "tiengnoi"}
                for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return '{"fields": {"NguoiDuocCap_HoTen": "Trần Văn Mẫu"}}'

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    files = {"": [{"name": "to-khai.png", "type": "image/png", "dataUrl": "data:image/png;base64,QUJD"}]}
    plain = await hon_nhan_runner.run(files, {})
    wanted = await hon_nhan_runner.run(files, {"_secondPass": True})
    assert "_second_pass" not in plain
    assert callable(wanted.pop("_second_pass"))
    assert plain["fields"] == wanted["fields"]
