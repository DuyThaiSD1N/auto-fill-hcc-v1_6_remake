import { useEffect, useMemo, useState } from "react";
import CopyButton from "../components/CopyButton";
import Icon from "../components/Icon";
import AttachSimulation from "../components/run/AttachSimulation";
import FormSimulation from "../components/run/FormSimulation";
import Json from "../components/run/Json";
import { Spinner } from "../components/Status";
import { formatDateTime, formatMs } from "../format";
import type { SimStats } from "../simulations/eform";
import {
  asRunDetail, consistency, exportBatch, loadScorer, runFields, runKey, scoreAttach,
  type AttachScore, type Batch, type Consistency, type LabRun, type Scorer, type StepResult,
} from "./engine";

type Tab = "form" | "attach" | "compare" | "json";

interface RunScore {
  form: SimStats | null;
  attach: AttachScore | null;
}

const STATUS_TEXT: Record<StepResult["status"], string> = { ok: "Xong", partial: "Có cảnh báo", error: "Lỗi" };

function avg(values: number[]): number | null {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

function monitorHref(requestId: string, kind: "autofill" | "attach"): string {
  return `${window.location.protocol}//${window.location.hostname}:12007/runs/${encodeURIComponent(requestId)}${kind === "attach" ? "?kind=attach" : ""}`;
}

function Dot({ status }: { status: StepResult["status"] }) {
  return <i className={`lab-dot lab-dot--${status}`} aria-label={STATUS_TEXT[status]} />;
}

function RunCell({ run, score, selected, onSelect }: { run: LabRun; score?: RunScore; selected: boolean; onSelect: () => void }) {
  const label = `Lần ${run.run + 1}`;
  if (run.status === "queued") return <span className="lab-cell lab-cell--idle faint">Chờ chạy</span>;
  if (run.status === "cancelled" && !run.fill) return <span className="lab-cell lab-cell--idle faint">Đã dừng</span>;
  const fill = run.fill;
  const attach = run.attach;
  return (
    <button type="button" className={`lab-cell${selected ? " is-selected" : ""}`} aria-pressed={selected} onClick={onSelect} aria-label={`Xem ${label}`}>
      {fill ? (
        <span className="lab-cell__line">
          <Dot status={fill.status} />
          <b>Điền</b>
          <span className="num">{formatMs(fill.ms)}</span>
        </span>
      ) : null}
      {fill && fill.status !== "error" && score?.form ? (
        <span className="lab-cell__line lab-cell__sub">
          <span className="num">{score.form.filled}/{score.form.cells} ô</span>
          <span className={score.form.red ? "ef-red num" : "num"}>{score.form.red} đỏ</span>
        </span>
      ) : null}
      {fill?.status === "error" ? <span className="lab-cell__line lab-cell__sub ef-red" title={fill.error}>{fill.error}</span> : null}
      {attach ? (
        <span className="lab-cell__line">
          <Dot status={attach.status} />
          <b>Đính</b>
          <span className="num">{formatMs(attach.ms)}</span>
        </span>
      ) : null}
      {score?.attach ? (
        <span className="lab-cell__line lab-cell__sub">
          <span className="num">{score.attach.items} mục</span>
          {score.attach.lost ? <span className="ef-red num">{score.attach.lost} lạc dòng</span> : null}
          {score.attach.unused ? <span className="ef-red num">{score.attach.unused} tệp sót</span> : null}
        </span>
      ) : null}
      {attach?.status === "error" ? <span className="lab-cell__line lab-cell__sub ef-red" title={attach.error}>{attach.error}</span> : null}
      {run.status === "running" ? <span className="lab-cell__line lab-cell__sub"><Spinner label={fill ? "Đang đính kèm" : "Đang điền"} /></span> : null}
      {run.status === "cancelled" ? <span className="lab-cell__line lab-cell__sub faint">Đã dừng giữa chừng</span> : null}
    </button>
  );
}

function StabilityCell({ cons, runs, attach }: { cons: Consistency | null; runs: number; attach: boolean }) {
  if (runs < 2) return <span className="faint">Chạy 1 lần — không so</span>;
  if (!cons || cons.runs.length < 2) return <span className="faint">Cần ≥ 2 lần điền xong</span>;
  const diff = cons.rows.length - cons.stable;
  return (
    <span className="lab-stab">
      <span className={diff ? "ef-red" : "lab-ok"}>
        <b className="num">{cons.stable}/{cons.rows.length}</b> field giống nhau ở {cons.runs.length} lần
      </span>
      {attach && cons.attachVariants ? (
        <span className={cons.attachVariants > 1 ? "ef-red" : "lab-ok"}>
          {cons.attachVariants > 1 ? `Đính kèm: ${cons.attachVariants} cách chia khác nhau` : "Đính kèm: mọi lần như nhau"}
        </span>
      ) : null}
    </span>
  );
}

function CompareTable({ cons, focus }: { cons: Consistency; focus: number }) {
  const unstable = cons.rows.filter((r) => !r.stable);
  const [onlyDiff, setOnlyDiff] = useState(unstable.length > 0);
  const rows = onlyDiff ? unstable : cons.rows;
  return (
    <div>
      <div className="lab-compare__bar">
        <span className="muted">
          {cons.runs.length} lần điền xong · <b className={unstable.length ? "ef-red" : "lab-ok"}>{unstable.length}</b> / {cons.rows.length} field có giá trị khác nhau giữa các lần
        </span>
        <label className="lab-check">
          <input type="checkbox" checked={onlyDiff} onChange={(e) => setOnlyDiff(e.target.checked)} /> Chỉ hiện field khác nhau
        </label>
      </div>
      {rows.length ? (
        <div className="table-wrap">
          <table className="mini-table lab-compare">
            <thead>
              <tr>
                <th>Field</th>
                {cons.runs.map((r) => <th key={r.run} className={r.run === focus ? "is-focus" : undefined}>Lần {r.run + 1}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className={row.stable ? undefined : "is-diff"}>
                  <td><span className="mono">{row.key}</span>{row.comp ? <small className="faint"> {row.comp}</small> : null}</td>
                  {row.values.map((v, i) => (
                    <td key={i} className={`${cons.runs[i].run === focus ? "is-focus" : ""}${!row.stable && (v ?? "") !== (row.values[0] ?? "") ? " is-odd" : ""}`}>
                      {v === null ? <span className="faint">(không trả)</span> : v === "" ? <span className="faint">(trống)</span> : v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="lab-ok">Mọi field giống hệt nhau ở tất cả các lần.</p>}
    </div>
  );
}

function StepHead({ title, step, kind }: { title: string; step?: StepResult; kind: "autofill" | "attach" }) {
  if (!step) return null;
  const errors = Array.isArray(step.response?.errors) ? (step.response!.errors as string[]) : [];
  return (
    <div className="lab-step">
      <span className={`outcome outcome--${step.status === "partial" ? "partial" : step.status}`}><Dot status={step.status} /> {title}: {STATUS_TEXT[step.status]}</span>
      <span className="num muted">{formatMs(step.ms)}</span>
      {step.requestId ? (
        <>
          <span className="mono">{step.requestId}</span>
          <CopyButton text={step.requestId} label="Chép mã" />
          <a className="btn btn--sm" href={monitorHref(step.requestId, kind)} target="_blank" rel="noreferrer">Monitor <Icon name="external" size={13} /></a>
        </>
      ) : null}
      {step.error ? <span className="ef-red">{step.error}</span> : null}
      {errors.map((e) => <span key={e} className="ef-red lab-step__err">{e}</span>)}
    </div>
  );
}

function RunDetailView({ batch, run, cons, tab, setTab }: { batch: Batch; run: LabRun; cons: Consistency | null; tab: Tab; setTab: (t: Tab) => void }) {
  const hasAttach = batch.settings.attach;
  const detail = useMemo(() => asRunDetail(batch, run), [batch, run]);
  const tabs: { key: Tab; label: string; show: boolean }[] = [
    { key: "form", label: "Mô phỏng form", show: true },
    { key: "attach", label: "Mô phỏng đính kèm", show: hasAttach },
    { key: "compare", label: `So sánh các lần của ${batch.sets[run.set]?.name ?? "bộ"}`, show: true },
    { key: "json", label: "Output máy chủ", show: true },
  ];
  return (
    <section className="lab-detail" aria-label="Chi tiết lượt">
      <div className="lab-detail__head">
        <h2>{batch.sets[run.set]?.name} · Lần {run.run + 1}</h2>
        <span className="faint">{(batch.sets[run.set]?.files ?? []).join(" · ")}</span>
      </div>
      <StepHead title="Điền" step={run.fill} kind="autofill" />
      <StepHead title="Đính kèm" step={run.attach} kind="attach" />
      <div className="tabs" role="tablist" aria-label="Chi tiết lượt">
        {tabs.filter((t) => t.show).map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>
      {tab === "form" ? (
        run.fill && run.fill.status !== "error" ? <FormSimulation run={detail} /> : <p className="faint">Lượt này không có kết quả điền.</p>
      ) : null}
      {tab === "attach" ? (
        run.attach && run.attach.status !== "error" ? <AttachSimulation run={detail} /> : <p className="faint">Lượt này không có kế hoạch đính kèm.</p>
      ) : null}
      {tab === "compare" ? (cons && cons.runs.length > 1 ? <CompareTable cons={cons} focus={run.run} /> : <p className="faint">Cần ít nhất 2 lần điền xong của bộ này để so.</p>) : null}
      {tab === "json" ? (
        <div className="layers">
          <div className="panel panel__body"><div className="section-title">Điền (fill)</div><Json value={run.fill?.response ?? run.fill?.error} tall empty="Không gọi điền" /></div>
          {hasAttach ? <div className="panel panel__body"><div className="section-title">Đính kèm (attach)</div><Json value={run.attach?.response ?? run.attach?.error} tall empty="Không gọi đính kèm" /></div> : null}
        </div>
      ) : null}
    </section>
  );
}

export default function Results({ batch, running }: { batch: Batch; running: boolean }) {
  const [scorer, setScorer] = useState<Scorer | null>(null);
  const [scorerError, setScorerError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  // Tab giữ nguyên khi chuyển lượt → bấm lần lượt các ô để so cùng một góc nhìn.
  const [tab, setTab] = useState<Tab>("form");

  useEffect(() => {
    let active = true;
    loadScorer(batch.procedure)
      .then((s) => { if (active) setScorer(s); })
      .catch((e) => { if (active) setScorerError(e instanceof Error ? e.message : String(e)); });
    return () => { active = false; };
  }, [batch.procedure]);

  const scores = useMemo(() => {
    const map = new Map<string, RunScore>();
    if (!scorer) return map;
    for (const run of batch.runs) {
      if (!run.fill && !run.attach) continue;
      map.set(runKey(run), {
        form: run.fill && run.fill.status !== "error" ? scorer.form(runFields(run)) : null,
        attach: scoreAttach(run, batch.sets[run.set]?.files.length ?? 0, scorer.components),
      });
    }
    return map;
  }, [batch, scorer]);

  const cons = useMemo(() => batch.sets.map((_, i) => consistency(batch, i)), [batch]);
  const runCount = Math.max(...batch.runs.map((r) => r.run + 1));

  // Tự mở lượt đầu tiên chạy xong để có cái xem ngay.
  const firstDone = batch.runs.find((r) => r.status === "done");
  useEffect(() => {
    if (!selected && firstDone) setSelected(runKey(firstDone));
  }, [selected, firstDone]);

  const done = batch.runs.filter((r) => r.status === "done");
  const fills = done.map((r) => r.fill).filter(Boolean) as StepResult[];
  const attaches = done.map((r) => r.attach).filter(Boolean) as StepResult[];
  const reds = done.map((r) => scores.get(runKey(r))?.form?.red).filter((n): n is number => typeof n === "number");
  const comparable = cons.filter((c): c is Consistency => !!c && c.runs.length > 1);
  const stable = comparable.reduce((n, c) => n + c.stable, 0);
  const total = comparable.reduce((n, c) => n + c.rows.length, 0);
  const failed = fills.filter((f) => f.status === "error").length + attaches.filter((a) => a.status === "error").length;
  const avgRed = avg(reds);
  const current = batch.runs.find((r) => runKey(r) === selected);

  return (
    <section className="lab-results" aria-label="Kết quả kiểm thử">
      <div className="page-head">
        <h1>{batch.label}</h1>
        <span className="faint">{batch.account} · {formatDateTime(batch.createdAt)}</span>
        {running ? <Spinner label={`Đang chạy ${done.length}/${batch.runs.length} lượt`} /> : null}
        <div className="page-head__actions">
          <button className="btn btn--sm" type="button" disabled={running} onClick={() => exportBatch(batch)}>
            <Icon name="document" size={14} /> Xuất JSON
          </button>
        </div>
      </div>
      {running ? (
        <div className="lab-progress" role="progressbar" aria-valuemin={0} aria-valuemax={batch.runs.length} aria-valuenow={done.length}>
          <span style={{ width: `${(done.length / batch.runs.length) * 100}%` }} />
        </div>
      ) : null}

      <div className="kpis">
        <div className="kpi"><span>Lượt xong</span><b>{done.length}/{batch.runs.length}</b><small>{failed ? `${failed} lần gọi lỗi` : "không lần gọi nào lỗi"}</small></div>
        <div className="kpi"><span>Điền trung bình</span><b>{formatMs(avg(fills.filter((f) => f.status !== "error").map((f) => f.ms)))}</b><small>{fills.filter((f) => f.status === "partial").length} lượt có cảnh báo</small></div>
        <div className="kpi"><span>Đính kèm trung bình</span><b>{batch.settings.attach ? formatMs(avg(attaches.filter((a) => a.status !== "error").map((a) => a.ms))) : "—"}</b><small>{batch.settings.attach ? (batch.settings.split ? "có tách giấy tờ" : "không tách giấy tờ") : "thủ tục chỉ điền"}</small></div>
        <div className="kpi"><span>Ô đỏ trên cổng (TB)</span><b className={avgRed ? "ef-red" : undefined}>{avgRed === null ? "—" : avgRed.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}</b><small>{scorerError ? "không nạp được mẫu form" : scorer ? "theo mô phỏng form" : "đang nạp mẫu form…"}</small></div>
        <div className="kpi"><span>Field ổn định giữa các lần</span><b className={total && stable < total ? "ef-red" : undefined}>{total ? `${Math.round((stable / total) * 100)}%` : "—"}</b><small>{total ? `${stable}/${total} field ở ${comparable.length} bộ` : "cần ≥ 2 lần mỗi bộ"}</small></div>
      </div>

      <div className="table-wrap lab-matrix-wrap">
        <table className="lab-matrix">
          <thead>
            <tr>
              <th>Bộ tài liệu</th>
              {Array.from({ length: runCount }, (_, i) => <th key={i}>Lần {i + 1}</th>)}
              <th>Giữa các lần</th>
            </tr>
          </thead>
          <tbody>
            {batch.sets.map((set, si) => (
              <tr key={si}>
                <th scope="row">
                  <span className="lab-matrix__set">{set.name}</span>
                  <small className="faint">{set.files.length} tệp{set.applicant ? " · có mốc người nộp" : ""}</small>
                </th>
                {Array.from({ length: runCount }, (_, ri) => {
                  const run = batch.runs.find((r) => r.set === si && r.run === ri);
                  return (
                    <td key={ri}>
                      {run ? <RunCell run={run} score={scores.get(runKey(run))} selected={selected === runKey(run)} onSelect={() => setSelected(runKey(run))} /> : null}
                    </td>
                  );
                })}
                <td><StabilityCell cons={cons[si]} runs={runCount} attach={batch.settings.attach} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {current && current.status !== "queued" ? <RunDetailView key={runKey(current)} batch={batch} run={current} cons={cons[current.set]} tab={tab} setTab={setTab} /> : null}
    </section>
  );
}
