from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_kinh_doanh.attach import planner as business_attach
from app.process.schemas import FileItem
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure


def _conversation(**updates):
    conv = {
        "_id": "c-business",
        "state": "guide_login",
        "procedure_key": "dang-ky-kinh-doanh",
        "location": {"province": "Thành phố Đà Nẵng", "ward": "Phường Hải Châu"},
        "upload_session_id": "HS-BUSINESS",
        "milestones": [],
    }
    conv.update(updates)
    return conv


def test_registry_exposes_dedicated_business_contract():
    proc = get_procedure("dang-ky-kinh-doanh")

    assert proc["businessWorkflow"] == "create"
    assert len(proc["pages"]) == 8
    assert get_pipeline(proc["key"])
    assert get_attach_pipeline(proc["key"])


def test_hkdonline_home_starts_bootstrap_once():
    conv = _conversation()
    proc = get_procedure(conv["procedure_key"])
    context = {"businessHost": True, "businessStage": "home"}

    first = flow._guide_login_on_page(conv, proc, conv["location"], context)
    second = flow._guide_login_on_page(conv, proc, conv["location"], context)

    assert first.actions == [{"type": "prepare_business_registration"}]
    assert "Thành lập mới hộ kinh doanh" in first.display_md
    assert second.actions == []
    assert second.display_md == ""


def test_home_guidance_does_not_claim_a_draft_exists_yet():
    assert "trang chủ" in vi.BUSINESS_PREPARING["md"]
    assert "trang kê khai" in vi.BUSINESS_PREPARING["md"]
    assert "hồ sơ nháp" not in vi.BUSINESS_PREPARING["md"]


def test_consent_intro_does_not_repeat_login_success():
    conv = _conversation(needed_login=True)

    reply = flow._to_consent(conv)

    assert "Đăng nhập thành công" not in reply.display_md
    assert reply.display_md.startswith("Đã vào trang kê khai ✓")


def test_hkdonline_main_root_moves_to_document_consent():
    conv = _conversation(business_prepare_started=True)
    proc = get_procedure(conv["procedure_key"])

    reply = flow._guide_login_on_page(
        conv, proc, conv["location"], {"businessHost": True, "businessStage": "main-root"}
    )

    assert conv["state"] == "consent"
    assert reply.cards[0]["kind"] == "consent_form"


@pytest.mark.asyncio
async def test_docs_complete_spawns_combined_business_job(monkeypatch):
    conv = _conversation(state="collecting_docs")
    spawned = []

    monkeypatch.setattr(
        flow.upload_service,
        "progress_of",
        AsyncMock(return_value={"received": 2, "total": 2, "files_count": 2}),
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coroutine: spawned.append(coroutine))
    monkeypatch.setattr(pipeline_runner, "run_business_registration", lambda *args: ("business", args))

    reply = await flow._docs_complete(conv)

    assert conv["state"] == "filling"
    assert conv["pipeline_status"] == "running"
    assert spawned == [("business", ("c-business", "HS-BUSINESS", "dang-ky-kinh-doanh"))]
    assert "8 khối thông tin" in reply.display_md


def test_business_ready_emits_one_combined_extension_action():
    conv = _conversation(
        state="filling",
        pipeline_status="business_ready",
        business_pages={"hinh-thuc-dang-ky": [], "dia-chi": []},
        attach_plan=[{"fileIndex": 0, "category": "BUSREGFRM"}],
    )

    reply = flow._business_ready_reply(conv)
    duplicate = flow._business_ready_reply(conv)

    assert reply.actions[0]["type"] == "start_business_registration"
    assert reply.actions[0]["session_id"] == "HS-BUSINESS"
    assert reply.actions[0]["businessDefaults"] == {"forceSelfSubmitter": True}
    assert duplicate.actions == []


@pytest.mark.asyncio
async def test_success_report_moves_to_done_and_updates_both_traces(monkeypatch):
    conv = _conversation(
        state="filling",
        business_pages={str(i): [] for i in range(8)},
        trace_request_id="trace-fill",
        attach_trace_request_id="trace-attach",
    )
    reports = []

    async def capture(request_id, kind, report):
        reports.append((request_id, kind, report))

    # flow import cục bộ app.chat.tracing; monkeypatch module thật.
    from app.channels.handfree.chat import tracing
    monkeypatch.setattr(tracing, "set_report", capture)

    reply = await flow._handle_business_report(
        conv, {"ok": True, "filledPages": 8, "attached": 3, "phase": "attach", "errors": []}
    )

    assert conv["state"] == "done"
    assert conv["attach_done"] is True
    assert "8/8" in reply.display_md
    assert "rà soát các thông tin đã điền ở từng khối" in reply.display_md
    assert "các tệp đã đính kèm" in reply.display_md
    assert [(request_id, kind) for request_id, kind, _ in reports] == [
        ("trace-fill", "autofill"), ("trace-attach", "attach")
    ]


@pytest.mark.asyncio
async def test_cancelled_report_shows_fill_and_attachment_progress(monkeypatch):
    conv = _conversation(state="filling", business_action_started=True)

    from app.channels.handfree.chat import tracing
    monkeypatch.setattr(tracing, "set_report", AsyncMock())

    reply = await flow._handle_business_report(conv, {
        "ok": False,
        "cancelled": True,
        "mode": "full",
        "phase": "fill",
        "filledPages": 3,
        "currentPage": 4,
        "totalPages": 8,
        "attachmentStarted": False,
        "errors": ["Công dân đã dừng tiến trình tự động kê khai."],
    })

    assert conv["state"] == "filling"
    assert conv["business_action_started"] is False
    assert conv["pipeline_status"] == "business_cancelled"
    assert "xử lý đến **khối 4/8**" in reply.display_md
    assert "hoàn tất **3/8 khối**" in reply.display_md
    assert "Chưa bắt đầu bước đính kèm" in reply.display_md


@pytest.mark.asyncio
async def test_cancelled_business_waits_for_explicit_retry(monkeypatch):
    conv = _conversation(
        state="filling",
        pipeline_status="business_ready",
        business_action_started=True,
        business_pages={str(i): [] for i in range(8)},
    )

    from app.channels.handfree.chat import tracing
    monkeypatch.setattr(tracing, "set_report", AsyncMock())

    stopped = await flow._handle_filling(conv, Intent("action", "business_report", {
        "ok": False,
        "cancelled": True,
        "mode": "full",
        "phase": "fill",
        "filledPages": 4,
        "currentPage": 5,
        "totalPages": 8,
        "errors": ["Công dân đã dừng tiến trình tự động kê khai."],
    }))
    watcher = await flow._handle_filling(conv, Intent("event", "page_status", {}))

    assert stopped.chips == [{
        "label": "🔁 Thử lại",
        "send": "__event:business_retry",
        "solid": True,
    }]
    assert conv["pipeline_status"] == "business_cancelled"
    assert watcher.actions == []
    assert watcher.display_md == ""

    retry = await flow._handle_filling(conv, Intent("event", "business_retry", {}))
    duplicate_retry = await flow._handle_filling(conv, Intent("event", "business_retry", {}))

    assert conv["pipeline_status"] == "business_ready"
    assert conv["business_result"] is None
    assert retry.actions[0]["type"] == "start_business_registration"
    assert duplicate_retry.actions == []


@pytest.mark.asyncio
async def test_duplicate_cancelled_business_report_is_silent(monkeypatch):
    payload = {
        "ok": False,
        "cancelled": True,
        "mode": "full",
        "phase": "fill",
        "filledPages": 1,
        "currentPage": 2,
        "totalPages": 8,
        "errors": ["Công dân đã dừng tiến trình tự động kê khai."],
    }
    conv = _conversation(
        state="filling",
        pipeline_status="business_ready",
        business_action_started=True,
    )

    from app.channels.handfree.chat import tracing
    set_report = AsyncMock()
    monkeypatch.setattr(tracing, "set_report", set_report)

    first = await flow._handle_business_report(conv, payload)
    duplicate = await flow._handle_business_report(conv, payload)

    assert first.display_md
    assert duplicate.display_md == ""
    assert set_report.await_count == 2


@pytest.mark.asyncio
async def test_attach_failure_reports_all_blocks_and_unfinished_upload(monkeypatch):
    conv = _conversation(
        state="filling",
        pipeline_status="business_ready",
        business_action_started=True,
    )

    from app.channels.handfree.chat import tracing
    monkeypatch.setattr(tracing, "set_report", AsyncMock())

    reply = await flow._handle_business_report(conv, {
        "ok": False,
        "mode": "full",
        "phase": "attach",
        "filledPages": 8,
        "currentPage": 8,
        "totalPages": 8,
        "plannedAttachments": 4,
        "uploadedAttachments": 4,
        "attachmentStarted": True,
        "attachmentCompleted": False,
        "errors": ["Không lưu được loại tài liệu."],
    })

    assert "điền đủ **8/8 khối dữ liệu**" in reply.display_md
    assert "tải lên **4/4 tệp**" in reply.display_md
    assert "chưa hoàn tất bước gán loại và lưu" in reply.display_md
    assert conv["pipeline_status"] == "business_failed"


@pytest.mark.asyncio
async def test_combined_pipeline_broadcasts_only_after_process_and_attach(monkeypatch):
    conv = _conversation()
    events = []

    monkeypatch.setattr(
        pipeline_runner.up_store,
        "get",
        AsyncMock(return_value={
            "_id": "HS-BUSINESS",
            "files": [{"name": "ho-so.pdf", "type": "application/pdf"}],
        }),
    )
    monkeypatch.setattr(
        pipeline_runner.up_store,
        "file_to_data_url",
        lambda *_args: "data:application/pdf;base64,AAA",
    )
    monkeypatch.setattr(pipeline_runner.conv_store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(pipeline_runner.conv_store, "save", AsyncMock())
    monkeypatch.setattr(pipeline_runner, "get_procedure", lambda _key: {"label": "HKD"})

    async def process(_files, options):
        assert options == {"allPages": True}
        return {"fields": [], "pages": {"hinh-thuc-dang-ky": []}, "extracted": {}, "stats": {}}

    async def attach(_files, _options, session=None):
        assert session is None
        return {"attachments": [{"fileIndex": 0, "category": "BUSREGFRM"}], "errors": []}

    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _key: process)
    monkeypatch.setattr(pipeline_runner, "get_attach_pipeline", lambda _key: attach)
    monkeypatch.setattr(pipeline_runner.tracing, "record_process", AsyncMock(return_value="fill-trace"))
    monkeypatch.setattr(pipeline_runner.tracing, "record_attach", AsyncMock(return_value="attach-trace"))
    monkeypatch.setattr(pipeline_runner, "broadcast", AsyncMock(side_effect=lambda _sid, event: events.append(event)))

    await pipeline_runner.run_business_registration("c-business", "HS-BUSINESS", "dang-ky-kinh-doanh")

    assert conv["pipeline_status"] == "business_ready"
    assert conv["attach_plan"][0]["category"] == "BUSREGFRM"
    assert events == [{"type": "business_ready", "pages": 1, "attachments": 1}]


@pytest.mark.asyncio
async def test_attach_planner_keeps_duplicate_file_names_separate(monkeypatch):
    files = [
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role=""),
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,BBB", role=""),
    ]
    monkeypatch.setattr(
        "app.services.ocr.ocr_per_file",
        AsyncMock(return_value=[
            {"name": "image.pdf", "text": "GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH"},
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]),
    )
    monkeypatch.setattr(
        business_attach,
        "_classify_with_llm",
        AsyncMock(return_value={
            0: {"type": "business_form", "documentName": "Giấy đề nghị"},
            1: {"type": "personal_legal", "documentName": "Căn cước công dân"},
        }),
    )

    result = await business_attach.plan(files)

    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1]
    assert [item["category"] for item in result["attachments"]] == ["BUSREGFRM", "CPID"]
