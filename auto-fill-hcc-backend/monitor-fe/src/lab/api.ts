// API của web Kiểm thử: đăng nhập bằng tài khoản bất kỳ (kết quả điền phụ thuộc xã/tỉnh của tài khoản, đúng như
// extension), gọi /api/v2/process giống hệt extension (multipart, action fill | attach).
import { ApiError } from "../api";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const ACCESS_KEY = "hcc_lab_access";
const REFRESH_KEY = "hcc_lab_refresh";
const USER_KEY = "hcc_lab_user";

export const LAB_AUTH_EXPIRED_EVENT = "hcc-lab:auth-expired";

export interface LabUser {
  id: string;
  username: string;
  name?: string | null;
  role?: string;
  xa?: string | null;
  tinh?: string | null;
}

interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: LabUser;
}

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value);
  } catch { /* trình duyệt chặn storage → phiên chỉ sống tới khi tải lại trang */ }
}

const memory: { access: string | null; refresh: string | null } = { access: read(ACCESS_KEY), refresh: read(REFRESH_KEY) };

export const labSession = {
  get access() { return memory.access; },
  get refresh() { return memory.refresh; },
  get user(): LabUser | null {
    const raw = read(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw) as LabUser; } catch { return null; }
  },
  save(data: LoginResponse): void {
    memory.access = data.accessToken;
    memory.refresh = data.refreshToken;
    write(ACCESS_KEY, data.accessToken);
    write(REFRESH_KEY, data.refreshToken);
    write(USER_KEY, JSON.stringify(data.user));
  },
  clear(): void {
    memory.access = null;
    memory.refresh = null;
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
    write(USER_KEY, null);
  },
};

async function parseError(response: Response): Promise<ApiError> {
  let message = `Không thể xử lý yêu cầu (HTTP ${response.status}).`;
  let errorCode: string | undefined;
  try {
    const body = (await response.json()) as { message?: string; detail?: unknown; error?: string };
    const detail = typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? JSON.stringify(body.detail) : "";
    message = body.message || detail || message;
    errorCode = body.error;
  } catch {
    // Gateway có thể trả HTML/plain text (502, 413 của nginx); giữ câu mặc định có mã HTTP.
  }
  return new ApiError(response.status, message, errorCode);
}

// Nhiều lượt chạy song song cùng hết hạn token → chỉ refresh một lần.
let refreshing: Promise<boolean> | null = null;

function refreshTokens(): Promise<boolean> {
  if (refreshing) return refreshing;
  const refreshToken = labSession.refresh;
  if (!refreshToken) return Promise.resolve(false);
  refreshing = fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
  })
    .then(async (response) => {
      if (!response.ok) return false;
      labSession.save((await response.json()) as LoginResponse);
      return true;
    })
    .catch(() => false)
    .finally(() => { refreshing = null; });
  return refreshing;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (labSession.access) headers.set("Authorization", `Bearer ${labSession.access}`);
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (response.status === 401) {
    if (retry && (await refreshTokens())) return request<T>(path, init, false);
    labSession.clear();
    window.dispatchEvent(new Event(LAB_AUTH_EXPIRED_EVENT));
  }
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export async function loginLab(username: string, password: string): Promise<LabUser> {
  const response = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw await parseError(response);
  const data = (await response.json()) as LoginResponse;
  labSession.save(data);
  return data.user;
}

export async function validateLabSession(): Promise<LabUser | null> {
  if (!labSession.access && !labSession.refresh) return null;
  try {
    const user = await request<LabUser>("/auth/me");
    write(USER_KEY, JSON.stringify(user));
    return user;
  } catch {
    labSession.clear();
    return null;
  }
}

export interface BeProcedure {
  key: string;
  label?: string;
  uploadHint?: string;
  supportsSplitDocuments?: boolean;
}

export async function listProcedures(): Promise<BeProcedure[]> {
  const data = await request<{ procedures?: BeProcedure[] }>("/api/v1/procedures");
  return data.procedures ?? [];
}

/** Một lần gọi /api/v2/process — dựng multipart y như api/endpoints.js của extension. */
export function processV2(
  action: "fill" | "attach",
  procedure: string,
  options: Record<string, unknown>,
  files: File[],
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append("action", action);
  form.append("procedure", procedure);
  form.append("options", JSON.stringify(options));
  form.append("fileMetadata", JSON.stringify(files.map((f) => ({ name: f.name, type: f.type || "image/jpeg", role: "doc" }))));
  for (const f of files) form.append("files", f, f.name);
  return request<Record<string, unknown>>("/api/v2/process", { method: "POST", body: form, signal });
}
