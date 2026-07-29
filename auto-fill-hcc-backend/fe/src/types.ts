// "commune"/"province" (Hành chính công xã/tỉnh): như "user" — không vào panel, chỉ khác nhãn.
export type Role = "admin" | "user" | "commune" | "province";

export interface User {
  id: string;
  username: string;
  name?: string | null;
  role?: Role;
  xa?: string | null;
  tinh?: string | null;
}

export interface ManagedUser {
  id: string;
  username: string;
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
  role: Role;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface UserListResp {
  items: ManagedUser[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UserCreateBody {
  username: string;
  password: string;
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
  role: Role;
}

export interface UserUpdateBody {
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
  role?: Role;
  password?: string;
}

export interface LoginResp {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface Attachment {
  name: string;
  role: string;
}

export interface TraceListItem {
  id: string;
  request_id: string;
  user_id: string;
  username?: string | null;
  name?: string | null;
  applicant_name?: string | null;
  attachments?: Attachment[];
  procedure: string;
  procedure_label?: string | null;
  ocr_provider?: string | null;
  ocr_label?: string | null;
  fields_count: number;
  kind?: string | null;             // "autofill" | "attach"
  key_fields_total?: number | null;  // tổng trường then chốt (chỉ autofill)
  key_fields_filled?: number | null; // số trường bóc tách được
  status: string;
  error_code?: string | null;
  created_at: string;
}

export interface TraceStats {
  ocr_latency_ms?: number | null;
  llm_latency_ms?: number | null;
  total_latency_ms?: number | null;
}

export interface TraceDetail extends TraceListItem {
  ocr_text: string;
  llm_output: unknown;
  stats?: TraceStats | null;    // thời gian OCR/LLM/tổng (ms) — trace cũ không có
  total_bytes?: number | null;  // dung lượng hồ sơ (payload)
}

export interface TraceListResp {
  items: TraceListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Facets {
  users: { userId: string; username?: string | null; name?: string | null }[];
  procedures: { key: string; label?: string | null }[];
}

export interface StatsProcedure {
  key: string;
  label: string;
  count: number;      // số hồ sơ riêng biệt
  requests?: number;  // số lượt bấm (autofill + đính kèm)
}

export interface StatsWard {
  userId: string;
  name: string;
  total: number;     // tổng hồ sơ riêng biệt của phường
  requests: number;  // tổng lượt bấm
  procedures: StatsProcedure[];
}

export interface StatsResp {
  wards: StatsWard[];
  procedures: StatsProcedure[]; // tổng theo thủ tục (toàn hệ thống)
  totalDossiers: number;
  totalRequests: number;
}
