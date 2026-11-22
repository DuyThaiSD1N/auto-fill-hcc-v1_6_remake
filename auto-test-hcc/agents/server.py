"""Dịch vụ agent, chạy trên máy host: python auto-test-hcc/agents/server.py

Phải chạy ngoài Docker vì cần claude, repo và docker. Web gọi vào qua nginx của test-fe (/agent-api/).
"""
from __future__ import annotations

import hashlib
import json
import queue
import re
import subprocess
import sys
import threading
import time

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import claude_runner
import evidence
import lab
import remote
import replay
import workspace
from config import (
    PUBLISH_WEB,
    AUTH_BACKEND_URL, BACKEND_URL, DEFAULT_ROUNDS, DEFAULT_RUNS, GIT_REMOTE, HOST, MAX_ROUNDS, MAX_RUNS, PORT, RUNS,
    CASES, SERVER_MODE, USE_WORKSPACE, WORKSPACE_PUSH, server_problems,
)
from orchestrator import Job, Orchestrator, recover_interrupted, revert_fix
from typing import Literal

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
_AUTH_TTL_S = 30

app = FastAPI(title="auto-test-hcc agents", docs_url=None, redoc_url=None, openapi_url=None)
_auth_cache: dict[str, tuple[float, dict]] = {}


def require_operator(authorization: str = Header("")) -> dict:
    """Dịch vụ này đọc giấy tờ thật và sửa được code → chỉ super_admin, giống quyền xem dữ liệu ở Monitor."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Thiếu access token")
    key = hashlib.sha256(authorization.encode()).hexdigest()
    hit = _auth_cache.get(key)
    if hit and time.monotonic() - hit[0] < _AUTH_TTL_S:
        return hit[1]
    try:
        response = httpx.get(f"{AUTH_BACKEND_URL}/auth/me", headers={"Authorization": authorization}, timeout=10)
    except httpx.HTTPError as reason:
        raise HTTPException(503, f"Không gọi được backend: {reason}") from reason
    if response.status_code == 401:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    if response.status_code != 200:
        raise HTTPException(503, f"Backend trả HTTP {response.status_code} khi kiểm tra tài khoản")
    user = response.json()
    if user.get("role") != "super_admin":
        raise HTTPException(403, "Chỉ tài khoản super_admin (tài khoản Monitor) mới dùng được phần Agent tự sửa.")
    _auth_cache[key] = (time.monotonic(), user)
    return user


class Service:
    """Một hàng đợi một luồng: các job dùng chung cây code và stack Docker nên không được chạy song song."""

    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.tasks: queue.Queue[tuple[str, str]] = queue.Queue()
        self.secrets: dict[str, dict] = {}  # mật khẩu tài khoản chạy lại: chỉ trong RAM, không bao giờ ghi đĩa
        self.busy: str | None = None
        RUNS.mkdir(parents=True, exist_ok=True)
        for path in sorted(RUNS.glob("at_*/job.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            # Job "Thêm thủ tục mới" cũ: chức năng đã gỡ (2026-11-09), dữ liệu để nguyên trên đĩa, không nạp lên web.
            if data.get("kind") == "dev":
                continue
            job = Job(data)
            self.jobs[job.data["id"]] = job
            if job.data["status"] in ("queued", "running"):
                self.tasks.put(("recover", job.data["id"]))
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        while True:
            kind, job_id = self.tasks.get()
            job = self.jobs[job_id]
            self.busy = job_id
            try:
                if kind == "run":
                    if job.cancel.is_set():
                        job.update(status="stopped")
                    else:
                        Orchestrator(job, self.secrets[job_id]).run()
                elif kind == "revert":
                    revert_fix(job)
                else:
                    recover_interrupted(job)
            except Exception as reason:  # noqa: BLE001 — luồng worker không được chết vì một job
                job.log(f"{type(reason).__name__}: {reason}", level="error")
            finally:
                self.secrets.pop(job_id, None)
                self.busy = None

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Không tìm thấy job")
        return job


service = Service()


class Applicant(BaseModel):
    """Mốc người nộp cho lượt trợ lý đã hết ngữ cảnh — cùng khoá formContext mà extension gửi."""
    applicantFullname: str = Field("", max_length=200)
    applicantIdentityNumber: str = Field("", max_length=32)
    applicantBirthday: str = Field("", max_length=32)


class JobRequest(BaseModel):
    requestId: str
    description: str = Field(min_length=5, max_length=4000)
    # Để trống: dùng tài khoản đã điền req, dịch vụ tự tạo bản chạy lại trên Mongo của backend thử (replay.shadow_account).
    replayUsername: str = Field("", max_length=200)
    replayPassword: str = Field("", max_length=200)
    runs: int = Field(DEFAULT_RUNS, ge=1, le=MAX_RUNS)
    maxRounds: int = Field(DEFAULT_ROUNDS, ge=1, le=MAX_ROUNDS)
    reproduce: bool = True
    applicant: Applicant | None = None
    # Chỉ còn chạy lại qua backend (bỏ Chromium / cổng thật ngày 18/11/2026). Giữ trường để client cũ gửi "api" vẫn hợp lệ.
    mode: Literal["api"] = "api"
    # Sửa cho sản phẩm nào: Auto Fill (extension Auto Fill) hay trợ lý hồ sơ (kênh handfree của backend).
    target: Literal["autofill", "troly"] = "autofill"


def _lookup(request_id: str) -> dict:
    request_id = request_id.strip()
    if not _REQUEST_ID.match(request_id):
        raise HTTPException(400, "Mã req không hợp lệ")
    try:
        return evidence.lookup(request_id)
    except evidence.CaseError as reason:
        raise HTTPException(404, str(reason)) from reason


@app.get("/agent-api/health")
def health() -> dict:
    return {
        "ok": True, "claude": bool(claude_runner.available()), "busy": service.busy, "queued": service.tasks.qsize(),
        "server": SERVER_MODE, "git": bool(GIT_REMOTE) or (USE_WORKSPACE and WORKSPACE_PUSH),
        "workspace": USE_WORKSPACE, "workspaceOwner": workspace.owner() if USE_WORKSPACE else None,
        "publish": remote.publishing() if PUBLISH_WEB else None,
        # Web Monitor chỉ hiện nhóm menu Auto test khi dịch vụ có API lab (bản cũ không có khoá này).
        "lab": True,
    }


@app.get("/agent-api/requests/{request_id}")
def request_preview(request_id: str, _: dict = Depends(require_operator)) -> dict:
    return _lookup(request_id)


@app.post("/agent-api/jobs")
def create_job(body: JobRequest, user: dict = Depends(require_operator)) -> dict:
    preview = _lookup(body.requestId)
    if preview["missingFiles"]:
        raise HTTPException(400, "Tệp gốc của req không còn trên đĩa nên không chạy lại được.")
    if not claude_runner.available():
        raise HTTPException(503, "Máy chưa có lệnh claude.")
    # Tài khoản chạy lại luôn do dịch vụ dựng sẵn (cùng xã / tỉnh với tài khoản đã điền req), web không hỏi. API vẫn nhận
    # cặp tài khoản + mật khẩu nếu được gửi kèm, cho script cũ.
    username = body.replayUsername.strip()
    if username and not body.replayPassword:
        raise HTTPException(400, "Gửi tài khoản chạy lại thì phải kèm mật khẩu, hoặc bỏ cả hai để dịch vụ tự dựng tài khoản test.")
    try:
        credentials = (
            {"username": username, "password": body.replayPassword} if username
            else replay.shadow_account(preview["account"])
        )
        # Đăng nhập thử ngay: hỏng thì báo liền, đừng để chạy được nửa đường mới hỏng.
        account = replay.login(credentials["username"], credentials["password"])["user"]
    except replay.LoginError as reason:
        raise HTTPException(400, str(reason)) from reason
    warnings = []
    if credentials.get("renamed"):
        warnings.append(
            f"Mongo local đã có tài khoản {preview['account'].get('username')} của người khác nên chạy lại bằng "
            f"{credentials['username']} (cùng xã, tỉnh). Tuỳ chỉnh riêng theo tên tài khoản, nếu có, có thể ra khác lượt gốc."
        )
    source = preview["account"]
    if (account.get("xa"), account.get("tinh")) != (source.get("xa"), source.get("tinh")):
        warnings.append(
            f"Tài khoản chạy lại {account.get('username')} ({account.get('xa')}, {account.get('tinh')}) khác đơn vị của req "
            f"({source.get('xa')}, {source.get('tinh')}), các ô phụ thuộc xã/tỉnh có thể ra khác lượt gốc."
        )
    applicant = {k: v.strip() for k, v in (body.applicant.model_dump() if body.applicant else {}).items() if v.strip()}
    job = Job.create(
        request_id=preview["requestId"],
        description=body.description.strip(),
        created_by=user.get("username", ""),
        settings={
            "runs": body.runs, "maxRounds": body.maxRounds, "reproduce": body.reproduce,
            "replayAccount": credentials["username"], "replayShadow": not username, "applicant": applicant, "mode": body.mode,
            "target": body.target, "kind": preview.get("kind") or "autofill",
        },
        preview=preview,
        warnings=warnings,
    )
    job_id = job.data["id"]
    service.jobs[job_id] = job
    service.secrets[job_id] = {"username": credentials["username"], "password": credentials["password"]}
    service.tasks.put(("run", job_id))
    return job.view()


@app.get("/agent-api/jobs")
def list_jobs(_: dict = Depends(require_operator)) -> dict:
    items = [job.summary() for job in service.jobs.values()]
    return {"items": sorted(items, key=lambda item: item["createdAt"], reverse=True), "busy": service.busy}


@app.get("/agent-api/jobs/{job_id}")
def get_job(job_id: str, _: dict = Depends(require_operator)) -> dict:
    return service.get(job_id).view()


@app.get("/agent-api/jobs/{job_id}/runs")
def get_runs(job_id: str, _: dict = Depends(require_operator)) -> dict:
    """Output đầy đủ của các lần chạy lại — nặng nên tách khỏi API thăm dò mỗi 2 giây."""
    job = service.get(job_id)
    phases = []
    original = _original_run(job)
    if original:
        phases.append({"phase": "original", "runs": [original]})
    for path in sorted((job.dir / "replay").glob("*/runs.json")):
        phases.append({"phase": path.parent.name, "runs": json.loads(path.read_text(encoding="utf-8"))})
    order = {"original": 0, "reproduce": 1}
    phases.sort(key=lambda item: (order.get(item["phase"], 2), item["phase"]))
    return {"phases": phases}


def _original_run(job: Job) -> dict | None:
    """Lượt gốc của req dưới dạng một lần chạy, để tab trường so ngay với các lần chạy lại (giống web trace)."""
    case_dir = CASES / job.data["id"] / "case"
    try:
        fields = json.loads((case_dir / "fields.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    response: dict = {"fields": fields, "requestId": job.data["requestId"]}
    plan_file = case_dir / "attach_plan.json"
    if plan_file.is_file():
        try:
            response["attachments"] = json.loads(plan_file.read_text(encoding="utf-8")).get("plan") or []
        except ValueError:
            pass
    return {"n": 1, "status": "ok", "requestId": job.data["requestId"], "response": response, "startedAt": job.data["case"].get("createdAt")}


class Approval(BaseModel):
    round: int = Field(ge=1)
    decision: Literal["approve", "retry", "reject"]
    note: str = Field("", max_length=3000)


@app.post("/agent-api/jobs/{job_id}/approval")
def approve_fix(job_id: str, body: Approval, user: dict = Depends(require_operator)) -> dict:
    """Người vận hành duyệt bản sửa đã qua test. Chỉ sau bước này mã mới build Docker, nạp extension và chạy kiểm."""
    job = service.get(job_id)
    note = body.note.strip()
    with job.lock:
        pending = job.data.get("approval")
        if not pending or job.decided.is_set():
            raise HTTPException(409, "Job không chờ duyệt bản sửa nào")
        # Bấm trên trang cũ đang hiện patch của vòng trước thì không được duyệt nhầm patch của vòng sau.
        if pending["round"] != body.round:
            raise HTTPException(409, f"Khung duyệt đã sang vòng {pending['round']}: tải lại trang và xem patch mới")
        if body.decision == "retry" and not pending.get("canRetry"):
            raise HTTPException(400, "Đây là vòng cuối, không còn vòng để làm lại: chọn đồng ý hoặc dừng.")
        if body.decision == "retry" and not note:
            raise HTTPException(400, "Làm lại thì cần ghi góp ý để hội đồng biết phải sửa khác đi thế nào.")
        job.verdict = {"decision": body.decision, "note": note, "by": user.get("username", "")}
        job.decided.set()
    return job.view()


class PlanReview(BaseModel):
    round: int = Field(ge=1)
    revision: int = Field(ge=1)
    decision: Literal["approve", "retry", "reject"]
    note: str = Field("", max_length=3000)


@app.post("/agent-api/jobs/{job_id}/plan")
def review_plan(job_id: str, body: PlanReview, user: dict = Depends(require_operator)) -> dict:
    """Người vận hành duyệt kế hoạch sửa của trọng tài, trước khi agent đụng vào code."""
    job = service.get(job_id)
    note = body.note.strip()
    with job.lock:
        pending = job.data.get("planApproval")
        if not pending or job.decided.is_set():
            raise HTTPException(409, "Job không chờ duyệt kế hoạch nào")
        # Trang cũ còn hiện kế hoạch trước thì không được duyệt nhầm kế hoạch mới.
        if (pending["round"], pending["revision"]) != (body.round, body.revision):
            raise HTTPException(409, "Kế hoạch đã được lập lại: tải lại trang và đọc kế hoạch mới")
        if body.decision == "retry" and not pending.get("canRevise"):
            raise HTTPException(400, "Đã hết lượt yêu cầu lập lại kế hoạch trong vòng này: chọn đồng ý hoặc dừng.")
        if body.decision == "retry" and not note:
            raise HTTPException(400, "Yêu cầu lập lại thì cần ghi góp ý để trọng tài biết phải đổi kế hoạch thế nào.")
        job.verdict = {"decision": body.decision, "note": note, "by": user.get("username", "")}
        job.decided.set()
    return job.view()


@app.post("/agent-api/jobs/{job_id}/stop")
def stop_job(job_id: str, _: dict = Depends(require_operator)) -> dict:
    job = service.get(job_id)
    if job.data["status"] not in ("queued", "running"):
        raise HTTPException(409, "Job không còn chạy")
    job.cancel.set()
    job.log("Đang dừng và hoàn tác…")
    return job.view()


@app.post("/agent-api/jobs/{job_id}/revert")
def revert_job(job_id: str, _: dict = Depends(require_operator)) -> dict:
    job = service.get(job_id)
    fix = job.data.get("fix")
    if not fix or fix.get("reverted") or fix.get("reverting"):
        raise HTTPException(409, "Không có bản sửa nào để hoàn tác")
    if USE_WORKSPACE and workspace.owner() != job_id:
        raise HTTPException(409, "Khu làm việc đã đặt lại cho ca sau, code của ca này không còn trên máy. Bản sửa vẫn ở nhánh "
                                 "GitHub của ca (nếu đã đẩy) và tệp fix.patch: không gộp nhánh đó là đủ.")
    with job.lock:
        fix["reverting"] = True
    service.tasks.put(("revert", job_id))
    return job.view()


# ---- Auto test trong web Monitor (12007): tái hiện lượt, nội dung đã điền, bộ ca test, lần chạy (agents/lab.py) ----

def _lab_request_id(request_id: str) -> str:
    request_id = request_id.strip()
    if not _REQUEST_ID.match(request_id):
        raise HTTPException(400, "Mã req không hợp lệ")
    return request_id


def _lab(call, *args, status: int = 404):
    try:
        return call(*args)
    except lab.LabError as reason:
        raise HTTPException(status, str(reason)) from reason


@app.get("/agent-api/lab/runs/{request_id}")
def lab_run(request_id: str, user: dict = Depends(require_operator)) -> dict:
    request_id = _lab_request_id(request_id)
    view = _lab(lab.run_view, request_id)
    lab.audit(user, "tái hiện lượt", request_id)
    return view


@app.get("/agent-api/lab/runs/{request_id}/raw")
def lab_raw(request_id: str, user: dict = Depends(require_operator)) -> dict:
    request_id = _lab_request_id(request_id)
    bundle = _lab(lab.raw_bundle, request_id)
    lab.audit(user, "xem / tải gói ghi thô", request_id)
    return bundle


@app.get("/agent-api/lab/recent")
def lab_recent(edited: bool = True, limit: int = 40, _: dict = Depends(require_operator)) -> dict:
    return _lab(lab.recent, edited, max(1, min(limit, 200)), status=503)


class LabCase(BaseModel):
    requestId: str


@app.post("/agent-api/lab/cases")
def lab_create_case(body: LabCase, user: dict = Depends(require_operator)) -> dict:
    return _lab(lab.create_case, _lab_request_id(body.requestId), user, status=422)


@app.delete("/agent-api/lab/cases/{case_id}")
def lab_delete_case(case_id: str, user: dict = Depends(require_operator)) -> dict:
    if not re.match(r"^[A-Z]{1,4}-\d{4}$", case_id):
        raise HTTPException(400, "Chỉ xoá được ca tạo từ lượt thật")
    _lab(lab.delete_case, case_id, user)
    return {"ok": True}


@app.get("/agent-api/lab/suites")
def lab_suites(_: dict = Depends(require_operator)) -> dict:
    return lab.suites()


class LabSuiteRun(BaseModel):
    suite: str = Field(min_length=3, max_length=200)
    target: Literal["dev", "release"] = "dev"
    caseIds: list[str] | None = Field(None, max_length=500)


@app.post("/agent-api/lab/suite-runs")
def lab_start_run(body: LabSuiteRun, user: dict = Depends(require_operator)) -> dict:
    return _lab(lambda: lab.runner.start(body.suite, body.target, body.caseIds, user, service.busy), status=409)


@app.get("/agent-api/lab/suite-runs")
def lab_runs(_: dict = Depends(require_operator)) -> dict:
    return {"runs": lab.list_runs(), "current": lab.runner.current}


@app.get("/agent-api/lab/suite-runs/{no}")
def lab_run_detail(no: int, _: dict = Depends(require_operator)) -> dict:
    return _lab(lab.get_run, no)


@app.get("/agent-api/lab/config")
def lab_config(_: dict = Depends(require_operator)) -> dict:
    return lab.config_view()


def port_taken(host: str, port: int) -> bool:
    import socket

    try:
        socket.create_connection((host, port), timeout=0.5).close()
        return True
    except OSError:
        return False


def main() -> None:
    # Console Windows mặc định cp1252, in tiếng Việt là văng UnicodeEncodeError ngay lúc khởi động.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    problems = server_problems()
    if problems:
        print("Không khởi động: cấu hình server có thể đụng vào production.\n- " + "\n- ".join(problems))
        sys.exit(2)
    if port_taken("127.0.0.1" if HOST in ("", "0.0.0.0", "::") else HOST, PORT):
        # Kiểm TRƯỚC khi dọn đường hầm: bản đang chạy giữ đường hầm của nó, dọn là cắt web và Mongo nguồn của bản đó.
        print(f"Không khởi động: cổng {PORT} đã có dịch vụ agent khác đang chạy (xem http://{HOST}:{PORT}/agent-api/health). "
              "Muốn chạy code mới thì tắt bản đó trước, khi nó không bận ca nào.")
        sys.exit(3)
    if remote.enabled():
        killed = remote.cleanup_orphans()
        if killed:
            print(f"Đã tắt {killed} đường hầm ssh còn sót của lần chạy trước.", flush=True)
    if PUBLISH_WEB and remote.enabled():
        # Đưa web 12008 lên server qua đường hầm ngược; rớt thì luồng này tự nối lại.
        threading.Thread(target=remote.keep_publishing, daemon=True, name="publish-web").start()
    version = subprocess.run([claude_runner.available() or "claude", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"Dịch vụ agent: http://{HOST}:{PORT} · claude {version} · backend thử {BACKEND_URL}"
          + (f" · đăng nhập qua {AUTH_BACKEND_URL}" if AUTH_BACKEND_URL != BACKEND_URL else ""))
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
