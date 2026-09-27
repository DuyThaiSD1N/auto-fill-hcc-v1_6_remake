import { formatClock } from "../../format";
import type { RunDetail } from "../../types";
import Json from "./Json";
import { parseMaybeJson } from "./model";
import { DroppedTable, LlmCallHead, LlmOutputs, OcrFilesTable } from "./Parts";

function Layer({ tier, title, desc, open = true, children }: {
  tier: string; title: string; desc: string; open?: boolean; children: React.ReactNode;
}) {
  return (
    <details className="layer" open={open}>
      <summary><span className="layer__tier">{tier}</span><h2>{title}</h2><span className="layer__desc">{desc}</span></summary>
      <div className="layer__body">{children}</div>
    </details>
  );
}

/** Output theo tầng: T1 đầu vào → T2 LLM thô → T3 parse → T4 sau xử lý → T5 trả FE. */
export default function OutputLayers({ run }: { run: RunDetail }) {
  const { trace, steps } = run;
  const kind = steps?.kind ?? trace?.kind;
  const out = steps?.outputs ?? {};

  if (!steps) {
    // Lượt ghi trước khi bật bộ ghi: chỉ còn OCR gộp + một output cuối.
    return (
      <div className="layers">
        <p className="faint">Lượt này được ghi trước khi có bộ ghi công đoạn — chỉ còn dữ liệu cũ.</p>
        <Layer tier="T1" title="OCR" desc="text gộp mọi tệp"><Json value={trace?.ocr_text} tall empty="Không lưu OCR" /></Layer>
        <Layer tier={kind === "attach" ? "T4" : "T3"} title={kind === "attach" ? "Kế hoạch đính kèm cuối" : "Output LLM đã parse"}
               desc={kind === "attach" ? "sau luật của planner — không phải output LLM" : "JSON LLM trả về"}>
          <Json value={trace?.llm_output} tall />
        </Layer>
      </div>
    );
  }

  const calls = steps.llm ?? [];
  return (
    <div className="layers">
      <Layer tier="T1" title="Đầu vào" desc={`${steps.ocr?.length ?? 0} tệp OCR · prompt theo hash system`}>
        <OcrFilesTable files={steps.ocr ?? []} />
        {calls.length ? (
          <p className="muted">System prompt: {Array.from(new Set(calls.map((c) => `#${c.n} ${c.system_hash ?? "—"}`))).join(" · ")}</p>
        ) : null}
      </Layer>

      <Layer tier="T2·T3" title="LLM" desc={`${calls.length} lần gọi — JSON sau parse của từng lần (thô gập lại)`}>
        {calls.length ? calls.map((c) => (
          <div key={c.n} className="call-card">
            <LlmCallHead call={c} />
            <div style={{ padding: 10 }}><LlmOutputs call={c} /></div>
          </div>
        )) : <p className="faint">Lượt này không gọi LLM.</p>}
      </Layer>

      <Layer tier="T4" title="Sau xử lý" desc="lọc field, mapper, luật đính kèm, gán ô">
        {kind === "autofill" ? (
          <>
            <div className="section-title">Field bị loại khi lọc</div><DroppedTable dropped={out.validate_dropped} />
            <div className="section-title">Field sau lọc (trước mapper)</div><Json value={parseMaybeJson(out.fields_after_validate)} />
            {out.reasoning_context ? (<><div className="section-title">Suy luận vai trò</div><Json value={out.reasoning_context} /></>) : null}
          </>
        ) : null}
        {out.plan ? (<><div className="section-title">Kế hoạch đính kèm sau luật</div><Json value={out.plan} tall /></>) : null}
        {out.extracted ? (<><div className="section-title">extracted</div><Json value={out.extracted} /></>) : null}
        {out.classified ? (<><div className="section-title">Kết quả gán ô</div><Json value={out.classified} /></>) : null}
      </Layer>

      <Layer tier="T5" title="Trả FE" desc="đúng dữ liệu extension/sidebar nhận">
        <Json value={out.response} tall />
      </Layer>

      {trace?.report ? (
        <Layer tier="EXT" title="Kết quả trên cổng" desc={`extension báo lúc ${formatClock(String(trace.report.received_at ?? ""))}`} open={false}>
          <Json value={trace.report} />
        </Layer>
      ) : null}

      {steps.truncated?.length ? (
        <p className="faint">Đã cắt bớt: {steps.truncated.map((t) => `${t.path}${t.dropped ? " (bỏ)" : t.len ? ` (${t.len} ký tự)` : ""}`).join(", ")}</p>
      ) : null}
    </div>
  );
}
