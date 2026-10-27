// Ảnh chụp form (content/form-snapshot) → BE POST /api/v1/form-snapshots, gửi TỪ BACKGROUND.
// Hàng đợi bền trong storage giống mốc nộp (lib/submitClickReporter.js): chỉ xoá khi BE nhận hoặc từ
// chối hẳn; làm mới token dùng chung refreshAuth của file đó (nạp trước file này trong background.js).
(() => {
  "use strict";

  const OUTBOX_KEY = "tlnd_form_snapshot_outbox";
  const AUTH_KEY = "tlnd_auth";        // khớp api/auth.js
  const ALARM = "tlnd-form-snapshot-outbox";
  const MAX_AGE_MS = 24 * 60 * 60 * 1000;
  const MAX_ITEMS = 200;
  const RETRY_STATUS = new Set([401, 408, 429]);

  const storageGet = (keys) => new Promise((resolve) => {
    chrome.storage.local.get(keys, (res) => { void chrome.runtime.lastError; resolve(res || {}); });
  });
  const storageSet = (obj) => new Promise((resolve) => {
    chrome.storage.local.set(obj, () => { void chrome.runtime.lastError; resolve(); });
  });

  let chain = Promise.resolve();
  function mutateOutbox(fn) {
    const run = async () => {
      const cur = (await storageGet([OUTBOX_KEY]))[OUTBOX_KEY];
      const next = fn(Array.isArray(cur) ? cur : []);
      await storageSet({ [OUTBOX_KEY]: next });
      return next;
    };
    chain = chain.then(run, run);
    return chain;
  }

  /** "ok" = BE đã nhận · "drop" = từ chối hẳn (lượt không thuộc tài khoản, BE cũ) · "retry". */
  async function send(item) {
    let auth = (await storageGet([AUTH_KEY]))[AUTH_KEY];
    if (!auth?.access) return "retry";
    const body = JSON.stringify(item);
    const post = () => globalThis.tlndOverBases((base) => globalThis.tlndFetch(`${base}/api/v1/form-snapshots`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${auth.access}` },
      body,
    }));
    let res;
    try { res = await post(); } catch (_) { return "retry"; }
    if (res.status === 401 && auth.refresh) {
      const next = await globalThis.__TLND_SUBMIT__?.refreshAuth?.(auth);
      if (!next) return "retry";
      auth = next;
      try { res = await post(); } catch (_) { return "retry"; }
    }
    if (res.ok) return "ok";
    if (RETRY_STATUS.has(res.status) || res.status >= 500) return "retry";
    return "drop";
  }

  let flushing = null;
  function flush() {
    if (flushing) return flushing;
    flushing = (async () => {
      const queue = (await storageGet([OUTBOX_KEY]))[OUTBOX_KEY];
      const fresh = (Array.isArray(queue) ? queue : [])
        .filter((it) => it?.snapshotId && Date.now() - Number(it.at || 0) < MAX_AGE_MS);
      for (const item of fresh) {
        const r = await send(item);
        if (r === "retry") {
          try { chrome.alarms.create(ALARM, { delayInMinutes: 1 }); } catch (_) {}
          return;
        }
        await mutateOutbox((cur) => cur.filter((it) => it?.snapshotId !== item.snapshotId));
      }
      await mutateOutbox((cur) => cur.filter((it) => Date.now() - Number(it?.at || 0) < MAX_AGE_MS));
    })().catch((e) => console.warn("[TLND] Không gửi được ảnh chụp form:", e?.message || e))
      .finally(() => { flushing = null; });
    return flushing;
  }

  async function enqueue(snapshot) {
    await mutateOutbox((cur) => [...cur.filter((it) => it?.snapshotId !== snapshot.snapshotId), snapshot]
      .slice(-MAX_ITEMS));
    void flush();
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg?.action === "formSnapshot" && msg.snapshot?.snapshotId) {
      enqueue(msg.snapshot).then(() => sendResponse({ ok: true }), () => sendResponse({ ok: false }));
      return true;
    }
    // Nút rời bước ở frame khác frame chứa form → phát lại cho mọi frame của tab.
    if (msg?.action === "formSnapshotStep" && sender?.tab?.id) {
      chrome.tabs.sendMessage(sender.tab.id, { action: "formSnapshotCapture", trigger: msg.trigger || "" },
        () => void chrome.runtime.lastError);
    }
    return undefined;
  });
  chrome.alarms?.onAlarm?.addListener((a) => { if (a?.name === ALARM) void flush(); });
  chrome.runtime?.onStartup?.addListener(() => { void flush(); });
  chrome.storage?.onChanged?.addListener((changes, area) => {
    if (area === "local" && changes[AUTH_KEY]?.newValue?.access) void flush();
  });
})();
