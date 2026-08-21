// API client RIÊNG cho bảng thống kê phường — token store tách hẳn khỏi trang quản trị
// (khóa localStorage khác) để phiên phường và phiên admin không đè nhau trên cùng trình duyệt.
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

const ACCESS_KEY = "hcc_ward_access";
const REFRESH_KEY = "hcc_ward_refresh";
const USER_KEY = "hcc_ward_user";

export interface WardUser {
  id: string;
  username: string;
  name?: string | null;
  role?: string;
  xa?: string | null;
  tinh?: string | null;
}

export interface LoginResp {
  accessToken: string;
  refreshToken: string;
  user: WardUser;
}

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
  getUser(): WardUser | null {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as WardUser) : null;
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

export const AUTH_EXPIRED_EVENT = "hcc-ward:auth-expired";

function forceLogout() {
  tokens.clear();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export class ApiError extends Error {
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
    code = data?.code || data?.error;
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
    if (retry && tokens.refresh && (await refreshTokens())) return request<T>(path, init, false);
    forceLogout();
  }
  if (!res.ok) throw await parseError(res);
  return res.json() as Promise<T>;
}

// Đăng nhập phường: KHÔNG gửi adminOnly — tài khoản phường (không phải admin) vẫn được cấp token.
export async function loginWard(username: string, password: string): Promise<LoginResp> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as LoginResp;
  tokens.save(data.accessToken, data.refreshToken);
  tokens.saveUser(data.user);
  return data;
}

export interface WardProcedure {
  key: string;
  label: string;
  count: number;
  requests?: number;
}

export interface WardDay {
  date: string; // YYYY-MM-DD
  count: number;
}

export interface WardSummary {
  ward: { name?: string | null; xa?: string | null; tinh?: string | null };
  range: { from?: string | null; to?: string | null };
  kpis: {
    dossiers: number;
    requests: number;
    procedureTypes: number;
    topProcedure: { label: string; count: number } | null;
  };
  byProcedure: WardProcedure[];
  byDay: WardDay[];
}

export function getWardSummary(dateFrom?: string, dateTo?: string): Promise<WardSummary> {
  const params = new URLSearchParams();
  if (dateFrom) params.set("dateFrom", dateFrom);
  if (dateTo) params.set("dateTo", dateTo);
  const qs = params.toString();
  return request<WardSummary>(`/api/v1/dashboard/summary${qs ? `?${qs}` : ""}`);
}
