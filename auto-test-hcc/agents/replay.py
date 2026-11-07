"""Chạy lại một req qua /api/v2/process y như extension, bằng tài khoản người dùng đã đăng nhập cho job."""
from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

from config import BACKEND_URL, REPLAY_CONCURRENCY, REPLAY_TIMEOUT_S, REPO
from evidence import database

# Khoá gắn với hồ sơ/phiên thật: gửi lại thì lượt thử dính vào hồ sơ của người dân.
_DROP_OPTIONS = {"dossierId", "sessionId", "conversation_id", "upload_session_id", "consent_id", "channel"}
_TRACE_WAIT_S = 6


class LoginError(Exception):
    pass


def replay_options(original: dict, tag: str) -> dict:
    options = {k: v for k, v in (original or {}).items() if k not in _DROP_OPTIONS}
    options["labRun"] = tag
    return options


def login(username: str, password: str) -> dict:
    """Đăng nhập như mọi client. Kết quả điền phụ thuộc xã/tỉnh nên tài khoản này quyết định cách chạy lại."""
    try:
        response = httpx.post(f"{BACKEND_URL}/auth/login", json={"username": username, "password": password}, timeout=30)
    except httpx.HTTPError as reason:
        raise LoginError(f"Không gọi được backend để đăng nhập: {reason}") from reason
    if response.status_code != 200:
        raise LoginError(f"Không đăng nhập được tài khoản {username}. Kiểm tra lại mật khẩu.")
    return response.json()


def clear_ocr_cache(file_shas: list[str]) -> None:
    """Bỏ cache OCR của đúng các tệp này để lượt sau OCR mới thật; lượt chạy tự ghi lại cache ngay sau đó.

    Làm từ ngoài nên không cần cờ riêng trong backend. Khoá là "<version>:<sha256>", so theo đuôi để
    backend đổi version vẫn trúng.
    """
    shas = [s for s in file_shas if s]
    if shas:
        database().ocr_cache.delete_many({"_id": {"$regex": f":({'|'.join(map(re.escape, shas))})$"}})


def read_trace(request_id: str) -> dict:
    """Trace ghi nền sau khi trả kết quả nên phải chờ. ocrFresh=None nghĩa là không xác minh được."""
    db = database()
    deadline = time.monotonic() + _TRACE_WAIT_S
    while True:
        steps = db.trace_steps.find_one({"_id": f"{request_id}:autofill"}, {"ocr.cache": 1, "timing.f": 1})
        trace = db.traces.find_one({"request_id": request_id}, {"ocr_text": 1})
        if steps and trace:
            caches = [ref.get("cache") for ref in steps.get("ocr") or []]
            return {
                "ocrText": trace.get("ocr_text") or "",
                "ocrFresh": bool(caches) and all(c == "miss" for c in caches),
                # Vài pipeline Bắc Ninh dùng lại câu trả lời LLM 30 phút: lượt đó không đo được độ dao động của LLM.
                "llmReused": bool(((steps.get("timing") or {}).get("f") or {}).get("llm_reused")),
            }
        if time.monotonic() > deadline:
            return {"ocrText": (trace or {}).get("ocr_text") or "", "ocrFresh": None, "llmReused": None}
        time.sleep(0.5)


def run_once(case: dict, number: int, tag: str, token: str, out_dir: Path) -> dict:
    files = []
    metadata = []
    for item in case["storedFiles"]:
        mime = item.get("type") or "application/octet-stream"
        files.append(("files", (item["name"], (REPO / item["path"]).read_bytes(), mime)))
        metadata.append({"name": item["name"], "type": mime, "role": item.get("role") or "doc"})
    data = {
        "action": "fill",
        "procedure": case["procedure"],
        "options": json.dumps(replay_options(case.get("options") or {}, tag), ensure_ascii=False),
        "fileMetadata": json.dumps(metadata, ensure_ascii=False),
    }
    started = time.monotonic()
    result: dict = {"n": number, "startedAt": datetime.now(timezone.utc).isoformat()}
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/v2/process",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REPLAY_TIMEOUT_S,
        )
        result["ms"] = int((time.monotonic() - started) * 1000)
        if response.status_code >= 400:
            result.update(status="error", error=f"HTTP {response.status_code}: {response.text[:300]}")
            return result
        body = response.json()
        errors = body.get("errors") if isinstance(body.get("errors"), list) else []
        request_id = body.get("requestId")
        result.update(status="partial" if errors else "ok", requestId=request_id, response=body)
        if request_id:
            trace = read_trace(request_id)
            (out_dir / f"run{number}_ocr.txt").write_text(trace.pop("ocrText"), encoding="utf-8")
            result.update(trace)
    except httpx.HTTPError as reason:
        result.update(status="error", ms=int((time.monotonic() - started) * 1000), error=f"{type(reason).__name__}: {reason}")
    return result


def replay(
    case: dict,
    count: int,
    phase: str,
    job_dir: Path,
    credentials: dict,
    cancel: threading.Event,
    on_run: Callable[[dict], None],
) -> list[dict]:
    """Chạy theo từng cặp, dọn cache trước mỗi cặp: dọn một lần đầu thì lượt sau lại trúng cache của lượt trước."""
    out_dir = job_dir / "replay" / phase
    out_dir.mkdir(parents=True, exist_ok=True)
    token = login(credentials["username"], credentials["password"])["accessToken"]
    shas = [f.get("sha256") for f in case["storedFiles"]]
    runs: list[dict] = []
    numbers = list(range(1, count + 1))
    with ThreadPoolExecutor(max_workers=REPLAY_CONCURRENCY) as pool:
        for start in range(0, count, REPLAY_CONCURRENCY):
            if cancel.is_set():
                break
            clear_ocr_cache(shas)
            chunk = numbers[start:start + REPLAY_CONCURRENCY]
            futures = [pool.submit(run_once, case, n, f"{phase}:{n}", token, out_dir) for n in chunk]
            for future in futures:
                run = future.result()
                runs.append(run)
                on_run(run)
    (out_dir / "runs.json").write_text(json.dumps(runs, ensure_ascii=False), encoding="utf-8")
    return runs


def strip_response(run: dict) -> dict:
    return {k: v for k, v in run.items() if k != "response"}
