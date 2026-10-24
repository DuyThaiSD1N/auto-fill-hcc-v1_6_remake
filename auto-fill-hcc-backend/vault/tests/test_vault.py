import hashlib
import importlib
import json

import pytest
from fastapi.testclient import TestClient

TOKEN = "t" * 64


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("VAULT_WRITE_TOKEN", TOKEN)
    import vault_app
    mod = importlib.reload(vault_app)
    return mod, TestClient(mod.app), tmp_path


def _auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def _post(client, bundle: dict, files: dict[str, bytes], token=TOKEN):
    raw = json.dumps(bundle).encode()
    parts = [("bundle", ("bundle.json", raw, "application/json"))]
    parts += [("file", (sha, data, "application/octet-stream")) for sha, data in files.items()]
    return client.post("/v1/bundles", files=parts, headers=_auth(token)), raw


def test_tu_choi_khi_sai_hoac_thieu_token(vault, monkeypatch):
    _, client, _ = vault
    assert client.post("/v1/blobs/missing", json={"sha256": []}, headers=_auth("sai")).status_code == 401
    assert client.post("/v1/blobs/missing", json={"sha256": []}).status_code == 401


def test_khong_cau_hinh_token_thi_dong_cua(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("VAULT_WRITE_TOKEN", "")
    import vault_app
    mod = importlib.reload(vault_app)
    client = TestClient(mod.app)
    assert client.post("/v1/blobs/missing", json={"sha256": []}, headers=_auth("")).status_code == 401


def test_luu_goi_va_tep_theo_sha256(vault):
    _, client, root = vault
    data = b"anh giay to gia"
    sha = hashlib.sha256(data).hexdigest()
    bundle = {"type": "request", "request_id": "r1", "created_at": "2026-10-23T08:00:00+00:00",
              "unit": {"user_id": "u1", "name": "Xa A"}, "procedure": "p",
              "files": [{"sha256": sha, "name": "a.jpg"}]}
    assert client.post("/v1/blobs/missing", json={"sha256": [sha]}, headers=_auth()).json() == {"missing": [sha]}

    res, raw = _post(client, bundle, {sha: data})
    assert res.status_code == 200, res.text
    bid = res.json()["id"]
    assert bid == hashlib.sha256(raw).hexdigest()
    assert (root / "blobs" / sha[:2] / sha[2:4] / sha).read_bytes() == data
    assert json.loads((root / "bundles" / "2026/10/23" / f"{bid}.json").read_bytes())["request_id"] == "r1"
    assert client.post("/v1/blobs/missing", json={"sha256": [sha]}, headers=_auth()).json() == {"missing": []}

    again, _ = _post(client, bundle, {})
    assert again.status_code == 200 and again.json()["id"] == bid
    import sqlite3
    rows = sqlite3.connect(root / "index.sqlite").execute("SELECT request_id, user_id FROM bundles").fetchall()
    assert rows == [("r1", "u1")]


def test_tu_choi_tep_sai_noi_dung(vault):
    _, client, root = vault
    sha = hashlib.sha256(b"that").hexdigest()
    res, _ = _post(client, {"files": [{"sha256": sha}]}, {sha: b"gia mao"})
    assert res.status_code == 422
    assert not (root / "blobs").exists()


def test_tu_choi_goi_thieu_tep(vault):
    _, client, _ = vault
    sha = hashlib.sha256(b"chua gui").hexdigest()
    res, _ = _post(client, {"files": [{"sha256": sha}]}, {})
    assert res.status_code == 409
    assert res.json()["detail"]["missing"] == [sha]
