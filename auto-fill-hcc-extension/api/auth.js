const TOKENS_KEY = "auth_tokens";

const AuthStore = {
  async saveTokens({ accessToken, refreshToken }) {
    await chrome.storage.local.set({
      [TOKENS_KEY]: { accessToken, refreshToken, savedAt: Date.now() },
    });
  },
  async getTokens() {
    const r = await chrome.storage.local.get(TOKENS_KEY);
    return r[TOKENS_KEY] || null;
  },
  async clearTokens() {
    await chrome.storage.local.remove(TOKENS_KEY);
  },
};

// Ghi nhớ tên đăng nhập (KHÔNG lưu mật khẩu) để tự điền sẵn ở lần đăng nhập sau.
const PREFILL_KEY = "login_prefill";

const CredStore = {
  async save(username) {
    await chrome.storage.local.set({ [PREFILL_KEY]: { username } });
  },
  async get() {
    const r = await chrome.storage.local.get(PREFILL_KEY);
    return r[PREFILL_KEY] || null;
  },
  async clear() {
    await chrome.storage.local.remove(PREFILL_KEY);
  },
};

if (typeof window !== "undefined") {
  window.AuthStore = AuthStore;
  window.CredStore = CredStore;
}
