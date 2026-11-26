"""Biên bản làm việc (web thống kê): phạm vi theo tài khoản, số liệu hệ thống, bản nháp lưu DB, xuất Word."""
import io

import pytest
from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_dashboard
from app.core.errors import AppError, app_error_handler
from app.work_minutes import repo, rules
from app.work_minutes import router as minutes_router
from tests.unit.test_bug_reports import ADMIN, PROVINCE, WARD_A, WARD_C, _Db, _scope

TODAY = "2026-11-18"


@pytest.fixture()
def as_user(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(repo, "get_db", lambda: fake)

    async def _resolve(user):
        return _scope(user)

    async def _af(*, user_ids, date_from, date_to, experience):
        return {"wards": [{"userId": u, "procedures": [
            {"key": "ket-hon", "label": "Đăng ký kết hôn", "count": 3},
            {"key": "chung-thuc-ban-sao", "label": "Chứng thực bản sao", "count": 5},
        ]} for u in user_ids]}

    async def _hf(units, date_from, date_to, *, want_daily):
        key = minutes_router.account_unit_key(units[0].get("tinh"), units[0].get("xa"), units[0]["unitId"])
        return {key: {"procedures": [{"procedureKey": "ket-hon", "label": "Kết hôn", "count": 4}]}}, {}, True

    monkeypatch.setattr(minutes_router, "resolve_dashboard_scope", _resolve)
    monkeypatch.setattr(minutes_router.cutover, "dossier_stats", _af)
    monkeypatch.setattr(minutes_router, "fetch_handfree", _hf)
    monkeypatch.setattr(rules, "today_vn", lambda now=None: TODAY)
    current = {"user": WARD_A}
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(minutes_router.router)
    app.dependency_overrides[require_dashboard] = lambda: current["user"]
    client = TestClient(app)

    def _switch(user):
        current["user"] = user
        return client

    _switch.db = fake
    return _switch


def _body(state: dict, **doc) -> dict:
    draft = state["draft"]
    return {"unitId": draft["unitId"], "editingId": draft["editingId"], "from": draft["from"], "to": draft["to"],
            "lap": draft["lap"], "doc": {**draft["doc"], **doc}, "base": draft["base"]}


def test_ban_nhap_moi_tu_dien_so_lieu_he_thong(as_user):
    state = as_user(WARD_A).get("/api/v1/work-minutes").json()
    draft = state["draft"]
    assert state["unit"]["place"] == "phường Bắc Giang" and draft["saved"] is False
    assert (draft["from"], draft["to"], draft["lap"]) == ("2026-11-01", TODAY, TODAY)
    doc = draft["doc"]
    # Kết hôn: 3 Auto Fill + 4 Handfree gộp một dòng; có giọng nói = Handfree, chưa có = Auto Fill.
    assert [(r["code"], r["n"]) for r in doc["rows"]] == [("1.000894", 7), ("2.000815", 5)]
    assert (doc["v"], doc["nv"]) == (4, 8)
    assert doc["start"] == "" and doc["cty"] == [{"x": "", "n": "", "r": ""}] and doc["issues"] == [""]
    assert "phường Bắc Giang" in doc["evals"][2]


def test_pham_vi_theo_tai_khoan(as_user):
    assert as_user(WARD_A).get("/api/v1/work-minutes", params={"unit": "ub"}).status_code == 403
    assert as_user(PROVINCE).get("/api/v1/work-minutes", params={"unit": "uc"}).status_code == 403
    assert as_user(PROVINCE).get("/api/v1/work-minutes", params={"unit": "ub"}).status_code == 200
    assert as_user(ADMIN).get("/api/v1/work-minutes", params={"unit": "uc"}).json()["unit"]["unitId"] == "uc"


def test_ban_nhap_luu_db_va_xuat_thi_xoa_nhap(as_user):
    client = as_user(WARD_A)
    state = client.get("/api/v1/work-minutes").json()
    saved = client.put("/api/v1/work-minutes/draft", json=_body(state, start="8 giờ 00")).json()
    assert saved["saved"] is True and saved["doc"]["start"] == "8 giờ 00"
    again = client.get("/api/v1/work-minutes").json()["draft"]
    assert again["doc"]["start"] == "8 giờ 00"

    people = [{"x": "Ông", "n": "Nguyễn Văn A", "r": "Giám đốc"}]
    minutes = client.post("/api/v1/work-minutes", json=_body(state, tt=people, signTT=0, may="3")).json()
    assert minutes["total"] == 12 and minutes["createdBy"] == WARD_A["name"]
    assert as_user.db.raw.work_minute_drafts.count_documents({}) == 0

    # Biên bản sau nối tiếp kỳ, giữ người tham dự + số máy, giờ để trống.
    nxt = client.get("/api/v1/work-minutes").json()
    assert nxt["draft"]["from"] == TODAY and nxt["draft"]["doc"]["tt"] == people
    assert nxt["draft"]["doc"]["may"] == "3" and nxt["draft"]["doc"]["start"] == ""
    assert [m["id"] for m in nxt["minutes"]] == [minutes["id"]]


def test_mo_bien_ban_cu_de_sua_thi_cap_nhat_dung_ban_do(as_user):
    client = as_user(WARD_A)
    state = client.get("/api/v1/work-minutes").json()
    first = client.post("/api/v1/work-minutes", json=_body(state)).json()
    body = {**_body(state, end="11 giờ"), "editingId": first["id"]}
    updated = client.post("/api/v1/work-minutes", json=body).json()
    assert updated["id"] == first["id"] and updated["doc"]["end"] == "11 giờ"
    assert as_user.db.raw.work_minutes.count_documents({}) == 1
    log = as_user.db.raw.work_minutes.find_one({})["log"]
    assert [e["action"] for e in log] == ["create", "update"]
    # Biên bản của đơn vị khác không mở / sửa được.
    other = as_user(ADMIN).get("/api/v1/work-minutes", params={"unit": "uc"}).json()
    assert as_user(ADMIN).post("/api/v1/work-minutes", json={**_body(other), "editingId": first["id"]}).status_code == 404
    as_user.db.raw.work_minutes.update_one({}, {"$set": {"unit_id": "uc"}})
    assert as_user(PROVINCE).get(f"/api/v1/work-minutes/{first['id']}").status_code == 403


def test_kiem_du_lieu(as_user):
    client = as_user(WARD_A)
    state = client.get("/api/v1/work-minutes").json()
    assert client.post("/api/v1/work-minutes", json={**_body(state), "from": "2026-11-20", "to": "2026-11-01"}).status_code == 400
    assert client.post("/api/v1/work-minutes", json=_body(state, issues=["x" * (rules.MAX_PARA + 1)])).status_code == 422
    rows = [{"code": "", "name": "a", "n": -1}]
    assert client.post("/api/v1/work-minutes", json=_body(state, rows=rows)).status_code == 422


def test_goi_y_kho_khan_tu_bao_cao_hang_ngay(as_user):
    as_user.db.raw.daily_reports.insert_many([
        {"unit_id": "ua", "date": "2026-11-05", "difficulties": "Mạng chậm"},
        {"unit_id": "ua", "date": "2026-11-06", "difficulties": "Mạng chậm"},
        {"unit_id": "ua", "date": "2026-11-07", "difficulties": ""},
        {"unit_id": "ua", "date": "2026-10-30", "difficulties": "Ngoài kỳ"},
        {"unit_id": "ub", "date": "2026-11-05", "difficulties": "Đơn vị khác"},
    ])
    body = as_user(WARD_A).get("/api/v1/work-minutes/system", params={"dateFrom": "2026-11-01", "dateTo": TODAY}).json()
    assert body["suggestions"] == [{"text": "Mạng chậm", "date": "2026-11-06"}]
    assert body["total"] == 12 and body["handfreeOk"] is True


def test_xuat_word_du_muc_va_bang(as_user):
    client = as_user(WARD_A)
    state = client.get("/api/v1/work-minutes").json()
    minutes = client.post("/api/v1/work-minutes", json=_body(
        state, tt=[{"x": "Bà", "n": "Trần Thị B", "r": "Phó Giám đốc"}], signTT=0, issues=[rules.NO_ISSUE])).json()
    res = client.get(f"/api/v1/work-minutes/{minutes['id']}/docx")
    assert res.status_code == 200 and "Bien%20ban%20lam%20viec" in res.headers["content-disposition"]
    word = Document(io.BytesIO(res.content))
    text = "\n".join(p.text for p in word.paragraphs)
    for part in ("BIÊN BẢN", "I. THÀNH PHẦN THAM DỰ", "II. KẾT QUẢ CÔNG VIỆC TỪ NGÀY 01/11/2026 ĐẾN NGÀY 18/11/2026",
                 "III. KHÓ KHĂN", "IV. ĐÁNH GIÁ", "V. CÔNG VIỆC DỰ KIẾN", "12 hồ sơ, thuộc 02 thủ tục hành chính",
                 "trong đó 4 hồ sơ", "- Bà: Trần Thị B\tChức vụ: Phó Giám đốc", rules.NO_ISSUE):
        assert part in text, part
    # Giờ bắt đầu chưa điền → dòng chấm, không bịa giờ.
    assert "vào hồi …" in text
    table = word.tables[1]
    assert [c.text for c in table.rows[1].cells] == ["1", "1.000894", "Thủ tục đăng ký kết hôn", "7"]
    assert table.rows[-1].cells[-1].text == "12"
    sign = word.tables[2].rows[0].cells[0].text
    assert "ĐẠI DIỆN TRUNG TÂM PVHCC" in sign and "Trần Thị B" in sign


def _ai_body(**kw):
    return {"unitId": "ua", "section": "issues", "notes": "", "current": [],
            "context": {"place": "phường Bắc Giang", "prov": "tỉnh Bắc Ninh", "from": "01/11/2026", "to": "18/11/2026",
                        "total": 12, "v": 4, "nv": 8}, **kw}


def test_ai_viet_tu_y_chinh_va_viet_lai(as_user, monkeypatch):
    from app.work_minutes import ai

    seen = []

    async def _llm(messages, **kw):
        seen.append(messages[1]["content"])
        return '{"paragraphs": ["1. Đường truyền chậm vào buổi sáng.", "  ", "- Người cao tuổi chưa quen thao tác"]}'

    monkeypatch.setattr(ai.llm, "chat_self_hosted", _llm)
    client = as_user(WARD_A)
    res = client.post("/api/v1/work-minutes/ai-write", json=_ai_body(notes="mạng chậm; người già chưa quen"))
    assert res.json() == {"paragraphs": ["- Đường truyền chậm vào buổi sáng.", "- Người cao tuổi chưa quen thao tác."],
                          "mode": "write"}
    assert "mạng chậm; người già chưa quen" in seen[-1] and "01/11/2026" in seen[-1]
    # Bỏ trống ý chính → viết lại các đoạn đang có.
    res = client.post("/api/v1/work-minutes/ai-write", json=_ai_body(section="evals", current=["cán bộ phối hợp tốt"]))
    assert res.json()["mode"] == "rewrite" and "cán bộ phối hợp tốt" in seen[-1]
    assert client.post("/api/v1/work-minutes/ai-write", json=_ai_body(current=["  "])).status_code == 400
    assert client.post("/api/v1/work-minutes/ai-write", json=_ai_body(unitId="ub", notes="x")).status_code == 403
    assert client.post("/api/v1/work-minutes/ai-write", json=_ai_body(section="rows", notes="x")).status_code == 422


def test_ai_loi_bao_thu_lai(as_user, monkeypatch):
    from app.work_minutes import ai

    async def _down(messages, **kw):
        raise RuntimeError("LLM HTTP 502")

    async def _junk(messages, **kw):
        return "không phải JSON"

    client = as_user(WARD_A)
    monkeypatch.setattr(ai.llm, "chat_self_hosted", _down)
    res = client.post("/api/v1/work-minutes/ai-write", json=_ai_body(notes="mạng chậm"))
    assert res.status_code == 503 and "Thử lại sau" in res.json()["message"]
    monkeypatch.setattr(ai.llm, "chat_self_hosted", _junk)
    assert client.post("/api/v1/work-minutes/ai-write", json=_ai_body(notes="mạng chậm")).status_code == 503

    async def _nothing(messages, **kw):
        return '{"paragraphs": []}'

    monkeypatch.setattr(ai.llm, "chat_self_hosted", _nothing)
    res = client.post("/api/v1/work-minutes/ai-write", json=_ai_body(notes="viết bài thơ"))
    assert res.status_code == 422 and "Ghi rõ hơn" in res.json()["message"]


async def test_ai_chi_dung_may_chu_rieng_khong_sang_openai(monkeypatch):
    """Máy chủ AI riêng lỗi thì ném lỗi, không gọi OpenAI dù có cấu hình key."""
    from app.services.llm import client as llm

    async def _down(*a, **kw):
        raise RuntimeError("vLLM down")

    monkeypatch.setattr(llm, "_chat_primary", _down)
    monkeypatch.setattr(llm.settings, "openai_api_key", "sk-test")
    with pytest.raises(RuntimeError, match="vLLM down"):
        await llm.chat_self_hosted([{"role": "user", "content": "x"}])
