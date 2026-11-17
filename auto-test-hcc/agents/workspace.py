"""Khu làm việc của agent: mỗi ca một cây code sạch, đặt đúng tag release đang chạy production.

- 3 repo thật (backend, extension Auto Fill, extension trợ lý) được clone riêng vào ``auto-test-hcc/.workspace/`` (gitignore),
  không dùng thư mục làm việc hay các bản clone của người phát triển.
- Đầu mỗi ca: lưu phần ca trước còn để lại (bản sửa đạt / Cần người xem) vào thư mục ca đó, rồi dọn sạch và đặt cả 3 repo
  về tag release mới nhất (hoặc ref ép trong cấu hình). Đường dẫn khu làm việc cố định: id extension unpacked của bot và
  cache build Docker giữ được qua các ca.
- Extension Auto Fill trong khu làm việc được trỏ sang backend thử (EXTENSION_BACKEND). Hai file này codeguard cấm agent
  sửa, nên không bao giờ lọt vào commit.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from config import COMPONENTS, EXTENSION_BACKEND, RUNS, USE_WORKSPACE, WORKSPACE

EXT_DIR = "auto-fill-hcc-extension"
_GIT = ["git", "-c", "core.autocrlf=false", "-c", "core.longpaths=true"]
_OWNER = WORKSPACE / ".autotest-job"
# Hai file chỉ đổi trong khu làm việc để extension của bot gọi backend thử; không tính là phần ca để lại.
_POINTED = {EXT_DIR: ("api/config.js", "manifest.json")}


class WorkspaceError(Exception):
    pass


def git(cwd: Path, *args: str, timeout: int = 600, env: dict | None = None, data: bytes | None = None) -> str:
    proc = subprocess.run([*_GIT, *args], cwd=cwd, capture_output=True, timeout=timeout, env=env, input=data)
    if proc.returncode != 0:
        raise WorkspaceError(f"git {args[0]} ({cwd.name}): {proc.stderr.decode('utf-8', 'replace').strip()[:400]}")
    return proc.stdout.decode("utf-8", "replace").strip()


def owner() -> str | None:
    """Ca đang giữ khu làm việc (code trong đó là của ca này)."""
    try:
        return _OWNER.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def component_of(rel: str) -> str | None:
    head = rel.split("/", 1)[0]
    return head if any(c["dir"] == head for c in COMPONENTS) else None


def latest_ref(path: Path, component: dict) -> str:
    if component["ref"]:
        return component["ref"]
    tags = [t for t in git(path, "tag", "--list", component["tags"], "--sort=-version:refname").splitlines() if t.strip()]
    if not tags:
        raise WorkspaceError(f"{component['dir']}: không có tag release nào khớp {component['tags']!r}.")
    return tags[0]


def _clone(component: dict, log: Callable[[str], None]) -> Path:
    path = WORKSPACE / component["dir"]
    if (path / ".git").exists():
        return path
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    log(f"Clone {component['url']} vào khu làm việc (lần đầu, có thể mất vài phút)…")
    git(WORKSPACE, "clone", "--quiet", "--no-checkout", component["url"], component["dir"], timeout=3600)
    git(path, "config", "core.autocrlf", "false")
    git(path, "config", "core.longpaths", "true")
    return path


def _pending_diff(path: Path, skip: tuple[str, ...]) -> str:
    """Diff (cả file mới) của phần chưa commit, bỏ các file chỉ trỏ backend thử. Dùng index tạm, không đụng index thật."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git(path, "read-tree", "HEAD", env=env)
        git(path, "add", "-A", env=env)
        if skip:
            git(path, "reset", "-q", "HEAD", "--", *skip, env=env)
        return git(path, "diff", "--cached", "--binary", "HEAD", env=env)


def save_leftover(log: Callable[[str], None]) -> str | None:
    """Ca trước còn để lại code (bản sửa đạt chưa ai gộp, hoặc Cần người xem): lưu vào thư mục ca đó trước khi dọn."""
    previous = owner()
    chunks = []
    for component in COMPONENTS:
        path = WORKSPACE / component["dir"]
        if not (path / ".git").exists():
            continue
        try:
            diff = _pending_diff(path, _POINTED.get(component["dir"], ()))
        except WorkspaceError:
            continue
        if diff:
            chunks.append(f"# repo {component['dir']}\n{diff}\n")
    if not chunks or not previous:
        return None
    target = RUNS / previous / "workspace-left.patch"
    if target.parent.is_dir():
        target.write_text("".join(chunks), encoding="utf-8")
        log(f"Khu làm việc còn code của ca {previous}: đã lưu vào {target.name} của ca đó trước khi dọn.")
    return previous


def point_extension(ext: Path, backend: str | None = None) -> None:
    """Extension của bot gọi backend thử: đổi BACKEND_URL + thêm quyền host. Chỉ trong khu làm việc."""
    backend = backend or EXTENSION_BACKEND
    config = ext / "api/config.js"
    text = config.read_text(encoding="utf-8")
    pointed, count = re.subn(r'^const BACKEND_URL = "[^"]*";', f'const BACKEND_URL = "{backend}";', text, count=1, flags=re.M)
    if not count:
        raise WorkspaceError("Không tìm thấy dòng const BACKEND_URL trong api/config.js của extension.")
    config.write_text(pointed, encoding="utf-8", newline="")
    manifest_path = ext / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hosts = list(manifest.get("host_permissions") or [])
    ws = re.sub(r"^http", "ws", backend)
    for host in (f"{backend}/*", f"{ws}/*"):
        if host not in hosts:
            hosts.insert(0, host)
    manifest["host_permissions"] = hosts
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")


def prepare(job_id: str, log: Callable[[str], None]) -> dict:
    """Đặt cả 3 repo về tag release mới nhất, dọn sạch. Trả {thư mục: {ref, commit, url, base}}."""
    if not USE_WORKSPACE:
        return {}
    save_leftover(log)
    info = {}
    for component in COMPONENTS:
        path = _clone(component, log)
        try:
            git(path, "fetch", "--quiet", "--tags", "--force", "--prune", "origin", timeout=1800)
        except (WorkspaceError, subprocess.TimeoutExpired) as reason:
            log(f"Không tải được tag mới của {component['dir']} ({str(reason)[:160]}), dùng tag đã có trên máy.")
        ref = latest_ref(path, component)
        commit = git(path, "rev-parse", f"{ref}^{{commit}}")
        git(path, "checkout", "--quiet", "--detach", "--force", commit, timeout=1200)
        git(path, "clean", "-fdq")
        info[component["dir"]] = {"ref": ref, "commit": commit, "url": component["url"], "base": component["base"]}
    point_extension(WORKSPACE / EXT_DIR)
    # Chứng cứ của ca khác (giấy tờ thật) không được nằm trong cây agent đọc được.
    cases = WORKSPACE / "auto-test-hcc" / "runs"
    shutil.rmtree(cases, ignore_errors=True)
    cases.mkdir(parents=True, exist_ok=True)
    _OWNER.write_text(job_id, encoding="utf-8")
    log("Khu làm việc: " + ", ".join(f"{d} @ {v['ref']} ({v['commit'][:8]})" for d, v in info.items()))
    return info
