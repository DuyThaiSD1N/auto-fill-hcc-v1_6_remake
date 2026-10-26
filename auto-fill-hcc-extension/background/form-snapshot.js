// Ảnh chụp form (content/form-snapshot) → BE POST /api/v1/form-snapshots.
// Hàng đợi bền trong storage giống mốc nộp: chỉ xoá khi BE nhận hoặc từ chối hẳn. Dùng chung base,
// token và cách làm mới token với mốc nộp: SUBMIT_WATCH_KEY, fetchWithTimeout, refreshSubmitTokens
// khai ở background.js (cùng phạm vi global của service worker / event page).
(() => {
  "use strict";
  const OUTBOX_KEY = "autofill_form_snapshot_outbox";
  const ALARM = "autofill-form-snapshot-outbox";
  const MAX_AGE_MS = 24 * 60 * 60 * 1000;
  const MAX_ITEMS = 200;
  const RETRY_STATUS = new Set([401, 408, 429]);
  const INFRA_STATUS = new Set([502, 503, 504]);

  let chain = Promise.resolve();
  function mutateOutbox(fn) {
    const run = async () => {
      const cur = (await chrome.storage.local.get([OUTBOX_KEY]))?.[OUTBOX_KEY];
      const next = fn(Array.isArray(cur) ? cur : []);
      await chrome.storage.local.set({ [OUTBOX_KEY]: next });
      return next;
    };
    chain = chain.then(run, run);
    return chain;
  }

  /** "ok" = BE đã nhận · "drop" = BE từ chối hẳn (lượt không thuộc tài khoản, BE cũ) · "retry". */
  async function send(item) {
    const store = await chrome.storage.local.get([SUBMIT_WATCH_KEY, "auth_tokens"]);
    const conf = store?.[SUBMIT_WATCH_KEY] || {};
    const bases = [...new Set([conf.base, ...(Array.isArray(conf.bases) ? conf.bases : [])]
      .map((b) => String(b || "").trim().replace(/\/+$/, "")).filter(Boolean))];
    let tokens = store?.auth_tokens;
    if (!bases.length || !tokens?.accessToken) return "retry";
    const body = JSON.stringify(item);
    const post = (base) => fetchWithTimeout(base + "/api/v1/form-snapshots", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + tokens.accessToken },
      body,
    });
    for (const base of bases) {
      let res;
      try { res = await post(base); } catch (_) { continue; }
      if (INFRA_STATUS.has(res.status)) continue;
      if (res.status === 401 && tokens.refreshToken) {
        const next = await refreshSubmitTokens(base, tokens);
        if (!next) return "retry";
        tokens = next;
        try { res = await post(base); } catch (_) { continue; }
      }
      if (res.ok) return "ok";
      if (RETRY_STATUS.has(res.status) || res.status >= 500) return "retry";
      return "drop";
    }
    return "retry";
  }

  let flushing = null;
  function flush() {
    if (flushing) return flushing;
    flushing = (async () => {
      const queue = (await chrome.storage.local.get([OUTBOX_KEY]))?.[OUTBOX_KEY];
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
    })().catch((e) => console.warn("[BG] Không gửi được ảnh chụp form:", e?.message || e))
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
  chrome.alarms.onAlarm.addListener((a) => { if (a?.name === ALARM) void flush(); });
  chrome.runtime.onStartup.addListener(() => { void flush(); });
})();
