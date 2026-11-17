"""Bản sửa đã duyệt và chạy lại đạt → một commit trên nhánh riêng của ca, push lên GitHub.

Chỉ chạy khi máy đặt AUTOTEST_GIT_REMOTE (server). Không đụng thư mục làm việc, index hay nhánh đang checkout:
commit dựng bằng index tạm từ HEAD + đúng các file của bản sửa, nên main và việc đang làm dở trên máy không đổi.
Nhánh mới mỗi ca, không push lên main: người xem tự mở PR nếu muốn gộp.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import codeguard
from config import GIT_BRANCH_PREFIX, GIT_REMOTE, REPO

_AUTHOR = {
    "GIT_AUTHOR_NAME": os.environ.get("AUTOTEST_GIT_NAME", "auto-test-hcc agent"),
    "GIT_AUTHOR_EMAIL": os.environ.get("AUTOTEST_GIT_EMAIL", "auto-test-hcc@localhost"),
}


class PublishError(Exception):
    pass


def _git(args: list[str], env: dict | None = None, data: bytes | None = None, timeout: int = 60) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO, env=env, input=data, capture_output=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise PublishError(f"git {args[0]}: {proc.stderr.decode('utf-8', 'replace').strip()[:400]}")
    return proc.stdout.decode("utf-8", "replace").strip()


def _head_blob(rel: str) -> tuple[str, bytes] | None:
    """(mode, nội dung) của file ở HEAD, None nếu HEAD chưa có file này."""
    line = _git(["ls-tree", "HEAD", "--", rel])
    if not line:
        return None
    mode, _, rest = line.partition(" ")
    sha = rest.split()[1]
    proc = subprocess.run(["git", "cat-file", "blob", sha], cwd=REPO, capture_output=True, timeout=60)
    return mode, proc.stdout


def branch_name(job_id: str) -> str:
    return f"{GIT_BRANCH_PREFIX}{job_id}"


def push_fix(job_id: str, job_dir: Path, changes: list[codeguard.Change], message: str) -> dict | None:
    """Trả {branch, commit, base, drift} hoặc None nếu máy không bật commit. Lỗi git ném PublishError."""
    if not GIT_REMOTE or not changes:
        return None
    index = job_dir / "git-index"
    env = {**os.environ, **_AUTHOR, "GIT_INDEX_FILE": str(index),
           "GIT_COMMITTER_NAME": _AUTHOR["GIT_AUTHOR_NAME"], "GIT_COMMITTER_EMAIL": _AUTHOR["GIT_AUTHOR_EMAIL"]}
    base = _git(["rev-parse", "HEAD"])
    # File đã khác HEAD từ trước khi agent sửa (bản sửa ca trước chưa gộp, sửa tay): commit mang theo cả phần khác đó.
    drift = []
    try:
        _git(["read-tree", "HEAD"], env)
        for change in changes:
            head = _head_blob(change.rel)
            if (head[1] if head else None) != change.before:
                drift.append(change.rel)
            if change.after is None:
                _git(["update-index", "--force-remove", "--", change.rel], env)
                continue
            sha = _git(["hash-object", "-w", "--stdin"], env, data=change.after)
            mode = head[0] if head else "100644"
            _git(["update-index", "--add", "--cacheinfo", f"{mode},{sha},{change.rel}"], env)
        tree = _git(["write-tree"], env)
        commit = _git(["commit-tree", tree, "-p", base, "-F", "-"], env, data=message.encode("utf-8"))
    finally:
        index.unlink(missing_ok=True)
    branch = branch_name(job_id)
    _git(["push", GIT_REMOTE, f"{commit}:refs/heads/{branch}"], timeout=180)
    return {"branch": branch, "commit": commit, "base": base, "remote": GIT_REMOTE, "drift": drift}
