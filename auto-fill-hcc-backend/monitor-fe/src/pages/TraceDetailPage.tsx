import { useCallback, useEffect, useState } from "react";
import { getTrace } from "../api";
import {
  formatBytes,
  formatDateTime,
  formatDuration,
  safeJson,
  traceActionLabel,
  traceSourceLabel,
  traceUnit,
} from "../format";
import type { MonitorUser, TraceDetail } from "../types";
import AppHeader from "../components/AppHeader";
import Icon from "../components/Icon";
import { ErrorNotice, PageLoading } from "../components/Status";
import TraceFileViewer from "../components/TraceFileViewer";

type OutputTab = "summary" | "ocr" | "llm" | "report";

const TABS: { key: OutputTab; index: string; label: string }[] = [
  { key: "summary", index: "02", label: "Tổng quan" },
  { key: "ocr", index: "03", label: "OCR" },
  { key: "llm", index: "04", label: "LLM" },
  { key: "report", index: "05", label: "Thực thi" },
];

interface Props {
  traceId: string;
  user: MonitorUser;
  onLogout: () => void;
  onBack: () => void;
}

function MetaItem({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return <div className="meta-item"><dt>{label}</dt><dd className={mono ? "mono" : undefined}>{value}</dd></div>;
}

export default function TraceDetailPage({ traceId, user, onLogout, onBack }: Props) {
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<OutputTab>("summary");
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setTrace(await getTrace(traceId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không tải được chi tiết trace.");
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    document.title = trace
      ? `${trace.request_id} — Trợ lý hồ sơ Monitor`
      : "Chi tiết trace — Trợ lý hồ sơ Monitor";
    return () => { document.title = "Trợ lý hồ sơ — Monitor"; };
  }, [trace]);

  async function copyRequestId() {
    if (!trace) return;
    try {
      await navigator.clipboard.writeText(trace.request_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard có thể bị chặn nếu domain chưa HTTPS; mã vẫn luôn hiển thị để copy tay.
    }
  }

  if (loading && !trace) {
    return <div className="monitor-app"><AppHeader user={user} onLogout={onLogout} /><PageLoading label="Đang tải dấu vết hồ sơ…" /></div>;
  }

  if (error && !trace) {
    return (
      <div className="monitor-app">
        <AppHeader user={user} onLogout={onLogout} />
        <main id="main-content" className="shell detail-error-page">
          <button className="button button--ghost" onClick={onBack} type="button"><Icon name="arrow-left" /> Quay lại tra cứu</button>
          <ErrorNotice message={error} onRetry={load} />
        </main>
      </div>
    );
  }

  if (!trace) return null;

  const ocrText = trace.ocr_text?.trim() || "";
  const llmText = safeJson(trace.llm_output);
  const reportText = safeJson(trace.report);
  const procedure = trace.procedure_label || trace.procedure || "Thủ tục chưa xác định";

  return (
    <div className="monitor-app">
      <AppHeader user={user} onLogout={onLogout} />
      <main id="main-content" className="shell detail-page">
        <nav className="detail-breadcrumb" aria-label="Điều hướng chi tiết">
          <button className="button button--ghost" onClick={onBack} type="button"><Icon name="arrow-left" /> Tra mã hỗ trợ</button>
          <span>/</span>
          <span className="mono">{trace.request_id}</span>
        </nav>

        <section className="trace-hero">
          <div className="trace-hero__main">
            <div className="trace-hero__labels">
              <span className={`badge badge--${trace.experience === "handfree" ? "voice" : "quiet"}`}>{traceSourceLabel(trace.experience)}</span>
              <span className="badge badge--outline">{traceActionLabel(trace.kind)}</span>
              <span className={`badge ${trace.status === "done" ? "badge--success" : "badge--warning"}`}>{trace.status || "Không rõ trạng thái"}</span>
            </div>
            <h1>{procedure}</h1>
            <p>{traceUnit(trace.name, trace.username)} · {formatDateTime(trace.created_at)}</p>
          </div>
          <div className="request-id-card">
            <span>Mã hỗ trợ</span>
            <strong>{trace.request_id}</strong>
            <button className="button button--secondary" onClick={copyRequestId} type="button">
              <Icon name={copied ? "check" : "copy"} /> {copied ? "Đã sao chép" : "Sao chép mã"}
            </button>
          </div>
        </section>

        <section className="trace-metrics" aria-label="Chỉ số xử lý">
          <article><span>Tệp đầu vào</span><strong>{(trace.attachments || []).length}</strong><small>{formatBytes(trace.total_bytes)}</small></article>
          <article><span>Trường điền</span><strong>{trace.fields_count ?? 0}</strong><small>{trace.kind === "attach" ? "Lượt đính kèm" : `${trace.key_fields_filled ?? 0}/${trace.key_fields_total ?? 0} trường then chốt`}</small></article>
          <article><span>OCR</span><strong>{formatDuration(trace.stats?.ocr_latency_ms)}</strong><small>{trace.ocr_label || trace.ocr_provider || "Không có nhãn"}</small></article>
          <article><span>Tổng xử lý</span><strong>{formatDuration(trace.stats?.total_latency_ms)}</strong><small>LLM {formatDuration(trace.stats?.llm_latency_ms)}</small></article>
        </section>

        <TraceFileViewer files={trace.attachments || []} traceId={trace.id} />

        <section className="output-workbench">
          <header className="output-heading">
            <div>
              <span className="eyebrow">Processing evidence</span>
              <h2>Output các bước</h2>
            </div>
            {error ? <span className="inline-error">{error}</span> : null}
          </header>

          <div className="output-tabs" role="tablist" aria-label="Output xử lý">
            {TABS.map((item) => (
              <button
                aria-controls={`trace-panel-${item.key}`}
                aria-selected={tab === item.key}
                className={tab === item.key ? "active" : ""}
                id={`trace-tab-${item.key}`}
                key={item.key}
                onClick={() => setTab(item.key)}
                role="tab"
                type="button"
              >
                <span>{item.index}</span>{item.label}
              </button>
            ))}
          </div>

          <div className="output-panel" id={`trace-panel-${tab}`} role="tabpanel" aria-labelledby={`trace-tab-${tab}`} tabIndex={0}>
            {tab === "summary" ? (
              <dl className="meta-grid">
                <MetaItem label="Đơn vị" value={traceUnit(trace.name, trace.username)} />
                <MetaItem label="Tài khoản" value={trace.username || "—"} mono />
                <MetaItem label="Người làm thủ tục" value={trace.applicant_name || "—"} />
                <MetaItem label="Thủ tục" value={procedure} />
                <MetaItem label="Nguồn" value={traceSourceLabel(trace.experience)} />
                <MetaItem label="Thao tác" value={traceActionLabel(trace.kind)} />
                <MetaItem label="Trạng thái" value={trace.status || "—"} />
                <MetaItem label="Mã lỗi" value={trace.error_code || "—"} mono />
                <MetaItem label="Thời gian" value={formatDateTime(trace.created_at)} />
                <MetaItem label="Trace ID" value={trace.id} mono />
              </dl>
            ) : null}

            {tab === "ocr" ? (
              ocrText ? <pre className="evidence-block evidence-block--text">{ocrText}</pre> : <OutputEmpty label="Trace này không lưu nội dung OCR." />
            ) : null}

            {tab === "llm" ? (
              llmText ? <pre className="evidence-block evidence-block--json">{llmText}</pre> : <OutputEmpty label="Trace này không lưu output LLM." />
            ) : null}

            {tab === "report" ? (
              reportText ? <pre className="evidence-block evidence-block--json">{reportText}</pre> : <OutputEmpty label="Chưa có báo cáo thực thi từ extension cho trace này." />
            ) : null}
          </div>
        </section>
      </main>
    </div>
  );
}

function OutputEmpty({ label }: { label: string }) {
  return <div className="output-empty"><Icon name="document" size={26} /><p>{label}</p></div>;
}
