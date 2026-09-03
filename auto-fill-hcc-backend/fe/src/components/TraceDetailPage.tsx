import { useEffect, useState } from "react";
import { getTrace } from "../api";
import type { TraceDetail, User } from "../types";
import { fmtBytes, fmtDateTime, fmtMs } from "../format";
import { goToList } from "../nav";
import TopBar, { type View } from "./TopBar";
import TraceFiles from "./TraceFiles";

interface Props {
  id: string;
  user: User;
  onLogout: () => void;
  onNavigate: (v: View) => void;
}

// Trang chi tiết trace ĐẦY ĐỦ (URL riêng #/trace/<id>) — mở từ nút "Xem chi tiết" trên drawer.
// Bố cục 2 cột: trái xem file, phải OCR text + LLM JSON; phía trên là thẻ meta gồm thời gian xử lý.
export default function TraceDetailPage({ id, user, onLogout, onNavigate }: Props) {
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setTrace(null);
    setError("");
    getTrace(id)
      .then((t) => alive && setTrace(t))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Lỗi tải chi tiết"));
    return () => {
      alive = false;
    };
  }, [id]);

  const llmText =
    trace && trace.llm_output != null ? JSON.stringify(trace.llm_output, null, 2) : "(không có)";

  return (
    <div className="app">
      <TopBar user={user} view="traces" onNavigate={onNavigate} onLogout={onLogout} />

      <button className="back-link" onClick={goToList}>
        ← Nhật ký
      </button>

      {error && <div className="error bar">{error}</div>}
      {!trace && !error && <div className="muted">Đang tải…</div>}

      {trace && (
        <>
          <div className="detail-head">
            <h1 className="detail-title">{trace.procedure_label || trace.procedure}</h1>
            <div className="detail-badges">
              <span className={`badge source-${trace.experience || "autofill"}`}>
                {trace.experience === "handfree" ? "Handfree" : "No handfree"}
              </span>
              <span className={`badge ${trace.kind === "attach" ? "warn" : "ok"}`}>
                {trace.kind === "attach" ? "Đính kèm" : "Auto-fill"}
              </span>
              {trace.ocr_label && (
                <span className={`badge ocr-${trace.ocr_provider}`}>{trace.ocr_label}</span>
              )}
              <span className={`badge ${trace.status === "done" ? "ok" : "warn"}`}>
                {trace.status}
              </span>
            </div>
            {trace.applicant_name && (
              <p className="muted detail-sub">Người làm thủ tục: {trace.applicant_name}</p>
            )}
          </div>

          <section className="panel detail-section">
            <dl className="meta meta-3">
              <div>
                <dt>Phường</dt>
                <dd>{trace.name || (trace.experience === "handfree" ? "—" : trace.username) || "—"}</dd>
              </div>
              <div>
                <dt>Tài khoản</dt>
                <dd>{trace.username || "—"}</dd>
              </div>
              <div>
                <dt>Thời gian</dt>
                <dd>{fmtDateTime(trace.created_at)}</dd>
              </div>
              <div>
                <dt>Loại</dt>
                <dd>{trace.experience === "handfree" ? "Handfree" : "No handfree"}</dd>
              </div>
              <div>
                <dt>Thao tác</dt>
                <dd>{trace.kind === "attach" ? "Đính kèm" : "Auto-fill"}</dd>
              </div>
              <div>
                <dt>Số trường điền</dt>
                <dd>{trace.fields_count}</dd>
              </div>
              {trace.kind !== "attach" && (
                <div>
                  <dt>Trường then chốt (bóc tách được)</dt>
                  <dd>{`${trace.key_fields_filled ?? 0}/${trace.key_fields_total ?? 0}`}</dd>
                </div>
              )}
              {trace.stats && (
                <>
                  <div>
                    <dt>Thời gian OCR</dt>
                    <dd>{fmtMs(trace.stats.ocr_latency_ms)}</dd>
                  </div>
                  <div>
                    <dt>Thời gian LLM</dt>
                    <dd>{fmtMs(trace.stats.llm_latency_ms)}</dd>
                  </div>
                  <div>
                    <dt>Tổng xử lý (server)</dt>
                    <dd>{fmtMs(trace.stats.total_latency_ms)}</dd>
                  </div>
                </>
              )}
              {trace.total_bytes != null && (
                <div>
                  <dt>Dung lượng hồ sơ</dt>
                  <dd>{fmtBytes(trace.total_bytes)}</dd>
                </div>
              )}
              <div>
                <dt>Mã request</dt>
                <dd className="mono">{trace.request_id}</dd>
              </div>
            </dl>
          </section>

          <div className="detail-cols">
            <section className="panel detail-section">
              <TraceFiles
                traceId={trace.id}
                attachments={trace.attachments ?? []}
                archiveName={`${trace.procedure}_${trace.request_id}`}
              />
            </section>

            <div className="detail-col-right">
              <section className="panel detail-section">
                <h3>Text OCR (gộp các file, ngăn bằng ---)</h3>
                <pre className="block ocr">{trace.ocr_text || "(không có)"}</pre>
              </section>
              <section className="panel detail-section">
                <h3>Output LLM parse được</h3>
                <pre className="block json">{llmText}</pre>
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
