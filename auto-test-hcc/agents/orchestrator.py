"""Máy trạng thái của một job: thu thập → chạy lại → họp → trọng tài → sửa → test → NGƯỜI DUYỆT → build → chạy lại → kết luận.

Phân vai: agent phân tích và viết code; mọi việc quyết định kết quả (chạy test, build, chấm 5 lần, hoàn tác) do mã
ở đây làm. Trọng tài chỉ đề ra tiêu chí, đạt hay không là do scoring.py chấm trên output thật của backend.
Code agent viết chỉ được build lên Docker và nạp vào extension sau khi người vận hành đọc patch và bấm đồng ý
(_await_approval). Không có cờ bỏ qua bước duyệt.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import claude_runner
import codeguard
import evidence
import publish
import regression_case
import replay
import roles
import scoring
import verify
import workspace
from claude_runner import AgentError, AgentResult
from config import (
    AGENT_TIMEOUT_S, APPROVAL_TIMEOUT_S, CASES, FIXER_TIMEOUT_S, JOB_BUDGET_USD, MAIN, MAX_REPAIRS, REGRESSION_CASES, RUNS,
    USE_WORKSPACE,
)
from verify import Stopped

_EVENT_LIMIT = 500
_SAVE_EVERY_S = 1.0
_SAVE_RETRY_S = (0.05, 0.1, 0.2, 0.4, 0.8)
# Chạy lại ra dưới chừng này field của lượt gốc thì coi là không giống lượt gốc.
_FAITHFUL_RATIO = 0.7
# Cả hội đồng cùng kết luận không có gì để sửa thì khỏi tốn một vòng phản biện.
_NO_DEBATE = {"ocr", "extension", "input", "not_a_bug"}
_NO_DEBATE_CONFIDENCE = 80

HEADLINES = {
    "fixed": "Đã sửa, chạy lại đạt hết",
    "skipped_ocr": "Bỏ qua: lỗi do OCR đọc sai",
    "report_only": "Không sửa code, chỉ báo cáo",
    "not_reproduced": "Không tái hiện được lỗi với code hiện tại",
    "need_human": "Chưa sửa được, cần người xem",
    "not_approved": "Bản sửa không được duyệt, mọi thay đổi đã hoàn tác",
}


class _AnyEvent:
    """Huỷ khi một trong các cờ được bật: dừng job, hoặc job xong không cần baseline nữa."""

    def __init__(self, *events: threading.Event):
        self.events = events

    def is_set(self) -> bool:
        return any(e.is_set() for e in self.events)


class JobError(Exception):
    pass


class NotApproved(Exception):
    """Người duyệt bấm dừng hoặc quá giờ không ai duyệt: hoàn tác rồi kết thúc job, không sang vòng sau."""


# Quyết định của người duyệt (POST /agent-api/jobs/{id}/approval).
APPROVE, RETRY, REJECT = "approve", "retry", "reject"
# Số lần tối đa người dùng được yêu cầu trọng tài lập lại kế hoạch trong một vòng (mỗi lần là một lượt agent tốn tiền).
_PLAN_REVISIONS = 3
VERDICTS = (APPROVE, RETRY, REJECT)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Job:
    """Dữ liệu job là dict thuần để trả thẳng cho web; mọi thay đổi đi qua lock vì web đọc từ luồng khác."""

    def __init__(self, data: dict):
        self.data = data
        self.dir: Path = RUNS / data["id"]
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.decided = threading.Event()  # người duyệt đã bấm một nút ở khung duyệt bản sửa
        self.verdict: dict | None = None
        self._saved_at = 0.0

    @classmethod
    def create(cls, *, request_id: str, description: str, created_by: str, settings: dict, preview: dict, warnings: list[str]) -> "Job":
        job_id = f"at_{datetime.now().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        job = cls({
            "id": job_id,
            "requestId": request_id,
            "description": description,
            "createdAt": now(),
            "createdBy": created_by,
            "settings": settings,
            "status": "queued",
            "stage": "collect",
            "outcome": None,
            "error": None,
            "warnings": warnings,
            "approval": None,
            "case": preview,
            "reproduce": None,
            "rounds": [],
            "fix": None,
            "report": None,
            "cost": {"usd": 0.0, "calls": 0},
            "touched": [],
            "stackDirty": False,
            "events": [],
        })
        job.dir.mkdir(parents=True, exist_ok=True)
        job.save()
        return job

    def view(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.data, ensure_ascii=False))

    def summary(self) -> dict:
        with self.lock:
            data = self.data
            case = data.get("case") or {}
            return {
                "id": data["id"],
                "requestId": data["requestId"],
                "label": case.get("label"),
                "description": data["description"],
                "status": data["status"],
                "stage": data["stage"],
                "outcome": data["outcome"],
                "createdAt": data["createdAt"],
                "rounds": len(data["rounds"]),
                "cost": data["cost"],
            }

    def save(self, force: bool = True) -> None:
        if not force and time.monotonic() - self._saved_at < _SAVE_EVERY_S:
            return
        with self.lock:
            text = json.dumps(self.data, ensure_ascii=False)
            self._saved_at = time.monotonic()
            temp = self.dir / "job.json.tmp"
            temp.write_text(text, encoding="utf-8")
            # Windows từ chối replace khi có tiến trình khác đang mở file (Defender, trình đọc): thử lại vài lần.
            # Hỏng hẳn thì thôi: dữ liệu vẫn còn trong RAM, lần lưu sau ghi đủ, không được làm chết job.
            for delay in _SAVE_RETRY_S:
                try:
                    os.replace(temp, self.dir / "job.json")
                    return
                except PermissionError:
                    time.sleep(delay)

    def update(self, **values) -> None:
        with self.lock:
            self.data.update(values)
        self.save()

    def log(self, text: str, level: str = "info", who: str | None = None) -> None:
        with self.lock:
            events = self.data["events"]
            events.append({"t": now(), "level": level, "who": who, "text": text})
            del events[:-_EVENT_LIMIT]
        self.save(force=level != "tool")


class Orchestrator:
    def __init__(self, job: Job, credentials: dict):
        self.job = job
        self.credentials = credentials
        self.guard = codeguard.Guard(job.dir)
        self.settings = job.data["settings"]
        self.case: dict = {}
        self.attempts: list[dict] = []
        self.pre_runs: list[dict] = []
        self.touched: list[str] = []
        self.denied: list[str] = []
        # Code của vòng trượt gần nhất (đã hoàn tác để vòng sau làm lại từ code gốc): hết vòng mà chưa đạt thì đặt lại cho người xem.
        self.kept: dict | None = None
        # Chứng cứ nằm trong cây agent đọc được: khu làm việc (mục 1) hoặc repo người phát triển (kiểu cũ).
        self.case_dir = CASES / job.data["id"] / "case"
        self.last_runs: list[dict] = []
        self.last_evaluation: dict = {}
        self._baselines = None
        self._baseline_stop = threading.Event()

    # ---- vòng đời ------------------------------------------------------------------------------------------

    def run(self) -> None:
        job = self.job
        job.update(status="running")
        try:
            self._run()
        except Stopped:
            self._cleanup()
            job.log("Đã dừng theo yêu cầu.")
            job.update(status="stopped")
        except (evidence.CaseError, replay.LoginError, AgentError, JobError) as reason:
            self._cleanup()
            job.log(str(reason), level="error")
            job.update(status="failed", error=str(reason))
        except Exception as reason:  # noqa: BLE001 — lỗi lạ vẫn phải hoàn tác, không để backend ở trạng thái dở
            self._cleanup()
            job.log(traceback.format_exc()[-1500:], level="error")
            job.update(status="failed", error=f"{type(reason).__name__}: {reason}")
        finally:
            self._baseline_stop.set()  # ca kết thúc không cần sửa: dừng phần đo nền còn chạy
            self.guard.discard_snapshot()
            job.save()

    def _run(self) -> None:
        self._prepare_workspace()
        self._collect()
        self._start_baselines()
        self._reproduce()
        for number in range(1, self.settings["maxRounds"] + 1):
            round_ = self._new_round(number)
            self._meeting(round_)
            decision = self._arbiter(round_)
            plan_notes: list[str] = []
            while True:
                kind = decision.get("decision")
                if kind == "skip_ocr":
                    return self._finish("skipped_ocr", decision.get("reason", ""))
                if kind == "report_only":
                    return self._finish("report_only", decision.get("reason", ""))
                problem = self._decision_problem(decision)
                if problem:
                    break
                precheck = scoring.evaluate(decision["acceptance"], self._precheck_runs())
                with self.job.lock:
                    round_["precheck"] = precheck
                if precheck["allPass"]:
                    return self._finish(
                        "not_reproduced",
                        f"Tiêu chí của trọng tài đã đạt {precheck['passed']}/{precheck['total']} lần với code hiện tại, nên không sửa gì. "
                        "Lỗi có thể đã được sửa từ sau lượt gốc, hoặc chỉ thỉnh thoảng mới xảy ra.",
                    )
                # Kế hoạch sửa phải có người đồng ý trước khi agent đụng vào code.
                verdict = self._await_plan(round_, decision, revision=len(plan_notes) + 1)
                if verdict["decision"] == APPROVE:
                    break
                if verdict["decision"] == REJECT:
                    note = verdict.get("note") or ""
                    reason = verdict.get("timeoutNote") or ("Người dùng không đồng ý kế hoạch sửa" + (f": {note}" if note else "."))
                    return self._finish("not_approved", reason + " Chưa sửa dòng code nào.")
                plan_notes.append(verdict["note"])
                with self.job.lock:
                    round_.setdefault("planHistory", []).append(round_["decision"])
                decision = self._arbiter(round_, plan_notes)
            if problem:
                self._round_failed(round_, decision, problem)
                continue
            try:
                if self._attempt(round_, decision):
                    return self._finish("fixed", decision.get("reason", ""))
            except NotApproved as reason:
                return self._finish("not_approved", str(reason))
        # Build trả stack về code gốc TRƯỚC khi đặt lại code để người xem: bản này chưa qua chạy kiểm, không được lên Docker.
        self._restore_stack()
        kept = self._keep_last_fix()
        reason = "Đã thử hết số vòng cho phép mà chưa đạt, xem lý do từng vòng ở trên."
        if kept:
            reason += (f" Code của vòng {kept} vẫn để trong thư mục làm việc cho người xem, chưa build lên Docker. "
                       "Không dùng thì bấm Hoàn tác bản sửa.")
        else:
            reason += " Không có code nào để lại, mọi thay đổi đã được hoàn tác."
        self._finish("need_human", reason)

    def _stage(self, name: str, text: str | None = None) -> None:
        if self.job.cancel.is_set():
            raise Stopped()
        self.job.update(stage=name)
        if text:
            self.job.log(text)

    def _finish(self, outcome: str, reason: str) -> None:
        job = self.job
        # Vòng trước có thể đã build bản sửa rồi trượt: code đã hoàn tác nhưng stack vẫn chạy bản đó.
        self._restore_stack()
        report = {"outcome": outcome, "headline": HEADLINES[outcome], "reason": reason, "finishedAt": now()}
        # Câu đời thường của trọng tài vòng cuối: web hiện cho tester trước, lý do kỹ thuật thu gọn bên dưới.
        decision = next((r.get("decision") for r in reversed(job.data.get("rounds") or []) if r.get("decision")), None) or {}
        if decision.get("plain"):
            report["plain"] = decision["plain"]
        job.update(stage="report", status="done", outcome=outcome, report=report)
        job.log(f"Kết luận: {report['headline']}.")

    def _cleanup(self) -> None:
        """Dừng hay lỗi giữa chừng đều trả code và stack Docker về như lúc đầu."""
        try:
            self._rollback()
            self._restore_stack()
        except Exception as reason:  # noqa: BLE001
            self.job.log(f"Hoàn tác lỗi, cần xem tay: {reason}", level="error")
            with self.job.lock:
                self.job.data["warnings"].append(f"Hoàn tác lỗi, cần xem tay: {reason}")

    def _rollback(self) -> None:
        if not self.guard.taken or not self.touched:
            return
        changes, _ = self.guard.changes(self.touched, extension=False)
        self.guard.restore(changes)
        if changes:
            self.job.log(f"Đã hoàn tác {len(changes)} file: {', '.join(c.rel for c in changes)}")
        self.touched = []
        self.job.update(touched=[])

    def _restore_stack(self) -> None:
        """Stack đang chạy bản sửa đã bị hoàn tác → build lại, kẻo backend local chạy code không có trong repo."""
        if not self.job.data.get("stackDirty"):
            return
        self.job.log("Build lại backend về code trước khi sửa…")
        result = verify.deploy(threading.Event())
        if not result["ok"]:
            raise JobError(f"Build lại sau khi hoàn tác bị lỗi ở bước {result.get('step')}")
        self.job.update(stackDirty=False)

    # ---- baseline đo nền ------------------------------------------------------------------------------------

    def _measure_baselines(self, cancel) -> dict:
        before = {"backend": verify.baseline(cancel)}
        before["regression"] = verify.regression_baseline(cancel)
        if self.for_troly:
            before["handfree"] = verify.handfree_baseline(cancel)
        return before

    def _start_baselines(self) -> None:
        """Đo baseline test ngay khi có cây code, song song với chạy lại + họp (trước đây đợi trọng tài xong mới đo, người dùng
        chờ thêm vài phút). Cây code không đổi tới lúc agent sửa nên kết quả vẫn đúng; ca kết thúc sớm thì dừng."""
        stop = self._baseline_stop
        cancel = _AnyEvent(self.job.cancel, stop)
        self._baselines = ThreadPoolExecutor(max_workers=1, thread_name_prefix="baseline").submit(self._measure_baselines, cancel)

    def _baseline_result(self) -> dict:
        if self._baselines is None:
            return self._measure_baselines(self.job.cancel)
        if not self._baselines.done():
            self.job.log("Baseline test vẫn đang đo nền, chờ xong rồi mới sửa…")
        return self._baselines.result()

    # ---- khu làm việc ----------------------------------------------------------------------------------------

    def _prepare_workspace(self) -> None:
        """Cây code sạch, đúng tag release đang chạy production; backend thử build đúng cây đó trước khi chạy lại req."""
        if not USE_WORKSPACE:
            return
        job = self.job
        self._stage("workspace", "Đặt khu làm việc về tag release đang chạy production…")
        try:
            info = workspace.prepare(job.data["id"], job.log)
        except (workspace.WorkspaceError, subprocess.TimeoutExpired, OSError) as reason:
            raise JobError(f"Không dựng được khu làm việc: {reason}") from reason
        job.update(workspace=info)
        built = verify.ensure_stack(job.cancel)
        if built is not None:
            job.log("Backend thử đã build theo khu làm việc." if built["ok"] else "Build backend thử lỗi.")
            if not built["ok"]:
                raise JobError(f"Không build được backend thử ở bước {built.get('step')}: "
                               f"{(built.get('output') or built.get('health') or '')[-400:]}")

    # ---- thu thập + chạy lại trước khi sửa -----------------------------------------------------------------

    def _collect(self) -> None:
        self._stage("collect", "Thu thập chứng cứ của req…")
        self.case = evidence.collect(self.job.data["requestId"], self.case_dir)
        applicant = self.settings.get("applicant")
        if applicant:
            options = self.case["options"]
            options["formContext"] = {**(options.get("formContext") or {}), **applicant}
        public = {k: v for k, v in self.case.items()
                  if k not in ("options", "storedFiles", "fields", "firstPassFields", "caseDir", "plan")}
        self.job.update(case=public)
        if replay.is_attach(self.case):
            self.job.log(f"Lượt ĐÍNH KÈM · thủ tục {self.case.get('label')}, {len(self.case['storedFiles'])} tệp, "
                         f"{len(self.case.get('plan') or [])} mục trong kế hoạch lượt gốc.")
        else:
            self.job.log(f"Thủ tục {self.case.get('label')}, {len(self.case['storedFiles'])} tệp, {len(self.case['fields'])} field ở lượt gốc.")
            info = self.case.get("thanhTra") or {}
            if info.get("has"):
                ran = info.get("ran")
                self.job.log("Thủ tục có lớp thanh tra (soát lại sau lượt điền đầu). " + (
                    f"Lượt gốc thanh tra ghi lại {info.get('patched', 0)} ô; chạy lại sẽ chờ thanh tra rồi chấm trên giá trị cuối."
                    if ran == "done" else f"Lượt gốc thanh tra không xong ({info.get('reason') or ran})." if ran else
                    "Lượt gốc không chạy thanh tra nên chạy lại cũng tắt thanh tra."))

    @property
    def for_troly(self) -> bool:
        return self.settings.get("target") == "troly"

    def _replay(self, phase: str, on_run: Callable[[dict], None]) -> list[dict]:
        runs = replay.replay(self.case, self.settings["runs"], phase, self.job.dir, self.credentials, self.job.cancel, on_run)
        if self.job.cancel.is_set():
            raise Stopped()
        self._share_replay(phase)
        return runs

    def _share_replay(self, phase: str) -> None:
        """OCR + ảnh chụp từng lần chạy lại ghi ở thư mục ca (repo người phát triển, agent bị chặn đọc): chép sang cạnh chứng cứ
        trong khu làm việc, đúng chỗ prompt chỉ ({chứng cứ}/../replay/<lượt>/)."""
        source = self.job.dir / "replay" / phase
        target = self.case_dir.parent / "replay" / phase
        if not source.is_dir() or source.resolve() == target.resolve():
            return
        shutil.copytree(source, target, dirs_exist_ok=True)

    def _table(self, runs: list[dict]) -> list[dict]:
        return scoring.field_table(self.case["fields"], runs, self.case.get("firstPassFields"))

    def _reproduce(self) -> None:
        table = self._table([])
        if self.settings["reproduce"]:
            self._stage("reproduce", f"Chạy lại {self.settings['runs']} lần với code hiện tại để xem lỗi có lặp lại không…")
            live: list[dict] = []
            self.job.update(reproduce={"runs": live, "total": self.settings["runs"]})

            def on_run(run: dict) -> None:
                with self.job.lock:
                    live.append(replay.strip_response(run))
                self.job.log(f"Lần {run['n']}: {run.get('status')}" + (f" · {run['error']}" if run.get("error") else ""))

            self.pre_runs = self._replay("reproduce", on_run)
            if self.pre_runs and not any(scoring.run_ok(r) for r in self.pre_runs):
                raise JobError(f"Chạy lại lỗi cả {len(self.pre_runs)} lần: {self.pre_runs[0].get('error')}")
            table = self._table(self.pre_runs)
            fresh = scoring.ocr_fresh_count(self.pre_runs)
            self._check_runs(self.pre_runs)
            self._check_second_pass(self.pre_runs)
            coverage = scoring.replay_coverage(self.case["fields"], self.pre_runs)
            faithful = coverage["ratio"] >= _FAITHFUL_RATIO
            if not faithful:
                self._warn(
                    f"Chạy lại chỉ ra {coverage['matched']}/{coverage['original']} field có giá trị của lượt gốc, nên kết quả chạy lại "
                    "không đại diện cho lượt gốc. Thường do thiếu ngữ cảnh, ví dụ mốc người nộp của lượt trợ lý."
                )
            with self.job.lock:
                self.job.data["reproduce"].update(
                    table=table, ocrFresh=fresh, coverage=coverage, faithful=faithful, phase="reproduce",
                )
            self.job.save()
        (self.case_dir / "reproduce.json").write_text(
            json.dumps({"runs": [replay.strip_response(r) for r in self.pre_runs], "table": table}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _check_runs(self, runs: list[dict]) -> None:
        """Cảnh báo những lần kết quả không đáng tin như mong đợi. Mỗi lần phải OCR mới, nên lần nào không xác nhận được là báo."""
        done = [r for r in runs if scoring.run_ok(r)]
        fresh = scoring.ocr_fresh_count(done)
        if fresh < len(done):
            self._warn(f"Chỉ {fresh}/{len(done)} lần xác nhận được OCR mới, các lần còn lại có thể trúng cache.")
        if any(r.get("llmReused") for r in runs):
            self._warn("Thủ tục này dùng lại câu trả lời LLM trong 30 phút, nên các lần chạy không đo được độ dao động của LLM.")

    def _check_second_pass(self, runs: list[dict]) -> None:
        """Thủ tục có thanh tra mà lần chạy lại không có kết quả thanh tra thì giá trị chấm chỉ là lượt điền đầu."""
        if not replay.wants_second_pass(self.case):
            return
        done = [r for r in runs if scoring.run_ok(r)]
        missing = [r for r in done if (r.get("secondPass") or {}).get("status") != "done"]
        if missing:
            states = ", ".join(sorted({str((r.get("secondPass") or {}).get("status") or "none") for r in missing}))
            self._warn(f"{len(missing)}/{len(done)} lần chạy lại không có kết quả thanh tra ({states}): các lần đó chấm trên lượt "
                       "điền đầu. Kiểm tra backend thử có bật SECOND_PASS_ENABLED (deploy/compose.*.yml).")

    def _warn(self, text: str) -> None:
        with self.job.lock:
            self.job.data["warnings"].append(text)
        self.job.log(text, level="warn")

    def _precheck_runs(self) -> list[dict]:
        return self.pre_runs or [{"status": "ok", "response": {"fields": self.case["fields"]}}]

    def _baseline_values(self) -> list[dict]:
        values = [scoring.run_values(self.case["fields"])]
        values.extend(scoring.actual_values(r) for r in self.pre_runs if scoring.run_ok(r))
        return values

    # ---- họp ------------------------------------------------------------------------------------------------

    def _new_round(self, number: int) -> dict:
        round_ = {"n": number, "opinions": [], "reviews": [], "debate": None, "decision": None, "fix": None,
                  "tests": None, "approval": None, "deploy": None, "retest": None, "result": None}
        with self.job.lock:
            self.job.data["rounds"].append(round_)
        self.job.save()
        return round_

    def _agent(self, who: str, kind: str, system: str, prompt: str, schema: dict, *, can_edit: bool = False, resume: str | None = None) -> AgentResult:
        model, effort = roles.model_for(kind)

        def on_event(text: str) -> None:
            if can_edit:
                self.job.update(touched=list(self.touched))
            self.job.log(text, level="tool", who=who)

        tries = 1 if can_edit else 2  # agent sửa đã có thể sửa dở, không chạy lại mù
        for attempt in range(1, tries + 1):
            try:
                result = claude_runner.run_agent(
                    model=model, effort=effort, system=system, prompt=prompt, schema=schema,
                    timeout=FIXER_TIMEOUT_S if can_edit else AGENT_TIMEOUT_S,
                    cancel=self.job.cancel, on_event=on_event, can_edit=can_edit, resume=resume,
                    # Chỉ gọi backend, extension không chạy: sửa extension là không kiểm chứng được nên không cho sửa.
                    edit_extension=False,
                    touched=self.touched if can_edit else None,
                )
                break
            except AgentError as reason:
                if attempt == tries:
                    raise
                self.job.log(f"{who} lỗi, thử lại: {reason}", level="warn")
        with self.job.lock:
            cost = self.job.data["cost"]
            cost["usd"] = round(cost["usd"] + result.cost, 4)
            cost["calls"] += 1
            spent = cost["usd"]
        self.job.save()
        if spent > JOB_BUDGET_USD:
            raise JobError(f"Job đã tiêu {spent:.2f} USD, vượt trần {JOB_BUDGET_USD:.0f} USD")
        return result

    def _ask(self, role: str, label: str, system: str, prompt: str, schema: dict, resume: str | None = None) -> dict:
        self.job.log("Bắt đầu phân tích", who=label)
        try:
            result = self._agent(label, "analyst", system, prompt, schema, resume=resume)
        except AgentError as reason:
            return {"role": role, "label": label, "error": str(reason)}
        return {"role": role, "label": label, "sessionId": result.session_id, "cost": result.cost, **result.output}

    def _together(self, tasks: list[Callable[[], dict]]) -> list[dict]:
        with ThreadPoolExecutor(max_workers=max(1, len(tasks))) as pool:
            return [f.result() for f in [pool.submit(task) for task in tasks]]

    def _meeting(self, round_: dict) -> None:
        brief = roles.case_brief(self.job.data, self.case, self.attempts)
        self._stage("meeting", f"Vòng {round_['n']}: hội đồng phân tích độc lập…")
        tasks = []
        thanh_tra = roles.has_thanh_tra(self.case)
        for role, spec in roles.analysts(self.case.get("kind"), thanh_tra).items():
            system, prompt = roles.analyst_prompt(role, brief, self.case.get("kind"), thanh_tra)
            tasks.append(lambda r=role, l=spec["label"], s=system, p=prompt: self._ask(r, l, s, p, roles.OPINION_SCHEMA))
        opinions = self._together(tasks)
        with self.job.lock:
            round_["opinions"] = opinions
        self.job.save()
        valid = [o for o in opinions if not o.get("error")]
        if len(valid) < 2:
            raise JobError("Hội đồng không đủ ý kiến: " + "; ".join(str(o.get("error")) for o in opinions if o.get("error")))
        skip = self._debate_skip_reason(valid)
        if skip:
            with self.job.lock:
                round_["debate"] = {"skipped": True, "reason": skip}
            self.job.log(skip)
            return

        self.job.log("Các ý kiến khác nhau hoặc cần chốt cách sửa, mở vòng phản biện…")
        public = [self._public_opinion(o) for o in valid]
        tasks = []
        for opinion in valid:
            others = [p for p in public if p["role"] != opinion["role"]]
            system, _ = roles.analyst_prompt(opinion["role"], brief, self.case.get("kind"), thanh_tra)
            tasks.append(lambda o=opinion, s=system, x=others: self._ask(
                o["role"], o["label"], s, roles.review_prompt(x), roles.REVIEW_SCHEMA, resume=o.get("sessionId"),
            ))
        system, prompt = roles.critic_prompt(brief, public)
        tasks.append(lambda s=system, p=prompt: self._ask("critic", roles.CRITIC["label"], s, p, roles.REVIEW_SCHEMA))
        reviews = self._together(tasks)
        with self.job.lock:
            round_["reviews"] = reviews
            round_["debate"] = {"skipped": False}
        self.job.save()

    @staticmethod
    def _debate_skip_reason(opinions: list[dict]) -> str | None:
        causes = {o["cause"] for o in opinions}
        if len(causes) == 1 and causes <= _NO_DEBATE and min(o["confidence"] for o in opinions) >= _NO_DEBATE_CONFIDENCE:
            return "Cả hội đồng cùng kết luận và không có gì để sửa nên bỏ vòng phản biện."
        return None

    @staticmethod
    def _public_opinion(opinion: dict) -> dict:
        return {k: v for k, v in opinion.items() if k not in ("sessionId", "cost")}

    def _arbiter(self, round_: dict, plan_notes: list[str] | None = None) -> dict:
        self._stage("arbiter", "Trọng tài lập lại kế hoạch theo góp ý…" if plan_notes else "Trọng tài xem xét và ra quyết định…")
        brief = roles.case_brief(self.job.data, self.case, self.attempts)
        opinions = [self._public_opinion(o) for o in round_["opinions"] if not o.get("error")]
        reviews = [self._public_opinion(o) for o in round_["reviews"] if not o.get("error")]
        prompt = roles.arbiter_prompt(brief, opinions, reviews, plan_notes=plan_notes, previous=round_.get("decision"))
        result = self._agent("Trọng tài", "arbiter", roles.ARBITER_SYSTEM, prompt, roles.DECISION_SCHEMA)
        with self.job.lock:
            round_["decision"] = {**result.output, "cost": result.cost}
        self.job.save()
        self.job.log(f"Trọng tài: {result.output.get('decision')} ({result.output.get('cause')})")
        return result.output

    def _decision_problem(self, decision: dict) -> str | None:
        if not decision.get("plan") or not decision.get("acceptance"):
            return "Trọng tài chọn sửa nhưng thiếu kế hoạch hoặc tiêu chí chấm."
        unknown = scoring.unknown_fields(decision["acceptance"], scoring.known_fields(self.case["fields"], self.pre_runs))
        if unknown:
            return f"Tiêu chí trỏ tới field không có trong output: {', '.join(unknown)}. Field phải lấy đúng từ reproduce.json."
        return None

    # ---- sửa + kiểm chứng -----------------------------------------------------------------------------------

    def _attempt(self, round_: dict, decision: dict) -> bool:
        job = self.job
        self._stage("fix", "Chờ baseline test (đã đo nền từ đầu ca)…" if self._baselines else "Đo baseline test trước khi sửa…")
        before = self._baseline_result()
        if before["backend"].get("broken"):
            raise JobError("Bộ test đang hỏng từ trước khi sửa, không có mốc để so: " + before["backend"].get("tail", "")[-300:])
        self.guard.take()
        brief = roles.case_brief(job.data, self.case, self.attempts)
        self.touched = []
        self.denied = []
        job.log("Bắt đầu sửa theo kế hoạch", who="Sửa code")
        result = self._agent("Sửa code", "fixer", roles.FIXER_SYSTEM, roles.fixer_prompt(brief, decision), roles.FIX_SCHEMA, can_edit=True)
        self.denied += result.denied
        output, session = result.output, result.session_id
        with job.lock:
            round_["fix"] = {**output, "cost": result.cost, "repairs": 0}
        job.save()

        for repair in range(MAX_REPAIRS + 1):
            problem = self._check_code(round_, output, before)
            if problem is None:
                break
            if repair == MAX_REPAIRS:
                return self._round_failed(round_, decision, problem)
            self._stage("fix", f"Kiểm tra chưa đạt, trả lại cho agent sửa (lần {repair + 1}/{MAX_REPAIRS})…")
            result = self._agent(
                "Sửa code", "fixer", roles.FIXER_SYSTEM,
                f"Hệ thống kiểm tra báo lỗi:\n\n{problem}\n\nHãy sửa tiếp cho đạt.",
                roles.FIX_SCHEMA, can_edit=True, resume=session,
            )
            self.denied += result.denied
            output, session = result.output, result.session_id or session
            with job.lock:
                round_["fix"].update(output, repairs=repair + 1)
            job.save()

        changes, _ = self.guard.changes(self.touched, extension=False)
        verdict = self._await_approval(round_, changes)
        if verdict["decision"] != APPROVE:
            note = verdict.get("note") or ""
            if verdict.get("timeout"):
                problem = note
            else:
                problem = "Người duyệt không đồng ý bản sửa" + (f": {note}" if note else ".")
            # Code người duyệt đã bác thì không để lại, kể cả khi job kết thúc ở Cần người xem.
            self._round_failed(round_, decision, problem, reviewer_note=note if verdict["decision"] == RETRY else None, keep=False)
            if verdict["decision"] == RETRY:
                return False
            raise NotApproved(problem + " Code đã trả về như trước khi sửa.")
        changes = self._changes_after_approval(round_)
        # stackDirty: vòng trước đã build bản sửa nay bị hoàn tác, nên dù vòng này chỉ đổi test vẫn phải build lại.
        if codeguard.touches_backend_app(changes) or job.data.get("stackDirty"):
            self._stage("deploy", "Build lại backend thử với bản sửa…")
            job.update(stackDirty=True)
            deployed = verify.deploy(job.cancel)
            with job.lock:
                round_["deploy"] = deployed
            job.save()
            if not deployed["ok"]:
                return self._round_failed(round_, decision, f"Build hoặc healthz lỗi ở bước {deployed.get('step')}: {deployed.get('output', deployed.get('health', ''))[-500:]}")
        return self._retest(round_, decision, changes)

    def _await_plan(self, round_: dict, decision: dict, revision: int) -> dict:
        """Trọng tài chọn sửa: dừng chờ người dùng đọc kế hoạch. approve = sửa theo kế hoạch; retry = trọng tài lập lại theo góp ý
        (tối đa _PLAN_REVISIONS lần mỗi vòng); reject hoặc quá giờ = kết thúc, chưa đụng dòng code nào."""
        job = self.job
        can_revise = revision <= _PLAN_REVISIONS
        self._stage("plan", "Trọng tài đã lập kế hoạch sửa. Chờ bạn xác nhận trước khi agent sửa code…")
        with job.lock:
            job.verdict = None
            job.decided.clear()
        job.update(planApproval={"round": round_["n"], "revision": revision, "since": now(), "canRevise": can_revise,
                                 "timeoutMin": APPROVAL_TIMEOUT_S // 60})
        job.log(f"Chờ duyệt kế hoạch sửa vòng {round_['n']}" + (f" (bản {revision})" if revision > 1 else "") + ".", level="warn")
        deadline = time.monotonic() + APPROVAL_TIMEOUT_S
        verdict: dict | None = None
        try:
            while verdict is None:
                if job.cancel.is_set():
                    raise Stopped()
                if time.monotonic() > deadline:
                    verdict = {"decision": REJECT, "timeout": True,
                               "timeoutNote": f"Quá {APPROVAL_TIMEOUT_S // 60} phút không ai duyệt kế hoạch sửa."}
                elif job.decided.wait(1):
                    with job.lock:
                        verdict = dict(job.verdict or {})
        finally:
            job.update(planApproval=None)
        if verdict.get("decision") not in VERDICTS or (verdict["decision"] == RETRY and not (can_revise and verdict.get("note"))):
            verdict["decision"] = REJECT if verdict.get("decision") not in (APPROVE,) else APPROVE
        verdict["at"] = now()
        verdict["revision"] = revision
        with job.lock:
            round_.setdefault("planReviews", []).append(verdict)
        job.save()
        said = {APPROVE: "đồng ý kế hoạch, cho sửa", RETRY: "yêu cầu lập lại kế hoạch", REJECT: "không đồng ý kế hoạch, dừng"}
        job.log(said[verdict["decision"]] + (f" · {verdict['note']}" if verdict.get("note") else ""), who=verdict.get("by") or "Người duyệt")
        return verdict

    def _await_approval(self, round_: dict, changes: list[codeguard.Change]) -> dict:
        """Bản sửa đã qua test nhưng chưa build, chưa nạp extension: dừng lại chờ người đọc patch và bấm duyệt."""
        job = self.job
        self._stage("approve", "Bản sửa đã qua test. Chờ người duyệt đọc patch, chưa build Docker, chưa nạp extension…")
        with job.lock:
            job.verdict = None
            job.decided.clear()
        job.update(approval={
            "round": round_["n"], "since": now(), "files": [c.rel for c in changes],
            "canRetry": round_["n"] < self.settings["maxRounds"], "timeoutMin": APPROVAL_TIMEOUT_S // 60,
        })
        job.log(f"Chờ duyệt bản sửa vòng {round_['n']} ({len(changes)} file).", level="warn")
        deadline = time.monotonic() + APPROVAL_TIMEOUT_S
        verdict: dict | None = None
        try:
            while verdict is None:
                if job.cancel.is_set():
                    raise Stopped()
                if time.monotonic() > deadline:
                    verdict = {"decision": REJECT, "timeout": True,
                               "note": f"Quá {APPROVAL_TIMEOUT_S // 60} phút không có ai duyệt bản sửa."}
                elif job.decided.wait(1):
                    with job.lock:
                        verdict = dict(job.verdict or {})
        finally:
            job.update(approval=None)
        if verdict.get("decision") not in VERDICTS:
            verdict["decision"] = REJECT
        verdict["at"] = now()
        with job.lock:
            round_["approval"] = verdict
        job.save()
        said = {APPROVE: "đồng ý, build và chạy kiểm", RETRY: "không đồng ý, làm lại theo góp ý", REJECT: "không đồng ý, dừng"}
        job.log(said[verdict["decision"]] + (f" · {verdict['note']}" if verdict.get("note") else ""), who=verdict.get("by") or "Người duyệt")
        return verdict

    def _changes_after_approval(self, round_: dict) -> list[codeguard.Change]:
        """Lúc chờ duyệt người vận hành có thể sửa tay file agent đã sửa: build đúng nội dung đang có trên đĩa và ghi lại patch."""
        changes, _ = self.guard.changes(self.touched, extension=False)
        patch = codeguard.make_patch(changes)
        if patch != round_["fix"].get("patch"):
            with self.job.lock:
                round_["fix"].update(approvedPatch=round_["fix"].get("patch"), patch=patch, files=[c.rel for c in changes])
            self._warn("File của bản sửa đã đổi sau lúc duyệt (có sửa tay?): build theo nội dung hiện tại trên đĩa, patch đã cập nhật.")
        return changes

    def _check_code(self, round_: dict, output: dict, before: dict) -> str | None:
        """Backend theo đúng thứ tự trong CLAUDE.md, extension chạy cả bộ test của nó. Trả về mô tả lỗi để agent sửa tiếp,
        None nếu đạt. Chỉ chạy bộ test của phía bị đổi."""
        job = self.job
        self._stage("test", "Kiểm tra bản sửa…")
        changes, outside = self.guard.changes(self.touched, extension=False)
        escaped = [path for path in outside if path not in self.denied]
        if escaped:
            raise JobError(f"Agent sửa ngoài phạm vi cho phép: {', '.join(escaped)}. Hãy xem lại các file này.")
        if not changes:
            return "Chưa có thay đổi nào trong code. Hãy thực hiện kế hoạch bằng Edit."
        patch = codeguard.make_patch(changes)
        with job.lock:
            round_["fix"]["files"] = [c.rel for c in changes]
            round_["fix"]["patch"] = patch
        job.save()
        leaks = codeguard.leaked_terms(patch, codeguard.private_terms(self.case["fields"], job.data["requestId"]))
        if leaks:
            return f"Patch chứa dữ liệu thật của hồ sơ ({len(leaks)} chuỗi: {', '.join(leaks)}). Hãy thay bằng dữ liệu bịa."

        with job.lock:
            round_["tests"] = {}
        if codeguard.touches_extension(changes):
            job.log("Chạy bộ test extension để so với trước khi sửa…")
            compared = verify.compare_extension(before["extension"], verify.extension_tests(job.cancel))
            with job.lock:
                round_["tests"]["extension"] = compared
            job.save()
            if not compared["ok"]:
                return "Có test extension mới đỏ so với trước khi sửa:\n" + "\n".join(compared["new"])
        if codeguard.touches_backend(changes):
            return self._check_backend(round_, output, before, changes)
        return None

    def _check_backend(self, round_: dict, output: dict, baselines: dict, changes: list[codeguard.Change]) -> str | None:
        job = self.job
        before = baselines["backend"]
        prefix = f"{codeguard.BE_DIR}/"
        changed_tests = [c.rel for c in changes if c.rel.startswith(f"{prefix}tests/")]
        test_files = verify.find_test_files(self.case.get("pipeline"), [*output.get("testFiles", []), *changed_tests])
        pipeline = verify.pipeline_tests(test_files, job.cancel)
        with job.lock:
            round_["tests"]["pipeline"] = {k: v for k, v in pipeline.items() if k != "output"}
        job.save()
        if pipeline.get("skipped"):
            self._warn("Không tìm thấy file test của pipeline, bỏ qua bước test riêng.")
        elif not pipeline["ok"]:
            return f"Test của pipeline đỏ ({pipeline['summary']}):\n{pipeline['output']}"

        job.log("Chạy toàn bộ test để so với baseline…")
        compared = verify.compare(before, verify.full_tests(job.cancel))
        with job.lock:
            round_["tests"]["full"] = compared
        job.save()
        if compared["broken"]:
            return f"Bộ test sập, không có số để so:\n{compared['tail']}"
        if not compared["ok"]:
            return "Có test mới đỏ so với trước khi sửa:\n" + "\n".join(compared["new"])
        problem = self._check_handfree(round_, baselines.get("handfree"), changes)
        if problem:
            return problem
        return self._check_regression(round_, baselines.get("regression") or {})

    def _check_handfree(self, round_: dict, before: dict | None, changes: list[codeguard.Change]) -> str | None:
        """Ca trợ lý hồ sơ mà bản sửa đụng phần trợ lý (kênh handfree, handfree/ của pipeline): bộ tests/handfree không được
        có test mới đỏ. Bộ này lỗi collect sẵn trên máy local, nên so trước/sau chứ không đòi xanh hết."""
        if not before or not codeguard.touches_handfree(changes):
            return None
        if before.get("broken"):
            self._warn("Bộ tests/handfree không chạy được từ trước khi sửa (máy thiếu thư viện?), bỏ qua bước so test trợ lý.")
            return None
        self.job.log("Chạy bộ tests/handfree để so với trước khi sửa…")
        compared = verify.compare(before, verify.handfree_tests(self.job.cancel))
        with self.job.lock:
            round_["tests"]["handfree"] = compared
        self.job.save()
        if compared["broken"]:
            return f"Bộ tests/handfree sập, không có số để so:\n{compared['tail']}"
        if not compared["ok"]:
            return "Có test trợ lý (tests/handfree) mới đỏ so với trước khi sửa:\n" + "\n".join(compared["new"])
        return None

    def _check_regression(self, round_: dict, before: dict) -> str | None:
        """Bộ ca hồi quy của các ca đã sửa trước đây: ca đang đạt mà bản sửa này làm trượt thì không được qua."""
        job = self.job
        if not verify.regression_cases():
            return None
        job.log("Phát lại bộ ca hồi quy để so với trước khi sửa…")
        compared = verify.compare_regression(before, verify.regression_run(job.cancel))
        with job.lock:
            round_["tests"]["regression"] = compared
        job.save()
        if compared["broken"]:
            return f"Trình phát lại ca hồi quy sập:\n{compared['tail']}"
        if not compared["ok"]:
            detail = "\n".join(f"- {k}: {compared['errors'].get(k, '')}" for k in compared["new"])
            return "Bản sửa làm trượt ca hồi quy của lần sửa trước (auto-test-hcc/regression/cases):\n" + detail
        return None

    def _retest(self, round_: dict, decision: dict, changes: list[codeguard.Change]) -> bool:
        job = self.job
        checks = decision["acceptance"]
        self._stage("retest", f"Chạy lại {self.settings['runs']} lần với bản sửa…")
        live: list[dict] = []
        with job.lock:
            round_["retest"] = {"runs": live, "total": self.settings["runs"], "phase": f"round{round_['n']}"}

        def on_run(run: dict) -> None:
            with job.lock:
                live.append(replay.strip_response(run))
            job.log(f"Lần {run['n']}: {run.get('status')}" + (f" · {run['error']}" if run.get("error") else ""))

        runs = self._replay(f"round{round_['n']}", on_run)
        self._check_runs(runs)
        self._check_second_pass(runs)
        evaluation = scoring.evaluate(checks, runs)
        targets = {str(c.get("field")) for c in checks}
        regressions = scoring.find_regressions(self._baseline_values(), runs, targets)
        with job.lock:
            round_["retest"].update(
                evaluation=evaluation, regressions=regressions, ocrFresh=scoring.ocr_fresh_count(runs),
            )
        job.save()
        job.log(f"Chấm: đạt {evaluation['passed']}/{evaluation['total']} lần, {len(regressions)} field hồi quy.")
        if evaluation["allPass"] and not regressions:
            self.last_runs, self.last_evaluation = runs, evaluation
            return self._accept(round_, changes)
        reason = f"Đạt {evaluation['passed']}/{evaluation['total']} lần."
        if regressions:
            reason += " Field đổi giá trị ngoài dự kiến: " + ", ".join(r["field"] for r in regressions)
        return self._round_failed(round_, decision, reason, evaluation=evaluation, regressions=regressions)

    def _accept(self, round_: dict, changes: list[codeguard.Change]) -> bool:
        job = self.job
        records = self.guard.keep_preimages(changes)
        patch = round_["fix"]["patch"]
        (job.dir / "fix.patch").write_text(patch, encoding="utf-8")
        self.touched = []
        with job.lock:
            round_["result"] = {"ok": True}
            job.data["fix"] = {"files": records, "patch": patch, "summary": round_["fix"].get("summary"), "reverted": False}
            job.data["touched"] = []
            job.data["stackDirty"] = False
        job.save()
        self._publish(round_, changes)
        self._save_regression(round_, changes)
        return True

    def _publish(self, round_: dict, changes: list[codeguard.Change]) -> None:
        """Đẩy bản sửa đạt lên nhánh riêng của ca. Lỗi git không làm hỏng kết quả, bản sửa vẫn nằm trên đĩa + fix.patch."""
        job = self.job
        if not publish.GIT_REMOTE and not (USE_WORKSPACE and publish.WORKSPACE_PUSH):
            return
        message = self._commit_message(round_)
        if USE_WORKSPACE:
            return self._publish_components(changes, message)
        try:
            result = publish.push_fix(job.data["id"], job.dir, changes, message)
        except (publish.PublishError, OSError, subprocess.TimeoutExpired) as reason:
            self._warn(f"Không đẩy được bản sửa lên GitHub: {reason}. Bản sửa vẫn nằm trong thư mục làm việc trên server.")
            return
        if not result:
            return
        with job.lock:
            job.data["fix"]["git"] = result
        job.save()
        job.log(f"Đã đẩy bản sửa lên nhánh {result['branch']} ({result['commit'][:10]}).")
        if result["drift"]:
            self._warn("File đã khác main từ trước khi sửa, commit mang cả phần khác đó: " + ", ".join(result["drift"]))

    def _publish_components(self, changes: list[codeguard.Change], message: str) -> None:
        """Mục 3: mỗi repo thật bị sửa một nhánh agent/<mã ca> dựng trên tag release, kèm link mở PR."""
        job = self.job
        pushes = publish.push_components(job.data["id"], job.dir, changes, message, job.data.get("workspace") or {})
        with job.lock:
            job.data["fix"]["pushes"] = pushes
        job.save()
        for item in pushes:
            if item.get("error"):
                self._warn(f"Không đẩy được bản sửa {item['component']} lên GitHub: {item['error']} "
                           "Bản sửa vẫn nằm trong khu làm việc và fix.patch của ca.")
            else:
                job.log(f"Đã đẩy {item['component']} lên nhánh {item['branch']} ({item['commit'][:10]}), dựng trên "
                        f"{item.get('ref')}. Mở PR: {item.get('compare') or item['remote']}")

    def _commit_message(self, round_: dict) -> str:
        job = self.job
        summary = (round_["fix"].get("summary") or "").strip()
        terms = codeguard.private_terms(self.case["fields"], job.data["requestId"])
        # leaked_terms chỉ xét dòng "+" của patch: đánh dấu từng dòng tóm tắt như dòng thêm mới.
        if not summary or codeguard.leaked_terms("\n".join(f"+{line}" for line in summary.splitlines()), terms):
            summary = f"sửa lỗi điền {self.case.get('procedure')}"
        by = (round_.get("approval") or {}).get("by") or ""
        # Không ghi mã req vào commit: mã req nối được tới hồ sơ người dân.
        return (f"agent: {summary.splitlines()[0][:150]}\n\nCa {job.data['id']} · thủ tục {self.case.get('procedure')} "
                f"· vòng {round_['n']} · chạy lại đạt {self.settings['runs']}/{self.settings['runs']} lần.\nNgười duyệt: {by}\n")

    # ---- ca hồi quy (mục 2) ----------------------------------------------------------------------------------

    def _passing_request(self) -> str | None:
        """requestId của một lượt chạy lại đạt mọi tiêu chí (lượt đó có trace OCR + LLM để phát lại)."""
        rows = self.last_evaluation.get("rows") or []
        for index, run in enumerate(self.last_runs):
            if run.get("requestId") and rows and all(row["cells"][index]["ok"] for row in rows):
                return run["requestId"]
        return None

    def _save_regression(self, round_: dict, changes: list[codeguard.Change]) -> None:
        """Ca đạt → ca hồi quy ẩn danh. Chỉ ghi khi phát lại ĐẠT trên code đã sửa; trượt trên code production = bắt được lỗi cũ.
        Lỗi ở bước này không làm hỏng kết quả của ca."""
        job = self.job
        report: dict = {"saved": False}
        try:
            report = self._build_regression(round_, changes)
        except regression_case.Skip as reason:
            report = {"saved": False, "reason": str(reason)}
        except Exception as reason:  # noqa: BLE001
            report = {"saved": False, "reason": f"{type(reason).__name__}: {str(reason)[:300]}"}
        with job.lock:
            job.data["regression"] = report
        job.save()
        if report.get("saved"):
            job.log(f"Đã lưu ca hồi quy {report['path']}" + ("" if report.get("catchesOldBug") else
                    " (phát lại trên code production cũng đạt: ca này chưa bắt được lỗi cũ)") + ". Soát rồi commit.")
        else:
            job.log(f"Không lưu ca hồi quy: {report.get('reason')}", level="warn")

    def _build_regression(self, round_: dict, changes: list[codeguard.Change]) -> dict:
        job = self.job
        if not codeguard.touches_backend(changes):
            raise regression_case.Skip("Bản sửa không đụng backend: ca hồi quy phát lại ở tầng backend nên không bắt được.")
        if replay.is_attach(self.case):
            # Bộ phát lại thay tệp bằng ảnh giả 1 trang, mà planner đính kèm chia giấy theo trang của tệp thật.
            raise regression_case.Skip("Ca đính kèm chưa có ca hồi quy: planner chia giấy theo trang của tệp thật, bộ phát lại "
                                       "chỉ có chữ OCR. Test unit fixer thêm vào pipeline là chốt chặn hồi quy.")
        if any("/thanh_tra/" in change.rel for change in changes):
            # Lớp thanh tra chạy nền với context rỗng nên lượt LLM của nó không vào trace: bộ phát lại chỉ phát được lượt đầu.
            raise regression_case.Skip("Bản sửa nằm ở lớp thanh tra (đợt 2): bộ phát lại chỉ phát lượt điền đầu, chưa phát được "
                                       "lượt soát. Test unit thanh tra fixer thêm vào là chốt chặn hồi quy.")
        request_id = self._passing_request()
        if not request_id:
            raise regression_case.Skip("Không có lượt chạy lại đạt nào có mã req để lấy trace.")
        db = evidence.test_database()
        account = db.users.find_one({"username": self.credentials.get("username")}, {"username": 1, "xa": 1, "tinh": 1}) or {}
        case = regression_case.build(
            job=job.data, case=self.case, decision=round_["decision"] or {}, run_request_id=request_id, db=db,
            account=account, options=replay.replay_options(self.case.get("options") or {}, "regression"),
        )
        draft = job.dir / "regression-case.json"
        draft.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
        fixed = verify.regression_run(threading.Event(), cases=[draft])
        result = fixed.get("results", {}).get(case["id"]) or {}
        if fixed.get("broken") or not result.get("ok"):
            raise regression_case.Skip("Phát lại ca vừa dựng trên code đã sửa không đạt "
                                       f"({result.get('error') or fixed.get('tail', '')[-200:]}), nên không lưu.")
        old = self._regression_on_production(draft, case["id"])
        target = regression_case.path_for(REGRESSION_CASES, case)
        target.parent.mkdir(parents=True, exist_ok=True)
        case["catchesOldBug"] = old is False
        target.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            shown = target.relative_to(MAIN).as_posix()
        except ValueError:
            shown = str(target)
        return {"saved": True, "path": shown, "catchesOldBug": old is False, "oldResult": old}

    def _regression_on_production(self, draft: Path, case_id: str) -> bool | None:
        """Phát lại trên đúng commit production (cây tạm từ HEAD của khu làm việc). True = đạt, False = trượt, None = không đo."""
        if not USE_WORKSPACE:
            return None
        repo = codeguard.REPO / codeguard.BE_DIR
        old = repo.parent / ".old-be"
        try:
            if old.exists():  # lần trước dừng giữa chừng
                shutil.rmtree(old, ignore_errors=True)
            workspace.git(repo, "worktree", "prune")
            workspace.git(repo, "worktree", "add", "--force", "--detach", str(old), "HEAD", timeout=600)
            result = verify.regression_run(threading.Event(), be=old, cases=[draft])
            item = result.get("results", {}).get(case_id)
            return None if result.get("broken") or item is None else bool(item["ok"])
        except (workspace.WorkspaceError, subprocess.TimeoutExpired, OSError):
            return None
        finally:
            try:
                workspace.git(repo, "worktree", "remove", "--force", str(old), timeout=300)
            except (workspace.WorkspaceError, subprocess.TimeoutExpired):
                pass

    def _round_failed(
        self, round_: dict, decision: dict, problem: str, evaluation: dict | None = None, regressions: list | None = None,
        reviewer_note: str | None = None, keep: bool = True,
    ) -> bool:
        job = self.job
        job.log(f"Vòng {round_['n']} không đạt: {problem[:300]}", level="warn")
        if keep and self.guard.taken and self.touched:
            changes, _ = self.guard.changes(self.touched, extension=False)
            if changes:
                self.kept = {"round": round_["n"], "changes": changes, "summary": (round_.get("fix") or {}).get("summary")}
        patch = (round_.get("fix") or {}).get("patch") or ""
        failed_rows = [
            {"check": r["check"], "values": [c["value"] for c in r["cells"]]}
            for r in (evaluation or {}).get("rows", []) if not all(c["ok"] for c in r["cells"])
        ]
        attempt = {
            "vong": round_["n"],
            "ke_hoach": decision.get("plan"),
            "patch": patch[:8000],
            "ly_do_that_bai": problem[:3000],
            "tieu_chi_truot": failed_rows,
            "hoi_quy": regressions or [],
        }
        if reviewer_note:
            attempt["gop_y_nguoi_duyet"] = reviewer_note[:3000]
        self.attempts.append(attempt)
        with job.lock:
            round_["result"] = {"ok": False, "reason": problem[:1500]}
        job.save()
        self._rollback()
        return False

    def _keep_last_fix(self) -> int | None:
        """Hết vòng mà chưa đạt: đặt lại code của vòng trượt gần nhất cho người xem thay vì xoá hết, ghi như một bản sửa
        để nút Hoàn tác bản sửa dùng được. Không build. Không đặt lại nếu patch lộ dữ liệu thật của hồ sơ, hoặc file đã
        bị ai đó sửa sau khi vòng đó hoàn tác. Trả số vòng đã để lại."""
        kept = self.kept
        if not kept:
            return None
        job = self.job
        changes = kept["changes"]
        patch = codeguard.make_patch(changes)
        if codeguard.leaked_terms(patch, codeguard.private_terms(self.case["fields"], job.data["requestId"])):
            self._warn(f"Không để lại code của vòng {kept['round']}: patch chứa dữ liệu thật của hồ sơ.")
            return None
        moved = [c.rel for c in changes if _read(codeguard.REPO / c.rel) != c.before]
        if moved:
            self._warn(f"Không để lại code của vòng {kept['round']}: file đã đổi sau khi hoàn tác ({', '.join(moved)}).")
            return None
        for change in changes:
            target = codeguard.REPO / change.rel
            if change.after is None:
                codeguard.remove_created(target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(change.after)
        records = self.guard.keep_preimages(changes)
        (job.dir / "fix.patch").write_text(patch, encoding="utf-8")
        with job.lock:
            job.data["fix"] = {"files": records, "patch": patch, "summary": kept["summary"], "reverted": False,
                               "unverified": True, "round": kept["round"]}
            for round_ in job.data["rounds"]:
                if round_["n"] == kept["round"] and round_.get("result"):
                    round_["result"]["kept"] = True
        job.save()
        job.log(f"Để lại code của vòng {kept['round']} ({len(records)} file) cho người xem, chưa build.", level="warn")
        return kept["round"]


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def revert_fix(job: Job) -> None:
    """Người dùng không giữ bản sửa đã đạt. File bị sửa tiếp sau đó thì giữ nguyên và báo lại."""
    guard = codeguard.Guard(job.dir)
    with job.lock:
        fix = job.data["fix"]
        fix["reverting"] = True
    job.save()
    if USE_WORKSPACE and workspace.owner() != job.data["id"]:
        # Khu làm việc đã đặt lại cho ca sau: code của ca này không còn trên máy (vẫn có trên nhánh GitHub + fix.patch).
        with job.lock:
            fix.update(reverting=False, reverted=True, revertedFiles=[], keptFiles=[], superseded=True)
        job.log("Khu làm việc đã chuyển sang ca khác nên không còn gì để hoàn tác trên máy.")
        job.save()
        return
    reverted, skipped = guard.revert(fix["files"])
    deployed = None
    if any(path.startswith(f"{codeguard.BE_DIR}/app/") for path in reverted):
        job.log("Build lại backend sau khi hoàn tác…")
        deployed = verify.deploy(threading.Event())
    with job.lock:
        fix.update(reverting=False, reverted=True, revertedFiles=reverted, keptFiles=skipped, revertDeploy=deployed)
    job.log(f"Đã hoàn tác {len(reverted)} file" + (f", giữ nguyên {len(skipped)} file đã bị sửa tiếp" if skipped else "") + ".")
    job.save()


def recover_interrupted(job: Job) -> None:
    """Dịch vụ bị tắt khi job đang chạy: hoàn tác phần sửa dở từ ảnh chụp, rồi build lại nếu stack đã nhận bản đó."""
    guard = codeguard.Guard(job.dir)
    touched = job.data.get("touched") or []
    if guard.taken and touched:
        changes, _ = guard.changes(touched)
        guard.restore(changes)
        job.log(f"Khởi động lại: đã hoàn tác {len(changes)} file sửa dở.", level="warn")
    if job.data.get("stackDirty"):
        job.log("Khởi động lại: build lại backend về code trước khi sửa…", level="warn")
        verify.deploy(threading.Event())
    guard.discard_snapshot()
    job.update(status="failed", error="Dịch vụ agent bị tắt giữa chừng.", touched=[], stackDirty=False, approval=None,
               planApproval=None)
