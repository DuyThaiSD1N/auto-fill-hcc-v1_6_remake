"""Bản sửa đạt → commit trên nhánh riêng của ca, push lên remote; thư mục làm việc, index và HEAD không đổi."""
import subprocess

import pytest

import publish
from codeguard import Change


def git(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.name", "t")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "core.autocrlf", "false")
    (work / "app").mkdir()
    (work / "app/a.py").write_bytes(b"x = 1\n")
    (work / "app/old.py").write_bytes(b"bo = 1\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "goc")
    git(work, "remote", "add", "origin", str(remote))
    monkeypatch.setattr(publish, "REPO", work)
    monkeypatch.setattr(publish, "GIT_REMOTE", "origin")
    return work, remote


def test_khong_bat_commit_thi_bo_qua(repo, monkeypatch, tmp_path):
    monkeypatch.setattr(publish, "GIT_REMOTE", "")
    assert publish.push_fix("at_1", tmp_path, [Change("app/a.py", b"x = 1\n", b"x = 2\n")], "m") is None


def test_day_nhanh_rieng_khong_dung_thu_muc_lam_viec(repo, tmp_path):
    work, remote = repo
    head = git(work, "rev-parse", "HEAD")
    # Thư mục làm việc đang giữ bản sửa (như sau khi agent sửa) + một file sửa tay không thuộc bản sửa.
    (work / "app/a.py").write_bytes(b"x = 2\n")
    (work / "app/new.py").write_bytes(b"moi = 1\n")
    (work / "app/old.py").unlink()
    (work / "ghi-chu.txt").write_bytes(b"sua tay\n")
    changes = [
        Change("app/a.py", b"x = 1\n", b"x = 2\n"),
        Change("app/new.py", None, b"moi = 1\n"),
        Change("app/old.py", b"bo = 1\n", None),
    ]
    result = publish.push_fix("at_abc", tmp_path, changes, "agent: sửa\n\nCa at_abc\n")

    assert result["branch"] == "agent/at_abc"
    assert result["base"] == head and result["drift"] == []
    assert git(work, "rev-parse", "HEAD") == head  # main không đổi
    assert git(work, "status", "--porcelain") != ""  # thư mục làm việc còn nguyên bản sửa
    assert not (tmp_path / "git-index").exists()
    commit = git(remote, "rev-parse", "refs/heads/agent/at_abc")
    assert commit == result["commit"]
    assert git(remote, "show", f"{commit}:app/a.py") == "x = 2"
    assert git(remote, "show", f"{commit}:app/new.py") == "moi = 1"
    files = git(remote, "ls-tree", "-r", "--name-only", commit).splitlines()
    assert "app/old.py" not in files and "ghi-chu.txt" not in files
    assert git(remote, "log", "-1", "--format=%s", commit) == "agent: sửa"


def test_file_da_lech_main_tu_truoc_thi_bao(repo, tmp_path):
    _, _ = repo
    # Lúc agent bắt đầu, file đã khác HEAD (bản sửa ca trước chưa gộp).
    result = publish.push_fix("at_x", tmp_path, [Change("app/a.py", b"x = 9\n", b"x = 10\n")], "m")
    assert result["drift"] == ["app/a.py"]
