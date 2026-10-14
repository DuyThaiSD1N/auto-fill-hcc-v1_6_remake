// Gửi mốc "bấm Gửi hồ sơ" lên BE TỪ BACKGROUND (service worker), không qua sidebar.
//
// Sidebar là iframe nằm trong trang cổng. Cổng chuyển hẳn trang ngay khi bấm nộp (Lai Châu,
// HkdOnline…) thì iframe chết trước khi kịp gửi `__event:submit_clicked` — mốc nộp mất lặng lẽ,
// và vì phiếu đánh giá cũng bật từ chính mốc đó nên không để lại dấu vết nào. Background không
// chết theo trang. Sidebar còn sống vẫn gửi event của nó (để hiện phiếu đánh giá); hai đường
// mang CHUNG click_id nên BE chỉ ghi một sự kiện.
//
// Conversation lấy từ tlnd_journey[tab] — map sidebar ghi sau MỖI lượt hỏi-đáp và dùng để khôi
// phục phiên sau chuyển trang, nên luôn trùng phiên sidebar đang mở trên tab đó. Tab tách (chứng
// thực nhiều hồ sơ) tra theo tab gốc.
//
// Mỗi mốc vào hàng đợi trong storage, chỉ xoá khi BE nhận (res.ok): token hết hạn, mất mạng,
// service worker bị tắt giữa chừng đều không làm mất mốc.
(() => {
  "use strict";

  const OUTBOX_KEY = "tlnd_submit_outbox";
  const AUTH_KEY = "tlnd_auth";        // khớp api/auth.js
  const JOURNEY_KEY = "tlnd_journey";  // khớp sidebar.js
  const ALARM = "tlnd-submit-outbox";
  const MAX_AGE_MS = 3 * 24 * 60 * 60 * 1000;
  const MAX_ITEMS = 100;
  const RETRY_STATUS = new Set([401, 408, 429]);

  const storageGet = (keys) => new Promise((resolve) => {
    chrome.storage.local.get(keys, (res) => { void chrome.runtime.lastError; resolve(res || {}); });
  });
  const storageSet = (obj) => new Promise((resolve) => {
    chrome.storage.local.set(obj, () => { void chrome.runtime.lastError; resolve(); });
  });

  let chain = Promise.resolve();
  // Mọi đọc-sửa-ghi hàng đợi đi qua một chuỗi: enqueue lúc đang flush không được mất mục.
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

  // BE XOAY VÒNG refresh token (token cũ bị thu hồi ngay). Sidebar có thể làm mới cùng lúc với
  // ta: bên thua nhận 401 dù cặp mới đã có trong storage → đọc lại trước khi coi là hỏng.
  // Không bao giờ xoá token ở đây: đưa cán bộ về màn đăng nhập là việc của sidebar.
  async function refreshAuth(used) {
    try {
      const res = await globalThis.tlndOverBases((base) => globalThis.tlndFetch(`${base}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: used.refresh }),
      }));
      if (res.ok) {
        const data = await res.json();
        if (data?.accessToken && data?.refreshToken) {
          const next = { access: data.accessToken, refresh: data.refreshToken, user: data.user || used.user,
            obtained_at: Date.now(), ttl_s: 0 };  // ttl_s=0 → sidebar so exp với giờ máy như cũ
          // Cán bộ vừa đăng xuất / đăng nhập tài khoản khác trong lúc ta làm mới → không được
          // hồi sinh phiên cũ vào storage; cặp mới chỉ dùng cho request này.
          const cur = (await storageGet([AUTH_KEY]))[AUTH_KEY];
          if (cur?.refresh === used.refresh) await storageSet({ [AUTH_KEY]: next });
          return next;
        }
      }
    } catch (_) { /* mạng — thử lại sau */ }
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const cur = (await storageGet([AUTH_KEY]))[AUTH_KEY];
    return cur?.access && cur.access !== used.access ? cur : null;
  }

  /** "ok" = BE đã nhận · "drop" = từ chối hẳn (phiên hết hạn/không phải của ta, BE cũ) · "retry". */
  async function send(item) {
    let auth = (await storageGet([AUTH_KEY]))[AUTH_KEY];
    if (!auth?.access) return "retry"; // chưa đăng nhập — chờ
    const body = JSON.stringify({
      click_id: item.clickId, clicked_at: item.clickedAt, host: item.host || "", ref: item.ref || "",
    });
    const path = `/api/v1/assistant/conversations/${encodeURIComponent(item.conversationId)}/submit-click`;
    const post = () => globalThis.tlndOverBases((base) => globalThis.tlndFetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${auth.access}` },
      body,
    }));
    let res;
    try { res = await post(); } catch (_) { return "retry"; }
    if (res.status === 401 && auth.refresh) {
      const next = await refreshAuth(auth);
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
      const all = Array.isArray(queue) ? queue : [];
      const fresh = all.filter((it) => it?.clickId && it?.conversationId
        && Date.now() - Number(it.clickedAt || 0) < MAX_AGE_MS);
      if (fresh.length !== all.length) {
        const keep = new Set(fresh.map((it) => it.clickId));
        await mutateOutbox((cur) => cur.filter((it) => keep.has(it?.clickId)));
      }
      for (const item of fresh) {
        const r = await send(item);
        if (r === "retry") {
          try { chrome.alarms.create(ALARM, { delayInMinutes: 1 }); } catch (_) {}
          return;
        }
        await mutateOutbox((cur) => cur.filter((it) => it?.clickId !== item.clickId));
      }
    })().catch((e) => console.warn("[TLND] Không gửi được hàng đợi mốc nộp:", e?.message || e))
      .finally(() => { flushing = null; });
    return flushing;
  }

  async function reportClick({ tabId, originTabId, host, ref, clickId, clickedAt }) {
    // Không có mã cú bấm thì sidebar cũng không có → BE không lọc trùng được giữa hai đường.
    if (!tabId || !clickId) return;
    const journeys = (await storageGet([JOURNEY_KEY]))[JOURNEY_KEY] || {};
    const conversationId = journeys[originTabId || tabId]?.conversation_id;
    if (!conversationId) return; // tab chưa có hồ sơ nào để chấm
    await mutateOutbox((cur) => {
      const list = cur.filter((it) => it?.clickId !== clickId);
      list.push({
        conversationId, clickId: String(clickId), clickedAt: Number(clickedAt) || Date.now(),
        host: String(host || ""), ref: String(ref || ""),
      });
      return list.slice(-MAX_ITEMS);
    });
    await flush();
  }

  // Hàng đợi còn mốc thì mọi dịp sống dậy đều thử gửi: hẹn giờ, trình duyệt mở lại, và lúc có
  // token mới (refresh token hỏng chỉ gỡ được khi cán bộ đăng nhập lại).
  chrome.alarms?.onAlarm?.addListener((a) => { if (a?.name === ALARM) void flush(); });
  chrome.runtime?.onStartup?.addListener(() => { void flush(); });
  chrome.storage?.onChanged?.addListener((changes, area) => {
    if (area === "local" && changes[AUTH_KEY]?.newValue?.access) void flush();
  });

  globalThis.__TLND_SUBMIT__ = { reportClick, flush };
})();
