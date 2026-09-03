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

export interface TraceStats {
  ocr_latency_ms?: number | null;
  llm_latency_ms?: number | null;
  total_latency_ms?: number | null;
}

export interface TraceListItem {
  id: string;
  request_id: string;
  user_id?: string | null;
  username?: string | null;
  name?: string | null;
  applicant_name?: string | null;
  attachments?: Attachment[];
  procedure?: string | null;
  procedure_label?: string | null;
  fields_count?: number | null;
  experience?: "autofill" | "handfree" | null;
  kind?: string | null;
  status?: string | null;
  error_code?: string | null;
  created_at: string;
}

export interface TraceDetail extends TraceListItem {
  ocr_provider?: string | null;
  ocr_label?: string | null;
  ocr_text?: string | null;
  llm_output?: unknown;
  report?: unknown;
  stats?: TraceStats | null;
  total_bytes?: number | null;
  key_fields_total?: number | null;
  key_fields_filled?: number | null;
}

export interface TraceListResponse {
  items: TraceListItem[];
  total: number;
  page: number;
  pageSize: number;
}
