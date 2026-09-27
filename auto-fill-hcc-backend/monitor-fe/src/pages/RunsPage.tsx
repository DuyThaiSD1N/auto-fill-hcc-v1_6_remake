import { listRuns } from "../api";
import { DateRange, Pager, ProcedureSelect, rangeToDates, ResetButton, SearchInput, Segmented, UnitSelect, useQueryFilters } from "../components/Filters";
import StageRibbon from "../components/StageRibbon";
import { EmptyState, ErrorNotice } from "../components/Status";
import { KindTag, OutcomeBadge, SourceTag } from "../components/Tags";
import { formatInt, formatMs, formatWhen } from "../format";
import { useAsync, useFacets } from "../hooks";
import { buildQuery, navigate } from "../router";
import type { RunRow } from "../types";

const DEFAULTS = {
  range: "7d", from: "", to: "", userId: "", procedure: "", source: "all", kind: "all",
  outcome: "all", minWait: "", maxWait: "", metric: "wait", sort: "new", q: "", page: "1",
};
const PAGE_SIZE = 50;

export function runHref(row: { request_id: string; kind?: string | null }) {
  return `/runs/${encodeURIComponent(row.request_id)}${row.kind ? `?kind=${encodeURIComponent(row.kind)}` : ""}`;
}

export default function RunsPage() {
  const { values: f, set, reset } = useQueryFilters(DEFAULTS);
  const { unitName, procLabel } = useFacets();
  const page = Math.max(1, Number(f.page) || 1);
  const query = buildQuery({
    ...rangeToDates(f.range, f.from, f.to),
    userId: f.userId, procedure: f.procedure, source: f.source, kind: f.kind, outcome: f.outcome,
    minWaitMs: f.minWait ? Math.round(Number(f.minWait) * 1000) : undefined,
    maxWaitMs: f.maxWait ? Math.round(Number(f.maxWait) * 1000) : undefined,
    metric: f.metric === "wait" ? undefined : f.metric,
    sort: f.sort === "new" ? undefined : f.sort, q: f.q, page, pageSize: PAGE_SIZE,
  });
  const { data, error, loading, reload } = useAsync(() => listRuns(query), query);
  const rows = data?.items ?? [];
  const scale = Math.max(1, ...rows.map((r) => r.timing?.wait ?? r.wait_ms ?? 0));

  return (
    <>
      <div className="page-head">
        <h1>Lượt xử lý</h1>
        <span className="page-head__meta num">
          {data ? `${formatInt(data.total)} lượt` : loading ? "Đang tải…" : ""}
        </span>
      </div>

      <div className="filters">
        <DateRange range={f.range} from={f.from} to={f.to} onChange={(p) => set(p)} />
        <UnitSelect value={f.userId} onChange={(v) => set({ userId: v })} />
        <ProcedureSelect value={f.procedure} onChange={(v) => set({ procedure: v })} />
        <Segmented label="Kênh" value={f.source} onChange={(v) => set({ source: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "autofill", label: "Auto Fill" }, { value: "handfree", label: "Handfree" }]} />
        <Segmented label="Bước" value={f.kind} onChange={(v) => set({ kind: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "autofill", label: "Điền" }, { value: "attach", label: "Đính kèm" },
                    { value: "classify", label: "Phân loại" }, { value: "owner_info", label: "Chủ hồ sơ" }]} />
        <Segmented label="Kết quả" value={f.outcome} onChange={(v) => set({ outcome: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "ok", label: "OK" }, { value: "issues", label: "Có vấn đề" }, { value: "error", label: "Hỏng" }]} />
        <label className="filter">
          <select className="select" aria-label="Khoảng thời gian áp cho" value={f.metric} onChange={(e) => set({ metric: e.target.value })}>
            <option value="wait">Người dùng chờ</option>
            <option value="ocr">OCR</option>
            <option value="llm">LLM</option>
          </select>
          <span>từ</span>
          <input className="input input--num" inputMode="decimal" value={f.minWait} placeholder="0"
                 onChange={(e) => set({ minWait: e.target.value.replace(/[^0-9.]/g, "") })} aria-label="Thời gian chờ từ (giây)" />
          <span>đến dưới</span>
          <input className="input input--num" inputMode="decimal" value={f.maxWait} placeholder="∞"
                 onChange={(e) => set({ maxWait: e.target.value.replace(/[^0-9.]/g, "") })} aria-label="Thời gian chờ đến dưới (giây)" />
          <span>giây</span>
        </label>
        <Segmented label="Sắp xếp" value={f.sort} onChange={(v) => set({ sort: v })}
          options={[{ value: "new", label: "Mới nhất" }, { value: "slow", label: f.metric === "wait" ? "Chậm nhất" : `${f.metric === "ocr" ? "OCR" : "LLM"} lâu nhất` }]} />
        <SearchInput value={f.q} onChange={(v) => set({ q: v })} placeholder="Mã hỗ trợ, mã hồ sơ, người làm thủ tục, đơn vị…" />
        <ResetButton onClick={reset} />
      </div>

      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}

      <div className="table-wrap" aria-busy={loading}>
        <table className="grid">
          <thead>
            <tr>
              <th>Thời gian</th><th>Kết quả</th><th>Bước</th><th>Kênh</th><th>Đơn vị</th>
              <th>Thủ tục</th><th>Người làm thủ tục</th><th>Mã hỗ trợ</th><th className="right">Người dùng chờ</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? Array.from({ length: 8 }, (_, i) => (
              <tr key={i} className="skeleton-row">{Array.from({ length: 9 }, (_, j) => <td key={j}><span /></td>)}</tr>
            )) : rows.map((row) => <RunTableRow key={`${row.request_id}:${row.kind}`} row={row} scale={scale}
                                                   unit={unitName(row.user_id, row.name)} proc={procLabel(row.procedure, row.procedure_label)} />)}
          </tbody>
        </table>
        {data && !rows.length ? <EmptyState title="Không có lượt nào khớp bộ lọc" hint="Nới khoảng thời gian hoặc xoá bớt điều kiện lọc." /> : null}
      </div>
      {data ? <Pager page={page} pageSize={PAGE_SIZE} total={data.total} onPage={(p) => set({ page: String(p) }, { keepPage: true })} /> : null}
    </>
  );
}

function RunTableRow({ row, scale, unit, proc }: { row: RunRow; scale: number; unit: string; proc: string }) {
  const when = formatWhen(row.created_at);
  const wait = row.timing?.wait ?? row.wait_ms ?? null;
  const href = runHref(row);
  return (
    <tr onClick={(e) => (e.metaKey || e.ctrlKey ? window.open(href, "_blank") : navigate(href))}>
      <td className="nowrap"><span className="cell-main num">{when.main}</span><span className="cell-sub">{when.sub}</span></td>
      <td><OutcomeBadge outcome={row.outcome} /></td>
      <td><KindTag kind={row.kind} /></td>
      <td><SourceTag source={row.experience} /></td>
      <td><span className="cell-main" title={unit}>{unit}</span></td>
      <td><span className="cell-main" title={proc}>{proc}</span>{row.error ? <span className="cell-sub" title={row.error}>{row.error}</span> : null}</td>
      <td><span className="cell-main">{row.applicant_name || "—"}</span></td>
      <td><a className="mono" href={href} onClick={(e) => e.stopPropagation()}>{row.request_id}</a></td>
      <td>
        <div className="wait-cell">
          <span className="mono">{formatMs(wait)}</span>
          <StageRibbon timing={row.legacy ? null : row.timing} legacyMs={row.legacy ? row.wait_ms : null} scaleMs={scale} />
        </div>
      </td>
    </tr>
  );
}
