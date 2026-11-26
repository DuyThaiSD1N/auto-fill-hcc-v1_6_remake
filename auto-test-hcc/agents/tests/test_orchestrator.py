"""Kịch bản đầu-cuối của máy trạng thái với agent/backend giả. Cái được kiểm là luồng và các chốt chặn."""
import importlib
import json
import sys
import threading
import time as time_module
from pathlib import Path

import pytest

import claude_runner
import codeguard
import evidence
import orchestrator
import replay
import roles
import verify
from claude_runner import AgentError, AgentResult
from orchestrator import Job, Orchestrator

GOOD = {"status": "ok", "response": {"fields": [{"name": "hoTen", "value": "A"}, {"name": "gioiTinh", "value": "Nam"}]}}
BAD = {"status": "ok", "response": {"fields": [{"name": "hoTen", "value": "A"}, {"name": "gioiTinh", "value": ""}]}}
CHECK = {"field": "gioiTinh", "op": "equals", "expected": "Nam", "why": "giấy ghi Nam"}
PLAN = {"summary": "s", "files": ["app/a.py"], "steps": ["x"], "test": "tests/unit/test_a.py"}


def opinion(cause, confidence=90):
    return {"cause": cause, "confidence": confidence, "summary": "s", "evidence": ["e"], "proposal": "p"}


class World:
    """Backend + agent giả. Mỗi kịch bản khai quyết định trọng tài và hành vi agent sửa."""

    def __init__(self, be: Path):
        self.be = be
        self.opinions = {"ocr": opinion("mapper"), "mapper": opinion("mapper"), "form": opinion("mapper")}
        self.decisions = [{"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [CHECK]}]
        self.pre_runs = [BAD] * 5
        self.after_runs = [[GOOD] * 5]
        self.fix_edits = [lambda: self.edit("x = 2\n")]
        self.pipeline_results = []
        self.full_results = []
        self.calls = []
        self.deploys = 0
        self.deploy_ok = True
        self.on_fixer = None
        self.cost = 0.01
        self.extension_results = []
        self.edit_extension = None

    def edit(self, text, rel="app/a.py"):
        (self.be / rel).write_text(text, encoding="utf-8")
        return rel

    def edit_ext(self, text):
        (self.be.parent / "auto-fill-hcc-extension/content/fill.js").write_text(text, encoding="utf-8")
        return "../auto-fill-hcc-extension/content/fill.js"

    def code(self):
        return (self.be / "app/a.py").read_text(encoding="utf-8")

    def ext_code(self):
        return (self.be.parent / "auto-fill-hcc-extension/content/fill.js").read_text(encoding="utf-8")

    def run_agent(self, *, system, prompt, schema, can_edit=False, touched=None, cancel=None, resume=None, edit_extension=False, **_):
        if can_edit:
            self.edit_extension = edit_extension
            self.calls.append("fixer" if not resume else "fixer-resume")
            if self.on_fixer:
                self.on_fixer()
            edit = self.fix_edits.pop(0) if self.fix_edits else None
            if edit:
                touched.append(str((self.be / edit()).resolve()))
            output = {"summary": "đã sửa", "changedFiles": ["app/a.py"], "testFiles": ["auto-fill-hcc-backend/tests/test_a.py"]}
        elif schema is roles.DECISION_SCHEMA:
            self.calls.append("arbiter")
            output = self.decisions.pop(0) if len(self.decisions) > 1 else self.decisions[0]
        elif schema is roles.REVIEW_SCHEMA:
            self.calls.append("review")
            output = {**opinion("mapper"), "stance": "agree", "rebuttal": "r"}
        else:
            role = next(r for r, spec in roles.ANALYSTS.items() if spec["task"] in system)
            self.calls.append(f"analyst:{role}")
            output = self.opinions[role]
            if isinstance(output, Exception):
                raise output
        return AgentResult(output=output, session_id="sess", cost=self.cost, turns=1)

    def replay(self, case, count, phase, job_dir, credentials, cancel, on_run):
        assert credentials["password"] == "mat-khau"
        self.calls.append(f"replay:{phase}")
        source = self.pre_runs if phase == "reproduce" else (self.after_runs.pop(0) if len(self.after_runs) > 1 else self.after_runs[0])
        runs = [{"n": i + 1, "ocrFresh": True, **r} for i, r in enumerate(source[:count])]
        for run in runs:
            on_run(run)
        folder = job_dir / "replay" / phase
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "runs.json").write_text(json.dumps(runs), encoding="utf-8")
        return runs

    def pipeline_tests(self, files, cancel):
        self.calls.append("pipeline-tests")
        return self.pipeline_results.pop(0) if self.pipeline_results else {"ok": True, "files": files, "summary": "1 passed", "output": ""}

    def extension_tests(self, cancel):
        self.calls.append("extension-tests")
        return self.extension_results.pop(0) if self.extension_results else {"total": 10, "failed": []}

    def full_tests(self, cancel):
        self.calls.append("full-tests")
        return self.full_results.pop(0) if self.full_results else {"bad": [], "failed": 0, "passed": 10, "skipped": 0, "errors": 0}

    def deploy(self, cancel):
        self.deploys += 1
        self.calls.append("deploy")
        return {"ok": self.deploy_ok, "ps": "app Up", "health": '{"ok":true}', "step": None if self.deploy_ok else "build", "output": ""}


@pytest.fixture
def world(tmp_path, monkeypatch):
    be = tmp_path / "repo/auto-fill-hcc-backend"
    (be / "app").mkdir(parents=True)
    (be / "tests").mkdir()
    (be / "app/a.py").write_text("x = 1\n", encoding="utf-8")
    (be / "tests/test_a.py").write_text("def test(): pass\n", encoding="utf-8")
    ext = be.parent / "auto-fill-hcc-extension/content"
    ext.mkdir(parents=True)
    (ext / "fill.js").write_text("const a = 1;\n", encoding="utf-8")
    runs = tmp_path / "runs"
    monkeypatch.setattr(codeguard, "REPO", be.parent)
    monkeypatch.setattr(orchestrator, "RUNS", runs)
    monkeypatch.setattr(orchestrator, "CASES", runs)  # chứng cứ giả không được rơi vào runs/ thật
    monkeypatch.setattr(orchestrator, "REGRESSION_CASES", tmp_path / "regression")
    monkeypatch.setattr(verify, "regression_baseline", lambda cancel: {"results": {}, "total": 0})
    monkeypatch.setattr(verify, "regression_cases", lambda: [])

    def no_regression(self, round_, changes):
        raise orchestrator.regression_case.Skip("test: không dựng ca hồi quy")

    monkeypatch.setattr(Orchestrator, "_build_regression", no_regression)
    world = World(be)
    monkeypatch.setattr(claude_runner, "run_agent", world.run_agent)
    monkeypatch.setattr(replay, "replay", world.replay)
    monkeypatch.setattr(verify, "pipeline_tests", world.pipeline_tests)
    monkeypatch.setattr(verify, "full_tests", world.full_tests)
    monkeypatch.setattr(verify, "baseline", lambda cancel: {"bad": [], "failed": 0, "passed": 10, "skipped": 0, "errors": 0})
    monkeypatch.setattr(verify, "deploy", world.deploy)
    monkeypatch.setattr(verify, "extension_tests", world.extension_tests)
    monkeypatch.setattr(verify, "extension_baseline", lambda cancel: {"total": 10, "failed": []})
    monkeypatch.setattr(verify, "find_test_files", lambda pipeline, extra: ["tests/test_a.py"])
    monkeypatch.setattr(evidence, "collect", lambda request_id, case_dir: (case_dir.mkdir(parents=True, exist_ok=True), {
        "requestId": request_id, "procedure": "thu-tuc", "label": "Thủ tục", "pipeline": "thu_tuc",
        "account": {"username": "u"}, "caseDir": "runs/x/case", "options": {},
        "storedFiles": [{"name": "a.jpg"}],
        "fields": [{"name": "hoTen", "value": "A"}, {"name": "gioiTinh", "value": ""}],
    })[1])
    return world


REVIEWER = {"verdicts": [], "seen": [], "plans": [], "plans_seen": []}


@pytest.fixture(autouse=True)
def reviewer():
    """Người duyệt giả: thấy khung duyệt thì bấm theo REVIEWER["verdicts"], hết danh sách thì đồng ý."""
    REVIEWER["verdicts"] = []
    REVIEWER["seen"] = []
    REVIEWER["plans"] = []  # câu trả lời ở khung duyệt kế hoạch, hết danh sách thì đồng ý
    REVIEWER["plans_seen"] = []
    return REVIEWER


def answer_approvals(job):
    def loop():
        answered = None
        deadline = time_module.monotonic() + 30
        planned = None
        while job.data["status"] not in ("done", "failed", "stopped") and time_module.monotonic() < deadline:
            plan = job.data.get("planApproval")
            if plan and (plan["round"], plan["revision"]) != planned and not job.decided.is_set():
                planned = (plan["round"], plan["revision"])
                REVIEWER["plans_seen"].append(dict(plan))
                verdict = REVIEWER["plans"].pop(0) if REVIEWER["plans"] else {"decision": "approve", "note": ""}
                if verdict is not None:
                    with job.lock:
                        job.verdict = {"by": "nguoi-duyet", **verdict}
                        job.decided.set()
            pending = job.data.get("approval")
            if pending and pending["round"] != answered and not job.decided.is_set():
                answered = pending["round"]
                REVIEWER["seen"].append(dict(pending))
                verdict = REVIEWER["verdicts"].pop(0) if REVIEWER["verdicts"] else {"decision": "approve", "note": ""}
                if callable(verdict):
                    verdict = verdict(job)
                if verdict is None:  # không bấm gì: để hết giờ hoặc để kịch bản tự bấm Dừng
                    continue
                with job.lock:
                    job.verdict = {"by": "nguoi-duyet", **verdict}
                    job.decided.set()
            time_module.sleep(0.01)

    threading.Thread(target=loop, daemon=True).start()


def start(reproduce=True, rounds=3, runs=5):
    job = Job.create(
        request_id="req_test", description="ô giới tính bị trống", created_by="t",
        settings={"runs": runs, "maxRounds": rounds, "reproduce": reproduce, "replayAccount": "u"},
        preview={"label": "Thủ tục"}, warnings=[],
    )
    answer_approvals(job)
    return job, Orchestrator(job, {"username": "u", "password": "mat-khau"})


def test_ca_hoi_dong_ket_luan_ocr_thi_bo_qua_khong_sua(world):
    world.opinions = {r: opinion("ocr") for r in world.opinions}
    world.decisions = [{"decision": "skip_ocr", "cause": "ocr", "reason": "giấy ghi Nam, OCR ra Năm"}]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "skipped_ocr" and job.data["status"] == "done"
    assert job.data["rounds"][0]["debate"]["skipped"] is True
    assert "review" not in world.calls and "fixer" not in world.calls
    assert world.deploys == 0 and world.code() == "x = 1\n"


def test_loi_mapper_hop_sua_kiem_thu_dat(world):
    job, orch = start()
    orch.run()
    data = job.data
    assert data["outcome"] == "fixed", data["error"]
    # Có vòng phản biện gồm 3 thành viên + người phản biện, rồi mới tới trọng tài.
    assert world.calls.count("review") == 4 and world.calls.index("arbiter") > world.calls.index("review")
    order = ["fixer", "pipeline-tests", "full-tests", "deploy", "replay:round1"]
    assert [c for c in world.calls if c in order] == order
    assert world.code() == "x = 2\n"
    assert data["fix"]["files"][0]["path"] == "auto-fill-hcc-backend/app/a.py" and "+x = 2" in data["fix"]["patch"]
    assert data["rounds"][0]["retest"]["evaluation"]["allPass"]
    assert not (job.dir / "snapshot").exists()


def test_ban_sua_qua_test_phai_cho_duyet_roi_moi_build(world, reviewer):
    def look(job):
        world.calls.append("approval")
        assert world.code() == "x = 2\n" and world.deploys == 0
        assert job.data["stage"] == "approve" and job.data["status"] == "running"
        return {"decision": "approve", "note": ""}

    reviewer["verdicts"] = [look]
    job, orch = start()
    orch.run()
    order = ["fixer", "pipeline-tests", "full-tests", "approval", "deploy", "replay:round1"]
    assert [c for c in world.calls if c in order] == order
    assert job.data["outcome"] == "fixed" and job.data["approval"] is None
    assert reviewer["seen"][0]["files"] == ["auto-fill-hcc-backend/app/a.py"] and reviewer["seen"][0]["canRetry"] is True
    assert job.data["rounds"][0]["approval"]["decision"] == "approve" and job.data["rounds"][0]["approval"]["by"] == "nguoi-duyet"


def test_khong_dong_y_lam_lai_thi_hoi_dong_doc_gop_y(world, reviewer, monkeypatch):
    seen = []
    real = world.run_agent

    def spy(**kwargs):
        seen.append(kwargs["prompt"])
        return real(**kwargs)

    monkeypatch.setattr(claude_runner, "run_agent", spy)
    reviewer["verdicts"] = [{"decision": "retry", "note": "Đừng sửa mapper chung, khoanh theo riêng thủ tục này"}]
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: world.edit("x = 3\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and world.code() == "x = 3\n"
    # Vòng 1 không được duyệt nên không build lần nào; chỉ build bản của vòng 2.
    assert world.deploys == 1 and "replay:round1" not in world.calls and "replay:round2" in world.calls
    first = job.data["rounds"][0]
    assert first["result"]["ok"] is False and "Người duyệt không đồng ý" in first["result"]["reason"]
    later = [p for p in seen if "<reviewer_note" in p]
    assert later and "khoanh theo riêng thủ tục này" in later[0]


def test_khong_dong_y_dung_thi_hoan_tac_khong_build(world, reviewer):
    reviewer["verdicts"] = [{"decision": "reject", "note": "sai hướng"}]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "not_approved" and job.data["status"] == "done"
    assert "sai hướng" in job.data["report"]["reason"]
    assert world.code() == "x = 1\n" and world.deploys == 0 and job.data["fix"] is None
    assert len(job.data["rounds"]) == 1 and "replay:round1" not in world.calls


def test_vong_cuoi_khong_cho_lam_lai(world, reviewer):
    job, orch = start(rounds=1)
    orch.run()
    assert reviewer["seen"][0]["canRetry"] is False


def test_het_gio_khong_ai_duyet_thi_hoan_tac_va_ket_thuc(world, reviewer, monkeypatch):
    monkeypatch.setattr(orchestrator, "APPROVAL_TIMEOUT_S", 0)
    reviewer["verdicts"] = [lambda job: None]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "not_approved" and "không có ai duyệt" in job.data["report"]["reason"]
    assert world.code() == "x = 1\n" and world.deploys == 0 and job.data["approval"] is None
    assert job.data["rounds"][0]["approval"]["timeout"] is True


def test_dung_khi_dang_cho_duyet_thi_hoan_tac(world, reviewer):
    reviewer["verdicts"] = [lambda job: job.cancel.set()]
    job, orch = start()
    orch.run()
    assert job.data["status"] == "stopped" and job.data["approval"] is None
    assert world.code() == "x = 1\n" and world.deploys == 0


def test_sua_tay_luc_cho_duyet_thi_build_theo_noi_dung_tren_dia(world, reviewer):
    def tweak(job):
        world.edit("x = 5\n")
        return {"decision": "approve", "note": ""}

    reviewer["verdicts"] = [tweak]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and world.code() == "x = 5\n"
    fix = job.data["rounds"][0]["fix"]
    assert "+x = 5" in fix["patch"] and "+x = 2" in fix["approvedPatch"] and "+x = 5" in job.data["fix"]["patch"]
    assert any("đã đổi sau lúc duyệt" in w for w in job.data["warnings"])


def test_api_duyet_chan_bam_nham(world, monkeypatch, tmp_path):
    import config
    from fastapi.testclient import TestClient

    # server.py dựng Service ngay lúc import và đọc runs/: trỏ sang thư mục tạm kẻo khôi phục nhầm job thật.
    monkeypatch.setattr(config, "RUNS", tmp_path / "server-runs")
    sys.modules.pop("server", None)
    try:
        server = importlib.import_module("server")
        server.app.dependency_overrides[server.require_operator] = lambda: {"username": "duyet-vien", "role": "super_admin"}
        client = TestClient(server.app)
        job = Job.create(request_id="req_test", description="ô trống", created_by="t", settings={"maxRounds": 3}, preview={}, warnings=[])
        server.service.jobs[job.data["id"]] = job
        url = f"/agent-api/jobs/{job.data['id']}/approval"
        assert client.post(url, json={"round": 1, "decision": "approve"}).status_code == 409  # không chờ duyệt gì
        job.update(approval={"round": 2, "since": "t", "files": [], "canRetry": False, "timeoutMin": 60})
        assert client.post(url, json={"round": 1, "decision": "approve"}).status_code == 409  # bấm trên trang của vòng trước
        assert client.post(url, json={"round": 2, "decision": "retry", "note": "x"}).status_code == 400  # vòng cuối
        assert client.post(url, json={"round": 2, "decision": "lam-bua"}).status_code == 422
        job.data["approval"]["canRetry"] = True
        assert client.post(url, json={"round": 2, "decision": "retry", "note": "   "}).status_code == 400  # làm lại phải có góp ý
        assert not job.decided.is_set()
        response = client.post(url, json={"round": 2, "decision": "retry", "note": " khoanh lại theo thủ tục "})
        assert response.status_code == 200 and job.decided.is_set()
        assert job.verdict == {"decision": "retry", "note": "khoanh lại theo thủ tục", "by": "duyet-vien"}
        assert client.post(url, json={"round": 2, "decision": "approve"}).status_code == 409  # đã bấm rồi
    finally:
        sys.modules.pop("server", None)


def test_giu_ban_sua_roi_hoan_tac_duoc(world):
    job, orch = start()
    orch.run()
    orchestrator.revert_fix(job)
    assert world.code() == "x = 1\n"
    assert job.data["fix"]["reverted"] and job.data["fix"]["revertedFiles"] == ["auto-fill-hcc-backend/app/a.py"]
    assert world.deploys == 2


def test_code_hien_tai_da_dat_thi_khong_sua(world):
    world.pre_runs = [GOOD] * 5
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "not_reproduced"
    assert "fixer" not in world.calls and world.deploys == 0


def test_loi_thinh_thoang_van_duoc_sua(world):
    world.pre_runs = [GOOD, GOOD, BAD, GOOD, GOOD]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"
    assert job.data["rounds"][0]["precheck"]["passed"] == 4


def test_khong_chay_lai_truoc_thi_cham_tren_luot_goc(world):
    job, orch = start(reproduce=False)
    orch.run()
    assert job.data["outcome"] == "fixed"
    assert "replay:reproduce" not in world.calls


def test_trot_ca_ba_vong_thi_de_lai_code_vong_cuoi_cho_nguoi_xem(world):
    world.after_runs = [[BAD] * 5]
    seen = []
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: (seen.append(world.code()), world.edit("x = 3\n"))[1],
                       lambda: (seen.append(world.code()), world.edit("x = 4\n"))[1]]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "need_human"
    # Mỗi vòng vẫn làm lại từ code gốc; hết vòng thì code của vòng cuối được đặt lại cho người xem.
    assert seen == ["x = 1\n", "x = 1\n"] and world.code() == "x = 4\n"
    assert len(job.data["rounds"]) == 3
    # 3 lần build bản sửa + 1 lần build trả về code gốc; bản để lại không được build.
    assert world.deploys == 4 and job.data["stackDirty"] is False and world.calls[-1] == "deploy"
    fix = job.data["fix"]
    assert fix["unverified"] is True and fix["round"] == 3 and "+x = 4" in fix["patch"]
    assert fix["files"][0]["path"] == "auto-fill-hcc-backend/app/a.py"
    assert job.data["rounds"][2]["result"]["kept"] is True and "kept" not in job.data["rounds"][0]["result"]
    assert "Code của vòng 3 vẫn để trong thư mục làm việc" in job.data["report"]["reason"]


def test_code_de_lai_hoan_tac_duoc(world):
    world.after_runs = [[BAD] * 5]
    job, orch = start(rounds=1)
    orch.run()
    assert world.code() == "x = 2\n"
    orchestrator.revert_fix(job)
    assert world.code() == "x = 1\n" and job.data["fix"]["reverted"]


def test_vong_cuoi_khong_viet_code_thi_de_lai_code_vong_truoc(world):
    world.after_runs = [[BAD] * 5]
    world.decisions = [
        {"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [CHECK]},
        {"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [{**CHECK, "field": "khongTonTai"}]},
    ]
    job, orch = start(rounds=2)
    orch.run()
    assert job.data["outcome"] == "need_human" and world.code() == "x = 2\n" and job.data["fix"]["round"] == 1


def test_code_nguoi_duyet_bac_thi_khong_de_lai(world, reviewer):
    reviewer["verdicts"] = [{"decision": "retry", "note": "sai chỗ"}]
    world.decisions = [
        {"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [CHECK]},
        {"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [{**CHECK, "field": "khongTonTai"}]},
    ]
    job, orch = start(rounds=2)
    orch.run()
    assert job.data["outcome"] == "need_human" and world.code() == "x = 1\n" and job.data["fix"] is None
    assert "Không có code nào để lại" in job.data["report"]["reason"]


def test_patch_lo_du_lieu_that_thi_khong_de_lai(world):
    world.fix_edits = [lambda: world.edit('ma = "req_test"\n')]
    job, orch = start(rounds=1)
    orch.run()
    assert job.data["outcome"] == "need_human" and world.code() == "x = 1\n" and job.data["fix"] is None
    assert any("dữ liệu thật" in w for w in job.data["warnings"])


def test_vong_sau_duoc_biet_lan_truoc_that_bai_vi_sao(world, monkeypatch):
    seen = []
    real = world.run_agent

    def spy(**kwargs):
        seen.append(kwargs["prompt"])
        return real(**kwargs)

    monkeypatch.setattr(claude_runner, "run_agent", spy)
    world.after_runs = [[BAD] * 5, [GOOD] * 5]
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: world.edit("x = 3\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and world.code() == "x = 3\n"
    later = [p for p in seen if "đã THẤT BẠI" in p]
    assert later and "x = 2" in later[0] and "Đạt 0/5" in later[0]


def test_ban_sua_vong_truoc_khong_chong_len_vong_sau(world):
    world.after_runs = [[BAD] * 5, [GOOD] * 5]
    seen = []
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: (seen.append(world.code()), world.edit("x = 3\n"))[1]]
    job, orch = start()
    orch.run()
    assert seen == ["x = 1\n"]


def test_vong_sau_ket_luan_khong_sua_thi_stack_duoc_tra_ve(world):
    world.after_runs = [[BAD] * 5]
    world.decisions = [
        {"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [CHECK]},
        {"decision": "report_only", "cause": "extension", "reason": "lỗi ở extension"},
    ]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "report_only"
    assert world.code() == "x = 1\n" and job.data["stackDirty"] is False
    assert world.deploys == 2


def test_vong_sau_chi_doi_test_van_phai_build_lai(world):
    world.after_runs = [[BAD] * 5, [GOOD] * 5]
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: world.edit("def test(): assert 1\n", "tests/test_a.py")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"
    assert world.deploys == 2


def test_test_pipeline_do_thi_khong_build_va_tra_lai_agent(world):
    world.pipeline_results = [{"ok": False, "files": [], "summary": "1 failed", "output": "AssertionError"}]
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: world.edit("x = 3\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"
    assert world.calls.index("fixer-resume") < world.calls.index("deploy")
    assert job.data["rounds"][0]["fix"]["repairs"] == 1


def test_test_moi_do_so_voi_baseline_thi_tra_lai_agent(world):
    world.full_results = [{"bad": ["FAILED tests/x"], "failed": 1, "passed": 9, "skipped": 0, "errors": 0}]
    job, orch = start()
    orch.run()
    assert "fixer-resume" in world.calls and job.data["outcome"] == "fixed"


def test_vuot_so_lan_va_thi_truot_vong_khong_build(world):
    world.pipeline_results = [{"ok": False, "files": [], "summary": "1 failed", "output": "x"}] * 3
    job, orch = start(rounds=1)
    orch.run()
    assert job.data["outcome"] == "need_human"
    # Test đỏ nên chưa từng build; code vẫn để lại cho người xem.
    assert world.deploys == 0 and world.code() == "x = 2\n" and job.data["fix"]["unverified"] is True


def test_patch_chua_du_lieu_that_bi_tra_lai(world):
    world.fix_edits = [lambda: world.edit('ma = "req_test"\n'), lambda: world.edit("x = 2\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and "fixer-resume" in world.calls
    assert "req_test" not in world.code()


def test_agent_khong_sua_gi_bi_nhac(world):
    world.fix_edits = [None, lambda: world.edit("x = 2\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and "fixer-resume" in world.calls


def test_hoi_quy_field_khac_lam_truot_vong(world):
    drifted = {"status": "ok", "response": {"fields": [{"name": "hoTen", "value": "B"}, {"name": "gioiTinh", "value": "Nam"}]}}
    world.after_runs = [[drifted] * 5]
    job, orch = start(rounds=1)
    orch.run()
    assert job.data["outcome"] == "need_human"
    assert job.data["rounds"][0]["retest"]["regressions"][0]["field"] == "hoTen"
    assert world.code() == "x = 2\n" and job.data["fix"]["unverified"] is True


def test_build_loi_thi_truot_vong_va_hoan_tac(world):
    world.deploy_ok = False
    job, orch = start(rounds=1)
    orch.run()
    assert world.code() == "x = 1\n"
    assert job.data["status"] == "failed" and "Build lại sau khi hoàn tác" in job.data["warnings"][0]


def test_tieu_chi_tro_field_khong_co_thi_khong_sua(world):
    bad = {**CHECK, "field": "khongTonTai"}
    world.decisions = [{"decision": "fix_code", "cause": "mapper", "reason": "r", "plan": PLAN, "acceptance": [bad]}]
    job, orch = start(rounds=1)
    orch.run()
    assert job.data["outcome"] == "need_human" and "fixer" not in world.calls


def test_dung_giua_luc_sua_thi_hoan_tac(world):
    job, orch = start()

    def stop_midway():
        world.edit("x = 9\n")
        orch.touched.append(str(world.be / "app/a.py"))
        job.cancel.set()
        raise verify.Stopped()

    world.on_fixer = stop_midway
    orch.run()
    assert job.data["status"] == "stopped" and world.code() == "x = 1\n"
    assert world.deploys == 0


def test_agent_sua_chet_giua_chung_thi_hoan_tac(world):
    job, orch = start()

    def crash():
        world.edit("x = 9\n")
        orch.touched.append(str(world.be / "app/a.py"))
        raise AgentError("hết hạn mức")

    world.on_fixer = crash
    orch.run()
    assert job.data["status"] == "failed" and "hết hạn mức" in job.data["error"]
    assert world.code() == "x = 1\n"


def test_mot_thanh_vien_loi_van_hop_tiep(world):
    world.opinions["form"] = AgentError("lỗi mạng")
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"
    assert job.data["rounds"][0]["opinions"][2]["error"]


def test_hoi_dong_khong_du_y_kien_thi_dung(world):
    world.opinions["form"] = AgentError("x")
    world.opinions["ocr"] = AgentError("y")
    job, orch = start()
    orch.run()
    assert job.data["status"] == "failed" and "không đủ ý kiến" in job.data["error"]


def test_vuot_tran_chi_phi_thi_dung_va_hoan_tac(world, monkeypatch):
    monkeypatch.setattr(orchestrator, "JOB_BUDGET_USD", 0.05)
    world.cost = 0.02
    job, orch = start()
    orch.run()
    assert job.data["status"] == "failed" and "vượt trần" in job.data["error"]
    assert world.code() == "x = 1\n"


def test_chay_lai_loi_ca_nam_lan_thi_dung_som(world):
    world.pre_runs = [{"status": "error", "error": "HTTP 500"}] * 5
    job, orch = start()
    orch.run()
    assert job.data["status"] == "failed" and "HTTP 500" in job.data["error"]
    assert not any(c.startswith("analyst") for c in world.calls)


def test_chay_lai_khac_luot_goc_thi_canh_bao_va_bao_hoi_dong(world, monkeypatch):
    seen = []
    real = world.run_agent

    def spy(**kwargs):
        seen.append(kwargs["prompt"])
        return real(**kwargs)

    monkeypatch.setattr(claude_runner, "run_agent", spy)
    world.pre_runs = [{"status": "partial", "response": {"fields": [{"name": "x", "value": True}]}}] * 5
    world.decisions = [{"decision": "report_only", "cause": "unknown", "reason": "chưa kiểm chứng được"}]
    job, orch = start()
    orch.run()
    assert job.data["reproduce"]["faithful"] is False
    assert any("không đại diện" in w for w in job.data["warnings"])
    assert "CẢNH BÁO về dữ liệu chạy lại" in seen[0]


def test_moc_nguoi_nop_vao_form_context(world):
    job = Job.create(
        request_id="req_test", description="ô sai", created_by="t",
        settings={"runs": 1, "maxRounds": 1, "reproduce": False, "replayAccount": "u", "applicant": {"applicantFullname": "A"}},
        preview={}, warnings=[],
    )
    orch = Orchestrator(job, {"username": "u", "password": "mat-khau"})
    orch._collect()
    assert orch.case["options"]["formContext"] == {"applicantFullname": "A"}


def test_luu_job_loi_tam_thoi_khong_lam_chet_job(world, monkeypatch):
    real = orchestrator.os.replace
    state = {"fails": 0}

    def flaky(src, dst):
        state["fails"] += 1
        if state["fails"] % 3:
            raise PermissionError(5, "Access is denied")
        return real(src, dst)

    monkeypatch.setattr(orchestrator.os, "replace", flaky)
    monkeypatch.setattr(orchestrator, "_SAVE_RETRY_S", (0, 0, 0))
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"


def test_luu_job_hong_han_van_chay_tiep(world, monkeypatch):
    def deny(src, dst):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(orchestrator.os, "replace", deny)
    monkeypatch.setattr(orchestrator, "_SAVE_RETRY_S", (0,))
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed"


def test_chi_goi_backend_thi_agent_khong_duoc_sua_extension(world):
    job, orch = start()
    orch.run()
    assert world.edit_extension is False
    assert "extension-tests" not in world.calls


def test_chay_kiem_khong_xac_nhan_duoc_ocr_moi_thi_canh_bao(world):
    stale = {"status": "ok", "response": GOOD["response"], "ocrFresh": False}
    job, orch = start()
    orch._check_runs([{**GOOD, "n": 1, "ocrFresh": True}, {**stale, "n": 2}])
    assert any("1/2 lần xác nhận được OCR mới" in w for w in job.data["warnings"])


def test_khoi_dong_lai_hoan_tac_phan_sua_do(world):
    job, orch = start()
    orch.guard.take()
    world.edit("x = 9\n")
    job.update(status="running", touched=[str(world.be / "app/a.py")], stackDirty=True)
    orchestrator.recover_interrupted(Job(json.loads((job.dir / "job.json").read_text(encoding="utf-8"))))
    assert world.code() == "x = 1\n" and world.deploys == 1


def test_mat_khau_khong_bao_gio_xuong_dia(world):
    job, orch = start()
    orch.run()
    leaked = [p for p in job.dir.rglob("*") if p.is_file() and b"mat-khau" in p.read_bytes()]
    assert leaked == []


def test_khong_co_luong_chan_khi_doc_trong_luc_chay(world):
    job, orch = start()
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            job.view()

    thread = threading.Thread(target=reader)
    thread.start()
    orch.run()
    stop.set()
    thread.join()
    assert job.data["outcome"] == "fixed"


def troly_job(world, monkeypatch, handfree_runs):
    """Ca trợ lý hồ sơ: bản sửa đụng app/channels/handfree/."""
    (world.be / "app/channels/handfree").mkdir(parents=True, exist_ok=True)
    (world.be / "app/channels/handfree/x.py").write_text("y = 1\n", encoding="utf-8")
    world.fix_edits = [lambda: world.edit("y = 2\n", "app/channels/handfree/x.py")]
    monkeypatch.setattr(verify, "handfree_baseline", lambda cancel: {"bad": ["FAILED cu"], "failed": 1, "passed": 9, "skipped": 0, "errors": 0})

    def handfree_tests(cancel):
        world.calls.append("handfree-tests")
        return handfree_runs.pop(0)

    monkeypatch.setattr(verify, "handfree_tests", handfree_tests)
    job, orch = start()
    with job.lock:
        job.data["settings"]["target"] = "troly"
    return job, orch


def test_ca_tro_ly_sua_phan_handfree_thi_chay_test_handfree(world, monkeypatch):
    ok = {"bad": ["FAILED cu"], "failed": 1, "passed": 10, "skipped": 0, "errors": 0}
    job, orch = troly_job(world, monkeypatch, [ok])
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert "handfree-tests" in world.calls
    assert job.data["rounds"][0]["tests"]["handfree"]["ok"] is True


def test_ca_tro_ly_test_handfree_moi_do_thi_tra_lai_agent(world, monkeypatch):
    bad = {"bad": ["FAILED cu", "FAILED moi"], "failed": 2, "passed": 9, "skipped": 0, "errors": 0}
    ok = {"bad": ["FAILED cu"], "failed": 1, "passed": 10, "skipped": 0, "errors": 0}
    world.fix_edits = None  # đặt trong troly_job
    job, orch = troly_job(world, monkeypatch, [bad, ok])
    world.fix_edits.append(lambda: world.edit("y = 3\n", "app/channels/handfree/x.py"))
    orch.run()
    assert world.calls.count("handfree-tests") == 2 and "fixer-resume" in world.calls
    assert job.data["outcome"] == "fixed", job.data["error"]


def test_ca_auto_fill_khong_chay_test_handfree(world, monkeypatch):
    monkeypatch.setattr(verify, "handfree_baseline", lambda cancel: (_ for _ in ()).throw(AssertionError("không được đo")))
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed" and "handfree-tests" not in world.calls


def test_baseline_do_nen_tu_dau_ca_truoc_khi_trong_tai_quyet(world, monkeypatch):
    def baseline(cancel):
        world.calls.append("baseline")
        return {"bad": [], "failed": 0, "passed": 10, "skipped": 0, "errors": 0}

    monkeypatch.setattr(verify, "baseline", baseline)
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert world.calls.count("baseline") == 1
    assert world.calls.index("baseline") < world.calls.index("arbiter")  # không còn đợi trọng tài xong mới đo


def test_ca_ket_thuc_som_thi_dung_phan_do_nen(world, monkeypatch):
    seen = {}

    def slow_baseline(cancel):
        while not cancel.is_set():  # giả lập bộ test dài: chỉ dừng khi được báo
            time_module.sleep(0.01)
        seen["stopped"] = True
        raise verify.Stopped()

    monkeypatch.setattr(verify, "baseline", slow_baseline)
    world.opinions = {r: opinion("ocr") for r in world.opinions}
    world.decisions = [{"decision": "skip_ocr", "cause": "ocr", "reason": "OCR đọc sai"}]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "skipped_ocr"
    orch._baselines.exception(timeout=5)  # luồng đo nền đã thoát
    assert seen.get("stopped") is True



def test_ke_hoach_phai_duoc_dong_y_truoc_khi_sua(world, reviewer):
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert len(reviewer["plans_seen"]) == 1 and reviewer["plans_seen"][0]["revision"] == 1
    assert world.calls.index("arbiter") < world.calls.index("fixer")
    assert job.data["rounds"][0]["planReviews"][0]["decision"] == "approve"
    assert job.data.get("planApproval") is None


def test_khong_dong_y_ke_hoach_thi_dung_chua_sua_code(world, reviewer):
    reviewer["plans"] = [{"decision": "reject", "note": "đừng sửa mapper chung"}]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "not_approved"
    assert "đừng sửa mapper chung" in job.data["report"]["reason"]
    assert "fixer" not in world.calls and world.code() == "x = 1\n" and world.deploys == 0


def test_gop_y_thi_trong_tai_lap_lai_ke_hoach(world, reviewer):
    revised = {**world.decisions[0], "reason": "kế hoạch mới", "plan": {**PLAN, "summary": "khoanh riêng thủ tục"}}
    world.decisions = [world.decisions[0], revised]
    reviewer["plans"] = [{"decision": "retry", "note": "khoanh riêng thủ tục này"}, {"decision": "approve", "note": ""}]
    prompts = []
    real = world.run_agent

    def spy(**kwargs):
        if kwargs.get("schema") is roles.DECISION_SCHEMA:
            prompts.append(kwargs["prompt"])
        return real(**kwargs)

    claude_runner.run_agent = spy
    try:
        job, orch = start()
        orch.run()
    finally:
        claude_runner.run_agent = real
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert world.calls.count("arbiter") == 2 and [p["revision"] for p in reviewer["plans_seen"]] == [1, 2]
    assert "khoanh riêng thủ tục này" in prompts[1] and "plan_note" in prompts[1]
    round_ = job.data["rounds"][0]
    assert round_["decision"]["plan"]["summary"] == "khoanh riêng thủ tục" and len(round_["planHistory"]) == 1


def test_qua_gio_khong_ai_duyet_ke_hoach_thi_dung(world, reviewer, monkeypatch):
    monkeypatch.setattr(orchestrator, "APPROVAL_TIMEOUT_S", 0)
    reviewer["plans"] = [None]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "not_approved" and "không ai duyệt kế hoạch" in job.data["report"]["reason"]
    assert "fixer" not in world.calls


# ---- thủ tục có thanh tra (điền đợt 2) --------------------------------------------------------------------------------

def _tt_job():
    return {"requestId": "req-mau", "description": "Ô họ tên sai", "settings": {}}


def _tt_case(**info):
    return {"caseDir": "runs/x/case", "label": "Thủ tục mẫu", "procedure": "thu-tuc-mau", "pipeline": "thu_tuc_mau",
            "thanhTra": {"has": True, "kind": "surveyjs", "dir": "auto-fill-hcc-backend/app/pipelines/thu_tuc_mau/thanh_tra/", **info}}


def test_thu_tuc_co_thanh_tra_thi_hoi_dong_co_vai_soat_thanh_tra_va_quy_tac_can_bang():
    brief = roles.case_brief(_tt_job(), _tt_case(ran="done", patched=2, outcomes={"sua": 1}), [])
    assert "Lớp thanh tra" in brief and "Cân bằng" in brief and "second_pass.json" in brief
    assert "thu_tuc_mau/thanh_tra/" in brief and "ghi lại 2 ô" in brief
    assert list(roles.analysts(None, True)) == ["ocr", "mapper", "form", "thanh_tra"]
    system, _ = roles.analyst_prompt("thanh_tra", brief, None, True)
    assert "Soát thanh tra" not in system and "THANH TRA" in system
    assert "thanh_tra" in roles.CAUSES and "plain" in roles.DECISION_SCHEMA["required"]


def test_thu_tuc_khong_thanh_tra_hoac_luot_dinh_kem_thi_brief_nhu_cu():
    plain = {"caseDir": "runs/x/case", "label": "Thủ tục mẫu", "procedure": "thu-tuc-mau", "pipeline": "thu_tuc_mau"}
    assert "Lớp thanh tra" not in roles.case_brief(_tt_job(), plain, [])
    assert "Lớp thanh tra" not in roles.case_brief(_tt_job(), {**_tt_case(ran="done"), "kind": "attach"}, [])
    assert list(roles.analysts("attach", True)) == ["ocr", "mapper", "form"]


def test_luot_goc_khong_chay_thanh_tra_thi_brief_noi_ro():
    brief = roles.case_brief(_tt_job(), _tt_case(ran=None), [])
    assert "KHÔNG chạy thanh tra" in brief and "second_pass.json là" not in brief


def test_doc_co_second_pass_trong_registry(monkeypatch, tmp_path):
    registry = tmp_path / "app/procedures/registry.py"
    registry.parent.mkdir(parents=True)
    registry.write_text('PROCEDURES = [\n    {\n        "key": "a-b",\n        "secondPass": True,\n    },\n    {\n'
                        '        "key": "c-d",\n        "label": "x",\n    },\n    {\n        "key": "e-f",\n'
                        '        # "secondPass": "formio",\n        "secondPass": "formio",\n    },\n]\n', encoding="utf-8")
    monkeypatch.setattr(evidence, "BE", tmp_path)
    assert evidence.second_pass_kind("a-b") == "surveyjs"
    assert evidence.second_pass_kind("c-d") is None  # không lấy nhầm secondPass của thủ tục sau
    assert evidence.second_pass_kind("e-f") == "formio"
    assert evidence.second_pass_kind("khong-co") is None
