"""Đọc req từ máy khác qua SSH: chỉ gọi đúng hai lệnh exists/cat, đường dẫn mã hoá base64, lỗi không để tệp cụt."""
import base64
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
