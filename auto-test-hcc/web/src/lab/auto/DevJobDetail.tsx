import { useCallback, useEffect, useMemo, useState } from "react";
import CopyButton from "../../components/CopyButton";
import Icon from "../../components/Icon";
import { ErrorNotice, PageLoading, Spinner } from "../../components/Status";
import { formatDateTime } from "../../format";
import { agentApi, devApi, errorText, loadInput, type DevAttempt, type DevInput, type DevJob, type InputGroup } from "./api";
import { Checks, DEV_STAGES, LogTab, OUTCOMES, Patch } from "./JobDetail";

const POLL_MS = 2000;
const GROUP_TITLES: Record<InputGroup, string> = { mapping: "Excel mapping điền", attach: "Ảnh ánh xạ đính kèm", samples: "File mẫu" };

function Rail({ job }: { job: DevJob }) {
  const live = job.status === "running" || job.status === "queued";
  const index = DEV_STAGES.findIndex((s) => s.key === job.stage);
  return (
    <ol className="at-rail" aria-label="Tiến trình">
      {DEV_STAGES.map((stage, i) => {
        const now = live && i === index;
        const state = now ? "now" : i < index || (!live && i <= index) ? "done" : "todo";
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

function Smoke({ attempt, onTestPortal }: { attempt: DevAttempt; onTestPortal?: (requestId: string) => void }) {
  const smoke = attempt.smoke;
  if (!smoke) return null;
  const bad = smoke.status === "error" || !smoke.filled;
  return (
    <div className={`dv-smoke${bad ? " is-bad" : ""}`}>
      <div className="dv-smoke__head">
        <b>Chạy thử trên file mẫu</b>
        <span className={`at-tag at-tag--${bad ? "bad" : smoke.status === "partial" ? "warn" : "ok"}`}>
          {smoke.status === "error" ? "Lỗi" : `${smoke.filled}/${smoke.total} ô có giá trị`}
        </span>
        {typeof smoke.ms === "number" ? <span className="faint num">{(smoke.ms / 1000).toFixed(1)} giây</span> : null}
        {smoke.requestId ? (
          <>
            <span className="mono faint">{smoke.requestId}</span>
            <CopyButton text={smoke.requestId} label="Chép mã req" />
            {onTestPortal && !bad ? (
              <button type="button" className="btn btn--sm btn--primary" onClick={() => onTestPortal(smoke.requestId!)}>
                Kiểm thử trên cổng thật
              </button>
            ) : null}
          </>
        ) : null}
      </div>
      {smoke.error ? <p className="form-error">{smoke.error}</p> : null}
      {smoke.errors.length ? (
        <ul className="dv-smoke__errors">{smoke.errors.map((e, i) => <li key={i}>{typeof e === "string" ? e : JSON.stringify(e)}</li>)}</ul>
      ) : null}
      {smoke.fields.length ? (
        <details className="at-more">
          <summary>Các ô backend trả ({smoke.fields.length})</summary>
          <div className="table-wrap">
            <table className="mini-table">
              <tbody>
                {smoke.fields.map((f, i) => (
                  <tr key={`${f.name}-${i}`}><td className="mono">{f.name}</td><td>{f.value}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </div>
  );
}

function AttemptView({ attempt, last, onTestPortal }: { attempt: DevAttempt; last: boolean; onTestPortal?: (id: string) => void }) {
  const out = attempt.output;
  return (
    <section className="at-round" aria-label={`Lần ${attempt.n}`}>
      <h2 className="at-round__title">Lần {attempt.n}{attempt.n > 1 ? " (agent sửa tiếp theo lỗi hệ thống báo)" : ""}</h2>
      <article className="at-card">
        <header className="at-card__head">
          <strong>Lập trình viên</strong>
          {out.pipelineFolder ? <span className="mono faint">{out.pipelineFolder}</span> : null}
          <span className="faint num at-card__conf">${attempt.cost.toFixed(2)}</span>
        </header>
        <p>{out.summary}</p>
        {out.assumptions?.length ? (
          <div className="dv-assume">
            <b><Icon name="alert" size={14} /> Agent tự suy ra, cần kiểm ({out.assumptions.length})</b>
            <ul>{out.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </div>
        ) : null}
        {out.questions?.length ? (
          <div className="dv-assume dv-assume--ask">
            <b>Cần bạn quyết</b>
            <ul>{out.questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
          </div>
        ) : null}
        {out.troLy ? <p className="muted"><b>Trợ lý:</b> {out.troLy}</p> : null}
        {out.notes ? <p className="muted">{out.notes}</p> : null}
        {attempt.files.length ? <p className="mono at-refs">{attempt.files.join("  ")}</p> : null}
        {attempt.patch ? <Patch patch={attempt.patch} open={last} /> : null}
      </article>
      <Checks round={{ tests: attempt.tests, deploy: attempt.deploy }} />
      <Smoke attempt={attempt} onTestPortal={last ? onTestPortal : undefined} />
      {attempt.problem ? <p className="at-failed"><b>Chưa đạt, đã trả lại cho agent.</b> {attempt.problem}</p> : null}
    </section>
  );
}

function InputsTab({ job }: { job: DevJob }) {
  const [opening, setOpening] = useState("");
  const [error, setError] = useState("");

  async function open(item: DevInput) {
    setOpening(item.name);
    setError("");
    try {
      const url = await loadInput(job.id, item.name);
      window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setOpening("");
    }
  }

  return (
    <div className="dv-inputs">
      {error ? <p className="form-error">{error}</p> : null}
      {(Object.keys(GROUP_TITLES) as InputGroup[]).map((group) => {
        const items = job.inputs.filter((i) => i.group === group);
        return (
          <section key={group}>
            <h3 className="section-title">{GROUP_TITLES[group]} <span className="faint">({items.filter((i) => !i.source).length})</span></h3>
            {items.length ? (
              <ul className="dv-input-list">
                {items.map((item) => (
                  <li key={item.path}>
                    <Icon name={item.source ? "document" : "file"} size={14} />
                    <span>{item.name}</span>
                    {item.source ? <span className="faint">bản chữ / ảnh tách từ {item.source}</span> : null}
                    <button type="button" className="btn btn--sm" disabled={opening === item.name} onClick={() => void open(item)}>
                      {opening === item.name ? <Spinner label="Đang mở" /> : "Xem"}
                    </button>
                  </li>
                ))}
              </ul>
            ) : <p className="faint">Không có.</p>}
          </section>
        );
      })}
    </div>
  );
}

type Tab = "flow" | "inputs" | "log";

export default function DevJobDetail({ id, onBack, onTestPortal }: { id: string; onBack: () => void; onTestPortal: (requestId: string) => void }) {
  const [job, setJob] = useState<DevJob | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("flow");
  const [acting, setActing] = useState(false);

  const refresh = useCallback(() => {
    devApi.get(id).then((data) => { setJob(data); setError(""); }).catch((reason) => setError(errorText(reason)));
  }, [id]);
  useEffect(refresh, [refresh]);

  const live = !job || job.status === "queued" || job.status === "running" || !!job.fix?.reverting;
  useEffect(() => {
    if (!live) return;
    const timer = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(timer);
  }, [live, refresh]);

  const lastEvent = useMemo(() => job?.events[job.events.length - 1], [job]);

  async function act(run: () => Promise<unknown>) {
    setActing(true);
    try {
      await run();
      refresh();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setActing(false);
    }
  }

  if (!job) return error ? <ErrorNotice message={error} onRetry={refresh} /> : <PageLoading label="Đang tải job…" />;

  const running = job.status === "queued" || job.status === "running";
  const account = job.settings.account;
  const tone = job.report ? OUTCOMES[job.report.outcome].tone : null;

  return (
    <div className="at-job">
      <div className="page-head">
        <button className="btn btn--sm" type="button" onClick={onBack}><Icon name="arrow-left" size={14} /> Trở lại</button>
        <h1>{job.procedure.label}</h1>
        <span className="mono faint">{job.procedure.key}</span>
        <CopyButton text={job.procedure.key} label="Chép key" />
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
              onClick={() => { if (window.confirm("Hoàn tác toàn bộ thủ tục này (cả link kê khai) và build lại backend?")) void act(() => agentApi.revert(job.id)); }}
            >
              {job.fix.reverting ? <Spinner label="Đang hoàn tác" /> : <><Icon name="refresh" size={14} /> Hoàn tác thủ tục</>}
            </button>
          ) : null}
        </div>
      </div>

      <div className="at-meta faint">
        {job.procedure.code ? <span className="mono">{job.procedure.code}</span> : null}
        {account ? <span>Chạy thử bằng {account.username}{account.xa ? ` · ${account.xa}` : ""}{account.tinh ? `, ${account.tinh}` : ""}</span> : null}
        <span>{job.settings.troLy ? "Có đưa lên trợ lý" : "Không đưa lên trợ lý"}</span>
        <span>Bắt đầu {formatDateTime(job.createdAt)}</span>
        <span className="num">{job.cost.calls} lượt agent · ${job.cost.usd.toFixed(2)}</span>
      </div>
      {job.description ? <blockquote className="at-quote">{job.description}</blockquote> : null}
      <Rail job={job} />
      {running ? (
        <p className="at-live" aria-live="polite">
          <Spinner label={job.status === "queued" ? "Đang chờ ca trước chạy xong" : lastEvent ? `${lastEvent.who ? `${lastEvent.who}: ` : ""}${lastEvent.text}` : "Đang chạy"} />
        </p>
      ) : null}
      {job.report && tone ? (
        <div className={`at-banner at-banner--${tone}`}><strong>{job.report.headline}</strong><p>{job.report.reason}</p></div>
      ) : null}
      {job.status === "failed" ? <div className="at-banner at-banner--bad"><strong>Job dừng vì lỗi</strong><p>{job.error}</p></div> : null}
      {job.status === "stopped" ? <div className="at-banner at-banner--plain"><strong>Đã dừng</strong><p>Mọi thay đổi của job này đã được hoàn tác.</p></div> : null}
      {job.fix?.reverted ? (
        <div className="at-banner at-banner--plain">
          <strong>Thủ tục đã được hoàn tác</strong>
          {job.fix.keptFiles?.length ? <p>Giữ nguyên vì đã bị sửa tiếp sau đó: {job.fix.keptFiles.join(", ")}</p> : null}
        </div>
      ) : null}
      {job.fix && !job.fix.reverted && !job.fix.reverting ? (
        <p className="muted at-note">Code nằm trong thư mục làm việc và chưa commit ({job.fix.files.length} file). Xem lại, kiểm các chỗ agent tự suy ra, rồi tự commit.</p>
      ) : null}
      {job.warnings.map((w) => <p key={w} className="at-warn"><Icon name="alert" size={14} /> {w}</p>)}
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <div className="tabs" role="tablist" aria-label="Chi tiết job">
        {([["flow", "Diễn biến"], ["inputs", "Tài liệu"], ["log", "Nhật ký"]] as [Tab, string][]).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>
      {tab === "flow" ? (
        <div className="at-flow">
          {job.link ? (
            <article className="at-card">
              <header className="at-card__head">
                <strong>Link kê khai</strong>
                <span className={`at-tag at-tag--${job.link.added ? "ok" : "plain"}`}>{job.link.added ? "Đã thêm vào ke_khai_links.json" : "Dùng link có sẵn"}</span>
              </header>
              <pre className="at-patch dv-entry">{JSON.stringify(job.link.entry, null, 2)}</pre>
            </article>
          ) : null}
          {job.attempts.map((attempt, i) => (
            <AttemptView key={attempt.n} attempt={attempt} last={i === job.attempts.length - 1} onTestPortal={job.outcome === "built" ? onTestPortal : undefined} />
          ))}
          {!job.attempts.length && !running ? <p className="faint">Agent chưa trả kết quả nào.</p> : null}
        </div>
      ) : null}
      {tab === "inputs" ? <InputsTab job={job} /> : null}
      {tab === "log" ? <LogTab job={job} /> : null}
    </div>
  );
}
