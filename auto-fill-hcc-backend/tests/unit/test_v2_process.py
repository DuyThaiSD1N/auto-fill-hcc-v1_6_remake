import base64
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.config import settings
from app.attachments import router as attachments_router
from app.process import router as process_router
from app.v2 import router as v2


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(v2.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "user-1", "username": "tester"}
    return TestClient(app)


def _multipart(action: str, *, metadata: list[dict] | None = None):
    meta = metadata or [{
        "name": "ho-so.pdf",
        "type": "application/pdf",
        "role": "doc",
    }]
    return {
        "data": {
            "action": action,
            "procedure": "thu-tuc-test",
            "options": json.dumps({"sessionId": "req_previous"}),
            "fileMetadata": json.dumps(meta),
        },
        "files": [("files", ("ho-so.pdf", b"binary-pdf", "application/pdf"))],
    }


def test_v2_fill_converts_multipart_and_reuses_v1_process(monkeypatch):
    captured = {}

    async def fake_process(body, background, user):
        captured.update(body=body, background=background, user=user)
        return {
            "sessionId": "req_fill",
            "requestId": "req_fill",
            "reviewToken": "review-capability",
            "fields": [{"name": "HoTen", "comp": "x-input", "value": "Nguyễn Văn A"}],
            "extracted": {},
            "stats": {},
            "errors": [],
            "pages": None,
            "businessFlow": None,
        }

    monkeypatch.setattr(v2, "process_v1", fake_process)
    response = _client().post("/api/v2/process", **_multipart("fill"))

    assert response.status_code == 200
    assert response.json()["action"] == "fill"
    assert response.json()["fields"][0]["name"] == "HoTen"
    assert response.json()["reviewToken"] == "review-capability"
    item = captured["body"].files[0]
    assert item.name == "ho-so.pdf"
    assert item.type == "application/pdf"
    assert item.role == "doc"
    assert base64.b64decode(item.dataUrl.split(",", 1)[1]) == b"binary-pdf"
    assert captured["body"].options["sessionId"] == "req_previous"
    assert captured["user"]["id"] == "user-1"


def test_v2_attach_reuses_v1_planner_and_filters_internal_fields(monkeypatch):
    captured = {}

    async def fake_plan(body, user):
        captured.update(body=body, user=user)
        return {
            "attachments": [{
                "fileIndex": 0,
                "fileName": "ho-so.pdf",
                "documentName": "Hồ sơ",
                "componentName": "Thành phần hồ sơ",
                "target": "existing",
                "needsAddComponent": False,
            }],
            "extracted": {},
            "stats": {},
            "errors": [],
            "requestId": "req_attach",
            "ocr_text": "không được lộ qua response",
        }

    monkeypatch.setattr(v2, "plan_attachments_v1", fake_plan)
    response = _client().post("/api/v2/process", **_multipart("attach"))

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "attach"
    assert data["requestId"] == "req_attach"
    assert data["attachments"][0]["fileIndex"] == 0
    assert "ocr_text" not in data
    assert captured["body"].options["sessionId"] == "req_previous"


def test_v2_rejects_bad_action_and_metadata_count():
    client = _client()
    bad_action = client.post("/api/v2/process", **_multipart("unknown"))
    assert bad_action.status_code == 400
    assert bad_action.json()["error"] == "BAD_ACTION"

    bad_metadata = _multipart("fill", metadata=[{"role": "doc"}, {"role": "doc"}])
    mismatch = client.post("/api/v2/process", **bad_metadata)
    assert mismatch.status_code == 400
    assert mismatch.json()["error"] == "BAD_FILE_METADATA"


def test_v2_fill_keeps_v1_file_persistence(tmp_path, monkeypatch):
    async def pipeline(files_by_role, _options):
        assert files_by_role["doc"][0]["name"] == "ho-so.pdf"
        assert "hasHandwriting" not in files_by_role["doc"][0]
        return {
            "fields": [], "extracted": {}, "stats": {}, "errors": [],
            "ocr_text": "", "llm_output": {},
        }

    async def create_request(**_kwargs):
        return "507f1f77bcf86cd799439011"

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(process_router, "get_procedure", lambda _key: {
        "mode": "agent", "roles": [], "label": "Thủ tục test",
    })
    monkeypatch.setattr(process_router, "get_pipeline", lambda _key: pipeline)
    monkeypatch.setattr(process_router.requests_repo, "create_request", create_request)
    monkeypatch.setattr(process_router.requests_repo, "finish_request", no_op)
    monkeypatch.setattr(process_router.audit, "log_request", no_op)
    monkeypatch.setattr(process_router.traces_repo, "create_trace", no_op)

    response = _client().post("/api/v2/process", **_multipart("fill"))

    assert response.status_code == 200
    saved = list(Path(tmp_path).glob("*/req_*/00_ho-so.pdf"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"binary-pdf"


def test_v2_attach_keeps_v1_file_persistence(tmp_path, monkeypatch):
    async def planner(files, _options, session=None):
        assert files[0].name == "ho-so.pdf"
        assert session["request_id"] == "req_previous"
        return {
            "attachments": [{
                "fileIndex": 0,
                "fileName": "ho-so.pdf",
                "documentName": "Hồ sơ",
                "componentName": "Thành phần hồ sơ",
                "target": "existing",
                "needsAddComponent": False,
            }],
            "extracted": {}, "stats": {}, "errors": [],
        }

    async def get_request(_request_id, user_id=None):
        assert user_id == "user-1"
        return {"request_id": "req_previous", "procedure": "thu-tuc-test"}

    async def create_request(**_kwargs):
        return "507f1f77bcf86cd799439011"

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(attachments_router, "get_procedure", lambda _key: {
        "mode": "attach", "label": "Thủ tục test",
    })
    monkeypatch.setattr(attachments_router, "get_attach_pipeline", lambda _key: planner)
    monkeypatch.setattr(attachments_router.requests_repo, "get_request_by_request_id", get_request)
    monkeypatch.setattr(attachments_router.requests_repo, "create_request", create_request)
    monkeypatch.setattr(attachments_router.traces_repo, "create_trace", no_op)

    response = _client().post("/api/v2/process", **_multipart("attach"))

    assert response.status_code == 200
    saved = list(Path(tmp_path).glob("*/req_*/00_ho-so.pdf"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"binary-pdf"
