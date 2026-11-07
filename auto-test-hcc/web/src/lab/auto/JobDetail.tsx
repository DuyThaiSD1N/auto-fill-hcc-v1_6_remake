import { useCallback, useEffect, useMemo, useState } from "react";
import CopyButton from "../../components/CopyButton";
import Icon from "../../components/Icon";
import { ErrorNotice, PageLoading, Spinner } from "../../components/Status";
import { formatClock, formatDateTime } from "../../format";
import type { Batch } from "../engine";
import Results from "../Results";
import {
  agentApi, errorText, loadShot, toBatch,
  type Check, type Decision, type Evaluation, type FormGap, type Job, type Opinion, type Outcome, type Round, type RunBrief,
} from "./api";

const POLL_MS = 2000;

const STAGES: { key: string; label: string; visited: (job: Job) => boolean }[] = [
  { key: "collect", label: "Thu thập", visited: () => true },
  { key: "portal", label: "Mở cổng", visited: (j) => j.settings.mode === "portal" && !!j.reproduce },
  { key: "reproduce", label: "Chạy lại", visited: (j) => !!j.reproduce },
  { key: "meeting", label: "Họp", visited: (j) => j.rounds.length > 0 },
  { key: "arbiter", label: "Trọng tài", visited: (j) => j.rounds.some((r) => r.decision) },
  { key: "fix", label: "Sửa", visited: (j) => j.rounds.some((r) => r.fix) },
  { key: "test", label: "Test", visited: (j) => j.rounds.some((r) => r.tests) },
  { key: "deploy", label: "Build", visited: (j) => j.rounds.some((r) => r.deploy) },
  { key: "retest", label: "Chạy kiểm", visited: (j) => j.rounds.some((r) => r.retest) },
  { key: "report", label: "Kết luận", visited: (j) => !!j.report },
];

const CAUSES: Record<string, string> = {
  ocr: "Lỗi OCR",
  mapper: "Lỗi mapper",
  llm: "LLM trích sai",
  catalog: "Danh mục, địa giới",
  extension: "Extension hoặc cổng",
  input: "Giấy tờ thiếu thông tin",
  not_a_bug: "Không phải lỗi",
  unknown: "Chưa rõ",
};

const DECISIONS: Record<Decision["decision"], string> = {
  skip_ocr: "Bỏ qua vì OCR đọc sai",
  fix_code: "Sửa code",
  report_only: "Không sửa, chỉ báo cáo",
};

const OUTCOMES: Record<Outcome, { label: string; tone: "ok" | "warn" | "bad" | "plain" }> = {
  fixed: { label: "Đã sửa", tone: "ok" },
  skipped_ocr: { label: "Bỏ qua: lỗi OCR", tone: "warn" },
  report_only: { label: "Chỉ báo cáo", tone: "plain" },
  not_reproduced: { label: "Không tái hiện", tone: "plain" },
  need_human: { label: "Cần người xem", tone: "bad" },
};

const STANCES: Record<NonNullable<Opinion["stance"]>, string> = { agree: "Đồng ý", partly: "Đồng ý một phần", disagree: "Phản đối" };

const OPS: Record<string, string> = {
  equals: "phải bằng",
  contains: "phải chứa",
  not_contains: "không được chứa",
  empty: "phải trống",
  not_empty: "không được trống",
  regex: "khớp mẫu",
};

const STATUS_LABEL: Record<Job["status"], string> = {
  queued: "Đang xếp hàng",
  running: "Đang chạy",
  done: "Xong",
  failed: "Lỗi",
  stopped: "Đã dừng",
};

export function OutcomeTag({ outcome }: { outcome: Outcome }) {
  const item = OUTCOMES[outcome];
  return <span className={`at-tag at-tag--${item.tone}`}>{item.label}</span>;
}

export function StatusTag({ status, stage }: { status: Job["status"]; stage: string }) {
  const tone = status === "failed" ? "bad" : "plain";
  const name = STAGES.find((s) => s.key === stage)?.label;
  return <span className={`at-tag at-tag--${tone}`}>{STATUS_LABEL[status]}{status === "running" && name ? `: ${name}` : ""}</span>;
}

function StageRail({ job }: { job: Job }) {
  const live = job.status === "running";
  const stages = STAGES.filter((s) => s.key !== "portal" || job.settings.mode === "portal");
  const index = stages.findIndex((s) => s.key === job.stage);
  return (
    <ol className="at-rail" aria-label="Tiến trình">
      {stages.map((stage, i) => {
        const now = live && i === index;
        const state = now ? "now" : stage.visited(job) && (i < index || !live) ? "done" : i < index ? "skip" : "todo";
        return (
          <li key={stage.key} className={`at-rail__item is-${state}`} aria-current={now ? "step" : undefined}>
            <span className="at-rail__dot">{state === "done" ? <Icon name="check" size={11} /> : null}</span>
            {stage.label}
          </li>
        );
      })}
    </ol>
  );
}

function HumanWait({ job, onReady, busy }: { job: Job; onReady: () => void; busy: boolean }) {
  if (!job.human) return null;
  return (
    <div className="at-human" role="alert">
      <div>
        <strong>Đang chờ bạn</strong>
        <p>{job.human.message}</p>
        <p className="faint">Cửa sổ Chromium nằm trên máy đang chạy dịch vụ agent. Bot không nộp hồ sơ.</p>
      </div>
      <button className="btn btn--primary" type="button" disabled={busy} onClick={onReady}>{job.human.button}</button>
    </div>
  );
}

function Banner({ job }: { job: Job }) {
  if (job.report) {
    const tone = OUTCOMES[job.report.outcome].tone;
    return (
      <div className={`at-banner at-banner--${tone}`}>
        <strong>{job.report.headline}</strong>
        <p>{job.report.reason}</p>
      </div>
    );
  }
  if (job.status === "failed") {
    return <div className="at-banner at-banner--bad"><strong>Job dừng vì lỗi</strong><p>{job.error}</p></div>;
  }
  if (job.status === "stopped") {
    return <div className="at-banner at-banner--plain"><strong>Đã dừng</strong><p>Mọi thay đổi của job này đã được hoàn tác.</p></div>;
  }
  return null;
}

function OpinionCard({ item }: { item: Opinion }) {
  if (item.error) {
    return (
      <article className="at-card">
        <header className="at-card__head"><strong>{item.label}</strong><span className="at-tag at-tag--bad">Không trả lời được</span></header>
        <p className="faint">{item.error}</p>
      </article>
    );
  }
  return (
    <article className="at-card">
      <header className="at-card__head">
        <strong>{item.label}</strong>
        <span className="at-tag at-tag--plain">{CAUSES[item.cause ?? "unknown"] ?? item.cause}</span>
        {item.stance ? <span className={`at-tag at-tag--${item.stance === "agree" ? "ok" : item.stance === "disagree" ? "bad" : "warn"}`}>{STANCES[item.stance]}</span> : null}
        <span className="faint num at-card__conf">{item.confidence}%</span>
      </header>
      <p>{item.summary}</p>
      {item.rebuttal ? <p className="at-rebuttal">{item.rebuttal}</p> : null}
      {item.evidence?.length ? (
        <details className="at-more">
          <summary>Bằng chứng ({item.evidence.length})</summary>
          <ul>{item.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
          {item.codeRefs?.length ? <p className="mono at-refs">{item.codeRefs.join("  ")}</p> : null}
        </details>
      ) : null}
      {item.proposal ? <p className="muted at-proposal"><b>Đề xuất:</b> {item.proposal}</p> : null}
    </article>
  );
}

function Gaps({ gaps }: { gaps?: FormGap[] }) {
  if (!gaps?.length) return null;
  return (
    <div className="at-regress">
      <b className="ef-red">Backend có giá trị nhưng form không nhận</b>
      <ul>
        {gaps.map((g) => (
          <li key={g.field}>
            <span className="mono">{g.field}</span>: {g.be}
            <span className="faint"> ({g.notFound ? `không thấy ô ${g.notFound} lần` : `ô trống ${g.empty} lần`})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Shots({ job, phase, runs }: { job: Job; phase: string; runs: RunBrief[] }) {
  const [open, setOpen] = useState<number | null>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const list = runs.filter((r) => r.screenshot);

  useEffect(() => {
    if (open === null) return;
    let alive = true;
    let made = "";
    setError("");
    loadShot(job.id, phase, open)
      .then((u) => { made = u; if (alive) setUrl(u); else URL.revokeObjectURL(u); })
      .catch((reason) => { if (alive) setError(errorText(reason)); });
    return () => { alive = false; if (made) URL.revokeObjectURL(made); setUrl(""); };
  }, [job.id, phase, open]);

  if (!list.length) return null;
  return (
    <div className="at-shots">
      <span className="muted">Ảnh cổng sau khi điền:</span>
      {list.map((r) => (
        <button key={r.n} type="button" className="btn btn--sm" aria-pressed={open === r.n} onClick={() => setOpen(open === r.n ? null : r.n)}>Lần {r.n}</button>
      ))}
      {error ? <p className="form-error">{error}</p> : null}
      {open !== null && url ? <img className="at-shot" src={url} alt={`Cổng sau khi điền lần ${open}`} /> : null}
    </div>
  );
}

function checkText(check: Check): string {
  const needsValue = !["empty", "not_empty"].includes(check.op);
  return `${OPS[check.op] ?? check.op}${needsValue ? ` "${check.expected}"` : ""}`;
}

function CheckMatrix({ evaluation, caption }: { evaluation: Evaluation; caption: string }) {
  const count = evaluation.total;
  return (
    <div className="table-wrap">
      <table className="mini-table at-matrix">
        <caption>{caption}: <b className={evaluation.allPass ? "lab-ok" : "ef-red"}>đạt {evaluation.passed}/{count} lần</b></caption>
        <thead>
          <tr>
            <th>Tiêu chí</th>
            {Array.from({ length: count }, (_, i) => <th key={i}>Lần {i + 1}</th>)}
          </tr>
        </thead>
        <tbody>
          {evaluation.rows.map((row, r) => (
            <tr key={r}>
              <td><span className="mono">{row.check.field}</span> <small className="faint">{checkText(row.check)}</small></td>
              {row.cells.map((cell, c) => (
                <td key={c} className={cell.ok ? "at-pass" : "at-fail"}>
                  {cell.value === null ? "lượt lỗi" : cell.value === "" ? <span className="faint">(trống)</span> : cell.value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DecisionCard({ decision }: { decision: Decision }) {
  return (
    <article className="at-card at-card--arbiter">
      <header className="at-card__head">
        <strong>Trọng tài</strong>
        <span className="at-tag at-tag--plain">{CAUSES[decision.cause] ?? decision.cause}</span>
        <span className={`at-tag at-tag--${decision.decision === "fix_code" ? "ok" : decision.decision === "skip_ocr" ? "warn" : "plain"}`}>{DECISIONS[decision.decision]}</span>
      </header>
      <p>{decision.reason}</p>
      {decision.dissent ? <p className="muted"><b>Ý kiến bị bác:</b> {decision.dissent}</p> : null}
      {decision.plan ? (
        <div className="at-plan">
          <b>Kế hoạch sửa:</b> {decision.plan.summary}
          <ol>{decision.plan.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
          {decision.plan.files.length ? <p className="mono at-refs">{decision.plan.files.join("  ")}</p> : null}
          {decision.plan.test ? <p className="muted"><b>Test:</b> {decision.plan.test}</p> : null}
        </div>
      ) : null}
      {decision.risk ? <p className="muted"><b>Rủi ro:</b> {decision.risk}</p> : null}
    </article>
  );
}

function Patch({ patch }: { patch: string }) {
  return (
    <details className="at-more" open>
      <summary>Patch</summary>
      <div className="at-patch__bar"><CopyButton text={patch} label="Chép patch" /></div>
      <pre className="at-patch">
        {patch.split("\n").map((line, i) => (
          <span key={i} className={line.startsWith("+") ? "is-add" : line.startsWith("-") ? "is-del" : line.startsWith("@@") ? "is-hunk" : undefined}>{line}{"\n"}</span>
        ))}
      </pre>
    </details>
  );
}

function RunDots({ runs, total }: { runs: RunBrief[]; total: number }) {
  return (
    <span className="at-dots" aria-label={`${runs.length}/${total} lần xong`}>
      {Array.from({ length: total }, (_, i) => {
        const run = runs.find((r) => r.n === i + 1);
        return <i key={i} className={run ? (run.status === "error" ? "is-bad" : "is-ok") : ""} title={run?.error ?? `Lần ${i + 1}`} />;
      })}
    </span>
  );
}

function Checks({ round }: { round: Round }) {
  const { tests, deploy } = round;
  const full = tests?.full;
  const extension = tests?.extension;
  if (!tests && !deploy) return null;
  return (
    <ul className="at-checks">
      {extension ? (
        <li className={extension.ok ? "" : "is-bad"}>
          <b>Test extension</b> {extension.failed}/{extension.total} file đỏ
          <span className="faint"> (trước khi sửa: {extension.failedBefore} đỏ)</span>
          {extension.new.length ? <ul>{extension.new.map((t) => <li key={t} className="mono">{t}</li>)}</ul> : <span className="faint"> · không có file mới đỏ</span>}
        </li>
      ) : null}
      {tests?.pipeline ? (
        <li className={tests.pipeline.ok || tests.pipeline.skipped ? "" : "is-bad"}>
          <b>Test pipeline</b> {tests.pipeline.summary}
          {tests.pipeline.files?.length ? <span className="mono faint"> {tests.pipeline.files.join(" ")}</span> : null}
        </li>
      ) : null}
      {full ? (
        <li className={full.ok ? "" : "is-bad"}>
          <b>Toàn bộ test</b> {full.after.failed} failed, {full.after.passed} passed, {full.after.errors} errors
          <span className="faint"> (trước khi sửa: {full.before.failed} failed, {full.before.passed} passed)</span>
          {full.new.length ? <ul>{full.new.map((t) => <li key={t} className="mono">{t}</li>)}</ul> : <span className="faint"> · không có test mới đỏ</span>}
        </li>
      ) : null}
      {deploy ? (
        <li className={deploy.ok ? "" : "is-bad"}>
          <b>Docker</b> {deploy.ok ? (deploy.ps || "đã Up") : `lỗi ở bước ${deploy.step}`}
          {deploy.health ? <span className="mono faint"> {deploy.health}</span> : null}
        </li>
      ) : null}
    </ul>
  );
}

function RoundView({ job, round, single }: { job: Job; round: Round; single: boolean }) {
  const retest = round.retest;
  return (
    <section className="at-round" aria-label={`Vòng ${round.n}`}>
      {single ? null : <h2 className="at-round__title">Vòng {round.n}</h2>}
      {round.opinions.length ? (
        <div>
          <h3 className="section-title">Ý kiến độc lập</h3>
          <div className="at-cards">{round.opinions.map((o) => <OpinionCard key={o.role} item={o} />)}</div>
        </div>
      ) : null}
      {round.debate?.skipped ? <p className="faint">{round.debate.reason}</p> : null}
      {round.reviews.length ? (
        <div>
          <h3 className="section-title">Phản biện</h3>
          <div className="at-cards">{round.reviews.map((o) => <OpinionCard key={o.role} item={o} />)}</div>
        </div>
      ) : null}
      {round.decision ? <DecisionCard decision={round.decision} /> : null}
      {round.precheck ? <CheckMatrix evaluation={round.precheck} caption="Tiêu chí trên code trước khi sửa" /> : null}
      {round.fix ? (
        <article className="at-card">
          <header className="at-card__head">
            <strong>Sửa code</strong>
            {round.fix.repairs ? <span className="at-tag at-tag--warn">Vá lại {round.fix.repairs} lần</span> : null}
          </header>
          <p>{round.fix.summary}</p>
          {round.fix.notes ? <p className="muted">{round.fix.notes}</p> : null}
          {round.fix.patch ? <Patch patch={round.fix.patch} /> : null}
        </article>
      ) : null}
      <Checks round={round} />
      {retest ? (
        <div className="at-retest">
          <h3 className="section-title">Chạy lại với bản sửa <RunDots runs={retest.runs} total={retest.total} /></h3>
          {retest.evaluation ? <CheckMatrix evaluation={retest.evaluation} caption="Tiêu chí sau khi sửa" /> : null}
          <Gaps gaps={retest.formGaps} />
          {retest.phase ? <Shots job={job} phase={retest.phase} runs={retest.runs} /> : null}
          {retest.regressions?.length ? (
            <div className="at-regress">
              <b className="ef-red">Field đổi giá trị ngoài dự kiến</b>
              <ul>
                {retest.regressions.map((r) => (
                  <li key={r.field}><span className="mono">{r.field}</span>: {r.before.join(" / ") || "(trống)"} → {r.after.join(" / ") || "(trống)"}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      {round.result && !round.result.ok ? (
        <p className="at-failed"><b>Vòng này không đạt, đã hoàn tác.</b> {round.result.reason}</p>
      ) : null}
    </section>
  );
}

function FieldsTab({ job }: { job: Job }) {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    agentApi.runs(job.id).then((data) => setBatch(data.phases.length ? toBatch(job, data.phases) : null)).catch((reason) => setError(errorText(reason)));
    // job đổi mỗi 2 giây khi đang chạy; chỉ tải lại khi có lượt mới.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id, job.rounds.length, job.reproduce?.runs.length, job.status]);
  useEffect(load, [load]);
  if (error) return <ErrorNotice message={error} onRetry={load} />;
  if (!batch) return <p className="faint">Chưa có lần chạy lại nào xong.</p>;
  return <Results key={batch.id} batch={batch} />;
}

function LogTab({ job }: { job: Job }) {
  return (
    <ol className="at-log">
      {[...job.events].reverse().map((event, i) => (
        <li key={i} className={`is-${event.level}`}>
          <time className="num faint">{formatClock(event.t)}</time>
          {event.who ? <b>{event.who}</b> : null}
          <span>{event.text}</span>
        </li>
      ))}
    </ol>
  );
}

type Tab = "flow" | "fields" | "log";

export default function JobDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("flow");
  const [acting, setActing] = useState(false);

  const refresh = useCallback(() => {
    agentApi.get(id).then((data) => { setJob(data); setError(""); }).catch((reason) => setError(errorText(reason)));
  }, [id]);

  useEffect(refresh, [refresh]);

  const live = !job || job.status === "queued" || job.status === "running" || !!job.fix?.reverting;
  useEffect(() => {
    if (!live) return;
    const timer = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(timer);
  }, [live, refresh]);

  const lastEvent = useMemo(() => job?.events[job.events.length - 1], [job]);

  async function act(run: () => Promise<Job>) {
    setActing(true);
    try {
      setJob(await run());
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setActing(false);
    }
  }

  if (!job) return error ? <ErrorNotice message={error} onRetry={refresh} /> : <PageLoading label="Đang tải job…" />;

  const running = job.status === "queued" || job.status === "running";
  const account = job.case.account;
  const tabs: { key: Tab; label: string }[] = [
    { key: "flow", label: "Diễn biến" },
    { key: "fields", label: "Kết quả điền" },
    { key: "log", label: "Nhật ký" },
  ];

  return (
    <div className="at-job">
      <div className="page-head">
        <button className="btn btn--sm" type="button" onClick={onBack}><Icon name="arrow-left" size={14} /> Trở lại</button>
        <h1>{job.case.label ?? job.requestId}</h1>
        <span className="mono faint">{job.requestId}</span>
        <CopyButton text={job.requestId} label="Chép mã" />
        <div className="page-head__actions">
          {running ? (
            <button className="btn btn--sm" type="button" disabled={acting} onClick={() => void act(() => agentApi.stop(job.id))}>
              <Icon name="x" size={14} /> Dừng và hoàn tác
            </button>
          ) : null}
          {job.fix && !job.fix.reverted ? (
            <button
              className="btn btn--sm"
              type="button"
              disabled={acting || !!job.fix.reverting}
              onClick={() => { if (window.confirm("Hoàn tác bản sửa này và build lại backend?")) void act(() => agentApi.revert(job.id)); }}
            >
              {job.fix.reverting ? <Spinner label="Đang hoàn tác" /> : <><Icon name="refresh" size={14} /> Hoàn tác bản sửa</>}
            </button>
          ) : null}
        </div>
      </div>

      <div className="at-meta faint">
        {account ? <span>{account.username}{account.xa ? ` · ${account.xa}` : ""}{account.tinh ? `, ${account.tinh}` : ""}</span> : null}
        <span>Chạy lại bằng {job.settings.replayAccount}</span>
        <span>Bắt đầu {formatDateTime(job.createdAt)}</span>
        <span className="num">{job.cost.calls} lượt agent · ${job.cost.usd.toFixed(2)}</span>
      </div>

      <blockquote className="at-quote">{job.description}</blockquote>
      <StageRail job={job} />
      {running ? (
        <p className="at-live" aria-live="polite">
          <Spinner label={job.status === "queued" ? "Đang chờ ca trước chạy xong" : lastEvent ? `${lastEvent.who ? `${lastEvent.who}: ` : ""}${lastEvent.text}` : "Đang chạy"} />
        </p>
      ) : null}
      {/* Dịch vụ gỡ trạng thái chờ ở nhịp sau: ẩn ngay kẻo người dùng bấm lần nữa khi tưởng chưa nhận. */}
      <HumanWait job={job} busy={acting} onReady={() => void act(async () => ({ ...(await agentApi.ready(job.id)), human: null }))} />
      <Banner job={job} />
      {job.fix?.reverted ? (
        <div className="at-banner at-banner--plain">
          <strong>Bản sửa đã được hoàn tác</strong>
          {job.fix.keptFiles?.length ? <p>Giữ nguyên vì đã bị sửa tiếp sau đó: {job.fix.keptFiles.join(", ")}</p> : null}
        </div>
      ) : null}
      {job.fix && !job.fix.reverted && !job.fix.reverting ? (
        <p className="muted at-note">Bản sửa đang nằm trong thư mục làm việc và chưa commit: {job.fix.files.map((f) => f.path).join(", ")}. Hãy xem lại rồi tự commit.</p>
      ) : null}
      {job.warnings.map((w) => <p key={w} className="at-warn"><Icon name="alert" size={14} /> {w}</p>)}
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <div className="tabs" role="tablist" aria-label="Chi tiết job">
        {tabs.map((t) => <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>{t.label}</button>)}
      </div>
      {tab === "flow" ? (
        <div className="at-flow">
          {job.reproduce ? (
            <p className="muted">
              Chạy lại với code hiện tại <RunDots runs={job.reproduce.runs} total={job.reproduce.total} />
              {typeof job.reproduce.ocrFresh === "number" ? <span className="faint"> {job.reproduce.ocrFresh}/{job.reproduce.total} lần xác nhận OCR mới</span> : null}
              {job.reproduce.coverage ? <span className={job.reproduce.faithful === false ? "ef-red" : "faint"}> · ra {job.reproduce.coverage.matched}/{job.reproduce.coverage.original} field của lượt gốc</span> : null}
            </p>
          ) : null}
          {job.reproduce ? <Gaps gaps={job.reproduce.formGaps} /> : null}
          {job.reproduce ? <Shots job={job} phase="reproduce" runs={job.reproduce.runs} /> : null}
          {job.rounds.map((round) => <RoundView key={round.n} job={job} round={round} single={job.rounds.length === 1} />)}
        </div>
      ) : null}
      {tab === "fields" ? <FieldsTab job={job} /> : null}
      {tab === "log" ? <LogTab job={job} /> : null}
    </div>
  );
}
