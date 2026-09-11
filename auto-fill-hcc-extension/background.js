// Background runtime xử lý click extension icon (Chrome service worker / Firefox event page).
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
// Mỗi tab hồ sơ mới giữ một bundle riêng; chữ ký có thể gồm tài liệu STT1 + CCCD dùng chung ở STT2.
const PENDING_ATTACH_KEY = "autofill_pending_attach";
const SPLIT_ATTACH_QUEUE_KEY = "autofill_split_attach_queue";
const SPLIT_ATTACH_QUEUE_STAGE_KEY = "autofill_split_attach_queue_stage";
const SPLIT_ATTACH_PROGRESS_KEY = "autofill_split_attach_progress";
const SPLIT_ATTACH_PROGRESS_TTL_MS = 24 * 60 * 60 * 1000;

async function getPendingMap() {
  try {
    const res = await chrome.storage.local.get(PENDING_ATTACH_KEY);
    return res[PENDING_ATTACH_KEY] || {};
  } catch (e) { return {}; }
}
async function setPendingMap(map) {
  try {
    await chrome.storage.local.set({ [PENDING_ATTACH_KEY]: map });
    return true;
  } catch (e) {
    return false;
  }
}

async function getSplitAttachQueue() {
  try {
    const res = await chrome.storage.local.get(SPLIT_ATTACH_QUEUE_KEY);
    return res[SPLIT_ATTACH_QUEUE_KEY] || null;
  } catch (e) { return null; }
}
async function setSplitAttachQueue(state) {
  try {
    await chrome.storage.local.set({ [SPLIT_ATTACH_QUEUE_KEY]: state });
    return true;
  } catch (e) { return false; }
}
async function clearSplitAttachQueue() {
  try { await chrome.storage.local.remove(SPLIT_ATTACH_QUEUE_KEY); }
  catch (e) { /* ignore */ }
}

async function getSplitAttachProgress() {
  try {
    const res = await chrome.storage.local.get(SPLIT_ATTACH_PROGRESS_KEY);
    return res[SPLIT_ATTACH_PROGRESS_KEY] || null;
  } catch (e) { return null; }
}

async function setSplitAttachProgress(progress) {
  try {
    await chrome.storage.local.set({
      [SPLIT_ATTACH_PROGRESS_KEY]: {
        ...progress,
        updatedAt: Date.now(),
        expiresAt: Date.now() + SPLIT_ATTACH_PROGRESS_TTL_MS,
      },
    });
    return true;
  } catch (e) { return false; }
}

async function updateSplitAttachProgress(state, patch = {}) {
  if (!state?.runId) return false;
  const current = await getSplitAttachProgress();
  if (!current || current.runId !== state.runId) return false;
  return await setSplitAttachProgress({ ...current, ...patch });
}

async function recordSplitAttachProgressResult(state, result = {}, ordinal = null) {
  const current = await getSplitAttachProgress();
  if (!current || !state?.runId || current.runId !== state.runId) return false;
  const ok = result.ok === true;
  return await setSplitAttachProgress({
    ...current,
    status: "running",
    completed: Math.min(Number(current.total) || 0, (Number(current.completed) || 0) + 1),
    succeeded: (Number(current.succeeded) || 0) + (ok ? 1 : 0),
    failed: (Number(current.failed) || 0) + (ok ? 0 : 1),
    activeOrdinal: null,
    lastResult: {
      ordinal: Number(ordinal) || null,
      ok,
      code: result.code || null,
      error: result.error || null,
    },
  });
}

// Mọi mutation của queue đi qua một chuỗi Promise để clear/đóng tab không thể cùng lúc mở hai tab.
let splitQueueMutation = Promise.resolve();
function withSplitQueueLock(task) {
  const run = splitQueueMutation.then(task, task);
  splitQueueMutation = run.catch(() => {});
  return run;
}

async function openNextSplitQueueItemUnlocked() {
  let state = await getSplitAttachQueue();
  if (!state) return { done: true };
  if (state.activeTabId) return { waiting: true, tabId: state.activeTabId };

  while (Array.isArray(state.remaining) && state.remaining.length) {
    const item = state.remaining.shift();
    let tab = null;
    try {
      const files = Array.isArray(item?.files) ? item.files.filter(Boolean) : [];
      const attachments = Array.isArray(item?.attachments) ? item.attachments.filter(Boolean) : [];
      if (!item?.url || !files.length || !attachments.length) {
        throw new Error("Bundle tách hồ sơ không đủ URL/file/kế hoạch đính kèm.");
      }

      // Modal Radix/React không ổn định trong tab nền. Chỉ tạo DUY NHẤT một tab và kích hoạt nó;
      // tab kế tiếp chỉ được tạo khi content báo thành công hoặc thất bại terminal.
      tab = await chrome.tabs.create({ url: "about:blank", active: true });
      const pendingMap = await getPendingMap();
      pendingMap[tab.id] = {
        files,
        attachments,
        procedure: item.procedure,
        ts: Date.now(),
      };
      // Tab tách là hồ sơ RIÊNG trên cổng nhưng cùng LƯỢT đính kèm → gieo khóa hồ sơ gốc vào
      // session của tab để cú bấm "Gửi hồ sơ" ở đây báo về được. Không gieo thì
      // reportDossierSubmitClick không thấy khóa và bỏ im lặng → mất hết hồ sơ tách.
      if (item.dossierId) {
        await chrome.storage.local.set({
          ["autofill_session_" + tab.id]: { dossierId: item.dossierId },
        });
      }
      if (!await setPendingMap(pendingMap)) throw new Error("Không lưu được bundle đính kèm cho tab kế tiếp.");

      state.activeTabId = tab.id;
      state.activeItem = { ordinal: item.ordinal || null };
      if (!await setSplitAttachQueue(state)) throw new Error("Không lưu được trạng thái hàng đợi tách hồ sơ.");
      await updateSplitAttachProgress(state, {
        status: "running",
        activeOrdinal: Number(item.ordinal) || null,
        paused: null,
      });
      await chrome.tabs.update(tab.id, { url: item.url, active: true });
      console.log("[AutoFill-SplitQueue] Bắt đầu bundle", item.ordinal || "?", {
        tabId: tab.id,
        remaining: state.remaining.length,
        procedure: item.procedure,
      });
      return { ok: true, tabId: tab.id, remaining: state.remaining.length };
    } catch (e) {
      if (tab?.id != null) {
        const pendingMap = await getPendingMap();
        if (pendingMap[tab.id]) { delete pendingMap[tab.id]; await setPendingMap(pendingMap); }
        try { await chrome.tabs.remove(tab.id); } catch (_) { /* ignore */ }
      }
      state.activeTabId = null;
      state.activeItem = null;
      state.results = Array.isArray(state.results) ? state.results : [];
      const failedResult = { ok: false, ordinal: item?.ordinal || null, error: e?.message || String(e) };
      state.results.push(failedResult);
      await recordSplitAttachProgressResult(state, failedResult, item?.ordinal || null);
      if (!await setSplitAttachQueue(state)) break;
    }
  }

  const progress = await getSplitAttachProgress();
  if (progress && state?.runId && progress.runId === state.runId) {
    await setSplitAttachProgress({
      ...progress,
      status: "completed",
      completed: Number(progress.total) || Number(progress.completed) || 0,
      activeOrdinal: null,
      paused: null,
    });
  }
  await clearSplitAttachQueue();
  console.log("[AutoFill-SplitQueue] Đã xử lý hết hàng đợi.", state?.results || []);
  return { done: true, results: state?.results || [] };
}

async function finishSplitQueueTabUnlocked(tabId, result = {}) {
  const state = await getSplitAttachQueue();
  if (!state || Number(state.activeTabId) !== Number(tabId)) return { queueAdvanced: false };
  state.results = Array.isArray(state.results) ? state.results : [];
  state.results.push({
    ok: result.ok === true,
    ordinal: state.activeItem?.ordinal || null,
    code: result.code || null,
    error: result.error || null,
  });
  state.activeTabId = null;
  state.activeItem = null;
  delete state.paused;
  await recordSplitAttachProgressResult(state, result, state.results[state.results.length - 1]?.ordinal || null);
  if (!await setSplitAttachQueue(state)) return { queueAdvanced: false, error: "Không lưu được kết quả tab." };
  console.log("[AutoFill-SplitQueue] Kết thúc bundle", state.results[state.results.length - 1]);
  // Cho cổng giải phóng request/session của tab vừa xong trước khi khởi tạo eForm tiếp theo.
  await new Promise((resolve) => setTimeout(resolve, 800));
  const next = await openNextSplitQueueItemUnlocked();
  return { queueAdvanced: true, next };
}

// Cho phép content script / popup-iframe lấy tabId của chính nó.
// Dọn state theo tab khi tab đóng (key panel + session lưu theo tabId, tránh tồn đọng storage).
chrome.tabs.onRemoved.addListener(async (tabId) => {
  try {
    chrome.storage.local.remove([
      "autofill_panel_open_" + tabId,
      "autofill_session_" + tabId,
    ]);
    await withSplitQueueLock(async () => {
      const map = await getPendingMap();
      if (map[tabId]) { delete map[tabId]; await setPendingMap(map); }
      await finishSplitQueueTabUnlocked(tabId, { ok: false, code: "tab-closed", error: "Tab hồ sơ đã bị đóng." });
    });
  } catch (e) { /* ignore */ }
});

// Mốc "bấm Gửi hồ sơ" từ content script → BE. Xử ở background chứ không ở popup vì popup có
// thể đã đóng lúc cán bộ bấm nộp; background thì luôn sống dậy được.
// SUBMIT_WATCH_KEY khai lại ở đây (service worker không nạp api/config.js) — sửa thì sửa cả hai.
const SUBMIT_WATCH_KEY = "autofill_submit_watch";

async function reportDossierSubmitClick(tabId, host, ref) {
  if (!tabId) return;
  const sessionKey = "autofill_session_" + tabId;
  const store = await chrome.storage.local.get([sessionKey, SUBMIT_WATCH_KEY, "auth_tokens"]);
  const session = store?.[sessionKey];
  const dossierId = String(session?.dossierId || "").trim();
  // Chưa có khóa = extension chưa điền/đính kèm gì cho hồ sơ này → không có gì để chấm.
  // Cố ý: báo cáo chỉ tính hồ sơ trợ lý có tham gia.
  if (!dossierId) return;
  const base = String(store?.[SUBMIT_WATCH_KEY]?.base || "").replace(/\/+$/, "");
  const accessToken = store?.auth_tokens?.accessToken;
  if (!base || !accessToken) return;
  try {
    await fetch(base + "/api/v1/dossiers/submit-click", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + accessToken },
      body: JSON.stringify({ dossierId, portalHost: host || "", portalDossierRef: ref || "" }),
    });
  } catch (e) {
    console.warn("[BG] Không báo được mốc nộp hồ sơ:", e?.message || e);
    return; // giữ khóa để lần bấm sau còn cơ hội ghi
  }
  // GIỮ khóa, chỉ đánh dấu đã nộp: chứng thực tách nhiều tab còn bấm nộp tiếp trên chính khóa
  // này và mỗi lần là một sự kiện. Khóa mới sinh ở LƯỢT process/đính kèm kế tiếp (popup.js
  // ensureDossierId), tức khi cán bộ bắt đầu hồ sơ khác.
  await chrome.storage.local.set({ [sessionKey]: { ...session, dossierSubmitted: true } });
  try {
    await chrome.runtime.sendMessage({ action: "dossierSubmitted", tabId });
  } catch (_) { /* popup không mở → bỏ qua */ }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "getTabId") {
    sendResponse({ tabId: sender?.tab?.id ?? null });
    return true;
  }
  if (msg?.action === "dossierSubmitClicked") {
    void reportDossierSubmitClick(sender?.tab?.id, msg.host, msg.ref);
    sendResponse?.({ ok: true });
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

  // Tải 1 ảnh (nhị phân) từ BE → dataURL base64. apiFetch trả text làm HỎNG nhị phân,
  // nên ảnh phiên QR dùng riêng handler này. GET mở (guard bằng sid bí mật, không cần token).
  if (msg?.action === "fetchImageDataUrl") {
    (async () => {
      try {
        const res = await fetch(msg.url, { headers: msg.headers || {} });
        if (!res.ok) return sendResponse({ error: `HTTP ${res.status}` });
        const blob = await res.blob();
        const dataUrl = await new Promise((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(r.result);
          r.onerror = () => reject(r.error);
          r.readAsDataURL(blob);
        });
        sendResponse({ ok: true, dataUrl, type: blob.type });
      } catch (e) {
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true;
  }

  // ===== Điều phối tách hồ sơ (split) =====
  if (msg?.action === "stageDossierTabAttach") {
    (async () => {
      const tabId = Number(msg.tabId);
      try {
        if (!Number.isInteger(tabId) || tabId <= 0) throw new Error("Không xác định được tab hồ sơ hiện tại.");
        await chrome.tabs.get(tabId); // xác nhận tab vẫn còn trước khi ghi pending
        const files = Array.isArray(msg.files) && msg.files.length ? msg.files : (msg.file ? [msg.file] : []);
        const attachments = Array.isArray(msg.attachments) && msg.attachments.length
          ? msg.attachments
          : (msg.planItem ? [msg.planItem] : []);
        if (!files.length || !attachments.length) throw new Error("Thiếu bộ file/kế hoạch phục hồi cho tab hiện tại.");
        const map = await getPendingMap();
        map[tabId] = {
          files,
          attachments,
          procedure: msg.procedure,
          ts: Date.now(),
          // Lượt reload chuyển từ thao tác trực tiếp sang state machine được tính là lượt đầu tiên.
          recoveryCode: msg.recoveryCode || null,
          recoveryCount: msg.recoveryCode ? 1 : 0,
        };
        if (!await setPendingMap(map)) throw new Error("Không lưu được hàng đợi phục hồi cho tab hiện tại.");
        sendResponse({ ok: true, tabId, ts: map[tabId].ts });
      } catch (e) {
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true;
  }
  if (msg?.action === "reloadDossierTabAttach") {
    (async () => {
      const tabId = Number(msg.tabId);
      try {
        if (!Number.isInteger(tabId) || tabId <= 0) throw new Error("Không xác định được tab cần tải lại.");
        const map = await getPendingMap();
        if (!map[tabId]) throw new Error("Tab hiện tại chưa có hàng đợi đính kèm để phục hồi.");
        await chrome.tabs.reload(tabId);
        sendResponse({ ok: true, tabId });
      } catch (e) {
        await withSplitQueueLock(async () => {
          const map = await getPendingMap();
          if (map[tabId]) { delete map[tabId]; await setPendingMap(map); }
          await finishSplitQueueTabUnlocked(tabId, {
            ok: false,
            code: "tab-reload-failed",
            error: e?.message || String(e),
          });
        });
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true;
  }
  if (msg?.action === "startSplitAttachQueue") {
    (async () => {
      let itemsStorageKey = "";
      try {
        itemsStorageKey = String(msg.itemsStorageKey || "");
        let rawItems = msg.items;
        if (itemsStorageKey) {
          if (itemsStorageKey !== SPLIT_ATTACH_QUEUE_STAGE_KEY) {
            throw new Error("Khóa staging của hàng đợi tách hồ sơ không hợp lệ.");
          }
          const staged = await chrome.storage.local.get(itemsStorageKey);
          rawItems = staged?.[itemsStorageKey]?.items;
          if (!Array.isArray(rawItems)) {
            throw new Error("Không đọc được dữ liệu hàng đợi tách hồ sơ từ storage.");
          }
        }
        const items = Array.isArray(rawItems) ? rawItems.filter(Boolean) : [];
        if (!items.length) throw new Error("Hàng đợi tách hồ sơ không có bundle hợp lệ.");
        const waitForTabId = Number(msg.waitForTabId) || null;
        const result = await withSplitQueueLock(async () => {
          if (waitForTabId) {
            await chrome.tabs.get(waitForTabId);
            const pendingMap = await getPendingMap();
            if (!pendingMap[waitForTabId]) {
              throw new Error("Tab hiện tại chưa có bundle phục hồi trước khi bắt đầu hàng đợi.");
            }
          }
          const state = {
            remaining: items,
            activeTabId: waitForTabId,
            activeItem: waitForTabId ? { ordinal: 1 } : null,
            results: [],
            startedAt: Date.now(),
            runId: String(msg.runId || `split-${Date.now()}`),
          };
          const total = Math.max(Number(msg.totalBundles) || 0, items.length + (waitForTabId ? 1 : 0));
          const initialCompleted = Math.max(0, Math.min(total, Number(msg.initialCompleted) || 0));
          const initialSucceeded = Math.max(0, Math.min(initialCompleted, Number(msg.initialSucceeded) || 0));
          if (!await setSplitAttachProgress({
            runId: state.runId,
            originTabId: Number(msg.originTabId) || null,
            procedure: String(msg.procedure || ""),
            status: "running",
            total,
            completed: initialCompleted,
            succeeded: initialSucceeded,
            failed: Math.max(0, initialCompleted - initialSucceeded),
            activeOrdinal: waitForTabId ? 1 : null,
            startedAt: state.startedAt,
            paused: null,
            lastResult: null,
          })) {
            throw new Error("Không lưu được tiến độ hàng đợi tách hồ sơ.");
          }
          if (!await setSplitAttachQueue(state)) throw new Error("Không lưu được hàng đợi tách hồ sơ tuần tự.");
          return waitForTabId
            ? { ok: true, waiting: true, tabId: waitForTabId, remaining: items.length }
            : await openNextSplitQueueItemUnlocked();
        });
        sendResponse(result);
      } catch (e) {
        sendResponse({ error: e?.message || String(e) });
      } finally {
        if (itemsStorageKey) {
          try { await chrome.storage.local.remove(itemsStorageKey); } catch (_) { /* ignore */ }
        }
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
      const tabId = msg.tabId ?? sender?.tab?.id;
      const result = await withSplitQueueLock(async () => {
        const map = await getPendingMap();
        if (tabId != null && map[tabId]) { delete map[tabId]; await setPendingMap(map); }
        return await finishSplitQueueTabUnlocked(tabId, { ok: true });
      });
      sendResponse({ ok: true, ...result });
    })();
    return true;
  }
  if (msg?.action === "pausePendingAttach") {
    (async () => {
      const tabId = msg.tabId ?? sender?.tab?.id;
      const result = await withSplitQueueLock(async () => {
        const state = await getSplitAttachQueue();
        if (!state || Number(state.activeTabId) !== Number(tabId)) {
          return { paused: false };
        }
        // Giữ nguyên pending + activeTabId để không mở tab kế tiếp. Reload thủ công tab này sẽ đọc
        // lại bundle và chạy lại; đóng tab thì onRemoved mới kết thúc bundle lỗi và chuyển tiếp.
        state.paused = {
          tabId,
          code: msg.code || "attach-failed",
          error: msg.error || "Đính kèm thất bại.",
          pausedAt: Date.now(),
        };
        await updateSplitAttachProgress(state, {
          status: "paused",
          activeOrdinal: Number(state.activeItem?.ordinal) || null,
          paused: {
            ordinal: Number(state.activeItem?.ordinal) || null,
            code: msg.code || "attach-failed",
            error: msg.error || "Đính kèm thất bại.",
          },
        });
        const saved = await setSplitAttachQueue(state);
        return { paused: saved, tabId };
      });
      sendResponse({ ok: true, ...result });
    })();
    return true;
  }
  if (msg?.action === "failPendingAttach") {
    (async () => {
      const tabId = msg.tabId ?? sender?.tab?.id;
      const result = await withSplitQueueLock(async () => {
        const map = await getPendingMap();
        if (tabId != null && map[tabId]) { delete map[tabId]; await setPendingMap(map); }
        return await finishSplitQueueTabUnlocked(tabId, {
          ok: false,
          code: msg.code || "attach-failed",
          error: msg.error || "Đính kèm thất bại.",
        });
      });
      sendResponse({ ok: true, ...result });
    })();
    return true;
  }
  if (msg?.action === "clearAllPendingAttach") {
    (async () => {
      await withSplitQueueLock(async () => {
        await setPendingMap({});
        await clearSplitAttachQueue();
        try {
          await chrome.storage.local.remove([SPLIT_ATTACH_QUEUE_STAGE_KEY, SPLIT_ATTACH_PROGRESS_KEY]);
        } catch (_) { /* ignore */ }
      });
      sendResponse({ ok: true });
    })();
    return true;
  }
});

// Kéo file phiên QR về dataURL theo CHUNK qua Port (thay cho fetchImageDataUrl gửi 1 cục).
// chrome.runtime message có trần kích thước (~64MB); file lớn (PDF 65MB → base64 ~87MB) gửi 1
// message sẽ HỤT → popup không nhận được. Port stream từng mảnh nhỏ để vượt trần này.
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "filePull") return;
  port.onMessage.addListener(async (msg) => {
    try {
      // PHẢI có timeout: fetch trần treo vô hạn thì port không bao giờ settle, popup coi như
      // đang kéo dở và KHÔNG thử lại → file "gửi rồi mà không thấy". 60s đủ cho PDF scan qua 4G.
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 60000);
      let res;
      try {
        res = await fetch(msg.url, { headers: msg.headers || {}, signal: ctrl.signal });
      } finally {
        clearTimeout(timer);
      }
      if (!res.ok) {
        console.warn("[BG] Kéo tệp phiên QR lỗi:", res.status, msg.url);
        port.postMessage({ error: `HTTP ${res.status}` });
        return;
      }
      const blob = await res.blob();
      const dataUrl = await new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result);
        r.onerror = () => reject(r.error);
        r.readAsDataURL(blob);
      });
      port.postMessage({ meta: true, type: blob.type });
      const CHUNK = 4 * 1024 * 1024; // 4MB/mảnh — an toàn dưới trần message
      for (let i = 0; i < dataUrl.length; i += CHUNK) {
        port.postMessage({ chunk: dataUrl.slice(i, i + CHUNK) });
      }
      port.postMessage({ done: true });
    } catch (e) {
      try { port.postMessage({ error: e?.message || String(e) }); } catch (_) { /* port đã đóng */ }
    }
  });
});
