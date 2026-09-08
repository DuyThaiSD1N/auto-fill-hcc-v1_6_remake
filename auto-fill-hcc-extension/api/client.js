// apiCall: gắn Bearer token + tự refresh khi 401. apiJson: parse JSON + ném lỗi chuẩn.
//
// BE đã là HTTPS (xem config.js) + có host_permissions → popup/iframe (context extension) FETCH THẲNG
// tới BE, KHÔNG qua chrome.runtime.sendMessage. Lý do: sendMessage có trần cứng 64MiB/message, hồ sơ
// nhiều file base64 nặng (vd biến động đất đai) vượt ngưỡng → "Message exceeded maximum allowed size".
// Fetch trực tiếp không có giới hạn này. Giữ background SW làm DỰ PHÒNG (chỉ khi fetch thẳng bị chặn,
// vd môi trường cũ BE còn http:// gây mixed-content).

// ===== Failover backend CHÍNH ↔ PHỤ =====
// Chỉ chuyển backend khi lỗi HẠ TẦNG (mạng/timeout/502/503/504). Status app-level (401/4xx/500)
// KHÔNG failover — đó là câu trả lời hợp lệ; 401 đã có refresh ở apiCall lo. Tránh double-submit.
const _BACKEND_INFRA_STATUS = new Set([502, 503, 504]);
const _backendDownAt = Object.create(null); // base → timestamp lần lỗi gần nhất (cho cooldown)

function _backendBases() {
  const list = [BACKEND_URL];
  const fb = (typeof BACKEND_URL_FALLBACK === "string" ? BACKEND_URL_FALLBACK : "").trim().replace(/\/+$/, "");
  if (fb && fb !== BACKEND_URL) list.push(fb);
  return list;
}

// Thứ tự thử: CHÍNH trước; nếu chính vừa lỗi trong cooldown thì PHỤ trước (vẫn giữ chính làm chốt cuối).
function _orderedBackendBases() {
  const bases = _backendBases();
  if (bases.length < 2) return bases;
  const [primary, secondary] = bases;
  const downTs = _backendDownAt[primary];
  const primaryDownRecently = downTs && (Date.now() - downTs < BACKEND_FAILOVER_COOLDOWN_MS);
  return primaryDownRecently ? [secondary, primary] : [primary, secondary];
}

async function _fetchWithTimeout(url, opts) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), BACKEND_TIMEOUT_MS);
  try {
    return await fetch(url, { ...opts, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function backendFetch(path, init = {}) {
  let requestBody = init.body;
  const isMultipart = typeof FormData !== "undefined" && requestBody instanceof FormData;
  if (requestBody != null && typeof requestBody !== "string" && !isMultipart) {
    try { requestBody = JSON.stringify(requestBody); } catch (_) { requestBody = String(requestBody); }
  }
  const method = init.method || "GET";
  const headers = init.headers || {};
  const noBody = method === "GET" || method === "HEAD";
  const bases = _orderedBackendBases();

  for (let i = 0; i < bases.length; i++) {
    const base = bases[i];
    const isLast = i === bases.length - 1;
    try {
      const res = await _fetchWithTimeout(base + path, {
        method,
        headers,
        body: noBody ? undefined : (requestBody ?? undefined),
      });
      // 502/503/504 = hạ tầng lỗi → thử backend còn lại (trừ khi đã là base cuối thì trả về như thường).
      if (!isLast && _BACKEND_INFRA_STATUS.has(res.status)) {
        _backendDownAt[base] = Date.now();
        console.warn(`[AutoFill] Backend lỗi HTTP ${res.status} tại ${base}${path} → chuyển sang backend phụ`);
        continue;
      }
      delete _backendDownAt[base]; // base này sống → xoá dấu lỗi
      if (i > 0) console.warn(`[AutoFill] Đang chạy trên BACKEND PHỤ: ${base} (backend chính đang lỗi)`);
      // fetch chỉ throw khi LỖI MẠNG; status lỗi (401/5xx) vẫn trả res bình thường để apiCall xử lý.
      return _makeRes(res.ok, res.status, await res.text());
    } catch (_) {
      // Lỗi mạng/timeout/abort → backend này coi như chết, thử backend phụ nếu còn.
      _backendDownAt[base] = Date.now();
      if (!isLast) {
        console.warn(`[AutoFill] Không gọi được backend ${base} (mạng/timeout) → chuyển sang backend phụ`);
        continue;
      }
      // Base CUỐI cũng lỗi:
      // FormData không thể truyền nguyên vẹn qua chrome.runtime.sendMessage. API v2 chạy trên
      // HTTPS nên luôn fetch trực tiếp; nếu lỗi mạng thì trả lỗi rõ ràng thay vì âm thầm biến
      // multipart thành "{}" hoặc đẩy base64 qua message có trần 64 MiB.
      if (isMultipart) {
        return _makeRes(false, 0, JSON.stringify({
          message: "Không kết nối được máy chủ để gửi hồ sơ. Vui lòng kiểm tra mạng và thử lại.",
        }));
      }
      // Fetch thẳng thất bại (mạng/mixed-content) → quay lại đường background SW cũ (dùng base cuối).
      return _backendFetchViaBackground(path, method, headers, requestBody, base);
    }
  }
}

function _backendFetchViaBackground(path, method, headers, bodyStr, base = BACKEND_URL) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      { action: "apiFetch", url: base + path, method, headers, body: bodyStr ?? null },
      (res) => {
        const errMsg = chrome.runtime.lastError?.message;
        if (errMsg || !res) {
          return resolve(_makeRes(false, 0, JSON.stringify({ message: errMsg || "Background không phản hồi" })));
        }
        if (res.error) {
          return resolve(_makeRes(false, 0, JSON.stringify({ message: res.error })));
        }
        resolve(_makeRes(res.ok, res.status, res.body ?? ""));
      }
    );
  });
}

function _makeRes(ok, status, body) {
  return {
    ok, status,
    json: async () => { try { return JSON.parse(body); } catch { return null; } },
    text: async () => body,
  };
}

async function apiCall(path, opts = {}) {
  const tokens = await AuthStore.getTokens();
  const isMultipart = typeof FormData !== "undefined" && opts.body instanceof FormData;
  const baseHeaders = { ...(opts.headers || {}) };
  // Với multipart, trình duyệt phải tự gắn boundary; set Content-Type bằng tay sẽ làm FastAPI
  // không tách được các part. JSON giữ nguyên contract cũ.
  if (!isMultipart && !Object.keys(baseHeaders).some((key) => key.toLowerCase() === "content-type")) {
    baseHeaders["Content-Type"] = "application/json";
  }
  const init = { method: opts.method || "GET", headers: baseHeaders, body: opts.body };
  const withAuth = (token) => ({
    ...init,
    headers: token ? { ...baseHeaders, Authorization: `Bearer ${token}` } : baseHeaders,
  });

  let res = await backendFetch(path, withAuth(tokens?.accessToken));

  if (res.status === 401 && tokens?.refreshToken) {
    const r = await backendFetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: tokens.refreshToken }),
    });
    if (r.ok) {
      const nt = await r.json();
      await AuthStore.saveTokens(nt);
      res = await backendFetch(path, withAuth(nt.accessToken));
    } else {
      await AuthStore.clearTokens();
      const err = new Error("UNAUTHORIZED");
      err.unauthorized = true;
      throw err;
    }
  }
  return res;
}

async function apiJson(path, opts) {
  const res = await apiCall(path, opts);
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* body rỗng */
  }
  if (!res.ok) {
    const err = new Error(data?.message || data?.error || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    if (res.status === 401) err.unauthorized = true;
    throw err;
  }
  return data;
}

// Base sẽ được thử ĐẦU TIÊN ở lần gọi kế tiếp — dùng để mở đúng trang báo cáo của backend
// đang chạy (chính hay phụ), vì hai backend có số liệu riêng.
function activeBackendBase() {
  return _orderedBackendBases()[0] || BACKEND_URL;
}

if (typeof window !== "undefined") {
  window.backendFetch = backendFetch;
  window.apiCall = apiCall;
  window.apiJson = apiJson;
  window.activeBackendBase = activeBackendBase;
}
