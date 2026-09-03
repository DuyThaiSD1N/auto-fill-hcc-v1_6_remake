// Biểu đồ tự vẽ bằng SVG/CSS — không thư viện. Adapt từ dashboard-bao-cao-tro-ly.html (thiết kế công báo).
import { useMemo, type CSSProperties } from "react";
import type { DayStat } from "./api";

// Bảng màu phân loại dùng chung cho donut, xếp hạng và bảng (khớp --p1..--p14 trong CSS).
export const PAL = [
  "#1256C7", "#0E8A45", "#C07C00", "#6D3AA8", "#0E7490", "#C8203F", "#C2410C",
  "#3F51B5", "#0891B2", "#65A30D", "#B45309", "#7C3AED", "#0F766E", "#BE123C",
];
export const PALBG = [
  "#EAF1FD", "#E7F6ED", "#FDF3E0", "#F2ECFB", "#E5F4F8", "#FDEDF0", "#FDF0E8",
  "#EDEFFA", "#E4F5F9", "#F0F7E4", "#FBF2E3", "#F3EDFD", "#E6F4F2", "#FDECF0",
];
const REST_COLOR = "#9AA7BA";

export const fmt = (n: number) => Math.round(n).toLocaleString("vi-VN");
const DOW_VI = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

// ── Cơ cấu theo thủ tục (donut nhỏ + chú giải) ───────────────────────────────
export interface Slice {
  label: string;
  count: number;
  color: string;
}

export function buildSlices(items: { label: string; count: number }[], maxSlices = 5): Slice[] {
  const sorted = [...items].filter((i) => i.count > 0).sort((a, b) => b.count - a.count);
  if (sorted.length <= maxSlices + 1) {
    return sorted.map((s, i) => ({ ...s, color: PAL[i % PAL.length] }));
  }
  const head = sorted.slice(0, maxSlices).map((s, i) => ({ ...s, color: PAL[i % PAL.length] }));
  const restCount = sorted.slice(maxSlices).reduce((a, b) => a + b.count, 0);
  return [...head, { label: "Thủ tục khác", count: restCount, color: REST_COLOR }];
}

export function DonutMini({ slices, total, procTypes }: { slices: Slice[]; total: number; procTypes: number }) {
  const size = 118;
  const sw = 20;
  const R = (size - sw) / 2;
  const C = 2 * Math.PI * R;
  let off = 0;
  const rings = slices.map((s, i) => {
    const len = total ? (C * s.count) / total : 0;
    const el = (
      <circle
        key={i}
        cx={size / 2}
        cy={size / 2}
        r={R}
        fill="none"
        stroke={s.color}
        strokeWidth={sw}
        strokeDasharray={`${len.toFixed(2)} ${(C - len).toFixed(2)}`}
        strokeDashoffset={(-off).toFixed(2)}
      >
        <title>{`${s.label}: ${fmt(s.count)}`}</title>
      </circle>
    );
    off += len;
    return el;
  });
  return (
    <div className="cb2">
      <div className="mini-donut">
        <div className="mdwrap" style={{ width: size, height: size }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <circle cx={size / 2} cy={size / 2} r={R} fill="none" stroke="#F0F3F8" strokeWidth={sw} />
            {rings}
          </svg>
          <div className="mdc">
            <b className="num">{fmt(procTypes)}</b>
            <span>Thủ tục</span>
          </div>
        </div>
        <div className="lgd">
          {slices.map((s, i) => (
            <div className="r" key={i} title={s.label}>
              <span className="sw" style={{ background: s.color }} />
              <span className="nm">{s.label}</span>
              <span className="n num">{fmt(s.count)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Diễn biến theo ngày (cột + lưới + đường trung bình) ───────────────────────
function dayParts(date: string): { dd: string; dow: string; weekend: boolean } {
  const [y, m, d] = date.split("-").map(Number);
  const dt = new Date(y, (m || 1) - 1, d || 1);
  const wd = dt.getDay();
  return { dd: String(d).padStart(2, "0"), dow: DOW_VI[wd], weekend: wd === 0 || wd === 6 };
}

export function BarDays({ data }: { data: DayStat[] }) {
  const series = data.map((d) => d.count);
  const max = Math.max(...series, 1);
  const step = Math.max(1, Math.ceil(max / 4 / 5) * 5);
  const top = Math.ceil(max / step) * step || 1;
  const work = series.filter((v) => v > 0);
  const avg = work.length ? work.reduce((a, b) => a + b, 0) / work.length : 0;

  const gl: JSX.Element[] = [];
  for (let v = top; v >= 0; v -= step) {
    gl.push(
      <i key={`g${v}`} className={v === 0 ? "zero" : ""} style={{ top: `${(1 - v / top) * 100}%` }}>
        <span>{fmt(v)}</span>
      </i>,
    );
  }
  if (avg > 0) {
    gl.push(
      <i key="avg" className="avg" style={{ top: `${(1 - avg / top) * 100}%` }}>
        <span>TB {fmt(avg)}/ngày</span>
      </i>,
    );
  }
  return (
    <div className="cb2">
      <div className="chart">
        <div className="gl">{gl}</div>
        <div className="bars">
          {data.map((d) => {
            const { dd, dow, weekend } = dayParts(d.date);
            const v = d.count;
            return (
              <div
                className={`dcol ${weekend ? "we" : ""} ${v === max && v > 0 ? "peak" : ""}`}
                key={d.date}
                title={`${dd}/${dow}: ${fmt(v)} hồ sơ`}
              >
                <span className="vv num">{v ? fmt(v) : ""}</span>
                <span className="col" style={{ height: `${(v / top) * 100}%` }} />
                <span className="dd num">
                  {dd}
                  <em>{dow}</em>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Ngày cao điểm trong tuần (cộng dồn theo thứ) ──────────────────────────────
export function WeekColumns({ data }: { data: DayStat[] }) {
  const order = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const sums = useMemo(() => {
    const acc: Record<string, number> = {};
    for (const d of data) {
      const { dow } = dayParts(d.date);
      acc[dow] = (acc[dow] || 0) + d.count;
    }
    return order.map((k) => acc[k] || 0);
  }, [data]);
  const max = Math.max(...sums, 1);
  return (
    <div className="cb2">
      <div className="wk">
        {order.map((k, i) => {
          const v = sums[i];
          const hi = v === max && v > 0;
          const bg = hi
            ? "linear-gradient(180deg,#3B82E8,#1256C7)"
            : v
              ? `hsl(214 ${28 + (v / max) * 34}% ${88 - (v / max) * 22}%)`
              : "#EEF2F8";
          return (
            <div className={`d ${hi ? "hi" : ""}`} key={k} title={`${k}: ${fmt(v)} hồ sơ`}>
              <span className="vl num">{v ? fmt(v) : ""}</span>
              <span className="bx" style={{ height: `${(v / max) * 100}%`, ["--wc" as string]: bg } as CSSProperties} />
              <span className="dn">{k}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
