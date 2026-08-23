import io
import json

import pytest
from starlette.datastructures import Headers, UploadFile

from app.batch import storage
from app.config import settings
from app.core.errors import AppError


def _upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=name,
        headers=Headers({"content-type": "application/pdf"}),
    )


@pytest.mark.asyncio
async def test_batch_storage_streams_files_and_builds_stable_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "batch_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "batch_min_free_disk_mb", 0)
    metadata = storage.parse_item_metadata(json.dumps({
        "clientDossierId": "hs-1",
        "files": [
            {"name": "a.pdf", "type": "application/pdf", "role": "doc"},
            {"name": "b.pdf", "type": "application/pdf", "role": "doc"},
        ],
    }), 2)

    files, total = await storage.save_uploads(
        job_id="job_1",
        item_id="item_1",
        uploads=[_upload("a.pdf", b"aaa"), _upload("b.pdf", b"bbbb")],
        metadata=metadata,
    )

    assert total == 7
    assert all((tmp_path / item["path"]).is_file() for item in files)
    assert storage.input_fingerprint("procedure", files) == storage.input_fingerprint(
        "procedure", list(reversed(files))
    )


def test_batch_metadata_requires_one_metadata_entry_per_file():
    with pytest.raises(AppError) as error:
        storage.parse_item_metadata(json.dumps({
            "clientDossierId": "hs-1",
            "files": [{"name": "a.pdf"}],
        }), 2)

    assert getattr(error.value, "error", None) == "BAD_BATCH_FILE_METADATA"
