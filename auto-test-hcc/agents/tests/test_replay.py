from pathlib import Path

import pytest

import replay
from replay import replay_options, strip_response


def test_bo_khoa_gan_voi_ho_so_that():
    options = replay_options({
        "dossierId": "d", "sessionId": "s", "conversation_id": "c", "upload_session_id": "u", "consent_id": "k", "channel": "handfree",
        "formContext": {"applicantFullname": "x"}, "submitterMode": "self", "extVersion": "1.0",
    }, "reproduce:1")
    assert options == {"formContext": {"applicantFullname": "x"}, "submitterMode": "self", "extVersion": "1.0", "labRun": "reproduce:1"}


def test_options_rong():
    assert replay_options(None, "t") == {"labRun": "t"}


def test_strip_response():
    assert strip_response({"n": 1, "response": {"fields": []}}) == {"n": 1}


class _Users:
    def __init__(self, docs):
        self.docs = {d["username"]: dict(d) for d in docs}

    def find_one(self, query, projection=None):
        return self.docs.get(query["username"])

    def update_one(self, query, update):
        self.docs.setdefault(query["username"], {"username": query["username"]}).update(update["$set"])


def _shadow_env(monkeypatch, docs):
    import types

    import verify

    users = _Users(docs)
    calls = []
    monkeypatch.setattr(replay, "database", lambda: types.SimpleNamespace(users=users))
    monkeypatch.setattr(verify, "_compose", lambda: (["docker", "compose", "-f", "x.yml"], Path("."), "autotest-app"))
    monkeypatch.setattr(verify, "USE_WORKSPACE", False)

    def fake_run(cmd, cwd, timeout, cancel, env=None):
        calls.append(cmd)
        name = next(a.split("=", 1)[1] for a in cmd if a.startswith("--username="))
        users.docs.setdefault(name, {"username": name})
        return 0, "Tạo mới user"

    monkeypatch.setattr(verify, "run", fake_run)
    return users, calls


def test_tai_khoan_chay_lai_tu_dung_dung_xa_tinh(monkeypatch):
    users, calls = _shadow_env(monkeypatch, [])
    creds = replay.shadow_account({"username": "PhuongA", "name": "Phường A", "xa": "Phường A", "tinh": "Tỉnh B", "role": "admin"})
    assert creds["username"] == "phuonga" and not creds["renamed"] and len(creds["password"]) >= 20
    cmd = calls[0]
    assert "--xa=Phường A" in cmd and "--tinh=Tỉnh B" in cmd and "--role=user" in cmd  # không dựng tài khoản admin
    assert f"--password={creds['password']}" in cmd  # dạng --khoá=giá-trị: mật khẩu bắt đầu bằng "-" vẫn đúng
    assert users.docs["phuonga"]["autotest_shadow"] is True


def test_trung_tai_khoan_test_co_san_thi_dung_ten_rieng(monkeypatch):
    users, calls = _shadow_env(monkeypatch, [{"username": "xatest"}])
    creds = replay.shadow_account({"username": "xatest", "xa": "Phường Mẫu", "tinh": "Tỉnh Mẫu"})
    assert creds["username"] == "autotest-xatest" and creds["renamed"]
    assert "autotest_shadow" not in users.docs["xatest"]  # tài khoản của người khác không bị đụng
    assert all("--username=xatest" not in a for a in calls[0])


def test_tao_lai_tai_khoan_cua_chinh_dich_vu(monkeypatch):
    users, calls = _shadow_env(monkeypatch, [{"username": "phuonga", "autotest_shadow": True}])
    first = replay.shadow_account({"username": "phuonga"})
    second = replay.shadow_account({"username": "phuonga"})
    assert first["username"] == second["username"] == "phuonga" and first["password"] != second["password"]


def test_dung_tai_khoan_loi_thi_bao(monkeypatch):
    import verify

    _shadow_env(monkeypatch, [])
    monkeypatch.setattr(verify, "run", lambda *a, **k: (1, "container không chạy"))
    with pytest.raises(replay.LoginError, match="container không chạy"):
        replay.shadow_account({"username": "phuonga"})
