import { Fragment } from "react";
import { formatMs } from "../../format";
import { stepLabel } from "../../stages";
import type { SpanDoc, StepsDoc } from "../../types";
import { callForSpan, type FlatSpan } from "./model";
import { LlmCallMeta, OcrFilesTable } from "./Parts";

const HIDDEN_ATTRS = new Set(["n", "pages"]);

/** Khung phải của tab Công đoạn: đúng dữ liệu của bước đang chọn. */
export default function Inspector({ span, steps }: { span: SpanDoc | null; steps: StepsDoc }) {
  if (!span) return <div className="panel inspector"><div className="panel__body faint">Chọn một bước bên trái.</div></div>;
  const call = span.n.startsWith("llm.") || span.n === "post.parse" ? callForSpan(steps, span) : undefined;
  const attrs = Object.entries(span.a || {}).filter(([k]) => !HIDDEN_ATTRS.has(k));

  return (
    <div className="panel inspector" aria-live="polite">
      <div className="panel__head">
        <h2>{stepLabel(span.n)}{call ? ` #${call.n}` : ""}</h2>
        <code className="mono faint">{span.n}</code>
        <span className="mono" style={{ marginLeft: "auto" }}>{formatMs(span.ms)}</span>
      </div>
      <div className="panel__body">
        <dl className="kv">
          <dt>Bắt đầu</dt><dd className="mono">+{formatMs(span.t0)}</dd>
          {"hasChildren" in span && (span as FlatSpan).hasChildren ? (
            <><dt>Thời gian riêng</dt><dd className="mono">{formatMs((span as FlatSpan).ownMs)} <span className="faint">(không tính bước con)</span></dd></>
          ) : null}
          <dt>Trạng thái</dt><dd>{span.st === "error" ? <b className="dropped">lỗi</b> : span.st === "open" ? "chưa đóng" : "ok"}</dd>
          {attrs.map(([k, v]) => (
            <Fragment key={k}><dt>{k}</dt><dd className="mono">{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd></Fragment>
          ))}
        </dl>

        {call ? (
          <>
            <div className="section-title">Lần gọi LLM</div>
            <LlmCallMeta call={call} />
          </>
        ) : null}

        {["ocr.call", "ocr.cache", "ocr.remote", "ocr.split", "pre.hash", "pre.decode", "pre.docx"].includes(span.n) ? (
          <><div className="section-title">Tệp OCR</div><OcrFilesTable files={steps.ocr || []} /></>
        ) : null}

      </div>
    </div>
  );
}
