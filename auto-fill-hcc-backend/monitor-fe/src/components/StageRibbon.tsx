import { formatMs } from "../format";
import { GROUPS, type Group } from "../stages";
import type { Timing } from "../types";

interface Seg { key: Group; ms: number }

/** Các đoạn theo thứ tự cố định; "Ghi DB" chỉ tính phần nằm TRONG thời gian chờ. */
export function ribbonSegments(timing: Timing | null | undefined, { includePersist = true } = {}): Seg[] {
  if (!timing) return [];
  const g = timing.g ?? {};
  const segs: Seg[] = [
    { key: "pre", ms: g.pre ?? 0 },
    { key: "ocr", ms: g.ocr ?? 0 },
    { key: "llm", ms: g.llm ?? 0 },
    { key: "post", ms: g.post ?? 0 },
    { key: "persist", ms: includePersist ? timing.persist_wait ?? 0 : 0 },
    { key: "other", ms: timing.other ?? 0 },
  ];
  return segs.filter((s) => s.ms > 0);
}

const LABEL: Record<Group, string> = Object.fromEntries(GROUPS.map((g) => [g.key, g.label])) as Record<Group, string>;

/** Băng công đoạn — thời gian một lượt chia theo nhóm, cùng màu ở mọi màn. */
export default function StageRibbon({
  timing, legacyMs, large = false, scaleMs,
}: { timing?: Timing | null; legacyMs?: number | null; large?: boolean; scaleMs?: number }) {
  const segs = ribbonSegments(timing);
  const total = segs.reduce((sum, s) => sum + s.ms, 0);
  const cls = `ribbon${large ? " ribbon--lg" : ""}`;
  if (!total) {
    if (legacyMs) {
      return (
        <span className={cls} title={`Dữ liệu cũ: chỉ có tổng OCR + LLM ${formatMs(legacyMs)}`}>
          <span className="ribbon__seg st-legacy" style={{ width: "100%" }} />
        </span>
      );
    }
    return <span className={cls} aria-hidden="true" />;
  }
  // scaleMs: cùng thang cho nhiều dòng (dòng dài hơn = chậm hơn); không có thì lấp đầy.
  const base = scaleMs && scaleMs > total ? scaleMs : total;
  const summary = segs.map((s) => `${LABEL[s.key]} ${formatMs(s.ms)}`).join(" · ");
  return (
    <span className={cls} role="img" aria-label={summary} title={summary}>
      {segs.map((s) => (
        <span key={s.key} className={`ribbon__seg st-${s.key}`} style={{ width: `${(s.ms / base) * 100}%` }} />
      ))}
    </span>
  );
}

export function RibbonLegend({ timing }: { timing?: Timing | null }) {
  const segs = ribbonSegments(timing);
  const persistBg = timing && !timing.persist_wait && timing.persist ? timing.persist : 0;
  return (
    <div className="ribbon-legend">
      {segs.map((s) => (
        <span key={s.key}>
          <i className={`swatch st-${s.key}`} />
          {LABEL[s.key]} <b>{formatMs(s.ms)}</b>
          {s.key === "llm" && timing?.n?.llm_calls ? <span className="faint">({timing.n.llm_calls} lần)</span> : null}
        </span>
      ))}
      {persistBg ? (
        <span title="Ghi DB chạy nền sau khi đã trả kết quả — không tính vào thời gian chờ">
          <i className="swatch st-persist" /> Ghi DB nền <b>{formatMs(persistBg)}</b>
        </span>
      ) : null}
    </div>
  );
}
