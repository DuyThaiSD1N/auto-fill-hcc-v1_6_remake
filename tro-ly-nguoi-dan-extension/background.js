// Service worker — bấm icon extension → mở/đóng khung Trợ lý (floating panel) trên trang.

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab?.id) return;
  try {
    await chrome.tabs.sendMessage(tab.id, { action: "togglePanel" });
  } catch (e) {
    // Trang không có content script (chrome://, file:// ...) — bỏ qua.
    console.warn("[BG] Không gửi được togglePanel:", e?.message || e);
  }
});

// Cho khung Trợ lý (popup chạy trong iframe) lấy tabId của chính nó.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "getTabId") {
    sendResponse({ tabId: sender?.tab?.id ?? null });
    return true;
  }
});

// ───────────── Tách hồ sơ chứng thực: queue tuần tự, bền qua MV3 service-worker sleep ─────────────
// Không truyền dataUrl của cả queue qua runtime message (có thể vượt trần ~64 MiB). Sidebar staging
// bundle trong storage; background chỉ nhận key nhẹ, mỗi lúc mở đúng MỘT tab active.
const PENDING_ATTACH_KEY = "tro_ly_pending_attach";
const SPLIT_ATTACH_QUEUE_KEY = "tro_ly_split_attach_queue";
const SPLIT_ATTACH_QUEUE_STAGE_KEY = "tro_ly_split_attach_queue_stage";

async function getPendingMap() {
  try {
    const res = await chrome.storage.local.get(PENDING_ATTACH_KEY);
    return res[PENDING_ATTACH_KEY] || {};
  } catch (_) { return {}; }
}

async function setPendingMap(map) {
  try {
    await chrome.storage.local.set({ [PENDING_ATTACH_KEY]: map });
    return true;
  } catch (_) { return false; }
}

async function getSplitAttachQueue() {
  try {
    const res = await chrome.storage.local.get(SPLIT_ATTACH_QUEUE_KEY);
    return res[SPLIT_ATTACH_QUEUE_KEY] || null;
  } catch (_) { return null; }
}

async function setSplitAttachQueue(state) {
  try {
    await chrome.storage.local.set({ [SPLIT_ATTACH_QUEUE_KEY]: state });
    return true;
  } catch (_) { return false; }
}

let splitQueueMutation = Promise.resolve();
function withSplitQueueLock(task) {
  const run = splitQueueMutation.then(task, task);
  splitQueueMutation = run.catch(() => {});
  return run;
}

function splitQueueSummary(state) {
  if (!state) return null;
  const results = Array.isArray(state.results) ? state.results : [];
  return {
    queueId: state.queueId,
    status: state.status || "running",
    total: Number(state.total) || 0,
    completed: results.length,
    succeeded: results.filter((r) => r?.ok).length,
    failed: results.filter((r) => !r?.ok).length,
    activeOrdinal: state.activeItem?.ordinal || null,
    results,
    startedAt: state.startedAt || null,
    completedAt: state.completedAt || null,
  };
}

async function completeSplitQueueUnlocked(state) {
  state.status = "done";
  state.activeTabId = null;
  state.activeItem = null;
  state.remaining = [];
  state.completedAt = Date.now();
  state.updatedAt = Date.now();
  await setSplitAttachQueue(state); // giữ summary nhẹ để sidebar đóng/mở lại vẫn báo kết quả được
  console.log("[TLND-SplitQueue] Hoàn tất", splitQueueSummary(state));
  return { done: true, summary: splitQueueSummary(state) };
}

async function openNextSplitQueueItemUnlocked() {
  let state = await getSplitAttachQueue();
  if (!state) return { done: true };
  if (state.status === "done") return { done: true, summary: splitQueueSummary(state) };
  if (state.activeTabId) return { waiting: true, tabId: state.activeTabId };

  while (Array.isArray(state.remaining) && state.remaining.length) {
    const item = state.remaining.shift();
    let tab = null;
    try {
      const files = Array.isArray(item?.files) ? item.files.filter(Boolean) : [];
      const attachments = Array.isArray(item?.attachments) ? item.attachments.filter(Boolean) : [];
      if (!item?.url || !files.length || !attachments.length) {
        throw new Error("Bundle tách hồ sơ không đủ URL, file hoặc kế hoạch đính kèm.");
      }

      // Lưu pending + activeTabId TRƯỚC khi điều hướng để content không thể đọc hụt bundle.
      tab = await chrome.tabs.create({ url: "about:blank", active: true });
      const pending = await getPendingMap();
      pending[tab.id] = {
        queueId: state.queueId,
        ordinal: item.ordinal || null,
        files,
        attachments,
        procedure: item.procedure,
        ts: Date.now(),
      };
      if (!await setPendingMap(pending)) throw new Error("Không lưu được bundle cho tab mới.");
      state.activeTabId = tab.id;
      state.activeItem = { ordinal: item.ordinal || null };
      state.updatedAt = Date.now();
      if (!await setSplitAttachQueue(state)) throw new Error("Không lưu được trạng thái queue.");
      await chrome.tabs.update(tab.id, { url: item.url, active: true });
      return { ok: true, tabId: tab.id, remaining: state.remaining.length };
    } catch (e) {
      if (tab?.id != null) {
        const pending = await getPendingMap();
        delete pending[tab.id];
        await setPendingMap(pending);
        try { await chrome.tabs.remove(tab.id); } catch (_) { /* bỏ qua */ }
      }
      state.activeTabId = null;
      state.activeItem = null;
      state.results = Array.isArray(state.results) ? state.results : [];
      state.results.push({ ok: false, ordinal: item?.ordinal || null,
        code: "open-tab-failed", error: e?.message || String(e) });
      state.updatedAt = Date.now();
      if (!await setSplitAttachQueue(state)) break;
    }
  }
  return await completeSplitQueueUnlocked(state);
}

async function finishSplitQueueTabUnlocked(tabId, result = {}) {
  const state = await getSplitAttachQueue();
  if (!state || state.status === "done" || Number(state.activeTabId) !== Number(tabId)) {
    return { queueAdvanced: false };
  }
  state.results = Array.isArray(state.results) ? state.results : [];
  state.results.push({
    ok: result.ok === true,
    ordinal: state.activeItem?.ordinal || null,
    code: result.code || null,
    error: result.error || null,
  });
  state.activeTabId = null;
  state.activeItem = null;
  state.updatedAt = Date.now();
  if (!await setSplitAttachQueue(state)) return { queueAdvanced: false, error: "Không lưu được kết quả tab." };
  await new Promise((resolve) => setTimeout(resolve, 800));
  return { queueAdvanced: true, next: await openNextSplitQueueItemUnlocked() };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "prepareSplitAttachQueue") {
    (async () => {
      const current = await getSplitAttachQueue();
      if (current?.status === "running") {
        sendResponse({ error: "Đang có một lượt tách hồ sơ khác chưa hoàn tất." });
        return;
      }
      await setPendingMap({});
      await chrome.storage.local.remove([SPLIT_ATTACH_QUEUE_KEY, SPLIT_ATTACH_QUEUE_STAGE_KEY]);
      sendResponse({ ok: true });
    })();
    return true;
  }
  if (msg?.action === "stageDossierTabAttach") {
    (async () => {
      try {
        const tabId = Number(msg.tabId);
        if (!Number.isInteger(tabId) || tabId <= 0) throw new Error("Không xác định được tab hiện tại.");
        await chrome.tabs.get(tabId);
        const files = Array.isArray(msg.files) ? msg.files.filter(Boolean) : [];
        const attachments = Array.isArray(msg.attachments) ? msg.attachments.filter(Boolean) : [];
        if (!files.length || !attachments.length) throw new Error("Thiếu bundle phục hồi cho tab hiện tại.");
        const pending = await getPendingMap();
        pending[tabId] = {
          queueId: msg.queueId,
          ordinal: 1,
          files,
          attachments,
          procedure: msg.procedure,
          ts: Date.now(),
          recoveryCode: msg.recoveryCode || null,
          recoveryCount: msg.recoveryCode ? 1 : 0,
        };
        if (!await setPendingMap(pending)) throw new Error("Không lưu được bundle phục hồi.");
        sendResponse({ ok: true, tabId });
      } catch (e) { sendResponse({ error: e?.message || String(e) }); }
    })();
    return true;
  }
  if (msg?.action === "reloadDossierTabAttach") {
    (async () => {
      const tabId = Number(msg.tabId);
      try {
        const pending = await getPendingMap();
        if (!pending[tabId]) throw new Error("Tab chưa có bundle phục hồi.");
        await chrome.tabs.reload(tabId);
        sendResponse({ ok: true, tabId });
      } catch (e) {
        await withSplitQueueLock(async () => {
          const pending = await getPendingMap();
          if (pending[tabId]) { delete pending[tabId]; await setPendingMap(pending); }
          await finishSplitQueueTabUnlocked(tabId, {
            ok: false, code: "tab-reload-failed", error: e?.message || String(e),
          });
        });
        sendResponse({ error: e?.message || String(e) });
      }
    })();
    return true;
  }
  if (msg?.action === "startSplitAttachQueue") {
    (async () => {
      const itemsStorageKey = String(msg.itemsStorageKey || "");
      try {
        if (itemsStorageKey !== SPLIT_ATTACH_QUEUE_STAGE_KEY) throw new Error("Khóa staging không hợp lệ.");
        const staged = await chrome.storage.local.get(itemsStorageKey);
        const items = staged?.[itemsStorageKey]?.items;
        if (!Array.isArray(items)) throw new Error("Không đọc được hàng đợi từ storage.");
        const queueId = String(msg.queueId || "");
        if (!queueId) throw new Error("Thiếu mã queue.");
        const waitForTabId = Number(msg.waitForTabId) || null;
        const result = await withSplitQueueLock(async () => {
          const current = await getSplitAttachQueue();
          if (current?.status === "running") throw new Error("Đang có một queue khác hoạt động.");
          if (waitForTabId) {
            await chrome.tabs.get(waitForTabId);
            const pending = await getPendingMap();
            if (!pending[waitForTabId]) throw new Error("Tab hiện tại chưa có bundle phục hồi.");
          }
          const initialResults = Array.isArray(msg.initialResults) ? msg.initialResults.filter(Boolean) : [];
          const state = {
            queueId,
            status: "running",
            total: Number(msg.total) || (items.length + initialResults.length + (waitForTabId ? 1 : 0)),
            remaining: items.filter(Boolean),
            activeTabId: waitForTabId,
            activeItem: waitForTabId ? { ordinal: 1 } : null,
            results: initialResults,
            startedAt: Date.now(),
            updatedAt: Date.now(),
          };
          if (!await setSplitAttachQueue(state)) throw new Error("Không lưu được queue.");
          return waitForTabId ? { ok: true, waiting: true, tabId: waitForTabId }
            : await openNextSplitQueueItemUnlocked();
        });
        sendResponse({ ...result, queueId });
      } catch (e) { sendResponse({ error: e?.message || String(e) }); }
      finally { try { await chrome.storage.local.remove(itemsStorageKey); } catch (_) { /* bỏ qua */ } }
    })();
    return true;
  }
  if (msg?.action === "getSplitAttachQueueStatus") {
    (async () => {
      const state = await getSplitAttachQueue();
      if (!state || (msg.queueId && state.queueId !== msg.queueId)) return sendResponse({ status: null });
      sendResponse({ ok: true, ...splitQueueSummary(state) });
    })();
    return true;
  }
  if (msg?.action === "getPendingAttach") {
    (async () => {
      const pending = await getPendingMap();
      sendResponse({ pending: pending[sender?.tab?.id] || null });
    })();
    return true;
  }
  if (msg?.action === "clearPendingAttach" || msg?.action === "failPendingAttach") {
    (async () => {
      const tabId = msg.tabId ?? sender?.tab?.id;
      const result = await withSplitQueueLock(async () => {
        const pending = await getPendingMap();
        if (tabId != null && pending[tabId]) { delete pending[tabId]; await setPendingMap(pending); }
        return await finishSplitQueueTabUnlocked(tabId, {
          ok: msg.action === "clearPendingAttach",
          code: msg.code || (msg.action === "clearPendingAttach" ? null : "attach-failed"),
          error: msg.error || null,
        });
      });
      sendResponse({ ok: true, ...result });
    })();
    return true;
  }
});

// Đóng tab đang xử lý được tính là một hồ sơ lỗi, nhưng queue vẫn tiếp tục tab kế tiếp.
chrome.tabs.onRemoved.addListener(async (tabId) => {
  try {
    await withSplitQueueLock(async () => {
      const pending = await getPendingMap();
      if (pending[tabId]) { delete pending[tabId]; await setPendingMap(pending); }
      await finishSplitQueueTabUnlocked(tabId, {
        ok: false, code: "tab-closed", error: "Tab hồ sơ đã bị đóng.",
      });
    });
  } catch (_) { /* bỏ qua */ }
});

// ───────────── Voice ASR qua offscreen document ─────────────
// Mic bị chặn trong iframe popup → đẩy việc thu mic + WS sang offscreen (top-level extension).
// popup → SW {type:"asr-start"|"asr-stop"} → SW đảm bảo offscreen tồn tại → chuyển lệnh xuống.
// QUAN TRỌNG: tạo MỚI offscreen mỗi lượt. Tái dùng document làm AudioContext lần 2 trở đi
// khởi tạo "suspended"/không thu được (mic sáng đèn nhưng im) → chỉ lần đầu chạy. Vì vậy đóng
// offscreen sau mỗi lượt (final/stop/error) để lượt sau luôn là document mới = giống lần đầu.
const OFFSCREEN_OPTS = {
  url: "offscreen.html",
  reasons: ["USER_MEDIA", "AUDIO_PLAYBACK"],
  justification: "Thu âm micro (ASR) và phát giọng đọc (TTS) cho trợ lý giọng nói.",
};

async function ensureFreshOffscreen() {
  await closeOffscreen(); // đảm bảo không còn document cũ → luôn tạo mới
  try {
    await chrome.offscreen.createDocument(OFFSCREEN_OPTS);
  } catch (e) {
    if (!/single offscreen/i.test(e?.message || "")) throw e;
    await closeOffscreen(); // race: còn sót document → đóng rồi tạo lại
    await chrome.offscreen.createDocument(OFFSCREEN_OPTS);
  }
}

async function closeOffscreen() {
  try {
    if (await chrome.offscreen.hasDocument()) await chrome.offscreen.closeDocument();
  } catch (_) {
    /* không có document / version cũ → bỏ qua */
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "asr-start") {
    (async () => {
      try {
        await ensureFreshOffscreen();
        chrome.runtime.sendMessage(
          { target: "offscreen", cmd: "start", lang: msg.lang || "vi", baseUrl: msg.baseUrl },
          () => void chrome.runtime.lastError,
        );
        sendResponse({ ok: true });
      } catch (e) {
        sendResponse({ ok: false, error: e?.message || String(e) });
      }
    })();
    return true; // async sendResponse
  }
  if (msg?.type === "asr-stop") {
    closeOffscreen(); // đóng document = dừng mic + WS ngay
    sendResponse?.({ ok: true });
    return false;
  }
  // Lượt kết thúc (final/stopped/error) → đóng offscreen để lượt sau tạo mới.
  // CHỈ đóng sau khi popup đã nhận event (event được broadcast tới cả popup lẫn SW cùng lúc).
  if (msg?.type === "asr-event") {
    if (msg.event === "final" || msg.event === "error" || (msg.event === "state" && msg.state === "stopped")) {
      closeOffscreen();
    }
    return false;
  }
  // TTS phát tại offscreen (sống xuyên chuyển trang, miễn autoplay policy). Tái dùng
  // document nếu có, KHÔNG đóng sau khi đọc — asr-start vẫn tạo mới (cắt loa = barge-in).
  if (msg?.type === "tts-speak") {
    (async () => {
      try {
        if (!(await chrome.offscreen.hasDocument())) {
          await chrome.offscreen.createDocument(OFFSCREEN_OPTS).catch((e) => {
            if (!/single offscreen/i.test(e?.message || "")) throw e;
          });
        }
        chrome.runtime.sendMessage(
          { target: "offscreen", cmd: "tts-speak", url: msg.url, text: msg.text, id: msg.id },
          () => void chrome.runtime.lastError,
        );
        sendResponse({ ok: true });
      } catch (e) {
        sendResponse({ ok: false, error: e?.message || String(e) });
      }
    })();
    return true; // async sendResponse
  }
  if (msg?.type === "tts-stop") {
    chrome.runtime.sendMessage(
      { target: "offscreen", cmd: "tts-stop" },
      () => void chrome.runtime.lastError,
    );
    sendResponse?.({ ok: true });
    return false;
  }
});
