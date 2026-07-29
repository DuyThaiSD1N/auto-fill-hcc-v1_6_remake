// apiCall: gắn Bearer token + tự refresh khi 401. apiJson: parse JSON + ném lỗi chuẩn.
//
// Mọi request tới BE đi QUA background service worker để tránh mixed-content blocking
// (popup được nhúng iframe trên trang HTTPS, fetch http:// bị auto-upgrade → SSL error).
// Background SW chạy ở context extension thuần, fetch http:// bình thường.

function backendFetch(path, init = {}) {
  return new Promise((resolve) => {
    // Guard: chrome.runtime bị undefined khi extension bị invalidated (reload extension mà popup iframe còn mở).
    if (typeof chrome === "undefined" || !chrome.runtime || !chrome.runtime.sendMessage) {
      return resolve(_makeRes(false, 0, JSON.stringify({ message: "Extension cần reload lại trang (chrome.runtime không khả dụng)." })));
    }
    let bodyStr = init.body;
    // chrome.runtime.sendMessage chỉ serialize được JSON-friendly value; body luôn dạng string.
    if (bodyStr != null && typeof bodyStr !== "string") {
      try { bodyStr = JSON.stringify(bodyStr); } catch (_) { bodyStr = String(bodyStr); }
    }
    chrome.runtime.sendMessage(
      {
        action: "apiFetch",
        url: BACKEND_URL + path,
        method: init.method || "GET",
        headers: init.headers || {},
        body: bodyStr ?? null,
      },
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
  const baseHeaders = {
    ...(opts.headers || {}),
    "Content-Type": "application/json",
  };
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

if (typeof window !== "undefined") {
  window.backendFetch = backendFetch;
  window.apiCall = apiCall;
  window.apiJson = apiJson;
}
