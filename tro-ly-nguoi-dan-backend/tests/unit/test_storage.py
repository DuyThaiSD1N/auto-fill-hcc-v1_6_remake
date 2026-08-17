import base64
import os
from datetime import datetime, timezone

from app.config import settings
from app.storage.files import save_request_files


class _F:
    def __init__(self, name, type, dataUrl, role):
        self.name, self.type, self.dataUrl, self.role = name, type, dataUrl, role


def test_save_request_files(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    raw = b"hello-image-bytes"
    data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
    created = datetime(2026, 6, 4, tzinfo=timezone.utc)

    files = [_F("cccd trước.jpg", "image/jpeg", data_url, "father")]
    meta = save_request_files("req_abc123", created, files)

    assert meta[0]["name"] == "cccd trước.jpg"
    assert meta[0]["role"] == "father"
    assert meta[0]["size"] == len(raw)
    # file thật được ghi đúng nội dung
    abs_path = os.path.join(str(tmp_path), meta[0]["path"])
    assert os.path.isfile(abs_path)
    with open(abs_path, "rb") as fh:
        assert fh.read() == raw
    # path nằm trong thư mục ngày/request_id
    assert "2026-06-04" in meta[0]["path"] and "req_abc123" in meta[0]["path"]
