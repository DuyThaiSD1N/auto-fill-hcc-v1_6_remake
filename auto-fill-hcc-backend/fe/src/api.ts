import type {
  Facets,
  LoginResp,
  ManagedUser,
  StatsResp,
  TraceDetail,
  TraceListResp,
  UserCreateBody,
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

export function getFacets(): Promise<Facets> {
  return request<Facets>(`/api/v1/traces/facets`);
}

export function getStats(dateFrom?: string, dateTo?: string): Promise<StatsResp> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("dateFrom", dateFrom);
  if (dateTo) params.set("dateTo", dateTo);
  const qs = params.toString();
  return request<StatsResp>(`/api/v1/traces/stats${qs ? `?${qs}` : ""}`);
}

// --- Quản lý tài khoản (admin) ---
export function listUsers(page = 1, pageSize = 20): Promise<UserListResp> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  return request<UserListResp>(`/api/v1/users?${params.toString()}`);
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

// Tải nội dung 1 file đính kèm của trace (ảnh/PDF) dưới dạng Blob, có Authorization.
async function requestBlob(path: string, retry = true): Promise<Blob> {
  const headers = new Headers();
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  const res = await fetch(`${BASE}${path}`, { headers });
  if (res.status === 401) {
    if (retry && tokens.refresh && (await refreshTokens())) return requestBlob(path, false);
    forceLogout();
  }
  if (!res.ok) throw await parseError(res);
  return res.blob();
}

export function fetchTraceFile(traceId: string, index: number): Promise<Blob> {
  return requestBlob(`/api/v1/traces/${traceId}/files/${index}`);
}

// Tải TẤT CẢ tài liệu của trace dưới dạng 1 file ZIP (BE gom, FE tải blob kèm Authorization).
export function fetchTraceArchive(traceId: string): Promise<Blob> {
  return requestBlob(`/api/v1/traces/${traceId}/download`);
}

export { ApiError };
