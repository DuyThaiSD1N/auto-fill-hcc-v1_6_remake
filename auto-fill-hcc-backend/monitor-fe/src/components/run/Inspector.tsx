import { Fragment } from "react";
import { formatMs } from "../../format";
import { stepLabel } from "../../stages";
import type { SpanDoc, StepsDoc } from "../../types";
import Json from "./Json";
import { callForSpan, parseMaybeJson, type FlatSpan } from "./model";
import { DroppedTable, LlmCallMeta, LlmOutputs, OcrFilesTable } from "./Parts";

const HIDDEN_ATTRS = new Set(["n", "pages"]);

/** Khung phải của tab Công đoạn: đúng dữ liệu của bước đang chọn. */
export default function Inspector({ span, steps }: { span: SpanDoc | null; steps: StepsDoc }) {
  if (!span) return <div className="panel inspector"><div className="panel__body faint">Chọn một bước bên trái.</div></div>;
  const call = span.n.startsWith("llm.") || span.n === "post.parse" ? callForSpan(steps, span) : undefined;
  const attrs = Object.entries(span.a || {}).filter(([k]) => !HIDDEN_ATTRS.has(k));
  const out = steps.outputs || {};

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
            <LlmOutputs call={call} />
          </>
        ) : null}

        {["ocr.call", "ocr.cache", "ocr.remote", "ocr.split", "pre.hash", "pre.decode", "pre.docx"].includes(span.n) ? (
          <><div className="section-title">Tệp OCR</div><OcrFilesTable files={steps.ocr || []} /></>
        ) : null}

        {span.n === "post.validate" ? (
          <>
            <div className="section-title">Field bị loại</div>
            <DroppedTable dropped={out.validate_dropped} />
            <div className="section-title">Field sau khi lọc (trước mapper)</div>
            <Json value={parseMaybeJson(out.fields_after_validate)} />
          </>
        ) : null}

        {span.n === "post.reason" ? (<><div className="section-title">Kết quả suy luận vai trò</div><Json value={out.reasoning_context} empty="Không có ngữ cảnh suy luận" /></>) : null}
        {span.n === "post.mapper" ? (
          <>
            <div className="section-title">Trước mapper</div><Json value={parseMaybeJson(out.fields_after_validate)} />
            <div className="section-title">Sau mapper + chuẩn hoá ngày (trả FE)</div><Json value={(out.response as { fields?: unknown } | undefined)?.fields} />
          </>
        ) : null}
        {span.n === "post.plan" || span.n === "post.stt1" ? (<><div className="section-title">T4 · Kế hoạch đính kèm sau luật</div><Json value={out.plan} /></>) : null}
        {span.n === "post.route" ? (<><div className="section-title">T4 · Kết quả gán ô</div><Json value={out.classified} /></>) : null}
        {span.n === "post.response" || span.n === "pipeline" ? (<><div className="section-title">T5 · Trả FE</div><Json value={out.response} /></>) : null}
      </div>
    </div>
  );
}
