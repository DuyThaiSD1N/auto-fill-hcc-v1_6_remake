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
    const base = await window.tlndBaseUrl();
    const res = await fetch(`${base}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(data?.message || `Đăng nhập thất bại (HTTP ${res.status})`);
    state = { access: data.accessToken, refresh: data.refreshToken, user: data.user };
    loaded = true;
    await _write(state);
    return state.user;
  }

  async function logout() {
    state = null;
    loaded = true;
    await _write(null);
  }

  async function refresh() {
    if (!state?.refresh) return false;
    try {
      const base = await window.tlndBaseUrl();
      const res = await fetch(`${base}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: state.refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      state = { access: data.accessToken, refresh: data.refreshToken, user: data.user || state.user };
      await _write(state);
      return true;
    } catch (_) {
      return false;
    }
  }

  // fetch có Bearer: 401 → refresh 1 lần → thử lại; vẫn 401 → xoá token + bắn sự kiện
  // cho sidebar bật màn đăng nhập (phiên chat GIỮ NGUYÊN — đăng nhập lại là tiếp tục).
  async function authFetch(url, init = {}) {
    await load();
    const doFetch = () =>
      fetch(url, {
        ...init,
        headers: {
          ...(init.headers || {}),
          ...(state?.access ? { Authorization: `Bearer ${state.access}` } : {}),
        },
      });
    let res = await doFetch();
    if (res.status === 401 && (await refresh())) res = await doFetch();
    if (res.status === 401) {
      await logout();
      window.dispatchEvent(new CustomEvent("tlnd-auth-required"));
    }
    return res;
  }

  window.tlndAuth = {
    load, login, logout, refresh, authFetch,
    get user() { return state?.user || null; },
  };
})();
