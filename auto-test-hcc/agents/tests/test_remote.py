"""Đọc req từ máy khác qua SSH: chỉ gọi đúng hai lệnh exists/cat, đường dẫn mã hoá base64, lỗi không để tệp cụt."""
import base64
import json
import subprocess

import pytest

import evidence
import remote


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.fixture
def ssh(monkeypatch):
    calls = []
    monkeypatch.setattr(remote, "SOURCE_SSH", "nlp@may-chu")
    monkeypatch.setattr(remote, "SOURCE_SSH_KEY", "C:/khoa")
    monkeypatch.setattr(remote.shutil, "which", lambda name: "/usr/bin/ssh")

    def fake_run(cmd, stdout=None, **kwargs):
        calls.append(cmd)
        reply = handler["reply"](cmd[-1])
        if hasattr(stdout, "write"):
            stdout.write(reply.get("data", b""))
            return subprocess.CompletedProcess(cmd, reply.get("code", 0), None, reply.get("err", b""))
        return subprocess.CompletedProcess(cmd, reply.get("code", 0), reply.get("data", b""), reply.get("err", b""))

    handler = {"reply": lambda command: {}}
    monkeypatch.setattr(remote.subprocess, "run", fake_run)
    return calls, handler


def test_missing_ma_hoa_duong_dan_va_doc_tra_loi(ssh):
    calls, handler = ssh
    handler["reply"] = lambda command: {"data": f"MISSING {b64('2026-11-17/b c.pdf')}\n".encode()}
    gone = remote.missing(["2026-11-17/a.jpg", "2026-11-17/b c.pdf"])
    assert gone == {"2026-11-17/b c.pdf"}
    command = calls[0][-1]
    assert command == f"exists {b64('2026-11-17/a.jpg')} {b64('2026-11-17/b c.pdf')}"
    assert calls[0][-2] == "nlp@may-chu" and "BatchMode=yes" in calls[0] and "C:/khoa" in calls[0]


def test_fetch_ghi_tep_va_loi_thi_khong_de_tep_cut(ssh, tmp_path):
    _, handler = ssh
    handler["reply"] = lambda command: {"data": b"%PDF-1"}
    target = tmp_path / "files/a.pdf"
    remote.fetch("2026-11-17/a.pdf", target)
    assert target.read_bytes() == b"%PDF-1"

    handler["reply"] = lambda command: {"data": b"%PD", "code": 2, "err": b"khong co"}
    broken = tmp_path / "files/b.pdf"
    with pytest.raises(remote.RemoteError):
        remote.fetch("2026-11-17/b.pdf", broken)
    assert not broken.exists() and not list(tmp_path.glob("files/*.part"))


def test_evidence_doc_tep_qua_ssh(ssh, monkeypatch, tmp_path):
    _, handler = ssh
    handler["reply"] = lambda command: (
        {"data": f"MISSING {b64('x/mat.jpg')}\n".encode()} if command.startswith("exists") else {"data": b"anh"}
    )
    files = [{"name": "con.jpg", "path": "x/con.jpg"}, {"name": "mat.jpg", "path": "x/mat.jpg"}, {"name": "rong"}]
    assert evidence._missing_files(files) == ["mat.jpg", "rong"]
    evidence._copy_file("x/con.jpg", tmp_path / "con.jpg")
    assert (tmp_path / "con.jpg").read_bytes() == b"anh"


def test_loi_ssh_thanh_cau_bao_cho_nguoi_dung(ssh):
    _, handler = ssh
    handler["reply"] = lambda command: {"code": 255, "err": b"Permission denied (publickey)."}
    with pytest.raises(evidence.CaseError, match="Permission denied"):
        evidence._missing_files([{"name": "a.jpg", "path": "x/a.jpg"}])


def test_mongo_thu_khong_roi_ve_nguon(monkeypatch):
    """Nguồn là production đọc từ xa: xoá cache OCR / đọc trace lượt chạy lại phải ở Mongo local, không phải nguồn."""
    monkeypatch.setattr(evidence, "TEST_MONGO_URI", "")
    monkeypatch.setattr(evidence, "_local_db", lambda: "local")
    monkeypatch.setattr(evidence, "_source_db", lambda: "production")
    evidence.test_database.cache_clear()
    try:
        assert evidence.test_database() == "local"
    finally:
        evidence.test_database.cache_clear()


def test_req_da_archive_thi_bao_ro_ly_do(monkeypatch):
    """Backend production xoá tệp, OCR, fields khoảng 30 phút sau lượt cuối: báo đúng lý do thay vì 'thiếu tệp'."""
    class Coll:
        def __init__(self, doc):
            self.doc = doc

        def find_one(self, *args, **kwargs):
            return self.doc

    class Db:
        process_requests = Coll({"request_id": "rq_x", "archived_at": "2026-11-17", "files": [{"name": "a.jpg"}]})
        traces = Coll({"request_id": "rq_x", "kind": "autofill"})
        trace_steps = Coll(None)

    monkeypatch.setattr(evidence, "database", lambda: Db())
    monkeypatch.setattr(evidence.archive, "enabled", lambda: False)
    with pytest.raises(evidence.CaseError, match="kho lưu trữ"):
        evidence.lookup("rq_x")


def test_duong_ham_web_noi_lai_khi_rot(monkeypatch, tmp_path):
    """Đường hầm ngược đưa web lên server: ssh dừng thì tự mở lại, lệnh chỉ mở cổng loopback của server."""
    started = []
    monkeypatch.setattr(remote, "_PID_FILE", tmp_path / "pids.txt")

    class Proc:
        returncode = 255
        pid = 4242

        def __init__(self, cmd, **kwargs):
            started.append(cmd)
            self.stderr = __import__("io").BytesIO(b"connection reset")

        def wait(self):
            return 255

        def poll(self):
            return 255

    monkeypatch.setattr(remote, "SOURCE_SSH", "nlp@may-chu")
    monkeypatch.setattr(remote, "PUBLISH_WEB", "12018:127.0.0.1:12008")
    monkeypatch.setattr(remote.shutil, "which", lambda name: "/usr/bin/ssh")
    monkeypatch.setattr(remote.subprocess, "Popen", Proc)
    monkeypatch.setattr(remote.time, "sleep", lambda s: None)
    remote.keep_publishing(rounds=3)
    assert len(started) == 3
    assert started[0][-3:] == ["-R", "127.0.0.1:12018:127.0.0.1:12008", "nlp@may-chu"]
    assert "ExitOnForwardFailure=yes" in started[0] and not remote.publishing()


ARCHIVED_RUN = {
    "bundleId": "b" * 64,
    "files": [{"name": "giay.pdf", "sha256": "s1", "path": "2026-11-10/giay.pdf", "role": "doc", "size": 3}],
    "ocrTexts": {"s1": "TEXT OCR KHO"},
    "runs": {"autofill": {
        "trace": {"procedure_label": "Thủ tục mẫu", "llm_output": {"fields": {"A": "1"}}},
        "steps": {"ocr": [{"name": "giay.pdf", "sha256": "s1"}], "llm": [{"n": 1, "purpose": "extract", "raw": "RAW KHO"}],
                  "outputs": {"response": {}}},
    }},
    "processRequests": [{
        "request_id": "rq_cu", "procedure": "thu-tuc-mau", "user_id": "u1", "experience": "autofill",
        "files": [{"name": "giay.pdf", "sha256": "s1", "path": "2026-11-10/giay.pdf", "type": "application/pdf", "role": "doc"}],
        "fields": [{"name": "A", "value": "1"}], "options": {"formContext": {"applicantFullname": "x"}},
    }],
    "formReview": {"rows": [{"name": "A", "be": "1", "final": "1"}]},
}


class _ArchivedDb:
    """Mongo production: lượt đã archive (không còn fields), tài khoản vẫn còn."""

    class _C:
        def __init__(self, doc):
            self.doc = doc

        def find_one(self, *args, **kwargs):
            return self.doc

    def __init__(self):
        self.process_requests = self._C({"request_id": "rq_cu", "archived_at": "2026-11-10", "files": [{"name": "giay.pdf"}]})
        self.traces = self._C(None)
        self.trace_steps = self._C(None)
        self.users = self._C({"_id": "u1", "username": "xaA", "xa": "Xã A", "tinh": "Tỉnh B"})
        self.conversations = self._C(None)


def test_lay_req_cu_tu_kho_luu_tru(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "database", lambda: _ArchivedDb())
    monkeypatch.setattr(evidence.archive, "enabled", lambda: True)
    monkeypatch.setattr(evidence.archive, "get_run", lambda rid: ARCHIVED_RUN if rid == "rq_cu" else None)
    downloads = []

    def fake_download(bundle, sha, target):
        downloads.append((bundle, sha))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"pdf")

    monkeypatch.setattr(evidence.archive, "download", fake_download)
    monkeypatch.setattr(evidence, "REPO", tmp_path)
    monkeypatch.setattr(evidence, "pipeline_folder", lambda procedure: "thu_tuc_mau")
    monkeypatch.setattr(evidence, "_procedure_link", lambda procedure: None)
    evidence._ARCHIVE_CACHE.clear()

    info = evidence.lookup("rq_cu")
    assert info["source"] == "archive" and info["missingFiles"] == [] and info["account"]["xa"] == "Xã A"
    case = evidence.collect("rq_cu", tmp_path / "case")
    assert downloads == [("b" * 64, "s1")]
    assert "TEXT OCR KHO" in (tmp_path / "case/ocr.txt").read_text(encoding="utf-8")
    assert "RAW KHO" in (tmp_path / "case/llm_raw.txt").read_text(encoding="utf-8")
    assert "formReview" in (tmp_path / "case/form_report.json").read_text(encoding="utf-8")
    assert case["fields"] == [{"name": "A", "value": "1"}] and case["options"]["formContext"] == {"applicantFullname": "x"}


def test_kho_khong_co_req_thi_bao_ro(monkeypatch):
    monkeypatch.setattr(evidence, "database", lambda: _ArchivedDb())
    monkeypatch.setattr(evidence.archive, "enabled", lambda: True)
    monkeypatch.setattr(evidence.archive, "get_run", lambda rid: None)
    evidence._ARCHIVE_CACHE.clear()
    with pytest.raises(evidence.CaseError, match="kho lưu trữ"):
        evidence.lookup("rq_cu")


def test_don_duong_ham_mo_coi_chi_tat_dung_ssh(monkeypatch, tmp_path):
    monkeypatch.setattr(remote, "_PID_FILE", tmp_path / "pids.txt")
    (tmp_path / "pids.txt").write_text("111\n222\n", encoding="utf-8")
    monkeypatch.setattr(remote, "_is_ssh", lambda pid: pid == 111)  # 222 đã thành tiến trình khác: không đụng
    killed = []
    monkeypatch.setattr(remote.subprocess, "run", lambda cmd, **k: killed.append(cmd))
    monkeypatch.setattr(remote.os, "kill", lambda pid, sig: killed.append(pid))
    assert remote.cleanup_orphans() == 1
    assert len(killed) == 1 and ("111" in killed[0] if isinstance(killed[0], list) else killed[0] == 111)
    assert not (tmp_path / "pids.txt").exists()


ARCHIVED_ATTACH = {
    "bundleId": "c" * 64,
    "files": [{"name": "anh.jpg", "sha256": "s2", "path": "2026-11-10/anh.jpg", "role": "attachment", "size": 3}],
    "ocrTexts": {"s2": "TEXT OCR DINH KEM"},
    "runs": {"attach": {
        "trace": {"procedure_label": "Thủ tục mẫu", "llm_output": {"attachments": [
            {"fileIndex": 0, "documentName": "Căn cước", "componentName": "Giấy tờ tùy thân", "target": "existing"},
        ]}},
        "steps": {"ocr": [{"name": "anh.jpg", "sha256": "s2"}], "llm": [{"n": 1, "purpose": "plan", "raw": "RAW CHIA GIAY"}],
                  "outputs": {"plan": []}},
    }},
    "processRequests": [{
        "request_id": "rq_dk", "procedure": "thu-tuc-mau", "user_id": "u1", "experience": "autofill",
        "files": [{"name": "anh.jpg", "sha256": "s2", "path": "2026-11-10/anh.jpg", "type": "image/jpeg", "role": "attachment"}],
        "options": {"splitDocuments": True, "sessionId": "rq_dien",
                    "attachmentContext": {"components": [{"index": 1, "componentName": "Giấy tờ tùy thân"}]}},
    }],
}


def test_luot_dinh_kem_trong_kho_luu_tru(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "database", lambda: _ArchivedDb())
    monkeypatch.setattr(evidence.archive, "enabled", lambda: True)
    monkeypatch.setattr(evidence.archive, "get_run", lambda rid: ARCHIVED_ATTACH if rid == "rq_dk" else None)

    def fake_download(bundle, sha, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"jpg")

    monkeypatch.setattr(evidence.archive, "download", fake_download)
    monkeypatch.setattr(evidence, "REPO", tmp_path)
    monkeypatch.setattr(evidence, "pipeline_folder", lambda procedure: "thu_tuc_mau")
    monkeypatch.setattr(evidence, "_procedure_link", lambda procedure: None)
    evidence._ARCHIVE_CACHE.clear()

    info = evidence.lookup("rq_dk")
    assert info["kind"] == "attach" and info["fieldsCount"] == 1 and info["splitDocuments"] is True and info["portalRows"] == 1
    assert info["needsApplicant"] is False and info["attachRuns"] == []
    case = evidence.collect("rq_dk", tmp_path / "case")
    assert case["pageCounts"] == [1] and len(case["plan"]) == 1
    fields = {f["name"]: f["value"] for f in case["fields"]}
    assert fields["dòng: Giấy tờ tùy thân"] == "Căn cước [#1]" and fields["tổng: trang thiếu"] == ""
    plan_file = json.loads((tmp_path / "case/attach_plan.json").read_text(encoding="utf-8"))
    assert plan_file["files"] == [{"so": "#1", "name": "anh.jpg", "pages": 1}] and plan_file["portalRows"][0]["componentName"] == "Giấy tờ tùy thân"
    assert "RAW CHIA GIAY" in (tmp_path / "case/llm_raw.txt").read_text(encoding="utf-8")


def test_luot_extension_tu_dinh_thi_khong_chay_lai(monkeypatch):
    class Db(_ArchivedDb):
        def __init__(self):
            super().__init__()
            self.process_requests = self._C({"request_id": "rq_ctv", "user_id": "u1", "files": [{"name": "a.pdf", "path": "x"}]})
            self.traces = self._C({"kind": "attach", "llm_output": {"attachments": [], "extracted": {"clientAttachmentCase": "single-row"}}})

    monkeypatch.setattr(evidence, "database", lambda: Db())
    monkeypatch.setattr(evidence.archive, "enabled", lambda: False)
    with pytest.raises(evidence.CaseError, match="extension tự đính"):
        evidence.lookup("rq_ctv")
