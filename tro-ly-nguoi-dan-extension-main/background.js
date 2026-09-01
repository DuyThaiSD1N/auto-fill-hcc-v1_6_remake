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

// Phiên đăng nhập của công dân nằm ở nhiều miền dù tab hoàn tất có thể đang ở cổng Bộ Tư pháp.
// Chỉ xóa đúng các miền tham gia luồng DVC/VNeID; tuyệt đối không quét rộng *.gov.vn hoặc *.moj.gov.vn.
const CITIZEN_COOKIE_HOSTS = Object.freeze([
  "dichvucong.gov.vn",
  "sso.dancuquocgia.gov.vn",
  "dichvucongnganhtuphap.moj.gov.vn",
  "tokhaidientu.moj.gov.vn",
]);

// Token đăng nhập của các cổng SPA không nhất thiết chỉ nằm trong cookie. Xóa thêm
// dữ liệu web đúng các origin tham gia luồng; không đụng chrome.storage của Trợ lý.
const CITIZEN_STORAGE_ORIGINS = Object.freeze([
  "https://dichvucong.gov.vn",
  "https://lienthong.dichvucong.gov.vn",
  "https://sso.dancuquocgia.gov.vn",
  "https://dichvucongnganhtuphap.moj.gov.vn",
  "https://tokhaidientu.moj.gov.vn",
]);

const CITIZEN_TAB_URL_PATTERNS = Object.freeze([
  "https://dichvucong.gov.vn/*",
  "https://*.dichvucong.gov.vn/*",
  "https://sso.dancuquocgia.gov.vn/*",
  "https://dichvucongnganhtuphap.moj.gov.vn/*",
  "https://tokhaidientu.moj.gov.vn/*",
]);

const JOURNEY_KEY = "tlnd_journey";
const COMPLETION_LOGOUT_KEY_PREFIX = "tlnd_completion_logout:";

// Click Đăng xuất thường điều hướng ngay, có thể hủy iframe sidebar trước khi nó kịp
// ghi trạng thái. Service worker xóa deadline theo tab để bộ đếm của công dân cũ
// tuyệt đối không sống lại khi trang kế tiếp dựng sidebar mới.
function clearCompletionLogoutForTab(tabId) {
  return new Promise((resolve) => {
    const key = String(tabId ?? "");
    if (!key) return resolve({ ok: false, cleared: false });
    const completionKey = `${COMPLETION_LOGOUT_KEY_PREFIX}${key}`;
    chrome.storage.local.get([JOURNEY_KEY, completionKey], (res) => {
      const journeys = res?.[JOURNEY_KEY] || {};
      const current = journeys[key];
      const hadSeparateState = !!res?.[completionKey];
      const hadLegacyState = !!current?.completion_logout;
      const removeSeparateState = () => {
        chrome.storage.local.remove([completionKey], () => {
          resolve({
            ok: !chrome.runtime.lastError,
            cleared: hadSeparateState || hadLegacyState,
          });
        });
      };
      if (!hadLegacyState) {
        removeSeparateState();
        return;
      }
      const next = { ...current };
      delete next.completion_logout;
      journeys[key] = next;
      chrome.storage.local.set({ [JOURNEY_KEY]: journeys }, removeSeparateState);
    });
  });
}

function citizenCookieRemovalHost(cookie) {
  const domain = String(cookie?.domain || "").replace(/^\./, "").toLowerCase();
  if (!domain) return "";
  for (const host of CITIZEN_COOKIE_HOSTS) {
    if (domain === host || domain.endsWith(`.${host}`)) return domain;
    // Cookie có thể được đặt ở miền cha (ví dụ dancuquocgia.gov.vn) nhưng vẫn áp dụng
    // cho đúng cổng SSO. Xóa qua host con đã được cấp quyền, không mở quyền toàn miền cha.
    if (host.endsWith(`.${domain}`)) return host;
  }
  return "";
}

function cookieRemovalUrl(cookie, host) {
  const path = String(cookie?.path || "/");
  if (!host) return "";
  // Cả cookie Secure và không-Secure đều có thể được xóa qua URL HTTPS; dùng một scheme
  // giúp quyền host không phải mở rộng thêm sang HTTP cho các cổng chỉ phục vụ HTTPS.
  return `https://${host}${path.startsWith("/") ? path : `/${path}`}`;
}

async function cookieStoreIdForTab(tabId) {
  if (!Number.isInteger(Number(tabId)) || Number(tabId) <= 0) return null;
  const stores = await chrome.cookies.getAllCookieStores();
  return stores.find((store) => Array.isArray(store?.tabIds)
    && store.tabIds.some((id) => Number(id) === Number(tabId)))?.id || null;
}

async function clearCitizenDvcCookies(tabId) {
  const storeId = await cookieStoreIdForTab(tabId).catch(() => null);
  const queryDetails = [{}];
  if (storeId) queryDetails[0].storeId = storeId;

  // Phiên đăng nhập chính là cookie không partition. Nếu Chrome hỗ trợ partition key,
  // quét thêm partition hiện tại để không bỏ sót cookie của iframe SSO.
  if (typeof chrome.cookies.getPartitionKey === "function"
      && Number.isInteger(Number(tabId)) && Number(tabId) > 0) {
    try {
      const partitionKey = await chrome.cookies.getPartitionKey({ tabId: Number(tabId) });
      if (partitionKey && Object.keys(partitionKey).length) {
        queryDetails.push({ ...(storeId ? { storeId } : {}), partitionKey });
      }
    } catch (_) {
      /* Chrome cũ hoặc frame không còn tồn tại: lượt cookie thường vẫn tiếp tục. */
    }
  }
  const queries = await Promise.allSettled(queryDetails.map((details) => chrome.cookies.getAll(details)));

  const unique = new Map();
  let failedQueries = 0;
  for (const query of queries) {
    if (query.status !== "fulfilled") {
      failedQueries += 1;
      continue;
    }
    for (const cookie of query.value || []) {
      const removalHost = citizenCookieRemovalHost(cookie);
      if (!removalHost) continue;
      const key = [
        cookie.storeId || storeId || "",
        cookie.domain || "",
        cookie.path || "/",
        cookie.name || "",
        JSON.stringify(cookie.partitionKey || null),
      ].join("|");
      unique.set(key, { cookie, removalHost });
    }
  }

  let removed = 0;
  let failed = 0;
  await Promise.all([...unique.values()].map(async ({ cookie, removalHost }) => {
    const url = cookieRemovalUrl(cookie, removalHost);
    if (!url || !cookie?.name) {
      failed += 1;
      return;
    }
    const details = { url, name: cookie.name };
    if (cookie.storeId || storeId) details.storeId = cookie.storeId || storeId;
    if (cookie.partitionKey) details.partitionKey = cookie.partitionKey;
    try {
      const result = await chrome.cookies.remove(details);
      if (result) removed += 1;
      else failed += 1;
    } catch (_) {
      failed += 1;
    }
  }));

  let storageCleared = false;
  let storageError = "";
  try {
    await chrome.browsingData.remove(
      { origins: [...CITIZEN_STORAGE_ORIGINS] },
      { localStorage: true, indexedDB: true },
    );
    storageCleared = true;
  } catch (error) {
    storageError = error?.message || String(error);
  }

  // sessionStorage không thuộc BrowsingData API. Yêu cầu content script xóa tại từng
  // tab đang mở, nhưng không reload trang vì công dân vừa nộp xong cần giữ nguyên màn hình.
  let clearedTabs = 0;
  let failedTabs = 0;
  try {
    const tabs = await chrome.tabs.query({ url: [...CITIZEN_TAB_URL_PATTERNS] });
    for (const tab of tabs || []) {
      if (!Number.isInteger(Number(tab?.id)) || Number(tab.id) <= 0) continue;
      try {
        await chrome.tabs.sendMessage(Number(tab.id), { action: "clearCitizenPortalSessionStorage" });
        clearedTabs += 1;
      } catch (_) {
        // Tab có thể chưa nạp content script; cookie và dữ liệu origin vẫn đã được dọn.
      }
    }
  } catch (_) {
    failedTabs += 1;
  }

  // Chỉ trả số lượng; không đưa tên hay giá trị cookie nhạy cảm về sidebar/log.
  return {
    ok: failedQueries === 0 && failed === 0 && storageCleared && failedTabs === 0,
    scopes: CITIZEN_COOKIE_HOSTS.length,
    found: unique.size,
    removed,
    failed,
    failedQueries,
    storageCleared,
    storageError,
    clearedTabs,
    failedTabs,
  };
}

// Cho khung Trợ lý (popup chạy trong iframe) lấy tabId của chính nó.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action === "getTabId") {
    sendResponse({ tabId: sender?.tab?.id ?? null });
    return true;
  }
  if (msg?.action === "clearCitizenDvcCookies") {
    clearCitizenDvcCookies(sender?.tab?.id)
      .then(sendResponse)
      .catch((error) => sendResponse({
        ok: false,
        scopes: CITIZEN_COOKIE_HOSTS.length,
        found: 0,
        removed: 0,
        failed: 0,
        failedQueries: 1,
        storageCleared: false,
        storageError: error?.message || String(error),
        clearedTabs: 0,
        failedTabs: 0,
        error: error?.message || String(error),
      }));
    return true;
  }
  if (msg?.action === "citizenManualLogoutDetected") {
    clearCompletionLogoutForTab(sender?.tab?.id).then(sendResponse);
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
          {
            target: "offscreen",
            cmd: "start",
            lang: msg.lang || "vi",
            baseUrl: msg.baseUrl,
            accessToken: msg.accessToken || "",
          },
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
    // Offscreen dùng CHUNG cho ASR và TTS. Đóng cả document ở đây sẽ cắt câu TTS
    // vừa phát (đặc biệt: thông báo hỏi đăng xuất gọi stopVoice ngay sau renderReply).
    // Chỉ dừng session micro; giữ document để hàng đợi loa tiếp tục phát bình thường.
    (async () => {
      try {
        if (await chrome.offscreen.hasDocument()) {
          chrome.runtime.sendMessage(
            { target: "offscreen", cmd: "stop" },
            () => void chrome.runtime.lastError,
          );
        }
        sendResponse?.({ ok: true });
      } catch (e) {
        sendResponse?.({ ok: false, error: e?.message || String(e) });
      }
    })();
    return true;
  }
  // Lượt kết thúc tự nhiên/lỗi → đóng offscreen để lượt sau tạo mới. Riêng "stopped"
  // là lệnh dừng micro chủ động; giữ offscreen vì cùng document có thể đang phát TTS.
  // CHỈ đóng sau khi popup đã nhận event (event được broadcast tới cả popup lẫn SW cùng lúc).
  if (msg?.type === "asr-event") {
    if (msg.event === "final" || msg.event === "error") {
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
          {
            target: "offscreen",
            cmd: "tts-speak",
            url: msg.url,
            protocols: msg.protocols || [],
            text: msg.text,
            id: msg.id,
          },
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
