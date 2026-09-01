// content.js — KHUNG SIDEBAR "Trợ lý người dân" (push-layout, KHÔNG che nội dung trang).
// Làm theo spec ../01-sidebar-panel-push-layout.md (§3.1–3.7), đổi prefix tro-ly-nguoi-dan/__tlnd.
//
// Vai trò file này: dựng/thu sidebar + launcher + persist; ĐIỀU PHỐI message.
// Việc ĐIỀN FORM nằm ở content/fill-core.js + các engine fill-* (nạp TRƯỚC file này).
(() => {
  if (window.__TLND_CONTENT__) return; // guard chống inject trùng
  window.__TLND_CONTENT__ = true;
  const H = window.__TLND__ || (window.__TLND__ = {});

  const PANEL_ID = "tro-ly-nguoi-dan-panel";
  const BUBBLE_ID = "tro-ly-nguoi-dan-bubble";
  const IFRAME_ID = "tro-ly-nguoi-dan-iframe";
  const TW_OVERRIDE_ID = "tro-ly-nguoi-dan-tw-translate-override";
  const BUSINESS_PROGRESS_ID = "tro-ly-nguoi-dan-business-progress";
  const LEGACY_AUTOFILL_PROGRESS_ID = "af-fillall-progress";
  const LEGACY_AUTOFILL_CANCEL_ID = "af-fillall-progress-cancel";
  const BUSINESS_RUN_KEY = "tlnd_business_registration_run";
  const BUSINESS_FILL_STATE_KEY = "autofill_fillall_state";
  const BUSINESS_ATTACH_STATE_KEY = "autofill_attachall_state";
  const SS_BUSINESS_ACTIVE_KEY = "__tlnd_business_run_active";
  const SS_BUSINESS_PROGRESS_KEY = "__tlnd_business_run_progress";
  const SIDEBAR_WIDTH = 400;               // px, = width panel = marginRight trang (cố định)
  const SS_OPEN_KEY = "__tlnd_panel_open"; // sessionStorage (cùng origin), chống giật khi reload
  const LEGACY_SS_DISMISS_KEY = "__tlnd_dismissed"; // dọn cờ "tắt hẳn" từ bản extension cũ
  const LEGACY_LS_DISMISS_KEY = "tlnd_dismissed";
  const JOURNEY_KEY = "tlnd_journey";
  const LAUNCHER_POSITION_KEY = "tlnd_launcher_position_v1";
  const LAUNCHER_SIZE = 80;
  const LAUNCHER_EDGE_GAP = 8;
  const IS_TOP_FRAME = window === window.top;
  const IS_DVC_HOST = location.origin === "https://dichvucong.gov.vn";
  const IS_DVC_HOME = IS_DVC_HOST && location.pathname === "/";
  const IS_BUSINESS_HOST = location.hostname === "hokinhdoanh.dkkd.gov.vn";
  const LAUNCHER_LOGO_URL = chrome.runtime.getURL("assets/icons/icon-128.png");

  let _origHtmlMarginRight = "";
  let _origHtmlTransition = "";
  let _origHtmlOverflowX = "";
  let legacyAutoFillProgressWatcher = null;

  // Hoạt động thật trên trang cổng cũng giữ phiên sống. Nếu chỉ nghe event trong iframe sidebar,
  // người dân đang rà/điền form trên trang sẽ bị timeout oan sau 10 phút.
  let _activityTabId = "";
  let _lastActivityWriteAt = 0;
  function persistPageActivity() {
    if (!IS_TOP_FRAME || Date.now() - _lastActivityWriteAt < 5000) return;
    const write = (tabId) => {
      if (!tabId) return;
      const now = Date.now();
      _lastActivityWriteAt = now;
      chrome.storage.local.get([JOURNEY_KEY], (res) => {
        const journeys = res?.[JOURNEY_KEY] || {};
        const current = journeys[tabId];
        if (!current?.conversation_id) return; // chưa bấm Bắt đầu → không tạo dấu phiên giả
        journeys[tabId] = { ...current, ts: now, last_activity_at: now };
        chrome.storage.local.set({ [JOURNEY_KEY]: journeys }, () => void chrome.runtime.lastError);
      });
    };
    if (_activityTabId) { write(_activityTabId); return; }
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      if (chrome.runtime.lastError) return;
      _activityTabId = String(res?.tabId ?? "");
      write(_activityTabId);
    });
  }
  // HkdOnline tự chạy qua nhiều full postback, không có event isTrusted của công dân. Cho adapter
  // chạm cùng journey để tiến trình tự động không bị quy tắc idle 10 phút xóa nhầm conversation.
  H.persistPageActivity = persistPageActivity;
  for (const eventName of ["pointerdown", "keydown", "input", "change", "scroll"]) {
    document.addEventListener(eventName, (event) => {
      if (event.isTrusted) persistPageActivity();
    }, { capture: true, passive: true });
  }

  // Nếu công dân tự bấm Đăng xuất trong lúc BOT đang chờ quyết định sau khi nộp hồ sơ,
  // sidebar phải hủy ngay bộ đếm của phiên cũ. Khớp nhãn hiển thị thay vì id/class riêng
  // từng cổng; chỉ nghe click thật ở top frame để không nhận nhầm menu ẩn hoặc script.
  document.addEventListener("click", (event) => {
    if (!IS_TOP_FRAME || !event.isTrusted) return;
    const control = event.composedPath?.().find((node) => node?.matches?.(
      'button, a, [role="button"], [role="menuitem"]'
    ));
    if (!control) return;
    const label = String(control.innerText || control.textContent || control.getAttribute?.("aria-label") || "")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/Đ/g, "D").replace(/đ/g, "d").replace(/\s+/g, " ").trim().toLowerCase();
    if (label !== "dang xuat" && !label.startsWith("dang xuat ")) return;
    chrome.runtime.sendMessage({ action: "citizenManualLogoutDetected" }, () => {
      void chrome.runtime.lastError;
    });
  }, { capture: true });

  // ── Push-layout: đẩy trang sang trái bằng marginRight trên <html> ──
  function applySidebarPushLayout() {
    const de = document.documentElement;
    _origHtmlMarginRight = de.style.marginRight || "";
    _origHtmlTransition = de.style.transition || "";
    _origHtmlOverflowX = de.style.overflowX || "";
    de.style.overflowX = "hidden";
    de.style.transition = "margin-right .3s cubic-bezier(.4,0,.2,1)";
    de.style.marginRight = `${SIDEBAR_WIDTH}px`;
  }
  function restoreSidebarPushLayout() {
    const de = document.documentElement;
    de.style.marginRight = _origHtmlMarginRight;
    de.style.transition = _origHtmlTransition;
    de.style.overflowX = _origHtmlOverflowX;
  }
  // Bù lệch dialog Tailwind căn giữa của trang (no-op với cổng không dùng Tailwind).
  function ensureTranslateOverrideStyle() {
    if (document.getElementById(TW_OVERRIDE_ID)) return;
    const st = document.createElement("style");
    st.id = TW_OVERRIDE_ID;
    const half = SIDEBAR_WIDTH / 2;
    st.textContent = `
      .translate-x-\\[-50\\%\\]{--tw-translate-x:calc(-50% - ${half}px)!important;}
      .data-\\[state\\=open\\]\\:slide-in-from-left-1\\/2[data-state=open]{
        --tw-enter-translate-x:calc(-50% - ${half}px)!important;}`;
    (document.head || document.documentElement).appendChild(st);
  }
  function removeTranslateOverrideStyle() {
    document.getElementById(TW_OVERRIDE_ID)?.remove();
  }

  // ── Panel (Shadow DOM host + iframe sidebar.html) ──
  function createPanel(tabId) {
    if (!IS_TOP_FRAME) return;
    const existing = document.getElementById(PANEL_ID);
    if (existing) return existing;

    const host = document.createElement("div");
    host.id = PANEL_ID;
    const shadow = host.attachShadow({ mode: "open" });
    const sidebarQuery = new URLSearchParams({ embedded: "1", tabId: String(tabId ?? "") });
    // Trang chủ DVC là điểm bắt đầu một lượt công dân mới. Báo cho iframe xóa conversation
    // cũ thay vì khôi phục journey còn sót từ trang thủ tục vừa quay về.
    if (IS_DVC_HOME) sidebarQuery.set("fresh", "dvc-home");
    shadow.innerHTML = `
      <style>
        :host {
          position: fixed; right: 0; top: 0; bottom: 0;
          width: ${SIDEBAR_WIDTH}px; z-index: 2147483647;
          transform: translateX(100%);
          transition: transform .3s cubic-bezier(.4,0,.2,1);
          background: #fff; box-shadow: -8px 0 32px rgba(15,40,80,.14);
          display: block;
        }
        :host(.open) { transform: translateX(0); }
        iframe { width:100%; height:100%; border:0; display:block; background:#fff; }
      </style>
      <iframe id="${IFRAME_ID}" allow="camera; microphone"
        src="${chrome.runtime.getURL(`sidebar.html?${sidebarQuery.toString()}`)}"></iframe>`;

    (document.body || document.documentElement).appendChild(host);

    hideLauncher();
    applySidebarPushLayout();
    ensureTranslateOverrideStyle();
    requestAnimationFrame(() => host.classList.add("open")); // kích hoạt trượt vào
    persistOpen(true);
    return host;
  }

  function minimizePanel() {
    const host = document.getElementById(PANEL_ID);
    if (!host) return;
    host.classList.remove("open");   // trượt ra
    restoreSidebarPushLayout();      // trả lại layout ngay
    showLauncher();
    persistOpen(false);
    // Giữ iframe sống (không mất state chat) — chỉ ẩn sau khi trượt xong.
    setTimeout(() => {
      // Công dân có thể bấm launcher mở lại ngay khi animation chưa kết thúc.
      // Chỉ ẩn nếu panel vẫn đang thu gọn, tránh timer cũ đóng nhầm panel vừa mở.
      if (host && !host.classList.contains("open")) host.style.display = "none";
    }, 320);
  }

  function restorePanel() {
    const host = document.getElementById(PANEL_ID);
    hideLauncher();
    if (!host) { togglePanel(); return; }
    host.style.display = "block";
    applySidebarPushLayout();
    requestAnimationFrame(() => host.classList.add("open"));
    persistOpen(true);
  }

  function closePanel() {
    // ✕ không còn mang nghĩa "tắt hẳn". Giữ iframe và phiên hội thoại sống,
    // chỉ thu panel về launcher giống nút – để công dân luôn có đường mở lại rõ ràng.
    minimizePanel();
  }

  function togglePanel() {
    if (!IS_TOP_FRAME) return;
    const host = document.getElementById(PANEL_ID);
    if (host && host.style.display !== "none" && host.classList.contains("open")) { closePanel(); return; }
    if (host) { restorePanel(); return; }
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      if (chrome.runtime.lastError) { createPanel(""); return; }
      createPanel(res?.tabId ?? "");
    });
  }

  function launcherPositionBounds() {
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth || LAUNCHER_SIZE;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight || LAUNCHER_SIZE;
    return {
      minLeft: LAUNCHER_EDGE_GAP,
      minTop: LAUNCHER_EDGE_GAP,
      maxLeft: Math.max(LAUNCHER_EDGE_GAP, viewportWidth - LAUNCHER_SIZE - LAUNCHER_EDGE_GAP),
      maxTop: Math.max(LAUNCHER_EDGE_GAP, viewportHeight - LAUNCHER_SIZE - LAUNCHER_EDGE_GAP),
    };
  }

  function clampLauncherPosition(left, top) {
    const bounds = launcherPositionBounds();
    return {
      left: Math.min(Math.max(Number(left) || bounds.minLeft, bounds.minLeft), bounds.maxLeft),
      top: Math.min(Math.max(Number(top) || bounds.minTop, bounds.minTop), bounds.maxTop),
    };
  }

  function normalizeLauncherPosition(left, top) {
    const bounds = launcherPositionBounds();
    const safe = clampLauncherPosition(left, top);
    const horizontalRange = bounds.maxLeft - bounds.minLeft;
    const verticalRange = bounds.maxTop - bounds.minTop;
    return {
      ...safe,
      xRatio: horizontalRange > 0 ? (safe.left - bounds.minLeft) / horizontalRange : 0,
      yRatio: verticalRange > 0 ? (safe.top - bounds.minTop) / verticalRange : 0,
    };
  }

  function applyLauncherPosition(button, position) {
    if (!button || !position) return;
    const bounds = launcherPositionBounds();
    const hasRatios = Number.isFinite(position.xRatio) && Number.isFinite(position.yRatio);
    const left = hasRatios
      ? bounds.minLeft + Math.min(Math.max(position.xRatio, 0), 1) * (bounds.maxLeft - bounds.minLeft)
      : position.left;
    const top = hasRatios
      ? bounds.minTop + Math.min(Math.max(position.yRatio, 0), 1) * (bounds.maxTop - bounds.minTop)
      : position.top;
    const safe = normalizeLauncherPosition(left, top);
    button.style.left = `${safe.left}px`;
    button.style.top = `${safe.top}px`;
    button.style.right = "auto";
    button.style.bottom = "auto";
    button.dataset.launcherXRatio = String(safe.xRatio);
    button.dataset.launcherYRatio = String(safe.yRatio);
    return safe;
  }

  function restoreLauncherPosition(button) {
    try {
      chrome.storage.local.get([LAUNCHER_POSITION_KEY], (stored) => {
        if (!chrome.runtime.lastError) {
          const position = stored?.[LAUNCHER_POSITION_KEY];
          if ((Number.isFinite(position?.xRatio) && Number.isFinite(position?.yRatio))
              || (Number.isFinite(position?.left) && Number.isFinite(position?.top))) {
            applyLauncherPosition(button, position);
          }
        }
        button.style.visibility = "visible";
      });
    } catch (_) {
      button.style.visibility = "visible";
    }
  }

  function persistLauncherPosition(button) {
    if (!button) return;
    const rect = button.getBoundingClientRect();
    const position = applyLauncherPosition(button, { left: rect.left, top: rect.top });
    try {
      chrome.storage.local.set({ [LAUNCHER_POSITION_KEY]: position }, () => void chrome.runtime.lastError);
    } catch (_) {}
  }

  function reflowLauncherPosition(button) {
    if (!button) return;
    const xRatio = Number(button.dataset.launcherXRatio);
    const yRatio = Number(button.dataset.launcherYRatio);
    if (Number.isFinite(xRatio) && Number.isFinite(yRatio)) {
      applyLauncherPosition(button, { xRatio, yRatio });
      return;
    }
    const rect = button.getBoundingClientRect();
    applyLauncherPosition(button, { left: rect.left, top: rect.top });
  }

  function enableLauncherDrag(button) {
    let drag = null;
    let suppressClick = false;
    button.addEventListener("pointerdown", (event) => {
      if (event.button != null && event.button !== 0) return;
      const rect = button.getBoundingClientRect();
      drag = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        left: rect.left,
        top: rect.top,
        moved: false,
      };
      button.dataset.dragging = "1";
      button.style.transition = "none";
      button.style.transform = "scale(1)";
      try { button.setPointerCapture(event.pointerId); } catch (_) {}
    });
    button.addEventListener("pointermove", (event) => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      const dx = event.clientX - drag.startX;
      const dy = event.clientY - drag.startY;
      if (!drag.moved && Math.hypot(dx, dy) < 4) return;
      drag.moved = true;
      event.preventDefault();
      applyLauncherPosition(button, { left: drag.left + dx, top: drag.top + dy });
    });
    const finishDrag = (event) => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      suppressClick = drag.moved;
      if (drag.moved) persistLauncherPosition(button);
      try { button.releasePointerCapture(event.pointerId); } catch (_) {}
      drag = null;
      delete button.dataset.dragging;
      button.style.transition = "transform .15s ease";
    };
    button.addEventListener("pointerup", finishDrag);
    button.addEventListener("pointercancel", finishDrag);
    button.addEventListener("click", (event) => {
      if (suppressClick) {
        suppressClick = false;
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      togglePanel();
    });
  }

  // ── Launcher: logo HCC lớn ở mép phải-trên, hiện khi panel thu gọn ──
  function showLauncher() {
    if (!IS_TOP_FRAME) return;
    let b = document.getElementById(BUBBLE_ID);
    if (!b) {
      b = document.createElement("button");
      b.type = "button";
      b.id = BUBBLE_ID;
      b.title = "Mở Trợ lý người dân";
      b.setAttribute("aria-label", "Mở Trợ lý người dân");
      Object.assign(b.style, {
        position: "fixed", right: "18px", top: "22px",
        width: "80px", height: "80px", borderRadius: "24px",
        cursor: "pointer", zIndex: "2147483646",
        padding: "7px", border: "1px solid rgba(23,58,94,.16)",
        background: "#fff",
        boxShadow: "0 6px 20px rgba(15,40,80,.35)",
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "transform .15s ease", touchAction: "none", userSelect: "none",
        visibility: "hidden",
      });
      b.innerHTML = `<img src="${LAUNCHER_LOGO_URL}" alt="" aria-hidden="true"
        draggable="false" style="display:block;width:100%;height:100%;object-fit:contain;border-radius:18px;pointer-events:none">`;
      b.addEventListener("mouseenter", () => {
        if (!b.dataset.dragging) b.style.transform = "scale(1.08)";
      });
      b.addEventListener("mouseleave", () => {
        if (!b.dataset.dragging) b.style.transform = "scale(1)";
      });
      enableLauncherDrag(b);
      document.documentElement.appendChild(b);
      restoreLauncherPosition(b);
    }
    b.style.display = "flex";
    reflowLauncherPosition(b);
  }
  function hideLauncher() {
    const b = document.getElementById(BUBBLE_ID);
    if (b) b.style.display = "none";
  }

  // HkdOnline full-postback sau mỗi nút Lưu. Trong lúc chạy, không dựng lại iframe sidebar
  // và không giữ margin-right 400px: hai việc đó làm trang co/giãn ở mọi postback. Thẻ tiến độ
  // dùng Shadow DOM + position:fixed nên không tham gia layout của cổng và chỉ cập nhật text/transform.
  function readBusinessProgressMirror() {
    try {
      const raw = sessionStorage.getItem(SS_BUSINESS_PROGRESS_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  }

  function writeBusinessProgressMirror(payload) {
    try {
      sessionStorage.setItem(SS_BUSINESS_ACTIVE_KEY, "1");
      sessionStorage.setItem(SS_BUSINESS_PROGRESS_KEY, JSON.stringify(payload || {}));
    } catch (_) { /* chrome.storage RUN_KEY vẫn là nguồn chuẩn qua postback */ }
  }

  function clearBusinessProgressMirror() {
    try {
      sessionStorage.removeItem(SS_BUSINESS_ACTIVE_KEY);
      sessionStorage.removeItem(SS_BUSINESS_PROGRESS_KEY);
    } catch (_) { /* ignore */ }
  }

  function releaseSidebarLayoutWithoutMotion() {
    const de = document.documentElement;
    de.style.transition = "none";
    de.style.marginRight = _origHtmlMarginRight;
    de.style.overflowX = _origHtmlOverflowX;
    removeTranslateOverrideStyle();
    // Khôi phục transition gốc ở frame kế, sau khi margin đã về đúng vị trí. Không force-reflow.
    requestAnimationFrame(() => {
      if (sessionStorage.getItem(SS_BUSINESS_ACTIVE_KEY) === "1") {
        de.style.transition = _origHtmlTransition;
      }
    });
  }

  function suspendSidebarForBusinessRun() {
    if (!IS_TOP_FRAME) return;
    const panel = document.getElementById(PANEL_ID);
    if (panel) {
      panel.classList.remove("open");
      panel.style.display = "none";
    }
    hideLauncher();
    releaseSidebarLayoutWithoutMotion();
  }

  function cancelLegacyAutoFillBusinessRun() {
    const legacy = document.getElementById(LEGACY_AUTOFILL_PROGRESS_ID);
    if (!legacy) return false;
    // Banner xanh thuộc extension Auto-fill. Click nút Huỷ thật để handler của extension đó xóa
    // state fill/attach của chính nó; chỉ remove DOM sẽ khiến engine cũ vẫn âm thầm điền song song.
    const cancel = legacy.querySelector(`#${LEGACY_AUTOFILL_CANCEL_ID}`);
    if (cancel) {
      try { cancel.click(); } catch (_) { /* vẫn gỡ banner bên dưới */ }
    }
    legacy.remove();
    return true;
  }

  function watchAndCancelLegacyAutoFillBusinessRun() {
    cancelLegacyAutoFillBusinessRun();
    if (legacyAutoFillProgressWatcher || !document.documentElement) return;
    // Hai extension cùng inject document_start nên banner cũ có thể xuất hiện sau thẻ Handfree.
    // Theo dõi trong suốt phiên để hủy ngay cả khi thứ tự khởi tạo thay đổi qua full postback.
    legacyAutoFillProgressWatcher = new MutationObserver(() => cancelLegacyAutoFillBusinessRun());
    legacyAutoFillProgressWatcher.observe(document.documentElement, { childList: true, subtree: true });
  }

  function stopLegacyAutoFillProgressWatcher() {
    legacyAutoFillProgressWatcher?.disconnect();
    legacyAutoFillProgressWatcher = null;
  }

  function normalizeBusinessProgress(text, meta = {}) {
    const raw = String(text || "").trim();
    const firstLine = raw.split("\n").map((line) => line.trim()).find(Boolean) || "Đang xử lý hồ sơ";
    const ratio = raw.match(/(\d+)\s*\/\s*(\d+)/);
    const step = Number(meta.step || ratio?.[1] || 0);
    const total = Number(meta.total || ratio?.[2] || 0);
    const bootstrapStage = /—\s*(home|select-registration|confirm|unknown)\b/i.test(raw);
    const phase = meta.phase || (bootstrapStage
      ? "bootstrap"
      : (/đính kèm|tài liệu/i.test(raw) ? "attach" : "fill"));
    const title = phase === "bootstrap"
      ? "Đang tự động mở trang kê khai"
      : "Đang tự động kê khai thông tin và đính kèm";
    let detail = String(meta.label || firstLine)
      .replace(/^Đang điền (khối|trang)\s+\d+\/\d+\s*[—-]?\s*/i, "")
      .replace(/\s*\(đừng thao tác tới khi xong\)\s*/gi, "")
      .trim();

    if (/—\s*home\b/i.test(raw)) detail = "Đang mở trang đăng ký hộ kinh doanh";
    else if (/—\s*select-registration\b/i.test(raw)) detail = "Đang chọn Thành lập mới hộ kinh doanh";
    else if (/—\s*confirm\b/i.test(raw)) detail = "Đang xác nhận và mở trang kê khai";
    if (!detail) detail = "Công dân chờ em xử lý hồ sơ ạ.";

    return {
      text: raw,
      title,
      detail,
      step: step > 0 ? step : 0,
      total: total > 0 ? total : 0,
      phase,
    };
  }

  function ensureBusinessProgressCard() {
    let host = document.getElementById(BUSINESS_PROGRESS_ID);
    if (host) return host;
    host = document.createElement("div");
    host.id = BUSINESS_PROGRESS_ID;
    host.setAttribute("data-tlnd-owned", "1");
    Object.assign(host.style, {
      position: "fixed", top: "14px", right: "14px", width: "min(360px, calc(100vw - 28px))",
      zIndex: "2147483647", display: "block", pointerEvents: "auto",
      contain: "layout style",
    });
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host { color-scheme: light; }
        * { box-sizing: border-box; }
        .card {
          overflow: hidden; border: 1px solid #b9dfd2; border-radius: 14px;
          background: rgba(255,255,255,.98); color: #17324d;
          box-shadow: 0 10px 28px rgba(15, 61, 82, .18);
          font: 400 14px/1.45 system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
        }
        .body { padding: 14px 14px 12px; }
        .head { display: flex; align-items: flex-start; gap: 10px; }
        .spinner {
          flex: 0 0 22px; width: 22px; height: 22px; margin-top: 1px;
          color: #0a8f68; animation: tlnd-spin .9s linear infinite;
        }
        .copy { min-width: 0; flex: 1; }
        .title { margin: 0; color: #096b52; font-size: 14px; line-height: 1.35; font-weight: 750; }
        .detail { margin: 3px 0 0; color: #28465f; font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }
        .meta { display: flex; justify-content: space-between; gap: 12px; margin-top: 11px; color: #5b7185; font-size: 12px; }
        .step { font-variant-numeric: tabular-nums; font-weight: 650; color: #36566f; }
        .track { height: 5px; margin-top: 7px; overflow: hidden; border-radius: 999px; background: #e4f2ed; }
        .bar {
          width: 100%; height: 100%; border-radius: inherit; background: #10a77b;
          transform: scaleX(.2); transform-origin: left center;
          transition: transform 220ms ease-out; will-change: transform;
        }
        .actions { display: flex; justify-content: flex-end; margin-top: 12px; }
        button {
          min-height: 44px; padding: 0 15px; border: 1px solid #d8a5a5; border-radius: 10px;
          background: #fff; color: #a12626; cursor: pointer; font: 700 13px/1 system-ui, sans-serif;
          transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
          touch-action: manipulation;
        }
        button:hover { background: #fff5f5; border-color: #c97979; }
        button:active { background: #fde8e8; }
        button:focus-visible { outline: 3px solid rgba(10,143,104,.32); outline-offset: 2px; }
        button:disabled { cursor: wait; opacity: .62; }
        @keyframes tlnd-spin { to { transform: rotate(360deg); } }
        @media (prefers-reduced-motion: reduce) {
          .spinner { animation: none; }
          .bar, button { transition: none; }
        }
      </style>
      <section class="card" role="region" aria-label="Tiến trình tự động kê khai hộ kinh doanh">
        <div class="body">
          <div class="head">
            <svg class="spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="3" opacity=".22"></circle>
              <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="3" stroke-linecap="round"></path>
            </svg>
            <div class="copy">
              <p class="title" id="title">Đang tự động mở trang kê khai</p>
              <p class="detail" id="detail" aria-live="polite">Công dân chờ em xử lý hồ sơ ạ.</p>
            </div>
          </div>
          <div class="meta"><span id="phase">Hồ sơ hộ kinh doanh</span><span class="step" id="step"></span></div>
          <div class="track" id="track" role="progressbar" aria-label="Tiến độ xử lý">
            <div class="bar" id="bar"></div>
          </div>
          <div class="actions">
            <button id="cancel" type="button" aria-label="Dừng tiến trình tự động kê khai">
              Dừng tiến trình
            </button>
          </div>
        </div>
      </section>`;
    const cancel = shadow.getElementById("cancel");
    cancel.addEventListener("click", async () => {
      if (cancel.disabled) return;
      cancel.disabled = true;
      cancel.textContent = "Đang dừng…";
      shadow.getElementById("title").textContent = "Đang dừng tiến trình";
      shadow.getElementById("detail").textContent = "Em đang dừng ở bước an toàn gần nhất ạ.";
      if (typeof H.cancelBusinessRegistrationRun === "function") {
        await H.cancelBusinessRegistrationRun();
        return;
      }
      chrome.storage.local.remove(
        [BUSINESS_RUN_KEY, BUSINESS_FILL_STATE_KEY, BUSINESS_ATTACH_STATE_KEY],
        () => H.finishBusinessRunUI?.("Đã dừng tiến trình tự động kê khai.")
      );
    });
    (document.documentElement || document.body).appendChild(host);
    return host;
  }

  function showBusinessProgress(text, meta = {}) {
    if (!IS_TOP_FRAME) return false;
    watchAndCancelLegacyAutoFillBusinessRun();
    const state = normalizeBusinessProgress(text, meta);
    writeBusinessProgressMirror(state);
    suspendSidebarForBusinessRun();
    const host = ensureBusinessProgressCard();
    const shadow = host.shadowRoot;
    shadow.getElementById("title").textContent = state.title;
    shadow.getElementById("detail").textContent = state.detail;
    shadow.getElementById("phase").textContent = state.phase === "attach"
      ? "Văn bản đính kèm" : "Hồ sơ hộ kinh doanh";
    const determinate = state.step > 0 && state.total > 0;
    shadow.getElementById("step").textContent = determinate ? `Khối ${state.step}/${state.total}` : "Đang xử lý";
    const track = shadow.getElementById("track");
    if (determinate) {
      const pct = Math.max(0.04, Math.min(1, state.step / state.total));
      shadow.getElementById("bar").style.transform = `scaleX(${pct})`;
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", String(state.total));
      track.setAttribute("aria-valuenow", String(state.step));
    } else {
      shadow.getElementById("bar").style.transform = "scaleX(.2)";
      track.removeAttribute("aria-valuemin");
      track.removeAttribute("aria-valuemax");
      track.removeAttribute("aria-valuenow");
    }
    return true;
  }

  function waitForPanelIframe(host, timeout = 1800) {
    return new Promise((resolve) => {
      const iframe = host?.shadowRoot?.getElementById(IFRAME_ID);
      if (!iframe) { resolve(); return; }
      let done = false;
      const finish = () => { if (!done) { done = true; clearTimeout(timer); resolve(); } };
      const timer = setTimeout(finish, timeout);
      iframe.addEventListener("load", finish, { once: true });
    });
  }

  async function finishBusinessRunUI() {
    if (!IS_TOP_FRAME) return;
    stopLegacyAutoFillProgressWatcher();
    clearBusinessProgressMirror();
    document.getElementById(BUSINESS_PROGRESS_ID)?.remove();
    const existing = document.getElementById(PANEL_ID);
    if (existing) {
      existing.style.display = "block";
      hideLauncher();
      applySidebarPushLayout();
      requestAnimationFrame(() => existing.classList.add("open"));
      persistOpen(true);
      return;
    }
    const host = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
        resolve(createPanel(chrome.runtime.lastError ? "" : (res?.tabId ?? "")));
      });
    });
    await waitForPanelIframe(host);
  }

  H.beginBusinessRunUI = (text, meta = {}) => showBusinessProgress(
    text || "Đang bắt đầu xử lý hồ sơ hộ kinh doanh…",
    meta
  );
  H.updateBusinessRunUI = showBusinessProgress;
  H.finishBusinessRunUI = finishBusinessRunUI;
  // ── Persist theo phiên trang (cùng origin) + journey (XUYÊN origin — docs/07 §2.1) ──
  function persistOpen(open) {
    // Giữ đủ ba trạng thái: "1" = đang mở, "0" = công dân chủ động thu gọn,
    // null = trang/context mới chưa biết trạng thái. Nếu xóa key khi thu gọn thì trang kế
    // tiếp không phân biệt được "đã thu" với "journey chưa kịp phục hồi".
    try { sessionStorage.setItem(SS_OPEN_KEY, open ? "1" : "0"); } catch (_) {}
  }
  function clearLegacyDismissedState() {
    // Bản cũ có thể để lại cờ ẩn toàn cục. Nếu không dọn, người đã từng bấm ✕
    // sẽ không nhìn thấy launcher dù bản mới không còn khái niệm "tắt hẳn".
    try { sessionStorage.removeItem(LEGACY_SS_DISMISS_KEY); } catch (_) {}
    try { chrome.storage.local.remove(LEGACY_LS_DISMISS_KEY, () => void chrome.runtime.lastError); } catch (_) {}
  }
  // Trang đăng nhập SSO/VNeID: khi ĐANG trong luồng (journey keep_open) → MỞ panel để bot đọc
  // kịch bản đăng nhập (mở VNeID → Quét QR); đọc xong sidebar tự thu gọn (collapse_after_tts) để
  // lộ mã QR. Ngoài luồng (tự vào trang SSO) → chỉ bong bóng, không chen màn quét QR.
  const IS_LOGIN_PAGE = /xacthuc|vneid|sso/.test(location.hostname);
  function restoreEarly() {
    if (!IS_TOP_FRAME) return;
    clearLegacyDismissedState();
    if (IS_BUSINESS_HOST) {
      const mirrored = readBusinessProgressMirror();
      // Mirror chỉ để dựng thẻ ngay, tránh khe trống lúc chờ chrome.storage. RUN_KEY mới là
      // nguồn chuẩn: nếu không còn RUN_KEY thì dọn mirror cũ và khôi phục panel bình thường.
      if (mirrored || sessionStorage.getItem(SS_BUSINESS_ACTIVE_KEY) === "1") {
        showBusinessProgress(mirrored?.text || "Đang tiếp tục xử lý hồ sơ hộ kinh doanh…", mirrored || {});
      }
      chrome.storage.local.get([BUSINESS_RUN_KEY], (res) => {
        if (chrome.runtime.lastError) {
          if (!mirrored) showInitial();
          return;
        }
        const run = res?.[BUSINESS_RUN_KEY];
        if (run) {
          showBusinessProgress(
            run.progressText || mirrored?.text || "Đang tiếp tục xử lý hồ sơ hộ kinh doanh…",
            {
              step: run.currentPage,
              total: run.totalPages,
              label: run.progressLabel,
              phase: run.progressPhase,
            }
          );
          return;
        }
        clearBusinessProgressMirror();
        document.getElementById(BUSINESS_PROGRESS_ID)?.remove();
        showInitial();
      });
      return;
    }
    // Trang chủ DVC quốc gia là điểm bắt đầu hành trình: mỗi lần vào/reload phải mở trợ lý.
    // Chỉ chạy lúc content script khởi tạo, nên bấm ✕ sau đó vẫn thu gọn bình thường.
    if (IS_DVC_HOME) { ensurePanelOpen(); return; }
    // Trang con DVC không được journey ép tự mở. Chỉ giữ đúng trạng thái trước điều hướng:
    // đang mở thì tiếp tục mở, đã thu gọn thì chỉ hiện launcher.
    if (IS_DVC_HOST) { showDvcChildInitial(); return; }
    showInitial();
  }
  function showDvcChildInitial() {
    let state = null;
    try { state = sessionStorage.getItem(SS_OPEN_KEY); } catch (_) {}
    if (state === "1") { ensurePanelOpen(); return; }
    if (state === "0") { showLauncher(); return; }
    // Lần điều hướng đầu tiên có thể sang context chưa có session key. Khi đó phải đọc
    // journey của đúng tab giống các origin khác; không được mặc định coi là đã thu gọn.
    showInitial();
  }
  function ensurePanelOpen() {
    const host = document.getElementById(PANEL_ID);
    if (host) {
      if (host.style.display === "none" || !host.classList.contains("open")) restorePanel();
      return;
    }
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      if (chrome.runtime.lastError) { createPanel(""); return; }
      createPanel(res?.tabId ?? "");
    });
  }
  function showInitial() {
    if (IS_LOGIN_PAGE) {
      // Đang trong luồng → mở panel đọc kịch bản đăng nhập (đọc xong tự thu gọn lộ QR);
      // ngoài luồng → chỉ bong bóng cho thoáng màn quét.
      chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
        const tabId = chrome.runtime.lastError ? "" : (res?.tabId ?? "");
        chrome.storage.local.get(["tlnd_journey"], (st) => {
          const j = chrome.runtime.lastError ? null : st?.tlnd_journey?.[tabId];
          if (j?.keep_open && Date.now() - (j.ts || 0) < 30 * 60 * 1000) createPanel(tabId);
          else showLauncher();
        });
      });
      return;
    }
    let wasOpen = false;
    try { wasOpen = sessionStorage.getItem(SS_OPEN_KEY) === "1"; } catch (_) {}
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      if (chrome.runtime.lastError) { if (wasOpen) createPanel(""); else showLauncher(); return; }
      const tabId = res?.tabId ?? "";
      if (wasOpen) { createPanel(tabId); return; }
      // Khác origin (sessionStorage mới tinh): journey của tab còn tươi → TỰ MỞ LẠI
      // để bot làm tiếp việc dang dở (chọn cơ quan, hướng dẫn đăng nhập...).
      chrome.storage.local.get(["tlnd_journey"], (st) => {
        if (chrome.runtime.lastError) { showLauncher(); return; }
        const j = st?.tlnd_journey?.[tabId];
        if (j?.keep_open && Date.now() - (j.ts || 0) < 30 * 60 * 1000) createPanel(tabId);
        else showLauncher();
      });
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", restoreEarly, { once: true });
  } else {
    restoreEarly();
  }

  if (IS_TOP_FRAME) {
    window.addEventListener("resize", () => {
      const launcher = document.getElementById(BUBBLE_ID);
      // Panel đang mở thì launcher display:none và rect trả về 0,0; không được
      // dùng tọa độ giả đó ghi đè vị trí người dùng đã kéo trước đây.
      // Resize do bật/tắt DevTools chỉ reflow theo tỷ lệ đã lưu, tuyệt đối không
      // ghi tọa độ pixel của viewport hẹp đè lên vị trí người dùng đã chọn.
      if (launcher && launcher.style.display !== "none") reflowLauncherPosition(launcher);
    });
  }

  // ── Message: icon extension (background) + header sidebar (iframe) ──
  let lastVneidModalDebugSignature = "";
  function collectVneidModalSignals() {
    const visible = (element) => {
      if (!element) return false;
      try {
        const style = getComputedStyle(element);
        return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0"
          && element.getClientRects().length > 0;
      } catch (_) {
        return false;
      }
    };
    const signals = {
      vneidLoginCodePrompt: !!(
        window.__TLND__ && typeof window.__TLND__.detectVneidLoginCodePrompt === "function"
        && window.__TLND__.detectVneidLoginCodePrompt(document, visible)
      ),
      vneidDataSharingPrompt: !!(
        window.__TLND__ && typeof window.__TLND__.detectVneidDataSharingPrompt === "function"
        && window.__TLND__.detectVneidDataSharingPrompt(document, visible)
      ),
      vneidPasscodePrompt: !!(
        window.__TLND__ && typeof window.__TLND__.detectVneidPasscodePrompt === "function"
        && window.__TLND__.detectVneidPasscodePrompt(document, visible)
      ),
    };
    const signature = [
      signals.vneidLoginCodePrompt ? "login-code" : "",
      signals.vneidDataSharingPrompt ? "data-sharing" : "",
      signals.vneidPasscodePrompt ? "passcode" : "",
    ].filter(Boolean).join("+");
    if (signature !== lastVneidModalDebugSignature) {
      console.info("[TLND-VNeID][content] modal-state", {
        state: signature || "closed",
        frame: IS_TOP_FRAME ? "top" : "child",
        host: location.hostname,
      });
      lastVneidModalDebugSignature = signature;
    }
    return signals;
  }

  function collectDeclarationPageSignals() {
    const foldSignalText = (value) => String(value || "")
      .replace(/Đ/g, "D").replace(/đ/g, "d")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/\s+/g, " ").trim().toLowerCase();
    const visible = (element) => {
      if (!element) return false;
      try {
        const style = getComputedStyle(element);
        return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0"
          && element.getClientRects().length > 0;
      } catch (_) {
        return false;
      }
    };
    const formKind = (window.__TLND__ && typeof window.__TLND__.detectFormKind === "function")
      ? window.__TLND__.detectFormKind() : "";
    if (!formKind) return { declarationTarget: false, declarationFormKind: "" };

    // Stepper có thể ở top-frame còn eForm nằm trong iframe. Chỉ frame chứa đồng thời
    // tiêu đề mẫu điện tử, nút Xem trước và form thật mới được quyền báo đang ở Kê khai.
    const hasInteractiveTemplateHeading = Array.from(document.querySelectorAll(
      "h1,h2,h3,h4,p,legend,strong,span,div"
    )).some((element) => {
      if (!visible(element)) return false;
      const raw = String(element.textContent || "").replace(/\s+/g, " ").trim();
      if (!raw || raw.length > 300) return false;
      const text = foldSignalText(raw);
      return text.startsWith("noi dung mau") && text.includes("dien tu tuong tac");
    });
    const hasPreviewControl = Array.from(document.querySelectorAll(
      'button,input[type="button"],input[type="submit"],a'
    )).some((element) => visible(element)
      && foldSignalText(element.value || element.textContent) === "xem truoc");

    return {
      declarationTarget: hasInteractiveTemplateHeading && hasPreviewControl,
      declarationFormKind: formKind,
    };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action === "togglePanel") { togglePanel(); sendResponse?.({ ok: true }); return; }
    if (msg?.action === "clearCitizenPortalSessionStorage" && IS_TOP_FRAME) {
      // Kết thúc hồ sơ mới được gọi action này. Xóa phiên web của cổng nhưng giữ trạng thái
      // mở/thu panel để reload xong Trợ lý không biến mất hoặc tự đổi trải nghiệm.
      let panelState = null;
      try { panelState = sessionStorage.getItem(SS_OPEN_KEY); } catch (_) {}
      try {
        sessionStorage.clear();
        if (panelState === "1" || panelState === "0") sessionStorage.setItem(SS_OPEN_KEY, panelState);
        sendResponse?.({ ok: true });
      } catch (error) {
        sendResponse?.({ ok: false, error: error?.message || String(error) });
      }
      return;
    }
    // Action "navigate" từ sidebar (BE ra lệnh chuyển trang) — chỉ top frame thi hành.
    if (msg?.action === "navigate" && msg.url && IS_TOP_FRAME) {
      sendResponse?.({ ok: true });
      // sessionStorage cùng origin: nếu đích cùng origin panel tự mở lại; khác origin → Bước 7 (journey).
      try { window.location.assign(msg.url); } catch (_) { /* URL hỏng thì thôi */ }
      return;
    }
    if (msg?.action === "getDossierUrl" && IS_TOP_FRAME) {
      // URL hồ sơ SẠCH: bỏ mã/step của hồ sơ đang làm, chỉ giữ khóa thủ tục + địa phương để
      // tab tách mở một hồ sơ MỚI thay vì nhân bản hồ sơ hiện tại.
      try {
        const u = new URL(location.href);
        const keep = new URLSearchParams();
        for (const key of ["maThuTuc", "tinhThanhId"]) {
          const value = u.searchParams.get(key);
          if (value) keep.set(key, value);
        }
        sendResponse({ ok: true,
          url: u.origin + u.pathname + (keep.toString() ? `?${keep.toString()}` : "") });
      } catch (e) {
        sendResponse({ error: "Không đọc được địa chỉ hồ sơ trên trang." });
      }
      return;
    }
    // SSO có thể render modal passcode/chia sẻ trong iframe. Mọi frame đều được quyền
    // kiểm tra, nhưng chỉ frame thật sự đang chứa modal mới phản hồi cho sidebar.
    if (msg?.action === "getVneidModalContext") {
      const modalSignals = collectVneidModalSignals();
      if (!Object.values(modalSignals).some(Boolean)) return;
      console.info("[TLND-VNeID][content] send-modal-context", {
        frame: IS_TOP_FRAME ? "top" : "child",
        ...modalSignals,
      });
      sendResponse({ ok: true, loginPage: true, ...modalSignals });
      return;
    }
    // Mọi frame được kiểm tra; frame chứa eForm thật mới phản hồi. Nhờ đó fallback kê khai
    // không phụ thuộc stepper top-frame và không nhận nhầm form Thông tin chủ hồ sơ.
    if (msg?.action === "getDeclarationContext") {
      const declaration = collectDeclarationPageSignals();
      if (!declaration.declarationTarget) return;
      sendResponse({ ok: true, url: location.href, ...declaration });
      return;
    }
    // Watcher (docs/07 §2.2): sidebar hỏi trạng thái trang — CHỈ ĐỌC DOM, không can thiệp.
    if (msg?.action === "getPageContext" && IS_TOP_FRAME) {
      const foldTxt = (s) => String(s || "")
        .replace(/Đ/g, "D").replace(/đ/g, "d")
        .normalize("NFD").replace(/[̀-ͯ]/g, "")
        .replace(/\s+/g, " ").trim().toLowerCase();
      // Chủ thể dữ liệu = tài khoản VNeID đang đăng nhập trên cổng (ghi vào biên bản consent).
      // Ưu tiên: (1) drawer cổng ngành tư pháp moj — có cả CCCD 12 số + tên; (2) chỉ tên
      // (#account_name Angular / .user-dropdown cổng React mới); không có → null, BE rơi về mã phiên.
      // Port từ auto-fill extractPortalPrincipal — null-safe, cổng lạ/DOM đổi không chặn luồng.
      function extractPortalPrincipal() {
        const CCCD_RE = /(?<!\d)\d{12}(?!\d)/; // đúng 12 chữ số (điện thoại 10 số không dính)
        let cccd = null;
        let name = null;
        try {
          const idLink = document.querySelector(
            'a[href*="thong-tin-dinh-danh"], a[href*="ho-so-ca-nhan"], a[href*="thong-tin-tai-khoan"]'
          );
          if (idLink) {
            // Neo vào link rồi leo lên ancestor GẦN NHẤT có <h3> (khối hồ sơ: tên + CCCD) — không leo tới body.
            let scope = idLink.parentElement;
            let hops = 0;
            while (scope && hops < 8 && !scope.querySelector("h3")) { scope = scope.parentElement; hops++; }
            if (scope) {
              const txt = String(scope.innerText || scope.textContent || "");
              const m = txt.match(CCCD_RE);
              if (m) cccd = m[0];
              const h3 = scope.querySelector("h3");
              if (h3) {
                const t = String(h3.innerText || h3.textContent || "").replace(/\s+/g, " ").trim();
                if (t && !/\d{6,}/.test(t)) name = t; // <h3> phải là tên, không phải dãy số
              }
            }
          }
          if (!name) {
            // Angular (#account_name) / cổng React quốc gia (.user-dropdown) CHỈ có tên.
            const el = document.querySelector("#account_name") || document.querySelector(".user-dropdown");
            if (el) {
              const t = String(el.innerText || el.textContent || "")
                .replace(/\s+/g, " ").replace(/^(xin chao|chao)[,!]?\s*/i, "").trim();
              if (t && t.length <= 60 && !/\d{6,}/.test(t)) name = t;
            }
          }
        } catch (e) { /* cổng lạ → null */ }
        return (cccd || name) ? { cccd: cccd || null, name: name || null, host: location.hostname } : null;
      }
      // Quét TOÀN trang (cap 100k phòng trang dị): khối "Chọn cơ quan thực hiện" của cổng
      // React nằm sâu (~16k ký tự innerText) — cắt ngắn sẽ bắt hụt tín hiệu.
      const body = foldTxt((document.body?.innerText || "").slice(0, 100000));
      const isPageVisible = (el) => {
        if (!el) return false;
        try {
          const style = getComputedStyle(el);
          return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0"
            && el.getClientRects().length > 0;
        } catch (_) {
          return false;
        }
      };
      // Chỉ tin marker chữ đang HIỂN THỊ. Angular thường giữ component đăng nhập/QR cũ
      // trong DOM sau khi đã vào kê khai; quét toàn body sẽ nhận nhầm và tự thu gọn panel.
      const hasVisibleText = (needle) => {
        const nodes = document.querySelectorAll("h1,h2,h3,h4,p,span,label,button,a,div");
        for (const el of nodes) {
          if (!isPageVisible(el)) continue;
          // Bỏ container lớn: marker phải thuộc chính dòng/khối UI đang hiện, không phải
          // wrapper chứa cả phần đăng nhập ẩn lẫn nội dung kê khai.
          const raw = String(el.textContent || "").replace(/\s+/g, " ").trim();
          if (raw.length > 300) continue;
          if (foldTxt(raw).includes(needle)) return true;
        }
        return false;
      };
      const accountEl = document.querySelector("#account_name") || document.querySelector(".user-dropdown");
      const loggedIn = isPageVisible(accountEl) || hasVisibleText("dang xuat");
      // Trang thủ tục đang hiện khối "Chọn cơ quan thực hiện" (khớp text fold dấu,
      // không dựa id/class dễ đổi).
      const agencyBlock = body.includes("chon co quan thuc hien");
      // Marker ĐÃ VÀO form kê khai thật: section "Kê khai thông tin". Liên thông có 2 trang
      // ĐỀU Angular + đều nhắc "chọn cơ quan thực hiện" (agencyBlock) — trang CHỌN CƠ QUAN
      // KHÔNG có marker này, trang KÊ KHAI thì có → dùng để phân biệt (chống kích hoạt sớm).
      const keKhaiForm = body.includes("ke khai thong tin");
      // Trang đăng nhập SSO/VNeID — host xác thực hoặc màn QR THỰC SỰ đang hiển thị.
      // Nếu #account_name đã hiện thì ưu tiên trạng thái đăng nhập, dù DOM còn sót chữ QR.
      let loginPage = !loggedIn && (/xacthuc|vneid|sso/.test(location.hostname)
        || (hasVisibleText("dang nhap") && hasVisibleText("quet ma qr")));
      // Ba modal nối tiếp trên SSO dùng chung URL/host. Tách tín hiệu để backend hướng dẫn
      // đúng việc đang hiện, không nhận nhầm chia sẻ dữ liệu thành nhập passcode.
      const {
        vneidLoginCodePrompt, vneidDataSharingPrompt, vneidPasscodePrompt,
      } = collectVneidModalSignals();
      // Modal xác thực là bằng chứng mạnh hơn nhãn tài khoản phía sau modal. Sau OTP, cổng
      // có thể đã hiện trạng thái đăng nhập nhưng vẫn bắt buộc công dân chia sẻ/passcode.
      if (vneidLoginCodePrompt || vneidDataSharingPrompt || vneidPasscodePrompt) loginPage = true;
      // Modal "Thông tin chung" của wizard hồ sơ — nút Xác nhận có data-e2e (hook test của cổng).
      const infoModalBtn = document.querySelector('button[data-e2e="confirm-button-information"]');
      const infoModal = !!(infoModalBtn && infoModalBtn.offsetParent !== null);
      // Wizard hồ sơ 4 bước (chủ hồ sơ → kê khai → thành phần → nhận kết quả): bước hiện
      // tại = bước ĐẦU TIÊN còn hiện SỐ thứ tự — bước đã xong thay số bằng icon ✓.
      // Khớp nhãn fold dấu, không dựa class React.
      let wizardStep = 0;
      {
        const labels = ["thong tin chu ho so", "ke khai thong tin", "thanh phan ho so", "thong tin nhan ket qua"];
        const leaves = Array.from(document.querySelectorAll("span,div")).filter((el) => el.children.length === 0);
        let found = 0;
        for (let i = 0; i < labels.length; i++) {
          const el = leaves.find((e) => foldTxt(e.textContent) === labels[i]);
          if (!el) continue;
          found += 1;
          const boxTxt = foldTxt(el.parentElement?.textContent || "");
          if (!wizardStep && boxTxt.startsWith(String(i + 1))) wizardStep = i + 1;
        }
        if (found < 2) wizardStep = 0; // không phải trang wizard
      }
      const rawFormKind = (window.__TLND__ && typeof window.__TLND__.detectFormKind === "function")
        ? window.__TLND__.detectFormKind() : "";
      const attachmentTarget = !!(
        window.__TLND__ && typeof window.__TLND__.hasAttachmentTarget === "function" &&
        window.__TLND__.hasAttachmentTarget()
      );
      const ownerContext = (wizardStep === 1 && window.__TLND__ &&
        typeof window.__TLND__.extractOwnerContext === "function")
        ? window.__TLND__.extractOwnerContext() : null;
      const businessHost = String(location.hostname || "").toLowerCase() === "hokinhdoanh.dkkd.gov.vn";
      const businessStage = businessHost && window.__TLND__
        && typeof window.__TLND__.detectBusinessCreateStage === "function"
        ? window.__TLND__.detectBusinessCreateStage().stage : "";
      const businessProcedureHint = businessHost && window.__TLND__
        && typeof window.__TLND__.detectBusinessProcedureHint === "function"
        ? window.__TLND__.detectBusinessProcedureHint() : "";
      sendResponse({
        ok: true,
        url: location.href,
        // Đã đăng nhập: tên tài khoản Angular/React đang hiện hoặc nút "Đăng xuất" đang hiện.
        loggedIn,
        // Chủ thể dữ liệu VNeID (CCCD/tên) — BE ghi vào biên bản consent; null nếu chưa nhận ra.
        principal: extractPortalPrincipal(),
        // Đã vào form kê khai. Khi trang có khối "chọn cơ quan" (agencyBlock) thì NULL formKind
        // TRỪ KHI là form THẬT (angular/legacy) VÀ đã có section "Kê khai thông tin" (keKhaiForm)
        // — vì liên thông có 2 trang đều Angular + đều nhắc "cơ quan thực hiện": trang CHỌN CƠ
        // QUAN (chưa keKhaiForm → null, không kích hoạt sớm) vs trang KÊ KHAI (có keKhaiForm → tin).
        // "standard" (ô tìm kiếm) luôn null khi có agencyBlock. loginPage/infoModal/wizard≠2 null mọi loại.
        formKind: (loginPage || infoModal || (wizardStep && wizardStep !== 2)
                   || (agencyBlock && (rawFormKind === "standard" || !keKhaiForm))) ? "" : rawFormKind,
        agencyBlock,
        loginPage,
        vneidLoginCodePrompt,
        vneidDataSharingPrompt,
        vneidPasscodePrompt,
        infoModal,
        wizardStep,
        // Thông tin định danh của đúng người đang đứng tên chủ hồ sơ. Backend dùng làm
        // context nghiệp vụ; extension không tự quyết người hay nguồn dữ liệu.
        ownerContext,
        // Attach-only (chứng thực bản sao) không có form bước 2: nhận diện trực tiếp bảng
        // Thành phần hồ sơ để BE chuyển sang nhận tệp, kể cả khi stepper render chưa ổn định.
        attachmentTarget,
        // HkdOnline reload toàn trang qua từng bước; backend chỉ cần stage đã xác thực từ
        // control/metadata cổng để quyết định bootstrap hay bắt đầu nhận giấy tờ.
        businessHost,
        businessStage,
        businessProcedureHint,
        // Chỉ tin đúng câu xác nhận nộp/gửi hồ sơ của cổng. Không ghép hai cụm chung
        // "thành công" + "mã hồ sơ" vì chúng có thể cùng xuất hiện ở màn tra cứu khác.
        submitted: body.includes("nop ho so thanh cong") || body.includes("gui ho so thanh cong"),
      });
      return;
    }
  });
  // Lệnh từ header sidebar (iframe) → điều khiển khung ở content.
  window.addEventListener("message", (e) => {
    const t = e.data && e.data.__tlnd;
    if (t === "minimizePanel") minimizePanel();
    else if (t === "restorePanel") restorePanel();
    else if (t === "closePanel") closePanel();
  });

})();
