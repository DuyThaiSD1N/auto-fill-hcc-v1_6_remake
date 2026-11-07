import { findSim, loadSurveyForm } from "../../simulations/registry";
import { findComponentRow, type SjsComponent, type SjsPlanItem } from "../../simulations/surveyjs";
import { useAsync } from "../../hooks";
import type { RunDetail } from "../../types";
import { EmptyState, ErrorNotice, Spinner } from "../Status";

interface PlanItem extends SjsPlanItem {
  target?: string;
}

const ROW = 56;

function planOf(run: RunDetail): PlanItem[] {
  return ((run.steps?.outputs?.plan ?? (run.trace?.llm_output as { attachments?: unknown } | undefined)?.attachments) ?? []) as PlanItem[];
}

function filesOf(run: RunDetail): string[] {
  return run.trace?.attachments?.map((a) => a.name || "") ?? run.steps?.ocr?.map((o) => o.name || "") ?? [];
}

/** Tệp gốc của một mục kế hoạch + trang đã tách (nếu có). */
function sourcesOf(item: PlanItem): { fileIndex: number; pages?: number[] }[] {
  if (item.sourceSegments?.length) return item.sourceSegments.map((s) => ({ fileIndex: s.fileIndex, pages: s.pages ?? s.pageIndexes }));
  if (item.sourceFileIndexes?.length) return item.sourceFileIndexes.map((fileIndex) => ({ fileIndex }));
  return typeof item.fileIndex === "number" ? [{ fileIndex: item.fileIndex }] : [];
}

/** Bảng THÀNH PHẦN HỒ SƠ của Cổng DVC quốc gia mới: dòng cố định, tệp nạp qua nút "Tải lên file" của từng dòng.
 *  Dòng nhận tệp tính đúng như extension (findUploadRow): khớp tên dòng, không khớp thì tệp không lên. */
function PortalComponents({ components, plan, files }: { components: SjsComponent[]; plan: PlanItem[]; files: string[] }) {
  const byRow = components.map(() => [] as PlanItem[]);
  const lost: PlanItem[] = [];
  for (const item of plan) {
    const row = findComponentRow(components, item);
    if (row === null) lost.push(item);
    else byRow[row].push(item);
  }
  const used = new Set(plan.filter((p) => !lost.includes(p)).flatMap((p) => sourcesOf(p).map((s) => s.fileIndex)));
  const unused = files.map((name, i) => ({ name, i })).filter(({ i }) => !used.has(i));
  const fileName = (i: number) => files[i] || `Tệp ${i + 1}`;

  return (
    <div>
      <p className="muted" style={{ marginBottom: 10 }}>
        {files.length} tệp → {plan.length - lost.length} tệp đính · {byRow.filter((r) => r.length).length}/{components.length} dòng có tệp
        {unused.length ? <span className="ef-red"> · {unused.length} tệp không được đính</span> : null}
      </p>
      <div className="sjs-card">
        <h2 className="sjs-card__title">Thành phần hồ sơ</h2>
        <div className="table-wrap">
          <table className="sjs-comp">
            <thead>
              <tr><th>#</th><th>Thành phần hồ sơ</th><th>Bản chính</th><th>Bản sao</th><th>Tài liệu đính kèm</th></tr>
            </thead>
            <tbody>
              {components.map((comp, ri) => (
                <tr key={ri} className={byRow[ri].length ? "is-attached" : undefined}>
                  <td className="num">{ri + 1}</td>
                  <td>{comp.name}</td>
                  <td className="num">{comp.banChinh ?? 1}</td>
                  <td className="num">{comp.banSao ?? 0}</td>
                  <td>
                    {byRow[ri].length ? (
                      <ul className="sjs-files">
                        {byRow[ri].map((item, k) => (
                          <li key={k}>
                            <span className="sjs-files__name">📄 {item.documentName || item.fileName || "(không tên)"}</span>
                            <small>
                              ← {sourcesOf(item).map((s) => `${fileName(s.fileIndex)}${s.pages?.length ? ` (trang ${s.pages.map((p) => p + 1).join(", ")})` : ""}`).join(" + ")}
                            </small>
                          </li>
                        ))}
                      </ul>
                    ) : <span className="faint">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {lost.length ? (
        <div className="panel panel__body" style={{ marginTop: 12 }}>
          <div className="section-title ef-red">Mục kế hoạch không khớp dòng nào ({lost.length}) — extension báo "Không tìm thấy dòng đính kèm"</div>
          <ul className="ef-problems">
            {lost.map((item, k) => (
              <li key={k}><b>{item.documentName || item.fileName}</b> — dòng "{item.slotName || item.componentName || `#${(item.slotIndex ?? 0) + 1}`}"</li>
            ))}
          </ul>
        </div>
      ) : null}
      {unused.length ? (
        <div className="panel panel__body" style={{ marginTop: 12 }}>
          <div className="section-title ef-red">Tệp không đính vào đâu ({unused.length})</div>
          <ul className="ef-problems">
            {unused.map(({ name, i }) => <li key={i}>{name || `Tệp ${i + 1}`} <small className="faint">tệp #{i}</small></li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/** Sơ đồ chung: tệp đầu vào → thành phần hồ sơ; tệp không đi đâu tô đỏ. */
function LinkDiagram({ plan, files }: { plan: PlanItem[]; files: string[] }) {
  const comps: string[] = [];
  const links: [number, number][] = [];
  for (const item of plan) {
    const comp = item.componentName || item.documentName || "(không tên)";
    if (!comps.includes(comp)) comps.push(comp);
    const ci = comps.indexOf(comp);
    for (const s of sourcesOf(item)) links.push([s.fileIndex, ci]);
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

/** Mô phỏng đính kèm: thủ tục có mẫu bảng thành phần của cổng → dựng bảng như cổng; còn lại → sơ đồ tệp → thành phần. */
export default function AttachSimulation({ run }: { run: RunDetail }) {
  const procedure = run.trace?.procedure ?? (run.steps?.meta?.procedure as string | undefined);
  const entry = findSim(procedure);
  const plan = planOf(run);
  const files = filesOf(run);
  // Kế hoạch của Cổng DVC quốc gia mới nhắm dòng cố định (target "fixed-slot" + slotName). Lượt cũ cùng mã thủ tục
  // (eForm moj: dòng có sẵn / thêm thành phần mới) không khớp bảng cổng mới → giữ sơ đồ chung.
  const portal = !!entry?.surveyjs && plan.some((p) => p.target === "fixed-slot" || !!p.slotName);
  const { data, error, loading, reload } = useAsync(
    async () => (portal && entry?.surveyjs ? (await loadSurveyForm(entry.surveyjs)).components ?? null : null),
    `attach-${entry?.key ?? "none"}:${portal ? "sjs" : "chung"}`,
  );
  if (!plan.length) return <EmptyState title="Lượt này không có kế hoạch đính kèm" />;
  if (!portal) return <LinkDiagram plan={plan} files={files} />;
  if (error) return <ErrorNotice message={error} onRetry={reload} />;
  if (loading) return <Spinner label="Đang tải mẫu thành phần hồ sơ" />;
  return data?.length ? <PortalComponents components={data} plan={plan} files={files} /> : <LinkDiagram plan={plan} files={files} />;
}
