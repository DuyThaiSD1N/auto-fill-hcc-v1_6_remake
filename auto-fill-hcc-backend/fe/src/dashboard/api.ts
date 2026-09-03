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

// ── Hợp đồng bảng thống kê (self-service phường + báo cáo cấp Tỉnh) ──────────
export type ScopeKind = "unit" | "province" | "all";

export interface ScopeUnit {
  unitId: string;
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
}

export interface DashScope {
  role: string;
  scopeKind: ScopeKind;
  province: string | null;
  canViewUnits: boolean; // true = tài khoản Tỉnh/admin → mở tab "Theo đơn vị"
  unitCount: number;
  self: ScopeUnit;
}

export interface ScopeResp extends DashScope {
  units: ScopeUnit[];
}

export interface ProcedureStat {
  key: string;
  label: string;
  count: number;
  requests?: number;
  units?: number; // số đơn vị có phát sinh thủ tục này (đa đơn vị)
}

export interface DayStat {
  date: string; // YYYY-MM-DD
  count: number;
}

export interface TopProcedure {
  label: string;
  count: number;
}

export interface UnitStat {
  unitId: string;
  name?: string | null;
  xa?: string | null;
  tinh?: string | null;
  role?: string | null;
  dossiers: number;
  requests: number;
  procedureTypes: number;
  topProcedure: TopProcedure | null;
}

export interface SummaryResp {
  scope: DashScope;
  selected: ScopeUnit | null; // null = toàn phạm vi; ngược lại là đơn vị đang lọc
  range: { from?: string | null; to?: string | null };
  sources: { autofill: boolean; handfree: boolean }; // handfree=false → chưa cộng được Handfree
  kpis: {
    dossiers: number;
    requests: number;
    procedureTypes: number;
    topProcedure: TopProcedure | null;
  };
  byProcedure: ProcedureStat[];
  byDay: DayStat[];
  units: UnitStat[]; // bảng Theo đơn vị (toàn phạm vi, không phụ thuộc đơn vị đang lọc)
}

function rangeQuery(dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const params = new URLSearchParams();
  if (dateFrom) params.set("dateFrom", dateFrom);
  if (dateTo) params.set("dateTo", dateTo);
  for (const [k, v] of Object.entries(extra ?? {})) if (v) params.set(k, v);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function getScope(): Promise<ScopeResp> {
  return request<ScopeResp>(`/api/v1/dashboard/scope`);
}

export function getSummary(dateFrom?: string, dateTo?: string, unit?: string): Promise<SummaryResp> {
  return request<SummaryResp>(`/api/v1/dashboard/summary${rangeQuery(dateFrom, dateTo, { unit: unit ?? "" })}`);
}

// ── Nhật ký hồ sơ (mỗi lượt = 1 dòng, Auto Fill, không PII, không thời lượng) ──
export interface LogItem {
  requestId: string | null;
  receivedAt: string | null; // ISO
  unitId: string;
  unitName: string;
  procedure: string | null;
  procedureLabel: string | null;
  kind: string; // "autofill" | "attach"
}

export interface LogsResp {
  scope: DashScope;
  range: { from?: string | null; to?: string | null };
  source: string; // "autofill"
  items: LogItem[];
  total: number;
  page: number;
  pageSize: number;
}

export function getLogs(
  dateFrom?: string,
  dateTo?: string,
  unit?: string,
  page = 1,
  pageSize = 15,
): Promise<LogsResp> {
  return request<LogsResp>(
    `/api/v1/dashboard/logs${rangeQuery(dateFrom, dateTo, {
      unit: unit ?? "",
      page: String(page),
      pageSize: String(pageSize),
    })}`,
  );
}

// Tải Excel: fetch kèm token (không dùng <a href> vì cần Authorization), trả blob + tên file.
export async function exportExcel(
  dateFrom?: string,
  dateTo?: string,
  unit?: string,
): Promise<{ blob: Blob; filename: string }> {
  const url = `${BASE}/api/v1/dashboard/export${rangeQuery(dateFrom, dateTo, { unit: unit ?? "" })}`;
  const send = () => {
    const headers = new Headers();
    if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
    return fetch(url, { headers });
  };
  let res = await send();
  if (res.status === 401 && tokens.refresh && (await refreshTokens())) res = await send();
  if (res.status === 401) forceLogout();
  if (!res.ok) throw await parseError(res);
  const blob = await res.blob();
  let filename = "thong-ke-ho-so.xlsx";
  const cd = res.headers.get("Content-Disposition") || "";
  const match = /filename\*=UTF-8''([^;]+)/i.exec(cd);
  if (match) {
    try {
      filename = decodeURIComponent(match[1]);
    } catch {
      /* giữ tên mặc định */
    }
  }
  return { blob, filename };
}
