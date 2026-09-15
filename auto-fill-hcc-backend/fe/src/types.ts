// "commune"/"province" (Hành chính công xã/tỉnh): như "user" — không vào panel, chỉ khác nhãn.
// "province_admin": tài khoản Tỉnh CHỈ để xem bảng thống kê đa đơn vị (khác "province" của HCC).
export type Role = "admin" | "user" | "commune" | "province" | "province_admin";

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
  access_disabled: boolean;
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
  access_disabled?: boolean;
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
  sha256?: string | null;
  uses?: number;
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
  experience?: "autofill" | "handfree" | null;
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
  exact?: number;
  estimated?: number;
}

export interface StatsWard {
  userId: string;
  name: string;
  role?: Role | null;
  total: number;     // tổng hồ sơ riêng biệt của phường
  requests: number;  // tổng lượt bấm
  exact: number;
  estimated: number;
  procedures: StatsProcedure[];
}

export type StatsScope = "official" | "all";
export type StatsSource = "all" | "autofill" | "handfree";

export interface StatsResp {
  source: StatsSource;
  scope: StatsScope;
  accountCount: number;
  includedRoles: Role[];
  wards: StatsWard[];
  procedures: StatsProcedure[]; // tổng theo thủ tục (toàn hệ thống)
  totalDossiers: number;
  totalRequests: number;
  exactDossiers: number;
  estimatedDossiers: number;
  estimatedRequests: number;
  dataQuality: "exact" | "estimated" | "mixed";
  uniqueDocuments: number;
  totalDocumentUses: number;
  reusedDocumentUses: number;
  documentDataQuality: "exact" | "partial";
  // Cách đếm hồ sơ của khoảng đang xem. "legacy" = ước tính theo lượt xử lý (đến hết
  // 14/9/2026); "submitted" = đếm hồ sơ đã nộp; "mixed" = khoảng vắt qua mốc nên gồm cả hai.
  counting?: { mode: "legacy" | "submitted" | "mixed"; submittedFrom: string };
}

export interface ReportProvinceOption {
  value: string;
  label: string;
  accountCount: number;
  officialAccountCount: number;
}

export interface ReportAccount {
  id: string;
  username: string;
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
  role: Role;
}

export interface ReportOptionsResp {
  provinces: ReportProvinceOption[];
  accounts: ReportAccount[];
  handfreeEnabled?: boolean;
}

export type ReportSelectionMode = "province" | "accounts";
export type ReportLayout = "daily_summary" | "procedure_detail";

export interface ReportExportBody {
  dateFrom: string;
  dateTo: string;
  selectionMode: ReportSelectionMode;
  province?: string;
  officialOnly?: boolean;
  accountIds?: string[];
  includeHandfree?: boolean;
  reportLayout?: ReportLayout;
}

export interface DownloadResult {
  blob: Blob;
  filename?: string;
}

// ── Vòng đời hồ sơ (collection `dossiers`) ────────────────────────────────────────────────
// Một hồ sơ = một khóa `dossier_id`, chung cho cả hai extension. KHÁC trace: trace là từng
// LƯỢT gọi API, còn đây là cả hồ sơ từ lúc bắt đầu tới lúc bấm nộp.
export interface SubmitEvent {
  at: string;
  host?: string | null;
  ref?: string | null;
}

// Phiếu đánh giá trải nghiệm của công dân (ẩn danh) — BE trả trong dossier.rating.
export interface Rating {
  level: number | null;      // 1..5 (5 = rất hài lòng); null = bỏ qua
  levelLabel: string;
  reasons: string[];
  note: string;
  skipped: boolean;
  at: string | null;
}

export interface DossierListItem {
  id: string;
  experience?: "autofill" | "handfree" | null;
  userId?: string | null;
  username?: string | null;
  name?: string | null;          // tài khoản thực hiện (phường)
  applicantName?: string | null; // công dân làm thủ tục
  procedure?: string | null;
  procedureLabel?: string | null;
  province?: string | null;
  ward?: string | null;
  startedAt: string;
  submittedAt?: string | null;
  // Chứng thực tách nhiều tab dùng chung một khóa và nộp nhiều lần → đây mới là SỐ HỒ SƠ thật
  // của lượt đó, không phải 1.
  submitCount: number;
  closedAt?: string | null;
  closeReason?: string | null;
  portalHost?: string | null;
  portalDossierRef?: string | null;
  durationMs?: number | null;
  rating?: Rating | null;         // đánh giá trải nghiệm (CẢ hai kênh); null = chưa/không có
}

export interface DossierDetail extends DossierListItem {
  submitEvents: SubmitEvent[];
  traces: TraceListItem[];
}

export interface DossierListResp {
  items: DossierListItem[];
  total: number;
  page: number;
  pageSize: number;
}
