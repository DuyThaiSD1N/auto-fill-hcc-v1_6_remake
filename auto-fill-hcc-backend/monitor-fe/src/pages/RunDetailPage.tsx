import { useEffect, useMemo, useState } from "react";
import { getRun } from "../api";
import CopyButton from "../components/CopyButton";
import Icon from "../components/Icon";
import AttachSimulation from "../components/run/AttachSimulation";
import Documents from "../components/run/Documents";
import FieldLineage from "../components/run/FieldLineage";
import FormSimulation from "../components/run/FormSimulation";
import Inspector from "../components/run/Inspector";
import Json from "../components/run/Json";
import { defaultSpan, flattenSpans } from "../components/run/model";
import OutputLayers from "../components/run/OutputLayers";
import Waterfall from "../components/run/Waterfall";
import StageRibbon, { RibbonLegend } from "../components/StageRibbon";
import { ErrorNotice, PageLoading } from "../components/Status";
import { KindTag, OutcomeBadge, SourceTag } from "../components/Tags";
import { formatBytes, formatDateTime, formatInt, formatMs, splitMs } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate, onLinkClick, useLocation } from "../router";
import type { RunDetail } from "../types";
import { dossierHref } from "./DossiersPage";

type Tab = "stages" | "output" | "docs" | "lineage" | "sim" | "form" | "raw";

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
  const { unitName, procLabel } = useFacets();
  const kind = steps?.kind ?? trace?.kind ?? "autofill";
  const timing = steps?.timing ?? trace?.timing ?? null;
  const flat = useMemo(() => flattenSpans(steps?.spans ?? []), [steps]);
  // Tab nằm trên URL (?tab=) → gửi link mở đúng tab.
  const loc = useLocation();
  const tab = ((loc.query.get("tab") as Tab | null) ?? (steps ? "stages" : "output"));
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
    { key: "output", label: "Output", show: true },
    { key: "docs", label: "Giấy tờ", show: true },
    { key: "lineage", label: "Dòng đời field", show: kind === "autofill" && !!steps },
    { key: "form", label: "Mô phỏng form", show: kind === "autofill" },
    { key: "sim", label: "Mô phỏng đính kèm", show: kind === "attach" },
    { key: "raw", label: "Dữ liệu thô", show: true },
  ];

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
            {trace?.applicant_name ? <><span>·</span><span>{trace.applicant_name}</span></> : null}
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
      {tab === "output" ? <OutputLayers run={run} /> : null}
      {tab === "docs" ? <Documents run={run} /> : null}
      {tab === "lineage" ? <FieldLineage run={run} /> : null}
      {tab === "sim" ? <div className="panel panel__body"><AttachSimulation run={run} /></div> : null}
      {tab === "form" ? <FormSimulation run={run} /> : null}
      {tab === "raw" ? (
        <div className="layers">
          <div className="panel panel__body"><div className="section-title">traces</div><Json value={trace} tall empty="Lượt này không có bản ghi traces" /></div>
          <div className="panel panel__body"><div className="section-title">trace_steps</div><Json value={steps} tall empty="Lượt này chưa có chi tiết công đoạn" /></div>
        </div>
      ) : null}
    </>
  );
}
