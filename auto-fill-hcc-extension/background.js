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

// Ngưỡng "cán bộ đã rời đi": cửa sổ mất focus VÀ không thao tác gì suốt ngần
// này thì coi như tab đó không còn được dùng. Khớp với NGUONG_NEN_MS bên
// lib/trangThai.js — hai chỗ nói về cùng một thứ, lệch nhau là ra hai kết luận
// khác nhau cho cùng một khoảnh khắc.
const NGUONG_ROI_DI_MS = 15 * 1000;

// Trình duyệt này có trả Promise cho `chrome.*` không? Hỏi thẳng thay vì suy từ
// một giá trị `undefined` mơ hồ. `chrome.tabs.query({})` không tham số callback:
// bản mới trả Promise, bản cũ trả undefined.
function hoTroPromise() {
  try {
    const r = chrome.tabs.query({});
    return !!(r && typeof r.then === "function");
  } catch (e) {
    return false;
  }
}

// Tab nào còn ĐANG ĐƯỢC DÙNG không?
//
// Thay cho phép kiểm cũ "có panel nào đang mở không" — phép đó quá chặt: panel
// mở suốt buổi nên không bao giờ nạp lại được bản mới. Ở đây hỏi thêm trang gốc
// xem cửa sổ có focus, tab có bị ẩn, và im lặng bao lâu rồi.
//
// Tab không trả lời (chưa có content script, hoặc content script đã mồ côi từ
// lần nạp lại trước) coi như KHÔNG được dùng: nó vốn đã hỏng sẵn, nạp lại không
// làm nó tệ thêm, mà cú bấm icon sẽ tự tiêm lại (xem chrome.action.onClicked).
async function coTabNaoDangLamViec() {
  let tabs;
  try { tabs = await chrome.tabs.query({}); } catch (e) { return true; } // không biết thì coi như CÓ
  // Trình duyệt CŨ không trả Promise cho chrome.tabs.query — nó trả `undefined`
  // và KHÔNG ném lỗi. Không chặn ở đây thì `tabs.map` mới ném, ở ngoài try, và
  // cả hàm hỏng theo một đường khó lần. Quan trọng hơn: không biết gì về các tab
  // thì câu trả lời đúng là "coi như đang bận", không phải "rảnh".
  if (!Array.isArray(tabs)) return true;
  const kq = await Promise.all(tabs.map(async (t) => {
    if (!t?.id) return false;
    let r;
    try { r = await chrome.tabs.sendMessage(t.id, { action: "hccTabDangLamViec" }); }
    catch (e) { return false; } // tab không có content script — không có gì để mất
    // `undefined` có HAI nghĩa khác hẳn nhau, phải phân biệt:
    //
    //   - Trình duyệt CŨ (sendMessage chưa trả Promise): mọi tab đều trả
    //     undefined mà không ném lỗi. Không biết gì ⇒ coi là bận.
    //   - Trình duyệt MỚI: undefined nghĩa là tab có người nhận message nhưng
    //     không ai trả lời — ví dụ một TRANG EXTENSION mở dạng tab (popup.html).
    //     Đó không phải panel trên trang cổng, không có gì để mất ⇒ rảnh.
    //
    // Gộp hai ca này lại là chặn vĩnh viễn: chỉ cần mở popup.html thành một tab
    // là không bao giờ tự cập nhật được nữa. Đã gặp thật khi trình diễn.
    if (r === undefined || r === null) return !hoTroPromise();
    if (!r.coPanel) return false;          // không có panel thì không có gì để mất
    if (r.an) return false;                 // tab bị ẩn
    if (!r.focus && Number(r.imLangMs) >= NGUONG_ROI_DI_MS) return false; // đã rời đi
    return true;
  }));
  return kq.some(Boolean);
}

// Gỡ panel ở MỌI tab ngay trước khi nạp lại. Cờ "panel đang mở" trong
// chrome.storage được giữ nguyên nên lần điều hướng kế tiếp panel tự mọc lại.
async function goPanelMoiTab() {
  let tabs = [];
  try { tabs = await chrome.tabs.query({}); } catch (e) { return; }
  await Promise.all(tabs.map(async (t) => {
    if (!t?.id) return;
    try { await chrome.tabs.sendMessage(t.id, { action: "hccGoPanelTruocKhiNapLai" }); }
    catch (e) { /* tab khong co content script - khong sao */ }
  }));
}


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

// Cờ "cần hỏi đánh giá", theo KHÓA HỒ SƠ chứ không theo tab.
// - theo hồ sơ: chứng thực tách nhiều tab dùng CHUNG một dossierId và tab nào cũng bấm nộp —
//   đánh dấu theo tab thì cán bộ bị hỏi 4 lần cho 1 hồ sơ.
// - vào storage chứ không giữ trong RAM của popup: bấm nộp xong trang thường điều hướng/postback
//   ngay (HkdOnline là full postback), panel dựng lại là mất sạch trạng thái trong RAM.
const RATING_PENDING_KEY = "autofill_rating_pending";
const RATING_DONE_KEY = "autofill_rating_done";
// Trần danh sách hồ sơ ĐÃ hỏi: chỉ để chống hỏi lại, không phải dữ liệu cần giữ lâu.
const RATING_DONE_MAX = 200;

async function markRatingPending(dossierId, tabId) {
  if (!dossierId) return false;
  const store = await chrome.storage.local.get([RATING_PENDING_KEY, RATING_DONE_KEY]);
  const done = Array.isArray(store?.[RATING_DONE_KEY]) ? store[RATING_DONE_KEY] : [];
  // Đã hỏi rồi thì thôi — kể cả khi cán bộ bấm nộp thêm lần nữa trên chính hồ sơ đó.
  if (done.includes(dossierId)) return false;
  const pending = store?.[RATING_PENDING_KEY];
  if (pending?.dossierId === dossierId) return true; // đã chờ sẵn, không ghi đè mốc cũ
  await chrome.storage.local.set({
    [RATING_PENDING_KEY]: { dossierId, tabId: tabId ?? null, at: Date.now() },
  });
  return true;
}

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
  // Bấm nộp = coi như đã nộp. Không chờ cổng báo "thành công": câu chữ đó khác nhau theo cổng
  // và chỉ thu thập được bằng cách nộp hồ sơ thật, nên chờ nó là không bao giờ hỏi được ở
  // phần lớn cổng. Đổi lại: có thể hỏi cả khi cổng báo thiếu giấy tờ — chấp nhận.
  await markRatingPending(dossierId, tabId);
  try {
    await chrome.runtime.sendMessage({ action: "dossierSubmitted", tabId, dossierId });
  } catch (_) { /* panel chưa dựng lại sau điều hướng → cờ ở storage lo tiếp */ }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "hccCoTabNaoDangLamViec") {
    coTabNaoDangLamViec().then((co) => sendResponse({ co }));
    return true;
  }
  if (msg?.action === "hccGoPanelMoiTab") {
    goPanelMoiTab().then(() => sendResponse({ ok: true }));
    return true;
  }
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

// ===== Tự cập nhật: kiểm tra ở BACKGROUND, không phụ thuộc panel =====
//
// Bản đầu đặt phép kiểm trong panel (`popup.js`), mà panel chỉ nối tới agent khi
// cán bộ đã mở nó và chọn thủ tục trên trang cổng (`ensureScanAgentConnected`
// chỉ được gọi từ `selectProcedure`). Máy nào cài xong rồi để đó thì extension
// KHÔNG BAO GIỜ biết có bản mới — đo 2026-09-12: đĩa đã có 1.17.0.16 mà trình
// duyệt vẫn đứng ở 1.17.0.15 sau 45 giây.
//
// Service worker thì luôn được `chrome.alarms` đánh thức, không cần ai mở gì.
const ALARM_CAP_NHAT = "hcc-kiem-ban-moi";
const NHIP_KIEM_PHUT = 1;
// Máy không có thao tác nào suốt ngần này thì coi là rảnh. Đây chính là "chờ nó
// không hoạt động bao lâu rồi mới cập nhật" — nạp lại giữa lúc cán bộ đang làm
// là cắt ngang công việc, mà thứ đang chờ chỉ là một bản vá.
const NGUONG_RANH_GIAY = 60;
const CONG_AGENT = [28147, 28148, 28149, 28150, 28151];

function datLichKiemBanMoi() {
  try { chrome.alarms.create(ALARM_CAP_NHAT, { periodInMinutes: NHIP_KIEM_PHUT }); }
  catch (e) { console.warn("[BG] khong dat duoc lich kiem ban moi:", e); }
}
chrome.runtime.onInstalled.addListener(datLichKiemBanMoi);
chrome.runtime.onStartup.addListener(datLichKiemBanMoi);
datLichKiemBanMoi(); // và ngay khi service worker vừa dậy

chrome.alarms.onAlarm.addListener((a) => {
  if (a?.name === ALARM_CAP_NHAT) void kiemBanMoi();
});

// ── Nút "Cập nhật" chủ động trên panel ──────────────────────────────────────
// Mặc định vẫn là tự nạp lại khi máy rảnh NGUONG_RANH_GIAY giây (kiemBanMoi) — bao được đa số ca. Cán bộ
// ngồi làm liên tục thì có khi cả buổi không rảnh, nên mỗi nhịp kiểm ghi "bản mới đang chờ" vào storage;
// panel đọc + nghe storage.onChanged để hiện nút cho cán bộ tự chọn lúc cập nhật.
const KHOA_BAN_CHO = "hcc_ban_moi_cho";                  // { version, luc }
const KHOA_TAI_LAI_TAB = "hcc_tai_lai_tab_sau_cap_nhat"; // { tabId, luc }
const TUOI_TAI_LAI_TAB_MS = 2 * 60 * 1000;

async function ghiBanCho(version) {
  try {
    const cu = (await chrome.storage.local.get(KHOA_BAN_CHO))?.[KHOA_BAN_CHO];
    // Cùng bản thì khỏi ghi lại mỗi phút — mỗi lần ghi là một storage.onChanged bắn tới mọi panel.
    if (cu && cu.version === version) return;
    await chrome.storage.local.set({ [KHOA_BAN_CHO]: { version, luc: Date.now() } });
  } catch (e) { /* mất nút thì chỉ là chờ tới lúc máy rảnh như cũ */ }
}

async function boBanCho() {
  try { await chrome.storage.local.remove(KHOA_BAN_CHO); } catch (e) { /* ignore */ }
}

// Panel vừa nghe agent báo có bản mới trên đĩa → kiểm NGAY, khỏi chờ nhịp 1 phút. kiemBanMoi tự giữ mọi
// luật "chỉ nạp lại khi rảnh", nên gọi thêm lần nào cũng an toàn.
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.action === "hccKiemBanMoiNgay") void kiemBanMoi();
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action !== "hccCapNhatNgay") return;
  (async () => {
    const d = await hoiAgent();
    const trenDia = d?.ext_versions?.[chrome.runtime.id];
    // Chỉ nạp lại khi trên đĩa THẬT SỰ có bản khác. Nút còn treo sau khi đã lên bản rồi thì thôi — nạp lại
    // vô ích là tải lại trang cổng oan.
    if (typeof trenDia !== "string" || !trenDia || trenDia === chrome.runtime.getManifest().version) {
      if (d) await boBanCho();
      sendResponse({ ok: false, lyDo: d ? "da-moi-nhat" : "khong-thay-agent" });
      return;
    }
    const tabId = Number(msg.tabId) || sender?.tab?.id || 0;
    if (tabId) {
      try { await chrome.storage.local.set({ [KHOA_TAI_LAI_TAB]: { tabId, luc: Date.now() } }); }
      catch (e) { /* không tải lại được tab thì panel mọc lại ở lần điều hướng kế tiếp */ }
    }
    sendResponse({ ok: true, version: trenDia });
    // Cán bộ đã xác nhận nên KHÔNG hỏi mayDangRanh / coTabNaoDangLamViec nữa. Gỡ panel khắp nơi trước (nạp
    // lại không làm panel biến mất, chỉ làm nó chết bên trong), rồi nạp lại.
    await goPanelMoiTab();
    console.info("[BG] Can bo bam Cap nhat - nap lai de len ban", trenDia);
    setTimeout(() => chrome.runtime.reload(), 150); // để câu trả lời kịp về panel
  })();
  return true;
});

// Service worker MỚI sau khi nạp lại: tải lại đúng tab cán bộ vừa bấm "Cập nhật". Content script bản mới
// chỉ được tiêm khi trang tải lại; cờ "panel đang mở" vẫn giữ nên panel mọc lại như trước. Chỉ tin mốc còn
// mới — mốc sót lại (trình duyệt tắt ngang) không được tải lại trang oan lúc mở máy hôm sau.
(async () => {
  try {
    const kho = await chrome.storage.local.get([KHOA_TAI_LAI_TAB, KHOA_BAN_CHO]);
    if (kho?.[KHOA_BAN_CHO]?.version === chrome.runtime.getManifest().version) await boBanCho();
    const r = kho?.[KHOA_TAI_LAI_TAB];
    if (!r) return;
    await chrome.storage.local.remove(KHOA_TAI_LAI_TAB);
    if (Date.now() - Number(r.luc || 0) > TUOI_TAI_LAI_TAB_MS) return;
    await chrome.tabs.reload(Number(r.tabId));
  } catch (e) {
    console.warn("[BG] Khong tai lai duoc tab sau khi cap nhat:", e?.message || e);
  }
})();

// Dò agent trên dải cổng của nó. KHÔNG cần token: /v1/ping là endpoint duy nhất
// không xác thực, và agent trả Access-Control-Allow-Origin: * nên service worker
// gọi được bằng CORS thường, không cần host_permissions cho 127.0.0.1.
async function hoiAgent() {
  // Kèm version ĐANG CHẠY của chính mình: agent chuyển lên CMS để trang Máy biết
  // Chrome đang chạy bản nào (khác bản trên đĩa khi chưa nạp lại). Agent bản cũ
  // bỏ qua query lạ, phản hồi ping không đổi (scan-bridge docs/local-api.md §1).
  const truyVan = `ext_id=${encodeURIComponent(chrome.runtime.id)}` +
    `&ext_ver=${encodeURIComponent(chrome.runtime.getManifest().version)}`;
  for (const cong of CONG_AGENT) {
    try {
      const ctrl = new AbortController();
      const hen = setTimeout(() => ctrl.abort(), 800);
      const res = await fetch(`http://127.0.0.1:${cong}/v1/ping?${truyVan}`, { signal: ctrl.signal });
      clearTimeout(hen);
      if (!res.ok) continue;
      const d = await res.json();
      if (d && d.app === "scan-bridge-agent") return d;
    } catch (e) { /* cổng này không có agent — thử cổng sau */ }
  }
  return null;
}

// Máy có đang rảnh không — theo thao tác chuột/phím của CẢ MÁY, không chỉ tab này.
async function mayDangRanh() {
  try {
    const tt = await chrome.idle.queryState(NGUONG_RANH_GIAY);
    return tt === "idle" || tt === "locked";
  } catch (e) {
    return false; // hỏi không được thì coi như đang dùng
  }
}

async function kiemBanMoi() {
  const d = await hoiAgent();
  if (!d) return;
  // Tra version CỦA CHÍNH MÌNH bằng chrome.runtime.id — agent giữ nhiều
  // extension, mỗi cái một version.
  const trenDia = d.ext_versions && d.ext_versions[chrome.runtime.id];
  if (typeof trenDia !== "string" || !trenDia) return;
  if (trenDia === chrome.runtime.getManifest().version) { await boBanCho(); return; }
  // Có bản mới đang chờ → panel hiện nút "Cập nhật" (cán bộ đang làm thì còn lâu mới tới lúc máy rảnh).
  await ghiBanCho(trenDia);

  if (!(await mayDangRanh())) return;
  if (await coTabNaoDangLamViec()) return;

  // Gỡ panel khắp nơi trước khi nạp lại: nạp lại KHÔNG làm panel biến mất, nó
  // chỉ chết bên trong (xem coTabNaoDangLamViec). Gỡ đi thì hỏng thành nhìn
  // thấy được, và cờ panelOpenKey được giữ nên panel tự mọc lại ở lần điều
  // hướng kế tiếp.
  await goPanelMoiTab();
  console.info("[BG] Nap lai de len ban", trenDia);
  chrome.runtime.reload();
}
