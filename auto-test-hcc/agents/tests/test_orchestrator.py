"""Kịch bản đầu-cuối của máy trạng thái với agent/backend giả. Cái được kiểm là luồng và các chốt chặn."""
import json
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


def start(reproduce=True, rounds=3, runs=5):
    job = Job.create(
        request_id="req_test", description="ô giới tính bị trống", created_by="t",
        settings={"runs": runs, "maxRounds": rounds, "reproduce": reproduce, "replayAccount": "u"},
        preview={"label": "Thủ tục"}, warnings=[],
    )
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


def test_trot_ca_ba_vong_thi_hoan_tac_va_tra_stack(world):
    world.after_runs = [[BAD] * 5]
    world.fix_edits = [lambda: world.edit("x = 2\n"), lambda: world.edit("x = 3\n"), lambda: world.edit("x = 4\n")]
    job, orch = start()
    orch.run()
    assert job.data["outcome"] == "need_human"
    assert world.code() == "x = 1\n"
    assert len(job.data["rounds"]) == 3
    # 3 lần build bản sửa + 1 lần build trả về code gốc.
    assert world.deploys == 4 and job.data["stackDirty"] is False
    assert job.data["fix"] is None


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
    assert world.deploys == 0 and world.code() == "x = 1\n"


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
    assert world.code() == "x = 1\n"


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


def portal_job(monkeypatch, world, on_wait=None, logged_in=lambda: False, enter_error=None):
    """Job chạy trên cổng với trình duyệt giả: người dùng bấm tiếp ngay khi web hiện yêu cầu."""
    calls = []
    job = Job.create(
        request_id="req_test", description="ô giới tính bị trống", created_by="t",
        settings={"runs": 5, "maxRounds": 1, "reproduce": True, "replayAccount": "u", "mode": "portal"},
        preview={"label": "Thủ tục"}, warnings=[],
    )

    def open_home(state, cancel, log):
        calls.append("open")

    def enter(procedure, credentials, state, cancel, log):
        calls.append("enter")
        if enter_error:
            raise RuntimeError(enter_error)
        state["formFields"] = 9

    def replay_on_portal(case, count, phase, job_dir, credentials, state, cancel, wait_human, on_run, log):
        calls.append(f"portal:{phase}")
        return world.replay(case, count, phase, job_dir, credentials, cancel, on_run)

    monkeypatch.setattr(orchestrator.browser, "open_home", open_home)
    monkeypatch.setattr(orchestrator.browser, "enter_form", enter)
    monkeypatch.setattr(orchestrator.browser, "is_logged_in", lambda state, cancel, log: logged_in())
    monkeypatch.setattr(orchestrator.browser, "replay_on_portal", replay_on_portal)

    def press_ready():
        # Nhận theo câu nhắc: hai lần chờ có thể nối sát nhau, không kịp thấy khoảng trống ở giữa.
        answered = None
        while job.data["status"] not in ("done", "failed", "stopped"):
            human = job.data.get("human")
            if human and human["since"] != answered:
                answered = human["since"]
                calls.append("human")
                if on_wait:
                    on_wait(job)
                else:
                    job.ready.set()
            time_module.sleep(0.01)

    threading.Thread(target=press_ready, daemon=True).start()
    return job, Orchestrator(job, {"username": "u", "password": "mat-khau"}), calls


def test_tren_cong_cho_nguoi_dang_nhap_roi_moi_chay(world, monkeypatch):
    job, orch, calls = portal_job(monkeypatch, world)
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert calls[:4] == ["open", "human", "enter", "portal:reproduce"] and "portal:round1" in calls
    assert job.data["human"] is None


def test_dang_nhap_xong_bot_tu_di_tiep_khong_can_bam_gi(world, monkeypatch):
    # on_wait không bấm nút: bot phải tự nhận ra đã đăng nhập.
    job, orch, calls = portal_job(monkeypatch, world, on_wait=lambda j: None, logged_in=lambda: True)
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert "enter" in calls and job.data["human"] is None


def test_bot_ket_khi_vao_to_khai_thi_nho_nguoi_roi_chay_tiep(world, monkeypatch):
    seen = []

    def press(job):
        seen.append(job.data["human"]["button"])
        job.ready.set()

    job, orch, calls = portal_job(monkeypatch, world, on_wait=press, enter_error="Cổng dừng ở bước Thông tin chủ hồ sơ.")
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert seen == ["Tôi đã đăng nhập xong", "Đã tới tờ khai, chạy tiếp"]
    assert calls.index("portal:reproduce") > calls.index("enter")


def test_dung_khi_dang_cho_nguoi_thi_thoat_ngay(world, monkeypatch):
    job, orch, calls = portal_job(monkeypatch, world, on_wait=lambda j: j.cancel.set())
    orch.run()
    assert job.data["status"] == "stopped" and job.data["human"] is None
    assert "portal:reproduce" not in calls


def test_het_gio_cho_nguoi_thi_bao_loi(world, monkeypatch):
    monkeypatch.setattr(orchestrator.browser, "HUMAN_TIMEOUT_S", 0)
    job, orch, _ = portal_job(monkeypatch, world, on_wait=lambda j: None)
    orch.run()
    assert job.data["status"] == "failed" and "không thấy bấm tiếp" in job.data["error"]


def test_tren_cong_be_dung_ma_form_trong_thi_khong_duoc_coi_la_dat(world, monkeypatch):
    fields = [{"name": "hoTen", "value": "A"}, {"name": "gioiTinh", "value": "Nam"}]
    world.pre_runs = [{"status": "ok", "response": {"fields": fields}, "form": {"hoTen": "A", "gioiTinh": ""}}] * 5
    world.after_runs = [[{"status": "ok", "response": {"fields": fields}, "form": {"hoTen": "A", "gioiTinh": ""}}] * 5]
    job, orch, _ = portal_job(monkeypatch, world)
    orch.run()
    assert job.data["outcome"] == "need_human"
    assert job.data["reproduce"]["formGaps"][0]["field"] == "gioiTinh"
    assert world.code() == "x = 1\n"


def test_sua_extension_chay_test_extension_khong_build_backend(world, monkeypatch):
    world.fix_edits = [lambda: world.edit_ext("const a = 2;\n")]
    job, orch, calls = portal_job(monkeypatch, world)
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert world.edit_extension is True
    assert "extension-tests" in world.calls
    assert "pipeline-tests" not in world.calls and "full-tests" not in world.calls and world.deploys == 0
    assert world.ext_code() == "const a = 2;\n"
    assert job.data["rounds"][0]["tests"]["extension"]["ok"]


def test_sua_extension_danh_dau_de_nap_lai_truoc_khi_chay_kiem(world, monkeypatch):
    seen = {}
    world.fix_edits = [lambda: world.edit_ext("const a = 2;\n")]
    job, orch, _ = portal_job(monkeypatch, world)
    real = orchestrator.browser.replay_on_portal

    def spy(case, count, phase, job_dir, credentials, state, *rest):
        seen[phase] = state.get("extensionStale")
        return real(case, count, phase, job_dir, credentials, state, *rest)

    monkeypatch.setattr(orchestrator.browser, "replay_on_portal", spy)
    orch.run()
    assert seen == {"reproduce": None, "round1": True}


def test_test_extension_moi_do_thi_tra_lai_agent(world, monkeypatch):
    world.extension_results = [{"total": 10, "failed": ["a.test.js"]}]
    world.fix_edits = [lambda: world.edit_ext("const a = 2;\n"), lambda: world.edit_ext("const a = 3;\n")]
    job, orch, _ = portal_job(monkeypatch, world)
    orch.run()
    assert job.data["outcome"] == "fixed" and "fixer-resume" in world.calls
    assert world.deploys == 0


def test_hoan_tac_extension_cung_danh_dau_nap_lai(world, monkeypatch):
    world.after_runs = [[BAD] * 5]
    world.fix_edits = [lambda: world.edit_ext("const a = 2;\n")]
    job, orch, _ = portal_job(monkeypatch, world)
    orch.run()
    assert job.data["outcome"] == "need_human"
    assert world.ext_code() == "const a = 1;\n"
    assert orch.portal_state["extensionStale"] is True


def test_sua_ca_be_lan_fe_chay_du_hai_bo_test_va_build(world, monkeypatch):
    def both():
        world.edit("x = 2\n")
        return world.edit_ext("const a = 2;\n")

    world.fix_edits = [both]
    job, orch, _ = portal_job(monkeypatch, world)
    orch.touched = []
    real = world.run_agent

    def spy(**kwargs):
        result = real(**kwargs)
        if kwargs.get("can_edit"):
            kwargs["touched"].append(str(world.be / "app/a.py"))
        return result

    monkeypatch.setattr(claude_runner, "run_agent", spy)
    orch.run()
    assert job.data["outcome"] == "fixed", job.data["error"]
    assert "extension-tests" in world.calls and "full-tests" in world.calls and world.deploys == 1


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
