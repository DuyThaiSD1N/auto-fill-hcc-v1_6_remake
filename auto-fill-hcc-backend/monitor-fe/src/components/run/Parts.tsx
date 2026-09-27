import { useEffect, useState } from "react";
import { getOcrText } from "../../api";
import { formatBytes, formatInt, formatMs, safeJson } from "../../format";
import CopyButton from "../CopyButton";
import { CACHE_REASONS, DROP_REASONS } from "../../stages";
import type { LlmCall, OcrFileRef } from "../../types";
import Json from "./Json";
import { parseMaybeJson, show } from "./model";

const PURPOSE: Record<string, string> = {
  extract: "trích xuất", reason: "suy luận", plan: "lập kế hoạch", classify: "phân loại", intent: "hiểu ý", call: "gọi",
};

export function LlmCallHead({ call }: { call: LlmCall }) {
  return (
    <div className="call-card__head">
      <b>LLM #{call.n} — {PURPOSE[call.purpose] ?? call.purpose}</b>
      <span className="mono">{formatMs(call.ms)}</span>
      <span className="muted">{call.target ?? "—"}{call.model ? ` · ${call.model}` : ""}</span>
      <span className="mono muted">{formatInt(call.tokens_in)} → {formatInt(call.tokens_out)} token</span>
      {call.finish_reason ? (
        <span className={call.finish_reason === "length" ? "outcome outcome--error" : "muted"}>
          {call.finish_reason === "length" ? "bị cắt do max_tokens" : call.finish_reason}
        </span>
      ) : null}
      {call.error ? <span className="outcome outcome--error">{call.error}</span> : null}
    </div>
  );
}

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

/**
 * Phần LLM viết NGOÀI khối JSON (lời giải thích, <think>…) — thứ duy nhất parse thật sự bỏ đi.
 * Fence ```json và khoảng trắng chỉ là định dạng nên không tính.
 */
function textOutsideJson(raw: string | null | undefined): { think: string; extra: string } {
  if (!raw) return { think: "", extra: "" };
  const think = (raw.match(/<think>[\s\S]*?<\/think>/gi) ?? []).join("\n").replace(/<\/?think>/gi, "").trim();
  let rest = raw.replace(/<think>[\s\S]*?<\/think>/gi, "");
  const fence = rest.match(/```json\s*[\s\S]*?\s*```/i);
  if (fence) rest = rest.replace(fence[0], "");
  else {
    const start = rest.indexOf("{");
    const end = rest.lastIndexOf("}");
    if (start >= 0 && end > start) rest = rest.slice(0, start) + rest.slice(end + 1);
  }
  return { think, extra: rest.replace(/```/g, "").trim() };
}

/**
 * Output của một lần gọi LLM.
 * - Parse được: chỉ hiện JSON sau parse (bản thô gập lại); nếu LLM viết thêm ngoài JSON thì hiện
 *   riêng đúng phần đó.
 * - Parse lỗi / không trả JSON: hiện bản thô (và lỗi parse).
 */
/** Bản parse của lần gọi; thiếu (lần gọi không gắn được parse) thì tự parse chuỗi thô bỏ fence/think. */
function parsedOf(call: LlmCall): unknown {
  const parsed = parseMaybeJson(call.parsed);
  if (parsed !== undefined && parsed !== null) return parsed;
  if (!call.raw || call.parse_error) return undefined;
  const text = call.raw.replace(/<think>[\s\S]*?<\/think>/gi, "");
  const fence = text.match(/```json\s*([\s\S]*?)\s*```/i);
  const body = fence ? fence[1] : text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1);
  try { return body ? JSON.parse(body) : undefined; } catch { return undefined; }
}

export function LlmOutputs({ call }: { call: LlmCall }) {
  const parsed = parsedOf(call);
  const hasParsed = parsed !== undefined && parsed !== null && !call.parse_error;
  const raw = (
    <Json value={call.raw ?? null} verbatim empty="Không lưu output thô (lượt ghi ở chế độ summary hoặc bị lược vì quá lớn)" />
  );

  if (hasParsed) {
    const { think, extra } = textOutsideJson(call.raw);
    return (
      <div>
        <div className="section-title copy-row">Output (JSON sau parse) <CopyButton text={safeJson(parsed)} label="Sao chép JSON" /></div>
        <Json value={parsed} />
        {extra ? (<><div className="section-title">Phần LLM viết ngoài JSON (bị bỏ khi parse)</div><pre className="code">{extra}</pre></>) : null}
        {think ? (<><div className="section-title">&lt;think&gt; (bị bỏ khi parse)</div><pre className="code">{think}</pre></>) : null}
        <details>
          <summary className="faint" style={{ cursor: "pointer", marginTop: 6 }}>Xem output thô (nguyên văn)</summary>
          {call.raw ? <div className="copy-row" style={{ margin: "6px 0" }}><CopyButton text={call.raw} label="Sao chép output thô" /></div> : null}
          {raw}
        </details>
      </div>
    );
  }

  return (
    <div>
      <div className="section-title copy-row">Output thô <span className="faint">(nguyên văn LLM trả)</span>
        {call.raw ? <CopyButton text={call.raw} label="Sao chép" /> : null}</div>
      {call.parse_error ? <p className="dropped">Parse lỗi: {call.parse_error}</p> : null}
      {raw}
      {!call.parse_error ? <p className="faint">Lần gọi này không trả JSON — code tự đọc output thô (vd tách theo thẻ).</p> : null}
    </div>
  );
}

export function OcrFilesTable({ files }: { files: OcrFileRef[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!files.length) return <p className="faint">Không có tệp OCR.</p>;
  return (
    <>
      <table className="mini-table">
        <thead><tr><th>Tệp</th><th>Nguồn</th><th className="right">Ký tự</th><th>Trang</th><th>Dung lượng</th><th /></tr></thead>
        <tbody>
          {files.map((f) => (
            <tr key={f.idx}>
              <td>{f.name}{f.error ? <div className="dropped">{f.error}</div> : null}</td>
              <td>
                {f.cache === "hit" ? <span className="tag">cache</span>
                  : f.cache === "docx" ? <span className="tag">DOCX</span>
                  : <span className="tag">OCR{f.reason ? ` · ${CACHE_REASONS[f.reason] ?? f.reason}` : ""}</span>}
              </td>
              <td className="right mono">{formatInt(f.chars)}</td>
              <td className="mono">{f.pages ?? "—"}</td>
              <td className="mono">{formatBytes(f.bytes)}</td>
              <td><button className="btn btn--sm" type="button" onClick={() => setOpen(open === f.idx ? null : f.idx)}>{open === f.idx ? "Ẩn" : "Xem text"}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {open !== null ? <OcrText file={files.find((f) => f.idx === open)!} /> : null}
    </>
  );
}

export function OcrText({ file }: { file: OcrFileRef }) {
  const [text, setText] = useState<string | null>(file.text ?? null);
  const [err, setErr] = useState("");
  useEffect(() => {
    setText(file.text ?? null);
    setErr("");
    if (file.text || !file.sha256) return undefined;
    let active = true;
    getOcrText(file.sha256)
      .then((d) => { if (active) setText(d.text); })
      .catch((e) => { if (active) setErr(e instanceof Error ? e.message : String(e)); });
    return () => { active = false; };
  }, [file.sha256, file.text]);
  if (err) return <p className="dropped">{err}</p>;
  if (text === null) return <p className="faint">{file.sha256 ? "Đang tải text OCR…" : "Không lưu text OCR của tệp này."}</p>;
  return (
    <>
      <div className="section-title copy-row">Text OCR · {file.name} {text ? <CopyButton text={text} label="Sao chép text OCR" /> : null}</div>
      <pre className="code code--tall">{text || "(rỗng)"}</pre>
    </>
  );
}

export function DroppedTable({ dropped }: { dropped: unknown }) {
  const rows = Array.isArray(dropped) ? (dropped as { name: string; value: unknown; reason: string }[]) : [];
  if (!rows.length) return <p className="faint">Không field nào bị loại.</p>;
  return (
    <table className="mini-table">
      <thead><tr><th>Field LLM trả</th><th>Giá trị</th><th>Lý do bị loại</th></tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}><td className="mono">{r.name}</td><td>{show(r.value)}</td><td className="dropped">{DROP_REASONS[r.reason] ?? r.reason}</td></tr>
        ))}
      </tbody>
    </table>
  );
}
