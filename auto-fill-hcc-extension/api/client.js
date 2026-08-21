// apiCall: gắn Bearer token + tự refresh khi 401. apiJson: parse JSON + ném lỗi chuẩn.
//
// BE đã là HTTPS (xem config.js) + có host_permissions → popup/iframe (context extension) FETCH THẲNG
// tới BE, KHÔNG qua chrome.runtime.sendMessage. Lý do: sendMessage có trần cứng 64MiB/message, hồ sơ
// nhiều file base64 nặng (vd biến động đất đai) vượt ngưỡng → "Message exceeded maximum allowed size".
// Fetch trực tiếp không có giới hạn này. Giữ background SW làm DỰ PHÒNG (chỉ khi fetch thẳng bị chặn,
// vd môi trường cũ BE còn http:// gây mixed-content).

async function backendFetch(path, init = {}) {
  let requestBody = init.body;
  const isMultipart = typeof FormData !== "undefined" && requestBody instanceof FormData;
  if (requestBody != null && typeof requestBody !== "string" && !isMultipart) {
    try { requestBody = JSON.stringify(requestBody); } catch (_) { requestBody = String(requestBody); }
  }
  const method = init.method || "GET";
  const headers = init.headers || {};
  const noBody = method === "GET" || method === "HEAD";
  try {
    const res = await fetch(BACKEND_URL + path, {
      method,
      headers,
      body: noBody ? undefined : (requestBody ?? undefined),
    });
    // fetch chỉ throw khi LỖI MẠNG; status lỗi (401/5xx) vẫn trả res bình thường để apiCall xử lý.
    return _makeRes(res.ok, res.status, await res.text());
  } catch (_) {
    // FormData không thể truyền nguyên vẹn qua chrome.runtime.sendMessage. API v2 chạy trên
    // HTTPS nên luôn fetch trực tiếp; nếu lỗi mạng thì trả lỗi rõ ràng thay vì âm thầm biến
    // multipart thành "{}" hoặc đẩy base64 qua message có trần 64 MiB.
    if (isMultipart) {
      return _makeRes(false, 0, JSON.stringify({
        message: "Không kết nối được máy chủ để gửi hồ sơ. Vui lòng kiểm tra mạng và thử lại.",
      }));
    }
    // Fetch thẳng thất bại (mạng/mixed-content) → quay lại đường background SW cũ.
    return _backendFetchViaBackground(path, method, headers, requestBody);
  }
}

function _backendFetchViaBackground(path, method, headers, bodyStr) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      { action: "apiFetch", url: BACKEND_URL + path, method, headers, body: bodyStr ?? null },
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

if (typeof window !== "undefined") {
  window.backendFetch = backendFetch;
  window.apiCall = apiCall;
  window.apiJson = apiJson;
}
