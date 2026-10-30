// Lõi web Kiểm thử: hàng đợi chạy (bộ tài liệu × lần), chấm từng lượt bằng engine mô phỏng form của Monitor, và so
// kết quả giữa các lần chạy cùng một bộ (độ ổn định của OCR + LLM).
import { findSim, loadAreaCatalog, loadForm, loadSurveyForm } from "../simulations/registry";
import { simulateEform, type SimStats } from "../simulations/eform";
import { findComponentRow, simulateSurveyJs, type SjsComponent, type SjsPlanItem } from "../simulations/surveyjs";
import { isSurveyJsOutput, toFields, type UiField } from "../simulations/fill";
import type { RunDetail, StepsDoc, TraceDoc } from "../types";
import { processV2 } from "./api";

export const MAX_SETS = 5;
export const MAX_RUNS = 5;
/** Số lượt chạy cùng lúc — cố định, đủ nhanh mà không dồn tải OCR/LLM. */
const CONCURRENCY = 2;

export interface Applicant {
  name: string;
  id: string;
  birthday: string;
}

export interface DocSet {
  name: string;
  files: File[];
  applicant: Applicant;
}

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

/** Một đợt kiểm thử — cũng là định dạng file JSON xuất/nhập (không chứa nội dung tệp). */
export interface Batch {
  version: 1;
  id: string;
  procedure: string;
  label: string;
  account: string;
  createdAt: string;
  settings: BatchSettings;
  sets: { name: string; files: string[]; applicant?: Applicant }[];
  runs: LabRun[];
}

export const runKey = (r: { set: number; run: number }) => `${r.set}-${r.run}`;

function newBatchId(): string {
  return `lab_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

export function createBatch(procedure: string, label: string, account: string, settings: BatchSettings, sets: DocSet[], runs: number): Batch {
  return {
    version: 1,
    id: newBatchId(),
    procedure,
    label,
    account,
    createdAt: new Date().toISOString(),
    settings,
    sets: sets.map((s) => ({ name: s.name, files: s.files.map((f) => f.name), applicant: hasApplicant(s.applicant) ? s.applicant : undefined })),
    runs: sets.flatMap((_, set) => Array.from({ length: runs }, (_, run) => ({ set, run, status: "queued" as const }))),
  };
}

export const hasApplicant = (a: Applicant | undefined) => !!a && !!(a.name.trim() || a.id.trim());

/** formContext extension gửi: mốc tài khoản VNeID của người nộp + (khai sinh kết hợp) tờ khai đang mở. */
function formContext(applicant: Applicant, variant: { value: string; signature: string[] } | undefined): Record<string, unknown> | null {
  const ctx: Record<string, unknown> = {};
  if (applicant.name.trim()) ctx.applicantFullname = applicant.name.trim();
  if (applicant.id.trim()) ctx.applicantIdentityNumber = applicant.id.replace(/\D+/g, "");
  if (applicant.birthday.trim()) ctx.applicantBirthday = applicant.birthday.trim();
  if (variant) {
    ctx.formVariant = variant.value;
    ctx.formSignature = variant.signature;
  }
  return Object.keys(ctx).length ? ctx : null;
}

async function step(
  action: "fill" | "attach",
  procedure: string,
  options: Record<string, unknown>,
  files: File[],
  signal: AbortSignal,
): Promise<StepResult> {
  const started = performance.now();
  try {
    const response = await processV2(action, procedure, options, files, signal);
    const errors = Array.isArray(response.errors) ? response.errors : [];
    return {
      status: errors.length ? "partial" : "ok",
      ms: Math.round(performance.now() - started),
      requestId: (response.requestId as string | undefined) ?? undefined,
      // Tệp nén thay thế (base64, cỡ MB) không cần cho chấm điểm.
      response: action === "attach" ? { ...response, replaceFiles: undefined } : response,
    };
  } catch (reason) {
    if (signal.aborted) throw reason;
    return { status: "error", ms: Math.round(performance.now() - started), error: reason instanceof Error ? reason.message : String(reason) };
  }
}

export interface RunnerHandle {
  stop: () => void;
  done: Promise<void>;
}

/** Chạy mọi lượt "queued" của đợt, tối đa CONCURRENCY lượt cùng lúc. Mỗi lượt: điền rồi đính kèm (như extension). */
export function startBatch(
  batch: Batch,
  sets: DocSet[],
  variant: { value: string; signature: string[] } | undefined,
  onRun: (run: LabRun) => void,
): RunnerHandle {
  const controller = new AbortController();
  const queue = batch.runs.filter((r) => r.status === "queued");
  const { settings } = batch;

  async function exec(run: LabRun) {
    const set = sets[run.set];
    const ctx = formContext(set.applicant, variant);
    const tag = `${batch.id}:${run.set + 1}-${run.run + 1}`;
    let current: LabRun = { ...run, status: "running", startedAt: new Date().toISOString() };
    onRun(current);
    try {
      if (settings.fill) {
        // freshOcr: BE bỏ qua cache OCR → lần nào cũng OCR mới, so giữa các lần mới công bằng (app/services/ocr.py).
        const options: Record<string, unknown> = { labRun: tag, freshOcr: true };
        if (ctx) options.formContext = ctx;
        current = { ...current, fill: await step("fill", batch.procedure, options, set.files, controller.signal) };
        onRun(current);
      }
      if (settings.attach) {
        const options: Record<string, unknown> = {
          labRun: tag,
          splitDocuments: settings.split,
          extVersion: "lab",
          attachSupports: ["attp-row", "fixed-slot", "add-document-dialog", "fixed-slot+add-document-dialog"],
        };
        current = { ...current, attach: await step("attach", batch.procedure, options, set.files, controller.signal) };
      }
      onRun({ ...current, status: "done", finishedAt: new Date().toISOString() });
    } catch {
      onRun({ ...current, status: "cancelled", finishedAt: new Date().toISOString() });
    }
  }

  const workers = Array.from({ length: Math.max(1, Math.min(CONCURRENCY, queue.length)) }, async () => {
    for (let next = queue.shift(); next; next = queue.shift()) {
      if (controller.signal.aborted) { onRun({ ...next, status: "cancelled" }); continue; }
      await exec(next);
    }
  });

  return {
    stop: () => controller.abort(),
    done: Promise.all(workers).then(() => undefined),
  };
}

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

export function exportBatch(batch: Batch): void {
  const blob = new Blob([JSON.stringify(batch, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `kiem-thu_${batch.procedure}_${batch.createdAt.slice(0, 19).replace(/[:T]/g, "-")}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function importBatch(file: File): Promise<Batch> {
  const data = JSON.parse(await file.text()) as Partial<Batch>;
  if (data?.version !== 1 || !data.procedure || !Array.isArray(data.runs) || !Array.isArray(data.sets)) {
    throw new Error("Tệp không phải kết quả xuất từ web Kiểm thử.");
  }
  return settle(data as Batch);
}

/** Lượt đang chạy dở lúc xuất / lúc lưu lịch sử (tab bị đóng giữa chừng) → coi như đã dừng. */
function settle(batch: Batch): Batch {
  return { ...batch, runs: batch.runs.map((r) => (r.status === "queued" || r.status === "running" ? { ...r, status: "cancelled" } : r)) };
}

// ---- lịch sử các đợt (IndexedDB của trình duyệt) ---------------------------------------------------------------

/** Giữ tối đa chừng này đợt gần nhất; cũ hơn tự xoá. */
const HISTORY_LIMIT = 50;
const DB_NAME = "hcc_lab_history";
// "summary" nhẹ để liệt kê; "batch" chứa đủ output máy chủ (có thể vài MB/đợt), chỉ đọc khi mở xem.
const SUMMARY = "summary";
const FULL = "batch";

export interface HistoryEntry {
  id: string;
  procedure: string;
  label: string;
  account: string;
  createdAt: string;
  finishedAt?: string;
  sets: number;
  runs: number;
  done: number;
  cancelled: number;
  errors: number;
}

function summarize(batch: Batch): HistoryEntry {
  const finished = batch.runs.map((r) => r.finishedAt).filter((t): t is string => !!t).sort();
  return {
    id: batch.id,
    procedure: batch.procedure,
    label: batch.label,
    account: batch.account,
    createdAt: batch.createdAt,
    finishedAt: finished[finished.length - 1],
    sets: batch.sets.length,
    runs: batch.runs.length,
    done: batch.runs.filter((r) => r.status === "done").length,
    cancelled: batch.runs.filter((r) => r.status === "cancelled").length,
    errors: batch.runs.filter((r) => r.fill?.status === "error" || r.attach?.status === "error").length,
  };
}

let dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  dbPromise ??= new Promise<IDBDatabase>((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(SUMMARY, { keyPath: "id" });
      req.result.createObjectStore(FULL, { keyPath: "id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  dbPromise.catch(() => { dbPromise = null; });
  return dbPromise;
}

function txDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = tx.onabort = () => reject(tx.error ?? new Error("Không ghi được lịch sử."));
  });
}

function request<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Mới nhất trước. */
export async function listHistory(): Promise<HistoryEntry[]> {
  const db = await openDb();
  const all = await request(db.transaction(SUMMARY).objectStore(SUMMARY).getAll() as IDBRequest<HistoryEntry[]>);
  return all.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function saveHistory(batch: Batch): Promise<void> {
  const db = await openDb();
  const tx = db.transaction([SUMMARY, FULL], "readwrite");
  tx.objectStore(SUMMARY).put(summarize(batch));
  tx.objectStore(FULL).put(batch);
  await txDone(tx);
  const list = await listHistory();
  if (list.length > HISTORY_LIMIT) await deleteHistory(...list.slice(HISTORY_LIMIT).map((e) => e.id));
}

export async function loadHistory(id: string): Promise<Batch> {
  const db = await openDb();
  const batch = await request(db.transaction(FULL).objectStore(FULL).get(id) as IDBRequest<Batch | undefined>);
  if (!batch) throw new Error("Đợt này không còn trong lịch sử.");
  return settle(batch);
}

export async function deleteHistory(...ids: string[]): Promise<void> {
  const db = await openDb();
  const tx = db.transaction([SUMMARY, FULL], "readwrite");
  for (const id of ids) {
    tx.objectStore(SUMMARY).delete(id);
    tx.objectStore(FULL).delete(id);
  }
  await txDone(tx);
}
