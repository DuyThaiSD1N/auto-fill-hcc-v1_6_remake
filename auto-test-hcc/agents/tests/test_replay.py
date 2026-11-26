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


def test_chay_lai_luot_dinh_kem_goi_action_attach(monkeypatch, tmp_path):
    import types

    import config

    sent = {}

    def fake_post(url, data=None, files=None, headers=None, timeout=None):
        sent.update(url=url, data=data)
        body = {
            "action": "attach", "requestId": "req_moi", "errors": [],
            "attachments": [{"fileIndex": 0, "documentName": "Tờ khai", "componentName": "Tờ khai đăng ký", "target": "existing"}],
            "replaceFiles": [{"fileIndex": 0, "name": "scan.pdf", "dataUrl": "data:application/pdf;base64," + "A" * 5000}],
        }
        return types.SimpleNamespace(status_code=200, json=lambda: body, text="")

    monkeypatch.setattr(replay.httpx, "post", fake_post)
    monkeypatch.setattr(replay, "read_trace", lambda rid, kind="autofill": {"ocrText": "", "ocrFresh": True, "llmReused": False, "kind": kind})
    monkeypatch.setattr(replay, "REPO", tmp_path)
    (tmp_path / "scan.pdf").write_bytes(b"%PDF-1.4")
    case = {"procedure": "thu-tuc-mau", "kind": "attach", "pageCounts": [1], "options": {"sessionId": "req_dien", "splitDocuments": True},
            "storedFiles": [{"name": "scan.pdf", "path": "scan.pdf", "type": "application/pdf"}]}
    run = replay.run_once(case, 1, "reproduce:1", "token", tmp_path)
    assert sent["data"]["action"] == "attach"
    assert '"sessionId"' not in sent["data"]["options"] and '"splitDocuments": true' in sent["data"]["options"]
    assert run["kind"] == "attach"  # trace đọc đúng trace_steps <req>:attach
    assert run["response"]["fields"][0] == {"name": "dòng: Tờ khai đăng ký", "value": "Tờ khai [#1]"}
    assert "replaceFiles" not in run["response"] and run["response"]["replacedFiles"] == ["scan.pdf"]
    assert (tmp_path / "run1_plan.json").is_file()


# ---- thủ tục có thanh tra (điền đợt 2) --------------------------------------------------------------------------------

def _tt_case(ran, kind="surveyjs"):
    return {"kind": "autofill", "thanhTra": {"has": True, "kind": kind, "ran": ran}}


def test_luot_goc_khong_chay_thanh_tra_thi_chay_lai_cung_tat():
    options = replay.second_pass_options({"fillSupports": ["secondPass", "secondPassArea", "khac"]}, _tt_case(None))
    assert options["fillSupports"] == ["khac"]
    assert not replay.wants_second_pass(_tt_case(None))


def test_luot_goc_co_thanh_tra_thi_giu_nang_luc_cua_extension():
    options = replay.second_pass_options({"fillSupports": ["secondPass"]}, _tt_case("done"))
    assert options["fillSupports"] == ["secondPass"]


def test_luot_tro_ly_khong_co_fill_supports_thi_khai_nhu_extension():
    assert "secondPassFormio" in replay.second_pass_options({}, _tt_case("done", "formio"))["fillSupports"]
    assert replay.second_pass_options({}, _tt_case("done", "hkd"))["fillSupports"] == ["secondPassHkd"]


def test_luot_dinh_kem_khong_chay_thanh_tra():
    assert not replay.wants_second_pass({**_tt_case("done"), "kind": "attach"})


def test_ghep_ket_qua_thanh_tra_vao_lan_chay_lai(tmp_path):
    body = {"fields": [{"name": "hoTen", "value": "Nguyen Van B"}]}
    doc = {"status": "done", "ms": 1200, "fields": [{"name": "hoTen", "value": "Nguyễn Văn B", "from": "Nguyen Van B", "by": "dinh_danh"}],
           "rulings": [{"inspector": "dinh_danh", "outcome": "sua"}, {"inspector": "dia_chi", "outcome": "giu"}]}
    brief = replay.apply_second_pass(body, doc, 3, tmp_path)
    assert body["fields"][0]["value"] == "Nguyễn Văn B" and body["firstPassFields"][0]["value"] == "Nguyen Van B"
    assert brief == {"status": "done", "reason": None, "ms": 1200, "outcomes": {"sua": 1, "giu": 1}, "patched": ["hoTen"]}
    assert (tmp_path / "run3_second_pass.json").is_file()


def test_thanh_tra_qua_gio_thi_giu_luot_dau(tmp_path):
    body = {"fields": [{"name": "hoTen", "value": "A"}]}
    brief = replay.apply_second_pass(body, {"status": "failed", "reason": "timeout"}, 1, tmp_path)
    assert body == {"fields": [{"name": "hoTen", "value": "A"}]} and brief["status"] == "failed"
    assert replay.apply_second_pass(body, None, 2, tmp_path) == {"status": "none"}
