import type {
  LoginResponse,
  MonitorUser,
  TraceDetail,
  TraceListResponse,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const ACCESS_KEY = "hcc_monitor_access";
const REFRESH_KEY = "hcc_monitor_refresh";
const USER_KEY = "hcc_monitor_user";

export const MONITOR_AUTH_EXPIRED_EVENT = "hcc-monitor:auth-expired";

export const monitorSession = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  get user(): MonitorUser | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as MonitorUser;
    } catch {
      return null;
    }
  },
  save(data: LoginResponse): void {
    localStorage.setItem(ACCESS_KEY, data.accessToken);
    localStorage.setItem(REFRESH_KEY, data.refreshToken);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  errorCode?: string;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Không thể xử lý yêu cầu (HTTP ${response.status}).`;
  let errorCode: string | undefined;
  try {
    const body = (await response.json()) as { message?: string; detail?: string; error?: string };
    message = body.message || body.detail || message;
    errorCode = body.error;
  } catch {
    // Gateway có thể trả HTML/plain text; không đưa nội dung đó lên giao diện.
  }
  return new ApiError(response.status, message, errorCode);
}

function expireSession(): void {
  monitorSession.clear();
  window.dispatchEvent(new Event(MONITOR_AUTH_EXPIRED_EVENT));
}

function isSuperAdmin(user: MonitorUser | null | undefined): user is MonitorUser {
  return user?.role === "super_admin";
}

async function refreshTokens(): Promise<boolean> {
  const refreshToken = monitorSession.refresh;
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    });
    if (!response.ok) return false;
    const data = (await response.json()) as LoginResponse;
    if (!isSuperAdmin(data.user)) return false;
    monitorSession.save(data);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (monitorSession.access) {
    headers.set("Authorization", `Bearer ${monitorSession.access}`);
  }
  const response = await fetch(`${BASE}${path}`, { ...init, headers });

  if (response.status === 401) {
    if (retry && (await refreshTokens())) {
      return request<T>(path, init, false);
    }
    expireSession();
  }
  if (response.status === 403) {
    // Monitor chỉ gọi API dành cho super admin/trace reader. 403 nghĩa là quyền của phiên
    // đã thay đổi; kết thúc phiên thay vì để người dùng mắc kẹt ở màn hình trắng.
    expireSession();
  }
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export async function loginMonitor(username: string, password: string): Promise<MonitorUser> {
  const response = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, superAdminOnly: true }),
  });
  if (!response.ok) throw await parseError(response);
  const data = (await response.json()) as LoginResponse;
  if (!isSuperAdmin(data.user)) {
    throw new ApiError(403, "Tài khoản này không có quyền truy cập trang Monitor.");
  }
  monitorSession.save(data);
  return data.user;
}

export async function validateMonitorSession(): Promise<MonitorUser | null> {
  if (!monitorSession.access && !monitorSession.refresh) return null;
  try {
    const user = await request<MonitorUser>("/auth/me");
    if (!isSuperAdmin(user)) {
      expireSession();
      return null;
    }
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch {
    monitorSession.clear();
    return null;
  }
}

export function listTraces(requestId: string, page = 1): Promise<TraceListResponse> {
  const params = new URLSearchParams({
    requestId,
    source: "all",
    page: String(page),
    pageSize: "20",
  });
  return request<TraceListResponse>(`/api/v1/traces?${params.toString()}`);
}

export function getTrace(id: string): Promise<TraceDetail> {
  return request<TraceDetail>(`/api/v1/traces/${encodeURIComponent(id)}`);
}

export async function fetchTraceFile(traceId: string, index: number): Promise<Blob> {
  const path = `/api/v1/traces/${encodeURIComponent(traceId)}/files/${index}`;

  async function fetchBlob(retry: boolean): Promise<Blob> {
    const headers = new Headers();
    if (monitorSession.access) headers.set("Authorization", `Bearer ${monitorSession.access}`);
    const response = await fetch(`${BASE}${path}`, { headers });
    if (response.status === 401 && retry && (await refreshTokens())) return fetchBlob(false);
    if (response.status === 401 || response.status === 403) expireSession();
    if (!response.ok) throw await parseError(response);
    return response.blob();
  }

  return fetchBlob(true);
}
