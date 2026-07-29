import { useEffect, useState } from "react";
import { getTrace } from "../api";
import type { TraceDetail } from "../types";
import { fmtBytes, fmtDateTime, fmtMs } from "../format";
import { goToTrace } from "../nav";
import TraceFiles from "./TraceFiles";

// Drawer XEM NHANH: liếc nhanh 1 trace. Muốn soi kỹ (file lớn, OCR/JSON rộng) → nút
// "Xem chi tiết" mở trang riêng #/trace/<id>.
export default function TraceDetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
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
    trace && trace.llm_output != null
      ? JSON.stringify(trace.llm_output, null, 2)
      : "(không có)";

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Chi tiết trace</h2>
          <div className="drawer-head-actions">
            <button className="btn-primary sm" onClick={() => goToTrace(id)}>
              Xem chi tiết →
            </button>
            <button className="ghost" onClick={onClose} aria-label="Đóng">
              ✕
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}
        {!trace && !error && <div className="muted">Đang tải…</div>}

        {trace && (
          <div className="drawer-body">
            <dl className="meta">
              <div>
                <dt>Phường</dt>
                <dd>{trace.name || trace.username || "—"}</dd>
              </div>
              <div>
                <dt>Tài khoản</dt>
                <dd>{trace.username || "—"}</dd>
              </div>
              <div>
                <dt>Thủ tục</dt>
                <dd>{trace.procedure_label || trace.procedure}</dd>
              </div>
              <div>
                <dt>Người làm thủ tục</dt>
                <dd>{trace.applicant_name || "—"}</dd>
              </div>
              <div>
                <dt>Model OCR</dt>
                <dd>{trace.ocr_label || "—"}</dd>
              </div>
              <div>
                <dt>Thời gian</dt>
                <dd>{fmtDateTime(trace.created_at)}</dd>
              </div>
              <div>
                <dt>Loại</dt>
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

            <TraceFiles
              traceId={trace.id}
              attachments={trace.attachments ?? []}
              archiveName={`${trace.procedure}_${trace.request_id}`}
            />

            <section>
              <h3>Text OCR (gộp các file, ngăn bằng ---)</h3>
              <pre className="block ocr">{trace.ocr_text || "(không có)"}</pre>
            </section>

            <section>
              <h3>Output LLM parse được</h3>
              <pre className="block json">{llmText}</pre>
            </section>
          </div>
        )}
      </aside>
    </div>
  );
}
