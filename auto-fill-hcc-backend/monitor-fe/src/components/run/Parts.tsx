import { formatBytes, formatInt, formatMs } from "../../format";
import { CACHE_REASONS } from "../../stages";
import type { LlmCall, OcrFileRef } from "../../types";

const PURPOSE: Record<string, string> = {
  extract: "trích xuất", reason: "suy luận", plan: "lập kế hoạch", classify: "phân loại", intent: "hiểu ý", call: "gọi",
};

export function LlmCallMeta({ call }: { call: LlmCall }) {
  return (
    <>
      <dl className="kv">
        <dt>Mục đích</dt><dd>{PURPOSE[call.purpose] ?? call.purpose}</dd>
        <dt>Nơi gọi</dt><dd className="mono">{call.caller || "—"}</dd>
        <dt>Endpoint</dt><dd>{call.target ?? "—"} {call.model ? <span className="faint">· {call.model}</span> : null}</dd>
        <dt>Token</dt><dd className="mono">{formatInt(call.tokens_in)} vào → {formatInt(call.tokens_out)} ra (trần {formatInt(call.max_tokens)})</dd>
        <dt>Kết thúc</dt><dd>{call.finish_reason === "length" ? <b className="dropped">bị cắt do max_tokens</b> : call.finish_reason ?? "—"}</dd>
        <dt>Prompt</dt><dd className="mono">{formatInt(call.prompt_chars)} ký tự · system <span className="faint">{call.system_hash ?? "—"}</span></dd>
        {call.think_chars ? <><dt>&lt;think&gt;</dt><dd className="mono">{formatInt(call.think_chars)} ký tự</dd></> : null}
      </dl>
      {call.tries?.length ? (
        <>
          <div className="section-title">Các lần thử</div>
          <ul className="plain tries">
            {call.tries.map((t, i) => (
              <li key={i}>
                <span className={t.ok ? "outcome outcome--ok" : "outcome outcome--error"}>{t.ok ? "✓" : "✕"}</span>
                <span>{t.target}</span><span className="mono">{formatMs(t.ms)}</span>
                {t.error ? <span className="dropped">{t.error}</span> : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}

export function OcrFilesTable({ files }: { files: OcrFileRef[] }) {
  if (!files.length) return <p className="faint">Không có tệp OCR.</p>;
  return (
    <table className="mini-table">
      <thead><tr><th>Tệp</th><th>Nguồn</th><th className="right">Ký tự</th><th>Trang</th><th>Dung lượng</th></tr></thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.idx}>
            <td className="mono">#{f.idx + 1}{f.error ? <div className="dropped">{f.error}</div> : null}</td>
            <td>
              {f.cache === "hit" ? <span className="tag">cache</span>
                : f.cache === "docx" ? <span className="tag">DOCX</span>
                : <span className="tag">OCR{f.reason ? ` · ${CACHE_REASONS[f.reason] ?? f.reason}` : ""}</span>}
            </td>
            <td className="right mono">{formatInt(f.chars)}</td>
            <td className="mono">{f.pages ?? "—"}</td>
            <td className="mono">{formatBytes(f.bytes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
