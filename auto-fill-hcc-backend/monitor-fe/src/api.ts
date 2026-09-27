import type {
  Dossier,
  DossierDetail,
  Facets,
  LatencyResponse,
  LoginResponse,
  MonitorUser,
  Page,
  RunDetail,
  RunRow,
  TraceDoc,
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
  if (response.status === 403 && path.startsWith("/auth/")) {
    // Chỉ 403 ở kiểm tra phiên mới là mất quyền; 403 của API dữ liệu hiện thành lỗi trên màn
    // (vd một endpoint chặn riêng) thay vì đá người dùng ra đăng nhập.
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

export function getTrace(id: string): Promise<TraceDoc> {
  return request<TraceDoc>(`/api/v1/traces/${encodeURIComponent(id)}`);
}

export function getFacets(): Promise<Facets> {
  return request<Facets>("/api/v1/monitor/facets");
}

export function listRuns(query: string): Promise<Page<RunRow>> {
  return request<Page<RunRow>>(`/api/v1/monitor/runs${query}`);
}

export function getRun(requestId: string, kind?: string | null): Promise<RunDetail> {
  const q = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return request<RunDetail>(`/api/v1/monitor/runs/${encodeURIComponent(requestId)}${q}`);
}

export function getOcrText(sha: string): Promise<{ id: string; text: string; chars?: number; truncated?: boolean }> {
  return request(`/api/v1/monitor/ocr/${encodeURIComponent(sha)}`);
}

export function listDossiers(query: string): Promise<Page<Dossier>> {
  return request<Page<Dossier>>(`/api/v1/monitor/dossiers${query}`);
}

export function getDossier(id: string): Promise<DossierDetail> {
  return request<DossierDetail>(`/api/v1/monitor/dossiers/${encodeURIComponent(id)}`);
}

export function getLatency(query: string): Promise<LatencyResponse> {
  return request<LatencyResponse>(`/api/v1/monitor/stats/latency${query}`);
}

/** Tải mọi tệp của một trace thành 1 file ZIP (BE nén sẵn). */
export async function downloadTraceZip(traceId: string): Promise<{ blob: Blob; filename: string }> {
  const path = `/api/v1/traces/${encodeURIComponent(traceId)}/download`;
  async function go(retry: boolean): Promise<Response> {
    const headers = new Headers();
    if (monitorSession.access) headers.set("Authorization", `Bearer ${monitorSession.access}`);
    const response = await fetch(`${BASE}${path}`, { headers });
    if (response.status === 401 && retry && (await refreshTokens())) return go(false);
    if (response.status === 401) expireSession();
    if (!response.ok) throw await parseError(response);
    return response;
  }
  const response = await go(true);
  const match = /filename="?([^";]+)"?/i.exec(response.headers.get("Content-Disposition") || "");
  return { blob: await response.blob(), filename: match?.[1] || `${traceId}.zip` };
}

export async function fetchTraceFile(traceId: string, index: number): Promise<Blob> {
  const path = `/api/v1/traces/${encodeURIComponent(traceId)}/files/${index}`;

  async function fetchBlob(retry: boolean): Promise<Blob> {
    const headers = new Headers();
    if (monitorSession.access) headers.set("Authorization", `Bearer ${monitorSession.access}`);
    const response = await fetch(`${BASE}${path}`, { headers });
    if (response.status === 401 && retry && (await refreshTokens())) return fetchBlob(false);
    if (response.status === 401) expireSession();
    if (!response.ok) throw await parseError(response);
    return response.blob();
  }

  return fetchBlob(true);
}
