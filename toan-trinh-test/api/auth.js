// api/auth.js — đăng nhập tài khoản quầy/kiosk (JWT) cho sidebar.
// Token sống ở chrome.storage.local (key tlnd_auth) — dùng chung mọi tab, sống qua restart;
// access 1h tự gia hạn bằng refresh (30 ngày) nên máy quầy đăng nhập ~1 lần/tháng.
// KHÔNG gửi adminOnly khi login — mọi role dùng được extension (adminOnly chỉ cho FE quản trị).
(() => {
  "use strict";

  const KEY = "tlnd_auth";
  let state = null; // {access, refresh, user}
  let loaded = false;

  function _read() {
    return new Promise((resolve) => {
      chrome.storage.local.get([KEY], (res) => {
        void chrome.runtime.lastError;
        resolve(res?.[KEY] || null);
      });
    });
  }
  // Thời điểm NHẬN token (giờ máy) + tuổi thọ token: tính hạn theo hai số này thì máy chạy sai giờ
  // (hay gặp ở máy quầy cũ) không còn tưởng token luôn hết hạn rồi làm mới liên tục.
  function _withClock(v) {
    if (!v?.access) return v;
    let ttl = 0;
    try {
      const p = JSON.parse(atob(v.access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")
        .padEnd(Math.ceil(v.access.split(".")[1].length / 4) * 4, "=")));
      ttl = Number(p.exp) - Number(p.iat);
    } catch (_) { /* token lạ → rơi về so exp với giờ máy */ }
    return { ...v, obtained_at: Date.now(), ttl_s: Number.isFinite(ttl) && ttl > 0 ? ttl : 0 };
  }
  function _write(v) {
    return new Promise((resolve) => {
      if (v) chrome.storage.local.set({ [KEY]: v }, () => { void chrome.runtime.lastError; resolve(); });
      else chrome.storage.local.remove([KEY], () => { void chrome.runtime.lastError; resolve(); });
    });
  }

  async function load() {
    if (!loaded) { state = await _read(); loaded = true; }
    return state;
  }

  async function login(username, password) {
    // Qua tlndOverBases: chính lỗi hạ tầng → tự thử backend phụ (cần chung JWT secret + tài khoản).
    const res = await window.tlndOverBases((base) =>
      window.tlndFetch(`${base}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }));
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const error = new Error(data?.message || `Đăng nhập thất bại (HTTP ${res.status})`);
      error.status = res.status;
      error.data = data;
      throw error;
    }
    state = _withClock({ access: data.accessToken, refresh: data.refreshToken, user: data.user });
    loaded = true;
    await _write(state);
    return state.user;
  }

  async function logout() {
    state = null;
    loaded = true;
    await _write(null);
  }

  // BE XOAY VÒNG refresh token (token cũ bị thu hồi ngay). Background (gửi mốc nộp hồ sơ) và
  // sidebar tab khác cũng làm mới — cầm cặp cũ trong RAM là lần refresh sau bị từ chối và cán bộ
  // bị đá ra màn đăng nhập. Nhận cặp mới ngay khi storage đổi. Chỉ nhận cặp CÓ token: xoá token
  // (đăng xuất ở tab khác) giữ hành vi cũ — tab này tự biết khi gặp 401.
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      const next = area === "local" ? changes[KEY]?.newValue : null;
      if (next?.access && next?.refresh) { state = next; loaded = true; }
    });
  } catch (_) { /* không có chrome.storage (test) */ }

  // Refresh bị từ chối nhưng storage đã có cặp khác → bên kia vừa thắng cuộc đua làm mới.
  // Cặp đó có thể về chậm hơn câu từ chối một nhịp nên đọc lại 2 lần.
  async function adoptRotatedTokens(usedRefresh) {
    for (const waitMs of [0, 1500]) {
      if (waitMs) await new Promise((resolve) => setTimeout(resolve, waitMs));
      const cur = await _read();
      if (cur?.access && cur?.refresh && cur.refresh !== usedRefresh) {
        state = cur;
        loaded = true;
        return true;
      }
    }
    return false;
  }

  // Kết quả: "ok" · "invalid" (BE nói rõ phiên không còn: 401/403) · "transient" (mất mạng, timeout,
  // BE đang khởi động lại, bảo trì…). CHỈ "invalid" mới được đăng xuất — trước đây mọi lỗi đều đăng
  // xuất nên cán bộ bị đá ra mỗi lần BE chập chờn.
  // Một lượt làm mới tại một thời điểm: TTS, nghe giọng nói và chat cùng cần token mới thì chờ chung.
  let refreshInFlight = null;
  function refresh() {
    if (!state?.refresh) return Promise.resolve("invalid");
    if (refreshInFlight) return refreshInFlight;
    const usedRefresh = state.refresh;
    refreshInFlight = (async () => {
      try {
        const res = await window.tlndOverBases((base) =>
          window.tlndFetch(`${base}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refreshToken: usedRefresh }),
          }));
        if (res.status === 401 || res.status === 403) {
          return (await adoptRotatedTokens(usedRefresh)) ? "ok" : "invalid";
        }
        if (!res.ok) return "transient";
        const data = await res.json();
        state = _withClock({ access: data.accessToken, refresh: data.refreshToken, user: data.user || state?.user });
        await _write(state);
        return "ok";
      } catch (_) {
        return "transient";
      }
    })().finally(() => { refreshInFlight = null; });
    return refreshInFlight;
  }

  function _accessNeedsRefresh(token, minValiditySeconds = 30) {
    if (!token) return true;
    // Có mốc nhận token → tính theo đồng hồ CỦA MÁY từ lúc nhận (không phụ thuộc máy đúng giờ hay sai).
    if (state?.access === token && state?.obtained_at && state?.ttl_s) {
      return Date.now() >= state.obtained_at + (state.ttl_s - minValiditySeconds) * 1000;
    }
    try {
      const payloadRaw = token.split(".")[1] || "";
      const normalized = payloadRaw.replace(/-/g, "+").replace(/_/g, "/");
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
      const payload = JSON.parse(atob(padded));
      return !Number.isFinite(payload.exp)
        || payload.exp <= Math.floor(Date.now() / 1000) + minValiditySeconds;
    } catch (_) {
      return true;
    }
  }

  // WebSocket không có vòng 401 -> refresh như authFetch. Vì vậy mỗi lượt ASR/TTS phải
  // lấy access token còn hạn trước khi mở socket, tránh quầy mở lâu rồi voice tự mất kết nối.
  async function getAccessToken(minValiditySeconds = 30) {
    await load();
    if (_accessNeedsRefresh(state?.access, minValiditySeconds)) {
      const result = await refresh();
      if (result === "invalid") {
        await logout();
        window.dispatchEvent(new CustomEvent("tlnd-auth-required"));
        return "";
      }
      // "transient": giữ phiên, dùng token đang có — lượt giọng nói này có thể hỏng, lượt sau thử lại.
    }
    return state?.access || "";
  }

  // fetch có Bearer: 401 → refresh 1 lần → thử lại; vẫn 401 → xoá token + bắn sự kiện
  // cho sidebar bật màn đăng nhập (phiên chat GIỮ NGUYÊN — đăng nhập lại là tiếp tục).
  async function authFetch(url, init = {}) {
    await load();
    // tlndFetch = fetch + timeout; url do caller dựng sẵn với 1 base (thường bọc trong tlndOverBases).
    const doFetch = () =>
      window.tlndFetch(url, {
        ...init,
        headers: {
          ...(init.headers || {}),
          ...(state?.access ? { Authorization: `Bearer ${state.access}` } : {}),
        },
      });
    let res = await doFetch();
    if (res.status === 401) {
      const result = await refresh();
      console.warn("[TLND-Auth] API trả 401", { refresh: result });
      if (result === "ok") {
        res = await doFetch();
        console.info("[TLND-Auth] kết quả gọi lại sau refresh", { status: res.status });
        if (res.status === 401) {
          // Token vừa cấp mà vẫn 401 = phiên thật sự không dùng được nữa.
          await logout();
          window.dispatchEvent(new CustomEvent("tlnd-auth-required"));
        }
      } else if (result === "invalid") {
        await logout();
        window.dispatchEvent(new CustomEvent("tlnd-auth-required"));
      }
      // "transient": trả nguyên 401 cho nơi gọi báo lỗi, KHÔNG đăng xuất.
    }
    return res;
  }

  window.tlndAuth = {
    load, login, logout, refresh, authFetch, getAccessToken,
    get user() { return state?.user || null; },
    get accessToken() { return state?.access || ""; },
  };
})();
