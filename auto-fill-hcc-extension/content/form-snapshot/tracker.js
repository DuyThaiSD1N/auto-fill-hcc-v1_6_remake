// Ảnh chụp form sau khi điền, gắn với requestId của lượt điền:
//   fill — đọc lại ngay sau khi điền xong (mốc so sánh); mỗi lần chụp đọc cả ô BE không trả
//   edit — cán bộ thao tác trên trang rồi ngừng EDIT_IDLE_MS, chỉ gửi khi giá trị khác lần trước
//   step — bấm nút rời bước kê khai (luật BE cấp) hoặc lệnh capture từ sidebar/background
// Nút rời bước có thể ở frame khác frame chứa form (tờ khai tư pháp nằm trong iframe) → frame
// bấm báo background, background phát lại cho mọi frame của tab. Gửi qua background (hàng đợi bền);
// sessionStorage giữ ảnh chưa gửi cho trang POST tải lại ngay sau cú bấm (Lai Châu).
// Dùng chung nguyên văn cho hai extension.
(() => {
  "use strict";
  const NS = window.__HCC__ || window.__TLND__;
  if (!NS) return;
  const FS = NS.formSnapshot || (NS.formSnapshot = {});
  if (FS.started || typeof FS.readFields !== "function" || typeof FS.listExtra !== "function"
    || typeof FS.matchStep !== "function") return;
  FS.started = true;

  const FILL_SETTLE_MS = 1500;
  const EDIT_IDLE_MS = 3000;
  const STEP_DEDUPE_MS = 3000;
  const PENDING_KEY = "__form_snapshot_pending";
  const PENDING_MAX_AGE_MS = 24 * 60 * 60 * 1000;
  const MAX_FIELDS = 600;
  const EXT_VERSION = (() => {
    try { return String(chrome.runtime.getManifest().version || ""); } catch (_) { return ""; }
  })();

  let config = null;
  let session = null;
  let editTimer = 0;
  let lastStepAt = 0;

  const newId = () => {
    try { return crypto.randomUUID(); } catch (_) { }
    return "s-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  };

  function readPending() {
    try {
      const list = JSON.parse(sessionStorage.getItem(PENDING_KEY) || "[]");
      return Array.isArray(list) ? list : [];
    } catch (_) { return []; }
  }

  function writePending(list) {
    try {
      if (list.length) sessionStorage.setItem(PENDING_KEY, JSON.stringify(list));
      else sessionStorage.removeItem(PENDING_KEY);
    } catch (_) { /* sessionStorage bị chặn → còn đường gửi thẳng */ }
  }

  function send(snapshot) {
    const others = readPending().filter((s) => s?.snapshotId !== snapshot.snapshotId);
    writePending([...others, snapshot].slice(-20));
    try {
      chrome.runtime.sendMessage({ action: "formSnapshot", snapshot }, (res) => {
        void chrome.runtime.lastError;
        if (res?.ok) writePending(readPending().filter((s) => s?.snapshotId !== snapshot.snapshotId));
      });
    } catch (_) { /* extension vừa nạp lại — ảnh còn trong sessionStorage */ }
  }

  function capture(kind, trigger = "") {
    if (!session) return;
    clearTimeout(editTimer);
    editTimer = 0;
    const extra = FS.listExtra(session.fields, session.formKind);
    const fields = FS.readFields([...session.fields, ...extra].slice(0, MAX_FIELDS), session.formKind);
    // Sang bước sau, cổng SPA gỡ form khỏi DOM: không còn ô nào của BE để đọc → không gửi ảnh rỗng.
    if (kind !== "fill" && fields.slice(0, session.fields.length).every((f) => f.value === null)) return;
    const values = JSON.stringify(fields.map((f) => f.value));
    if (kind === "edit" && values === session.lastValues) return;
    session.lastValues = values;
    send({
      snapshotId: newId(), requestId: session.requestId, kind, trigger: String(trigger).slice(0, 120),
      host: location.hostname, path: (location.pathname + location.hash).slice(0, 500), at: Date.now(), fields,
      extVersion: EXT_VERSION,
    });
  }

  function onStep(trigger) {
    if (Date.now() - lastStepAt < STEP_DEDUPE_MS) return;
    lastStepAt = Date.now();
    capture("step", trigger);
  }

  function onUserAction(e) {
    if (!e.isTrusted || !session?.ready) return;
    clearTimeout(editTimer);
    editTimer = setTimeout(() => capture("edit"), EDIT_IDLE_MS);
  }

  // Mọi frame nhận lệnh điền: nhớ luật để bắt nút rời bước kể cả frame không chứa form.
  FS.arm = (cfg) => {
    if (cfg?.requestId) config = cfg;
  };

  // Frame đã điền: giữ danh sách field BE trả để đọc lại.
  FS.track = (cfg, fields, formKind) => {
    if (!cfg?.requestId || !Array.isArray(fields) || !fields.length) return;
    config = cfg;
    const current = { requestId: cfg.requestId, fields, formKind, lastValues: null, ready: false };
    session = current;
    setTimeout(() => {
      if (session !== current) return;
      capture("fill");
      current.ready = true;
    }, FILL_SETTLE_MS);
  };

  // Chọn option Choices/mat-select không phát input/change thật → nghe cả phím và chuột.
  for (const type of ["input", "change", "keyup", "pointerup"]) document.addEventListener(type, onUserAction, true);
  window.addEventListener("pagehide", () => { if (editTimer) capture("edit"); });

  // capture: cổng có handler riêng có thể stopPropagation; Angular huỷ DOM bước ngay sau cú bấm.
  document.addEventListener("click", (e) => {
    if (!e.isTrusted || !config?.stepRules) return;
    const trigger = FS.matchStep(config.stepRules, e.target?.closest?.(FS.CLICKABLE));
    if (!trigger) return;
    onStep(trigger);
    try { chrome.runtime.sendMessage({ action: "formSnapshotStep", trigger }, () => void chrome.runtime.lastError); }
    catch (_) { /* extension vừa nạp lại */ }
  }, true);

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.action === "formSnapshotCapture") onStep(String(msg.trigger || ""));
  });

  readPending().filter((s) => Date.now() - Number(s?.at || 0) < PENDING_MAX_AGE_MS).forEach(send);
})();
