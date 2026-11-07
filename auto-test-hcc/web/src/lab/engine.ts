// Hiển thị kết quả các lần chạy lại của một ca: chấm từng lượt bằng engine mô phỏng form của Monitor và so giữa các lần.
import { findSim, loadAreaCatalog, loadForm, loadSurveyForm } from "../simulations/registry";
import { simulateEform, type SimStats } from "../simulations/eform";
import { findComponentRow, simulateSurveyJs, type SjsComponent, type SjsPlanItem } from "../simulations/surveyjs";
import { isSurveyJsOutput, toFields, type UiField } from "../simulations/fill";
import type { RunDetail, StepsDoc, TraceDoc } from "../types";

export interface BatchSettings {
  fill: boolean;
  attach: boolean;
  split: boolean;
  variant: string;
}

export interface StepResult {
  status: "ok" | "partial" | "error";
  ms: number;
  requestId?: string;
  response?: Record<string, unknown>;
  error?: string;
}

export type RunStatus = "queued" | "running" | "done" | "cancelled";

export interface LabRun {
  set: number;
  run: number;
  status: RunStatus;
  /** ISO — lúc lượt bắt đầu gọi máy chủ / lúc xong hoặc bị dừng. */
  startedAt?: string;
  finishedAt?: string;
  fill?: StepResult;
  attach?: StepResult;
}

/** Các lần chạy lại của một ca, mỗi đợt (trước sửa, sau sửa từng vòng) là một "bộ". */
export interface Batch {
  version: 1;
  id: string;
  procedure: string;
  label: string;
  account: string;
  createdAt: string;
  settings: BatchSettings;
  sets: { name: string; files: string[] }[];
  runs: LabRun[];
}

export const runKey = (r: { set: number; run: number }) => `${r.set}-${r.run}`;

// ---- chấm điểm ----------------------------------------------------------------------------------------------

export function runFields(run: LabRun): UiField[] {
  return toFields(run.fill?.response);
}

export function runPlan(run: LabRun): (SjsPlanItem & { target?: string })[] {
  const list = run.attach?.response?.attachments;
  return Array.isArray(list) ? (list as SjsPlanItem[]) : [];
}

/** RunDetail giả cho các component mô phỏng của Monitor (FormSimulation, AttachSimulation). */
export function asRunDetail(batch: Batch, run: LabRun): RunDetail {
  const files = batch.sets[run.set]?.files ?? [];
  return {
    trace: { id: "", request_id: run.fill?.requestId ?? "", procedure: batch.procedure, attachments: files.map((name) => ({ name })), created_at: batch.createdAt } as TraceDoc,
    steps: { meta: { procedure: batch.procedure }, outputs: { response: run.fill?.response, plan: runPlan(run) } } as unknown as StepsDoc,
  };
}

export interface Scorer {
  form: (fields: UiField[]) => SimStats | null;
  components: SjsComponent[] | null;
}

const scorers = new Map<string, Promise<Scorer>>();

/** Nạp mẫu form của thủ tục một lần, trả hàm chấm ô đỏ dùng chung cho mọi lượt. */
export function loadScorer(procedure: string): Promise<Scorer> {
  let hit = scorers.get(procedure);
  if (!hit) {
    hit = buildScorer(procedure);
    hit.catch(() => scorers.delete(procedure));
    scorers.set(procedure, hit);
  }
  return hit;
}

async function buildScorer(procedure: string): Promise<Scorer> {
  const entry = findSim(procedure);
  if (!entry) return { form: () => null, components: null };
  const [eforms, survey, area] = await Promise.all([
    Promise.all((entry.forms ?? []).map(loadForm)),
    entry.surveyjs ? loadSurveyForm(entry.surveyjs) : Promise.resolve(null),
    entry.surveyjs ? loadAreaCatalog() : Promise.resolve(null),
  ]);
  return {
    components: survey?.components ?? null,
    form: (fields) => {
      if (!fields.length) return null;
      // Cùng luật chọn mẫu với FormSimulation: output comp "sjs-*" → biểu mẫu SurveyJS, còn lại → eForm.
      if (survey && (isSurveyJsOutput(fields) || !eforms.length)) return simulateSurveyJs(survey, fields, area).stats;
      if (!eforms.length) return null;
      // Nhiều tờ khai: extension điền tờ đang mở = tờ nhận được nhiều field nhất.
      const sims = eforms.map((form) => simulateEform(form, fields));
      return sims.reduce((best, sim) => (sim.unmatched.length < best.unmatched.length ? sim : best)).stats;
    },
  };
}

export interface AttachScore {
  items: number;
  lost: number;
  unused: number;
  files: number;
}

export function scoreAttach(run: LabRun, files: number, components: SjsComponent[] | null): AttachScore | null {
  if (!run.attach || run.attach.status === "error") return null;
  const plan = runPlan(run);
  const lost = components?.length ? plan.filter((p) => findComponentRow(components, p) === null) : [];
  const used = new Set(
    plan.filter((p) => !lost.includes(p)).flatMap((p) =>
      p.sourceSegments?.length ? p.sourceSegments.map((s) => s.fileIndex) : p.sourceFileIndexes?.length ? p.sourceFileIndexes : typeof p.fileIndex === "number" ? [p.fileIndex] : []),
  );
  return { items: plan.length, lost: lost.length, unused: Array.from({ length: files }, (_, i) => i).filter((i) => !used.has(i)).length, files };
}

// ---- so sánh giữa các lần -------------------------------------------------------------------------------------

export function fieldKey(f: UiField & { occurrence?: number | null }): string {
  return f.occurrence ? `${f.name}#${f.occurrence}` : f.name;
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value as object).sort().map((k) => [k, canonical((value as Record<string, unknown>)[k])]));
  }
  return value;
}

/** Giá trị so sánh: bỏ khoảng trắng thừa, object xếp khoá; rỗng/null coi như nhau. */
export function valueText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value.normalize("NFC").replace(/\s+/g, " ").trim();
  if (typeof value === "object") {
    const parts = Object.values(value as Record<string, unknown>);
    if (parts.every((v) => v === null || v === undefined || v === "")) return "";
    return JSON.stringify(canonical(value));
  }
  return String(value);
}

export interface CompareRow {
  key: string;
  comp?: string;
  values: (string | null)[];
  stable: boolean;
}

export interface Consistency {
  runs: LabRun[];
  rows: CompareRow[];
  stable: number;
  /** Số kiểu kế hoạch đính kèm khác nhau giữa các lần (1 = mọi lần đính như nhau). */
  attachVariants: number;
}

/** Các lần chạy xong (điền không lỗi) của một bộ → bảng field × lần, đánh dấu field có giá trị khác nhau. */
export function consistency(batch: Batch, set: number): Consistency | null {
  const runs = batch.runs.filter((r) => r.set === set && r.status === "done" && r.fill && r.fill.status !== "error");
  if (!runs.length) return null;
  const maps = runs.map((r) => new Map(runFields(r).map((f) => [fieldKey(f), f] as const)));
  const keys: string[] = [];
  for (const m of maps) for (const k of m.keys()) if (!keys.includes(k)) keys.push(k);
  const rows = keys.map((key) => {
    const values = maps.map((m) => (m.has(key) ? valueText(m.get(key)!.value) : null));
    const comp = maps.find((m) => m.has(key))?.get(key)?.comp;
    return { key, comp, values, stable: values.every((v) => (v ?? "") === (values[0] ?? "")) };
  });
  const attachRuns = batch.runs.filter((r) => r.set === set && r.attach && r.attach.status !== "error");
  const signatures = new Set(attachRuns.map((r) => runPlan(r).map((p) => {
    const src = p.sourceSegments?.length
      ? p.sourceSegments.map((s) => `${s.fileIndex}:${(s.pages ?? s.pageIndexes ?? []).join(".")}`).join("+")
      : (p.sourceFileIndexes ?? [p.fileIndex]).join("+");
    return `${src}>${p.slotName || p.componentName || p.documentName || ""}`;
  }).sort().join("|")));
  return { runs, rows, stable: rows.filter((r) => r.stable).length, attachVariants: signatures.size };
}
