"""Bản sửa đã duyệt và chạy lại đạt → commit trên nhánh riêng của ca, push lên GitHub, kèm link mở PR.

- Khu làm việc (mặc định trên máy local): mỗi phần bị sửa (backend, extension Auto Fill, extension trợ lý) thành một commit
  trên nhánh ``agent/<mã ca>`` của ĐÚNG repo thật của phần đó, dựng trên tag release đang chạy production. Link "compare"
  mở PR vào nhánh base (main); không có token nên không tự tạo PR, người bấm link để mở.
- Kiểu cũ (AUTOTEST_GIT_REMOTE): một commit monorepo đẩy lên remote đó.

Không đụng thư mục làm việc, index hay nhánh đang checkout: commit dựng bằng index tạm từ HEAD + đúng các file của bản sửa.
Không bao giờ push lên main.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import codeguard
from config import COMPONENTS, GIT_BRANCH_PREFIX, GIT_REMOTE, REPO, USE_WORKSPACE, WORKSPACE, WORKSPACE_PUSH

_AUTHOR = {
    "GIT_AUTHOR_NAME": os.environ.get("AUTOTEST_GIT_NAME", "auto-test-hcc agent"),
    "GIT_AUTHOR_EMAIL": os.environ.get("AUTOTEST_GIT_EMAIL", "auto-test-hcc@localhost"),
}


class PublishError(Exception):
    pass


def _git(args: list[str], env: dict | None = None, data: bytes | None = None, timeout: int = 60, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=cwd or REPO, env=env, input=data, capture_output=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise PublishError(f"git {args[0]}: {proc.stderr.decode('utf-8', 'replace').strip()[:400]}")
    return proc.stdout.decode("utf-8", "replace").strip()


def _head_blob(rel: str, cwd: Path | None = None) -> tuple[str, bytes] | None:
    """(mode, nội dung) của file ở HEAD, None nếu HEAD chưa có file này."""
    line = _git(["ls-tree", "HEAD", "--", rel], cwd=cwd)
    if not line:
        return None
    mode, _, rest = line.partition(" ")
    sha = rest.split()[1]
    proc = subprocess.run(["git", "cat-file", "blob", sha], cwd=cwd or REPO, capture_output=True, timeout=60)
    return mode, proc.stdout


def branch_name(job_id: str) -> str:
    return f"{GIT_BRANCH_PREFIX}{job_id}"


def compare_url(remote_url: str, base: str, branch: str) -> str | None:
    """Link GitHub mở PR từ ``branch`` vào ``base``. Remote không phải GitHub thì None."""
    found = re.match(r"^(?:https://github\.com/|git@github\.com:)([^/]+)/(.+?)(?:\.git)?/?$", remote_url.strip())
    if not found:
        return None
    return f"https://github.com/{found.group(1)}/{found.group(2)}/compare/{quote(base)}...{quote(branch, safe='')}?expand=1"


def _commit(repo: Path, items: list[tuple[str, codeguard.Change]], message: str, index: Path) -> tuple[str, str, list[str]]:
    """Commit (từ HEAD của ``repo``) gồm đúng các file (đường dẫn trong repo, thay đổi). Trả (commit, base, drift)."""
    env = {**os.environ, **_AUTHOR, "GIT_INDEX_FILE": str(index),
           "GIT_COMMITTER_NAME": _AUTHOR["GIT_AUTHOR_NAME"], "GIT_COMMITTER_EMAIL": _AUTHOR["GIT_AUTHOR_EMAIL"]}
    base = _git(["rev-parse", "HEAD"], cwd=repo)
    # File đã khác HEAD từ trước khi agent sửa (bản sửa ca trước chưa gộp, sửa tay): commit mang theo cả phần khác đó.
    drift = []
    try:
        _git(["read-tree", "HEAD"], env, cwd=repo)
        for rel, change in items:
            head = _head_blob(rel, cwd=repo)
            if (head[1] if head else None) != change.before:
                drift.append(change.rel)
            if change.after is None:
                _git(["update-index", "--force-remove", "--", rel], env, cwd=repo)
                continue
            sha = _git(["hash-object", "-w", "--stdin"], env, data=change.after, cwd=repo)
            mode = head[0] if head else "100644"
            _git(["update-index", "--add", "--cacheinfo", f"{mode},{sha},{rel}"], env, cwd=repo)
        tree = _git(["write-tree"], env, cwd=repo)
        commit = _git(["commit-tree", tree, "-p", base, "-F", "-"], env, data=message.encode("utf-8"), cwd=repo)
    finally:
        index.unlink(missing_ok=True)
    return commit, base, drift


def push_fix(job_id: str, job_dir: Path, changes: list[codeguard.Change], message: str) -> dict | None:
    """Kiểu cũ: một commit monorepo. Trả {branch, commit, base, drift} hoặc None nếu máy không bật."""
    if not GIT_REMOTE or not changes:
        return None
    commit, base, drift = _commit(REPO, [(c.rel, c) for c in changes], message, job_dir / "git-index")
    branch = branch_name(job_id)
    _git(["push", GIT_REMOTE, f"{commit}:refs/heads/{branch}"], timeout=180)
    return {"branch": branch, "commit": commit, "base": base, "remote": GIT_REMOTE, "drift": drift}


def push_components(job_id: str, job_dir: Path, changes: list[codeguard.Change], message: str, info: dict) -> list[dict]:
    """Khu làm việc: mỗi repo bị sửa một commit + nhánh agent/<mã ca>. Lỗi repo nào ghi ở repo đó, không chặn repo khác."""
    if not (USE_WORKSPACE and WORKSPACE_PUSH) or not changes:
        return []
    groups: dict[str, list[tuple[str, codeguard.Change]]] = {}
    for change in changes:
        head, _, rest = change.rel.partition("/")
        groups.setdefault(head, []).append((rest, change))
    branch = branch_name(job_id)
    results = []
    for component in COMPONENTS:
        items = groups.get(component["dir"])
        if not items:
            continue
        repo = WORKSPACE / component["dir"]
        meta = info.get(component["dir"]) or {}
        result = {"component": component["dir"], "branch": branch, "ref": meta.get("ref"), "base": component["base"],
                  "remote": component["url"], "files": [rel for rel, _ in items]}
        try:
            commit, parent, drift = _commit(repo, items, message, job_dir / f"git-index-{component['dir']}")
            _git(["push", "origin", f"{commit}:refs/heads/{branch}"], timeout=300, cwd=repo)
            result.update(commit=commit, parent=parent, drift=drift,
                          compare=compare_url(component["url"], component["base"], branch))
        except (PublishError, OSError, subprocess.TimeoutExpired) as reason:
            result["error"] = str(reason)[:400]
        results.append(result)
    return results
