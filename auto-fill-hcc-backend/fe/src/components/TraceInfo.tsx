import type { TraceDetail, TraceTiming } from "../types";
import { fmtBytes, fmtDateTime, fmtMs } from "../format";

// Thông tin MỘT lượt cho trang quản lý: ai, thủ tục gì, bao lâu, bao nhiêu tệp. KHÔNG có nội dung giấy
// tờ (text OCR, output LLM, tệp gốc, dữ liệu trả extension) — BE không trả các thứ đó cho admin; soi
// sâu một lượt thì dùng web Monitor. Trace cũ chỉ có `stats`; trace mới có thêm `timing` từng công đoạn.

const GROUPS: { key: "pre" | "ocr" | "llm" | "post"; label: string; color: string }[] = [
  { key: "pre", label: "Tiền xử lý", color: "#2f7bd0" },
  { key: "ocr", label: "OCR", color: "#c98217" },
  { key: "llm", label: "LLM", color: "#6e4bd6" },
  { key: "post", label: "Hậu xử lý", color: "#0b9384" },
];

// Tên bước theo mã của bộ ghi thời gian (app/monitor/recorder.py) — cùng bảng với monitor-fe/src/stages.ts.
const STEP_LABELS: Record<string, string> = {
  "pre.request": "Nhận request",
  "pre.receive": "Đọc tệp tải lên",
  "pre.prepare": "Chuẩn bị",
  "pre.load": "Nạp tệp của phiên",
  "pre.hash": "Băm tệp",
  "pre.decode": "Giải mã tệp",
  "pre.docx": "Tách DOCX",
  "pre.docx_images": "Ảnh trong DOCX",
  "ocr.call": "OCR",
  "ocr.cache": "Tra cache OCR",
  "ocr.remote": "Gọi OCR",
  "ocr.server": "Máy chủ OCR",
  "ocr.split": "Tách kết quả OCR",
  "llm.extract": "LLM trích xuất",
  "llm.reason": "LLM suy luận",
  "llm.plan": "LLM lập kế hoạch",
  "llm.classify": "LLM phân loại",
  "llm.intent": "LLM hiểu ý",
  "llm.call": "LLM",
  "post.parse": "Đọc JSON",
  "post.reason": "Suy luận vai trò",
  "post.fallback": "Vá kết quả",
  "post.validate": "Lọc field",
  "post.mapper": "Mapper thủ tục",
  "post.dates": "Chuẩn hoá ngày",
  "post.plan": "Luật đính kèm",
  "post.stt1": "STT1 ảo",
  "post.route": "Gán ô giấy tờ",
  "post.response": "Dựng response",
  "persist.files": "Lưu tệp",
  "persist.db": "Ghi DB",
  "persist.review": "Lưu rà soát",
  pipeline: "Pipeline thủ tục",
};

// timing.s lưu mã bước với "." đổi thành "_" (khoá Mongo) → đổi lại dấu đầu tiên: "llm_extract" → "llm.extract".
const stepCode = (key: string) => (STEP_LABELS[key] ? key : key.replace("_", "."));

const OUTCOME: Record<string, { label: string; cls: string }> = {
  ok: { label: "Thành công", cls: "ok" },
  partial: { label: "Có lỗi một phần", cls: "warn" },
  error: { label: "Lỗi", cls: "warn" },
};

function Timing({ timing, outcome }: { timing: TraceTiming; outcome?: string | null }) {
  const wait = timing.wait ?? 0;
  const parts = [
    ...GROUPS.map((g) => ({ ...g, ms: timing.g?.[g.key] ?? 0 })),
    { key: "other", label: "Chưa đo", color: "", ms: timing.other ?? 0 },
  ].filter((p) => p.ms > 0);
  const n = timing.n ?? {};
  const steps = Object.entries(timing.s ?? {})
    .map(([key, ms]) => [stepCode(key), ms] as const)
    .filter(([name, ms]) => ms > 0 && name !== "pipeline")
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const o = outcome ? OUTCOME[outcome] : undefined;

  return (
    <section className="trace-timing">
      <h3>Thời gian từng công đoạn</h3>
      <div className="trace-timing__head">
        <div>
          <span className="trace-timing__wait">{fmtMs(wait)}</span>
          <span className="muted"> người dùng chờ</span>
        </div>
        {o ? <span className={`badge ${o.cls}`}>{o.label}</span> : null}
      </div>
      {wait > 0 && parts.length ? (
        <>
          <div className="stage-bar" role="img" aria-label={parts.map((p) => `${p.label} ${fmtMs(p.ms)}`).join(", ")}>
            {parts.map((p) => (
              <span key={p.key} className={p.color ? undefined : "stage-bar__other"}
                style={{ width: `${(p.ms / wait) * 100}%`, background: p.color || undefined }} />
            ))}
          </div>
          <ul className="stage-legend">
            {parts.map((p) => (
              <li key={p.key}>
                <i className={p.color ? undefined : "stage-bar__other"} style={{ background: p.color || undefined }} />
                {p.label} <b>{fmtMs(p.ms)}</b> <span className="muted">({Math.round((p.ms / wait) * 100)}%)</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <dl className="meta meta-3 trace-timing__meta">
        <div><dt>Số lần gọi LLM</dt><dd>{n.llm_calls ?? 0}</dd></div>
        {n.tok_in || n.tok_out ? <div><dt>Token LLM (vào → ra)</dt><dd>{(n.tok_in ?? 0).toLocaleString("vi-VN")} → {(n.tok_out ?? 0).toLocaleString("vi-VN")}</dd></div> : null}
        {n.ocr_hit || n.ocr_miss ? <div><dt>Tệp OCR (gọi mới / dùng lại)</dt><dd>{n.ocr_miss ?? 0} / {n.ocr_hit ?? 0}</dd></div> : null}
        {timing.persist_wait ? <div><dt>Ghi DB trong lúc chờ</dt><dd>{fmtMs(timing.persist_wait)}</dd></div> : null}
      </dl>
      {steps.length ? (
        <table className="trace-steps">
          <thead><tr><th>Bước lâu nhất</th><th className="num">Thời gian</th></tr></thead>
          <tbody>
            {steps.map(([name, ms]) => (
              <tr key={name}>
                <td>{STEP_LABELS[name] ?? name} <code>{name}</code></td>
                <td className="num">{fmtMs(ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}

export default function TraceInfo({ trace, wide = false }: { trace: TraceDetail; wide?: boolean }) {
  const files = trace.attachments ?? [];
  return (
    <>
      <dl className={`meta${wide ? " meta-3" : ""}`}>
        <div>
          <dt>Phường</dt>
          <dd>{trace.name || (trace.experience === "handfree" ? "—" : trace.username) || "—"}</dd>
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

      {trace.timing ? <Timing timing={trace.timing} outcome={trace.outcome} /> : null}

      <section className="trace-files-names">
        <h3>File đính kèm ({files.length})</h3>
        {files.length ? (
          <ul>
            {files.map((f, i) => <li key={`${i}-${f.name}`}>{f.name || "(không tên)"}</li>)}
          </ul>
        ) : <p className="muted">Không có tệp.</p>}
      </section>
    </>
  );
}
