from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.batch import router as batch_router
from app.config import settings
from app.core.errors import AppError, app_error_handler


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(batch_router.router)
    return TestClient(app)


def test_batch_api_requires_dedicated_bearer_secret(monkeypatch):
    monkeypatch.setattr(settings, "batch_api_secret", "batch-secret")
    client = _client()

    missing = client.post("/api/v1/batch/jobs", json={"name": "Đợt 1", "procedure": "test"})
    wrong = client.post(
        "/api/v1/batch/jobs",
        headers={"Authorization": "Bearer wrong"},
        json={"name": "Đợt 1", "procedure": "test"},
    )

    assert missing.status_code == 401
    assert missing.json()["error"] == "INVALID_BATCH_SECRET"
    assert wrong.status_code == 401


def test_create_batch_job(monkeypatch):
    monkeypatch.setattr(settings, "batch_api_secret", "batch-secret")
    monkeypatch.setattr(batch_router, "get_procedure", lambda _: {"label": "Test"})
    monkeypatch.setattr(batch_router, "get_pipeline", lambda _: object())

    async def fake_create_job(*, name, procedure):
        return {
            "job_id": "job_1",
            "name": name,
            "procedure": procedure,
            "status": "draft",
        }

    monkeypatch.setattr(batch_router.repo, "create_job", fake_create_job)
    response = _client().post(
        "/api/v1/batch/jobs",
        headers={"Authorization": "Bearer batch-secret"},
        json={"name": "Đợt 1", "procedure": "thu-tuc-test"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "jobId": "job_1",
        "name": "Đợt 1",
        "procedure": "thu-tuc-test",
        "status": "draft",
        "counts": {"total": 0},
        "createdAt": None,
        "startedAt": None,
        "finishedAt": None,
    }
