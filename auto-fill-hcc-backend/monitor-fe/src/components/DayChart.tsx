import { useEffect, useRef, useState } from "react";
import { formatMs } from "../format";
import type { LatencyRow, Metric } from "../types";

const SEGS = [
  { key: "preAvg", label: "Tiền xử lý", cls: "st-pre" },
  { key: "ocrAvg", label: "OCR", cls: "st-ocr" },
  { key: "llmAvg", label: "LLM", cls: "st-llm" },
  { key: "postAvg", label: "Hậu xử lý", cls: "st-post" },
  { key: "otherAvg", label: "Chưa đo", cls: "st-other" },
] as const;

const H = 240, PAD = { l: 52, r: 12, t: 12, b: 28 };

function niceMax(v: number): number {
  if (v <= 0) return 1000;
  const p = 10 ** Math.floor(Math.log10(v));
  const m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}

function dayLabel(key: string | null): string {
  const [, m, d] = String(key ?? "").split("-");
  return d && m ? `${d}/${m}` : String(key ?? "");
}

const SINGLE = {
  ocr: { key: "avg", label: "OCR", cls: "st-ocr" },
  llm: { key: "avg", label: "LLM", cls: "st-llm" },
} as const;

/**
 * Chỉ số "chờ": cột = thời gian chờ TRUNG BÌNH của ngày, chia theo công đoạn (tổng cột = trung bình).
 * Chỉ số OCR / LLM: cột một màu = trung bình của bước đó (chỉ lượt có chạy thật bước đó).
 */
export default function DayChart({ rows, metric = "wait" }: { rows: LatencyRow[]; metric?: Metric }) {
  const segs = metric === "wait" ? SEGS : [SINGLE[metric]];
  const [hover, setHover] = useState<number | null>(null);
  // Đo bề rộng thật của khung → viewBox khớp pixel, chữ trục không bị co giãn.
  const box = useRef<HTMLElement | null>(null);
  const [W, setW] = useState(760);
  useEffect(() => {
    const el = box.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setW(Math.max(320, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  if (!rows.length) return <p className="faint">Chưa có lượt nào có dữ liệu công đoạn trong khoảng này.</p>;

  const total = (r: LatencyRow) => segs.reduce((s, g) => s + (r[g.key] ?? 0), 0);
  const max = niceMax(Math.max(...rows.map(total)));
  const iw = W - PAD.l - PAD.r, ih = H - PAD.t - PAD.b;
  const bw = Math.max(6, Math.min(40, (iw / rows.length) * 0.62));
  const x = (i: number) => PAD.l + (iw / rows.length) * (i + 0.5);
  const y = (v: number) => PAD.t + ih - (v / max) * ih;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const cur = hover !== null ? rows[hover] : null;
  const top = cur && metric === "wait" ? [...SEGS].sort((a, b) => (cur[b.key] ?? 0) - (cur[a.key] ?? 0))[0] : null;
  const noun = metric === "wait" ? "chờ" : SINGLE[metric].label;

  return (
    <figure style={{ margin: 0 }} ref={box}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Thời gian chờ trung bình theo ngày, ${rows.length} ngày, chia theo công đoạn`}
           onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="grid-line" x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} />
            <text x={PAD.l - 6} y={y(t) + 3} textAnchor="end">{formatMs(t)}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          let acc = 0;
          return (
            <g key={r.key ?? i} opacity={hover === null || hover === i ? 1 : 0.55}>
              {segs.map((g) => {
                const v = r[g.key] ?? 0;
                if (v <= 0) return null;
                const t = y(acc + v), h = y(acc) - t;
                acc += v;
                // 1px khe giữa các đoạn chồng để phân biệt không cần dựa vào màu.
                return <rect key={g.key} className={g.cls} x={x(i) - bw / 2} y={t} width={bw} height={Math.max(0, h - 1)} rx={1.5} />;
              })}
              <rect x={x(i) - iw / rows.length / 2} y={PAD.t} width={iw / rows.length} height={ih} fill="transparent"
                    onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0}
                    aria-label={`${dayLabel(r.key)}: ${r.n} lượt, ${noun} trung bình ${formatMs(r.avg)}`} />
              {rows.length <= 16 || i % Math.ceil(rows.length / 12) === 0 ? (
                <text x={x(i)} y={H - 8} textAnchor="middle">{dayLabel(r.key)}</text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="ribbon-legend" aria-hidden="true">
        {segs.map((g) => <span key={g.key + g.label}><i className={`swatch ${g.cls}`} />{g.label}</span>)}
      </div>
      <div className="chart-tip" aria-live="polite">
        {cur ? (
          <span>
            Ngày <b>{dayLabel(cur.key)}</b>: <b className="num">{cur.n}</b> lượt, {noun} trung bình <b>{formatMs(cur.avg)}</b>
            {cur.slowest ? <>, lâu nhất <b>{formatMs(cur.slowest.ms)}</b></> : null}
            {top && cur[top.key] ? <> — phần lớn thời gian ở <b>{top.label}</b> ({formatMs(cur[top.key])})</> : null}.
          </span>
        ) : "Rê chuột (hoặc Tab) vào một ngày để xem số."}
      </div>
    </figure>
  );
}
