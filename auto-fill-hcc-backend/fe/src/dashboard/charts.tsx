// Biểu đồ tự vẽ bằng SVG — không dùng thư viện, để kiểm soát trọn vẹn thẩm mỹ (sơn mài).
import { useMemo } from "react";

// Bảng màu phân loại theo tinh thần sơn mài: son, ngọc bích, vàng, mực-xám, cánh gián, ngọc nhạt.
export const CATEGORICAL = [
  "#C4342B", // son (cinnabar)
  "#2E6E5B", // ngọc bích (jade)
  "#C89B3C", // vàng (gilt)
  "#4A5072", // mực xám (ink-slate)
  "#A8683E", // cánh gián (clay)
  "#5C9A86", // ngọc nhạt
];
const REST_COLOR = "#9AA0AE";

const fmt = (n: number) => n.toLocaleString("vi-VN");

// ── Donut cơ cấu thủ tục ─────────────────────────────────────────────────────
export interface DonutSlice {
  label: string;
  count: number;
  color: string;
}

export function buildSlices(items: { label: string; count: number }[], maxSlices = 5): DonutSlice[] {
  const sorted = [...items].filter((i) => i.count > 0).sort((a, b) => b.count - a.count);
  if (sorted.length <= maxSlices) {
    return sorted.map((s, i) => ({ ...s, color: CATEGORICAL[i % CATEGORICAL.length] }));
  }
  const head = sorted.slice(0, maxSlices).map((s, i) => ({ ...s, color: CATEGORICAL[i % CATEGORICAL.length] }));
  const restCount = sorted.slice(maxSlices).reduce((a, b) => a + b.count, 0);
  return [...head, { label: "Thủ tục khác", count: restCount, color: REST_COLOR }];
}

export function Donut({ slices, total }: { slices: DonutSlice[]; total: number }) {
  const R = 60;
  const C = 2 * Math.PI * R;
  const segments = useMemo(() => {
    let acc = 0;
    return slices.map((s) => {
      const frac = total > 0 ? s.count / total : 0;
      const seg = { ...s, len: frac * C, offset: -acc * C };
      acc += frac;
      return seg;
    });
  }, [slices, total, C]);

  return (
    <div className="donut-wrap">
      <div className="donut-fig">
        <svg viewBox="0 0 160 160" className="donut" role="img" aria-label="Cơ cấu thủ tục">
          <g transform="rotate(-90 80 80)">
            <circle cx="80" cy="80" r={R} fill="none" stroke="var(--hairline)" strokeWidth="22" />
            {segments.map((s, i) => (
              <circle
                key={s.label}
                cx="80"
                cy="80"
                r={R}
                fill="none"
                stroke={s.color}
                strokeWidth="22"
                strokeDasharray={`${Math.max(s.len - 1.5, 0)} ${C}`}
                strokeDashoffset={s.offset}
                strokeLinecap="butt"
                className="donut-seg"
                style={{ animationDelay: `${i * 90}ms` }}
              />
            ))}
          </g>
          <text x="80" y="74" className="donut-total">
            {fmt(total)}
          </text>
          <text x="80" y="94" className="donut-cap">
            hồ sơ
          </text>
        </svg>
      </div>
      <ul className="legend">
        {slices.map((s) => (
          <li key={s.label}>
            <span className="legend-dot" style={{ background: s.color }} aria-hidden="true" />
            <span className="legend-label" title={s.label}>
              {s.label}
            </span>
            <span className="legend-val">{fmt(s.count)}</span>
            <span className="legend-pct">{total > 0 ? Math.round((s.count / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Xếp hạng theo thủ tục (thanh ngang) ──────────────────────────────────────
export function RankBars({ items }: { items: { key: string; label: string; count: number }[] }) {
  const max = items[0]?.count ?? 0;
  return (
    <div className="rank">
      {items.map((p, i) => (
        <div className={`rank-row ${i === 0 ? "lead" : ""}`} key={p.key}>
          <span className="rank-idx">{i + 1}</span>
          <span className="rank-label" title={p.label}>
            {p.label}
          </span>
          <span className="rank-track">
            <span className="rank-fill" style={{ width: `${max ? (p.count / max) * 100 : 0}%` }} />
          </span>
          <span className="rank-val">{fmt(p.count)}</span>
        </div>
      ))}
    </div>
  );
}

// ── Diễn biến theo ngày (cột) ────────────────────────────────────────────────
const dm = (iso: string) => {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
};

export function DayColumns({ data }: { data: { date: string; count: number }[] }) {
  const max = data.reduce((m, d) => Math.max(m, d.count), 0);
  const W = 640;
  const H = 200;
  const padB = 26;
  const padT = 12;
  const n = data.length;
  const gap = n > 1 ? Math.min(10, 360 / n) : 0;
  const colW = n > 0 ? Math.max(6, (W - gap * (n - 1)) / n) : 0;
  const plotH = H - padB - padT;

  return (
    <div className="cols-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="cols" preserveAspectRatio="none" role="img" aria-label="Lượt hồ sơ theo ngày">
        <line x1="0" y1={H - padB} x2={W} y2={H - padB} stroke="var(--hairline)" strokeWidth="1" />
        {data.map((d, i) => {
          const h = max > 0 ? (d.count / max) * plotH : 0;
          const x = i * (colW + gap);
          const y = H - padB - h;
          return (
            <g key={d.date} className="col-g">
              <title>{`${dm(d.date)}: ${fmt(d.count)} hồ sơ`}</title>
              <rect
                x={x}
                y={y}
                width={colW}
                height={Math.max(h, d.count > 0 ? 2 : 0)}
                rx={Math.min(3, colW / 2)}
                className="col-bar"
                style={{ transformOrigin: `${x + colW / 2}px ${H - padB}px`, animationDelay: `${i * 20}ms` }}
              />
            </g>
          );
        })}
      </svg>
      <div className="cols-axis">
        {n > 0 && <span>{dm(data[0].date)}</span>}
        {n > 2 && <span>{dm(data[Math.floor((n - 1) / 2)].date)}</span>}
        {n > 1 && <span>{dm(data[n - 1].date)}</span>}
      </div>
    </div>
  );
}
