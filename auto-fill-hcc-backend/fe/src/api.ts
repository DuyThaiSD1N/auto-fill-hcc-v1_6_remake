import type {
  DossierDetail,
  DossierListResp,
  Facets,
  LoginResp,
  ManagedUser,
  DownloadResult,
  ReportExportBody,
  ReportOptionsResp,
  StatsResp,
  StatsSource,
  TraceDetail,
  TraceListResp,
  UserCreateBody,
  UserListFilters,
  UserListResp,
  UserUpdateBody,
} from "./types";

// Dev dùng proxy của Vite nên base rỗng. Prod set VITE_API_BASE (vd https://api...).
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

const ACCESS_KEY = "hcc_access";
const REFRESH_KEY = "hcc_refresh";
const USER_KEY = "hcc_user";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  save(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  saveUser(user: unknown) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

// Phát khi phiên hết hạn KHÔNG cứu được (refresh fail/không có). App nghe sự kiện này để
// tự đẩy về màn đăng nhập, thay vì để người dùng kẹt ở panel với token đã chết.
export const AUTH_EXPIRED_EVENT = "hcc:auth-expired";

function forceLogout() {
  tokens.clear();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `Lỗi ${res.status}`;
  let code: string | undefined;
  try {
    const data = await res.json();
    message = data?.message || data?.detail || message;
    code = data?.code;
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, message, code);
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: refresh }),
  });
  if (!res.ok) return false;
  const data = (await res.json()) as LoginResp;
  tokens.save(data.accessToken, data.refreshToken);
  tokens.saveUser(data.user);
  return true;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    if (retry && tokens.refresh && (await refreshTokens())) {
      return request<T>(path, init, false);
    }
    // Access hết hạn mà refresh cũng hết hạn/không có → phiên kết thúc: dọn token + đẩy về login.
    forceLogout();
  }
  if (!res.ok) throw await parseError(res);
  return res.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<LoginResp> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // adminOnly: BE từ chối cấp token nếu không phải admin (chặn ngay tại login, không chỉ ở UI).
    body: JSON.stringify({ username, password, adminOnly: true }),
  });
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as LoginResp;
  // Phòng tuyến 2 (nếu BE bản cũ chưa hiểu adminOnly): vẫn kiểm role, không lưu token.
  if (data.user.role !== "admin") {
    throw new ApiError(403, "Tài khoản này không có quyền truy cập trang quản lý.");
  }
  tokens.save(data.accessToken, data.refreshToken);
  tokens.saveUser(data.user);
  return data;
}

export interface TraceQuery {
  source?: "all" | "autofill" | "handfree";
  userId?: string;
  procedure?: string;
  dateFrom?: string;
  dateTo?: string;
  requestId?: string;
  page?: number;
  pageSize?: number;
}

export function listTraces(q: TraceQuery): Promise<TraceListResp> {
  const params = new URLSearchParams();
  if (q.source) params.set("source", q.source);
  if (q.userId) params.set("userId", q.userId);
  if (q.procedure) params.set("procedure", q.procedure);
  if (q.dateFrom) params.set("dateFrom", q.dateFrom);
  if (q.dateTo) params.set("dateTo", q.dateTo);
  if (q.requestId) params.set("requestId", q.requestId);
  params.set("page", String(q.page ?? 1));
  params.set("pageSize", String(q.pageSize ?? 20));
  return request<TraceListResp>(`/api/v1/traces?${params.toString()}`);
}

export function getTrace(id: string): Promise<TraceDetail> {
  return request<TraceDetail>(`/api/v1/traces/${id}`);
}

export function getFacets(source: "all" | "autofill" | "handfree" = "all"): Promise<Facets> {
  return request<Facets>(`/api/v1/traces/facets?source=${source}`);
}

export function getStats(
  source: StatsSource,
  scope: "official" | "all",
  dateFrom?: string,
  dateTo?: string,
  signal?: AbortSignal,
): Promise<StatsResp> {
  const params = new URLSearchParams();
  params.set("source", source);
  params.set("scope", scope);
  if (dateFrom) params.set("dateFrom", dateFrom);
  if (dateTo) params.set("dateTo", dateTo);
  const qs = params.toString();
  return request<StatsResp>(`/api/v1/traces/stats${qs ? `?${qs}` : ""}`, { signal });
}

// --- Kết xuất báo cáo Excel (admin) ---
export function getReportOptions(signal?: AbortSignal): Promise<ReportOptionsResp> {
  return request<ReportOptionsResp>(`/api/v1/reports/options`, { signal });
}

// --- Quản lý tài khoản (admin) ---
export function listUsers(
  page = 1,
  pageSize = 20,
  filters: UserListFilters = {},
): Promise<UserListResp> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (filters.role) params.set("role", filters.role);
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.tinh) params.set("tinh", filters.tinh);
  // "all" là mặc định của BE — không gửi để URL gọn và cache dễ đoán hơn.
  if (filters.status && filters.status !== "all") params.set("status", filters.status);
  return request<UserListResp>(`/api/v1/users?${params.toString()}`);
}

/** Bỏ dấu xóa mềm. Không có đường này thì xóa mềm chỉ là giấu đi, không cứu được gì. */
export function restoreUser(id: string): Promise<ManagedUser> {
  return request<ManagedUser>(`/api/v1/users/${id}/restore`, { method: "POST" });
}

export function createUser(body: UserCreateBody): Promise<ManagedUser> {
  return request<ManagedUser>(`/api/v1/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function updateUser(id: string, body: UserUpdateBody): Promise<ManagedUser> {
  return request<ManagedUser>(`/api/v1/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteUser(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/v1/users/${id}`, { method: "DELETE" });
}

// --- Nhập tài khoản hàng loạt từ Excel ---
export type ImportRowStatus =
  | "create" | "created" | "exists" | "exists_deleted" | "duplicate_in_file" | "error";

/** Một dòng kết quả. BE KHÔNG trả mật khẩu. */
export interface ImportRow {
  row: number;
  name: string;
  username: string;
  tinh: string;
  xa: string;
  role: "" | "commune" | "province";
  status: ImportRowStatus;
  message: string;
}

export interface ImportResult {
  applied: boolean;
  summary: Partial<Record<ImportRowStatus, number>>;
  rows: ImportRow[];
}

/** apply=false: chỉ kiểm, không ghi. apply=true: BE kiểm lại từ đầu rồi mới tạo — gửi lại
 *  đúng file, không giữ gì ở BE giữa hai bước. */
export function importUsers(file: File, apply: boolean): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  // KHÔNG tự đặt Content-Type: trình duyệt phải tự thêm boundary của multipart.
  return request<ImportResult>(`/api/v1/users/import?apply=${apply ? "true" : "false"}`, {
    method: "POST",
    body,
  });
}

export function downloadImportTemplate(): Promise<DownloadResult> {
  return requestDownload(`/api/v1/users/import/template`);
}

// --- Danh mục tỉnh/xã ---
export interface Province {
  text: string;
  slug: string;
  name: string;
}

export function getProvinces(signal?: AbortSignal): Promise<{ provinces: Province[] }> {
  return request<{ provinces: Province[] }>(`/api/v1/provinces`, { signal });
}

export function getWards(
  slug: string,
  signal?: AbortSignal,
): Promise<{ slug: string; province: string; communes: string[] }> {
  const params = new URLSearchParams({ slug });
  return request<{ slug: string; province: string; communes: string[] }>(
    `/api/v1/wards?${params.toString()}`,
    { signal },
  );
}

// Tải nội dung 1 file đính kèm của trace (ảnh/PDF) dưới dạng Blob, có Authorization.
async function requestDownload(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<DownloadResult> {
  const headers = new Headers(init.headers);
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401) {
    if (retry && tokens.refresh && (await refreshTokens())) {
      return requestDownload(path, init, false);
    }
    forceLogout();
  }
  if (!res.ok) throw await parseError(res);
  const disposition = res.headers.get("Content-Disposition") || "";
  const encodedFilename = disposition
    .match(/filename\*\s*=\s*UTF-8''([^;]+)/i)?.[1]
    ?.trim()
    .replace(/^"|"$/g, "");
  let filename: string | undefined;
  if (encodedFilename) {
    try {
      filename = decodeURIComponent(encodedFilename);
    } catch {
      // Header lỗi encoding thì vẫn tải được bằng tên ASCII dự phòng.
    }
  }
  filename ||= disposition.match(/filename="?([^";]+)"?/i)?.[1];
  return { blob: await res.blob(), filename };
}

async function requestBlob(path: string): Promise<Blob> {
  return (await requestDownload(path)).blob;
}

export function fetchTraceFile(traceId: string, index: number): Promise<Blob> {
  return requestBlob(`/api/v1/traces/${traceId}/files/${index}`);
}

// Tải TẤT CẢ tài liệu của trace dưới dạng 1 file ZIP (BE gom, FE tải blob kèm Authorization).
export function fetchTraceArchive(traceId: string): Promise<Blob> {
  return requestBlob(`/api/v1/traces/${traceId}/download`);
}

export function exportReportExcel(
  body: ReportExportBody,
  signal?: AbortSignal,
): Promise<DownloadResult> {
  return requestDownload(`/api/v1/reports/excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export { ApiError };

// --- Vòng đời hồ sơ (danh sách + chi tiết) ---
export interface DossierQuery {
  source?: "all" | "autofill" | "handfree";
  status?: "all" | "submitted" | "unsubmitted";
  userId?: string;
  procedure?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export function listDossiers(q: DossierQuery, signal?: AbortSignal): Promise<DossierListResp> {
  const params = new URLSearchParams();
  if (q.source) params.set("source", q.source);
  if (q.status) params.set("status", q.status);
  if (q.userId) params.set("userId", q.userId);
  if (q.procedure) params.set("procedure", q.procedure);
  if (q.dateFrom) params.set("dateFrom", q.dateFrom);
  if (q.dateTo) params.set("dateTo", q.dateTo);
  params.set("page", String(q.page ?? 1));
  params.set("pageSize", String(q.pageSize ?? 20));
  return request<DossierListResp>(`/api/v1/dossiers?${params.toString()}`, { signal });
}

export function getDossier(id: string): Promise<DossierDetail> {
  return request<DossierDetail>(`/api/v1/dossiers/${encodeURIComponent(id)}`);
}
