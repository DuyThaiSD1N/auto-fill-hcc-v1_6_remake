import { useState } from "react";
import { getLatency, listRuns } from "../api";
import DayChart from "../components/DayChart";
import { DateRange, ProcedureSelect, rangeToDates, ResetButton, Segmented, UnitSelect, useQueryFilters } from "../components/Filters";
import StageRibbon from "../components/StageRibbon";
import { ErrorNotice } from "../components/Status";
import { KindTag, OutcomeBadge } from "../components/Tags";
import { formatInt, formatMs, formatWhen, pct } from "../format";
import { useAsync, useFacets } from "../hooks";
import { buildQuery, navigate, onLinkClick } from "../router";
import type { LatencyRow, Metric, RunRef } from "../types";
import { runHref } from "./RunsPage";

const DEFAULTS = { metric: "wait", range: "7d", from: "", to: "", userId: "", procedure: "", source: "all", kind: "all" };

// Tên chỉ số trong câu chữ + điều kiện tính (để người đọc biết số lấy trên những lượt nào).
const METRIC_TEXT: Record<Metric, { name: string; title: string; scope: string }> = {
  wait: { name: "Chờ", title: "Người dùng phải chờ bao lâu", scope: "tính mọi lượt có dữ liệu công đoạn" },
  ocr: { name: "OCR", title: "OCR mất bao lâu mỗi lượt", scope: "chỉ tính lượt có gọi OCR thật (không tính lượt dùng lại kết quả cũ)" },
  llm: { name: "LLM", title: "LLM mất bao lâu mỗi lượt", scope: "chỉ tính lượt có gọi LLM (cộng mọi lần gọi trong lượt)" },
};
const BUCKET_CLS = ["b-fast", "b-ok", "b-slow", "b-bad"];

function bucketLabels(bounds: number[]): string[] {
  const s = bounds.map((b) => (b / 1000).toLocaleString("vi-VN"));
  return [`Dưới ${s[0]} giây`, `${s[0]}–${s[1]} giây`, `${s[1]}–${s[2]} giây`, `Trên ${s[2]} giây`];
}

function RunLink({ run, children }: { run: RunRef | null; children: React.ReactNode }) {
  if (!run) return <>{children}</>;
  const href = runHref({ request_id: run.requestId, kind: run.kind });
  return <a href={href} onClick={(e) => onLinkClick(e, href)} title={`Mở lượt ${run.requestId}`}>{children}</a>;
}

export default function DashboardPage() {
  const { values: f, set, reset } = useQueryFilters(DEFAULTS);
  const metric = (["wait", "ocr", "llm"].includes(f.metric) ? f.metric : "wait") as Metric;
  const text = METRIC_TEXT[metric];
  const base = { ...rangeToDates(f.range, f.from, f.to), userId: f.userId, procedure: f.procedure, source: f.source, kind: f.kind };
  const mq = metric === "wait" ? undefined : metric;
  const qAll = buildQuery({ ...base, metric: mq, group: "all" });
  const qDay = buildQuery({ ...base, metric: mq, group: "day" });
  const qProc = buildQuery({ ...base, metric: mq, group: "procedure" });
  const qUnit = buildQuery({ ...base, metric: mq, group: "unit" });
  const qSlow = buildQuery({ ...base, metric: mq, sort: "slow", pageSize: 10 });
  const all = useAsync(() => getLatency(qAll), qAll);
  const day = useAsync(() => getLatency(qDay), qDay);
  const proc = useAsync(() => getLatency(qProc), qProc);
  const unit = useAsync(() => getLatency(qUnit), qUnit);
  const slow = useAsync(() => listRuns(qSlow), qSlow);
  const k = all.data?.rows[0];
  const bounds = all.data?.bounds ?? [5000, 10000, 20000];
  const labels = bucketLabels(bounds);
  const error = all.error || day.error || proc.error || unit.error;

  // Bấm một mốc → danh sách lượt cùng bộ lọc + khoảng thời gian của CHỈ SỐ đang xem.
  const openBucket = (i: number) => navigate(`/runs${buildQuery({
    range: f.range, from: f.from, to: f.to, userId: f.userId, procedure: f.procedure, source: f.source, kind: f.kind,
    metric: mq, minWait: i > 0 ? bounds[i - 1] / 1000 : undefined, maxWait: i < 3 ? bounds[i] / 1000 : undefined, sort: "slow",
  })}`);

  return (
    <>
      <div className="page-head">
        <h1>Tổng quan thời gian</h1>
        <span className="page-head__meta">{text.scope}</span>
      </div>
      <div className="filters">
        <Segmented label="Chỉ số" value={metric} onChange={(v) => set({ metric: v })}
          options={[{ value: "wait", label: "Tổng thời gian chờ" }, { value: "ocr", label: "OCR" }, { value: "llm", label: "LLM" }]} />
        <DateRange range={f.range} from={f.from} to={f.to} onChange={(p) => set(p)} />
        <UnitSelect value={f.userId} onChange={(v) => set({ userId: v })} />
        <ProcedureSelect value={f.procedure} onChange={(v) => set({ procedure: v })} />
        <Segmented label="Kênh" value={f.source} onChange={(v) => set({ source: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "autofill", label: "Auto Fill" }, { value: "handfree", label: "Handfree" }]} />
        <Segmented label="Bước" value={f.kind} onChange={(v) => set({ kind: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "autofill", label: "Điền" }, { value: "attach", label: "Đính kèm" }, { value: "classify", label: "Phân loại" }]} />
        <ResetButton onClick={reset} />
      </div>
      {error ? <ErrorNotice message={error} onRetry={() => { all.reload(); day.reload(); proc.reload(); unit.reload(); }} /> : null}

      <div className="kpis kpis--6">
        <div className="kpi"><span>Số lượt{metric === "wait" ? "" : ` có ${text.name}`}</span><b>{formatInt(k?.n ?? 0)}</b></div>
        <div className="kpi"><span>{text.name} trung bình</span><b>{formatMs(k?.avg)}</b></div>
        <div className="kpi">
          <span>{text.name} nhanh nhất</span>
          <b><RunLink run={k?.fastest ?? null}>{formatMs(k?.fastest?.ms)}</RunLink></b>
          <small>{k?.fastest ? "bấm để mở lượt" : ""}</small>
        </div>
        <div className="kpi">
          <span>{text.name} lâu nhất</span>
          <b><RunLink run={k?.slowest ?? null}>{formatMs(k?.slowest?.ms)}</RunLink></b>
          <small>{k?.slowest ? "bấm để mở lượt" : ""}</small>
        </div>
        <div className="kpi"><span>Có lỗi / hỏng</span><b>{k ? pct(k.errors + k.partial, k.n) : "—"}</b><small>{k ? `${k.partial} có lỗi · ${k.errors} hỏng` : ""}</small></div>
        {metric === "llm" ? (
          <div className="kpi"><span>Số lần gọi LLM / lượt</span><b>{k?.llmCalls ?? "—"}</b><small>{k?.tokOut ? `~${formatInt(k.tokOut)} token ra / lượt` : ""}</small></div>
        ) : (
          <div className="kpi"><span>OCR dùng lại kết quả cũ</span><b>{k ? pct(k.ocrHit, k.ocrHit + k.ocrMiss) : "—"}</b><small>{k ? `${formatInt(k.ocrHit)}/${formatInt(k.ocrHit + k.ocrMiss)} tệp` : ""}</small></div>
        )}
      </div>

      {k ? (
        <section className="panel" style={{ marginBottom: 12 }}>
          <div className="panel__head"><h2>{text.title}</h2><span className="faint">bấm một nhóm để xem các lượt trong nhóm đó</span></div>
          <div className="panel__body">
            <div className="dist" role="group" aria-label={`Phân bố ${text.name}`}>
              {k.buckets.map((count, i) => (count ? (
                <button key={i} type="button" className={`dist__seg ${BUCKET_CLS[i]}`} style={{ flexGrow: count }}
                        onClick={() => openBucket(i)} title={`${labels[i]}: ${count} lượt`}
                        aria-label={`${labels[i]}: ${count} lượt (${pct(count, k.n)})`} />
              ) : null))}
            </div>
            <div className="dist__legend">
              {labels.map((label, i) => (
                <button key={i} type="button" onClick={() => openBucket(i)}>
                  <i className={`swatch ${BUCKET_CLS[i]}`} />
                  <span>{label}</span>
                  <b className="num">{pct(k.buckets[i] ?? 0, k.n)}</b>
                  <span className="faint num">{formatInt(k.buckets[i] ?? 0)} lượt</span>
                </button>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <div className="dash-grid">
        <section className="panel">
          <div className="panel__head">
            <h2>Theo ngày</h2>
            <span className="faint">{metric === "wait" ? "chiều cao cột = thời gian chờ trung bình, chia theo công đoạn" : `chiều cao cột = ${text.name} trung bình mỗi lượt`}</span>
          </div>
          <div className="panel__body">{day.data ? <DayChart rows={day.data.rows} metric={metric} /> : <p className="faint">Đang tải…</p>}</div>
        </section>
        <GroupTable title="Theo thủ tục" rows={proc.data?.rows} kind="procedure" metric={metric} bounds={bounds} filters={f} />
        <GroupTable title="Theo đơn vị" rows={unit.data?.rows} kind="unit" metric={metric} bounds={bounds} filters={f} />
        <section className="panel">
          <div className="panel__head"><h2>10 lượt {metric === "wait" ? "lâu nhất" : `${text.name} lâu nhất`}</h2></div>
          <div className="table-wrap" style={{ border: 0 }}>
            <table className="grid">
              <tbody>
                {(slow.data?.items ?? []).map((r) => {
                  const when = formatWhen(r.created_at);
                  const v = metric === "wait" ? r.wait_ms : metric === "ocr" ? r.timing?.g?.ocr : r.timing?.g?.llm;
                  return (
                    <tr key={`${r.request_id}:${r.kind}`} onClick={() => navigate(runHref(r))}>
                      <td className="nowrap num">{when.main} <span className="faint">{when.sub}</span></td>
                      <td><OutcomeBadge outcome={r.outcome} compact /></td>
                      <td><KindTag kind={r.kind} /></td>
                      <td><span className="cell-main">{r.procedure_label || r.procedure}</span></td>
                      <td><div className="wait-cell"><span className="mono">{formatMs(v)}</span><StageRibbon timing={r.legacy ? null : r.timing} legacyMs={r.legacy ? r.wait_ms : null} /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}

type SortKey = "n" | "avg" | "slowest" | "ocrAvg" | "llmAvg" | "llmCalls" | "over" | "err";

function GroupTable({ title, rows, kind, metric, bounds, filters }: {
  title: string; rows?: LatencyRow[]; kind: "procedure" | "unit"; metric: Metric; bounds: number[];
  filters: Record<string, string>;
}) {
  const { unitName, procLabel } = useFacets();
  const [sort, setSort] = useState<SortKey>("n");
  const name = METRIC_TEXT[metric].name;
  const value = (r: LatencyRow, key: SortKey): number => {
    if (key === "err") return (r.errors + r.partial) / Math.max(r.n, 1);
    if (key === "over") return (r.buckets[3] ?? 0) / Math.max(r.n, 1);
    if (key === "slowest") return r.slowest?.ms ?? -1;
    return (r[key] as number | null) ?? -1;
  };
  const sorted = [...(rows ?? [])].sort((a, b) => value(b, sort) - value(a, sort)).slice(0, 30);
  const head = (key: SortKey, label: string) => (
    <th className="right" aria-sort={sort === key ? "descending" : "none"}>
      <button className="btn btn--ghost btn--sm" type="button" onClick={() => setSort(key)}>{label}{sort === key ? " ↓" : ""}</button>
    </th>
  );
  const open = (r: LatencyRow) => navigate(`/runs${buildQuery({
    [kind === "unit" ? "userId" : "procedure"]: r.key ?? "", sort: "slow", range: filters.range, from: filters.from, to: filters.to,
    source: filters.source, kind: filters.kind, metric: metric === "wait" ? undefined : metric,
  })}`);
  const over = `Trên ${(bounds[2] / 1000).toLocaleString("vi-VN")} s`;
  return (
    <section className="panel">
      <div className="panel__head"><h2>{title}</h2><span className="faint">bấm dòng để xem các lượt lâu nhất</span></div>
      <div className="table-wrap" style={{ border: 0 }}>
        <table className="grid">
          <thead>
            <tr>
              <th>{kind === "unit" ? "Đơn vị" : "Thủ tục"}</th>
              {head("n", "Lượt")}{head("avg", `${name} TB`)}{head("slowest", "Lâu nhất")}
              {metric === "wait" ? <>{head("ocrAvg", "OCR TB")}{head("llmAvg", "LLM TB")}</> : null}
              {metric !== "ocr" ? head("llmCalls", "Gọi LLM / lượt") : null}
              {head("over", over)}{head("err", "Lỗi")}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.key ?? "none"} onClick={() => open(r)}>
                <td><span className="cell-main">{kind === "unit" ? unitName(r.key, r.name) : procLabel(r.key, r.label)}</span></td>
                <td className="right num">{formatInt(r.n)}</td>
                <td className="right mono">{formatMs(r.avg)}</td>
                <td className="right mono" onClick={(e) => e.stopPropagation()}><RunLink run={r.slowest}>{formatMs(r.slowest?.ms)}</RunLink></td>
                {metric === "wait" ? <><td className="right mono">{formatMs(r.ocrAvg)}</td><td className="right mono">{formatMs(r.llmAvg)}</td></> : null}
                {metric !== "ocr" ? <td className="right num">{r.llmCalls ?? "—"}</td> : null}
                <td className="right num">{pct(r.buckets[3] ?? 0, r.n)}</td>
                <td className="right num">{pct(r.errors + r.partial, r.n)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows && !rows.length ? <p className="state">Chưa có dữ liệu.</p> : null}
      </div>
    </section>
  );
}
