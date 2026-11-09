// API của dịch vụ agent (auto-test-hcc/agents/server.py), đi qua nginx ở /agent-api/.
import { ApiError } from "../../api";
import { labSession, request } from "../api";
import type { Batch, LabRun } from "../engine";

export interface Opinion {
  role: string;
  label: string;
  cause?: string;
  confidence?: number;
  summary?: string;
  evidence?: string[];
  proposal?: string;
  codeRefs?: string[];
  fields?: string[];
  stance?: "agree" | "partly" | "disagree";
  rebuttal?: string;
  error?: string;
}

export interface Check {
  field: string;
  op: string;
  expected: string;
  why?: string;
}

export interface Plan {
  summary: string;
  files: string[];
  steps: string[];
  test: string;
}

export interface Decision {
  decision: "skip_ocr" | "fix_code" | "report_only";
  cause: string;
  reason: string;
  dissent?: string;
  plan?: Plan;
  acceptance?: Check[];
  risk?: string;
}

export interface Evaluation {
  rows: { check: Check; cells: { value: string | null; ok: boolean }[] }[];
  passed: number;
  total: number;
  allPass: boolean;
}

export interface RunBrief {
  n: number;
  status: "ok" | "partial" | "error";
  ms?: number;
  requestId?: string;
  error?: string;
  ocrFresh?: boolean | null;
  screenshot?: string;
  portalWrites?: number;
}

export interface FormGap {
  field: string;
  be: string;
  notFound: number;
  empty: number;
}

export interface Regression {
  field: string;
  before: string[];
  after: string[];
}

export interface FullTests {
  ok: boolean;
  new: string[];
  fixed: string[];
  broken: boolean;
  before: Counts;
  after: Counts;
}

export interface ExtensionTests {
  ok: boolean;
  new: string[];
  total: number;
  failed: number;
  failedBefore: number;
}

export interface Counts {
  failed: number;
  passed: number;
  skipped: number;
  errors: number;
}

export interface Round {
  n: number;
  opinions: Opinion[];
  reviews: Opinion[];
  debate: { skipped: boolean; reason?: string } | null;
  decision: Decision | null;
  precheck?: Evaluation;
  fix: { summary: string; files?: string[]; patch?: string; repairs?: number; notes?: string } | null;
  tests: { pipeline?: { ok: boolean; skipped?: boolean; summary: string; files?: string[] }; full?: FullTests; extension?: ExtensionTests } | null;
  approval?: ApprovalResult | null;
  deploy: { ok: boolean; step?: string | null; ps?: string; health?: string } | null;
  retest: { runs: RunBrief[]; total: number; phase?: string; evaluation?: Evaluation; regressions?: Regression[]; ocrFresh?: number; formGaps?: FormGap[] } | null;
  /** kept: hết vòng mà chưa đạt, code của vòng này được để lại trong thư mục làm việc cho người xem. */
  result: { ok: boolean; reason?: string; kept?: boolean } | null;
}

/** approve: build + chạy kiểm; retry: hoàn tác, vòng sau làm lại theo góp ý; reject: hoàn tác và kết thúc. */
export type Verdict = "approve" | "retry" | "reject";

export interface ApprovalResult {
  decision: Verdict;
  note?: string;
  by?: string;
  at?: string;
  timeout?: boolean;
}

/** Bản sửa đã qua test, đang chờ người duyệt trước khi build Docker và nạp extension. */
export interface PendingApproval {
  round: number;
  since: string;
  files: string[];
  canRetry: boolean;
  timeoutMin: number;
}

export interface FileRecord {
  path: string;
  created: boolean;
}

export interface RequestInfo {
  requestId: string;
  procedure: string;
  label: string;
  status?: string;
  createdAt?: string;
  fieldsCount?: number;
  account: { username: string; name?: string; xa?: string | null; tinh?: string | null };
  files: { name: string; size?: number }[];
  missingFiles: string[];
  pipeline?: string | null;
  experience?: string;
  needsApplicant?: boolean;
}

export interface Job {
  id: string;
  requestId: string;
  description: string;
  createdAt: string;
  createdBy: string;
  settings: { runs: number; maxRounds: number; reproduce: boolean; replayAccount: string; mode?: RunMode };
  human: { message: string; button: string; since: string } | null;
  approval?: PendingApproval | null;
  status: "queued" | "running" | "done" | "failed" | "stopped";
  stage: string;
  outcome: Outcome | null;
  error: string | null;
  warnings: string[];
  case: Partial<RequestInfo>;
  reproduce: { runs: RunBrief[]; total: number; ocrFresh?: number; formGaps?: FormGap[]; faithful?: boolean; coverage?: { original: number; matched: number }; table?: { field: string; original: string; runs: (string | null)[]; stable: boolean }[] } | null;
  rounds: Round[];
  /** unverified: code của vòng chưa đạt, để lại cho người xem (Cần người xem), chưa build lên Docker. */
  fix: {
    files: FileRecord[]; patch: string; summary?: string; reverted: boolean; reverting?: boolean; revertedFiles?: string[]; keptFiles?: string[];
    unverified?: boolean; round?: number;
  } | null;
  report: { outcome: Outcome; headline: string; reason: string; finishedAt: string } | null;
  cost: { usd: number; calls: number };
  events: { t: string; level: string; who: string | null; text: string }[];
}

export type RunMode = "portal" | "api";

export type Outcome = "fixed" | "skipped_ocr" | "report_only" | "not_reproduced" | "need_human" | "not_approved";

export interface JobSummary {
  id: string;
  requestId: string;
  label?: string;
  description: string;
  status: Job["status"];
  stage: string;
  outcome: Outcome | null;
  createdAt: string;
  rounds: number;
  cost: { usd: number; calls: number };
}

export interface NewJob {
  requestId: string;
  description: string;
  replayUsername: string;
  replayPassword: string;
  runs: number;
  maxRounds: number;
  reproduce: boolean;
  applicant?: { applicantFullname: string; applicantIdentityNumber: string; applicantBirthday: string };
  mode: RunMode;
}

interface Phase {
  phase: string;
  runs: (RunBrief & { startedAt?: string; response?: Record<string, unknown> })[];
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const agentApi = {
  health: () => request<{ ok: boolean; claude: boolean; busy: string | null; queued: number }>("/agent-api/health"),
  lookup: (id: string) => request<RequestInfo>(`/agent-api/requests/${encodeURIComponent(id)}`),
  list: () => request<{ items: JobSummary[]; busy: string | null }>("/agent-api/jobs"),
  get: (id: string) => request<Job>(`/agent-api/jobs/${encodeURIComponent(id)}`),
  runs: (id: string) => request<{ phases: Phase[] }>(`/agent-api/jobs/${encodeURIComponent(id)}/runs`),
  create: (body: NewJob) => request<Job>("/agent-api/jobs", json(body)),
  stop: (id: string) => request<Job>(`/agent-api/jobs/${encodeURIComponent(id)}/stop`, { method: "POST" }),
  revert: (id: string) => request<Job>(`/agent-api/jobs/${encodeURIComponent(id)}/revert`, { method: "POST" }),
  ready: (id: string) => request<Job>(`/agent-api/jobs/${encodeURIComponent(id)}/ready`, { method: "POST" }),
  approve: (id: string, body: { round: number; decision: Verdict; note: string }) =>
    request<Job>(`/agent-api/jobs/${encodeURIComponent(id)}/approval`, json(body)),
};

/** Ảnh cần Bearer token nên không gắn thẳng vào <img src>. */
export async function loadShot(id: string, phase: string, n: number): Promise<string> {
  const response = await fetch(`/agent-api/jobs/${encodeURIComponent(id)}/shots/${phase}/${n}`, {
    headers: { Authorization: `Bearer ${labSession.access}` },
  });
  if (!response.ok) throw new ApiError(response.status, "Không tải được ảnh.");
  return URL.createObjectURL(await response.blob());
}

/** nginx trả 502/504 khi dịch vụ trên máy host chưa bật. */
export function serviceDown(reason: unknown): boolean {
  return reason instanceof ApiError && (reason.status === 502 || reason.status === 504);
}

export function errorText(reason: unknown): string {
  if (serviceDown(reason)) return "Dịch vụ agent chưa chạy. Mở terminal ở gốc repo và chạy: python auto-test-hcc/agents/server.py";
  return reason instanceof Error ? reason.message : String(reason);
}

function phaseName(phase: string): string {
  if (phase === "reproduce") return "Trước khi sửa";
  const round = /^round(\d+)$/.exec(phase);
  return round ? `Sau sửa, vòng ${round[1]}` : phase;
}

/** Đổi kết quả chạy lại sang Batch để dùng lại nguyên màn Results của web Kiểm thử. */
export function toBatch(job: Job, phases: Phase[]): Batch {
  const files = (job.case.files ?? []).map((f) => f.name);
  const runs: LabRun[] = phases.flatMap((phase, set) => phase.runs.map((r) => ({
    set,
    run: r.n - 1,
    status: "done" as const,
    startedAt: r.startedAt,
    fill: { status: r.status, ms: r.ms ?? 0, requestId: r.requestId, response: r.response, error: r.error },
  })));
  return {
    version: 1,
    id: `${job.id}:${phases.map((p) => `${p.phase}-${p.runs.length}`).join(",")}`,
    procedure: job.case.procedure ?? "",
    label: job.case.label ?? job.requestId,
    account: job.settings.replayAccount,
    createdAt: job.createdAt,
    settings: { fill: true, attach: false, split: false, variant: "" },
    sets: phases.map((p) => ({ name: phaseName(p.phase), files })),
    runs,
  };
}
