import { useEffect, useMemo, useState } from "react";
import { getRun } from "../api";
import CopyButton from "../components/CopyButton";
import Icon from "../components/Icon";
import AttachSimulation from "../components/run/AttachSimulation";
import FormSimulation from "../components/run/FormSimulation";
import Inspector from "../components/run/Inspector";
import Json from "../components/run/Json";
import { defaultSpan, flattenSpans } from "../components/run/model";
import Waterfall from "../components/run/Waterfall";
import StageRibbon, { RibbonLegend } from "../components/StageRibbon";
import { ErrorNotice, PageLoading } from "../components/Status";
import { KindTag, OutcomeBadge, SourceTag } from "../components/Tags";
import { formatBytes, formatDateTime, formatInt, formatMs, splitMs } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate, onLinkClick, useLocation } from "../router";
import { toFields, type UiField } from "../simulations/fill";
import type { FormSnapshot, FormSnapshotField, RunDetail } from "../types";
import { dossierHref } from "./DossiersPage";

type Tab = "stages" | "form" | "sim" | "snap" | "raw";

const FLAG_LABELS: Record<string, string> = {
  llm_fallback: "LLM rơi sang dự phòng",
  llm_cut: "LLM bị cắt do max_tokens",
  parse_fail: "Parse JSON lỗi",
  ocr_fallback: "OCR rơi sang máy dự phòng",
  ocr_error: "Có tệp OCR lỗi",
  client_attach: "Extension tự đính (không qua BE)",
};

export default function RunDetailPage({ requestId, kind }: { requestId: string; kind: string | null }) {
  const { data, error, loading, reload } = useAsync(() => getRun(requestId, kind), `${requestId}:${kind}`);
  useEffect(() => {
    document.title = "Lượt xử lý — Monitor";
    return () => { document.title = "Monitor — Trợ lý nhân dân"; };
  }, [requestId]);

  if (loading && !data) return <PageLoading label="Đang tải lượt xử lý…" />;
  if (error && !data) return <><Crumbs requestId={requestId} /><ErrorNotice message={error} onRetry={reload} /></>;
  if (!data) return null;
  return <RunView run={data} requestId={requestId} />;
}

function Crumbs({ requestId }: { requestId: string }) {
  return (
    <nav className="crumbs" aria-label="Vị trí">
      <a href="/runs" onClick={(e) => onLinkClick(e, "/runs")}>Lượt xử lý</a><span>/</span><span className="mono">{requestId}</span>
    </nav>
  );
}

function RunView({ run, requestId }: { run: RunDetail; requestId: string }) {
  const { trace, steps } = run;
  const snapshots = run.snapshots ?? [];
  const { unitName, procLabel } = useFacets();
  const kind = steps?.kind ?? trace?.kind ?? "autofill";
  const timing = steps?.timing ?? trace?.timing ?? null;
  const flat = useMemo(() => flattenSpans(steps?.spans ?? []), [steps]);
  // Tab nằm trên URL (?tab=) → gửi link mở đúng tab.
  const loc = useLocation();
  const asked = loc.query.get("tab");
  const fallback: Tab = steps ? "stages" : "raw";
  const setTab = (next: Tab) => {
    const q = new URLSearchParams(loc.query);
    q.set("tab", next);
    navigate(`${loc.path}?${q.toString()}`, { replace: true });
  };
  const [selected, setSelected] = useState<number | null>(() => defaultSpan(flat));

  const meta = (steps?.meta ?? {}) as Record<string, string | number | undefined>;
  const procedure = trace?.procedure ?? (meta.procedure as string | undefined);
  const dossierId = trace?.dossier_id ?? (meta.dossier_id as string | undefined);
  const wait = timing?.wait ?? trace?.stats?.total_latency_ms ?? null;
  const [num, unit] = splitMs(wait);
  // Tiêu đề tab: thủ tục + đơn vị để phân biệt nhiều tab đang mở (không đưa tên người dân lên tab).
  const tabTitle = [procLabel(procedure, trace?.procedure_label), unitName(trace?.user_id ?? (meta.user_id as string | undefined), trace?.name)]
    .filter((x) => x && x !== "—").join(" · ");
  useEffect(() => { if (tabTitle) document.title = `${tabTitle} — Monitor`; }, [tabTitle]);
  const n = timing?.n ?? {};
  const pages = (steps?.ocr ?? []).reduce((sum, f) => sum + (f.pages ?? 0), 0);
  const errors = steps?.errors?.length ? steps.errors : trace?.errors ?? (trace?.error_code ? [trace.error_code] : []);
  const flags = Object.entries(timing?.f ?? {}).filter(([, v]) => v).map(([k]) => k);

  const tabs: { key: Tab; label: string; show: boolean }[] = [
    { key: "stages", label: "Công đoạn", show: !!steps },
    // Mô phỏng cần steps.outputs: BE chỉ trả khi không bật kho (máy local), xem app/monitor/router.py.
    { key: "form", label: "Mô phỏng form", show: kind === "autofill" && !!steps?.outputs },
    { key: "sim", label: "Mô phỏng đính kèm", show: kind === "attach" && !!steps?.outputs },
    { key: "snap", label: "Ô trên form", show: snapshots.length > 0 },
    { key: "raw", label: "Dữ liệu thô", show: true },
  ];
  const tab: Tab = tabs.find((t) => t.key === asked && t.show)?.key ?? fallback;

  return (
    <>
      <Crumbs requestId={requestId} />
      <section className="run-head" aria-label="Tóm tắt lượt">
        <div className="run-head__title">
          <h1>{procLabel(procedure, trace?.procedure_label)}</h1>
          <div className="run-head__meta">
            <OutcomeBadge outcome={steps?.outcome ?? trace?.outcome ?? (trace?.status === "error" ? "error" : "ok")} />
            <KindTag kind={kind} />
            <SourceTag source={steps?.experience ?? trace?.experience} />
            <span>{unitName(trace?.user_id ?? (meta.user_id as string), trace?.name ?? (meta.name as string))}</span>
            <span>·</span>
            <span className="num">{formatDateTime(trace?.created_at ?? steps?.created_at)}</span>
          </div>
        </div>
        <div className="run-head__actions">
          <CopyButton text={requestId} label="Sao chép mã" />
          {dossierId ? (
            <a className="btn btn--sm" href={dossierHref(dossierId)} onClick={(e) => onLinkClick(e, dossierHref(dossierId))}>
              Hồ sơ <Icon name="chevron-right" size={14} />
            </a>
          ) : null}
        </div>
        <div className="run-head__time">
          <div className="bignum" aria-label={`Người dùng chờ ${formatMs(wait)}`}>{num}<small>{unit}</small></div>
          <StageRibbon timing={timing} legacyMs={timing ? null : trace?.stats?.total_latency_ms} large />
          <span className="bignum-label">{timing ? "người dùng chờ" : "OCR + LLM (dữ liệu cũ)"}</span>
          {timing ? <RibbonLegend timing={timing} /> : <span />}
        </div>
        <div className="facts">
          <span><b>{formatInt(n.ocr_files ?? trace?.attachments?.length ?? 0)}</b> tệp</span>
          <span><b>{formatBytes(n.bytes ?? trace?.total_bytes)}</b></span>
          {pages ? <span><b>{pages}</b> trang</span> : null}
          {n.ocr_files ? <span>OCR cache <b>{n.ocr_hit ?? 0}/{n.ocr_files}</b></span> : null}
          {n.llm_calls ? <span><b>{n.llm_calls}</b> lần gọi LLM · <b>{formatInt(n.tok_in)}</b>→<b>{formatInt(n.tok_out)}</b> token</span> : null}
          {trace?.key_fields_total ? <span>Field then chốt <b>{trace.key_fields_filled}/{trace.key_fields_total}</b></span> : null}
          {flags.map((f) => <span key={f} className="outcome outcome--partial">{FLAG_LABELS[f] ?? f}</span>)}
          {errors.length ? <span className="outcome outcome--error" title={errors.join("\n")}>{errors.length} lỗi: {errors[0]}</span> : null}
        </div>
      </section>

      <div className="tabs" role="tablist" aria-label="Chi tiết lượt">
        {tabs.filter((t) => t.show).map((t) => (
          <button key={t.key} role="tab" type="button" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
            {t.key === "stages" ? <span className="count">{flat.length}</span> : null}
            {t.key === "snap" ? <span className="count">{snapshots.length}</span> : null}
          </button>
        ))}
      </div>

      {tab === "stages" && steps ? (
        <div className="stage-view">
          <div className="panel">
            <Waterfall spans={flat} waitMs={timing?.wait} selected={selected} onSelect={setSelected} />
          </div>
          <Inspector span={flat.find((s) => s.i === selected) ?? null} steps={steps} />
        </div>
      ) : null}
      {tab === "form" ? <FormSimulation run={run} /> : null}
      {tab === "sim" ? <div className="panel panel__body"><AttachSimulation run={run} /></div> : null}
      {tab === "snap" ? <FormCompare snapshots={snapshots} response={steps?.outputs?.response} /> : null}
      {tab === "raw" ? (
        <div className="layers">
          <div className="panel panel__body"><div className="section-title">traces</div><Json value={trace} tall empty="Lượt này không có bản ghi traces" /></div>
          <div className="panel panel__body"><div className="section-title">trace_steps</div><Json value={steps} tall empty="Lượt này chưa có chi tiết công đoạn" /></div>
        </div>
      ) : null}
    </>
  );
}

// ── Ô trên form: giá trị BE trả (outputs.response.fields) đối chiếu với ảnh chụp form extension gửi về ──

const SNAP_KIND: Record<string, string> = { fill: "Sau khi điền", edit: "Cán bộ sửa", step: "Rời bước" };

type CompareStatus = "match" | "diff" | "empty" | "missing" | "extra";

const COMPARE_STATUS: Record<CompareStatus, { label: string; className: string }> = {
  match: { label: "Khớp", className: "outcome outcome--ok" },
  diff: { label: "Khác", className: "outcome outcome--partial" },
  empty: { label: "Trống trên form", className: "outcome outcome--error" },
  missing: { label: "Không thấy ô", className: "outcome outcome--error" },
  extra: { label: "Ngoài BE", className: "tag" },
};

interface CompareRow {
  key: string;
  name: string;
  label?: string | null;
  section?: string | null;
  be?: unknown;
  form?: unknown;
  status: CompareStatus;
}

/** Giá trị → chữ để xem và so: object (x-select-area…) nối các giá trị con, bỏ phần trống. */
function valueText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(valueText).filter(Boolean).join(", ");
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).map(valueText).filter(Boolean).join(" · ");
  if (typeof value === "boolean") return value ? "Có" : "Không";
  return String(value).replace(/\s+/g, " ").trim();
}

function sameValue(be: unknown, form: unknown): boolean {
  if (be && form && typeof be === "object" && typeof form === "object" && !Array.isArray(be) && !Array.isArray(form)) {
    const a = be as Record<string, unknown>;
    const b = form as Record<string, unknown>;
    const keys = Object.keys(a).filter((k) => k in b && valueText(a[k]));
    if (keys.length) return keys.every((k) => sameValue(a[k], b[k]));
  }
  return valueText(be).toLowerCase() === valueText(form).toLowerCase();
}

const fieldKey = (name: string, occurrence: unknown) => `${name}#${occurrence ?? ""}`;

function compareRows(beFields: UiField[], formFields: FormSnapshotField[]): CompareRow[] {
  const byKey = new Map(formFields.map((f) => [fieldKey(f.name, f.occurrence), f]));
  const byName = new Map<string, FormSnapshotField>();
  for (const f of formFields) if (!byName.has(f.name)) byName.set(f.name, f);
  const used = new Set<FormSnapshotField>();
  const rows: CompareRow[] = beFields.map((b) => {
    const occurrence = (b as { occurrence?: number }).occurrence;
    const key = fieldKey(b.name, occurrence);
    const f = byKey.get(key) ?? byName.get(b.name);
    if (f) used.add(f);
    const status: CompareStatus = !f || f.value === null ? "missing"
      : !valueText(f.value) && valueText(b.value) ? "empty"
        : sameValue(b.value, f.value) ? "match" : "diff";
    return { key, name: b.name, label: f?.label, section: f?.section, be: b.value, form: f?.value, status };
  });
  // Ô BE không trả nhưng trên form có giá trị: cán bộ tự điền thêm hoặc cổng tự điền.
  const extras = formFields
    .filter((f) => !used.has(f) && valueText(f.value))
    .sort((a, b) => (a.pos ?? Infinity) - (b.pos ?? Infinity));
  for (const f of extras) {
    rows.push({ key: `extra:${fieldKey(f.name, f.occurrence)}`, name: f.name, label: f.label, section: f.section,
      form: f.value, status: "extra" });
  }
  return rows;
}

function FormCompare({ snapshots, response }: { snapshots: FormSnapshot[]; response: unknown }) {
  // Mặc định ảnh "sau khi điền": đúng thứ extension đã điền, chưa lẫn phần cán bộ sửa.
  const [index, setIndex] = useState(() => Math.max(0, snapshots.findIndex((s) => s.kind === "fill")));
  const [onlyIssues, setOnlyIssues] = useState(false);
  const snap = snapshots[Math.min(index, snapshots.length - 1)];
  const beFields = useMemo(() => toFields(response), [response]);
  const rows = useMemo(() => compareRows(beFields, snap.fields ?? []), [beFields, snap]);
  const counts = rows.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }), {});
  const shown = onlyIssues ? rows.filter((r) => r.status !== "match") : rows;

  return (
    <div className="layers">
      <div className="panel panel__body">
        <div className="seg" role="group" aria-label="Ảnh chụp form">
          {snapshots.map((s, i) => (
            <button key={`${s.at}:${i}`} type="button" aria-pressed={i === index} onClick={() => setIndex(i)} title={s.trigger || undefined}>
              {SNAP_KIND[s.kind] ?? s.kind} · {formatDateTime(new Date(s.at).toISOString())}
            </button>
          ))}
        </div>
        <p className="faint" style={{ marginTop: 8 }}>
          {snap.host}{snap.path} · extension {snap.extVersion || "?"}{snap.trigger ? ` · ${snap.trigger}` : ""}
        </p>
        <div className="facts" style={{ marginTop: 8 }}>
          {(Object.keys(COMPARE_STATUS) as CompareStatus[]).filter((s) => counts[s]).map((s) => (
            <span key={s} className={COMPARE_STATUS[s].className}>{COMPARE_STATUS[s].label} <b>{counts[s]}</b></span>
          ))}
          {!beFields.length ? <span className="faint">Lượt này không có output BE để đối chiếu</span> : null}
          <label style={{ marginLeft: "auto", display: "inline-flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} /> Chỉ ô lệch
          </label>
        </div>
      </div>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr><th>Ô</th><th>BE trả</th><th>Trên form</th><th>Đối chiếu</th></tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.key}>
                <td>
                  <div className="mono">{r.name}</div>
                  {r.label || r.section ? <div className="faint">{[r.section, r.label].filter(Boolean).join(" › ")}</div> : null}
                </td>
                <td>{r.status === "extra" ? <span className="faint">—</span> : valueText(r.be) || <span className="faint">(trống)</span>}</td>
                <td>{r.form === null || r.form === undefined ? <span className="faint">(không thấy ô)</span> : valueText(r.form) || <span className="faint">(trống)</span>}</td>
                <td><span className={COMPARE_STATUS[r.status].className}>{COMPARE_STATUS[r.status].label}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
