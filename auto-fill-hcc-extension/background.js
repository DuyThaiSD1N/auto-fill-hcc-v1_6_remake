// Service worker xử lý click extension icon.
// Bấm icon → gửi message content script (top frame) tab hiện tại để toggle panel nổi.
chrome.action.onClicked.addListener(async (tab) => {
  if (!tab?.id) return;
  try {
    await chrome.tabs.sendMessage(tab.id, { action: "togglePanel" });
  } catch (e) {
    // Content script chưa có / mồ côi sau reload extension → inject lại rồi thử lại.
    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
      await chrome.tabs.sendMessage(tab.id, { action: "togglePanel" });
    } catch (e2) {
      console.warn("[BG] Không mở được panel:", e2?.message || e2);
    }
  }
});

// ===== Tách hồ sơ (split KPI): hàng đợi file chờ đính, keyed theo tabId =====
// Mỗi tab hồ sơ mới giữ đúng 1 file riêng; content.js của tab đó tự lấy & đính khi tới Bước 3.
const PENDING_ATTACH_KEY = "autofill_pending_attach";

async function getPendingMap() {
  try {
    const res = await chrome.storage.local.get(PENDING_ATTACH_KEY);
    return res[PENDING_ATTACH_KEY] || {};
  } catch (e) { return {}; }
}
async function setPendingMap(map) {
  try { await chrome.storage.local.set({ [PENDING_ATTACH_KEY]: map }); } catch (e) { /* ignore */ }
}

// Cho phép content script / popup-iframe lấy tabId của chính nó.
// Dọn state theo tab khi tab đóng (key panel + session lưu theo tabId, tránh tồn đọng storage).
chrome.tabs.onRemoved.addListener(async (tabId) => {
  try {
    chrome.storage.local.remove([
      "autofill_panel_open_" + tabId,
      "autofill_session_" + tabId,
    ]);
    const map = await getPendingMap();
    if (map[tabId]) { delete map[tabId]; await setPendingMap(map); }
  } catch (e) { /* ignore */ }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "getTabId") {
    sendResponse({ tabId: sender?.tab?.id ?? null });
    return true;
  }
  // Proxy fetch: popup-iframe gọi API BE qua background để TRÁNH mixed-content blocking
  // (popup nhúng iframe trên trang HTTPS, fetch http:// bị auto-upgrade → ERR_SSL_PROTOCOL_ERROR).
  // Background SW chạy ở context extension thuần, fetch http:// bình thường.
  if (msg?.action === "apiFetch") {
    (async () => {
      try {
        const init = { method: msg.method || "GET", headers: msg.headers || {} };
        if (msg.body != null) init.body = msg.body;
        const res = await fetch(msg.url, init);
        const body = await res.text();
        sendResponse({ ok: res.ok, status: res.status, body });
      } catch (e) {
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true; // giữ kênh cho phản hồi async
  }

  // ===== Điều phối tách hồ sơ (split) =====
  if (msg?.action === "openDossierTabAndAttach") {
    (async () => {
      try {
        const tab = await chrome.tabs.create({ url: msg.url, active: false });
        const map = await getPendingMap();
        map[tab.id] = { file: msg.file, planItem: msg.planItem, procedure: msg.procedure, ts: Date.now() };
        await setPendingMap(map);
        sendResponse({ ok: true, tabId: tab.id });
      } catch (e) {
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true;
  }
  if (msg?.action === "getPendingAttach") {
    (async () => {
      const map = await getPendingMap();
      sendResponse({ pending: map[sender?.tab?.id] || null });
    })();
    return true;
  }
  if (msg?.action === "clearPendingAttach") {
    (async () => {
      const map = await getPendingMap();
      const tabId = msg.tabId ?? sender?.tab?.id;
      if (tabId != null && map[tabId]) { delete map[tabId]; await setPendingMap(map); }
      sendResponse({ ok: true });
    })();
    return true;
  }
  if (msg?.action === "clearAllPendingAttach") {
    (async () => { await setPendingMap({}); sendResponse({ ok: true }); })();
    return true;
  }
});
