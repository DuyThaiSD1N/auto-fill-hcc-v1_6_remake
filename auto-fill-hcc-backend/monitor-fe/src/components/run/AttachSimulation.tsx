import type { RunDetail } from "../../types";
import { EmptyState } from "../Status";

interface PlanItem {
  fileIndex?: number; fileName?: string; componentName?: string; documentName?: string;
  target?: string; sourceFileIndexes?: number[]; sourceSegments?: { fileIndex: number; pageIndexes?: number[] }[];
}

const ROW = 56;

/** Mô phỏng đính kèm: tệp đầu vào → thành phần hồ sơ; tệp không đi đâu tô đỏ. */
export default function AttachSimulation({ run }: { run: RunDetail }) {
  const plan = ((run.steps?.outputs?.plan ?? (run.trace?.llm_output as { attachments?: unknown } | undefined)?.attachments) ?? []) as PlanItem[];
  const files = (run.trace?.attachments?.map((a) => a.name || "") ?? run.steps?.ocr?.map((o) => o.name || "") ?? []);
  if (!plan.length) return <EmptyState title="Lượt này không có kế hoạch đính kèm" />;

  const comps: string[] = [];
  const links: [number, number][] = [];
  for (const item of plan) {
    const comp = item.componentName || item.documentName || "(không tên)";
    if (!comps.includes(comp)) comps.push(comp);
    const ci = comps.indexOf(comp);
    const sources = item.sourceFileIndexes?.length ? item.sourceFileIndexes
      : item.sourceSegments?.length ? item.sourceSegments.map((s) => s.fileIndex)
      : typeof item.fileIndex === "number" ? [item.fileIndex] : [];
    for (const fi of sources) links.push([fi, ci]);
  }
  const used = new Set(links.map(([f]) => f));
  const height = Math.max(files.length, comps.length) * ROW;

  return (
    <div>
      <p className="muted" style={{ marginBottom: 10 }}>
        {files.length} tệp → {comps.length} thành phần · {files.filter((_, i) => !used.has(i)).length} tệp không được đính
      </p>
      <div className="sim">
        <div className="sim__col">
          {files.map((name, i) => (
            <div key={i} className={`sim__item${used.has(i) ? "" : " sim__item--miss"}`} style={{ minHeight: ROW - 8 }}>
              {name || `Tệp ${i + 1}`}<small>{used.has(i) ? `tệp #${i}` : "không đính vào đâu"}</small>
            </div>
          ))}
        </div>
        <svg viewBox={`0 0 140 ${height}`} height={height} preserveAspectRatio="none" aria-hidden="true">
          {links.map(([f, c], k) => (
            <path key={k} d={`M0 ${f * ROW + ROW / 2 - 4} C70 ${f * ROW + ROW / 2 - 4}, 70 ${c * ROW + ROW / 2 - 4}, 140 ${c * ROW + ROW / 2 - 4}`}
                  fill="none" stroke="var(--st-post)" strokeWidth="1.5" />
          ))}
        </svg>
        <div className="sim__col">
          {comps.map((comp, i) => {
            const items = plan.filter((p) => (p.componentName || p.documentName || "(không tên)") === comp);
            return (
              <div key={i} className="sim__item" style={{ minHeight: ROW - 8 }}>
                {comp}<small>{items.map((p) => p.documentName).filter(Boolean).join(" · ")}{items[0]?.target ? ` · ${items[0].target}` : ""}</small>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
