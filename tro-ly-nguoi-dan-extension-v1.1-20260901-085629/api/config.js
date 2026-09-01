// api/config.js — địa chỉ backend Trợ lý người dân.
// Domain thật qua nginx trên server — bắt buộc HTTPS vì sidebar nhúng trong trang https
// (mixed content).
// Dev local: chrome.storage.local.set({ tlnd_base_url: "http://localhost:8010" })
// (console của SIDEBAR — chuột phải vào panel → Inspect; trang web không có chrome.storage).
const TLND_DEFAULT_BASE_URL = "https://trolyhoso-hcc.vnekyc.vn";
const TLND_BASE_URL_KEY = "tlnd_base_url";
const TLND_LEGACY_BASE_URLS = new Set([
  "https://trolynguoidan-admin.vnekyc.vn",
]);

// Đọc base URL (ưu tiên override trong storage). Dùng: const base = await tlndBaseUrl();
function tlndBaseUrl() {
  return new Promise((resolve) => {
    try {
      chrome.storage.local.get([TLND_BASE_URL_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(TLND_DEFAULT_BASE_URL);
        const v = String(res?.[TLND_BASE_URL_KEY] || "").trim().replace(/\/+$/, "");
        if (!v || TLND_LEGACY_BASE_URLS.has(v)) {
          // Bản đã cài có thể còn lưu domain Handfree cũ trong storage. Chỉ migrate
          // đúng giá trị legacy; URL dev/tùy chỉnh khác của đội triển khai vẫn giữ nguyên.
          if (v) {
            chrome.storage.local.set({ [TLND_BASE_URL_KEY]: TLND_DEFAULT_BASE_URL });
          }
          return resolve(TLND_DEFAULT_BASE_URL);
        }
        resolve(v);
      });
    } catch (_) {
      resolve(TLND_DEFAULT_BASE_URL);
    }
  });
}

//   https://host → wss://host   ·   http://host:8010 → ws://host:8010
function tlndWsBase(httpBase) {
  const base = String(httpBase || "").replace(/\/+$/, "");
  if (base.startsWith("https://")) return "wss://" + base.slice("https://".length);
  if (base.startsWith("http://")) return "ws://" + base.slice("http://".length);
  return base;
}

window.tlndBaseUrl = tlndBaseUrl;
window.tlndWsBase = tlndWsBase;
window.TLND_DEFAULT_BASE_URL = TLND_DEFAULT_BASE_URL;
