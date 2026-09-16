// Service worker — bấm icon extension → mở/đóng khung Trợ lý trên trang.
//
// Hai chế độ khung (xem lib/panelMode.js):
//   push      — iframe đẩy trang sang trái, do content.js dựng. MẶC ĐỊNH.
//   sidepanel — khung bên của chính trình duyệt (chrome.sidePanel).
// Ở chế độ sidepanel, cú bấm icon do CHROME xử lý (openPanelOnActionClick=true)
// nên listener dưới đây KHÔNG chạy. Cố tự mở bằng sidePanel.open() trong listener
// là hỏng: hàm đó đòi user gesture, mà đọc cài đặt là async nên gesture đã mất.

importScripts("lib/panelMode.js");
const PM = globalThis.__TLND_PANEL_MODE__;

// Bấm icon. Content script còn sống thì chỉ bật/tắt panel như trước.
//
// Tab mở từ TRƯỚC lần nạp lại extension (tự cập nhật, bấm "⬆ Cập nhật", nạp tay ở chrome://extensions)
// giữ content script MỒ CÔI: mọi message tới nó hỏng ("Receiving end does not exist"), nên trước đây bấm
// icon im lặng và cán bộ phải tự tải lại trang. Giờ tiêm lại ĐỦ bộ file theo đúng thứ tự manifest rồi gửi
// lại. Đo 2026-09-14 trên Chrome 151: bản tiêm lại chạy trong isolated world MỚI (cờ window.__TLND_*__ của
// bản mồ côi không còn), nên các guard chống nạp trùng không chặn.
//
// Chỉ tiêm trên trang khớp content_scripts.matches — trùng khít web_accessible_resources, nên trang khác
// không bao giờ bị dựng panel chết. Panel/launcher mồ côi còn nằm trên trang (nạp lại mà không kịp
// hccGoPanelTruocKhiNapLai) thì gỡ trước: iframe của nó thuộc bản extension cũ đã chết, còn listener thuộc
// world cũ — để lại thì content.js mới sẽ dùng lại đúng cái xác đó (createPanel/showLauncher tìm theo id).
function khopMauUrl(url, mau) {
  const m = /^(\*|https?):\/\/(\*|(?:\*\.)?[^/*]+)(\/.*)$/.exec(String(mau || ""));
  if (!m || !url) return false;
  let u;
  try { u = new URL(url); } catch (e) { return false; }
  const scheme = u.protocol.slice(0, -1);
  if (m[1] === "*" ? scheme !== "http" && scheme !== "https" : scheme !== m[1]) return false;
  const host = m[2];
  if (host.startsWith("*.")) {
    const goc = host.slice(2);
    if (u.hostname !== goc && !u.hostname.endsWith("." + goc)) return false;
  } else if (host !== "*" && u.hostname !== host) {
    return false;
  }
  const duong = m[3].split("*").map((x) => x.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*");
  return new RegExp("^" + duong + "$").test(u.pathname + u.search);
}

async function moPanelTheoIcon(tab) {
  if (!tab?.id) return "khong-tab";
  try {
    await chrome.tabs.sendMessage(tab.id, { action: "togglePanel" });
    return "da-gui";
  } catch (e) { /* không có content script sống — xét tiêm lại */ }
  const cs = chrome.runtime.getManifest().content_scripts?.[0];
  if (!cs || !(cs.matches || []).some((mau) => khopMauUrl(tab.url, mau))) return "khong-ho-tro";
  // id khớp PANEL_ID / BUBBLE_ID trong content.js.
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      document.getElementById("tro-ly-nguoi-dan-panel")?.remove();
      document.getElementById("tro-ly-nguoi-dan-bubble")?.remove();
    },
  });
  const target = { tabId: tab.id, allFrames: !!cs.all_frames };
  if (cs.css?.length) await chrome.scripting.insertCSS({ target, files: cs.css });
  await chrome.scripting.executeScript({ target, files: cs.js });
  await chrome.tabs.sendMessage(tab.id, { action: "togglePanel" });
  return "tiem-lai";
}

chrome.action.onClicked.addListener((tab) => {
  moPanelTheoIcon(tab)
    .then((kq) => { if (kq === "khong-ho-tro") console.warn("[BG] Trang không hỗ trợ Trợ lý:", tab?.url); })
    .catch((e) => console.warn("[BG] Không mở được panel:", e?.message || e));
});

// ── Áp dụng chế độ khung ────────────────────────────────────────────────────
// Service worker bị Chrome giết/dựng lại liên tục, nên phải áp lại ở MỌI lần
// khởi động chứ không chỉ lúc người dùng đổi cài đặt — không thì sau một lần SW
// ngủ dậy, bấm icon lại quay về đẩy trang.

async function ganTuyChonKhungBen(tabId) {
  if (!tabId) return;
  try {
    await chrome.sidePanel.setOptions({
      tabId, path: PM.duongSidebar(tabId), enabled: true,
    });
  } catch (e) {
    console.warn("[BG] Không đặt được sidePanel cho tab", tabId, e?.message || e);
  }
}

// phatChoMoiTab=true CHỈ khi cài đặt thật sự đổi. Không được phát lúc SW khởi động
// lại (chuyện xảy ra liên tục): tab đang mở sẽ bị dựng/dọn khung mỗi lần SW ngủ dậy.
async function apDungCheDo(phatChoMoiTab = false) {
  const mode = await PM.cheDoHieuLuc();
  if (phatChoMoiTab) void baoMoiTab(mode);
  if (!PM.hoTroKhungBen()) return PM.DAY_TRANG;   // Chrome/Cốc Cốc cũ → không đụng gì
  const khungBen = mode === PM.KHUNG_BEN;
  try {
    await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: khungBen });
  } catch (e) {
    console.warn("[BG] Không đổi được hành vi sidePanel:", e?.message || e);
    return PM.DAY_TRANG;
  }
  // Gán đường có sẵn tabId cho các tab đang mở. Chỉ bật khi thật sự ở chế độ khung
  // bên: bật khi đang chạy đẩy trang là mọc thêm một cửa thứ hai trong menu khung
  // bên của Chrome, mở ra hai phiên hội thoại song song trên cùng một tab.
  try {
    const tabs = await chrome.tabs.query({});
    await Promise.all(tabs.map((t) => (
      khungBen
        ? ganTuyChonKhungBen(t.id)
        : chrome.sidePanel.setOptions({ tabId: t.id, enabled: false }).catch(() => {})
    )));
  } catch (e) {
    console.warn("[BG] Không quét được tab để áp chế độ khung:", e?.message || e);
  }
  return mode;
}

void apDungCheDo();
chrome.runtime.onStartup?.addListener(() => void apDungCheDo());
chrome.runtime.onInstalled.addListener(() => void apDungCheDo());

// Tab mới / điều hướng: đường sidebar phải mang đúng tabId của tab đó.
chrome.tabs.onCreated.addListener(async (tab) => {
  if (!PM.hoTroKhungBen() || !tab?.id) return;
  if (await PM.cheDoHieuLuc() === PM.KHUNG_BEN) await ganTuyChonKhungBen(tab.id);
});

// Đổi cài đặt ở BẤT KỲ đâu đều áp lại — kể cả khi màn Cài đặt nằm trong khung bên
// của một cửa sổ khác.
// Đổi chế độ phải tới MỌI tab đang mở, không chỉ tab đang mở màn Cài đặt: bỏ sót
// là tab kia giữ nguyên khung đẩy trang trong khi cả máy đã chuyển sang khung bên.
async function baoMoiTab(mode) {
  let tabs = [];
  try { tabs = await chrome.tabs.query({}); } catch (_) { return; }
  await Promise.all(tabs.map(async (t) => {
    if (!t.id) return;
    try { await chrome.tabs.sendMessage(t.id, { action: "panelModeChanged", mode }); }
    catch (_) { /* tab không có content script — bình thường */ }
  }));
}

chrome.storage.onChanged.addListener((thayDoi, vung) => {
  if (vung !== "local" || !(PM.KHOA in thayDoi)) return;
  void apDungCheDo(true);
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action !== "getPanelMode") return;
  // content.js hỏi đường này vì chrome.sidePanel không tồn tại trong content script.
  (async () => {
    sendResponse({
      mode: await PM.cheDoHieuLuc(),
      dat: await PM.docCheDo(),
      hoTro: PM.hoTroKhungBen(),
      moNgay: PM.hoTroMoNgay(),
      khungBenMo: khungBenMoTheoTab.has(sender?.tab?.id),
    });
  })();
  return true;
});

// ── Nút tròn trên trang mở khung bên ────────────────────────────────────────
// Đo trên Chrome 152 (2026-09-13): cú bấm THẬT trong content script chuyển được user gesture qua
// runtime.sendMessage, nên gọi sidePanel.open() ở đây được. Trình duyệt cũ không chuyển gesture
// thì open() bị từ chối → trả ok:false để content.js chỉ đường sang biểu tượng thanh công cụ.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.action !== "openSidePanel") return;
  const tabId = sender?.tab?.id;
  if (!tabId || !PM.hoTroMoNgay()) { sendResponse({ ok: false }); return; }
  // KHÔNG await gì trước open(): mọi await đều làm rơi mất gesture vừa chuyển sang.
  try {
    chrome.sidePanel.setOptions({ tabId, path: PM.duongSidebar(tabId), enabled: true }).catch(() => {});
    chrome.sidePanel.open({ tabId })
      .then(() => sendResponse({ ok: true }))
      .catch((e) => {
        console.warn("[BG] Nút tròn không mở được khung bên:", e?.message || e);
        sendResponse({ ok: false });
      });
  } catch (e) {
    console.warn("[BG] Nút tròn không mở được khung bên:", e?.message || e);
    sendResponse({ ok: false });
  }
  return true;
});

// ── Khung bên đang mở cho tab nào ───────────────────────────────────────────
// Sidebar ở khung bên giữ một port suốt đời trang; port đứt nghĩa là khung đã đóng. Dùng port chứ
// không dùng sidePanel.onOpened/onClosed: hai sự kiện đó chỉ có ở Chrome gần đây, port thì chạy ở
// mọi bản có sidePanel. SW bị Chrome dọn thì bảng này mất, nhưng sidebar tự nối lại port nên bảng
// dựng lại được — và SW chết thì không có onDisconnect nào báo "đóng" oan.
const khungBenMoTheoTab = new Map(); // tabId -> số port đang mở

async function baoKhungBen(tabId, mo) {
  try { await chrome.tabs.sendMessage(tabId, { action: "khungBenTrangThai", mo }); }
  catch (_) { /* tab không có content script — bình thường */ }
}

chrome.runtime.onConnect.addListener((port) => {
  const m = /^tlnd-khung-ben:(\d+)$/.exec(port.name || "");
  if (!m) return;
  const tabId = Number(m[1]);
  khungBenMoTheoTab.set(tabId, (khungBenMoTheoTab.get(tabId) || 0) + 1);
  void baoKhungBen(tabId, true);
  port.onDisconnect.addListener(() => {
    const con = (khungBenMoTheoTab.get(tabId) || 1) - 1;
    if (con > 0) { khungBenMoTheoTab.set(tabId, con); return; }
    khungBenMoTheoTab.delete(tabId);
    void baoKhungBen(tabId, false);
  });
});

// Phiên đăng nhập của công dân nằm ở nhiều miền dù tab hoàn tất có thể đang ở cổng Bộ Tư pháp.
// Chỉ xóa đúng các miền tham gia luồng DVC/VNeID; tuyệt đối không quét rộng *.gov.vn hoặc *.moj.gov.vn.
const CITIZEN_COOKIE_HOSTS = Object.freeze([
  "dichvucong.gov.vn",
  "sso.dancuquocgia.gov.vn",
  "dichvucongnganhtuphap.moj.gov.vn",
  "tokhaidientu.moj.gov.vn",
  "dichvucongnnmt.mae.gov.vn",
  "dvc.moet.gov.vn",
  "dvc.moc.gov.vn",
  "dichvucong.bacninh.gov.vn",
]);

// Token đăng nhập của các cổng SPA không nhất thiết chỉ nằm trong cookie. Xóa thêm
// dữ liệu web đúng các origin tham gia luồng; không đụng chrome.storage của Trợ lý.
const CITIZEN_STORAGE_ORIGINS = Object.freeze([
  "https://dichvucong.gov.vn",
  "https://lienthong.dichvucong.gov.vn",
  "https://sso.dancuquocgia.gov.vn",
  "https://dichvucongnganhtuphap.moj.gov.vn",
  "https://tokhaidientu.moj.gov.vn",
  "https://dichvucongnnmt.mae.gov.vn",
  "https://dvc.moet.gov.vn",
  "https://dvc.moc.gov.vn",
  "https://dichvucong.bacninh.gov.vn",
]);

const CITIZEN_TAB_URL_PATTERNS = Object.freeze([
  "https://dichvucong.gov.vn/*",
  "https://*.dichvucong.gov.vn/*",
  "https://sso.dancuquocgia.gov.vn/*",
  "https://dichvucongnganhtuphap.moj.gov.vn/*",
  "https://tokhaidientu.moj.gov.vn/*",
  "https://dichvucongnnmt.mae.gov.vn/*",
  "https://dvc.moet.gov.vn/*",
  "https://dvc.moc.gov.vn/*",
  "https://dichvucong.bacninh.gov.vn/*",
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
      // Chrome trả BAO NGOÀI { partitionKey: {...} }, KHÔNG trả thẳng CookiePartitionKey.
      // Nhét nguyên bao ngoài vào getAll làm Chrome ném "Unexpected property: 'partitionKey'"
      // — và ném ĐỒNG BỘ ngay trong .map() nên Promise.allSettled bên dưới không đỡ được:
      // cả lượt dọn đổ vỡ, không xóa nổi một cookie nào, công dân trước vẫn đăng nhập.
      const res = await chrome.cookies.getPartitionKey({ tabId: Number(tabId) });
      const partitionKey = res?.partitionKey || res;
      // Chỉ gửi khi có topLevelSite thật: object rỗng/hình dạng lạ cũng bị API từ chối.
      if (partitionKey && typeof partitionKey.topLevelSite === "string" && partitionKey.topLevelSite) {
        queryDetails.push({ ...(storeId ? { storeId } : {}), partitionKey });
      }
    } catch (_) {
      /* Chrome cũ hoặc frame không còn tồn tại: lượt cookie thường vẫn tiếp tục. */
    }
  }
  // async arrow: biến cú ném ĐỒNG BỘ của API thành promise bị từ chối để allSettled đỡ được.
  // Một lượt quét hỏng chỉ được làm hỏng chính nó, không được kéo sập việc dọn phiên công dân.
  const queries = await Promise.allSettled(
    queryDetails.map(async (details) => chrome.cookies.getAll(details)),
  );

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
  if (await coPanelDangLamViec()) return true;
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
// Sidebar tự ghi trạng thái (lib/trangThai.js) theo tab — background không hỏi thẳng được iframe hay
// khung bên. Có panel nào "đang làm việc" trong 10 giây gần nhất (đang tải tệp quét lên, đang gọi BE…)
// là bận. Nhịp quá 60 giây = panel đã chết → dọn.
const TIEN_TO_TRANG_THAI_PANEL = "tlnd_trang_thai_panel:";
async function coPanelDangLamViec() {
  const kho = chrome.storage.session || chrome.storage.local;
  let tatCa;
  try { tatCa = await kho.get(null); } catch (e) { return false; }
  // Trình duyệt cũ không trả Promise → không biết gì → coi như bận (cùng quy ước với các tab).
  if (tatCa === undefined || tatCa === null) return !hoTroPromise();
  const gio = Date.now();
  const hetHan = [];
  let ban = false;
  for (const [k, v] of Object.entries(tatCa)) {
    if (!k.startsWith(TIEN_TO_TRANG_THAI_PANEL)) continue;
    const tuoi = gio - Number(v?.luc || 0);
    if (tuoi > 60 * 1000) { hetHan.push(k); continue; }
    if (tuoi <= 10 * 1000 && v?.tt === "dang-lam-viec") ban = true;
  }
  if (hetHan.length) { try { await kho.remove(hetHan); } catch (_) { /* ignore */ } }
  return ban;
}

// Sidebar vừa nghe agent báo có bản extension mới trên đĩa → kiểm NGAY, khỏi chờ nhịp 1 phút.
// kiemBanMoi tự giữ mọi luật "chỉ nạp lại khi rảnh", nên gọi thêm lần nào cũng an toàn.
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.action === "hccKiemBanMoiNgay") void kiemBanMoi();
});

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
