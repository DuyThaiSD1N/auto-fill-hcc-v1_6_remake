import { useEffect, useMemo, useRef } from "react";
import { formatMs } from "../../format";
import { stepLabel } from "../../stages";
import { barClass, type FlatSpan } from "./model";

function ticks(total: number): number[] {
  if (total <= 0) return [];
  const step = [100, 250, 500, 1000, 2000, 5000, 10000, 20000, 30000, 60000].find((s) => total / s <= 6) ?? 120000;
  const out: number[] = [];
  // Bỏ vạch sát mép phải để nhãn không tràn/xuống dòng.
  for (let t = step; t < total * 0.9; t += step) out.push(t);
  return out;
}

// Lượt gọi ra dịch vụ ngoài (mỗi span llm.* là một lần gọi LLM; ocr.remote là một lần gọi OCR cho một tệp) —
// là chỗ tốn thời gian chính nên in đậm cho dễ dò.
const isCall = (name: string) => name === "ocr.remote" || name.startsWith("llm.");

/** Waterfall: trục thời gian chung, cây cha–con thụt lề, ↑/↓ để chọn bước. */
export default function Waterfall({ spans, waitMs, selected, onSelect }: {
  spans: FlatSpan[]; waitMs?: number | null; selected: number | null; onSelect: (id: number) => void;
}) {
  const total = useMemo(() => Math.max(1, waitMs ?? 0, ...spans.map((s) => s.t0 + s.ms)), [spans, waitMs]);
  const rows = useRef<Record<number, HTMLButtonElement | null>>({});

  useEffect(() => {
    if (selected !== null) rows.current[selected]?.focus({ preventScroll: true });
  }, [selected]);

  function onKey(event: React.KeyboardEvent, index: number) {
    const next = event.key === "ArrowDown" ? index + 1 : event.key === "ArrowUp" ? index - 1 : -1;
    if (next < 0 || next >= spans.length) return;
    event.preventDefault();
    onSelect(spans[next].i);
  }

  const pos = (ms: number) => `${(ms / total) * 100}%`;
  return (
    <div className="wf" role="listbox" aria-label="Các bước theo thời gian">
      <div className="wf__axis" aria-hidden="true">
        <span>Bước</span>
        <span className="wf__ticks">
          <span style={{ left: 0, transform: "none" }}>0</span>
          {ticks(total).map((t) => <span key={t} style={{ left: pos(t) }}>{formatMs(t)}</span>)}
        </span>
        <span style={{ textAlign: "right" }}>Thời gian</span>
      </div>
      {spans.map((s, index) => {
        const cls = barClass(s.n);
        return (
          <button
            key={s.i}
            ref={(el) => { rows.current[s.i] = el; }}
            type="button"
            role="option"
            className={`wf__row${isCall(s.n) ? " wf__row--call" : ""}`}
            aria-selected={selected === s.i}
            tabIndex={selected === s.i ? 0 : -1}
            onClick={() => onSelect(s.i)}
            onKeyDown={(e) => onKey(e, index)}
          >
            <span className="wf__name" style={{ paddingLeft: s.depth * 14 }}>
              <em>{stepLabel(s.n)}{typeof s.a?.n === "number" && s.n.startsWith("llm.") ? ` #${s.a.n}` : ""}</em>
              <code>{s.n}</code>
            </span>
            <span className="wf__track">
              {waitMs ? <span className="wf__wait" style={{ left: pos(waitMs) }} title="Kết quả tới người dùng" /> : null}
              <span
                className={`wf__bar ${cls || "wf__bar--group"}${s.hasChildren && cls ? " wf__bar--container" : ""}${s.st === "error" ? " wf__bar--error" : ""}`}
                style={{ left: pos(s.t0), width: pos(Math.max(s.ms, total * 0.002)) }}
                title={s.hasChildren ? `Tổng ${formatMs(s.ms)} · riêng ${formatMs(s.ownMs)}` : undefined}
              />
            </span>
            <span className="wf__ms">{formatMs(s.ms)}</span>
          </button>
        );
      })}
    </div>
  );
}
