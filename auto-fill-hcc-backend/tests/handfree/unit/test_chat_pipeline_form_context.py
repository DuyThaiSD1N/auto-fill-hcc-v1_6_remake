import pytest

from app.channels.handfree.chat import pipeline_runner


@pytest.mark.asyncio
async def test_chat_process_passes_saved_form_context_to_pipeline(monkeypatch):
    conversation = {
        "_id": "c-form-context",
        "form_context": {
            "applicantFullname": "NGUYỄN TUẤN ANH",
            "applicantIdentityNumber": "027202006253",
        },
    }
    captured: dict = {}

    async def fake_get_session(_sid):
        return {"_id": "HS-TEST", "files": [{"name": "to-khai.pdf", "type": "application/pdf"}]}

    async def fake_get_conversation(_conv_id):
        return conversation

    async def fake_pipeline(_files_by_role, options):
        captured.update(options)
        return {"fields": [], "stats": {}, "errors": []}

    async def fake_record_process(*_args, **_kwargs):
        return "trace-test"

    async def noop_async(*_args, **_kwargs):
        return None

    monkeypatch.setattr(pipeline_runner.up_store, "get", fake_get_session)
    monkeypatch.setattr(
        pipeline_runner.up_store,
        "file_to_data_url",
        lambda _sid, _file: "data:application/pdf;base64,AAA",
    )
    monkeypatch.setattr(pipeline_runner.conv_store, "get", fake_get_conversation)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", noop_async)
    monkeypatch.setattr(pipeline_runner, "get_procedure", lambda _key: {"review": False})
    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _key: fake_pipeline)
    monkeypatch.setattr(pipeline_runner.tracing, "record_process", fake_record_process)
    monkeypatch.setattr(pipeline_runner, "broadcast", noop_async)

    await pipeline_runner.run_process("c-form-context", "HS-TEST", "trich-luc-ks")

    assert captured["formContext"] == conversation["form_context"]
    assert conversation["pipeline_status"] == "fields_ready"


@pytest.mark.asyncio
async def test_chat_process_creates_new_trace_when_reprocessing(monkeypatch):
    conversation = {"_id": "c-refill", "form_context": {}}
    captured = {}

    async def fake_get_session(_sid):
        return {"_id": "HS-REFILL", "files": [{"name": "cccd.pdf", "type": "application/pdf"}]}

    async def fake_pipeline(_files_by_role, _options):
        return {"fields": [{"name": "HoTen", "value": "A"}], "stats": {}}

    async def fake_record_process(*_args, **kwargs):
        captured.update(kwargs)
        return "trace-moi"

    async def noop_async(*_args, **_kwargs):
        return None

    monkeypatch.setattr(pipeline_runner.up_store, "get", fake_get_session)
    monkeypatch.setattr(
        pipeline_runner.up_store, "file_to_data_url",
        lambda _sid, _file: "data:application/pdf;base64,AAA",
    )

    async def fake_get_conversation(_conv_id):
        return conversation

    monkeypatch.setattr(pipeline_runner.conv_store, "get", fake_get_conversation)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", noop_async)
    monkeypatch.setattr(pipeline_runner, "get_procedure", lambda _key: {"review": False})
    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _key: fake_pipeline)
    monkeypatch.setattr(pipeline_runner.tracing, "record_process", fake_record_process)
    monkeypatch.setattr(pipeline_runner, "broadcast", noop_async)

    await pipeline_runner.run_process("c-refill", "HS-REFILL", "ket-hon")

    assert "reuse_request_id" not in captured
    assert conversation["trace_request_id"] == "trace-moi"


@pytest.mark.asyncio
async def test_owner_info_runs_without_legacy_ocr_provider_reset(monkeypatch):
    conversation = {
        "_id": "c-owner-info",
        "owner_context": {
            "fullName": "NGUYỄN TUẤN ANH",
            "identityNumber": "027202006253",
        },
        "execution_subject": "self",
    }
    captured: dict = {}
    events: list[dict] = []

    async def fake_get_session(_sid):
        return {
            "_id": "HS-OWNER",
            "files": [{"name": "cccd.pdf", "type": "application/pdf"}],
        }

    async def fake_get_conversation(_conv_id):
        return conversation

    async def fake_pipeline(_files_by_role, options):
        captured.update(options)
        return {
            "fields": [{"name": "Owner_NgayCap", "value": "02/07/2021"}],
            "owner_match": {"matched": True},
            "errors": [],
        }

    async def fake_broadcast(_sid, event):
        events.append(event)

    async def noop_async(*_args, **_kwargs):
        return None

    monkeypatch.setattr(pipeline_runner.up_store, "get", fake_get_session)
    monkeypatch.setattr(
        pipeline_runner.up_store,
        "file_to_data_url",
        lambda _sid, _file: "data:application/pdf;base64,AAA",
    )
    monkeypatch.setattr(pipeline_runner.conv_store, "get", fake_get_conversation)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", noop_async)
    monkeypatch.setattr(
        pipeline_runner,
        "get_procedure",
        lambda _key: {
            "ownerInfo": {
                "fields": {
                    "Owner_NgayCap": {
                        "key": "issueDate",
                        "label": "Ngày cấp",
                        "comp": "owner-date",
                    }
                }
            }
        },
    )
    monkeypatch.setattr(pipeline_runner, "get_owner_info_pipeline", lambda _key: fake_pipeline)
    monkeypatch.setattr(pipeline_runner, "broadcast", fake_broadcast)

    await pipeline_runner.run_owner_info("c-owner-info", "HS-OWNER", "ket-hon")

    assert captured == {"ownerContext": conversation["owner_context"]}
    assert conversation["pipeline_status"] == "owner_fields_ready"
    assert conversation["owner_fields"][0]["value"] == "02/07/2021"
    assert events == [{"type": "owner_fields_ready", "count": 1}]
