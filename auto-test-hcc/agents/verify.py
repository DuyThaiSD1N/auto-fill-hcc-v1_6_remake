"""Quy trình bắt buộc của CLAUDE.md sau khi sửa backend: test pipeline → test toàn bộ → build → healthz.

Mã chạy các bước này, không phải agent: agent sửa code không có Bash, và kết quả test phải là thật.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from config import BACKEND_URL, BE, EXT, RUNS, SUPPORT

_TREES = ("app", "tests")
_SUMMARY = re.compile(r"(\d+) (failed|passed|skipped|errors?)\b")
_COMPOSE = ["docker", "compose", "-f", "compose.prod.yml"]
# Chỉ hai cây này; tests/handfree lỗi collect sẵn.
_FULL_ARGS = [
    "tests/unit", "tests/integration", "-q", "--continue-on-collection-errors",
    "-p", "no:cacheprovider", "-p", "win_socketpair", "--tb=native", "-rfE",
]


class Stopped(Exception):
    pass


def run(cmd: list[str], cwd: Path, timeout: int, cancel: threading.Event, env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    chunks: list[str] = []
    reader = threading.Thread(target=lambda: chunks.extend(proc.stdout), daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    while proc.poll() is None:
        if cancel.is_set():
            _kill(proc)
            raise Stopped()
        if time.monotonic() > deadline:
            _kill(proc)
            reader.join(timeout=2)
            return 124, "".join(chunks) + f"\n[quá thời gian {timeout}s]"
        time.sleep(0.3)
    reader.join(timeout=5)
    return proc.returncode, "".join(chunks)


def _kill(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.kill()


def _pytest_env() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(SUPPORT)
    return env


def parse_pytest(output: str) -> dict:
    counts = {"failed": 0, "passed": 0, "skipped": 0, "errors": 0}
    for line in reversed(output.splitlines()):
        found = _SUMMARY.findall(line)
        if found and (" in " in line or line.startswith("=")):
            for number, word in found:
                counts["errors" if word.startswith("error") else word] = int(number)
            break
    bad = sorted({
        line.split(" - ")[0].strip()
        for line in output.splitlines()
        if line.startswith(("FAILED ", "ERROR "))
    })
    return {**counts, "bad": bad}


def pipeline_tests(test_files: list[str], cancel: threading.Event) -> dict:
    """Bước 1. Có đỏ thì không được build."""
    if not test_files:
        return {"ok": False, "skipped": True, "summary": "Không tìm thấy file test của pipeline", "output": ""}
    cmd = [sys.executable, "-m", "pytest", *test_files, "-q", "-p", "no:cacheprovider", "-p", "win_socketpair", "--tb=short"]
    code, output = run(cmd, BE, 600, cancel, _pytest_env())
    parsed = parse_pytest(output)
    return {
        "ok": code == 0,
        "files": test_files,
        "summary": f"{parsed['passed']} passed, {parsed['failed']} failed, {parsed['errors']} errors",
        "output": output[-6000:],
    }


def find_test_files(pipeline: str | None, extra: list[str]) -> list[str]:
    files = {path.replace("\\", "/").split("auto-fill-hcc-backend/")[-1] for path in extra}
    if pipeline:
        # Test của pipeline hay có hậu tố (test_ho_tro_mai_tang_mapper.py), không chỉ đúng tên folder.
        files |= {path.relative_to(BE).as_posix() for path in (BE / "tests/unit").glob(f"test_{pipeline}*.py")}
    return sorted(f for f in files if (BE / f).is_file() and f.endswith(".py"))


def tree_key(base: Path = BE, trees: tuple[str, ...] = _TREES) -> str:
    digest = hashlib.sha1()
    for tree in trees:
        for path in sorted((base / tree).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
                stat = path.stat()
                digest.update(f"{path.relative_to(base)}|{stat.st_size}|{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def full_tests(cancel: threading.Event) -> dict:
    code, output = run([sys.executable, "-m", "pytest", *_FULL_ARGS], BE, 1200, cancel, _pytest_env())
    parsed = parse_pytest(output)
    if code not in (0, 1) or not parsed["passed"]:
        # Pytest sập (INTERNALERROR, quá giờ) thì không có số để so: coi là chưa biết, không phải là "không đỏ".
        return {**parsed, "broken": True, "tail": output[-3000:]}
    return parsed


def baseline(cancel: threading.Event) -> dict:
    """Số đỏ của cây code hiện tại, trước khi agent sửa. Cây không đổi thì dùng lại kết quả cũ."""
    cache = RUNS / "_baseline"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{tree_key()}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = full_tests(cancel)
    if not result.get("broken"):
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def compare(before: dict, after: dict) -> dict:
    new = sorted(set(after["bad"]) - set(before["bad"]))
    fixed = sorted(set(before["bad"]) - set(after["bad"]))
    return {
        "ok": not after.get("broken") and not new,
        "new": new,
        "fixed": fixed,
        "before": {k: before.get(k) for k in ("failed", "passed", "skipped", "errors")},
        "after": {k: after.get(k) for k in ("failed", "passed", "skipped", "errors")},
        "broken": bool(after.get("broken")),
        "tail": after.get("tail", ""),
    }


def extension_tests(cancel: threading.Event) -> dict:
    """Extension không có test runner: chạy từng file bằng node, đếm cả tests/*.test.js và tests/test-*.js."""
    files = sorted({*(EXT / "tests").glob("*.test.js"), *(EXT / "tests").glob("test-*.js")})

    def one(path: Path) -> str | None:
        code, _ = run(["node", str(path)], EXT, 180, cancel, _pytest_env())
        return None if code == 0 else path.name

    with ThreadPoolExecutor(max_workers=6) as pool:
        failed = sorted(name for name in pool.map(one, files) if name)
    return {"total": len(files), "failed": failed}


def extension_baseline(cancel: threading.Event) -> dict:
    """Bộ test extension nhiều test khớp regex trên source nên có thể đỏ sẵn: so trước/sau, không đòi về 0."""
    cache = RUNS / "_baseline"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"ext-{tree_key(EXT, ('.',))}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = extension_tests(cancel)
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def compare_extension(before: dict, after: dict) -> dict:
    new = sorted(set(after["failed"]) - set(before["failed"]))
    return {
        "ok": not new,
        "new": new,
        "fixed": sorted(set(before["failed"]) - set(after["failed"])),
        "total": after["total"],
        "failed": len(after["failed"]),
        "failedBefore": len(before["failed"]),
    }


def healthz() -> tuple[bool, str]:
    try:
        response = httpx.get(f"{BACKEND_URL}/healthz", timeout=5)
        return response.status_code == 200 and response.json().get("ok") is True, response.text[:200]
    except (httpx.HTTPError, ValueError) as reason:
        return False, f"{type(reason).__name__}: {reason}"


def deploy(cancel: threading.Event) -> dict:
    """Bước 3–5. Luôn -f compose.prod.yml: compose mặc định đá app sang network khác làm web trace 502."""
    code, output = run([*_COMPOSE, "up", "-d", "--build", "--remove-orphans", "app"], BE, 1500, cancel)
    if code != 0:
        return {"ok": False, "step": "build", "output": output[-4000:]}
    _, ps = run([*_COMPOSE, "ps", "app", "--format", "{{.Name}} {{.Status}}"], BE, 60, cancel)
    deadline = time.monotonic() + 120
    health = ""
    while time.monotonic() < deadline:
        if cancel.is_set():
            raise Stopped()
        alive, health = healthz()
        if alive:
            return {"ok": True, "ps": ps.strip(), "health": health}
        time.sleep(2)
    return {"ok": False, "step": "healthz", "ps": ps.strip(), "health": health}
