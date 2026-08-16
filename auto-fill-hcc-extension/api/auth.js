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

if (typeof window !== "undefined") {
  window.AuthStore = AuthStore;
}
