// Auto test trong Monitor: gọi dịch vụ agent (auto-test-hcc/agents/server.py, /agent-api/lab/*) qua nginx của Monitor.
// Dịch vụ chạy trên máy host của người phát triển; server production không có → nhóm menu Auto test tự ẩn.
import { useEffect, useState } from "react";
import { apiRequest } from "../api";

export type EventSource = "backend" | "form" | "chat" | "extension";

export interface LabEvent {
  no: number;
  t: number;
  at: string | null;
  src: EventSource;
  type: string;
  label: string;
  text: string;
  ms: number | null;
  warn: boolean;
  step: number;
  data: unknown;
  snap: string | null;
}

export interface LabSnapshot {
  id: string;
  t: number | null;
  at: string | null;
  kind: "fill" | "edit" | "step" | string;
  trigger: string;
  label: string;
  fields: number | null;
  empty: boolean;
  extVersion?: string | null;
  host?: string | null;
  path?: string | null;
}

export interface LabRow {
  key: string;
  name: string;
  label: string;
  section?: string | null;
  comp?: string | null;
  pos?: number | null;
  inBe: boolean;
  be: string;
  fill: string | null;
  final: string | null;
  verdict: string;
  verdictText: string;
  onDocs: number;
  beKey?: string;
  source: "llm" | "rule" | "be" | "none";
}

export interface LabFile {
  idx: number;
  name: string;
  type?: string | null;
  role?: string | null;
  size?: number | null;
  pages?: number | null;
  chars?: number | null;
  cache?: string | null;
  provider?: string | null;
  error?: string | null;
  ocr: string;
}

export interface LabChat {
  t: number;
  at: string;
  role: "user" | "bot";
  text: string;
  source?: string | null;
  state?: string | null;
}

export interface LabSummary {
  total: number;
  beFilled: number;
  same: number;
  edited: number;
  missing: number;
  missingOnDocs: number;
  nodata: number;
  byVerdict: Record<string, number>;
}

export interface LabRunView {
  requestId: string;
  kind: string;
  source: "mongo" | "archive" | "local";
  procedure?: string | null;
  label?: string | null;
  experience?: string | null;
  outcome?: string | null;
  unit: { id?: string; username?: string | null; name?: string | null; xa?: string | null; tinh?: string | null };
  dossierId?: string | null;
  startAt: string | null;
  durationMs: number;
  backendEstimated: boolean;
  waitMs: number;
  extVersion?: string | null;
  files: LabFile[];
  steps: { no: number; name: string; from: number | null; to: number | null }[];
  events: LabEvent[];
  chat: LabChat[];
  chatSource?: string | null;
  conversationId?: string | null;
  snapshots: LabSnapshot[];
  trust?: string | null;
  hasReview: boolean;
  rows: LabRow[];
  summary: LabSummary;
  beFields: { name: string; comp?: string | null; occurrence?: number | null; value: unknown }[];
  caseId: string | null;
}

export interface RecentRun {
  requestId: string;
  procedure?: string | null;
  label?: string | null;
  unit?: string | null;
  experience?: string | null;
  kinds?: string[];
  createdAt?: string | null;
  edited?: number | null;
  files?: number | null;
}

export interface CaseSummary {
  id: string;
  procedure?: string | null;
  label?: string | null;
  origin: "lab" | "agent" | string;
  createdAt?: string | null;
  requestId?: string | null;
  unit?: string | null;
  xa?: string | null;
  experience?: string | null;
  answer?: "form" | "backend" | null;
  files: number;
  llm: number;
  checks: number;
  edited: number;
  history: { no: number; status: CaseStatus; failed: number }[];
}

export type CaseStatus = "pass" | "fail" | "review" | "error";

export interface Counts { pass: number; fail: number; review: number; error: number }

export interface RunBrief {
  no: number;
  suite: string;
  suiteLabel?: string | null;
  target: "dev" | "release";
  targetLabel?: string;
  commit?: string | null;
  dirty?: boolean;
  tag?: string | null;
  status: "running" | "done" | "error";
  startedAt?: string;
  finishedAt?: string;
  durationMs?: number;
  by?: string | null;
  counts?: Counts;
  fields?: { ok: number; total: number };
  error?: string;
  total?: number;
  previous?: number | null;
}

export interface Suite {
  key: string;
  kind: "lab" | "agent";
  label?: string | null;
  procedure?: string | null;
  cases: CaseSummary[];
  edited: number;
  lastRun: RunBrief | null;
  running: boolean;
}

export interface Target { key: "dev" | "release"; label: string; ok: boolean; commit?: string | null; dirty?: boolean; tag?: string | null }

export interface ResultRow {
  field: string;
  op: string;
  expected: unknown;
  actual: string | null;
  ok: boolean;
  label?: string | null;
  verdict?: string | null;
  edited?: boolean;
  be?: string | null;
}

export interface CaseResult {
  id: string;
  ok: boolean;
  error?: string | null;
  rows: ResultRow[];
  extraFields: string[];
  ms?: number | null;
  status: CaseStatus;
  okFields: number;
  totalFields: number;
  failedFields: number;
}

export interface RunDetailLab extends RunBrief {
  caseIds?: string[];
  results?: CaseResult[];
  previousResults?: Record<string, { status: CaseStatus; failed?: number; rows: Record<string, string | null> }>;
}

export interface AccessEntry { at: string; user?: string | null; action: string; requestId?: string | null; caseId?: string; run?: number; suite?: string }

export interface LabConfig {
  source: { mongo: string; archive: boolean };
  lab: { cases: number; suites: number; runs: number; dir: string };
  targets: Target[];
  access: AccessEntry[];
}

const enc = encodeURIComponent;
const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const labApi = {
  run: (id: string) => apiRequest<LabRunView>(`/agent-api/lab/runs/${enc(id)}`),
  raw: (id: string) => apiRequest<Record<string, unknown>>(`/agent-api/lab/runs/${enc(id)}/raw`),
  recent: (edited: boolean) => apiRequest<{ source: string; items: RecentRun[] }>(`/agent-api/lab/recent?edited=${edited ? "true" : "false"}&limit=60`),
  createCase: (requestId: string) => apiRequest<{ caseId: string; existing: boolean; stats?: Record<string, number> }>("/agent-api/lab/cases", json({ requestId })),
  deleteCase: (id: string) => apiRequest<{ ok: boolean }>(`/agent-api/lab/cases/${enc(id)}`, { method: "DELETE" }),
  suites: () => apiRequest<{ suites: Suite[]; targets: Target[] }>("/agent-api/lab/suites"),
  startRun: (suite: string, target: "dev" | "release", caseIds?: string[]) =>
    apiRequest<RunBrief>("/agent-api/lab/suite-runs", json({ suite, target, caseIds: caseIds?.length ? caseIds : null })),
  runs: () => apiRequest<{ runs: RunBrief[]; current: number | null }>("/agent-api/lab/suite-runs"),
  runDetail: (no: number) => apiRequest<RunDetailLab>(`/agent-api/lab/suite-runs/${no}`),
  config: () => apiRequest<LabConfig>("/agent-api/lab/config"),
};

let available: Promise<boolean> | null = null;

/** Dịch vụ agent có chạy và có API lab không (kiểm một lần mỗi lần tải trang). */
export function labAvailable(): Promise<boolean> {
  if (!available) {
    available = fetch("/agent-api/health", { headers: { Accept: "application/json" } })
      .then(async (r) => r.ok && Boolean(((await r.json()) as { lab?: boolean }).lab))
      .catch(() => false);
  }
  return available;
}

export function useLabAvailable(): boolean | null {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    labAvailable().then((v) => { if (alive) setOk(v); });
    return () => { alive = false; };
  }, []);
  return ok;
}

/** Tạo ca nếu lượt chưa có ca, rồi chạy riêng ca đó trên bản đang phát triển (máy không có cây đó, như server
 * production chỉ có khu làm việc, thì chạy trên bản production). Trả số lần chạy. */
export async function rerunRequest(requestId: string, caseId: string | null, procedure?: string | null): Promise<number> {
  const id = caseId ?? (await labApi.createCase(requestId)).caseId;
  const { targets } = await labApi.suites();
  const target = targets.find((t) => t.key === "dev" && t.ok)?.key ?? targets.find((t) => t.ok)?.key;
  if (!target) throw new Error("Máy chạy dịch vụ agent không có cây backend nào để chạy ca.");
  const run = await labApi.startRun(`lab:${(procedure ?? "khac").replace(/[^\w.-]/g, "_")}`, target, [id]);
  return run.no;
}
