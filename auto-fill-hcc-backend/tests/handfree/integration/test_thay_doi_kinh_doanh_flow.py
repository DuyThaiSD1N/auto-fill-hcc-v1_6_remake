"""Thay đổi nội dung ĐK hộ kinh doanh (HkdOnline, businessWorkflow "change") — luồng handfree:
bootstrap pha 1 DỪNG ở màn tra cứu hộ KD để nhận giấy tờ (mã số nằm trong Thông báo/GCN),
pipeline chạy với page="__change__", start action mang workflow + businessFlow."""
import asyncio

from app.channels.handfree.chat import flow, intents, pipeline_runner
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh"


def _conv(**kw):
    base = {
        "_id": "t-thay-doi-kd", "state": "guide_login", "history": [],
        "procedure_key": KEY, "milestones": [], "agency_done": True,
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"},
    }
    base.update(kw)
    return base


def test_registry_entry_change_workflow():
    proc = get_procedure(KEY)
    assert proc and proc["businessWorkflow"] == "change"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert len(proc["pages"]) == 7, "không có trang Hình thức đăng ký"
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys[:2] == ["thong_bao", "gcn_cu"], "GCN cũ là nguồn mã số tra cứu — phải nổi bật"
    assert KEY in intents._PROCEDURE_HINTS


async def test_bootstrap_pha_1_dung_o_man_tra_cuu():
    conv = _conv()
    r = await flow.handle_turn(conv, intents.Intent(
        "event", "page_status", {"businessHost": True, "businessStage": "home"}))
    action = r.actions[0]
    assert action["type"] == "prepare_business_registration"
    assert action["workflow"] == "change" and action["stop_at"] == "search-business"
    assert "tìm kiếm hộ kinh" in r.display_md.lower()
    # Lượt page_status sau (đang bootstrap) không phát trùng action.
    r2 = await flow.handle_turn(conv, intents.Intent(
        "event", "page_status", {"businessHost": True, "businessStage": "select-registration"}))
    assert not r2.actions


async def test_man_tra_cuu_chuyen_sang_nhan_giay_to():
    for stage in ("search-business", "select-change", "confirm", "main-root"):
        conv = _conv()
        await flow.handle_turn(conv, intents.Intent(
            "event", "page_status", {"businessHost": True, "businessStage": stage}))
        assert conv["state"] in ("consent", "ask_doc_method"), (stage, conv["state"])


async def test_runner_dung_options_change_va_luu_business_flow(monkeypatch):
    captured = {}

    async def fake_pipeline(files_by_role, options):
        captured["options"] = options
        return {"pages": {"nguoi-nop-ho-so": []}, "fields": [],
                "businessFlow": {"workflow": "change", "pageOrder": ["nguoi-nop-ho-so"],
                                 "search": {"method": "businessNumber", "value": "0123"}}}

    async def fake_attach(files, options, session=None):
        return {"attachments": [], "errors": []}

    saved = {}

    async def fake_get(cid):
        return {"_id": cid, "procedure_key": KEY}

    async def fake_save(conv):
        saved.update(conv)

    async def fake_up_get(sid):
        return {"_id": sid, "files": [{"fid": "f1.jpg", "name": "a.jpg", "type": "image/jpeg"}]}

    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda key: fake_pipeline)
    monkeypatch.setattr(pipeline_runner, "get_attach_pipeline", lambda key: fake_attach)
    monkeypatch.setattr(pipeline_runner.conv_store, "get", fake_get)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", fake_save)
    monkeypatch.setattr(pipeline_runner.up_store, "get", fake_up_get)
    monkeypatch.setattr(pipeline_runner, "_session_files",
                        lambda sess: [{"name": "a.jpg", "type": "image/jpeg", "dataUrl": "data:,x", "role": ""}])

    async def fake_trace(*args, **kwargs):
        return "trace-1"

    monkeypatch.setattr(pipeline_runner.tracing, "record_process", fake_trace)
    monkeypatch.setattr(pipeline_runner.tracing, "record_attach", fake_trace)

    async def fake_broadcast(sid, payload):
        captured["broadcast"] = payload

    monkeypatch.setattr(pipeline_runner, "broadcast", fake_broadcast)

    await pipeline_runner.run_business_registration("c1", "HS-1", KEY)
    assert captured["options"] == {"page": "__change__"}, "change KHÔNG dùng allPages"
    assert saved["business_flow"]["search"]["value"] == "0123"
    assert captured["broadcast"]["type"] == "business_ready"


def test_ready_action_mang_workflow_va_business_flow():
    conv = {"procedure_key": KEY, "pipeline_status": "business_ready",
            "business_action_started": False,
            "business_pages": {"nguoi-nop-ho-so": []},
            "business_flow": {"search": {"method": "identityNumber", "value": "012345678901"},
                              "pageOrder": ["nguoi-nop-ho-so"]},
            "attach_plan": [], "upload_session_id": "HS-X", "location": {}}
    r = flow._business_ready_reply(conv)
    action = r.actions[0]
    assert action["workflow"] == "change"
    assert action["businessFlow"]["pageOrder"] == ["nguoi-nop-ho-so"]
    assert "tra cứu hộ kinh doanh" in r.display_md.lower()


def test_upload_classifier_da_dang_ky():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    proc = get_procedure(KEY)
    docs = proc["requiredDocs"]
    assert classifier.fallback_to_slot(
        "THÔNG BÁO THAY ĐỔI nội dung đăng ký hộ kinh doanh", docs, [], None)[0] == "thong_bao"
    assert classifier.fallback_to_slot(
        "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH mã số 0123", docs, [], None)[0] == "gcn_cu"
