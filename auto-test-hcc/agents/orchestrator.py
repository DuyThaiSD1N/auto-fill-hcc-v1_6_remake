"""Máy trạng thái của một job: thu thập → chạy lại → họp → trọng tài → sửa → test → NGƯỜI DUYỆT → build → chạy lại → kết luận.

Phân vai: agent phân tích và viết code; mọi việc quyết định kết quả (chạy test, build, chấm 5 lần, hoàn tác) do mã
ở đây làm. Trọng tài chỉ đề ra tiêu chí, đạt hay không là do scoring.py chấm trên output thật của backend.
Code agent viết chỉ được build lên Docker và nạp vào extension sau khi người vận hành đọc patch và bấm đồng ý
(_await_approval). Không có cờ bỏ qua bước duyệt.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import browser
import claude_runner
import codeguard
import evidence
import replay
import roles
import scoring
import verify
from claude_runner import AgentError, AgentResult
from config import AGENT_TIMEOUT_S, APPROVAL_TIMEOUT_S, FIXER_TIMEOUT_S, JOB_BUDGET_USD, MAX_REPAIRS, RUNS
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
    # Job "Thêm thủ tục mới" (devjob.py)
    "built": "Đã làm xong thủ tục: test, build và chạy thử file mẫu đều đạt",
    "dev_failed": "Chưa làm xong thủ tục, mọi thay đổi đã hoàn tác",
}


class JobError(Exception):
    pass


class NotApproved(Exception):
    """Người duyệt bấm dừng hoặc quá giờ không ai duyệt: hoàn tác rồi kết thúc job, không sang vòng sau."""


# Quyết định của người duyệt (POST /agent-api/jobs/{id}/approval).
APPROVE, RETRY, REJECT = "approve", "retry", "reject"
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
        self.ready = threading.Event()  # người dùng bấm "Đã tới tờ khai" trên web
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
            "human": None,
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
                "kind": data.get("kind", "fix"),
                "requestId": data["requestId"],
                "label": case.get("label"),
                "description": data["description"],
                "status": data["status"],
                "stage": data["stage"],
                "outcome": data["outcome"],
                "createdAt": data["createdAt"],
                "rounds": len(data["rounds"]) or len(data.get("attempts") or []),
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
        self.portal_state: dict = {}
        self.budget = JOB_BUDGET_USD

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
            self.guard.discard_snapshot()
            job.save()

    def _run(self) -> None:
        self._collect()
        self._reproduce()
        for number in range(1, self.settings["maxRounds"] + 1):
            round_ = self._new_round(number)
            self._meeting(round_)
            decision = self._arbiter(round_)
            kind = decision.get("decision")
            if kind == "skip_ocr":
                return self._finish("skipped_ocr", decision.get("reason", ""))
            if kind == "report_only":
                return self._finish("report_only", decision.get("reason", ""))
            problem = self._decision_problem(decision)
            if problem:
                self._round_failed(round_, decision, problem)
                continue
            precheck = scoring.evaluate(decision["acceptance"], self._precheck_runs())
            with self.job.lock:
                round_["precheck"] = precheck
            if precheck["allPass"]:
                return self._finish(
                    "not_reproduced",
                    f"Tiêu chí của trọng tài đã đạt {precheck['passed']}/{precheck['total']} lần với code hiện tại, nên không sửa gì. "
                    "Lỗi có thể đã được sửa từ sau lượt gốc, hoặc chỉ thỉnh thoảng mới xảy ra.",
                )
            try:
                if self._attempt(round_, decision):
                    return self._finish("fixed", decision.get("reason", ""))
            except NotApproved as reason:
                return self._finish("not_approved", str(reason))
        self._finish("need_human", "Đã thử hết số vòng cho phép mà chưa đạt. Mọi thay đổi đã được hoàn tác, xem lý do từng vòng ở trên.")

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
        changes, _ = self.guard.changes(self.touched, self.on_portal)
        self.guard.restore(changes)
        if changes:
            self.job.log(f"Đã hoàn tác {len(changes)} file: {', '.join(c.rel for c in changes)}")
        if codeguard.touches_extension(changes):
            self.portal_state["extensionStale"] = True
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

    # ---- thu thập + chạy lại trước khi sửa -----------------------------------------------------------------

    def _collect(self) -> None:
        self._stage("collect", "Thu thập chứng cứ của req…")
        self.case = evidence.collect(self.job.data["requestId"], self.job.dir / "case")
        applicant = self.settings.get("applicant")
        if applicant:
            options = self.case["options"]
            options["formContext"] = {**(options.get("formContext") or {}), **applicant}
        public = {k: v for k, v in self.case.items() if k not in ("options", "storedFiles", "fields", "caseDir")}
        self.job.update(case=public)
        self.job.log(f"Thủ tục {self.case.get('label')}, {len(self.case['storedFiles'])} tệp, {len(self.case['fields'])} field ở lượt gốc.")

    @property
    def on_portal(self) -> bool:
        return self.settings.get("mode") == "portal"

    def _wait_human(self, message: str, button: str = "Đã tới tờ khai, chạy tiếp", done: Callable[[], bool] | None = None) -> None:
        """Chờ người dùng làm trên cửa sổ bot. Có ``done`` thì tự đi tiếp khi điều kiện đúng, nút trên web chỉ là đường dự phòng."""
        job = self.job
        job.ready.clear()
        job.update(human={"message": message, "button": button, "since": now()})
        job.log(f"Chờ bạn: {message}", level="warn")
        deadline = time.monotonic() + browser.HUMAN_TIMEOUT_S
        try:
            while not job.ready.wait(3):
                if job.cancel.is_set():
                    raise Stopped()
                if done and done():
                    return
                if time.monotonic() > deadline:
                    raise JobError(f"Quá {browser.HUMAN_TIMEOUT_S // 60} phút không thấy bấm tiếp.")
        finally:
            job.update(human=None)

    def _open_portal(self) -> None:
        """Người dùng chỉ đăng nhập, mọi việc còn lại bot làm. Bot kẹt thì nhờ người bấm hộ đoạn đó rồi chạy tiếp."""
        job = self.job
        self._stage("portal", "Mở trang chủ Cổng DVC quốc gia…")
        browser.open_home(self.portal_state, job.cancel, job.log)
        self._wait_human(
            "Trên cửa sổ Chromium của bot, bấm Đăng nhập và hoàn tất VNeID. Xong bot tự vào thủ tục và tự điền.",
            button="Tôi đã đăng nhập xong",
            done=lambda: browser.is_logged_in(self.portal_state, job.cancel, job.log),
        )
        job.log("Đã đăng nhập, bot tự vào thủ tục…")
        try:
            browser.enter_form(self.case["procedure"], self.credentials, self.portal_state, job.cancel, job.log)
        except (RuntimeError, browser.Error) as reason:
            self._wait_human(f"Bot chưa tự vào được tờ khai: {str(reason)[:200]} Hãy bấm tới tờ khai giúp rồi bấm nút bên dưới.")

    def _replay(self, phase: str, on_run: Callable[[dict], None]) -> list[dict]:
        if self.on_portal:
            runs = browser.replay_on_portal(
                self.case, self.settings["runs"], phase, self.job.dir, self.credentials, self.portal_state,
                self.job.cancel, self._wait_human, on_run, self.job.log,
            )
        else:
            runs = replay.replay(self.case, self.settings["runs"], phase, self.job.dir, self.credentials, self.job.cancel, on_run)
        if self.job.cancel.is_set():
            raise Stopped()
        return runs

    def _reproduce(self) -> None:
        table = scoring.field_table(self.case["fields"], [])
        if self.on_portal:
            self._open_portal()
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
            table = scoring.field_table(self.case["fields"], self.pre_runs)
            fresh = scoring.ocr_fresh_count(self.pre_runs)
            self._check_runs(self.pre_runs)
            coverage = scoring.replay_coverage(self.case["fields"], self.pre_runs)
            faithful = coverage["ratio"] >= _FAITHFUL_RATIO
            if not faithful:
                self._warn(
                    f"Chạy lại chỉ ra {coverage['matched']}/{coverage['original']} field có giá trị của lượt gốc, nên kết quả chạy lại "
                    "không đại diện cho lượt gốc. Thường do thiếu ngữ cảnh, ví dụ mốc người nộp của lượt trợ lý."
                )
            with self.job.lock:
                self.job.data["reproduce"].update(
                    table=table, ocrFresh=fresh, coverage=coverage, faithful=faithful,
                    formGaps=scoring.form_gaps(self.pre_runs), phase="reproduce",
                )
            self.job.save()
        (self.job.dir / "case" / "reproduce.json").write_text(
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
        if not self.on_portal:
            return
        unread = [r["n"] for r in done if r.get("form") is None]
        if unread:
            self._warn(f"Lần {unread} không đọc lại được form, các lần đó được chấm trên giá trị backend trả.")
        other = {r["wrongProcedure"] for r in runs if r.get("wrongProcedure")}
        if other:
            self._warn(f"Panel nhận diện sang thủ tục khác ({', '.join(other)}), kết quả không so được với req. Kiểm tra lại trang đang mở.")

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

    def _agent(
        self, who: str, kind: str, system: str, prompt: str, schema: dict, *,
        can_edit: bool = False, resume: str | None = None, timeout: int | None = None, **extra,
    ) -> AgentResult:
        """``extra`` chuyển thẳng cho claude_runner (write, edit_troly, budget) — job thêm thủ tục cần quyền rộng hơn."""
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
                    timeout=timeout or (FIXER_TIMEOUT_S if can_edit else AGENT_TIMEOUT_S),
                    cancel=self.job.cancel, on_event=on_event, can_edit=can_edit, resume=resume,
                    # Chỉ gọi backend thì extension không chạy, sửa extension là không kiểm chứng được.
                    edit_extension=can_edit and self.on_portal,
                    touched=self.touched if can_edit else None,
                    **extra,
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
        if spent > self.budget:
            raise JobError(f"Job đã tiêu {spent:.2f} USD, vượt trần {self.budget:.0f} USD")
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
        for role, spec in roles.ANALYSTS.items():
            system, prompt = roles.analyst_prompt(role, brief)
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
            system, _ = roles.analyst_prompt(opinion["role"], brief)
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

    def _arbiter(self, round_: dict) -> dict:
        self._stage("arbiter", "Trọng tài xem xét và ra quyết định…")
        brief = roles.case_brief(self.job.data, self.case, self.attempts)
        opinions = [self._public_opinion(o) for o in round_["opinions"] if not o.get("error")]
        reviews = [self._public_opinion(o) for o in round_["reviews"] if not o.get("error")]
        result = self._agent("Trọng tài", "arbiter", roles.ARBITER_SYSTEM, roles.arbiter_prompt(brief, opinions, reviews), roles.DECISION_SCHEMA)
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
        self._stage("fix", "Đo baseline test trước khi sửa…")
        before = {"backend": verify.baseline(job.cancel)}
        if before["backend"].get("broken"):
            raise JobError("Bộ test đang hỏng từ trước khi sửa, không có mốc để so: " + before["backend"].get("tail", "")[-300:])
        if self.on_portal:
            before["extension"] = verify.extension_baseline(job.cancel)
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

        changes, _ = self.guard.changes(self.touched, self.on_portal)
        verdict = self._await_approval(round_, changes)
        if verdict["decision"] != APPROVE:
            note = verdict.get("note") or ""
            if verdict.get("timeout"):
                problem = note
            else:
                problem = "Người duyệt không đồng ý bản sửa" + (f": {note}" if note else ".")
            self._round_failed(round_, decision, problem, reviewer_note=note if verdict["decision"] == RETRY else None)
            if verdict["decision"] == RETRY:
                return False
            raise NotApproved(problem + " Code đã trả về như trước khi sửa.")
        changes = self._changes_after_approval(round_)
        if codeguard.touches_extension(changes):
            self.portal_state["extensionStale"] = True  # lượt chạy kiểm sau đây nạp lại trước khi điền
        # stackDirty: vòng trước đã build bản sửa nay bị hoàn tác, nên dù vòng này chỉ đổi test vẫn phải build lại.
        if codeguard.touches_backend_app(changes) or job.data.get("stackDirty"):
            self._stage("deploy", "Build lại backend bằng compose.prod.yml…")
            job.update(stackDirty=True)
            deployed = verify.deploy(job.cancel)
            with job.lock:
                round_["deploy"] = deployed
            job.save()
            if not deployed["ok"]:
                return self._round_failed(round_, decision, f"Build hoặc healthz lỗi ở bước {deployed.get('step')}: {deployed.get('output', deployed.get('health', ''))[-500:]}")
        return self._retest(round_, decision, changes)

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
        changes, _ = self.guard.changes(self.touched, self.on_portal)
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
        changes, outside = self.guard.changes(self.touched, self.on_portal)
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
            return self._check_backend(round_, output, before["backend"], changes)
        return None

    def _check_backend(self, round_: dict, output: dict, before: dict, changes: list[codeguard.Change]) -> str | None:
        job = self.job
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
        evaluation = scoring.evaluate(checks, runs)
        targets = {str(c.get("field")) for c in checks}
        regressions = scoring.find_regressions(self._baseline_values(), runs, targets)
        with job.lock:
            round_["retest"].update(
                evaluation=evaluation, regressions=regressions, ocrFresh=scoring.ocr_fresh_count(runs), formGaps=scoring.form_gaps(runs),
            )
        job.save()
        job.log(f"Chấm: đạt {evaluation['passed']}/{evaluation['total']} lần, {len(regressions)} field hồi quy.")
        if evaluation["allPass"] and not regressions:
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
        return True

    def _round_failed(
        self, round_: dict, decision: dict, problem: str, evaluation: dict | None = None, regressions: list | None = None,
        reviewer_note: str | None = None,
    ) -> bool:
        job = self.job
        job.log(f"Vòng {round_['n']} không đạt: {problem[:300]}", level="warn")
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


def revert_fix(job: Job) -> None:
    """Người dùng không giữ bản sửa đã đạt. File bị sửa tiếp sau đó thì giữ nguyên và báo lại."""
    guard = codeguard.Guard(job.dir)
    with job.lock:
        fix = job.data["fix"]
        fix["reverting"] = True
    job.save()
    reverted, skipped = guard.revert(fix["files"])
    deployed = None
    if any(path.startswith(f"{codeguard.BE_DIR}/app/") for path in reverted):
        job.log("Build lại backend sau khi hoàn tác…")
        deployed = verify.deploy(threading.Event())
    if any(path.startswith(f"{codeguard.EXT_DIR}/") for path in reverted):
        browser.reload_if_open(job.log)
    with job.lock:
        fix.update(reverting=False, reverted=True, revertedFiles=reverted, keptFiles=skipped, revertDeploy=deployed)
    job.log(f"Đã hoàn tác {len(reverted)} file" + (f", giữ nguyên {len(skipped)} file đã bị sửa tiếp" if skipped else "") + ".")
    job.save()


def recover_interrupted(job: Job) -> None:
    """Dịch vụ bị tắt khi job đang chạy: hoàn tác phần sửa dở từ ảnh chụp, rồi build lại nếu stack đã nhận bản đó."""
    guard = codeguard.Guard(job.dir, troly=job.data.get("kind") == "dev" and bool(job.data["settings"].get("troLy")))
    touched = job.data.get("touched") or []
    if guard.taken and touched:
        changes, _ = guard.changes(touched)
        guard.restore(changes)
        job.log(f"Khởi động lại: đã hoàn tác {len(changes)} file sửa dở.", level="warn")
    if job.data.get("stackDirty"):
        job.log("Khởi động lại: build lại backend về code trước khi sửa…", level="warn")
        verify.deploy(threading.Event())
    guard.discard_snapshot()
    job.update(status="failed", error="Dịch vụ agent bị tắt giữa chừng.", touched=[], stackDirty=False, approval=None)
