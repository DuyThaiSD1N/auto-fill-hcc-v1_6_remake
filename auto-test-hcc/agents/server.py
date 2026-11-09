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
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

import browser
import claude_runner
import devjob
import evidence
import replay
from config import BACKEND_URL, DEFAULT_ROUNDS, DEFAULT_RUNS, HOST, MAX_ROUNDS, MAX_RUNS, PORT, RUNS
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
        response = httpx.get(f"{BACKEND_URL}/auth/me", headers={"Authorization": authorization}, timeout=10)
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
            job = Job(json.loads(path.read_text(encoding="utf-8")))
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
                        runner = devjob.DevOrchestrator if job.data.get("kind") == "dev" else Orchestrator
                        runner(job, self.secrets[job_id]).run()
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
    replayUsername: str = Field(min_length=1, max_length=200)
    replayPassword: str = Field(min_length=1, max_length=200)
    runs: int = Field(DEFAULT_RUNS, ge=1, le=MAX_RUNS)
    maxRounds: int = Field(DEFAULT_ROUNDS, ge=1, le=MAX_ROUNDS)
    reproduce: bool = True
    applicant: Applicant | None = None
    mode: Literal["portal", "api"] = "portal"


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
    return {"ok": True, "claude": bool(claude_runner.available()), "busy": service.busy, "queued": service.tasks.qsize()}


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
    if body.mode == "portal":
        problem = browser.preflight()
        if problem:
            raise HTTPException(400, problem)
    # Đăng nhập thử ngay: sai mật khẩu thì báo liền, đừng để chạy được nửa đường mới hỏng.
    try:
        account = replay.login(body.replayUsername, body.replayPassword)["user"]
    except replay.LoginError as reason:
        raise HTTPException(400, str(reason)) from reason
    warnings = []
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
            "replayAccount": body.replayUsername, "applicant": applicant, "mode": body.mode,
        },
        preview=preview,
        warnings=warnings,
    )
    job_id = job.data["id"]
    service.jobs[job_id] = job
    service.secrets[job_id] = {"username": body.replayUsername, "password": body.replayPassword}
    service.tasks.put(("run", job_id))
    return job.view()


class DevProcedure(BaseModel):
    key: str = Field(min_length=3, max_length=100)
    code: str = Field("", max_length=20)
    label: str = Field(min_length=5, max_length=300)
    url: str = Field("", max_length=500)
    newLink: bool = True
    needsAgencySelect: bool = True
    provinceOnlyAgency: bool = False
    selectSo: bool = False
    autoConfirm: bool = True
    linkNotes: str = Field("", max_length=3000)


class DevRequest(BaseModel):
    procedure: DevProcedure
    notes: str = Field("", max_length=6000)
    troLy: bool = True
    replayUsername: str = Field(min_length=1, max_length=200)
    replayPassword: str = Field(min_length=1, max_length=200)


@app.get("/agent-api/dev/links")
def dev_link_check(key: str = "", code: str = "", _: dict = Depends(require_operator)) -> dict:
    """Web gọi khi gõ key/mã: key đã có thì dùng lại link, mã trùng thủ tục khác thì cảnh báo."""
    return devjob.link_check(key.strip(), code.strip())


@app.post("/agent-api/dev/jobs")
def create_dev_job(
    meta: str = Form(...),
    mapping: list[UploadFile] = File(default=[]),
    attach: list[UploadFile] = File(default=[]),
    samples: list[UploadFile] = File(default=[]),
    user: dict = Depends(require_operator),
) -> dict:
    """Một request multipart: thông tin thủ tục (JSON trong ô meta) + tệp kéo thả theo 3 nhóm."""
    try:
        body = DevRequest.model_validate_json(meta)
    except ValidationError as reason:
        raise HTTPException(400, "Thông tin thủ tục chưa đúng: " + "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in reason.errors())) from reason
    procedure = {**body.procedure.model_dump(), "key": body.procedure.key.strip(), "label": body.procedure.label.strip(),
                 "code": body.procedure.code.strip(), "url": body.procedure.url.strip()}
    problems = devjob.validate_procedure(procedure)
    if problems:
        raise HTTPException(400, " ".join(problems))
    files = [(group, f.filename or "tep", f.file.read()) for group, items in (("mapping", mapping), ("attach", attach), ("samples", samples)) for f in items]
    if not files:
        raise HTTPException(400, "Chưa có tệp nào: kéo thả ít nhất file Excel mapping hoặc file mẫu.")
    for group, name, data in files:
        try:
            devjob.check_upload(group, name, len(data))
        except devjob.InputError as reason:
            raise HTTPException(400, str(reason)) from reason
    if not claude_runner.available():
        raise HTTPException(503, "Máy chưa có lệnh claude.")
    try:
        account = replay.login(body.replayUsername, body.replayPassword)["user"]
    except replay.LoginError as reason:
        raise HTTPException(400, str(reason)) from reason
    check = devjob.link_check(procedure["key"], procedure["code"])
    warnings = []
    if check["sameCode"]:
        warnings.append("Mã thủ tục này đã có ở: " + ", ".join(f"{i['key']} ({i['label']})" for i in check["sameCode"])
                        + ". Kiểm tra lại có làm trùng không.")
    if check["pipelineExists"]:
        warnings.append(f"Thư mục pipeline {check['folder']} đã có sẵn: agent sẽ sửa trên đó.")
    try:
        job = devjob.create_job(
            procedure=procedure, notes=body.notes.strip(), created_by=user.get("username", ""),
            settings={"troLy": body.troLy, "replayAccount": body.replayUsername,
                      "account": {k: account.get(k) for k in ("username", "xa", "tinh")}},
            files=files, warnings=warnings,
        )
    except devjob.InputError as reason:
        raise HTTPException(400, str(reason)) from reason
    job_id = job.data["id"]
    service.jobs[job_id] = job
    service.secrets[job_id] = {"username": body.replayUsername, "password": body.replayPassword}
    service.tasks.put(("run", job_id))
    return job.view()


@app.get("/agent-api/jobs/{job_id}/inputs/{name}")
def get_input(job_id: str, name: str, _: dict = Depends(require_operator)) -> FileResponse:
    """Xem lại tệp đã gửi cho job thêm thủ tục (ảnh ánh xạ, bản chữ của Excel)."""
    job = service.get(job_id)
    item = next((i for i in job.data.get("inputs") or [] if i["name"] == name), None)
    if not item:
        raise HTTPException(404, "Không có tệp này")
    path = devjob.REPO / item["path"]
    if not path.is_file() or job.dir not in path.parents:
        raise HTTPException(404, "Tệp không còn")
    return FileResponse(path, media_type=devjob._mime(path.name), filename=path.name)


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
    for path in sorted((job.dir / "replay").glob("*/runs.json")):
        phases.append({"phase": path.parent.name, "runs": json.loads(path.read_text(encoding="utf-8"))})
    phases.sort(key=lambda item: (item["phase"] != "reproduce", item["phase"]))
    return {"phases": phases}


@app.get("/agent-api/jobs/{job_id}/shots/{phase}/{number}")
def get_shot(job_id: str, phase: str, number: int, _: dict = Depends(require_operator)) -> FileResponse:
    """Ảnh chụp cổng thật sau một lần điền."""
    job = service.get(job_id)
    if not re.fullmatch(r"reproduce|round\d+", phase):
        raise HTTPException(400, "Sai tên lượt")
    path = job.dir / "replay" / phase / f"run{number}.png"
    if not path.is_file():
        raise HTTPException(404, "Không có ảnh")
    return FileResponse(path, media_type="image/png")


@app.post("/agent-api/jobs/{job_id}/ready")
def job_ready(job_id: str, _: dict = Depends(require_operator)) -> dict:
    """Người dùng đã đăng nhập và mở tới tờ khai trên cửa sổ bot."""
    job = service.get(job_id)
    if not job.data.get("human"):
        raise HTTPException(409, "Job không chờ thao tác nào")
    job.ready.set()
    return job.view()


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
    with job.lock:
        fix["reverting"] = True
    service.tasks.put(("revert", job_id))
    return job.view()


def main() -> None:
    # Console Windows mặc định cp1252, in tiếng Việt là văng UnicodeEncodeError ngay lúc khởi động.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    version = subprocess.run([claude_runner.available() or "claude", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"Dịch vụ agent: http://{HOST}:{PORT} · claude {version}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
