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

import scoring
from config import BACKEND_URL, REPLAY_CONCURRENCY, REPLAY_TIMEOUT_S, REPO
from evidence import test_database as database

# Khoá gắn với hồ sơ/phiên thật: gửi lại thì lượt thử dính vào hồ sơ của người dân.
_DROP_OPTIONS = {"dossierId", "sessionId", "conversation_id", "upload_session_id", "consent_id", "channel"}
_TRACE_WAIT_S = 6
# Thanh tra chạy nền sau khi /process trả lượt điền đầu; backend thử đặt SECOND_PASS_TIMEOUT_SECONDS=60 (deploy/compose.*.yml).
_SECOND_PASS_WAIT_S = 90
# fillSupports bản extension Auto Fill gửi cho thủ tục có thanh tra (popup.js); hộ kinh doanh gửi riêng secondPassHkd.
_SECOND_PASS_SUPPORTS = ["secondPass", "secondPassLegacy", "secondPassAngular", "secondPassArea", "secondPassFormio", "secondPassBacNinh"]


class LoginError(Exception):
    pass


def replay_options(original: dict, tag: str) -> dict:
    options = {k: v for k, v in (original or {}).items() if k not in _DROP_OPTIONS}
    options["labRun"] = tag
    return options


def wants_second_pass(case: dict) -> bool:
    """Chạy lại có thanh tra khi và chỉ khi lượt gốc đã chạy thanh tra: giữ đúng điều kiện của lượt gốc."""
    info = case.get("thanhTra") or {}
    return bool(info.get("has") and info.get("ran")) and not is_attach(case)


def second_pass_options(options: dict, case: dict) -> dict:
    """Bật / tắt thanh tra cho lần chạy lại qua fillSupports (backend thử bật SECOND_PASS_ENABLED cho mọi tài khoản).

    Lượt gốc không chạy thanh tra → bỏ mọi năng lực secondPass*, kẻo lần chạy lại có thanh tra còn lượt gốc thì không.
    Lượt gốc có thanh tra mà options không mang fillSupports (lượt trợ lý gọi pipeline trực tiếp) → khai như extension."""
    supports = options.get("fillSupports")
    if not wants_second_pass(case):
        if isinstance(supports, list):
            options["fillSupports"] = [s for s in supports if not str(s).startswith("secondPass")]
        return options
    if not isinstance(supports, list) or not any(str(s).startswith("secondPass") for s in supports):
        kind = (case.get("thanhTra") or {}).get("kind")
        options["fillSupports"] = ["secondPassHkd"] if kind == "hkd" else list(_SECOND_PASS_SUPPORTS)
    return options


def wait_second_pass(request_id: str, wait_s: float = _SECOND_PASS_WAIT_S) -> dict | None:
    """Kết quả thanh tra của một lần chạy lại, đọc thẳng collection second_pass của backend thử (có cả biên bản).
    None = backend không chạy thanh tra cho lượt này."""
    db = database()
    deadline = time.monotonic() + wait_s
    while True:
        doc = db.second_pass.find_one({"_id": request_id})
        if doc and doc.get("status") != "pending":
            return doc
        if time.monotonic() > deadline:
            return {"status": "pending", "reason": "quá giờ chờ"} if doc else None
        time.sleep(1)


def apply_second_pass(body: dict, doc: dict | None, number: int, out_dir: Path) -> dict:
    """Ghép bản vá thanh tra vào kết quả: response.fields = giá trị cuối lên form, firstPassFields = lượt điền đầu.
    Biên bản đầy đủ ghi ra run<n>_second_pass.json cho agent đọc. Trả tóm tắt để hiện trên web."""
    if not doc:
        return {"status": "none"}
    patch = doc.get("fields") or []
    rulings = doc.get("rulings") or []
    (out_dir / f"run{number}_second_pass.json").write_text(json.dumps(
        {"status": doc.get("status"), "reason": doc.get("reason"), "ms": doc.get("ms"), "patch": patch, "rulings": rulings,
         "timing": doc.get("timing") or {}}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if doc.get("status") == "done":
        body["firstPassFields"] = body.get("fields") or []
        body["fields"] = scoring.merge_patch(body["firstPassFields"], patch)
    outcomes: dict[str, int] = {}
    for ruling in rulings:
        if isinstance(ruling, dict) and ruling.get("outcome"):
            outcomes[ruling["outcome"]] = outcomes.get(ruling["outcome"], 0) + 1
    return {
        "status": doc.get("status"), "reason": doc.get("reason"), "ms": doc.get("ms"), "outcomes": outcomes,
        "patched": [scoring.field_key(f) for f in patch if isinstance(f, dict)],
    }


def login(username: str, password: str) -> dict:
    """Đăng nhập như mọi client. Kết quả điền phụ thuộc xã/tỉnh nên tài khoản này quyết định cách chạy lại."""
    try:
        response = httpx.post(f"{BACKEND_URL}/auth/login", json={"username": username, "password": password}, timeout=30)
    except httpx.HTTPError as reason:
        raise LoginError(f"Không gọi được backend để đăng nhập: {reason}") from reason
    if response.status_code != 200:
        raise LoginError(f"Không đăng nhập được tài khoản {username}. Kiểm tra lại mật khẩu.")
    return response.json()


_SHADOW_ROLES = {"user", "commune", "province"}


def shadow_account(account: dict) -> dict:
    """Tài khoản test cho mọi lượt chạy lại: đúng username / xã / tỉnh của tài khoản đã điền req, tạo trên Mongo của backend
    thử. Người vận hành không phải nhập tài khoản nào.

    Req lấy từ production thì tài khoản gốc không có ở Mongo local. Mật khẩu ngẫu nhiên, chỉ giữ trong RAM của job; mỗi
    lần tạo ca đặt lại. Chỉ ghi đè tài khoản do chính dịch vụ tạo (cờ autotest_shadow): trùng tài khoản test có sẵn của
    người khác thì dùng tên ``autotest-<username>`` cùng xã / tỉnh (``renamed``), không đổi mật khẩu của người ta.
    """
    import secrets

    import verify

    original = str(account.get("username") or "").strip().lower()
    users = database().users
    username = original or "autotest-khong-ten"
    existing = users.find_one({"username": username}, {"autotest_shadow": 1})
    if existing and not existing.get("autotest_shadow"):
        # Trùng tài khoản test có sẵn của người khác ở local: không đổi mật khẩu của nó, dùng tên riêng cùng xã / tỉnh.
        username = f"autotest-{original}"
    password = secrets.token_urlsafe(18)
    compose, cwd, service = verify._compose()
    role = account.get("role") if account.get("role") in _SHADOW_ROLES else "user"
    # Dạng --khoá=giá-trị: mật khẩu ngẫu nhiên có thể bắt đầu bằng "-", argparse sẽ hiểu nhầm là một tuỳ chọn.
    cmd = [*compose, "exec", "-T", service, "python", "-m", "scripts.seed_user", f"--username={username}",
           f"--password={password}", f"--name={account.get('name') or username} (auto-test)", f"--role={role}"]
    if account.get("xa"):
        cmd.append(f"--xa={account['xa']}")
    if account.get("tinh"):
        cmd.append(f"--tinh={account['tinh']}")
    env = verify._compose_env()
    code, output = verify.run(cmd, cwd, 180, threading.Event(), env)
    if code != 0:
        raise LoginError(f"Không tạo được tài khoản chạy lại {username} trên backend thử: {output.strip()[-300:]}")
    users.update_one({"username": username}, {"$set": {"autotest_shadow": True}})
    return {"username": username, "password": password, "renamed": username != original}


def clear_ocr_cache(file_shas: list[str]) -> None:
    """Bỏ cache OCR của đúng các tệp này để lượt sau OCR mới thật; lượt chạy tự ghi lại cache ngay sau đó.

    Làm từ ngoài nên không cần cờ riêng trong backend. Khoá là "<version>:<sha256>", so theo đuôi để
    backend đổi version vẫn trúng.
    """
    shas = [s for s in file_shas if s]
    if shas:
        database().ocr_cache.delete_many({"_id": {"$regex": f":({'|'.join(map(re.escape, shas))})$"}})


def read_trace(request_id: str, kind: str = "autofill") -> dict:
    """Trace ghi nền sau khi trả kết quả nên phải chờ. ocrFresh=None nghĩa là không xác minh được."""
    db = database()
    deadline = time.monotonic() + _TRACE_WAIT_S
    while True:
        steps = db.trace_steps.find_one({"_id": f"{request_id}:{kind}"}, {"ocr.cache": 1, "timing.f": 1})
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


def is_attach(case: dict) -> bool:
    return case.get("kind") == "attach"


def attach_result(case: dict, body: dict, number: int, out_dir: Path) -> dict:
    """Lượt đính kèm: kế hoạch backend trả quy thành ô ảo (scoring.attach_fields) đặt vào response.fields để chấm như lượt
    điền. Kế hoạch đầy đủ ghi ra run<n>_plan.json cho agent đọc."""
    plan = [item for item in body.get("attachments") or [] if isinstance(item, dict)]
    (out_dir / f"run{number}_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    # replaceFiles là tệp nén base64 (cỡ MB) cho cổng giới hạn dung lượng: chỉ giữ tên, kẻo runs.json phình.
    replaced = [item.get("name") or item.get("fileIndex") for item in body.get("replaceFiles") or [] if isinstance(item, dict)]
    body = {k: v for k, v in body.items() if k != "replaceFiles"}
    if replaced:
        body["replacedFiles"] = replaced
    return {**body, "fields": scoring.attach_fields(plan, case.get("pageCounts"), body.get("errors"))}


def run_once(case: dict, number: int, tag: str, token: str, out_dir: Path) -> dict:
    files = []
    metadata = []
    for item in case["storedFiles"]:
        mime = item.get("type") or "application/octet-stream"
        files.append(("files", (item["name"], (REPO / item["path"]).read_bytes(), mime)))
        metadata.append({"name": item["name"], "type": mime, "role": item.get("role") or "doc"})
    data = {
        "action": "attach" if is_attach(case) else "fill",
        "procedure": case["procedure"],
        "options": json.dumps(second_pass_options(replay_options(case.get("options") or {}, tag), case), ensure_ascii=False),
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
        if is_attach(case):
            body = attach_result(case, body, number, out_dir)
        elif request_id and wants_second_pass(case):
            result["secondPass"] = apply_second_pass(body, wait_second_pass(request_id), number, out_dir)
        result.update(status="partial" if errors else "ok", requestId=request_id, response=body)
        if request_id:
            trace = read_trace(request_id, "attach" if is_attach(case) else "autofill")
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
