export interface MonitorUser {
  id: string;
  username: string;
  name?: string | null;
  role: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: MonitorUser;
}

export interface Attachment {
  name?: string | null;
  role?: string | null;
  sha256?: string | null;
  uses?: number | null;
}

/** Tóm tắt thời gian (traces.timing / trace_steps.timing) — xem app/monitor/recorder.py::summary. */
export interface Timing {
  v?: number;
  wait?: number;
  wall?: number;
  g?: { pre?: number; ocr?: number; llm?: number; post?: number };
  other?: number;
  persist?: number;
  persist_wait?: number;
  s?: Record<string, number>;
  n?: Record<string, number>;
  f?: Record<string, boolean>;
}

export type Outcome = "ok" | "partial" | "error";

export interface RunRow {
  id: string | null;
  request_id: string;
  kind: string;
  experience: string;
  outcome: Outcome;
  created_at: string;
  user_id?: string | null;
  username?: string | null;
  name?: string | null;
  procedure?: string | null;
  procedure_label?: string | null;
  applicant_name?: string | null;
  dossier_id?: string | null;
  error?: string | null;
  timing?: Timing | null;
  wait_ms?: number | null;
  legacy?: boolean;
  files?: number | null;
  total_bytes?: number | null;
  key_fields_total?: number | null;
  key_fields_filled?: number | null;
  source: "trace" | "steps";
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Facets {
  users: { userId: string; username?: string | null; name?: string | null }[];
  procedures: { key: string; label?: string | null }[];
}

export interface TraceDoc {
  id: string;
  request_id: string;
  kind?: string;
  experience?: string;
  status?: string;
  outcome?: Outcome;
  error_code?: string | null;
  errors?: string[];
  user_id?: string;
  username?: string | null;
  name?: string | null;
  applicant_name?: string | null;
  procedure?: string;
  procedure_label?: string | null;
  dossier_id?: string | null;
  attachments?: Attachment[];
  ocr_provider?: string | null;
  ocr_label?: string | null;
  ocr_text?: string | null;
  llm_output?: unknown;
  report?: Record<string, unknown> | null;
  stats?: { ocr_latency_ms?: number; llm_latency_ms?: number; total_latency_ms?: number } | null;
  timing?: Timing | null;
  total_bytes?: number | null;
  fields_count?: number | null;
  key_fields_total?: number | null;
  key_fields_filled?: number | null;
  created_at: string;
}

export interface SpanDoc {
  i: number;
  p: number | null;
  n: string;
  t0: number;
  ms: number;
  st: "ok" | "error" | "open";
  a: Record<string, unknown>;
}

export interface LlmCall {
  n: number;
  purpose: string;
  caller?: string;
  fn?: string;
  span?: number;
  t0?: number;
  ms?: number;
  max_tokens?: number;
  thinking?: boolean;
  prompt_chars?: number;
  system_hash?: string | null;
  tokens_in?: number | null;
  tokens_out?: number | null;
  finish_reason?: string | null;
  model?: string | null;
  target?: string | null;
  tries?: { target: string; ms: number; ok: boolean; error?: string }[];
  raw?: string | null;
  parsed?: unknown;
  parse_error?: string;
  think_chars?: number;
  error?: string;
}

export interface OcrFileRef {
  idx: number;
  name?: string | null;
  type?: string | null;
  sha256?: string | null;
  bytes?: number | null;
  cache?: "hit" | "miss" | "off" | "docx";
  reason?: string | null;
  pages?: number | null;
  chars?: number;
  provider?: string | null;
  error?: string | null;
  text?: string;
}

export interface StepsDoc {
  id: string;
  request_id: string;
  kind: string;
  experience: string;
  outcome: Outcome;
  steps_only?: boolean;
  created_at: string;
  meta: Record<string, unknown>;
  timing: Timing | null;
  spans: SpanDoc[];
  ocr: OcrFileRef[];
  llm: LlmCall[];
  outputs: Record<string, unknown>;
  errors: string[];
  truncated: { path: string; len?: number; dropped?: boolean }[];
}

export interface RunDetail {
  trace: TraceDoc | null;
  steps: StepsDoc | null;
}

export interface Dossier {
  id: string;
  experience?: string;
  userId?: string;
  username?: string | null;
  name?: string | null;
  applicantName?: string | null;
  procedure?: string;
  procedureLabel?: string | null;
  startedAt?: string | null;
  submittedAt?: string | null;
  submitCount?: number;
  submitEvents?: { at: string; host?: string; ref?: string }[];
  closedAt?: string | null;
  closeReason?: string;
  rating?: { level?: number; label?: string; reasons?: string[]; note?: string; skipped?: boolean } | null;
  durationMs?: number | null;
  runs?: number;
}

export interface DossierDetail {
  dossier: Dossier | null;
  traces: (TraceDoc & { report?: Record<string, unknown> | null })[];
  stepsOnly: (Partial<StepsDoc> & { request_id: string; kind: string })[];
}

export interface RunRef {
  requestId: string;
  kind?: string | null;
  ms?: number | null;
}

export type Metric = "wait" | "ocr" | "llm";

export interface LatencyRow {
  key: string | null;
  label?: string | null;
  name?: string | null;
  n: number;
  /** Trung bình của chỉ số đang xem (chờ / OCR / LLM). */
  avg: number | null;
  fastest: RunRef | null;
  slowest: RunRef | null;
  preAvg: number | null;
  ocrAvg: number | null;
  llmAvg: number | null;
  postAvg: number | null;
  otherAvg: number | null;
  persistWaitAvg: number | null;
  /** Số lượt theo 4 mốc của chỉ số: < b1, b1–b2, b2–b3, ≥ b3. */
  buckets: number[];
  errors: number;
  partial: number;
  ocrHit: number;
  ocrMiss: number;
  llmCalls: number | null;
  tokOut: number | null;
}

export interface LatencyResponse {
  group: string;
  metric: Metric;
  bounds: number[];
  rows: LatencyRow[];
}
