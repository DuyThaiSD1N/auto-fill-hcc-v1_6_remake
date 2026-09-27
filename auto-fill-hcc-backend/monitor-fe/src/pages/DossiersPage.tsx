import { listDossiers } from "../api";
import { DateRange, Pager, ProcedureSelect, rangeToDates, ResetButton, SearchInput, Segmented, UnitSelect, useQueryFilters } from "../components/Filters";
import { EmptyState, ErrorNotice } from "../components/Status";
import { SourceTag } from "../components/Tags";
import { formatInt, formatMs, formatWhen } from "../format";
import { useAsync, useFacets } from "../hooks";
import { buildQuery, navigate } from "../router";
import type { Dossier } from "../types";

const DEFAULTS = { range: "7d", from: "", to: "", userId: "", procedure: "", source: "all", status: "all", q: "", page: "1" };
const PAGE_SIZE = 50;

export function dossierHref(id: string) {
  return `/dossiers/${encodeURIComponent(id)}`;
}

export default function DossiersPage() {
  const { values: f, set, reset } = useQueryFilters(DEFAULTS);
  const { unitName, procLabel } = useFacets();
  const page = Math.max(1, Number(f.page) || 1);
  const query = buildQuery({
    ...rangeToDates(f.range, f.from, f.to),
    userId: f.userId, procedure: f.procedure, source: f.source, status: f.status, q: f.q, page, pageSize: PAGE_SIZE,
  });
  const { data, error, loading, reload } = useAsync(() => listDossiers(query), query);
  const rows = data?.items ?? [];

  return (
    <>
      <div className="page-head">
        <h1>Hồ sơ</h1>
        <span className="page-head__meta num">{data ? `${formatInt(data.total)} hồ sơ` : loading ? "Đang tải…" : ""}</span>
      </div>

      <div className="filters">
        <DateRange range={f.range} from={f.from} to={f.to} onChange={(p) => set(p)} />
        <UnitSelect value={f.userId} onChange={(v) => set({ userId: v })} />
        <ProcedureSelect value={f.procedure} onChange={(v) => set({ procedure: v })} />
        <Segmented label="Kênh" value={f.source} onChange={(v) => set({ source: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "autofill", label: "Auto Fill" }, { value: "handfree", label: "Handfree" }]} />
        <Segmented label="Trạng thái" value={f.status} onChange={(v) => set({ status: v })}
          options={[{ value: "all", label: "Tất cả" }, { value: "submitted", label: "Đã nộp" }, { value: "unsubmitted", label: "Chưa nộp" }]} />
        <SearchInput value={f.q} onChange={(v) => set({ q: v })} placeholder="Mã hồ sơ, người làm thủ tục, đơn vị, thủ tục…" />
        <ResetButton onClick={reset} />
      </div>

      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}

      <div className="table-wrap" aria-busy={loading}>
        <table className="grid">
          <thead>
            <tr>
              <th>Bắt đầu</th><th>Trạng thái</th><th>Kênh</th><th>Đơn vị</th><th>Thủ tục</th>
              <th>Người làm thủ tục</th><th className="right">Lượt</th><th className="right">Tới lúc nộp</th><th>Đánh giá</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? Array.from({ length: 8 }, (_, i) => (
              <tr key={i} className="skeleton-row">{Array.from({ length: 9 }, (_, j) => <td key={j}><span /></td>)}</tr>
            )) : rows.map((d) => <DossierRow key={d.id} d={d} unit={unitName(d.userId, d.name)} proc={procLabel(d.procedure, d.procedureLabel)} />)}
          </tbody>
        </table>
        {data && !rows.length ? <EmptyState title="Không có hồ sơ nào khớp bộ lọc" hint="Nới khoảng thời gian hoặc xoá bớt điều kiện lọc." /> : null}
      </div>
      {data ? <Pager page={page} pageSize={PAGE_SIZE} total={data.total} onPage={(p) => set({ page: String(p) }, { keepPage: true })} /> : null}
    </>
  );
}

export function DossierStatus({ d }: { d: Dossier }) {
  if (d.submittedAt) {
    return <span className="outcome outcome--ok"><span className="outcome__dot">✓</span>Đã nộp{d.submitCount && d.submitCount > 1 ? ` ×${d.submitCount}` : ""}</span>;
  }
  if (d.closedAt) return <span className="tag">Đã đóng</span>;
  return <span className="tag">Chưa nộp</span>;
}

function DossierRow({ d, unit, proc }: { d: Dossier; unit: string; proc: string }) {
  const when = formatWhen(d.startedAt);
  const href = dossierHref(d.id);
  return (
    <tr onClick={(e) => (e.metaKey || e.ctrlKey ? window.open(href, "_blank") : navigate(href))}>
      <td className="nowrap"><span className="cell-main num">{when.main}</span><span className="cell-sub">{when.sub}</span></td>
      <td><DossierStatus d={d} /></td>
      <td><SourceTag source={d.experience} /></td>
      <td><span className="cell-main" title={unit}>{unit}</span></td>
      <td><span className="cell-main" title={proc}>{proc}</span></td>
      <td><a className="cell-main" href={href} onClick={(e) => e.stopPropagation()}>{d.applicantName || <span className="faint mono">{d.id}</span>}</a></td>
      <td className="right num">{d.runs ?? "—"}</td>
      <td className="right mono">{formatMs(d.durationMs)}</td>
      <td>{d.rating?.label ? <span className="tag">{d.rating.label}</span> : <span className="faint">—</span>}</td>
    </tr>
  );
}
