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

from config import (
    BACKEND_URL, BE, COMPOSE_FILE, COMPOSE_SERVICE, EXT, MAIN_BE, REGRESSION, REGRESSION_CASES, RUNS, SUPPORT, USE_WORKSPACE,
    server_problems,
)

_TREES = ("app", "tests")
_SUMMARY = re.compile(r"(\d+) (failed|passed|skipped|errors?)\b")
# Backend thử đang chạy code nào: khoá cây code lúc build gần nhất. Khu làm việc đổi tag / ca khác → build lại trước khi chạy.
_STACK_MARK = RUNS / "_stack.json"


def _compose_env() -> dict | None:
    """Biến cho deploy/compose.local.yml và compose.server.yml: build từ cây backend agent đang sửa (khu làm việc), dùng .env
    của backend local (server: bản chép .env production), dữ liệu upload riêng. compose.prod.yml (máy local kiểu cũ) không cần."""
    if not COMPOSE_FILE:
        return None
    env = dict(os.environ)
    env.update(AUTOTEST_BE_DIR=str(BE), AUTOTEST_MAIN_ENV=str(MAIN_BE / ".env"), AUTOTEST_DATA_DIR=str(RUNS / "_backend_data"))
    return env


def _compose() -> tuple[list[str], Path, str]:
    """Lệnh compose, thư mục chạy, tên service. Máy local: compose.prod.yml của backend như CLAUDE.md. Server: compose.server.yml
    (backend thử, project riêng, cổng riêng): compose.prod.yml trên server trolyhoso là build đè backend production."""
    if COMPOSE_FILE:
        path = Path(COMPOSE_FILE).resolve()
        return ["docker", "compose", "-f", str(path)], path.parent, COMPOSE_SERVICE
    if server_problems():
        raise RuntimeError("Cấu hình server thiếu AUTOTEST_COMPOSE_FILE: không build, kẻo đè backend production.")
    return ["docker", "compose", "-f", "compose.prod.yml"], BE, "app"
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
    """Khoá nội dung cây code. Repo git (khu làm việc): commit + phần chưa commit, nên mọi ca cùng tag dùng chung baseline
    dù checkout lại làm đổi mtime. Thư mục thường (máy cũ): theo kích thước + mtime."""
    if (base / ".git").exists():
        return _git_tree_key(base, trees)
    digest = hashlib.sha1()
    for tree in trees:
        for path in sorted((base / tree).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
                stat = path.stat()
                digest.update(f"{path.relative_to(base)}|{stat.st_size}|{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def _git_tree_key(base: Path, trees: tuple[str, ...]) -> str:
    def git(*args: str) -> bytes:
        return subprocess.run(["git", "-c", "core.autocrlf=false", *args], cwd=base, capture_output=True, timeout=120).stdout

    paths = [t for t in trees if t != "."] or ["."]
    digest = hashlib.sha1(b"git|" + git("rev-parse", "HEAD").strip())
    digest.update(git("diff", "HEAD", "--binary", "--", *paths))
    for rel in sorted(git("ls-files", "--others", "--exclude-standard", "--", *paths).decode("utf-8", "replace").splitlines()):
        file = base / rel
        digest.update(f"\n+{rel}\n".encode())
        if file.is_file():
            digest.update(file.read_bytes())
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


def extension_tests(cancel: threading.Event, root: Path = EXT) -> dict:
    """Extension không có test runner: chạy từng file bằng node, đếm cả tests/*.test.js và tests/test-*.js.

    ``root`` = EXT (Auto Fill) hoặc TROLY (trợ lý), hai extension cùng kiểu bộ test.
    """
    files = sorted({*(root / "tests").glob("*.test.js"), *(root / "tests").glob("test-*.js")})

    def one(path: Path) -> str | None:
        code, _ = run(["node", str(path)], root, 180, cancel, _pytest_env())
        return None if code == 0 else path.name

    with ThreadPoolExecutor(max_workers=6) as pool:
        failed = sorted(name for name in pool.map(one, files) if name)
    return {"total": len(files), "failed": failed}


def extension_baseline(cancel: threading.Event, root: Path = EXT) -> dict:
    """Bộ test extension nhiều test khớp regex trên source nên có thể đỏ sẵn: so trước/sau, không đòi về 0."""
    cache = RUNS / "_baseline"
    cache.mkdir(parents=True, exist_ok=True)
    prefix = "ext" if root == EXT else "troly"
    path = cache / f"{prefix}-{tree_key(root, ('.',))}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = extension_tests(cancel, root)
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


# Cây tests/handfree (trợ lý) lỗi collect sẵn trên máy local (thiếu protobuf cho ASR): chạy riêng, so trước/sau như cây chính.
_HANDFREE_ARGS = [
    "tests/handfree/unit", "tests/handfree/integration", "-q", "--continue-on-collection-errors",
    "-p", "no:cacheprovider", "-p", "win_socketpair", "--tb=native", "-rfE",
]


def handfree_tests(cancel: threading.Event) -> dict:
    code, output = run([sys.executable, "-m", "pytest", *_HANDFREE_ARGS], BE, 1200, cancel, _pytest_env())
    parsed = parse_pytest(output)
    if code not in (0, 1) or not parsed["passed"]:
        return {**parsed, "broken": True, "tail": output[-3000:]}
    return parsed


def handfree_baseline(cancel: threading.Event) -> dict:
    cache = RUNS / "_baseline"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"hf-{tree_key()}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = handfree_tests(cancel)
    if not result.get("broken"):
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
    """Bước 3–5. Luôn chỉ rõ file compose: compose mặc định đá app sang network khác làm web trace 502."""
    compose, cwd, service = _compose()
    extra = [] if COMPOSE_FILE else ["--remove-orphans"]
    env = _compose_env()
    key = tree_key() if USE_WORKSPACE else None
    code, output = run([*compose, "up", "-d", "--build", *extra, service], cwd, 1500, cancel, env)
    if code != 0:
        return {"ok": False, "step": "build", "output": output[-4000:]}
    _, ps = run([*compose, "ps", service, "--format", "{{.Name}} {{.Status}}"], cwd, 60, cancel, env)
    deadline = time.monotonic() + 120
    health = ""
    while time.monotonic() < deadline:
        if cancel.is_set():
            raise Stopped()
        alive, health = healthz()
        if alive:
            if key:
                _STACK_MARK.parent.mkdir(parents=True, exist_ok=True)
                _STACK_MARK.write_text(json.dumps({"key": key, "at": time.time()}), encoding="utf-8")
            return {"ok": True, "ps": ps.strip(), "health": health}
        time.sleep(2)
    return {"ok": False, "step": "healthz", "ps": ps.strip(), "health": health}


def stack_current() -> bool:
    """Backend thử đang sống và chạy đúng cây code hiện có trong khu làm việc."""
    try:
        mark = json.loads(_STACK_MARK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return mark.get("key") == tree_key() and healthz()[0]


def ensure_stack(cancel: threading.Event) -> dict | None:
    """Khu làm việc vừa đặt lại tag (hoặc backend thử chưa bật): build lại trước khi chạy lại req. None = đã khớp sẵn."""
    if not USE_WORKSPACE or stack_current():
        return None
    return deploy(cancel)


# ---- bộ ca hồi quy (regression/) --------------------------------------------------------------------------------------

def regression_cases() -> list[Path]:
    return sorted(REGRESSION_CASES.rglob("*.json")) if REGRESSION_CASES.is_dir() else []


def regression_run(cancel: threading.Event, be: Path = BE, cases: list[Path] | None = None) -> dict:
    """Phát lại các ca hồi quy trên cây backend ``be`` (OCR/LLM đã ghi, không mạng). {id: {ok, error}}, broken nếu runner sập."""
    cases = regression_cases() if cases is None else cases
    if not cases:
        return {"results": {}, "total": 0}
    out = RUNS / "_regression_out.json"
    out.unlink(missing_ok=True)
    cmd = [sys.executable, str(REGRESSION / "run.py"), "--be", str(be), "--json", str(out), *map(str, cases)]
    code, output = run(cmd, be, 900, cancel, _pytest_env())
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"results": {}, "total": len(cases), "broken": True, "tail": output[-3000:]}
    results = {item["id"]: {"ok": bool(item.get("ok")), "error": item.get("error")} for item in data.get("results", [])}
    return {"results": results, "total": len(results)}


def regression_baseline(cancel: threading.Event) -> dict:
    cases = regression_cases()
    digest = hashlib.sha1(tree_key().encode())
    for path in cases:
        digest.update(path.name.encode() + path.read_bytes())
    cache = RUNS / "_baseline"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"reg-{digest.hexdigest()}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = regression_run(cancel, cases=cases)
    if not result.get("broken"):
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def compare_regression(before: dict, after: dict) -> dict:
    """Ca đang đạt trước khi sửa mà nay trượt = hồi quy. Ca trượt sẵn không tính (code production chưa có bản sửa đó)."""
    passed_before = {k for k, v in before.get("results", {}).items() if v["ok"]}
    now = after.get("results", {})
    new = sorted(k for k in passed_before if k in now and not now[k]["ok"])
    return {
        "ok": not after.get("broken") and not new,
        "new": new,
        "errors": {k: now[k]["error"] for k in new if now[k].get("error")},
        "fixed": sorted(k for k, v in now.items() if v["ok"] and k not in passed_before),
        "total": after.get("total", 0),
        "passed": sum(1 for v in now.values() if v["ok"]),
        "broken": bool(after.get("broken")),
        "tail": after.get("tail", ""),
    }
