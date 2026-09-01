import hashlib

import pytest

from app.batch import worker
from app.config import settings


@pytest.mark.asyncio
async def test_batch_worker_reuses_process_contract_without_writing_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "batch_storage_dir", str(tmp_path))
    stored = tmp_path / "job_1" / "item_1" / "000_ho_so.pdf"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"pdf-content")
    captured = {}

    async def pipeline(files_by_role, options):
        captured["files"] = files_by_role
        captured["options"] = options
        return {
            "fields": [{"name": "HoTen", "comp": "x-input", "value": "Nguyễn Văn A"}],
            "extracted": {"source": "test"},
            "stats": {"total_latency_ms": 12},
            "errors": [],
        }

    async def get_job(_):
        return {"status": "running"}

    async def complete_item(item_id, worker_id, result):
        captured.update(item_id=item_id, worker_id=worker_id, result=result)
        return True

    async def fail_item(*args, **kwargs):
        pytest.fail("Không được đưa hồ sơ hợp lệ vào nhánh lỗi")

    async def finish_job(_):
        captured["finished_checked"] = True

    async def extend_lease(*_):
        return True

    monkeypatch.setattr(worker, "get_procedure", lambda _: {"mode": "agent", "roles": []})
    monkeypatch.setattr(worker, "get_pipeline", lambda _: pipeline)
    monkeypatch.setattr(worker.repo, "get_job", get_job)
    monkeypatch.setattr(worker.repo, "complete_item", complete_item)
    monkeypatch.setattr(worker.repo, "fail_item", fail_item)
    monkeypatch.setattr(worker.repo, "finish_job_if_terminal", finish_job)
    monkeypatch.setattr(worker.repo, "extend_lease", extend_lease)

    await worker.process_item({
        "item_id": "item_1",
        "job_id": "job_1",
        "procedure": "thu-tuc-test",
        "options": {"formContext": {"name": "A"}},
        "files": [{
            "name": "ho_so.pdf",
            "type": "application/pdf",
            "role": "doc",
            "path": str(stored.relative_to(tmp_path)),
            "sha256": hashlib.sha256(b"pdf-content").hexdigest(),
        }],
    }, "worker-1")

    assert captured["result"]["requestId"] == "item_1"
    assert captured["result"]["sessionId"] == "item_1"
    assert captured["result"]["fields"][0]["name"] == "HoTen"
    assert captured["options"]["formContext"]["name"] == "A"
    assert captured["finished_checked"] is True
