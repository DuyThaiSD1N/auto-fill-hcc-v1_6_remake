// content.js — KHUNG SIDEBAR "Trợ lý nhân dân" (push-layout, KHÔNG che nội dung trang).
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

  // ── Chế độ khung: đẩy trang (mặc định) hay khung bên trình duyệt ──
  // PHẢI hỏi background: chrome.sidePanel không tồn tại trong ngữ cảnh content
  // script, nên tự dò ở đây luôn ra "không hỗ trợ". Mặc định "push" để mọi đường
  // hỏng (SW đang ngủ, message rớt) đều rơi về chế độ chạy được ở mọi trình duyệt.
  let _cheDoKhung = "push";
  // Tab này là một HỒ SƠ TÁCH (chứng thực nhiều tài liệu = nhiều hồ sơ = nhiều tab) hay không.
  // Có thẻ → khung dựng ở chế độ "hồ sơ phụ" (companion.html) thay vì khung hội thoại đầy đủ:
  // một phiên chỉ được MỘT khung lái, hai khung cùng phiên là đếm nộp hai lần và báo trạng thái
  // trang của sai hồ sơ về backend. Xem SPLIT_TAB_INFO_KEY trong background.js.
  const SPLIT_TAB_INFO_KEY = "tlnd_split_tab_info";
  let _theHoSoPhu = null;
  // Khung bên của TAB NÀY có đang mở không. Nguồn thật là port sidebar giữ với background (xem
  // khungBenMoTheoTab); ở đây chỉ là bản sao để quyết định hiện/ẩn nút tròn.
  let _khungBenMo = false;
  function hoiCheDoKhung() {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ action: "getPanelMode" }, (res) => {
          if (chrome.runtime.lastError) return resolve("push");
          _khungBenMo = !!res?.khungBenMo;
          resolve(res?.mode === "sidepanel" ? "sidepanel" : "push");
        });
      } catch (_) { resolve("push"); }
    });
  }
  const laKhungBen = () => _cheDoKhung === "sidepanel";

  function layTabId() {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
          resolve(chrome.runtime.lastError ? null : (res?.tabId ?? null));
        });
      } catch (_) { resolve(null); }
    });
  }

  function docTheHoSoPhu() {
    return new Promise((resolve) => {
      try {
        // Đọc bản đồ TRƯỚC khi hỏi số tab: hỏi số tab phải đánh thức service worker, mà gần như
        // mọi trang đều không dính tới hồ sơ tách. Bản đồ rỗng → về ngay, luồng thường không
        // phải chờ thêm một vòng message chỉ để biết mình không phải tab tách.
        chrome.storage.local.get([SPLIT_TAB_INFO_KEY], (st) => {
          const map = chrome.runtime.lastError ? null : st?.[SPLIT_TAB_INFO_KEY];
          if (!map || !Object.keys(map).length) return resolve(null);
          void (async () => {
            const tabId = await layTabId();
            const the = tabId == null ? null : map[tabId];
            // Thẻ quá cũ là rác của lượt trước mà Chrome dùng lại số tab — bỏ, đừng dựng nhầm
            // khung hồ sơ phụ cho một tab công dân tự mở.
            if (!the || Date.now() - (the.ts || 0) > 12 * 60 * 60 * 1000) return resolve(null);
            resolve({ ...the, tabId });
          })();
        });
      } catch (_) { resolve(null); }
    });
  }

  // Hoạt động thật trên trang cổng cũng giữ phiên sống. Nếu chỉ nghe event trong iframe sidebar,
  // người dân đang rà/điền form trên trang sẽ bị timeout oan sau 20 phút.
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
  // chạm cùng journey để tiến trình tự động không bị quy tắc idle 20 phút xóa nhầm conversation.
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
    // Tab hồ sơ tách nạp trang hồ sơ phụ: nó chỉ ĐỌC lại hội thoại của hồ sơ chính, không cầm
    // phiên nên không thể gửi nhầm gì lên backend.
    const trangKhung = _theHoSoPhu ? "companion.html" : "sidebar.html";
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
        src="${chrome.runtime.getURL(`${trangKhung}?${sidebarQuery.toString()}`)}"></iframe>`;

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
    dongPreview(); // thu khung Trợ lý thì không để khung xem trước lơ lửng trên trang
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

  // Gỡ HẲN khung đẩy trang (khác minimizePanel: hàm kia cố tình giữ iframe sống để
  // không mất hội thoại). Chỉ dùng khi chuyển sang khung bên — để iframe sống nghĩa
  // là hai bản sidebar cùng chạy trên một tab, cùng nói chuyện với một conversation.
  function huyPanel() {
    dongPreview();
    document.getElementById(PANEL_ID)?.remove();
    restoreSidebarPushLayout();
    removeTranslateOverrideStyle();
    hideLauncher();
    persistOpen(false);
  }

  function togglePanel() {
    if (!IS_TOP_FRAME || laKhungBen()) return;
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
      if (laKhungBen()) moKhungBen();
      else togglePanel();
    });
  }

  // ── Nút tròn ở chế độ KHUNG BÊN ──
  // Hiện khi khung bên của tab này đang đóng, ẩn khi đang mở — cùng vai với chế độ đẩy trang
  // (nút hiện khi khung Trợ lý thu gọn).
  function capNhatLauncherKhungBen(mo) {
    _khungBenMo = !!mo;
    if (!IS_TOP_FRAME || !laKhungBen()) return;
    if (_khungBenMo) hideLauncher();
    else showLauncher();
  }

  function moKhungBen() {
    try {
      chrome.runtime.sendMessage({ action: "openSidePanel" }, (res) => {
        if (chrome.runtime.lastError || !res?.ok) chiDuongThanhCongCu();
      });
    } catch (_) { chiDuongThanhCongCu(); }
  }

  // Trình duyệt không cho mở khung bên từ nút trên trang (bản cũ không chuyển user gesture qua
  // message). Bấm mà im lặng là tệ nhất — nói rõ phải bấm ở đâu.
  function chiDuongThanhCongCu() {
    const b = document.getElementById(BUBBLE_ID);
    if (!b) return;
    document.getElementById(BUBBLE_ID + "-goi-y")?.remove();
    const r = b.getBoundingClientRect();
    const tip = document.createElement("div");
    tip.id = BUBBLE_ID + "-goi-y";
    tip.setAttribute("role", "status");
    tip.textContent = "Bấm biểu tượng Trợ lý trên thanh công cụ của trình duyệt để mở khung bên.";
    Object.assign(tip.style, {
      position: "fixed", zIndex: "2147483646", maxWidth: "260px",
      top: `${Math.round(r.bottom + 8)}px`, right: `${Math.max(8, Math.round(window.innerWidth - r.right))}px`,
      padding: "8px 11px", borderRadius: "10px", background: "#173a5e", color: "#fff",
      font: "600 12.5px/1.4 system-ui, sans-serif", boxShadow: "0 6px 20px rgba(15,40,80,.3)",
    });
    document.documentElement.appendChild(tip);
    setTimeout(() => tip.remove(), 5000);
  }

  // ── Xem trước giấy tờ TRÊN TRANG GỐC ──
  // Cùng cách với autofill: khung Trợ lý 400px không đọc nổi một tờ A4, và nhúng iframe
  // chrome-extension:// thì không phụ thuộc CSP của từng cổng. Khác autofill ở hai điểm:
  //  - mở bằng NHẤN (doc-row / dòng tệp) chứ không rê chuột → đóng bằng ✕ / bấm ra ngoài / Esc;
  //  - lệnh tới qua chrome.tabs.sendMessage, không qua postMessage của iframe cha: ở chế độ khung
  //    bên, sidebar KHÔNG phải iframe của trang này. Một đường chung cho cả hai chế độ.
  const PREVIEW_ID = "tro-ly-nguoi-dan-preview";
  const PREVIEW_LE = 10;
  const PREVIEW_W_MAX = 760;
  const PREVIEW_H_MAX = 960;
  const PREVIEW_W_MIN = 300; // hẹp hơn thì phủ cả màn (đè lên khung Trợ lý) còn hơn một khung vô dụng
  let previewBox = null;
  let previewFrame = null;
  let previewSanSang = false;
  let previewCho = []; // lệnh gửi trước khi preview.js báo sẵn sàng
  // GHIM = mở bằng nhấn (doc-row / dòng tệp): chỉ đóng bằng ✕ / bấm ra ngoài / Esc. Không ghim = xem
  // tạm lúc rê chuột trên dòng tệp: rời chuột thì tự ẩn, trừ khi con trỏ đang ở trên khung.
  let previewGhim = false;
  let previewChoRoiDi = false; // đang xem tạm, con trỏ đã rời dòng tệp — chờ bằng chứng nó đi chỗ khác
  let previewTinTuLuc = 0;      // mốc hết ân hạn
  // Ân hạn sau khi rời dòng tệp: chuyển động trong khoảng này chưa tính là "đã đi chỗ khác", vì con trỏ
  // còn đang vượt khe từ Trợ lý sang khung.
  const PREVIEW_AN_HAN_MS = 500;

  function dungPreview() {
    if (previewBox) return previewBox;
    const box = document.createElement("div");
    box.id = PREVIEW_ID;
    Object.assign(box.style, {
      position: "fixed", display: "none", zIndex: "2147483645", // dưới khung Trợ lý và nút tròn
      background: "#fff", border: "1px solid rgba(23,58,94,.2)", borderRadius: "10px",
      overflow: "hidden", boxShadow: "0 12px 40px rgba(15,40,80,.28)",
    });
    const f = document.createElement("iframe");
    f.src = chrome.runtime.getURL("preview.html");
    Object.assign(f.style, { border: "0", width: "100%", height: "100%", display: "block", background: "#f4f6f9" });
    box.appendChild(f);
    document.documentElement.appendChild(box);
    previewBox = box;
    previewFrame = f;
    previewSanSang = false;
    previewCho = [];
    return box;
  }

  function datChoPreview(box) {
    const vw = document.documentElement.clientWidth || window.innerWidth;
    const vh = window.innerHeight;
    // Đẩy trang: khung Trợ lý phủ SIDEBAR_WIDTH bên phải → chừa ra. Khung bên: trình duyệt đã tự
    // thu hẹp tab, cả viewport là của trang.
    const panel = document.getElementById(PANEL_ID);
    const panelMo = !!panel && panel.style.display !== "none" && panel.classList.contains("open");
    const chiemPhai = panelMo ? SIDEBAR_WIDTH : 0;
    let trong = vw - chiemPhai - 2 * PREVIEW_LE;
    const deLen = trong < PREVIEW_W_MIN;
    if (deLen) trong = vw - 2 * PREVIEW_LE;
    const w = Math.max(1, Math.min(PREVIEW_W_MAX, trong));
    const h = Math.max(1, Math.min(PREVIEW_H_MAX, vh - 2 * PREVIEW_LE));
    // Áp sát cạnh khung Trợ lý: mắt đi từ dòng vừa bấm sang nội dung ngắn nhất.
    const phai = deLen ? PREVIEW_LE : chiemPhai + PREVIEW_LE;
    Object.assign(box.style, {
      width: `${w}px`, height: `${h}px`,
      left: `${Math.max(PREVIEW_LE, vw - phai - w)}px`,
      top: `${Math.max(PREVIEW_LE, Math.round((vh - h) / 2))}px`,
      zIndex: deLen ? "2147483647" : "2147483645",
    });
  }

  function guiPreview(msg) {
    if (!previewSanSang) { previewCho.push(msg); return; }
    previewFrame?.contentWindow?.postMessage(msg, "*");
  }

  // Rời dòng tệp (chưa ghim) thì CHƯA ẩn — con trỏ có thể đang đi sang khung để cuộn xem trang 2, 3.
  // Chỉ ẩn khi có BẰNG CHỨNG con trỏ đã đi chỗ khác: trang gốc hoặc sidebar nhận lại mousemove.
  // Không dựa vào mouseenter của khung được: khung chứa iframe KHÁC TIẾN TRÌNH (preview.html lồng trình
  // xem PDF) — đo 2026-09-13, rê vào đó không bắn mouseenter nào lên khung ở trang cha. Cùng cách sửa
  // với autofill (content.js — choChuotRoiDi).
  function choChuotRoiDi() {
    if (previewGhim || !previewBox || previewBox.style.display === "none") return;
    previewChoRoiDi = true;
    previewTinTuLuc = Date.now() + PREVIEW_AN_HAN_MS;
  }
  function chuotDaRoiDi() {
    if (!previewChoRoiDi || previewGhim || Date.now() < previewTinTuLuc) return;
    previewChoRoiDi = false;
    dongPreview();
  }

  function moPreview(msg) {
    // Sidebar bản cũ không gửi `ghim` → coi là nhấn (ghim), đúng hành vi trước khi có xem tạm.
    const ghim = msg.ghim !== false;
    const dangHien = !!previewBox && previewBox.style.display !== "none";
    // Đang GHIM mà tới lệnh xem tạm (rê chuột) → bỏ qua: ghim là để đọc lâu, không giật theo con trỏ.
    if (dangHien && previewGhim && !ghim) return;
    const box = dungPreview();
    previewChoRoiDi = false;
    previewGhim = ghim;
    datChoPreview(box);
    box.style.display = "block";
    guiPreview({
      type: "tlnd-preview-nhom",
      tieuDe: msg.tieuDe, bieuTuong: msg.bieuTuong, tep: msg.tep, chiSo: msg.chiSo, ghim,
    });
  }

  // baoSidebar=false khi chính sidebar ra lệnh đóng — nó đã biết rồi.
  function dongPreview({ baoSidebar = true } = {}) {
    previewChoRoiDi = false;
    previewGhim = false;
    if (!previewBox || previewBox.style.display === "none") return;
    previewBox.style.display = "none";
    if (!baoSidebar) return;
    try {
      chrome.runtime.sendMessage({ action: "tlndPreviewDaDong" }, () => void chrome.runtime.lastError);
    } catch (_) { /* context extension đã mất (vừa cập nhật) — không còn ai để báo */ }
  }

  if (IS_TOP_FRAME) {
    window.addEventListener("message", (e) => {
      if (!previewFrame || e.source !== previewFrame.contentWindow) return;
      const d = e.data;
      if (d?.type === "tlnd-preview-san-sang") {
        previewSanSang = true;
        const cho = previewCho;
        previewCho = [];
        cho.forEach(guiPreview);
      } else if (d?.type === "tlnd-preview-can") {
        // Nội dung nằm trên BE, chỉ sidebar có token → xin sidebar. Nó trả về bằng tlndPreviewData.
        try {
          chrome.runtime.sendMessage({ action: "tlndPreviewCan", fid: String(d.fid || "") },
            () => void chrome.runtime.lastError);
        } catch (_) { /* context mất */ }
      } else if (d?.type === "tlnd-preview-dong") {
        dongPreview();
      }
    });
    // Bấm ra ngoài khung xem trước trên TRANG, hoặc Esc → đóng. Bấm vào khung Trợ lý (đẩy trang)
    // thì sidebar tự quyết: bấm trong iframe của nó vốn không tới được document này.
    document.addEventListener("pointerdown", (e) => {
      if (!previewBox || previewBox.style.display === "none" || previewBox.contains(e.target)) return;
      const panel = document.getElementById(PANEL_ID);
      if (panel && panel.contains(e.target)) return;
      dongPreview();
    }, true);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && previewBox && previewBox.style.display !== "none") dongPreview();
    }, true);
    // Bằng chứng "con trỏ đã đi chỗ khác" cho khung đang xem tạm (xem choChuotRoiDi). Trên viền khung
    // hay khung Trợ lý thì chưa tính — phần bên trong Trợ lý do sidebar tự báo.
    document.addEventListener("mousemove", (e) => {
      if (!previewChoRoiDi || !previewBox || previewBox.contains(e.target)) return;
      const panel = document.getElementById(PANEL_ID);
      if (panel && panel.contains(e.target)) return;
      chuotDaRoiDi();
    }, { capture: true, passive: true });
    window.addEventListener("resize", () => {
      if (previewBox && previewBox.style.display !== "none") datChoPreview(previewBox);
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
      b.title = "Mở Trợ lý nhân dân";
      b.setAttribute("aria-label", "Mở Trợ lý nhân dân");
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
  async function restoreEarly() {
    if (!IS_TOP_FRAME) return;
    clearLegacyDismissedState();
    _cheDoKhung = await hoiCheDoKhung();
    if (laKhungBen()) {
      // Trình duyệt sở hữu khung — trang không dựng iframe, không đẩy layout. Nút tròn thì GIỮ
      // (yêu cầu BA 2026-09-13): hiện khi khung bên đang đóng, bấm vào là mở khung bên.
      huyPanel();
      capNhatLauncherKhungBen(_khungBenMo);
      // Khung bên SỐNG XUYÊN điều hướng, nên mốc "về trang chủ DVC = lượt công dân
      // mới" không còn tự kích hoạt lúc dựng lại iframe. Báo bằng message thay thế.
      if (IS_DVC_HOME) {
        chrome.runtime.sendMessage({ action: "dvcHomeReached" }, () => void chrome.runtime.lastError);
      }
      return;
    }
    // Tab hồ sơ tách: dựng khung "hồ sơ phụ" ngay, trước mọi nhánh khác. Tab này do máy mở nên
    // không có dấu phiên — để nó rơi xuống showInitial() là chỉ còn bong bóng, bấm vào ra màn
    // bắt đầu như chưa làm gì (đúng cảnh công dân đang gặp).
    _theHoSoPhu = await docTheHoSoPhu();
    if (_theHoSoPhu) {
      // Bấm "Nộp hồ sơ" làm cổng nạp lại trang. Công dân đã thu gọn khung thì đừng bật lại —
      // họ thu gọn chính vì đang muốn nhìn trang.
      let daThuGon = false;
      try { daThuGon = sessionStorage.getItem(SS_OPEN_KEY) === "0"; } catch (_) {}
      if (daThuGon) showLauncher(); else ensurePanelOpen();
      return;
    }
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
    document.addEventListener("DOMContentLoaded", () => void restoreEarly(), { once: true });
  } else {
    void restoreEarly();
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

  // ===== Mốc "công dân bấm Gửi hồ sơ" (docs: vòng đời hồ sơ) =====
  // Chỉ CHẤM MỐC thời điểm nộp — không can thiệp cú bấm. Đây là sự thật về TRANG nên nghe
  // độc lập với trạng thái hội thoại; gác theo state là mất dấu ở mọi nhánh đi chệch.
  // Bộ luật nhận diện do BE gửi xuống (registry.PORTAL_SUBMIT) → thêm cổng khỏi phát hành lại.
  let submitRules = null;
  let lastSubmitClickAt = 0;
  // Tự nạp luật từ storage thay vì chỉ chờ sidebar gửi: sidebar chỉ gửi luật tới ĐÚNG tab của
  // nó, còn chứng thực tách hồ sơ mở thêm tab mới — tab đó không có luật nên cú bấm "Nộp" ở
  // đó không bao giờ được nhận ra, mất hẳn hồ sơ tách. Sidebar đã lưu sẵn luật ở key này.
  const SUBMIT_RULES_KEY = "tlnd_submit_rules";
  try {
    chrome.storage.local.get([SUBMIT_RULES_KEY], (res) => {
      void chrome.runtime.lastError;
      const rules = res?.[SUBMIT_RULES_KEY];
      if (!submitRules && rules && typeof rules === "object") submitRules = rules;
    });
    // Luật về sau content script đã chạy (hồ sơ đầu tiên) → nghe thay đổi để khỏi lỡ.
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local" || !changes[SUBMIT_RULES_KEY]) return;
      const rules = changes[SUBMIT_RULES_KEY].newValue;
      submitRules = rules && typeof rules === "object" ? rules : null;
    });
  } catch (_) { /* context mất sau khi reload extension — chờ setSubmitRules như cũ */ }
  // input[type=submit]: cổng HkdOnline (ASP.NET) dùng input chứ không phải button/a.
  const SUBMIT_CLICKABLE = 'button, a, input[type="submit"], input[type="button"]';

  const foldLabel = (s) => String(s || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();

  function matchSubmitClick(el) {
    if (!submitRules) return null;
    const rule = submitRules[location.hostname];
    if (!rule) return null;
    // Cổng chặn BẮT BUỘC: chỉ trang nộp của MỘT hồ sơ. Trang chủ/hồ sơ của tôi/tra cứu đều
    // có thể có nút chữ giống nhau — không khớp URL thì tuyệt đối không tính.
    let ref = "";
    if (rule.urlPattern) {
      // pathname + hash: cổng SPA (liên thông khai sinh) để đường dẫn trong hash, bỏ hash là
      // không phân biệt nổi trang nào. Query cố ý bỏ — nó đổi liên tục theo phiên.
      let m = null;
      try { m = new RegExp(rule.urlPattern).exec(location.pathname + location.hash); }
      catch (_) { return null; }
      if (!m) return null;
      ref = m[1] || "";
    }
    const id = String(el.id || "");
    if (Array.isArray(rule.buttonIds) && rule.buttonIds.includes(id)) return { ref };
    // Nhãn là lưới đỡ khi cổng đổi id (id sinh từ nhãn nên hai thứ đổi cùng lúc).
    // <input> không có textContent — nhãn nằm ở value.
    const label = foldLabel(el.tagName === "INPUT" ? el.value : el.textContent);
    if (Array.isArray(rule.buttonText) && rule.buttonText.some((t) => label === t)) return { ref };
    // Nền tảng Form.io: nút cuối không có id và nhãn đổi theo thủ tục ("Nộp hồ sơ" vs
    // "Thanh toán") → chỉ còn thuộc tính là mỏ neo ổn định.
    if (rule.buttonSelector) {
      try { if (el.matches(rule.buttonSelector)) return { ref }; } catch (_) {}
    }
    return null;
  }

  // LƯỚI ĐỠ cho cú bấm: dò chữ trên MÀN KẾT QUẢ theo `successText` của luật cổng (BE khai).
  // Dành cho cổng mà màn kết quả không có câu "nộp/gửi hồ sơ thành công" — liên thông khai
  // sinh chỉ hiện "Vui lòng ghi nhớ… Số hồ sơ… Ngày hẹn trả dự kiến". Vẫn khóa theo urlPattern
  // như cú bấm: cụm chữ có khớp mà sai trang thì tuyệt đối không tính.
  // `body` đã bỏ dấu + gộp khoảng trắng (foldTxt ở page_status) nên so thẳng với cụm của BE.
  function matchSuccessText(body) {
    const rule = submitRules?.[location.hostname];
    const groups = rule?.successText;
    if (!Array.isArray(groups) || !groups.length || !body) return false;
    if (rule.urlPattern) {
      let ok = false;
      try { ok = new RegExp(rule.urlPattern).test(location.pathname + location.hash); }
      catch (_) { return false; }
      if (!ok) return false;
    }
    return groups.some((group) => Array.isArray(group) && group.length
      && group.every((phrase) => typeof phrase === "string" && phrase && body.includes(phrase)));
  }

  // Capture-phase: cổng có thể stopPropagation ở handler riêng của nút.
  document.addEventListener("click", (e) => {
    if (!IS_TOP_FRAME || !submitRules) return;
    const el = e.target?.closest?.(SUBMIT_CLICKABLE);
    if (!el) return;
    const hit = matchSubmitClick(el);
    if (!hit) return;
    // Bấm dồn (double-click, cổng chưa phản hồi) chỉ tính một lần trong 3 giây.
    if (Date.now() - lastSubmitClickAt < 3000) return;
    lastSubmitClickAt = Date.now();
    try {
      chrome.runtime.sendMessage({
        __tlnd: "submitClicked", host: location.hostname, ref: hit.ref,
      }, () => void chrome.runtime.lastError);
    } catch (_) {}
  }, true);

  // Mốc thao tác gần nhất trên trang — dùng cho câu "tab này im lặng bao lâu rồi".
  window.__TLND_HOAT_DONG_CUOI__ = Date.now();
  if (IS_TOP_FRAME) {
    for (const ev of ["mousemove", "mousedown", "keydown", "wheel", "touchstart", "click", "scroll"]) {
      document.addEventListener(ev, () => { window.__TLND_HOAT_DONG_CUOI__ = Date.now(); },
        { passive: true, capture: true });
    }
  }

  // Báo hoạt động + focus của TRANG GỐC sang sidebar (lib/trangThai.js). Iframe mù với thao tác ngoài
  // khung: cán bộ gõ vào form cổng thì document.hasFocus() của iframe trả false và panel tưởng cán bộ
  // đã bỏ đi. Tên message autofill-hcc-* là của lib dùng chung — giữ nguyên để hai bản không lệch.
  // Khung bên không có iframe trên trang → không gửi được, lib tự dùng focus của chính khung bên.
  if (IS_TOP_FRAME) {
    let lucBaoSidebarCuoi = 0;
    const guiSidebar = (tin) => {
      document.getElementById(PANEL_ID)?.shadowRoot?.getElementById(IFRAME_ID)?.contentWindow?.postMessage(tin, "*");
    };
    const baoHoatDongChoSidebar = () => {
      const gio = Date.now();
      if (gio - lucBaoSidebarCuoi < 2000) return; // gom bớt: mousemove bắn liên tục
      lucBaoSidebarCuoi = gio;
      guiSidebar({ type: "autofill-hcc-hoat-dong" });
    };
    const baoTrangThaiChoSidebar = () => guiSidebar({
      type: "autofill-hcc-trang-thai-trang",
      focus: document.hasFocus(),
      an: document.visibilityState === "hidden",
    });
    for (const ev of ["mousemove", "mousedown", "keydown", "wheel", "touchstart", "click", "scroll"]) {
      document.addEventListener(ev, baoHoatDongChoSidebar, { passive: true, capture: true });
    }
    window.addEventListener("focus", baoTrangThaiChoSidebar);
    window.addEventListener("blur", baoTrangThaiChoSidebar);
    document.addEventListener("visibilitychange", baoTrangThaiChoSidebar);
    setInterval(baoTrangThaiChoSidebar, 3000);
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action === "setSubmitRules") {
      submitRules = msg.rules && typeof msg.rules === "object" ? msg.rules : null;
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "togglePanel") { togglePanel(); sendResponse?.({ ok: true }); return; }
    // Xem trước + nút tròn khung bên: chỉ frame chính có khung trên trang. Frame con im lặng,
    // KHÔNG trả lời — tabs.sendMessage tới mọi frame, frame con trả trước là nuốt câu trả lời thật.
    if (msg?.action === "tlndPreviewOpen") {
      if (!IS_TOP_FRAME) return;
      moPreview(msg);
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "tlndPreviewData") {
      if (!IS_TOP_FRAME) return;
      if (previewBox) {
        guiPreview({ type: "tlnd-preview-du-lieu", fid: msg.fid, mime: msg.mime, dataUrl: msg.dataUrl, loi: msg.loi });
      }
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "tlndPreviewHide") {
      if (!IS_TOP_FRAME) return;
      choChuotRoiDi(); // rời dòng tệp: CHƯA ẩn, chờ bằng chứng con trỏ đi chỗ khác
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "tlndPreviewChuotOSidebar") {
      if (!IS_TOP_FRAME) return;
      chuotDaRoiDi(); // con trỏ đang ở chỗ khác trong Trợ lý
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "tlndPreviewClose") {
      if (!IS_TOP_FRAME) return;
      dongPreview({ baoSidebar: false });
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "khungBenTrangThai") {
      if (!IS_TOP_FRAME) return;
      capNhatLauncherKhungBen(!!msg.mo);
      sendResponse?.({ ok: true });
      return;
    }
    if (msg?.action === "panelModeChanged") {
      // Tới từ HAI nguồn: background phát cho MỌI tab khi cài đặt đổi, và sidebar
      // gửi riêng cho tab của nó kèm moKhung. Hai đường có thể tới theo thứ tự bất
      // kỳ nên xử lý phải bất biến theo số lần gọi.
      const moi = msg.mode === "sidepanel" ? "sidepanel" : "push";
      const doiChe = moi !== _cheDoKhung;
      _cheDoKhung = moi;
      if (laKhungBen()) {
        if (doiChe) huyPanel();
        capNhatLauncherKhungBen(_khungBenMo);
      } else if (msg.moKhung) {
        ensurePanelOpen();           // tab người dùng vừa bấm: mở thẳng, không bắt mở tay
      } else if (doiChe) {
        showInitial();               // tab khác: trả về đúng trạng thái của chế độ đẩy trang
      }
      sendResponse?.({ ok: true });
      return;
    }
    // ---- tự cập nhật: hai câu hỏi của background ------------------------
    // Tab này có đang được dùng không. Chỉ frame chính trả lời.
    if (msg?.action === "hccTabDangLamViec") {
      if (!IS_TOP_FRAME) return;
      sendResponse?.({
        coPanel: !!document.getElementById(PANEL_ID) || !!document.getElementById(BUBBLE_ID),
        focus: document.hasFocus(),
        an: document.visibilityState === "hidden",
        imLangMs: Date.now() - (window.__TLND_HOAT_DONG_CUOI__ || 0),
      });
      return;
    }
    // Gỡ panel NGAY TRƯỚC khi extension nạp lại. Nạp lại KHÔNG làm panel biến
    // mất — nó ở nguyên đó nhưng mọi chrome.* bên trong đã chết. Gỡ đi thì hỏng
    // trở nên nhìn thấy được, và cờ mở panel trong storage được GIỮ nên lần điều
    // hướng kế tiếp panel tự mọc lại.
    if (msg?.action === "hccGoPanelTruocKhiNapLai") {
      if (IS_TOP_FRAME) {
        try {
          document.getElementById(PANEL_ID)?.remove();
          document.getElementById(BUBBLE_ID)?.remove();
        } catch (e) { /* ignore */ }
      }
      sendResponse?.({ ok: true });
      return;
    }
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
      // Các cổng bộ ngành nền iGate (Angular Material, route padsvc/apply-online + wizard
      // 4 bước giống nhau): NN&MT + GD&ĐT + Xây dựng. Trang "chọn nơi và loại" (nếu cổng có)
      // nhận theo form#ngSelectAgencyForm1 (id hardcode trong template Angular, ổn định).
      // Cổng bộ nền iGate: hộp thoại chọn cơ quan form#ngSelectAgencyForm(1) + wizard
      // mat-stepper. Bộ Nội vụ dùng CÙNG component (UBND tỉnh → Sở/Ban ngành → Sở Nội vụ).
      const maeHost = ["dichvucongnnmt.mae.gov.vn", "dvc.moet.gov.vn", "dvc.moc.gov.vn",
        "dichvucongbnv.moha.gov.vn"].includes(location.hostname);
      // ngSelectAgencyForm1 = trang "chọn nơi và loại" (MAE/GD&ĐT); ngSelectAgencyForm = HỘP
      // THOẠI "Chọn trường hợp giải quyết" của cổng Bộ Xây dựng. Cả hai đều do portal-mae.js lo.
      const maeAgencyBlock = maeHost && !!document.querySelector(
        "form#ngSelectAgencyForm1, form#ngSelectAgencyForm");
      // Trang thủ tục đang hiện khối "Chọn cơ quan thực hiện" (khớp text fold dấu,
      // không dựa id/class dễ đổi). Trên host MAE tắt hẳn: engine chọn cơ quan React
      // không chạy được ở đó, tín hiệu riêng là maeAgencyBlock.
      const agencyBlock = !maeHost && body.includes("chon co quan thuc hien");
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
      // Wizard MAE (mat-horizontal-stepper, nhãn KHÁC cổng tư pháp): 1 Thông tin hồ sơ →
      // 2 Thành phần hồ sơ → 3 Thông tin phí → 4 Nộp hồ sơ. Cả 4 step CÙNG tồn tại trong
      // DOM (chỉ đổi visibility) → tin header aria-selected, không quét nội dung panel.
      if (maeHost && !maeAgencyBlock && !wizardStep) {
        const maeLabels = ["thong tin ho so", "thanh phan ho so", "thong tin phi", "nop ho so"];
        const headers = Array.from(document.querySelectorAll("mat-step-header"));
        const matched = headers.filter((h) => maeLabels.some((l) => foldTxt(h.textContent).includes(l)));
        if (matched.length >= 2) {
          const selected = matched.find((h) => h.getAttribute("aria-selected") === "true");
          const idx = maeLabels.findIndex((l) => foldTxt(selected?.textContent || "").includes(l));
          if (idx >= 0) wizardStep = idx + 1;
        }
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
      // Đếm ô bắt buộc còn trống ở bước chủ hồ sơ — backend dùng để quyết định có xin giấy
      // tờ ngay tại bước này không (đủ hết thì khỏi bắt công dân quét lại).
      const ownerForm = (wizardStep === 1 && window.__TLND__ &&
        typeof window.__TLND__.ownerFormRequiredState === "function")
        ? window.__TLND__.ownerFormRequiredState() : null;
      const businessHost = String(location.hostname || "").toLowerCase() === "hokinhdoanh.dkkd.gov.vn";
      // Stage GỘP (thành lập mới + thay đổi): search-business/select-change chỉ luồng thay
      // đổi mới nhận ra — BE cần chúng để dừng nhận giấy tờ đúng màn tra cứu hộ KD.
      const businessStage = businessHost && window.__TLND__
        && typeof window.__TLND__.detectBusinessAnyStage === "function"
        ? window.__TLND__.detectBusinessAnyStage().stage
        : (businessHost && window.__TLND__
           && typeof window.__TLND__.detectBusinessCreateStage === "function"
           ? window.__TLND__.detectBusinessCreateStage().stage : "");
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
        // Trang chọn cơ quan MAE có 3 input radio mang name → detectFormKind dương tính giả
        // "standard"; maeAgencyBlock null formKind để BE không tưởng đã vào kê khai.
        formKind: (loginPage || infoModal || maeAgencyBlock || (wizardStep && wizardStep !== 2)
                   || (agencyBlock && (rawFormKind === "standard" || !keKhaiForm))) ? "" : rawFormKind,
        agencyBlock,
        maeAgencyBlock,
        loginPage,
        vneidLoginCodePrompt,
        vneidDataSharingPrompt,
        vneidPasscodePrompt,
        infoModal,
        wizardStep,
        // Thông tin định danh của đúng người đang đứng tên chủ hồ sơ. Backend dùng làm
        // context nghiệp vụ; extension không tự quyết người hay nguồn dữ liệu.
        ownerContext,
        ownerForm,
        // Attach-only (chứng thực bản sao) không có form bước 2: nhận diện trực tiếp bảng
        // Thành phần hồ sơ để BE chuyển sang nhận tệp, kể cả khi stepper render chưa ổn định.
        attachmentTarget,
        // Bước Thông tin chủ hồ sơ nhánh ỦY QUYỀN có bảng đính kèm riêng cho văn bản ủy
        // quyền. Cờ này để backend biết trang đang ở nhánh ủy quyền (cần quét giấy tờ ngay
        // vì 4 ô ủy quyền luôn trống), và để KHÔNG nhầm bảng đó là thành phần hồ sơ.
        authorizationBlock: !!(
          window.__TLND__ && typeof window.__TLND__.hasAuthorizationAttachmentBlock === "function"
          && window.__TLND__.hasAuthorizationAttachmentBlock()
        ),
        // HkdOnline reload toàn trang qua từng bước; backend chỉ cần stage đã xác thực từ
        // control/metadata cổng để quyết định bootstrap hay bắt đầu nhận giấy tờ.
        businessHost,
        businessStage,
        businessProcedureHint,
        // Chỉ tin đúng câu xác nhận nộp/gửi hồ sơ của cổng. Không ghép hai cụm chung
        // "thành công" + "mã hồ sơ" vì chúng có thể cùng xuất hiện ở màn tra cứu khác.
        // Cổng nào màn kết quả nói khác (liên thông khai sinh) thì BE khai câu riêng trong
        // successText — khóa cả URL, xem matchSuccessText.
        submitted: body.includes("nop ho so thanh cong") || body.includes("gui ho so thanh cong")
          || matchSuccessText(body),
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
