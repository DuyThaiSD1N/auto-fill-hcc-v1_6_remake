// Nhận lệnh từ popup và điền dữ liệu cứng vào form hộ tịch điện tử.

// Guard chống nạp trùng: nếu content script bị inject lại (vd background re-inject sau khi
// reload extension), KHÔNG đăng ký listener lần 2 → tránh 1 click toggle 2 lần (mở rồi đóng ngay).
(() => {
  const CONTENT_VERSION = "panel-after-fill-v3";
  if (window.__AUTOFILL_HCC_MESSAGE_HANDLER__) {
    try {
      chrome.runtime.onMessage.removeListener(window.__AUTOFILL_HCC_MESSAGE_HANDLER__);
    } catch (e) {
      console.warn("[AutoFill] Không gỡ được listener cũ:", e);
    }
  }
  window.__AUTOFILL_HCC_CONTENT__ = true;
  window.__AUTOFILL_HCC_CONTENT_VERSION__ = CONTENT_VERSION;

  // Namespace chia sẻ giữa các file content (fill-angular.js...). Mỗi file 1 IIFE, giao tiếp qua đây.
  const H = (window.__HCC__ = window.__HCC__ || {});

  // ===== Location Manager: Load địa chỉ tỉnh/xã =====
  // Init và load data ngay khi content script chạy
  (async function initLocationManager() {
    // content/locations.js nạp trước content.js, nhưng nếu thiếu (hoặc đã nạp xong) thì bỏ qua —
    // gọi thẳng .load() trên undefined sẽ ném lỗi và chặn cả phần khởi tạo panel bên dưới.
    if (!window.locationManager || window.locationManager.loaded) return;
    try {
      await window.locationManager.load();
      console.log('[AutoFill] LocationManager loaded successfully');
    } catch (error) {
      console.error('[AutoFill] Failed to load LocationManager:', error);
    }
  })();

  // ===== Floating panel (chỉ trong top frame) =====
  const PANEL_ID = "autofill-hcc-panel";
  const BUBBLE_ID = "autofill-hcc-bubble";
  const IFRAME_ID = "autofill-hcc-iframe";
  const IS_TOP_FRAME = window === window.top;
  const PANEL_MIN_H = 160; // chiều cao tối thiểu của iframe (px)
  const APP_VERSION_LABEL = "1.15 · 1/9"; // hiện ở header panel; đổi tay mỗi lần phát hành (kèm ngày để hỗ trợ)
  // Trạng thái panel lưu THEO TAB (autofill_panel_open_<tabId>) để mỗi tab là 1 phiên độc lập:
  // reload cùng tab thì tự mở lại, nhưng mở TAB MỚI sẽ không bị kéo panel/phiên của tab cũ sang.
  let CURRENT_TAB_ID = null;

  function panelOpenKey() {
    return "autofill_panel_open_" + (CURRENT_TAB_ID ?? "");
  }
  // Trạng thái ĐÃ THU NHỎ (bubble) — lưu riêng để reload/postback dựng lại BUBBLE, KHÔNG bung panel full che form.
  function panelMinKey() {
    return "autofill_panel_min_" + (CURRENT_TAB_ID ?? "");
  }
  // Chỉ trạng thái thu nhỏ DO EXTENSION tạo ra sau khi nhận dữ liệu mới được tự mở lại ở bước đính kèm.
  // Tách key khỏi panelMinKey để không bao giờ hiểu nhầm thao tác thu nhỏ thủ công của cán bộ.
  function panelAutoMinKey() {
    return "autofill_panel_auto_min_" + (CURRENT_TAB_ID ?? "");
  }

  // sessionStorage: ĐỒNG BỘ, sống qua reload TRONG CÙNG TAB, tab MỚI không kế thừa → dùng để dựng lại
  // panel NGAY LẬP TỨC khi reload (không chờ async getTabId/storage → hết giật "ẩn rồi hiện").
  const SS_OPEN = "__af_panel_open";
  const SS_MIN = "__af_panel_min"; // đang thu nhỏ (bubble) — song song SS_OPEN, đồng bộ để reload giữ nguyên bubble
  const SS_AUTO_MIN = "__af_panel_auto_min"; // JSON { reason, procedure, phase, expiresAt }
  const SS_TAB = "__af_tab_id";
  const AUTO_MIN_TTL_MS = 30 * 60 * 1000;
  // Phiên "điền 8 trang" đang chạy (đồng bộ, sống qua reload trong cùng tab). Khi bật, KHÔNG mount lại
  // panel/iframe (nặng → nhấp nháy mỗi postback); chỉ hiện banner tiến độ nhẹ "Đang điền X/8".
  const SS_FILLALL = "__af_fillall_active";
  const SS_FILLALL_STEP = "__af_fillall_step"; // vd "3/8" — để dựng banner NGAY lúc reload, khỏi khe trống
  // Khóa trạng thái phiên fill-all trong chrome.storage.local (phải TRÙNG FILLALL_KEY ở business-registration.js).
  // Sống suốt phiên bất kể sessionStorage → dùng làm chốt chặn mount panel ở nhánh async khôi phục.
  const FILLALL_STATE_KEY = "autofill_fillall_state";
  // Tương tự cho phiên "đính kèm nhiều bước" (đăng ký hộ kinh doanh) — cũng ẩn panel + hiện tiến độ.
  const ATTACHALL_STATE_KEY = "autofill_attachall_state";
  // Và cho phiên điền 7 trang của cổng ĐKKD qua mạng (content/procedures/enterprise-registration.js).
  // Khóa riêng vì state machine HkdOnline sẽ tự resume nếu dùng chung FILLALL_STATE_KEY.
  const ENTERPRISE_FILLALL_STATE_KEY = "autofill_enterprise_fillall";
  function sessSet(k, v) { try { window.sessionStorage.setItem(k, v); } catch (e) { /* ignore */ } }
  function sessGet(k) { try { return window.sessionStorage.getItem(k); } catch (e) { return null; } }
  function sessDel(k) { try { window.sessionStorage.removeItem(k); } catch (e) { /* ignore */ } }

  function setPanelOpen(open) {
    // Ghi sessionStorage TRƯỚC (không phụ thuộc tabId) để lần reload sau khôi phục ngay.
    if (open) sessSet(SS_OPEN, "1"); else sessDel(SS_OPEN);
    if (CURRENT_TAB_ID == null) return; // chưa biết tab → chưa ghi chrome.storage, tránh key global
    try {
      if (open) chrome.storage.local.set({ [panelOpenKey()]: true });
      else chrome.storage.local.remove(panelOpenKey());
    } catch (e) { /* ignore */ }
  }

  // Lưu/xoá trạng thái thu nhỏ (mirror sessionStorage + chrome.storage như setPanelOpen).
  function setPanelMinimized(min) {
    if (min) sessSet(SS_MIN, "1"); else sessDel(SS_MIN);
    if (CURRENT_TAB_ID == null) return;
    try {
      if (min) chrome.storage.local.set({ [panelMinKey()]: true });
      else chrome.storage.local.remove(panelMinKey());
    } catch (e) { /* ignore */ }
  }

  function normalizeAutoMinState(value) {
    if (!value || typeof value !== "object") return null;
    if (value.reason !== "after-fill") return null;
    const expiresAt = Number(value.expiresAt || 0);
    if (!expiresAt || expiresAt <= Date.now()) return null;
    return {
      reason: "after-fill",
      procedure: String(value.procedure || ""),
      phase: value.phase === "filled" ? "filled" : "filling",
      expiresAt,
    };
  }

  function readAutoMinState() {
    try {
      const raw = sessGet(SS_AUTO_MIN);
      const state = normalizeAutoMinState(raw ? JSON.parse(raw) : null);
      if (!state && raw) sessDel(SS_AUTO_MIN);
      return state;
    } catch (_) {
      sessDel(SS_AUTO_MIN);
      return null;
    }
  }

  function setAutoMinState(value) {
    const state = normalizeAutoMinState(value);
    if (state) sessSet(SS_AUTO_MIN, JSON.stringify(state));
    else sessDel(SS_AUTO_MIN);
    if (CURRENT_TAB_ID == null) return;
    try {
      if (state) chrome.storage.local.set({ [panelAutoMinKey()]: state });
      else chrome.storage.local.remove(panelAutoMinKey());
    } catch (_) { /* ignore */ }
  }

  function clearAutoMinState() {
    setAutoMinState(null);
  }

  function removeUI() {
    document.getElementById(PANEL_ID)?.remove();
    document.getElementById(BUBBLE_ID)?.remove();
    setPanelOpen(false);
    setPanelMinimized(false); // đóng hẳn → xoá luôn cờ thu nhỏ
    clearAutoMinState();
  }

  function togglePanel() {
    if (!IS_TOP_FRAME) return;
    // Đang mở (kể cả đang thu nhỏ) → coi như đóng hẳn.
    if (document.getElementById(PANEL_ID) || document.getElementById(BUBBLE_ID)) {
      removeUI();
      return;
    }
    // Lấy tabId của frame này (để iframe biết gửi message đúng tab khi user đổi tab khác).
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      createPanel(res?.tabId ?? "");
    });
  }

  function _headerBtn(txt) {
    const b = document.createElement("button");
    b.textContent = txt;
    Object.assign(b.style, {
      background: "transparent", color: "#fff", border: "none",
      fontSize: "18px", lineHeight: "1", padding: "0 6px", cursor: "pointer",
    });
    return b;
  }

  function createPanel(tabId) {
    if (document.getElementById(PANEL_ID)) return;
    if (tabId != null && tabId !== "") { CURRENT_TAB_ID = tabId; sessSet(SS_TAB, String(tabId)); } // nhớ tab
    const root = document.createElement("div");
    root.id = PANEL_ID;
    Object.assign(root.style, {
      position: "fixed", top: "12px", right: "12px",
      width: "360px", height: "auto", maxHeight: "calc(100vh - 24px)",
      background: "#fff", border: "1px solid #ccc", borderRadius: "8px",
      boxShadow: "0 6px 24px rgba(0,0,0,.18)", zIndex: "2147483646",
      display: "flex", flexDirection: "column", overflow: "hidden",
      fontFamily: 'system-ui, "Segoe UI", sans-serif',
    });
    // Header (drag handle + thu nhỏ + đóng)
    const header = document.createElement("div");
    Object.assign(header.style, {
      background: "#1565c0", color: "#fff", padding: "6px 10px",
      display: "flex", alignItems: "center", justifyContent: "space-between",
      cursor: "move", userSelect: "none", fontSize: "13px", fontWeight: "600",
      flex: "0 0 auto",
    });
    const title = document.createElement("span");
    Object.assign(title.style, { display: "flex", alignItems: "center", gap: "6px" });
    const logo = document.createElement("img");
    logo.src = chrome.runtime.getURL("assets/icons/hcc-48.png");
    Object.assign(logo.style, { width: "18px", height: "18px", borderRadius: "3px", background: "#fff" });
    const titleText = document.createElement("span");
    titleText.textContent = "Trợ lý hồ sơ HCC";
    // Pill version mờ ngay sau tiêu đề — nhận biết nhanh phiên bản khi hỗ trợ, không chiếm dòng riêng.
    const ver = document.createElement("span");
    ver.textContent = "v" + APP_VERSION_LABEL;
    Object.assign(ver.style, {
      flex: "0 0 auto", fontSize: "10px", fontWeight: "600", lineHeight: "1",
      padding: "2px 6px", borderRadius: "999px", whiteSpace: "nowrap",
      background: "rgba(255,255,255,.22)", color: "#fff", letterSpacing: ".2px",
    });
    // Nút "Lịch sử cập nhật" ngay cạnh pill version → postMessage cho iframe (popup) mở popover.
    const histBtn = document.createElement("button");
    histBtn.type = "button";
    histBtn.textContent = "★ Lịch sử";
    histBtn.title = "Lịch sử cập nhật";
    Object.assign(histBtn.style, {
      flex: "0 0 auto", fontSize: "10px", fontWeight: "700", lineHeight: "1",
      padding: "3px 8px", borderRadius: "999px", whiteSpace: "nowrap", cursor: "pointer",
      background: "rgba(255,255,255,.18)", color: "#fff", border: "1px solid rgba(255,255,255,.42)",
    });
    histBtn.addEventListener("click", (e) => {
      e.stopPropagation();  // không kích hoạt kéo panel
      const f = document.getElementById(IFRAME_ID);
      if (f && f.contentWindow) f.contentWindow.postMessage({ type: "autofill-hcc-open-history" }, "*");
    });
    title.append(logo, titleText, ver, histBtn);
    const btns = document.createElement("div");
    const minBtn = _headerBtn("–");
    minBtn.title = "Thu nhỏ";
    minBtn.addEventListener("click", (e) => { e.stopPropagation(); minimizePanel(); });
    const closeBtn = _headerBtn("×");
    closeBtn.title = "Đóng";
    closeBtn.addEventListener("click", (e) => { e.stopPropagation(); removeUI(); });
    btns.append(minBtn, closeBtn);
    header.append(title, btns);
    root.appendChild(header);

    // Iframe load popup.html với param đánh dấu embedded + tabId.
    // Chiều cao auto-fit theo nội dung qua postMessage (xem listener bên dưới).
    const iframe = document.createElement("iframe");
    iframe.id = IFRAME_ID;
    iframe.src = chrome.runtime.getURL(`popup.html?embedded=1&tabId=${tabId}`);
    Object.assign(iframe.style, {
      border: "0", width: "100%", height: "420px", background: "#fff", display: "block",
      // Chống "giật": ẩn nội dung iframe đến khi popup render xong (nhận resize msg đầu) rồi HIỆN DẦN.
      opacity: "0", transition: "opacity 140ms ease",
    });
    // Fallback: nếu vì lý do gì không nhận được resize msg, vẫn hiện iframe sau khi load (khỏi trắng mãi).
    const reveal = () => { const f = document.getElementById(IFRAME_ID); if (f) f.style.opacity = "1"; };
    iframe.addEventListener("load", () => setTimeout(reveal, 60));
    setTimeout(reveal, 1500);
    root.appendChild(iframe);

    document.documentElement.appendChild(root);
    enableDrag(root, header);
    setPanelOpen(true);
    setPanelMinimized(false); // dựng panel FULL → không còn ở trạng thái thu nhỏ
    clearAutoMinState();
  }

  // Dựng bubble góc phải trên (nếu chưa có). Tách riêng để nhánh khôi phục sau reload gọi được mà
  // KHÔNG cần panel tồn tại — reload lúc đang thu nhỏ chỉ dựng lại bubble, không bung panel che form.
  function showBubble() {
    if (document.getElementById(BUBBLE_ID)) return;
    const bubble = document.createElement("div");
    bubble.id = BUBBLE_ID;
    bubble.title = "Mở Trợ lý hồ sơ HCC";
    Object.assign(bubble.style, {
      position: "fixed", top: "12px", right: "12px",
      width: "48px", height: "48px", borderRadius: "50%",
      background: "#fff", overflow: "hidden",
      display: "flex", alignItems: "center", justifyContent: "center",
      boxShadow: "0 4px 14px rgba(0,0,0,.3)", cursor: "pointer",
      zIndex: "2147483646", userSelect: "none",
    });
    const bubbleImg = document.createElement("img");
    bubbleImg.src = chrome.runtime.getURL("assets/icons/hcc-128.png");
    Object.assign(bubbleImg.style, { width: "100%", height: "100%", objectFit: "cover" });
    bubble.appendChild(bubbleImg);
    bubble.addEventListener("click", restorePanel);
    document.documentElement.appendChild(bubble);
  }

  // Thu nhỏ: ẩn panel (giữ iframe để không mất trạng thái) + hiện bubble + LƯU cờ thu nhỏ (để reload giữ nguyên).
  function minimizePanel({ reason = "manual", procedure = "", preserveAuto = false, requirePanel = false } = {}) {
    const panel = document.getElementById(PANEL_ID);
    if (requirePanel && !panel) return false;
    if (panel) panel.style.display = "none";
    showBubble();
    setPanelMinimized(true);
    if (reason === "after-fill") {
      setAutoMinState({
        reason: "after-fill",
        procedure,
        phase: "filling",
        expiresAt: Date.now() + AUTO_MIN_TTL_MS,
      });
    } else if (!preserveAuto) {
      clearAutoMinState();
    }
    return true;
  }

  function requestIframeContentResize() {
    const iframe = document.getElementById(IFRAME_ID);
    if (!iframe?.contentWindow) return;
    const request = () => iframe.contentWindow?.postMessage({ type: "autofill-hcc-request-resize" }, "*");
    // Nhịp đầu sau khi display:flex để iframe có kích thước; nhịp sau bắt kịp Angular/ảnh/font vừa render.
    window.requestAnimationFrame(request);
    setTimeout(request, 100);
  }

  // Bấm bubble → hiện lại panel (tạo mới nếu chưa có) + xoá cờ thu nhỏ.
  function restorePanel() {
    document.getElementById(BUBBLE_ID)?.remove();
    setPanelMinimized(false);
    clearAutoMinState();
    const panel = document.getElementById(PANEL_ID);
    if (panel) {
      panel.style.display = "flex";
      requestIframeContentResize();
    }
    else chrome.runtime.sendMessage({ action: "getTabId" }, (res) => createPanel(res?.tabId ?? ""));
  }

  // Toast nằm trên TRANG CỔNG (không nằm trong iframe panel) nên cán bộ vẫn thấy khi panel đang thu nhỏ.
  // Dùng Shadow DOM để CSS của từng cổng không làm đổi màu/kích thước thông báo.
  const PAGE_TOAST_ID = "autofill-hcc-page-toast";
  let pageToastTimer = null;
  let pageToastRemoveTimer = null;

  function pageToastIcon(kind) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2.4");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("d", kind === "warn" ? "M12 7v6m0 4h.01M12 3l10 18H2L12 3z" : "M5 12.5l4.2 4.2L19 7");
    svg.appendChild(path);
    return svg;
  }

  function showPageToast(message, kind = "success") {
    if (!IS_TOP_FRAME) return false;
    const text = String(message || "").replace(/\s+/g, " ").trim().slice(0, 180);
    if (!text) return false;
    const tone = kind === "warn" ? "warn" : "success";
    if (pageToastTimer) clearTimeout(pageToastTimer);
    if (pageToastRemoveTimer) clearTimeout(pageToastRemoveTimer);
    document.getElementById(PAGE_TOAST_ID)?.remove();

    const host = document.createElement("div");
    host.id = PAGE_TOAST_ID;
    Object.assign(host.style, {
      position: "fixed",
      top: "18px",
      left: "50%",
      transform: "translateX(-50%)",
      width: "min(420px, calc(100vw - 32px))",
      zIndex: "2147483647",
      pointerEvents: "none",
    });
    const shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = `
      .toast {
        box-sizing: border-box;
        display: flex;
        align-items: center;
        gap: 11px;
        width: 100%;
        padding: 12px 14px;
        border: 1px solid rgba(255,255,255,.28);
        border-radius: 10px;
        color: #fff;
        background: #166534;
        box-shadow: 0 10px 28px rgba(15,23,42,.28);
        font-family: system-ui, "Segoe UI", sans-serif;
        opacity: 0;
        transform: translateY(-10px);
        animation: toast-in 180ms ease-out forwards;
      }
      .toast.warn { background: #92400e; }
      .icon {
        flex: 0 0 30px;
        display: grid;
        place-items: center;
        width: 30px;
        height: 30px;
        border-radius: 999px;
        background: rgba(255,255,255,.16);
      }
      .icon svg { width: 19px; height: 19px; }
      .copy { min-width: 0; }
      .title { margin: 0 0 1px; font-size: 12px; line-height: 1.3; font-weight: 700; opacity: .9; }
      .message { margin: 0; font-size: 14px; line-height: 1.45; font-weight: 600; overflow-wrap: anywhere; }
      .toast.leaving { animation: toast-out 160ms ease-in forwards; }
      @keyframes toast-in { to { opacity: 1; transform: translateY(0); } }
      @keyframes toast-out { to { opacity: 0; transform: translateY(-8px); } }
      @media (prefers-reduced-motion: reduce) {
        .toast, .toast.leaving { animation-duration: 1ms; transform: none; }
      }
    `;
    const toast = document.createElement("div");
    toast.className = `toast ${tone}`;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    toast.setAttribute("aria-atomic", "true");
    const icon = document.createElement("span");
    icon.className = "icon";
    icon.appendChild(pageToastIcon(tone));
    const copy = document.createElement("div");
    copy.className = "copy";
    const title = document.createElement("p");
    title.className = "title";
    title.textContent = tone === "warn" ? "Cần rà soát" : "Hoàn tất";
    const body = document.createElement("p");
    body.className = "message";
    body.textContent = text;
    copy.append(title, body);
    toast.append(icon, copy);
    shadow.append(style, toast);
    document.documentElement.appendChild(host);

    pageToastTimer = setTimeout(() => {
      toast.classList.add("leaving");
      pageToastRemoveTimer = setTimeout(() => host.remove(), 180);
    }, 5000);
    return true;
  }

  H.showPageToast = showPageToast;

  // ===== Chế độ "điền 8 trang": ẩn panel/iframe (nặng, nhấp nháy mỗi postback), chỉ giữ banner nhẹ =====
  const FILLALL_BANNER_ID = "af-fillall-progress";

  // Banner tiến độ tối giản (text + nút Huỷ) — nhẹ nên re-render mỗi reload gần như không thấy giật.
  function showFillAllProgress(text) {
    let el = document.getElementById(FILLALL_BANNER_ID);
    if (!el) {
      el = document.createElement("div");
      el.id = FILLALL_BANNER_ID;
      Object.assign(el.style, {
        position: "fixed", top: "12px", right: "12px", zIndex: "2147483646",
        padding: "8px 14px", borderRadius: "8px", background: "#1565c0", color: "#fff",
        font: "600 13px/1.35 system-ui, 'Segoe UI', sans-serif",
        boxShadow: "0 4px 14px rgba(0,0,0,.25)", maxWidth: "300px", whiteSpace: "pre-wrap",
        pointerEvents: "none", // banner không chặn click trang; chỉ nút Huỷ mới nhận click.
      });
      const txt = document.createElement("div");
      txt.id = FILLALL_BANNER_ID + "-txt";
      const btn = document.createElement("button");
      btn.id = FILLALL_BANNER_ID + "-cancel";
      btn.type = "button";
      btn.textContent = "✕ Huỷ tiến trình";
      Object.assign(btn.style, {
        marginTop: "8px", width: "100%", padding: "5px 8px", cursor: "pointer",
        border: "1px solid rgba(255,255,255,.6)", borderRadius: "6px",
        background: "rgba(255,255,255,.15)", color: "#fff",
        font: "600 12px/1.2 system-ui, 'Segoe UI', sans-serif", pointerEvents: "auto",
      });
      btn.addEventListener("click", (e) => { e.stopPropagation(); cancelFillAll(); });
      el.appendChild(txt);
      el.appendChild(btn);
      (document.body || document.documentElement).appendChild(el);
    }
    const txtEl = document.getElementById(FILLALL_BANNER_ID + "-txt");
    if (txtEl) txtEl.textContent = text; else el.textContent = text;
    return el;
  }

  // Huỷ toàn bộ tiến trình fill 8 trang + đính kèm: xoá state trong chrome.storage → các state machine
  // (stepFillAll/stepAttachAll) tự dừng ở lần resume kế (không còn state → return sớm).
  function cancelFillAll() {
    try {
      chrome.storage.local.remove([FILLALL_STATE_KEY, ATTACHALL_STATE_KEY, ENTERPRISE_FILLALL_STATE_KEY]);
    } catch (e) { /* ignore */ }
    sessDel(SS_FILLALL);
    sessDel(SS_FILLALL_STEP);
    const banner = document.getElementById(FILLALL_BANNER_ID);
    if (banner) {
      banner.style.background = "#b23b3b";
      const txtEl = document.getElementById(FILLALL_BANNER_ID + "-txt");
      if (txtEl) txtEl.textContent = "Đã huỷ tiến trình. Bạn có thể thao tác lại trên trang.";
      const btn = document.getElementById(FILLALL_BANNER_ID + "-cancel");
      if (btn) btn.remove();
      setTimeout(() => document.getElementById(FILLALL_BANNER_ID)?.remove(), 5000);
    }
    // Dựng lại panel để user tiếp tục dùng.
    if (!document.getElementById(PANEL_ID)) {
      createPanel(CURRENT_TAB_ID ?? sessGet(SS_TAB) ?? "");
    }
  }

  // Bắt đầu phiên fill-all: đánh dấu (đồng bộ) + gỡ panel/bubble NGAY (không đụng SS_OPEN → nhớ để bật lại).
  function beginFillAllUI() {
    sessSet(SS_FILLALL, "1");
    document.getElementById(PANEL_ID)?.remove();
    document.getElementById(BUBBLE_ID)?.remove();
  }

  // Hiện tiến độ + mirror TOÀN VĂN sang sessionStorage để reload sau dựng banner NGAY (khỏi khe trống).
  function setRunProgressText(text) {
    sessSet(SS_FILLALL_STEP, text);
    showFillAllProgress(text);
  }

  // Tiến độ fill 8 trang: "Đang điền trang X/8 — <tên trang>".
  function setFillAllProgress(step, total, label) {
    setRunProgressText(`Đang điền trang ${step}/${total}${label ? " — " + label : ""}\n(đừng thao tác tới khi xong)`);
  }

  // Kết thúc phiên fill-all: xoá cờ + hiện lại panel nếu trước đó đang mở.
  function endFillAllUI(doneText) {
    sessDel(SS_FILLALL);
    sessDel(SS_FILLALL_STEP);
    const banner = document.getElementById(FILLALL_BANNER_ID);
    if (banner) {
      if (doneText) {
        banner.style.background = "#1e824c";
        const txtEl = document.getElementById(FILLALL_BANNER_ID + "-txt");
        if (txtEl) txtEl.textContent = doneText; else banner.textContent = doneText;
        document.getElementById(FILLALL_BANNER_ID + "-cancel")?.remove(); // xong → bỏ nút Huỷ
        setTimeout(() => document.getElementById(FILLALL_BANNER_ID)?.remove(), 8000);
      } else {
        banner.remove();
      }
    }
    // Fill-all CHỈ khởi động được từ panel đang mở → luôn dựng lại (không phụ thuộc sessionStorage, vốn có
    // thể đã bị reset qua các nhịp postback). createPanel sẽ tự set lại SS_OPEN + chrome.storage.
    if (!document.getElementById(PANEL_ID)) {
      createPanel(CURRENT_TAB_ID ?? sessGet(SS_TAB) ?? "");
    }
  }

  H.beginFillAllUI = beginFillAllUI;
  H.endFillAllUI = endFillAllUI;
  H.setFillAllProgress = setFillAllProgress;
  H.setRunProgressText = setRunProgressText;

  // Auto-fit: popup (iframe) gửi chiều cao nội dung → co panel "vừa đủ".
  if (IS_TOP_FRAME) {
    if (window.__AUTOFILL_HCC_RESIZE_HANDLER__) {
      window.removeEventListener("message", window.__AUTOFILL_HCC_RESIZE_HANDLER__);
    }
    const onResizeMsg = (e) => {
      const d = e.data;
      if (!d || d.type !== "autofill-hcc-resize") return;
      const iframe = document.getElementById(IFRAME_ID);
      if (!iframe) return;
      const max = window.innerHeight - 120;
      iframe.style.height = Math.max(PANEL_MIN_H, Math.min(d.height || 0, max)) + "px";
      if (iframe.style.opacity !== "1") iframe.style.opacity = "1"; // nội dung sẵn sàng → hiện dần
    };
    window.__AUTOFILL_HCC_RESIZE_HANDLER__ = onResizeMsg;
    window.addEventListener("message", onResizeMsg);
  }

  // Cổng dvc là SPA: URL có thể đổi không reload, hoặc nội dung thủ tục đổi sau khi URL đã đứng yên.
  // Theo dõi cả URL lẫn tín hiệu DOM; debounce + chữ ký giúp không quét lại theo mọi mutation nhỏ.
  // Content script ở isolated world nên không patch history.pushState của trang (main world): vẫn poll href
  // làm lưới an toàn, rồi retry vài nhịp để chờ Angular/Vue render xong tên thủ tục.
  if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_URLWATCH__) {
    window.__AUTOFILL_HCC_URLWATCH__ = true;
    let lastHref = location.href;
    let lastSignalSignature = "";
    let domDetectTimer = null;
    let navigationRetryTimers = [];

    const postPanelPageChanged = (reason) => {
      const iframe = document.getElementById(IFRAME_ID);
      if (!iframe?.contentWindow) return;
      try {
        iframe.contentWindow.postMessage(
          { type: "autofill-hcc-page-changed", url: location.href, reason },
          "*"
        );
      } catch (_) { /* ignore */ }
    };

    const scheduleNavigationDetection = () => {
      navigationRetryTimers.forEach(clearTimeout);
      navigationRetryTimers = [0, 350, 1000, 2500].map((delay) =>
        setTimeout(() => postPanelPageChanged("url"), delay)
      );
    };

    const procedureSignalSignature = () => {
      try {
        const signals = collectProcedureSignals();
        return JSON.stringify([
          signals.url,
          signals.title,
          signals.headings,
          signals.businessProcedureHint,
          signals.enterpriseProcedureHint,
          signals.enterpriseEntityLabel,
          signals.bodyText,
        ]);
      } catch (_) {
        return "";
      }
    };

    const PROCEDURE_HEADING_SELECTOR = ".text-2xl.font-bold, h1, h2, title";
    const containsProcedureHeading = (node) => node?.nodeType === Node.ELEMENT_NODE
      && (node.matches(PROCEDURE_HEADING_SELECTOR) || node.querySelector(PROCEDURE_HEADING_SELECTOR));
    const isProcedureMutation = (mutations) => mutations.some((mutation) => {
      if (mutation.type === "characterData") {
        return !!mutation.target.parentElement?.closest(PROCEDURE_HEADING_SELECTOR);
      }
      if (mutation.type === "attributes") {
        // HKD đổi active wizard bằng class; các cổng khác chỉ quan tâm container có heading thủ tục.
        return location.hostname.includes("hokinhdoanh.dkkd.gov.vn")
          || !!mutation.target.closest?.(PROCEDURE_HEADING_SELECTOR)
          || containsProcedureHeading(mutation.target);
      }
      if (mutation.target.closest?.(PROCEDURE_HEADING_SELECTOR)) return true;
      return [...mutation.addedNodes, ...mutation.removedNodes].some((node) => {
        if (containsProcedureHeading(node)) return true;
        // Cổng không có heading (vd Lai Châu) thường thay cả một khối nội dung khi đổi thủ tục.
        return String(node.textContent || "").replace(/\s+/g, " ").trim().length >= 20;
      });
    });

    const notifyPanelUrlChanged = () => {
      if (location.href === lastHref) return;
      lastHref = location.href;
      lastSignalSignature = "";
      scheduleNavigationDetection();
    };

    window.addEventListener("popstate", notifyPanelUrlChanged);
    window.addEventListener("hashchange", notifyPanelUrlChanged);
    setInterval(notifyPanelUrlChanged, 1000);

    lastSignalSignature = procedureSignalSignature();
    const procedureObserver = new MutationObserver((mutations) => {
      if (!isProcedureMutation(mutations)) return;
      if (domDetectTimer) clearTimeout(domDetectTimer);
      domDetectTimer = setTimeout(() => {
        domDetectTimer = null;
        const signature = procedureSignalSignature();
        if (!signature || signature === lastSignalSignature) return;
        lastSignalSignature = signature;
        postPanelPageChanged("dom");
      }, 400);
    });
    procedureObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "hidden", "aria-current", "aria-selected"],
    });
  }

  function enableDrag(root, handle) {
    let dragging = false, startX = 0, startY = 0, startTop = 0, startLeft = 0;
    handle.addEventListener("mousedown", (e) => {
      if (e.target.tagName === "BUTTON") return;
      dragging = true;
      startX = e.clientX; startY = e.clientY;
      const rect = root.getBoundingClientRect();
      startTop = rect.top; startLeft = rect.left;
      root.style.right = "auto"; // chuyển sang dùng left
      root.style.left = startLeft + "px";
      e.preventDefault();
    });
    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      root.style.top = Math.max(0, startTop + e.clientY - startY) + "px";
      root.style.left = Math.max(0, startLeft + e.clientX - startX) + "px";
    });
    document.addEventListener("mouseup", () => { dragging = false; });
  }

  function handleAutofillMessage(msg, sender, sendResponse) {
    // manifest inject content script vào all_frames. Các action state machine HkdOnline chỉ được
    // frame chính trả lời; nếu iframe con phản hồi `unknown` trước, popup sẽ dừng dù trang gốc đúng.
    if (window.top !== window && [
      "startFillAllBusiness",
      "startChangeBusiness",
      "startAttachAllBusiness",
      "navigateBusinessPage",
      "detectBusinessPage",
      "detectBusinessChangeStage",
    ].includes(msg?.action)) return;
    if (msg?.action === "togglePanel") { togglePanel(); sendResponse({ ok: true }); return; }
    if (msg?.action === "showPageToast") {
      if (!IS_TOP_FRAME) return;
      sendResponse({ ok: true, shown: showPageToast(msg.message, msg.kind) });
      return;
    }
    if (msg?.action === "minimizePanelForFill") {
      if (!IS_TOP_FRAME) return;
      const minimized = minimizePanel({
        reason: "after-fill",
        procedure: msg.procedure || "",
        requirePanel: true,
      });
      sendResponse({ ok: true, minimized });
      return;
    }
    if (msg?.action === "markPanelFillComplete") {
      if (!IS_TOP_FRAME) return;
      // Theo yêu cầu: fill xong GIỮ NGUYÊN icon (bubble), KHÔNG tự bung panel lại ở bước đính kèm
      // (trước đây tự mở nhưng iframe chưa fit chiều cao kịp → panel bị cắt ~1/5). Xoá cờ after-fill để
      // observer đính kèm ngừng theo dõi; panel vẫn ở bubble (qua SS_MIN). Cán bộ bấm icon để mở lại —
      // đường restorePanel fit đúng chiều cao. Phản hồi "đã điền" đã có page-toast nên không cần bung panel.
      clearAutoMinState();
      sendResponse({ ok: true, armed: false });
      return;
    }
    if (msg?.action === "restorePanelAfterFillFailure") {
      if (!IS_TOP_FRAME) return;
      const state = readAutoMinState();
      if (state) restorePanel();
      sendResponse({ ok: true, restored: !!state });
      return;
    }
    if (msg?.action === "clearPanelAutoRestore") {
      if (!IS_TOP_FRAME) return;
      clearAutoMinState();
      sendResponse({ ok: true });
      return;
    }
    if (msg?.action === "startFillAllBusiness") {
      const pages = (msg && msg.pages) || {};
      const st = {
        // Đi đúng thứ tự biểu mẫu từ đầu; đến trang người nộp mới sao chép contact tài khoản tại chỗ.
        order: [...BUSINESS_PAGE_ORDER],
        pages,
        step: 0,
        retries: 0,
        phase: "fill",
        filledStep: -1,
        // Default theo tài khoản/phường (vd Xuân Hương) do popup truyền xuống; giữ trong state để sống qua postback.
        businessDefaults: (msg && msg.businessDefaults) || null,
        // Gộp đính kèm: điền xong 8 trang → tự chạy state machine đính kèm (nếu popup gửi kèm).
        attachPayload: (msg && msg.attachPayload) || null,
      };
      sessSet(SS_FILLALL, "1"); // đánh dấu SỚM (đồng bộ) để reload đầu không kịp mount lại panel
      H.setFillAllState(st).then(() => {
        sendResponse({ ok: true, started: true });
        // Ẩn panel/iframe SAU khi đã trả response (tránh phá iframe khi popup còn chờ). Reload đầu tiên
        // của postback sẽ tự xoá DOM; cờ SS_FILLALL giữ cho các reload sau không dựng lại.
        setTimeout(() => { beginFillAllUI(); H.stepFillAll(); }, 60);
      });
      return true;
    }
    if (msg?.action === "startChangeBusiness") {
      const flow = (msg && msg.businessFlow) || {};
      const pages = (msg && msg.pages) || {};
      const detected = typeof H.detectBusinessChangeStage === "function"
        ? H.detectBusinessChangeStage() : { stage: "unknown" };
      if (detected.stage === "unknown") {
        sendResponse({ error: "Trang hiện tại không thuộc luồng nghiệp vụ hộ kinh doanh đã chọn. Hãy mở đúng hồ sơ rồi chạy lại." });
        return true;
      }
      const order = Array.isArray(flow.pageOrder) && flow.pageOrder.length
        ? [...flow.pageOrder] : ["nguoi-nop-ho-so"];
      const st = {
        workflow: flow.workflow || "change",
        businessFlow: flow,
        // Lưu riêng khóa tìm kiếm vì đây là dữ liệu bootstrap bắt buộc phải sống qua nhiều full postback.
        businessSearch: (msg && msg.businessSearch) || flow.search || null,
        order,
        pages,
        step: 0,
        retries: 0,
        phase: "fill",
        filledStep: -1,
        bootstrapDone: false,
        businessDefaults: (msg && msg.businessDefaults) || null,
        attachPayload: (msg && msg.attachPayload) || null,
      };
      sessSet(SS_FILLALL, "1");
      H.setFillAllState(st).then(() => {
        sendResponse({ ok: true, started: true, stage: detected.stage, order });
        setTimeout(() => { beginFillAllUI(); H.stepFillAll(); }, 60);
      });
      return true;
    }
    if (msg?.action === "startAttachAllBusiness") {
      // Đính kèm hộ kinh doanh (cổng HkdOnline): khai báo loại → tải file → gán loại → Lưu, qua nhiều postback.
      const files = Array.isArray(msg.files) ? msg.files : [];
      const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
      if (!files.length || !attachments.length) {
        sendResponse({ error: "Thiếu file hoặc kế hoạch đính kèm." });
        return true;
      }
      if (typeof H.startAttachAllBusiness !== "function") {
        sendResponse({ error: "Chưa nạp được module đính kèm hộ kinh doanh." });
        return true;
      }
      sessSet(SS_FILLALL, "1");
      H.startAttachAllBusiness(files, attachments).then((r) => {
        sendResponse(r || { ok: true, started: true });
        setTimeout(() => { beginFillAllUI(); H.stepAttachAll(); }, 60);
      });
      return true;
    }
    if (msg?.action === "navigateBusinessPage") {
      H.navigateBusinessRegistrationPage(msg.page, msg.label).then(sendResponse);
      return true;
    }
    if (msg?.action === "detectBusinessPage") {
      // Chỉ frame có breadcrumb mới trả lời (tránh frame con trả null đè lên).
      if (!document.querySelector('[id*="SiteMapPath"]')) return;
      sendResponse(H.detectBusinessPageKey());
      return;
    }
    if (msg?.action === "detectBusinessChangeStage") {
      const result = typeof H.detectBusinessChangeStage === "function"
        ? H.detectBusinessChangeStage() : { stage: "unknown", pageKey: null };
      sendResponse({ ok: true, ...result });
      return;
    }
    if (msg?.action === "collectFormContext") {
      if (!hasFillableForm()) return;
      sendResponse({ ok: true, formContext: collectFormContext() });
      return;
    }
    if (msg?.action === "collectAttachmentContext") {
      if (!hasAttachmentTarget()) return;
      sendResponse({ ok: true, attachmentContext: collectAttachmentContext() });
      return;
    }
    if (msg?.action === "attachFilesByPlan") {
      if (!hasAttachmentTarget()) return;
      const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
      if (!attachments.length) {
        sendResponse({ error: "Không có kế hoạch đính kèm từ backend." });
        return;
      }
      (async () => {
        let files = Array.isArray(msg.files) ? msg.files : [];
        // File lớn (hợp đồng vài chục MB) vượt giới hạn 64MiB của sendMessage → popup ghi vào
        // chrome.storage.local, chỉ gửi key; đọc lại ở đây rồi XOÁ key để không phình storage.
        if (msg.filesStorageKey) {
          try {
            const got = await chrome.storage.local.get(msg.filesStorageKey);
            const stored = got?.[msg.filesStorageKey];
            if (Array.isArray(stored?.files)) files = stored.files;
          } catch (e) {
            console.warn("[AutoFill] đọc file đính kèm từ storage lỗi:", e);
          } finally {
            try { chrome.storage.local.remove(msg.filesStorageKey); } catch (e) { /* ignore */ }
          }
        }
        if (!files.length) {
          sendResponse({ error: "Không có file nào để đính kèm." });
          return;
        }
        const res = await attachFilesByPlan(files, attachments, msg.procedure || "", { mode: msg.mode || "merge" });
        sendResponse(res);
      })();
      return true;
    }
    if (msg?.action === "getDossierUrl") {
      // Chỉ frame TRÊN CÙNG trả URL hồ sơ; trả URL SẠCH (giữ maThuTuc/tinhThanhId) để mở hồ sơ MỚI.
      if (window.top !== window) return;
      try {
        const u = new URL(location.href);
        const keep = new URLSearchParams();
        for (const k of ["maThuTuc", "tinhThanhId"]) {
          const v = u.searchParams.get(k);
          if (v) keep.set(k, v);
        }
        sendResponse({ ok: true, url: u.origin + u.pathname + (keep.toString() ? "?" + keep.toString() : "") });
      } catch (e) {
        console.warn("[AutoFill] Lấy URL hồ sơ lỗi:", e);
        sendResponse({ error: "Không đọc được địa chỉ hồ sơ trên trang." });
      }
      return;
    }
    if (msg?.action === "detectProcedure") {
      // Chỉ frame TRÊN CÙNG trả lời (URL + heading nằm ở trang gốc, không phải iframe con).
      if (window.top !== window) return;
      sendResponse({ ok: true, signals: collectProcedureSignals() });
      return;
    }
    if (msg?.action === "getPortalFlowState") {
      // Chỉ cổng DVC quốc gia có khối chọn cơ quan + modal "Thông tin chung"
      // (content/agency-select.js trả lời). Cổng khác trả unsupported để popup đi thẳng, không
      // phải chờ hết vòng retry inject của sendToContent.
      if (window.top !== window || window.__HCC_AGENCY_FLOW__) return;
      sendResponse({ ok: true, unsupported: true });
      return;
    }
    if (msg?.action === "getPortalPrincipal") {
      // Danh tính tài khoản VNeID đang đăng nhập trên CỔNG → popup gắn consent theo (người + thủ tục).
      if (window.top !== window) return;
      sendResponse({ ok: true, principal: extractPortalPrincipal() });
      return;
    }
    if (msg?.action === "attachFilesViaWallet") {
      if (!hasAttachmentTarget()) return;
      const files = Array.isArray(msg.files) ? msg.files : [];
      if (!files.length) {
        sendResponse({ error: "Không có file nào để đính kèm." });
        return;
      }
      attachFilesToRequiredCopyCertification(files).then(sendResponse);
      return true;
    }
    if (msg?.action === "openBacNinhTab") {
      if (typeof H.isBacNinhForm === "function" && !H.isBacNinhForm()) return;
      if (typeof H.activateBacNinhTab !== "function") {
        sendResponse({ error: "Engine biểu mẫu Bắc Ninh chưa sẵn sàng." });
        return true;
      }
      Promise.resolve(H.activateBacNinhTab(msg.tabName)).then(sendResponse)
        .catch(() => sendResponse({ error: "Không mở được phần biểu mẫu yêu cầu." }));
      return true;
    }
    if (msg.action === "fillBacNinhAuthorizedPerson") {
      const fields = Array.isArray(msg.fields) ? msg.fields : [];
      if (typeof H.isBacNinhForm === "function" && !H.isBacNinhForm()) return;
      if (!fields.length || typeof H.fillAuthorizedPersonBacNinh !== "function") {
        sendResponse({ error: "Không có dữ liệu người được ủy quyền hoặc engine Bắc Ninh chưa sẵn sàng." });
        return;
      }
      Promise.resolve().then(() => H.fillAuthorizedPersonBacNinh(fields, msg.subjectOption)).then(sendResponse)
        .catch(() => sendResponse({ error: "Không điền được thông tin người ủy quyền." }));
      return true;
    }
    if (msg.action !== "fillFields") return;
    // Content script chạy trên mọi frame; chỉ frame thật sự chứa form mới xử lý.
    // Phát hiện loại form: Angular mới ([formcontrolname]), web-component cũ (x-*),
    // hoặc form HTML thường (input/select[name]) của các thủ tục đất đai.
    const formKind = detectFormKind();
    if (!formKind) return; // frame không chứa form thật
    let fields = Array.isArray(msg.fields) ? msg.fields : [];
    // Lượt điền MỘT trang HKD cũng phải áp default theo địa bàn (vd "Lý do giải thể" / "Địa chỉ nhận
    // kết quả" của tài khoản Hải Châu), giống hệt lượt tự chạy cả luồng.
    if (msg.businessPage && typeof H.applyBusinessLocalDefaults === "function") {
      try { fields = H.applyBusinessLocalDefaults(fields, msg.businessDefaults, msg.businessPage); }
      catch (e) { console.warn("[AutoFill] default theo địa bàn:", e); }
    }
    if (!fields.length) { sendResponse({ error: "Không có trường nào để điền." }); return; }
    const forceStandard = fields.some((f) =>
      String(f?.comp || "").startsWith("dom-") || String(f?.name || "").startsWith("data[")
    );
    // Form Bắc Ninh dùng engine riêng (khớp ô theo NHÃN, comp bn-*) — ưu tiên trước mọi nhánh khác.
    const filler = formKind === "bacninh"
      ? H.fillFormBacNinh
      : (forceStandard
        ? fillFormStandard
        : (formKind === "liz" ? H.fillFormLiz
          : (formKind === "angular" ? H.fillFormAngular : (formKind === "legacy" ? H.fillForm : fillFormStandard))));
    if (typeof filler !== "function") {
      sendResponse({ error: `Engine điền chưa nạp (formKind=${formKind}).` });
      return;
    }
    // LUÔN trả response (kể cả khi engine ném lỗi) → tránh popup retry/re-inject gây điền lặp.
    Promise.resolve().then(() => filler(fields))
      .then((res) => {
        // HKD quét riêng trang ngành nghề: điền ghi chú mặc định theo tài khoản/phường nếu popup có config.
        // Luồng này không tự Lưu; cán bộ vẫn rà soát và lưu như các lần điền lẻ khác.
        if (msg.businessPage === "nganh-nghe-kinh-doanh" && typeof H.fillBusinessActDefault === "function") {
          try { H.fillBusinessActDefault(msg.businessDefaults); } catch (e) { /* không chặn response điền chính */ }
        }
        sendResponse(res);
      })
      .catch((e) => {
        console.warn("[AutoFill] Điền dữ liệu lên trang lỗi:", e);
        sendResponse({ error: "Không điền được dữ liệu lên trang. Vui lòng thử lại." });
      });
    return true; // giữ kênh để phản hồi bất đồng bộ (cascade địa danh cần chờ)
  }

  window.__AUTOFILL_HCC_MESSAGE_HANDLER__ = handleAutofillMessage;
  chrome.runtime.onMessage.addListener(handleAutofillMessage);

  // Sau khi chuyển trang (WebForms reload → DOM bị xoá), tự bật lại panel nổi nếu trước đó đang mở.
  // Chống giật: dựng lại panel NGAY (document_start + sessionStorage đồng bộ), iframe hiện dần khi sẵn sàng.
  if (IS_TOP_FRAME) {
    // (1) NGAY LẬP TỨC (đồng bộ): panel trước đó đang mở trong tab này → dựng lại luôn, không chờ async
    //     → không còn khoảng "trống panel" giữa lúc reload → hết giật.
    const restoreEarly = () => {
      // Đang chạy tiến trình nhiều bước (fill 8 trang / đính kèm) → KHÔNG dựng lại panel/iframe (nặng,
      // nhấp nháy); chỉ dựng lại banner tiến độ ngay (toàn văn đã mirror ở SS_FILLALL_STEP).
      if (sessGet(SS_FILLALL) === "1") {
        showFillAllProgress(sessGet(SS_FILLALL_STEP) || "Đang xử lý hồ sơ...");
        return;
      }
      if (sessGet(SS_OPEN) !== "1") return;
      const cachedTab = sessGet(SS_TAB) || "";
      if (cachedTab) CURRENT_TAB_ID = cachedTab;
      // Trước đó user thu nhỏ → chỉ dựng lại BUBBLE, KHÔNG bung panel full (đây là bug che form khi click gây postback).
      if (sessGet(SS_MIN) === "1") {
        if (!document.getElementById(PANEL_ID)) showBubble();
        return;
      }
      if (!document.getElementById(PANEL_ID)) createPanel(cachedTab);
    };
    if (document.documentElement) restoreEarly();
    else document.addEventListener("DOMContentLoaded", restoreEarly, { once: true });

    // (2) Đối chiếu với chrome.storage (per-tab, chuẩn hơn) + lấy tabId thật.
    try {
      chrome.runtime.sendMessage({ action: "getTabId" }, (r) => {
        if (chrome.runtime.lastError) return;
        CURRENT_TAB_ID = r?.tabId ?? "";
        sessSet(SS_TAB, String(CURRENT_TAB_ID));
        // Đọc CẢ cờ panel-open LẪN trạng thái fill-all. Cổng này reload kiểu reset sessionStorage ở nhiều
        // nhịp → SS_FILLALL có thể mất; nhưng FILLALL_STATE_KEY (chrome.storage) sống suốt phiên → dùng nó
        // làm chốt chặn mount panel (nếu chỉ dựa sessionStorage thì nhịp sau panel sẽ hiện lại).
        chrome.storage.local.get([panelOpenKey(), panelMinKey(), panelAutoMinKey(), FILLALL_STATE_KEY,
          ATTACHALL_STATE_KEY, ENTERPRISE_FILLALL_STATE_KEY], (res) => {
          if (chrome.runtime.lastError) return;
          const fillSt = res && res[FILLALL_STATE_KEY];
          const attachSt = (res && res[ATTACHALL_STATE_KEY]) || (res && res[ENTERPRISE_FILLALL_STATE_KEY]);
          if (sessGet(SS_FILLALL) === "1" || fillSt || attachSt) {
            // Đang chạy fill-all / đính-kèm nhiều bước → không mount panel; giữ cờ sync + banner cho nhịp sau.
            if (fillSt || attachSt) {
              sessSet(SS_FILLALL, "1");
              if (fillSt && typeof fillSt.step === "number" && Array.isArray(fillSt.order)) {
                setFillAllProgress(fillSt.step + 1, fillSt.order.length, "");
              } else if (attachSt && !document.getElementById(FILLALL_BANNER_ID)) {
                showFillAllProgress("Đang đính kèm hồ sơ...");
              } else if (!document.getElementById(FILLALL_BANNER_ID)) {
                showFillAllProgress("Đang xử lý...");
              }
            }
            return;
          }
          const openByStore = res && res[panelOpenKey()];
          const openBySess = sessGet(SS_OPEN) === "1";
          if (!(openByStore || openBySess)) return;
          const storedAutoMin = normalizeAutoMinState(res && res[panelAutoMinKey()]);
          if (storedAutoMin) sessSet(SS_AUTO_MIN, JSON.stringify(storedAutoMin));
          else if (res && res[panelAutoMinKey()]) clearAutoMinState();
          // Đang thu nhỏ (per-tab qua chrome.storage, chuẩn hơn sessionStorage vốn có thể bị reset) → giữ bubble,
          // không mount panel full. sessionStorage đồng bộ lại để nhánh restoreEarly nhịp sau cũng biết.
          if ((res && res[panelMinKey()]) || sessGet(SS_MIN) === "1") {
            sessSet(SS_MIN, "1");
            // Nếu nhánh đồng bộ lỡ dựng panel full (hiếm: SS_MIN mất mà SS_OPEN còn) → thu lại về bubble.
            if (document.getElementById(PANEL_ID)) minimizePanel({ preserveAuto: true });
            else showBubble();
            maybeRestorePanelForAttachment();
            return;
          }
          if (!document.getElementById(PANEL_ID)) createPanel(CURRENT_TAB_ID);
        });
      });
    } catch (e) { /* ignore */ }
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " ");

  // Fill-tất-cả-8-trang: mỗi lần trang load lại (sau Lưu/điều hướng), nếu đang có phiên thì chạy bước kế.
  if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_FILLALL_RESUMED__) {
    window.__AUTOFILL_HCC_FILLALL_RESUMED__ = true;
    let resumeTimer = null;
    const resume = () => {
      // DOMContentLoaded và pageshow cùng có thể chạy trên navigation thường. Debounce để chỉ có
      // một step; pageshow còn cứu trường hợp document ngành nghề được khôi phục từ bfcache.
      if (resumeTimer) clearTimeout(resumeTimer);
      resumeTimer = setTimeout(() => {
        if (typeof H.getFillAllState === "function" && typeof H.stepFillAll === "function") {
          H.getFillAllState().then((st) => {
            if (!st) return;
            console.log("[FillAll] auto-resume", st.step, st.phase, st.pendingIndustryDelete || "");
            Promise.resolve(H.stepFillAll()).catch((error) => {
              console.error("[FillAll] auto-resume lỗi:", error);
            });
          });
        }
        // Phiên đính kèm hộ kinh doanh cũng resume qua từng postback.
        if (typeof H.getAttachAllState === "function" && typeof H.stepAttachAll === "function") {
          H.getAttachAllState().then((st) => { if (st) H.stepAttachAll(); });
        }
      }, 600);
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", resume, { once: true });
    } else {
      setTimeout(resume, 0); // defer để const/hàm bên dưới đã khởi tạo (tránh TDZ)
    }
    window.addEventListener("pageshow", resume);
  }

  const SPLIT_RELOADABLE_WALLET_CODES = new Set([
    "wallet-stale-modal",
    "wallet-modal-not-opened",
    "wallet-device-upload-not-opened",
  ]);
  const SPLIT_MAX_RELOADS_PER_WALLET_CODE = 3;

  function isSplitReloadableWalletError(code) {
    return SPLIT_RELOADABLE_WALLET_CODES.has(String(code || ""));
  }

  // ===== Tách hồ sơ (split): tab hồ sơ mới tự đính bundle file từ background khi tới Bước 3 =====
  // Trang nộp hồ sơ reload/chuyển bước → content script chạy lại; mỗi lần load kiểm tra pending của tab.
  // Portal React (cổng mới): tab mới dừng ở "Thông tin chủ hồ sơ" → tự bấm "Bước tiếp theo" để qua
  // trang đính kèm. Chỉ bấm đúng ở bước này và chỉ tính retry khi DOM thực sự KHÔNG chuyển bước.
  // eForm cũ KHÔNG có nút này (data-e2e/id không khớp) → no-op, giữ nguyên hành vi user tự điều hướng.
  if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_SPLIT_POLLER__) {
    window.__AUTOFILL_HCC_SPLIT_POLLER__ = true;
    try {
      chrome.runtime.sendMessage({ action: "getPendingAttach" }, (res) => {
        if (chrome.runtime.lastError) return;
        const pending = res?.pending;
        const pendingFiles = Array.isArray(pending?.files) && pending.files.length
          ? pending.files
          : (pending?.file ? [pending.file] : []);
        const pendingAttachments = Array.isArray(pending?.attachments) && pending.attachments.length
          ? pending.attachments
          : (pending?.planItem ? [pending.planItem] : []);
        if (!pendingFiles.length || !pendingAttachments.length) return;
        let deadline = Date.now() + 5 * 60 * 1000; // hết hạn 5 phút ACTIVE để tránh poll vô tận
        let busy = false;
        let terminal = false;
        let hiddenSince = null;
        let nextFailures = 0;
        const maxNextFailures = 5;
        const recoveryBaseKey = `__af_split_attach_reload_${pending.ts || "legacy"}`;
        const recoveryTotalKey = `${recoveryBaseKey}_total`;
        const ownerStepPresent = () => Array.from(document.querySelectorAll("h1, h2, h3")).some((heading) =>
          isVisible(heading) && foldedNodeText(heading).includes("thong tin chu ho so")
        );
        const findOwnerNextButton = () => {
          if (!ownerStepPresent()) return null;
          return Array.from(document.querySelectorAll(
            'button[id^="kt_buoc-tiep-theo"], button[data-e2e="btn-next"]'
          )).find((btn) =>
            !btn.disabled && btn.getAttribute("aria-disabled") !== "true" && isVisible(btn)
          ) || null;
        };
        const clickNextAndVerify = async () => {
          const btn = findOwnerNextButton();
          if (!btn) return { attempted: false, advanced: false };
          const beforeUrl = location.href;
          btn.scrollIntoView({ block: "center", inline: "center" });
          btn.focus?.();
          btn.click(); // một click logic; không phát chuỗi event kép lên nút submit của React
          const advanced = await waitFor(() =>
            location.href !== beforeUrl ||
            !ownerStepPresent() ||
            hasAttachmentTarget(),
            4000,
            120
          );
          return { attempted: true, advanced: !!advanced };
        };
        const recoveryKeyForCode = (code) =>
          `${recoveryBaseKey}_${String(code || "unknown").replace(/[^a-z0-9_-]+/gi, "_")}`;
        const splitReloadCount = (code) => {
          try { return Number.parseInt(sessionStorage.getItem(recoveryKeyForCode(code)) || "0", 10) || 0; }
          catch (_) { return 0; }
        };
        const splitReloadTotal = () => {
          try { return Number.parseInt(sessionStorage.getItem(recoveryTotalKey) || "0", 10) || 0; }
          catch (_) { return 0; }
        };
        const markSplitReload = (code) => {
          try {
            sessionStorage.setItem(recoveryKeyForCode(code), String(splitReloadCount(code) + 1));
            sessionStorage.setItem(recoveryTotalKey, String(splitReloadTotal() + 1));
            return true;
          } catch (_) {
            return false; // không reload nếu không lưu được guard, tránh reload vô hạn
          }
        };
        const seedInitialSplitReload = () => {
          const code = String(pending?.recoveryCode || "");
          const count = Number.parseInt(String(pending?.recoveryCount || "0"), 10) || 0;
          if (!isSplitReloadableWalletError(code) || count <= 0) return;
          try {
            // Tab đầu tiên đã reload một lượt để chuyển từ popup sang state machine. Seed guard để
            // tổng số reload của chính trạng thái treo này vẫn bị chặn ở mức 3 như các tab mới.
            if (splitReloadCount(code) < count) {
              sessionStorage.setItem(recoveryKeyForCode(code), String(count));
            }
            if (splitReloadTotal() < count) {
              sessionStorage.setItem(recoveryTotalKey, String(count));
            }
          } catch (_) { /* guard chỉ là cơ chế chống lặp; lỗi storage thì tick sẽ tự dừng an toàn */ }
        };
        const clearSplitReloadGuards = () => {
          try {
            sessionStorage.removeItem(recoveryBaseKey); // dọn guard của bản extension cũ
            sessionStorage.removeItem(recoveryTotalKey);
            for (const code of SPLIT_RELOADABLE_WALLET_CODES) {
              sessionStorage.removeItem(recoveryKeyForCode(code));
            }
          } catch (_) { /* ignore */ }
        };
        const finishPendingAttach = (ok, details = {}) => {
          if (terminal) return;
          terminal = true;
          if (ok) showPageToast("Đã đính kèm xong hồ sơ.", "success");
          if (!ok && details.code === "wallet-file-not-persisted") {
            showPageToast("Cổng chưa nhận file sau 2 lần thử. Hàng đợi đã dừng tại hồ sơ này.", "warn");
            chrome.runtime.sendMessage({
              action: "pausePendingAttach",
              code: details.code,
              error: details.error || null,
            });
            return;
          }
          chrome.runtime.sendMessage({
            action: ok ? "clearPendingAttach" : "failPendingAttach",
            code: details.code || null,
            error: details.error || null,
          });
        };
        seedInitialSplitReload();
        const tick = async () => {
          if (terminal) return;
          // Chrome và React throttle tab nền; tuyệt đối không click modal hoặc tiêu retry khi tab ẩn.
          // Queue background luôn activate đúng một tab, còn người dùng chuyển tay thì tiến trình tạm dừng.
          if (document.hidden) {
            if (!hiddenSince) hiddenSince = Date.now();
            setTimeout(tick, 500);
            return;
          }
          if (hiddenSince) {
            deadline += Date.now() - hiddenSince;
            hiddenSince = null;
          }
          if (Date.now() > deadline) {
            finishPendingAttach(false, { code: "split-timeout", error: "Hết thời gian chờ trang đính kèm sẵn sàng." });
            return;
          }
          if (!busy && typeof hasAttachmentTarget === "function" && hasAttachmentTarget()) {
            busy = true; // TỚI BƯỚC 3 → tự đính toàn bộ bundle theo kế hoạch STT1/STT2
            try {
              const r = await attachFilesByPlan(pendingFiles, pendingAttachments, pending.procedure || "", { mode: "split" });
              // Không coi kết quả đính một phần là thành công: chứng thực chữ ký phải đủ cả STT1 và STT2.
              if (r?.ok && !r?.error) {
                clearSplitReloadGuards();
                finishPendingAttach(true);
                return;
              }
              if (isSplitReloadableWalletError(r?.code)) {
                // Cổng React đôi khi cần nhiều hơn một lượt khởi tạo lại. Cho mỗi trạng thái treo reload
                // tối đa 3 lần, đồng thời giữ trần tổng 9 lần cho cả pending để không tạo vòng lặp vô hạn.
                const maxReloadTotal = SPLIT_RELOADABLE_WALLET_CODES.size * SPLIT_MAX_RELOADS_PER_WALLET_CODE;
                if (
                  splitReloadCount(r.code) < SPLIT_MAX_RELOADS_PER_WALLET_CODE &&
                  splitReloadTotal() < maxReloadTotal
                ) {
                  if (markSplitReload(r.code)) {
                    console.warn(`[AutoFill-Split] Ví tài liệu bị treo (${r.code}), reload để cổng khởi tạo lại trạng thái này.`);
                    location.reload();
                  } else {
                    console.warn("[AutoFill-Split] Không lưu được reload guard; dừng để tránh vòng lặp.");
                    finishPendingAttach(false, { code: r.code, error: r.error || "Không lưu được reload guard." });
                  }
                  return;
                }
                console.warn(`[AutoFill-Split] Trạng thái ${r.code} vẫn lỗi sau reload; dừng để tránh vòng lặp.`, r.error);
                finishPendingAttach(false, { code: r.code, error: r.error });
                return;
              }
              if (r?.error) {
                console.warn("[AutoFill-Split] Đính kèm lỗi terminal; chuyển sang tab kế tiếp.", r.error);
                finishPendingAttach(false, { code: r.code || "attach-failed", error: r.error });
                return;
              }
            } catch (e) { /* thử lại vòng sau */ }
            busy = false;
          } else if (!busy && nextFailures < maxNextFailures && ownerStepPresent()) {
            busy = true;
            const step = await clickNextAndVerify();
            busy = false;
            if (step.attempted && !step.advanced) {
              nextFailures++;
              console.warn(`[AutoFill-Split] Bước tiếp theo chưa chuyển trang (${nextFailures}/${maxNextFailures}).`);
            }
            if (step.advanced) {
              setTimeout(tick, 500);
              return;
            }
            if (nextFailures >= maxNextFailures) {
              console.warn("[AutoFill-Split] Dừng retry Bước tiếp theo sau nhiều lần trang không chuyển.");
              finishPendingAttach(false, {
                code: "owner-next-not-advanced",
                error: "Nút Bước tiếp theo không chuyển sang trang đính kèm.",
              });
              return;
            }
          }
          setTimeout(tick, 1200);
        };
        tick();
      });
    } catch (e) { /* ignore */ }
  }

  function detectFormKind() {
    // Cổng Bắc Ninh (Liferay) có field portlet đặc trưng `_org_bn_hoso_noptructuyen_*` —
    // prefix chỉ cổng này dùng → nhận diện chắc chắn, ưu tiên trước "standard" (cũng có input[name]).
    if (document.querySelectorAll('[name^="_org_bn_hoso_noptructuyen_"]').length >= 3) return "bacninh";
    // Trang HOÀN THIỆN TÀI KHOẢN VNeID (/vneidsso) — portlet khác (`_taikhoan_sso_vneid_`), cùng engine
    // fill-bacninh.js (nhánh fillAccountBacNinh khớp NAME suffix). Cùng "bacninh" để dùng chung dispatch.
    if (document.querySelectorAll('[name*="_taikhoan_sso_vneid_"]').length >= 3) return "bacninh";
    // Cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn) — Angular Material bọc trong custom element `liz-*`,
    // DOM strip HẾT formcontrolname → engine riêng fill-liz.js khớp theo (.group-header, mat-label).
    // Nhận diện bằng liz-form-component (prefix riêng cổng này) + không có formcontrolname → không đụng
    // nhánh "angular" bên dưới (nhánh đó cần formcontrolname).
    if (
      document.querySelectorAll("liz-form-component, liz-input, liz-datepicker, liz-select").length >= 3 &&
      document.querySelectorAll("[formcontrolname]").length === 0
    ) return "liz";
    const ngCount = document.querySelectorAll("[formcontrolname]").length;
    const legacyCount = document.querySelectorAll("x-input, x-date, x-radio").length;
    const standardCount = document.querySelectorAll(
      "#form-content input[name], #form-content select[name], #form-content textarea[name], " +
      "form input[name], form select[name], form textarea[name], " +
      ".form-wrapper input[name], .form-wrapper select[name], .form-wrapper textarea[name]"
    ).length;
    if (ngCount >= 3) return "angular";
    if (legacyCount >= 3) return "legacy";
    if (standardCount >= 3) return "standard";
    return "";
  }

  // Khỏi cần user bấm chọn trang. Trả { pageKey, label }; pageKey=null nếu không nhận ra.

  // ===== FILL TẤT CẢ 8 TRANG đăng ký kinh doanh (fill → Lưu → sang trang, tự lặp qua reload) =====
  // Cổng ASP.NET reload sau MỖI lần Lưu/điều hướng → không thể lặp trong 1 context. State máy được
  // lưu ở chrome.storage.local, mỗi lần content script load lại thì chạy tiếp 1 bước.
  const BUSINESS_PAGE_ORDER = [
    "hinh-thuc-dang-ky", "dia-chi", "nganh-nghe-kinh-doanh", "ten-ho-kinh-doanh",
    "chu-ho-kinh-doanh", "thong-tin-ve-von", "thong-tin-ve-thue", "nguoi-nop-ho-so",
  ];

  // readAcctContact: đọc sđt/email tài khoản (span _Vw chế độ xem, fallback input). Dùng bởi business-registration.js.
  function readAcctContact(baseId) {
    const vw = ((document.getElementById(baseId + "_Vw") || {}).textContent || "").trim();
    if (vw) return vw;
    const inp = document.getElementById(baseId);
    return ((inp && inp.value) || "").trim();
  }

  function hasFillableForm() {
    return !!detectFormKind();
  }

  function hasAttachmentTarget() {
    return !!(
      document.querySelector('input[type="file"][name*="filethanhPhanHoSo"]') || // cổng Bắc Ninh
      findCopyCertificationAttachmentRow() ||
      findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"]) ||
      fixedSlotUploadInputs().length > 0 // cổng Bộ VHTTDL: input file trong <app-upload-flie-multi> (nút icon, không chữ "Chọn tệp")
    );
  }

  const ATTACHMENT_STEP_SNIPPETS = ["thanh phan ho so", "ho so kem theo"];

  // Một số cổng Angular (Ninh Bình...) render SẴN input[type=file] của mọi bước trong DOM.
  // Vì vậy sự tồn tại của input chỉ đủ cho engine đính kèm, nhưng KHÔNG đủ để tự bung panel sau fill.
  // Nếu stepper có bước hồ sơ đính kèm thì chỉ tin đúng bước đang aria-selected=true.
  function activeAttachmentStepState() {
    const headers = Array.from(document.querySelectorAll(
      'mat-step-header[role="tab"], [role="tab"][aria-controls^="cdk-step-content-"]'
    ));
    const attachmentHeaders = headers.filter((header) => {
      const text = foldedNodeText(header);
      return ATTACHMENT_STEP_SNIPPETS.some((snippet) => text.includes(snippet));
    });
    if (!attachmentHeaders.length) return null;
    return attachmentHeaders.some((header) =>
      header.getAttribute("aria-selected") === "true" && isVisible(header)
    );
  }

  function attachmentInputHasVisibleScope(input) {
    if (!input) return false;
    if (isVisible(input)) return true;
    // Native file input thường bị ẩn, còn hàng/nút upload mới là phần cán bộ nhìn thấy.
    const scope = input.closest?.(
      "tr, li, .form-group, .input-group, app-upload-flie-multi, [class*='upload']"
    );
    return !!scope && isVisible(scope);
  }

  function hasVisibleAttachmentTarget() {
    const stepState = activeAttachmentStepState();
    if (stepState === false) return false;
    // Bước "Thành phần hồ sơ" đang active là bằng chứng mạnh; native input có thể bị CSS ẩn.
    if (stepState === true) return hasAttachmentTarget();

    const copyRow = findCopyCertificationAttachmentRow();
    if (copyRow && isVisible(copyRow)) return true;
    if (findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"])) return true;
    const inputs = [
      ...document.querySelectorAll('input[type="file"][name*="filethanhPhanHoSo"]'),
      ...fixedSlotUploadInputs(),
    ];
    return inputs.some(attachmentInputHasVisibleScope);
  }

  function maybeRestorePanelForAttachment() {
    if (!IS_TOP_FRAME || location.hostname.includes("hokinhdoanh.dkkd.gov.vn")) return false;
    const state = readAutoMinState();
    // phase=filling chặn observer bật panel lại do chính thao tác điền làm DOM thay đổi.
    if (!state || state.phase !== "filled" || !hasVisibleAttachmentTarget()) return false;
    restorePanel(); // đồng thời xoá cờ → chỉ tự mở đúng một lần
    return true;
  }

  // SPA có thể đưa màn đính kèm vào DOM mà không reload. Quan sát nhẹ, debounce và chỉ làm việc khi
  // đang có cờ after-fill; thu nhỏ thủ công không tạo cờ nên hoàn toàn không bị ảnh hưởng.
  if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_ATTACH_REOPEN_WATCH__) {
    window.__AUTOFILL_HCC_ATTACH_REOPEN_WATCH__ = true;
    let attachReopenTimer = null;
    const scheduleAttachmentReopen = () => {
      if (!readAutoMinState()) return;
      if (attachReopenTimer) clearTimeout(attachReopenTimer);
      attachReopenTimer = setTimeout(() => {
        attachReopenTimer = null;
        maybeRestorePanelForAttachment();
      }, 250);
    };
    const startAttachmentReopenWatch = () => {
      scheduleAttachmentReopen();
      const observer = new MutationObserver(scheduleAttachmentReopen);
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "hidden", "style"],
      });
    };
    if (document.documentElement) startAttachmentReopenWatch();
    else document.addEventListener("DOMContentLoaded", startAttachmentReopenWatch, { once: true });
  }

  async function waitFor(fn, timeout = 3000, interval = 100) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const v = fn();
      if (v) return v;
      await sleep(interval);
    }
    return null;
  }

  const COPY_CERT_ATTACHMENT_SNIPPETS = [
    "ban chinh giay to",
    "co so de chung thuc ban sao",
    "ban sao can chung thuc",
  ];

  function nodeText(el) {
    return String(el?.textContent || "").replace(/\s+/g, " ").trim();
  }

  // Tín hiệu để popup tự nhận diện thủ tục theo trang: URL + các heading (tên thủ tục).
  function collectProcedureSignals() {
    const headings = [];
    const visibleHeadings = [];
    const seen = new Set();
    const push = (raw, visible = false) => {
      const s = String(raw || "").replace(/\s+/g, " ").trim();
      if (s.length >= 6 && s.length <= 250 && !seen.has(s)) {
        seen.add(s);
        headings.push(s);
        if (visible) visibleHeadings.push(s);
      }
    };
    // Heading chuẩn của eForm hộ tịch/chứng thực (moj) = đúng tên thủ tục; kèm h1/h2 dự phòng.
    document.querySelectorAll(".text-2xl.font-bold, h1, h2")
      .forEach((el) => push(nodeText(el), isVisible(el)));
    // Văn bản hiển thị (cắt ngắn) — để nhận diện cổng SPA không có heading (vd laichau): khớp tên thủ tục.
    const bodyText = String(document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 6000);
    // HkdOnline có cùng URL/domain cho nhiều loại hồ sơ. Hint dựa vào marker của ACTIVE wizard step
    // và loại hồ sơ đang hiển thị, tránh suy thủ tục chỉ vì tên option xuất hiện trong body.
    const businessProcedureHint = typeof H.detectBusinessProcedureHint === "function"
      ? H.detectBusinessProcedureHint() : "";
    // Cổng ĐKKD qua mạng (dangkyquamang) cũng dùng chung domain/URL cho mọi loại hình doanh nghiệp.
    // Hint chỉ nói "đang ở cổng doanh nghiệp, bước nào" để popup không giữ nhầm thủ tục hộ kinh doanh.
    const enterpriseProcedureHint = typeof H.detectEnterpriseProcedureHint === "function"
      ? H.detectEnterpriseProcedureHint() : "";
    // Loại hình đọc từ chính hồ sơ đang mở ("Loại hình doanh nghiệp: Công ty cổ phần") — thứ duy
    // nhất phân biệt được CTCP với TNHH/DNTN/hợp danh trên cùng domain.
    const enterpriseEntityLabel = typeof H.detectEnterpriseEntityLabel === "function"
      ? H.detectEnterpriseEntityLabel() : "";
    return {
      url: location.href,
      title: document.title || "",
      headings,
      visibleHeadings,
      bodyText,
      businessProcedureHint,
      enterpriseProcedureHint,
      enterpriseEntityLabel,
    };
  }

  // Danh tính tài khoản VNeID đang đăng nhập TRÊN CỔNG (để gắn consent theo người + thủ tục).
  // CHỈ quét trong VÙNG TÀI KHOẢN (neo theo link định danh / #account_name) — KHÔNG quét cả trang, vì
  // biểu mẫu cũng có số định danh của NGƯỜI NỘP (vd 036192014693) sẽ bị vớ nhầm. Đọc không ra → trả
  // {cccd:null} → popup rơi về fallback "mã phiên + thủ tục". Không bao giờ throw.
  function extractPortalPrincipal() {
    const CCCD_RE = /(?<!\d)\d{12}(?!\d)/; // số định danh = đúng 12 chữ số (điện thoại 10 số không dính)
    let cccd = null;
    let name = null;
    try {
      // moj (dichvucongnganhtuphap.moj.gov.vn): drawer tài khoản có link "thong-tin-dinh-danh"/"ho-so-ca-nhan".
      // Neo vào link rồi leo lên ancestor GẦN NHẤT có <h3> (khối hồ sơ: tên + CCCD) — không leo tới body.
      const idLink = document.querySelector(
        'a[href*="thong-tin-dinh-danh"], a[href*="ho-so-ca-nhan"], a[href*="thong-tin-tai-khoan"]'
      );
      if (idLink) {
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
      // Angular (Lâm Đồng/Lai Châu…): #account_name CHỈ có tên (không CCCD) → dùng cho bằng chứng, gate rơi phiên.
      if (!name) {
        const el = document.querySelector("#account_name");
        if (el) {
          const t = String(el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
          if (t && !/\d{6,}/.test(t)) name = t;
        }
      }
    } catch (e) {
      /* cổng lạ / DOM đổi → trả null, không chặn luồng */
    }
    return { cccd: cccd || null, name: name || null, host: location.hostname };
  }

  function foldedNodeText(el) {
    return foldChoiceText(nodeText(el));
  }

  function textContainsAll(el, snippets) {
    const text = foldedNodeText(el);
    return snippets.every((snippet) => text.includes(snippet));
  }

  function findButtonByText(root, labels) {
    const wants = labels.map((label) => foldChoiceText(label));
    return Array.from(root.querySelectorAll("button")).find((button) => {
      if (!isVisible(button)) return false;
      const text = foldedNodeText(button);
      return wants.some((want) => text === want || text.includes(want));
    }) || null;
  }

  function findButtonsByText(root, labels) {
    const wants = labels.map((label) => foldChoiceText(label));
    return Array.from(root.querySelectorAll("button")).filter((button) => {
      if (!isVisible(button) || button.disabled) return false;
      const text = foldedNodeText(button);
      return wants.some((want) => text === want || text.includes(want));
    });
  }

  function shortText(value, max = 240) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? text.slice(0, max) + "..." : text;
  }

  function describeElementForLog(el) {
    if (!el) return null;
    const rect = el.getBoundingClientRect?.();
    return {
      tag: el.tagName,
      text: shortText(nodeText(el), 160),
      disabled: !!el.disabled,
      visible: isVisible(el),
      className: shortText(el.className, 160),
      id: el.id || "",
      name: el.getAttribute?.("name") || "",
      rect: rect ? {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
      } : null,
      html: shortText(el.outerHTML, 500),
    };
  }

  function describeAttachmentRowForLog(row) {
    if (!row) return null;
    const cells = Array.from(row.cells || []);
    return {
      componentName: shortText(attachmentComponentName(row), 240),
      attachedFile: shortText(rowAttachedFileName(row), 160),
      rowText: shortText(nodeText(row), 500),
      cellCount: cells.length,
      cells: cells.map((cell, index) => ({
        index,
        visible: isVisible(cell),
        text: shortText(nodeText(cell), 220),
        buttons: findButtonsByText(cell, ["Chọn tệp đính kèm", "Chọn tệp"]).map(describeElementForLog),
      })),
    };
  }

  function visibleDialogSnapshot() {
    return Array.from(document.querySelectorAll("[role='dialog']")).map((dialog, index) => ({
      index,
      visible: isVisible(dialog),
      state: dialog.getAttribute("data-state") || "",
      text: shortText(nodeText(dialog), 500),
    }));
  }

  function attachDebug(label, data = {}) {
    console.log(`[AutoFill-AttachPlan][debug] ${label}`, data);
  }

  function findDialogByText(label) {
    const want = foldChoiceText(label);
    return Array.from(document.querySelectorAll("[role='dialog']")).find((dialog) =>
      foldedNodeText(dialog).includes(want)
    ) || null;
  }

  function findDialogsByText(label) {
    const want = foldChoiceText(label);
    return Array.from(document.querySelectorAll("[role='dialog']")).filter((dialog) =>
      foldedNodeText(dialog).includes(want)
    );
  }

  function findLatestDialogByText(label) {
    const dialogs = findDialogsByText(label).filter(isVisible);
    return dialogs[dialogs.length - 1] || null;
  }

  function findCopyCertificationAttachmentRow() {
    const rows = Array.from(document.querySelectorAll("tr"));
    const matched = rows.find((row) =>
      textContainsAll(row, COPY_CERT_ATTACHMENT_SNIPPETS) &&
      (findAttachmentFileInput(row) || findAttachmentChooseButton(row))
    );
    if (matched) return matched;

    const button = findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"]);
    return button?.closest?.("tr") || null;
  }

  function isAddAttachmentRow(row) {
    return !!findButtonByText(row, ["Thêm thành phần hồ sơ"]);
  }

  function attachmentComponentName(row) {
    if (!row) return "";
    const cells = Array.from(row.cells || []);
    const cell = cells[1] || cells[0] || row;
    const clone = cell.cloneNode(true);
    clone.querySelectorAll("button, svg, input, textarea, select").forEach((node) => node.remove());
    const text = nodeText(clone)
      .replace(/\bBắt buộc\b/gi, "")
      .replace(/^Tên Hồ Sơ:\s*/i, "")
      .replace(/\s+/g, " ")
      .trim();
    if (text) return text;
    const input = findComponentNameInput(row);
    return String(input?.value || "").trim();
  }

  function hasAttachmentChooseControl(row) {
    return !!(
      findAttachmentChooseButton(row) ||
      findAttachmentFileInput(row)
    );
  }

  function findAttachmentCandidateRows() {
    return Array.from(document.querySelectorAll("tr")).filter((row) => {
      if (isAddAttachmentRow(row)) return false;
      return hasAttachmentChooseControl(row);
    });
  }

  function findAttachmentRows() {
    return findAttachmentCandidateRows().filter((row) => {
      const hasChooseButton = hasAttachmentChooseControl(row);
      const hasKnownComponent = !!attachmentComponentName(row);
      return hasChooseButton && hasKnownComponent;
    });
  }

  function componentTextMatches(row, componentName) {
    if (!row) return false;
    if (textContainsAll(row, COPY_CERT_ATTACHMENT_SNIPPETS)) return textContainsAll({ textContent: componentName }, COPY_CERT_ATTACHMENT_SNIPPETS);
    const rowText = foldChoiceText(attachmentComponentName(row));
    const want = foldChoiceText(componentName || "");
    if (!rowText || !want) return false;
    return rowText === want || rowText.includes(want) || want.includes(rowText);
  }

  function findAttachmentRowByComponent(componentName, componentIndex) {
    const rows = findAttachmentRows();
    if (componentIndex && rows[componentIndex - 1]) {
      const indexed = rows[componentIndex - 1];
      if (componentTextMatches(indexed, componentName) || textContainsAll(indexed, COPY_CERT_ATTACHMENT_SNIPPETS)) {
        return indexed;
      }
    }
    if (foldChoiceText(componentName || "").includes("ban chinh giay to")) {
      return findCopyCertificationAttachmentRow();
    }
    return rows.find((row) => componentTextMatches(row, componentName)) || null;
  }

  function collectAttachmentContext() {
    return {
      components: findAttachmentRows().map((row, index) => ({
        index: index + 1,
        componentName: attachmentComponentName(row),
        required: foldedNodeText(row).includes("bat buoc"),
        hasFile: !!nodeText(row.cells?.[2] || "").trim(),
      })),
    };
  }

  function fileExtension(name) {
    const match = String(name || "").match(/(\.[^.\s]+)$/);
    return match ? match[1] : "";
  }

  function safeAttachmentFileName(payload, documentName) {
    const ext = fileExtension(payload?.name);
    let base = String(documentName || "").trim() || attachmentDocumentName(payload);
    // documentName có thể ĐÃ kèm đuôi (vd "…đất.pdf") → bỏ đuôi trùng để KHÔNG thành "…đất.pdf.pdf".
    if (ext && base.toLowerCase().endsWith(ext.toLowerCase())) base = base.slice(0, -ext.length);
    return base + ext;
  }

  function dataUrlToFile(payload, documentName = "") {
    const dataUrl = String(payload?.dataUrl || "");
    const comma = dataUrl.indexOf(",");
    if (comma < 0) throw new Error(`File ${payload?.name || ""} không có dataUrl hợp lệ.`);
    const meta = dataUrl.slice(0, comma);
    const b64 = dataUrl.slice(comma + 1);
    const mime = (/^data:([^;,]+)/.exec(meta)?.[1]) || payload?.type || "application/octet-stream";
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new File([bytes], safeAttachmentFileName(payload, documentName), {
      type: mime,
      lastModified: Date.now(),
    });
  }

  function attachmentDocumentName(file) {
    const raw = String(file?.name || "tai-lieu")
      .replace(/\.[^.]+$/, "")
      .replace(/[^\p{L}\p{N}_\-\s]+/gu, " ")
      .replace(/\s+/g, " ")
      .trim();
    return (raw || "tai-lieu").slice(0, 50);
  }

  // Ô "Tên tài liệu" của Ví cá nhân / Danh sách tài liệu điện tử (cổng Đà Nẵng). Thực nghiệm: DẤU CÁCH và
  // CHỮ TIẾNG VIỆT CÓ DẤU đều được chấp nhận — chỉ DẤU CHẤM (kể cả đuôi ".pdf") mới gây "Tên tài liệu không
  // hợp lệ". → GIỮ nguyên chữ (kể cả có dấu), số, dấu cách, "_", "-"; chỉ bỏ đuôi file + loại dấu chấm và
  // ký tự lạ khác. KHÔNG fold dấu, KHÔNG đổi dấu cách thành "_".
  function walletSafeDocumentName(name) {
    const s = String(name || "")
      .replace(/\.[^.\s]+$/, "")               // bỏ đuôi file (.pdf, .jpg…)
      .replace(/[^\p{L}\p{N}_\-\s]+/gu, " ")   // giữ chữ (mọi ngôn ngữ), số, _, -, dấu cách; bỏ dấu chấm & ký tự khác
      .replace(/\s+/g, " ")
      .trim();
    return s.slice(0, 100) || "Tài liệu";
  }

  function setFilesOnInput(input, files, options = {}) {
    if (!input || !files.length) return false;
    if (files.length > 1 && options.allowMultiple !== false) {
      input.multiple = true;
      input.setAttribute("multiple", "");
    }
    const dt = new DataTransfer();
    files.forEach((file) => dt.items.add(file));
    const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "files");
    if (desc?.set) desc.set.call(input, dt.files);
    else input.files = dt.files;
    // Một số form (vd Hỗ trợ mai táng) đọc xong sẽ RESET input.files về rỗng để cho phép
    // chọn lại cùng file → check sau dispatch sẽ thành false-negative. Chốt kết quả gán ở đây.
    const assigned = !!(input.files && input.files.length === files.length);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    if (options.assumeConsumed) return assigned;
    return input.files && input.files.length === files.length;
  }

  function markAttachmentResult(target, ok) {
    injectAutofillStyles();
    if (ok) markFilled(target);
    else markUnfilled(target);
  }

  async function attachFilesToInput(input, payloadFiles, markTarget, method) {
    const files = payloadFiles.map(dataUrlToFile);
    const ok = setFilesOnInput(input, files);
    await sleep(500);
    markAttachmentResult(markTarget || input?.parentElement || input, ok);
    if (!ok) {
      return {
        error: `Không gắn được file vào input đính kèm (${method}).`,
        attached: 0,
        fileNames: files.map((file) => file.name),
      };
    }
    return {
      ok: true,
      method,
      attached: files.length,
      fileNames: files.map((file) => file.name),
    };
  }

  function findWalletUploadDoneButton(dialog) {
    return Array.from(dialog.querySelectorAll("button")).find((button) => {
      if (!isVisible(button) || button.disabled) return false;
      const text = foldedNodeText(button);
      if (
        text.includes("chon lai") ||
        text.includes("tai len tu thiet bi") ||
        text.includes("tao tep") ||
        text.includes("ky so") ||
        text.includes("quay lai")
      ) {
        return false;
      }
      return (
        text.includes("them vao vi") ||
        text.includes("tai len & chon") ||
        text.includes("tai len va chon") ||
        text === "chon"
      );
    }) || null;
  }

  async function ensureWalletDocumentName(dialog, documentName) {
    const input = await waitFor(() => dialog.querySelector('input[name="documentName"]'), 8000, 100);
    if (!input) return false;
    // Ô này chỉ nhận [chữ cái, số, _, -] → phải làm sạch (bỏ đuôi file, khoảng trắng, dấu). Fallback cũ
    // "Tài liệu chứng thực" có dấu cách nên cũng không hợp lệ → dùng walletSafeDocumentName.
    const safeName = walletSafeDocumentName(documentName);
    setNativeValue(input, safeName, { typing: true, commit: true });
    await sleep(150);
    return true;
  }

  async function waitForUploadCompletion(dialog, previousText) {
    const completed = await waitFor(() => {
      const doneButton = findWalletUploadDoneButton(dialog);
      if (!doneButton) return true;
      if (!document.documentElement.contains(dialog)) return true;
      const text = foldedNodeText(doneButton);
      return !text.includes("dang tai len") && !doneButton.disabled && text !== previousText;
    }, 20000, 150);
    return !!completed;
  }

  async function waitForWalletDialogClosed(dialog) {
    const closed = await waitFor(() =>
      !document.documentElement.contains(dialog) ||
      dialog.getAttribute("data-state") === "closed" ||
      !isVisible(dialog),
      12000,
      100
    );
    return !!closed;
  }

  function findLatestDialog() {
    const dialogs = Array.from(document.querySelectorAll("[role='dialog']")).filter(isVisible);
    return dialogs[dialogs.length - 1] || null;
  }

  function findDialogCloseButton(dialog) {
    return Array.from(dialog.querySelectorAll("button")).find((button) => {
      const text = foldedNodeText(button);
      return text === "close" || text.includes("close") || text === "x" || !!button.querySelector("svg.lucide-x");
    }) || null;
  }

  async function closeDocumentWalletDialogs() {
    const dialogs = findDialogsByText("Danh sách tài liệu điện tử").filter(isVisible);
    for (const dialog of dialogs.reverse()) {
      const closeButton = findDialogCloseButton(dialog);
      if (closeButton) closeButton.click();
      else document.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
      await sleep(250);
    }
    const closed = await waitFor(() => !findLatestDialogByText("Danh sách tài liệu điện tử"), 3000, 100);
    return !!closed;
  }

  function walletDeviceUploadState(previousDialog) {
    // React có thể thay toàn bộ node Radix dialog khi chuyển từ danh sách ví sang form upload.
    // Luôn đọc lại modal đang sống; không giữ cứng node trước khi click.
    const liveDialog = findLatestDialogByText("Danh sách tài liệu điện tử") ||
      (previousDialog && document.documentElement.contains(previousDialog) && isVisible(previousDialog)
        ? previousDialog
        : findLatestDialog());
    if (!liveDialog) return { dialog: null, input: null };
    const input = liveDialog.querySelector("#upload-container input[type='file']") ||
      liveDialog.querySelector("input[type='file']");
    return { dialog: liveDialog, input };
  }

  async function openWalletDeviceUpload(previousDialog) {
    let lastButton = null;
    for (let attempt = 0; attempt < 2; attempt++) {
      const initial = walletDeviceUploadState(previousDialog);
      if (initial.input) return { ...initial, button: lastButton };
      const liveDialog = initial.dialog;
      if (!liveDialog) break;

      const button = findButtonByText(liveDialog, ["Tải lên từ thiết bị"]);
      if (!button || button.disabled || button.getAttribute("aria-disabled") === "true") break;
      lastButton = button;
      button.scrollIntoView?.({ block: "center", inline: "center" });
      button.focus?.();
      button.click();

      const opened = await waitFor(() => {
        const state = walletDeviceUploadState(liveDialog);
        return state.input ? state : null;
      }, attempt === 0 ? 2500 : 4000, 100);
      if (opened) return { ...opened, button };
      await sleep(attempt === 0 ? 300 : 0);
    }

    const finalState = walletDeviceUploadState(previousDialog);
    return { ...finalState, button: lastButton };
  }

  function findComponentNameInput(root) {
    const controls = Array.from(root.querySelectorAll("input:not([type='hidden']):not([type='file']), textarea"))
      .filter((el) => isVisible(el) && !el.disabled && el.getAttribute("name") !== "documentName");
    const preferred = controls.find((el) => {
      const box = el.closest(".space-y-2, .form-group, label, div") || el.parentElement || el;
      const text = foldChoiceText(
        [
          el.getAttribute("name"),
          el.getAttribute("placeholder"),
          el.getAttribute("aria-label"),
          nodeText(box),
        ].filter(Boolean).join(" ")
      );
      return text.includes("thanh phan") || text.includes("ten ho so") || text.includes("ten tai lieu");
    });
    return preferred || controls[0] || null;
  }

  function findComponentNameInputs(root) {
    return Array.from(root.querySelectorAll("input:not([type='hidden']):not([type='file']), textarea"))
      .filter((el) => !el.disabled && el.getAttribute("name") !== "documentName");
  }

  async function fillAttachmentComponentName(row, componentName) {
    const inputs = findComponentNameInputs(row);
    if (!inputs.length) return false;
    for (const input of inputs) {
      setNativeValue(input, componentName, { typing: true, commit: true });
    }
    await sleep(250);
    return true;
  }

  function findReusableBlankAttachmentRow() {
    return findAttachmentCandidateRows().find((row) =>
      !attachmentComponentName(row) && findComponentNameInput(row)
    ) || null;
  }

  function componentNameForAppendedFile(planItem = {}, payloadFile = {}) {
    const componentName = String(planItem.componentName || "").trim();
    if (componentName && !isCopyCertificationDefaultComponentName(componentName)) return componentName;
    return String(planItem.detectedType || planItem.documentName || attachmentDocumentName(payloadFile) || "Tài liệu chứng thực").trim();
  }

  function isCopyCertificationDefaultComponentName(value) {
    return foldChoiceText(value || "").includes("ban chinh giay to");
  }

  function rowAttachedFileName(row) {
    if (!row) return "";
    const cells = Array.from(row?.cells || []);
    const attachCell = cells[2] || row;
    if (!attachCell) return "";
    const clone = attachCell.cloneNode(true);
    clone.querySelectorAll("button, svg, input, textarea, select").forEach((node) => node.remove());
    const text = nodeText(clone);
    if (!text || foldChoiceText(text).includes("chon tep")) return "";
    return text;
  }

  function rowHasAttachedFile(row) {
    return !!rowAttachedFileName(row);
  }

  function liveAttachmentRowForVerification(row, planItem = {}) {
    if (row && document.documentElement.contains(row)) return row;
    const componentName = planItem?.componentName || "";
    const componentIndex = planItem?.componentIndex || null;
    return findAttachmentRowByComponent(componentName, componentIndex) ||
      (Number(componentIndex) === 1 ? findCopyCertificationAttachmentRow() : null) ||
      null;
  }

  async function waitForPersistedAttachment(row, planItem = {}, previousName = "") {
    // Modal đóng chỉ chứng minh thao tác click đã chạy. Cổng React có thể đóng modal nhưng request
    // lưu file thất bại; chỉ tên file xuất hiện thật trên dòng hồ sơ mới là hậu điều kiện thành công.
    return await waitFor(() => {
      const liveRow = liveAttachmentRowForVerification(row, planItem);
      if (!liveRow) return null;
      const attachedName = rowAttachedFileName(liveRow);
      if (!attachedName || attachedName === previousName) return null;
      return { row: liveRow, fileName: attachedName };
    }, 12000, 150);
  }

  function attachmentTextKey(value) {
    return foldChoiceText(value || "")
      .replace(/\.(pdf|jpe?g|png|webp|xml|docx?|xlsx?|mp3|mp4|wav|mov)\b/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function attachmentKeyEquals(a, b) {
    const left = attachmentTextKey(a);
    const right = attachmentTextKey(b);
    return !!left && left === right;
  }

  function attachmentPlanLabels(planItem = {}, payloadFile = {}) {
    const componentName = String(planItem.componentName || "").trim();
    return uniqueElements([
      isCopyCertificationDefaultComponentName(componentName) ? "" : componentName,
      planItem.detectedType,
      planItem.documentName,
      componentNameForAppendedFile(planItem, payloadFile),
      attachmentDocumentName(payloadFile),
      payloadFile.name,
    ].filter(Boolean)).map(attachmentTextKey).filter(Boolean);
  }

  function findExistingAttachedRowForPlanItem(planItem = {}, payloadFile = {}) {
    const labels = attachmentPlanLabels(planItem, payloadFile);
    if (!labels.length) return null;
    const wantsNewComponent = planItem?.target === "new" || planItem?.needsAddComponent;
    const expectedNewComponent = wantsNewComponent ? componentNameForAppendedFile(planItem, payloadFile) : "";
    return findAttachmentRows().find((row) => {
      const attachedName = rowAttachedFileName(row);
      if (!attachedName) return false;
      const componentName = attachmentComponentName(row);
      if (wantsNewComponent) {
        // Thành phần động do extension tự đặt tên phải khớp chính xác. So kiểu chứa nhau sẽ
        // nhận nhầm các tên gần giống, ví dụ "CCCD ... HÒA" với "CCCD ... HOÀN".
        return attachmentKeyEquals(componentName, expectedNewComponent) &&
          labels.some((label) => attachmentKeyEquals(attachedName, label));
      }
      // Với các dòng cố định, tên thành phần hồ sơ thường là mô tả dài và có thể chứa
      // nhãn của dòng khác (vd dòng 1 có cụm "giao dịch đã được chứng thực"). Nếu dùng
      // componentName để bắt trùng, file của dòng 2 sẽ bị skip nhầm khi dòng 1 đã có file.
      // Tên file là định danh tài liệu, không phải nhãn component. Phải so chính xác để
      // "Giấy khai sinh" không nuốt "Giấy khai sinh 2" và HÒA không nuốt HOÀN.
      return labels.some((label) => attachmentKeyEquals(attachedName, label));
    }) || null;
  }

  function findEmptyAttachmentRowByComponent(componentName) {
    return findAttachmentRows().find((row) =>
      componentTextMatches(row, componentName) && !rowHasAttachedFile(row)
    ) || null;
  }

  function attachmentFileCell(row) {
    const cells = Array.from(row?.cells || []);
    return cells[2] || row || null;
  }

  function findAttachmentFileInput(row) {
    const attachCell = attachmentFileCell(row);
    return attachCell?.querySelector?.("input[type='file']") || null;
  }

  function findAttachmentChooseButtons(row) {
    const attachCell = attachmentFileCell(row);
    const fromAttachCell = attachCell ? findButtonsByText(attachCell, ["Chọn tệp đính kèm", "Chọn tệp"]) : [];
    if (fromAttachCell.length) return fromAttachCell;
    return row ? findButtonsByText(row, ["Chọn tệp đính kèm", "Chọn tệp"]) : [];
  }

  function findAttachmentChooseButton(row) {
    return findAttachmentChooseButtons(row)[0] || null;
  }

  function uniqueElements(items) {
    const seen = new Set();
    const result = [];
    for (const item of items) {
      if (!item || seen.has(item)) continue;
      seen.add(item);
      result.push(item);
    }
    return result;
  }

  function clickLikeUser(el) {
    if (!el) return;
    el.focus?.();
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      const ev = type.startsWith("pointer") && typeof PointerEvent === "function"
        ? new PointerEvent(type, { bubbles: true, cancelable: true, pointerType: "mouse", isPrimary: true })
        : new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
      el.dispatchEvent(ev);
    }
    el.click?.();
  }

  async function resolveLiveAttachmentRow(row, planItem = {}) {
    if (row && document.documentElement.contains(row)) return row;
    const componentName = planItem?.componentName || "";
    const componentIndex = planItem?.componentIndex || null;
    if (componentName || componentIndex) {
      const live = await waitFor(() =>
        findAttachmentRowByComponent(componentName, componentIndex),
        2500,
        100
      );
      if (live) return live;
    }
    return row || null;
  }

  async function openDocumentWalletForRow(row, planItem = {}) {
    const liveRow = await resolveLiveAttachmentRow(row, planItem);
    if (!liveRow) return { error: "Không tìm thấy dòng hồ sơ để chọn tệp.", code: "attachment-row-not-found" };

    const preciseButtons = findAttachmentChooseButtons(liveRow);
    const legacyRowButton = findButtonByText(liveRow, ["Chọn tệp đính kèm", "Chọn tệp"]);
    const globalButton = findButtonByText(document, ["Chọn tệp đính kèm", "Chọn tệp"]);
    const buttons = uniqueElements([
      ...preciseButtons,
      legacyRowButton,
      globalButton?.closest?.("tr") === liveRow ? globalButton : null,
    ]);
    attachDebug("open-modal candidates", {
      planItem: {
        fileIndex: planItem?.fileIndex,
        fileName: planItem?.fileName,
        documentName: planItem?.documentName,
        componentName: planItem?.componentName,
        target: planItem?.target,
      },
      row: describeAttachmentRowForLog(liveRow),
      preciseButtonCount: preciseButtons.length,
      candidateCount: buttons.length,
      buttons: buttons.map(describeElementForLog),
      dialogsBefore: visibleDialogSnapshot(),
    });
    if (!buttons.length) return { error: "Không tìm thấy nút Chọn tệp đính kèm.", code: "attachment-button-not-found", row: liveRow };

    // Mỗi nút thử click tối đa 2 lần, chờ modal lâu hơn (trang còn bận re-render/preview sau khi
    // đính các file trước → click đầu dễ hụt; tăng timeout + retry để file cuối không bị bỏ sót).
    for (let index = 0; index < buttons.length; index++) {
      const button = buttons[index];
      for (let attempt = 0; attempt < 2; attempt++) {
        button.scrollIntoView({ block: "center", inline: "center" });
        await sleep(attempt === 0 ? 150 : 500);
        attachDebug("open-modal click", {
          index,
          attempt,
          button: describeElementForLog(button),
          activeBefore: describeElementForLog(document.activeElement),
        });
        // Radix/React xử lý một logical click. clickLikeUser phát cả MouseEvent("click") rồi
        // el.click(), có thể làm nút toggle mở modal xong đóng ngay trước lúc waitFor quan sát.
        button.focus?.();
        button.click();
        const dialog = await waitFor(() => findLatestDialogByText("Danh sách tài liệu điện tử"), 6000, 120);
        if (dialog) return { ok: true, dialog, row: liveRow };
        attachDebug("open-modal no-dialog-after-click", {
          index,
          attempt,
          button: describeElementForLog(button),
          activeAfter: describeElementForLog(document.activeElement),
          dialogsAfter: visibleDialogSnapshot(),
          bodyHasWalletTitle: foldedNodeText(document.body).includes("danh sach tai lieu dien tu"),
        });
      }
    }

    return {
      error: "Không mở được modal Danh sách tài liệu điện tử.",
      code: "wallet-modal-not-opened",
      row: liveRow,
      debug: {
        row: describeAttachmentRowForLog(liveRow),
        buttonCount: buttons.length,
        buttons: buttons.map(describeElementForLog),
        dialogs: visibleDialogSnapshot(),
      },
    };
  }

  function findRemoveAttachmentButton(row) {
    const attachCell = attachmentFileCell(row);
    return Array.from(attachCell?.querySelectorAll("button") || []).find((button) => {
      if (!isVisible(button)) return false;
      const text = foldedNodeText(button);
      if (text.includes("chon tep") || text.includes("xem")) return false;
      const imgAlt = foldChoiceText(button.querySelector("img")?.getAttribute("alt") || "");
      return (
        text.includes("close") ||
        text === "x" ||
        imgAlt.includes("close") ||
        !!button.querySelector("svg.lucide-x")
      );
    }) || null;
  }

  async function confirmIfNeeded() {
    const dialog = findLatestDialog();
    if (!dialog) return;
    const text = foldedNodeText(dialog);
    if (!text.includes("xoa") && !text.includes("xac nhan") && !text.includes("dong y")) return;
    const button = findButtonByText(dialog, ["Xác nhận", "Đồng ý", "Có", "Xóa"]);
    if (button) {
      button.click();
      await sleep(300);
    }
  }

  async function clearExistingAttachment(row, expectedDocumentName = "") {
    const currentName = rowAttachedFileName(row);
    if (!currentName) return true;
    const expected = foldChoiceText(expectedDocumentName || "");
    if (expected && foldChoiceText(currentName).includes(expected)) return true;

    const removeButton = findRemoveAttachmentButton(row);
    if (!removeButton) {
      console.warn("[AutoFill-AttachPlan] Row đã có file nhưng không tìm thấy nút xóa:", currentName);
      return false;
    }
    removeButton.click();
    await sleep(250);
    await confirmIfNeeded();
    await waitFor(() => !rowAttachedFileName(row), 3000, 100);
    return !rowAttachedFileName(row);
  }

  async function submitComponentName(root) {
    const button = findButtonByText(root, ["Thêm", "Thêm mới", "Lưu", "Xác nhận", "Đồng ý", "Hoàn tất"]);
    if (!button || button.disabled) return false;
    button.click();
    await sleep(500);
    return true;
  }

  async function addAttachmentComponent(componentName) {
    const reusableBlankRow = findReusableBlankAttachmentRow();
    if (reusableBlankRow) {
      const beforeRows = findAttachmentCandidateRows();
      await fillAttachmentComponentName(reusableBlankRow, componentName);
      const row = await waitFor(() => {
        if (document.documentElement.contains(reusableBlankRow) && componentTextMatches(reusableBlankRow, componentName)) {
          return reusableBlankRow;
        }
        const rows = findAttachmentRows();
        return rows.find((candidate) =>
          !beforeRows.includes(candidate) && componentTextMatches(candidate, componentName)
        ) || null;
      }, 3000, 100);
      if (row) {
        markAttachmentResult(row, true);
        return row;
      }
    }

    const beforeRows = findAttachmentCandidateRows();
    const beforeCount = beforeRows.length;
    const addButton = findButtonByText(document, ["Thêm thành phần hồ sơ"]);
    if (!addButton) throw new Error("Không tìm thấy nút Thêm thành phần hồ sơ.");

    addButton.click();
    await sleep(350);

    const dialog = findLatestDialog();
    if (dialog && !foldedNodeText(dialog).includes("danh sach tai lieu dien tu")) {
      const input = findComponentNameInput(dialog);
      if (input) {
        await fillAttachmentComponentName(dialog, componentName);
        await submitComponentName(dialog);
      }
    } else {
      const newRow = await waitFor(() => {
        const rows = findAttachmentCandidateRows();
        if (rows.length > beforeCount) return rows[rows.length - 1];
        return null;
      }, 1500, 100);
      if (newRow && findComponentNameInput(newRow)) {
        await fillAttachmentComponentName(newRow, componentName);
        await submitComponentName(newRow);
      }
    }

    const row = await waitFor(() => {
      const rows = findAttachmentCandidateRows();
      if (rows.length > beforeCount) {
        const newRows = rows.filter((row) => !beforeRows.includes(row));
        const matched = newRows.find((candidate) =>
          componentTextMatches(candidate, componentName) && !rowHasAttachedFile(candidate)
        );
        return matched || newRows.find((candidate) => !rowHasAttachedFile(candidate)) || null;
      }
      return rows.find((candidate) =>
        componentTextMatches(candidate, componentName) && !rowHasAttachedFile(candidate)
      ) || null;
    }, 4000, 120);

    if (!row) throw new Error(`Không thêm được thành phần hồ sơ "${componentName}".`);
    markAttachmentResult(row, true);
    return row;
  }

  // SPLIT (cổng Đà Nẵng lưu danh sách "thành phần hồ sơ" theo mẫu per tài khoản/thủ tục): hồ sơ/tab SAU bị
  // DÍNH các dòng "Thêm thành phần" đã thêm ở tab TRƯỚC (thường RỖNG). Xóa hết dòng ĐÃ THÊM (dòng có nút
  // trash `img[alt="delete"]`) — dòng CỐ ĐỊNH (STT1 "Bản chính giấy tờ…") KHÔNG có nút xóa nên được giữ.
  async function clearAddedAttachmentRows() {
    let removed = 0;
    for (let guard = 0; guard < 20; guard++) {
      const rows = findAttachmentRows();
      const deletable = rows.find((row) =>
        Array.from(row.querySelectorAll('img[alt="delete"]')).some((img) => isVisible(img.closest("button") || img))
      );
      if (!deletable) break;
      const btn = Array.from(deletable.querySelectorAll('img[alt="delete"]'))
        .map((img) => img.closest("button"))
        .find((b) => b && isVisible(b));
      if (!btn) break;
      const before = findAttachmentRows().length;
      btn.click();
      // Cổng hiện HỘP XÁC NHẬN role="alertdialog" ("Bạn có muốn xóa tệp đính kèm" / nút "Xác nhận") — role
      // KHÁC "dialog" nên findLatestDialog không bắt được. Đợi alertdialog rồi bấm "Xác nhận".
      const confirmDlg = await waitFor(() =>
        Array.from(document.querySelectorAll('[role="alertdialog"], [role="dialog"]'))
          .filter(isVisible)
          .find((d) => foldedNodeText(d).includes("xoa")) || null,
        2000, 100
      );
      if (confirmDlg) {
        const yes = findButtonByText(confirmDlg, ["Xác nhận", "Đồng ý", "Xóa", "Có"]);
        if (yes) { yes.click(); await sleep(300); }
      }
      const shrank = await waitFor(() => findAttachmentRows().length < before, 2500, 100);
      if (!shrank) break; // không xóa được → dừng, tránh lặp vô hạn
      removed++;
    }
    return removed;
  }

  async function attachOneFileViaDocumentWallet(row, payloadFile, planItem = {}) {
    const intendedDocumentName = planItem.documentName || attachmentDocumentName(payloadFile);
    row = await resolveLiveAttachmentRow(row, planItem);
    if (!row) return { error: `Không tìm thấy dòng hồ sơ "${planItem.componentName || ""}".`, fileNames: [payloadFile.name] };
    const staleDialogsClosed = await closeDocumentWalletDialogs();
    if (!staleDialogsClosed) {
      return {
        error: "Modal Danh sách tài liệu điện tử cũ không đóng được.",
        code: "wallet-stale-modal",
        fileNames: [payloadFile.name],
        debug: { dialogs: visibleDialogSnapshot() },
      };
    }
    row = await resolveLiveAttachmentRow(row, planItem);
    if (!row) return { error: `Không tìm thấy dòng hồ sơ "${planItem.componentName || ""}".`, fileNames: [payloadFile.name] };
    const existingName = rowAttachedFileName(row);
    if (existingName && foldChoiceText(existingName).includes(foldChoiceText(intendedDocumentName))) {
      markAttachmentResult(row, true);
      return { ok: true, attached: 1, fileNames: [existingName], skipped: true };
    }
    if (existingName) {
      if (planItem.appendOnOccupied === false) {
        return {
          error: `Dòng hồ sơ đã có file "${existingName}", không ghi đè file cũ.`,
          fileNames: [payloadFile.name],
        };
      }
      const appendComponentName = componentNameForAppendedFile(planItem, payloadFile);
      attachDebug("row occupied, append new component", {
        existingName,
        intendedDocumentName,
        appendComponentName,
        row: describeAttachmentRowForLog(row),
      });
      const appendedRow = await addAttachmentComponent(appendComponentName);
      return await attachOneFileViaDocumentWallet(appendedRow, payloadFile, {
        ...planItem,
        target: "new",
        needsAddComponent: true,
        componentIndex: null,
        componentName: appendComponentName,
        appendOnOccupied: false,
      });
    }

    const openResult = await openDocumentWalletForRow(row, planItem);
    if (openResult?.error) {
      console.warn("[AutoFill-AttachPlan] Không mở được modal upload", {
        error: openResult.error,
        debug: openResult.debug,
        planItem,
        payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
      });
      return { error: openResult.error, code: openResult.code, fileNames: [payloadFile.name], debug: openResult.debug };
    }
    let dialog = openResult.dialog;
    row = openResult.row || row;

    const deviceUpload = await openWalletDeviceUpload(dialog);
    dialog = deviceUpload.dialog || dialog;
    const uploadInput = deviceUpload.input;
    if (!uploadInput) {
      return {
        error: "Đã mở ví tài liệu nhưng nút Tải lên từ thiết bị không chuyển sang form chọn file.",
        code: "wallet-device-upload-not-opened",
        fileNames: [payloadFile.name],
        debug: {
          hasDeviceUploadButton: !!deviceUpload.button,
          dialog: shortText(nodeText(dialog), 500),
        },
      };
    }

    const file = dataUrlToFile(payloadFile, intendedDocumentName);
    if (!setFilesOnInput(uploadInput, [file], { allowMultiple: false })) {
      markAttachmentResult(dialog, false);
      return { error: `Không gắn được file ${file.name} vào input tải tệp.`, fileNames: [file.name] };
    }

    await waitFor(() => dialog.querySelector('input[name="documentName"]') || findWalletUploadDoneButton(dialog), 12000, 100);
    const nameOk = await ensureWalletDocumentName(dialog, intendedDocumentName);
    if (!nameOk) {
      markAttachmentResult(dialog, false);
      return { error: `Không tìm thấy ô Tên tài liệu cho file ${file.name}.`, fileNames: [file.name] };
    }

    const doneButton = await waitFor(() => {
      const button = findWalletUploadDoneButton(dialog);
      if (button && !button.disabled) return button;
      return null;
    }, 20000, 100);
    if (!doneButton) {
      markAttachmentResult(dialog, false);
      return { error: "Không tìm thấy nút Thêm vào ví & Chọn sau khi tải file.", fileNames: [file.name] };
    }

    const previousText = foldedNodeText(doneButton);
    doneButton.click();
    const uploadCompleted = await waitForUploadCompletion(dialog, previousText);
    const dialogClosed = await waitForWalletDialogClosed(dialog);
    if (document.documentElement.contains(dialog) && isVisible(dialog)) {
      await closeDocumentWalletDialogs();
    }
    const persisted = await waitForPersistedAttachment(row, planItem, existingName);
    if (!persisted) {
      const liveRow = liveAttachmentRowForVerification(row, planItem) || row;
      markAttachmentResult(liveRow || dialog, false);
      return {
        error: `Cổng chưa ghi nhận file ${file.name} vào dòng hồ sơ; ô vẫn chưa có tên file.`,
        code: "wallet-file-not-persisted",
        fileNames: [file.name],
        debug: {
          uploadCompleted,
          dialogClosed,
          row: describeAttachmentRowForLog(liveRow),
        },
      };
    }
    markAttachmentResult(persisted.row, true);
    return { ok: true, attached: 1, fileNames: [file.name] };
  }

  async function attachFilesViaDocumentWalletModal(row, payloadFiles) {
    const attachedNames = [];
    const errors = [];

    for (const payloadFile of payloadFiles) {
      const currentRow = findCopyCertificationAttachmentRow() || row;
      const result = await attachOneFileViaDocumentWallet(currentRow, payloadFile);
      if (result?.error) {
        errors.push(result.error);
        break;
      }
      attachedNames.push(...(result.fileNames || []));
      await sleep(600);
    }

    if (errors.length) {
      return {
        error: errors.join("; "),
        attached: attachedNames.length,
        fileNames: attachedNames,
      };
    }
    return {
      ok: true,
      method: "wallet-modal",
      attached: attachedNames.length,
      fileNames: attachedNames,
    };
  }

  function payloadForPlanItem(payloadFiles, planItem, index) {
    const byIndex = Number.isInteger(planItem?.fileIndex) ? payloadFiles[planItem.fileIndex] : null;
    if (byIndex) return byIndex;
    return payloadFiles.find((file) => file.name === planItem.fileName) || payloadFiles[index] || null;
  }

  function isIdentityAttachmentItem(item) {
    if (Number(item?.componentIndex) === 2) return true;
    const text = foldChoiceText([
      item?.detectedType,
      item?.componentName,
      item?.documentName,
      item?.fileName,
    ].filter(Boolean).join(" "));
    return text.includes("can cuoc cong dan") || text.includes("cccd");
  }

  function isGenericDocumentNameForPlan(name) {
    const text = foldChoiceText(name || "");
    return /^(\d+|img|image|photo|scan|screenshot|zalo|z\d+|file|document|tai lieu)([\s_:-]*\d*)?$/.test(text);
  }

  function normalizeAttachmentPlan(attachments, procedure = "") {
    const items = attachments.map((item) => ({ ...item }));
    for (const item of items) {
      if (isGenericDocumentNameForPlan(item.documentName) && item.detectedType) {
        item.documentName = item.detectedType;
      }
    }

    // Hotfix STT1 file ảo (Đà Nẵng/Hải Châu): plan đã được BE định hình chủ đích (giấy tờ thật đều
    // target=new, 1 file ảo vào STT1). KHÔNG chạy heuristic đảo CCCD↔STT1 nữa — nếu chạy sẽ đẩy nhầm
    // giấy tờ thật lên STT1 và biến file ảo (fileName chứa "CCCD") thành bản trùng của giấy tờ thật → bị bỏ qua.
    if (procedure === "chung-thuc-ban-sao" && items.length > 1 && !items.some((item) => item.virtualCopy)) {
      const existing = items.find((item) => item.target === "existing" || item.needsAddComponent === false);
      const primary = items.find((item) =>
        !isIdentityAttachmentItem(item) &&
        foldChoiceText(item.detectedType || item.componentName || item.documentName || "") !== "tai lieu chung thuc"
      );
      if (existing && primary && existing !== primary && isIdentityAttachmentItem(existing)) {
        for (const item of items) {
          if (item === primary) {
            item.target = "existing";
            item.componentIndex = 1;
            item.needsAddComponent = false;
          } else {
            item.target = "new";
            item.componentIndex = null;
            item.needsAddComponent = true;
            if (!item.componentName || foldChoiceText(item.componentName).includes("ban chinh giay to")) {
              item.componentName = item.detectedType || item.documentName || "Tài liệu chứng thực";
            }
          }
        }
      }
    }

    return items.sort((a, b) => {
      const ax = a.target === "existing" || a.needsAddComponent === false ? 0 : 1;
      const bx = b.target === "existing" || b.needsAddComponent === false ? 0 : 1;
      return ax - bx;
    });
  }

  async function rowForPlanItem(planItem) {
    const componentName = planItem?.componentName || "Tài liệu chứng thực";
    const emptyExistingRow = findEmptyAttachmentRowByComponent(componentName);
    if (emptyExistingRow) return emptyExistingRow;
    if (planItem?.target === "new" || planItem?.needsAddComponent) {
      return await addAttachmentComponent(componentName);
    }
    return findAttachmentRowByComponent(componentName, planItem?.componentIndex) ||
      findCopyCertificationAttachmentRow();
  }

  // Các ô đính kèm cố định của thủ tục Hỗ trợ mai táng: nhận diện đúng hàng theo text.
  const FIXED_SLOT_KEYWORDS = {
    to_khai_mai_tang: ["de nghi ho tro chi phi mai tang", "ho tro chi phi mai tang", "mau so 04", "to khai de nghi"],
    giay_chung_tu: ["giay chung tu hoac giay bao tu", "giay chung tu", "giay bao tu"],
    quyet_dinh_thoi_huong: ["thoi huong tro cap", "danh sach thoi huong", "thoi huong"],
    // Khai sinh liên thông (bảng + menu "Chọn tệp tin"): khớp đúng dòng theo tên giấy tờ.
    birth_proof: ["chung sinh", "lam chung", "cam doan"],
    residence_form: ["thay doi thong tin cu tru", "thay doi noi cu tru", "cu tru"],
    household_application: ["don de nghi dau noi nuoc sach va hop dong dich vu cap nuoc (theo mau", "don de nghi dau noi nuoc sach"],
    organization_application: ["don de nghi dau noi nuoc sach va hop dong dich vu cap nuoc (to chuc", "cap nuoc (to chuc"],
    business_registration_or_establishment: ["quyet dinh thanh lap", "dang ky kinh doanh", "dang ky doanh nghiep"],
    // Điểm trò chơi điện tử công cộng (Bộ VHTTDL) — khớp dòng theo text, dự phòng slotIndex 0/1/2.
    tro_choi_don_de_nghi: ["de nghi cap giay chung nhan du dieu kien hoat dong diem cung cap dich vu tro choi dien tu", "mau so 51a"],
    tro_choi_giay_tuy_than: ["chung minh nhan dan/can cuoc/can cuoc cong dan cua chu diem", "can cuoc cong dan cua chu diem"],
    tro_choi_gpkd: ["giay chung nhan dang ky kinh doanh/giay chung nhan dang ky doanh nghiep", "dang ky kinh doanh/giay chung nhan"],
    legal_land_house_document: ["giay to chung minh nha dat hop phap"],
    land_house_transfer_contract: ["hop dong chuyen nhuong quyen su dung dat quyen so huu nha o", "hop dong mua ban nha dat co xac nhan"],
    organization_property_or_lease_authorization: ["co quan to chuc doanh nghiep tai dia chi de nghi cap nuoc", "thue tru so", "van ban cua chu so huu nha dat uy quyen"],
    doi_ten_legal_land_house_document: ["giay to chung minh nha dat hop phap"],
    doi_ten_confirmed_name_change_application: ["don xin doi ten trong hop dong dich vu cap nuoc co xac nhan", "xac nhan va dau cua 02 don vi"],
    doi_ten_org_property_or_lease_authorization: ["co quan to chuc doanh nghiep tai dia chi de nghi cap nuoc", "thue tru so", "van ban cua chu so huu nha dat uy quyen"],
    doi_ten_business_registration_or_establishment: ["quyet dinh thanh lap", "dang ky kinh doanh", "dang ky doanh nghiep"],
    doi_ten_template_name_change_application: ["don de nghi doi ten trong hop dong dich vu cap nuoc (theo mau"],
    doi_ten_transfer_contract: ["hop dong chuyen nhuong quyen su dung dat quyen so huu nha o", "hop dong mua ban nha dat co xac nhan"],
    doi_ten_owner_consent_company_rental: ["cong ty thue nha phai co giay dong thuan", "chu nha dong y de cong ty dung ten dong ho nuoc"],
    attp_dossier: ["thanh phan ho so", "don de nghi cap giay chung nhan", "giay xac nhan du suc khoe", "tap huan kien thuc an toan thuc pham"],
    phieu_dang_ky_du_tuyen: ["phieu dang ky du tuyen", "mau so 01", "du tuyen cong chuc", "du tuyen vien chuc"],
    gpxd_application: ["don de nghi cap giay phep xay dung theo mau so 1 phu luc so ii", "don de nghi cap giay phep xay dung"],
    gpxd_land_document: ["giay to hop phap ve dat dai chung minh su phu hop muc dich su dung dat", "mot trong nhung giay to hop phap ve dat dai", "dieu 53 cua nghi dinh so 175"],
    gpxd_design_dossier: ["ho so thiet ke xay dung doi voi nha o rieng le", "doi voi nha o rieng le cua ho gia dinh ca nhan", "doi voi nha o rieng le cua to chuc"],
  };

  // input[type=file] thuộc bảng thành phần hồ sơ (có nút "Chọn tệp tin"/btn_upload gần đó).
  function isUploadSlotInput(input) {
    // Cổng Bộ VHTTDL (liz): input file nằm trong <app-upload-flie-multi>, nút upload là icon fa-upload
    // (không có text "Chọn tệp") → nhận diện thẳng theo custom element bọc input.
    if (input.closest && input.closest("app-upload-flie-multi")) return true;
    let node = input;
    for (let i = 0; i < 5 && node; i++) {
      if (node.querySelector && node.querySelector(".btn_upload")) return true;
      const text = foldChoiceText(nodeText(node));
      if (
        text.includes("chon tep tin") ||
        (text.includes("chon tep") && (text.includes("ban sao") || text.includes("ban chinh")))
      ) return true;
      node = node.parentElement;
    }
    return false;
  }

  function fixedSlotUploadInputs() {
    return Array.from(document.querySelectorAll('input[type="file"]')).filter(isUploadSlotInput);
  }

  function fixedSlotRowText(input) {
    const row =
      input.closest("tr") ||
      input.closest("td") ||
      input.closest("li, [class*='ng-star-inserted']") ||
      input.parentElement;
    return foldChoiceText(nodeText(row || input));
  }

  async function chooseBootstrapFileOptionForInput(input) {
    const group = input.closest(".input-group, .form-group, td, li") || input.parentElement;
    if (!group) return false;
    const toggle = Array.from(group.querySelectorAll("button, a")).find((el) =>
      foldChoiceText(nodeText(el)).includes("chon tep tin")
    );
    if (toggle) {
      clickLikeUser(toggle);
      await sleep(80);
    }
    const options = Array.from(group.querySelectorAll(".dropdown-menu .selector-scanner, .dropdown-menu a, li a"));
    const choose = options.find((el) => foldChoiceText(nodeText(el)) === "chon tep tin") ||
      options.find((el) => foldChoiceText(nodeText(el)).includes("chon tep tin"));
    if (!choose) return false;
    clickLikeUser(choose);
    await sleep(120);
    return true;
  }

  function findFixedSlotInput(item, usedInputs) {
    const inputs = fixedSlotUploadInputs();
    const free = inputs.filter((el) => !usedInputs.has(el));
    const keywords = FIXED_SLOT_KEYWORDS[item.slotKey] || [];
    const byText = free.find((el) => {
      const text = fixedSlotRowText(el);
      return keywords.some((kw) => text.includes(kw));
    });
    if (byText) return byText;
    // Fallback theo thứ tự ô trên form (slotIndex) nếu không khớp được theo text.
    if (Number.isInteger(item.slotIndex) && inputs[item.slotIndex] && !usedInputs.has(inputs[item.slotIndex])) {
      return inputs[item.slotIndex];
    }
    return null;
  }

  function otherListFileRows() {
    return Array.from(document.querySelectorAll("#_fcgiayToKhac > li, li[id^='giayToKhac_lr_']")).filter((row) =>
      row.querySelector('input[name="HoSoOnline_giayToKhac[]"]')
    );
  }

  function hasOtherListFileAttachment() {
    return !!document.querySelector('input[name="HoSoOnline_giayToKhac[]"]');
  }

  function otherListFileNameInput(row) {
    return row?.querySelector?.('input[name="HoSoOnline_giayToKhac[]"]') || null;
  }

  function otherListFileInput(row) {
    return row?.querySelector?.('input[type="file"][name^="HoSoOnline_giayToKhac_file_"]') || null;
  }

  function otherListFileHasFile(row) {
    const fileInput = otherListFileInput(row);
    if (fileInput?.files?.length) return true;
    const textInput = fileInput?.closest?.(".input-group")?.querySelector?.('input[readonly="readonly"], input[readonly]');
    return !!String(textInput?.value || "").trim();
  }

  async function ensureOtherListFileRow(componentName) {
    let rows = otherListFileRows();
    let row = rows.find((candidate) => {
      const nameInput = otherListFileNameInput(candidate);
      return nameInput && !String(nameInput.value || "").trim() && !otherListFileHasFile(candidate);
    }) || null;

    if (!row) {
      const addButton = rows[rows.length - 1]?.querySelector?.("input.act.add, button.act.add, .act.add");
      if (addButton) {
        const beforeCount = rows.length;
        clickLikeUser(addButton);
        row = await waitFor(() => {
          const nextRows = otherListFileRows();
          return nextRows.length > beforeCount ? nextRows[nextRows.length - 1] : null;
        }, 2500, 100);
      }
    }
    if (!row) throw new Error(`Không tìm thấy dòng Giấy tờ khác để thêm "${componentName}".`);

    const input = otherListFileNameInput(row);
    if (!input) throw new Error(`Không tìm thấy ô tên Giấy tờ khác cho "${componentName}".`);
    setNativeValue(input, componentName, { typing: true, commit: true });
    await sleep(150);
    return row;
  }

  async function attachOneFileToOtherListFile(payloadFile, planItem = {}) {
    const componentName = planItem.componentName || planItem.documentName || attachmentDocumentName(payloadFile);
    const row = await ensureOtherListFileRow(componentName);
    const input = otherListFileInput(row);
    if (!input) {
      return { error: `Không tìm thấy input file Giấy tờ khác cho "${componentName}".`, fileNames: [] };
    }
    const file = dataUrlToFile(payloadFile, planItem.documentName || componentName);
    await chooseBootstrapFileOptionForInput(input);
    const ok = setFilesOnInput(input, [file], { assumeConsumed: true });
    await sleep(500);
    markAttachmentResult(row, ok);
    if (!ok) return { error: `Không gắn được file vào Giấy tờ khác "${componentName}".`, fileNames: [file.name] };
    return { ok: true, method: "other-listfile", attached: 1, fileNames: [file.name] };
  }

  // Form đính kèm kiểu BẢNG + MENU (vd khai sinh liên thông): mỗi dòng có nút mat-menu-trigger
  // "Chọn tệp tin"; bấm mở mat-menu (overlay render lazy) chứa input[type=file] ẩn (#fileDinhKem).
  function menuSlotTriggers() {
    return Array.from(document.querySelectorAll("button.mat-menu-trigger")).filter((b) =>
      foldChoiceText(nodeText(b)).includes("chon tep tin")
    );
  }

  // Text của dòng (tên giấy tờ) chứa nút "Chọn tệp tin" — để khớp đúng ô theo nội dung.
  function menuSlotRowText(trigger) {
    const row =
      trigger.closest("tr") ||
      trigger.closest("li, [class*='ng-star-inserted']") ||
      trigger.parentElement;
    return foldChoiceText(nodeText(row || trigger));
  }

  function findMenuSlotTrigger(item, usedTriggers) {
    const all = menuSlotTriggers();
    if (!all.length) return null;
    const free = all.filter((b) => !usedTriggers.has(b));
    // GPXD có nhiều dòng bản vẽ gần giống nhau; STT13 cũng chứa "02 bộ bản vẽ..."
    // nên ưu tiên slotIndex đã map từ BE để tránh match nhầm trước STT27.
    const idx = Number.isInteger(item.slotIndex) ? item.slotIndex : 0;
    if (String(item.slotKey || "").startsWith("gpxd_") && all[idx] && !usedTriggers.has(all[idx])) {
      return all[idx];
    }
    // 1) Ưu tiên khớp theo NỘI DUNG dòng (tên giấy tờ) — bền vững với số dòng/thứ tự nút.
    const keywords = FIXED_SLOT_KEYWORDS[item.slotKey] || [];
    if (keywords.length) {
      const byText = free.find((b) => {
        const text = menuSlotRowText(b);
        return keywords.some((kw) => text.includes(kw));
      });
      if (byText) return byText;
    }
    // 2) Fallback theo VỊ TRÍ (slotIndex) trên danh sách đầy đủ.
    if (all[idx] && !usedTriggers.has(all[idx])) return all[idx];
    // 3) Fallback cuối: ô trống đầu tiên.
    return free[0] || null;
  }

  function openMenuPanels() {
    return Array.from(
      document.querySelectorAll(
        ".cdk-overlay-container .mat-menu-panel, .cdk-overlay-container .mat-mdc-menu-panel"
      )
    );
  }

  async function openMenuGetFileInput(trigger) {
    // Chụp tập panel đang mở TRƯỚC khi click để nhận diện panel mới của đúng trigger này.
    const before = new Set(openMenuPanels().map((p) => p.id).filter(Boolean));
    trigger.click(); // mở mat-menu → overlay render input ẩn
    return await waitFor(() => {
      // 1) Panel gắn ĐÚNG trigger này qua aria-controls (chuẩn nhất, tránh lấy nhầm panel dòng khác).
      const ctrl = trigger.getAttribute("aria-controls");
      let panel = ctrl ? document.getElementById(ctrl) : null;
      // 2) Hoặc panel MỚI xuất hiện (không thuộc tập trước click); chỉ lấy panel duy nhất nếu còn 1.
      if (!panel) {
        const panels = openMenuPanels();
        panel = panels.find((p) => p.id && !before.has(p.id)) || (panels.length === 1 ? panels[0] : null);
      }
      return panel ? panel.querySelector('input[type="file"]') : null;
    }, 3000);
  }

  async function closeOpenMenu() {
    const backdrop = document.querySelector(".cdk-overlay-backdrop");
    if (backdrop) backdrop.click();
    else document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    // Đợi overlay đóng HẲN: nếu không, dòng kế tiếp mở menu khi panel dòng trước còn đang đóng
    // → querySelector trả panel cũ → bơm nhầm file vào dòng trước.
    await waitFor(() => openMenuPanels().length === 0, 1500);
  }

  // Đính kèm cho thủ tục có ô upload cố định: bơm thẳng file vào input ẩn của đúng hàng, không qua
  // modal "ví giấy tờ". Hỗ trợ 2 dạng: (1) input cạnh .btn_upload (vd mai táng); (2) bảng + menu
  // "Chọn tệp tin" (vd khai sinh liên thông). Gom nhiều file cùng 1 ô (input multiple) nếu có.
  async function attachFilesByFixedSlot(payloadFiles, attachments) {
    const attachedNames = [];
    const errors = [];
    const usedInputs = new Set();
    const usedTriggers = new Set();

    const bySlot = new Map();
    attachments.forEach((item, i) => {
      const key = item.repeatUpload
        ? `${item.slotKey || `idx-${item.slotIndex}`}-repeat-${i}`
        : item.slotKey || `idx-${item.slotIndex}`;
      if (!bySlot.has(key)) bySlot.set(key, { item, indices: [] });
      bySlot.get(key).indices.push(i);
    });

    for (const { item, indices } of bySlot.values()) {
      const slotLabel = item.slotName || item.componentName || "";
      const files = indices
        .map((i) => payloadForPlanItem(payloadFiles, attachments[i], i))
        .filter(Boolean)
        .map((payload) => dataUrlToFile(payload));
      if (!files.length) {
        errors.push(`Không tìm thấy file cho ô "${slotLabel}".`);
        continue;
      }
      const fileNames = files.map((f) => f.name);

      // (1) Ô upload trực tiếp: input ẩn cạnh .btn_upload (vd mai táng).
      const input = findFixedSlotInput(item, usedInputs);
      if (input) {
        if (!item.repeatUpload) usedInputs.add(input);
        console.log("[AutoFill-FixedSlot] attaching (input)", { slotIndex: item.slotIndex, slotName: slotLabel, fileNames });
        // GÁN THẲNG bằng DataTransfer TRƯỚC (input ẩn vẫn set được). Nếu đã gán → KHÔNG click "Chọn tệp tin":
        // ở cổng Lai Châu click option đó MỞ HỘP THOẠI FILE GỐC của OS (thừa, chặn UI). Chỉ khi gán hụt
        // (cổng chỉ nhận file sau khi mở dropdown, vd mai táng) mới click rồi thử lại.
        // assumeConsumed: form mai táng reset input.files sau khi đọc → lấy kết quả gán trước dispatch.
        let ok = setFilesOnInput(input, files, { assumeConsumed: true });
        if (!ok) {
          await chooseBootstrapFileOptionForInput(input);
          ok = setFilesOnInput(input, files, { assumeConsumed: true });
        }
        await sleep(600);
        const markTarget = input.closest("tr") || input.closest("td") || input.parentElement || input;
        markAttachmentResult(markTarget, ok);
        if (ok) attachedNames.push(...fileNames);
        else errors.push(`Không gắn được file vào ô "${slotLabel}".`);
        continue;
      }

      // (2) Ô kiểu bảng + menu: mở "Chọn tệp tin" → input ẩn trong overlay (vd khai sinh liên thông).
      const trigger = findMenuSlotTrigger(item, usedTriggers);
      if (trigger) {
        if (!item.repeatUpload) usedTriggers.add(trigger);
        console.log("[AutoFill-FixedSlot] attaching (menu)", { slotIndex: item.slotIndex, slotName: slotLabel, fileNames });
        const menuInput = await openMenuGetFileInput(trigger);
        if (!menuInput) {
          await closeOpenMenu();
          errors.push(`Không mở được ô đính kèm "${slotLabel}".`);
          continue;
        }
        const ok = setFilesOnInput(menuInput, files, { assumeConsumed: true });
        await sleep(600);
        await closeOpenMenu();
        const markTarget = trigger.closest("tr") || trigger.closest("td") || trigger.parentElement || trigger;
        markAttachmentResult(markTarget, ok);
        if (ok) attachedNames.push(...fileNames);
        else errors.push(`Không gắn được file vào ô "${slotLabel}".`);
        continue;
      }

      errors.push(`Không tìm thấy ô đính kèm "${slotLabel}".`);
    }

    if (errors.length) {
      return {
        error: errors.join("; "),
        attached: attachedNames.length,
        skipped: 0,
        fileNames: attachedNames,
        skippedNames: [],
      };
    }
    return {
      ok: true,
      method: "fixed-slot",
      attached: attachedNames.length,
      skipped: 0,
      fileNames: attachedNames,
      skippedNames: [],
    };
  }

  // Chế độ TÁCH HỒ SƠ (split): ép mọi file về STT1 (dòng "Bản chính giấy tờ…"), KHÔNG thêm dòng.
  // Mỗi hồ sơ chỉ 1 file → file khác thuộc hồ sơ/tab khác (popup + background điều phối).
  function forceRow1PlanItem(item) {
    // Chứng thực chữ ký: giấy tùy thân (CCCD/Hộ chiếu...) PHẢI vào STT2, TUYỆT ĐỐI không ép về STT1.
    // Case bản dịch đặt forceFirstRow vì tên file có thể chứa chữ "CCCD" nhưng vẫn là tài liệu hàng 1.
    if (!item?.forceFirstRow && isIdentityAttachmentItem(item)) {
      const row2 = findAttachmentRows()[1] || null;
      const name2 = row2 ? attachmentComponentName(row2) : "";
      return {
        ...item,
        target: "existing",
        componentIndex: 2,
        needsAddComponent: false,
        appendOnOccupied: false,
        componentName: name2 || item?.componentName || "",
      };
    }
    const row1 = findCopyCertificationAttachmentRow() || findAttachmentRows()[0] || null;
    const name1 = row1 ? attachmentComponentName(row1) : "";
    return {
      ...item,
      target: "existing",
      componentIndex: 1,
      needsAddComponent: false,
      appendOnOccupied: false, // STT1 đã có file → KHÔNG thêm dòng mới (giữ 1 hồ sơ 1 file)
      componentName: name1 || item?.componentName || "",
    };
  }

  // ===== Engine đính kèm bảng-checkbox (Form.io/Angular CDK table, vd ATTP cấp lại — Bộ Công Thương) =====
  // Mỗi dòng giấy tờ: mat-checkbox (chọn) + rdo_File (Bản chính/Bản sao) + ô upload input[type=file] (ở CUỐI
  // dòng, KHÔNG phải cells[2] như findAttachmentFileInput mặc định). Khớp dòng bằng componentName (substring
  // fold). Với target "attp-row": tick checkbox → chọn loại bản → set file vào input trong dòng.
  async function tickAttpRowCheckbox(row) {
    const cell = row.cells?.[1] || row.cells?.[0] || row;
    const cb = cell.querySelector('input[type="checkbox"]') || row.querySelector('input[type="checkbox"]');
    if (!cb || cb.checked) return;
    const clickable = cb.closest("mat-checkbox") || cb.closest("label") || cb;
    clickable.click();
    await sleep(200);
    if (!cb.checked) {
      cb.checked = true;
      cb.dispatchEvent(new Event("input", { bubbles: true }));
      cb.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  async function setAttpRowLoaiBan(row, loaiBan) {
    const want = foldChoiceText(loaiBan || "");   // "ban chinh" | "ban sao"
    if (!want) return;
    const radios = Array.from(row.querySelectorAll("mat-radio-button"));
    const target = radios.find((r) => foldChoiceText(nodeText(r)).includes(want));
    if (!target) return;
    const input = target.querySelector('input[type="radio"]');
    if (input?.checked || target.classList.contains("mat-radio-checked")) return;
    (target.querySelector("label") || target).click();
    await sleep(150);
  }

  // Fingerprint tên tài liệu: bỏ đuôi file + mọi ký tự KHÔNG phải chữ/số (khoảng trắng, "_", ".", "…",
  // "/") → chuỗi chữ-số thuần. Nhờ vậy so khớp được bất kể dấu phân cách hay tên bị cắt ngắn khi hiển thị.
  function attpDocFingerprint(value) {
    return foldChoiceText(value || "").replace(/\.[a-z0-9]{2,5}$/i, "").replace(/[^a-z0-9]/g, "");
  }

  // Đọc fingerprint các file ĐÃ đính trong ô đính kèm của dòng. Ô đính kèm là ô chứa input[type=file]
  // (ở cổng Đà Nẵng/Bộ Xây dựng là CỘT CUỐI, KHÁC cells[2] = cột "Loại bản") → không dùng rowAttachedFileName.
  function attpRowAttachedFingerprints(row) {
    const input = row?.querySelector?.('input[type="file"]');
    const cell = (input && input.closest('td, th, mat-cell, [role="cell"], [role="gridcell"]')) || row;
    if (!cell) return [];
    const fileRe = /\.(pdf|jpe?g|png|webp|docx?|xlsx?)\b/i;
    // Mỗi file hiển thị 1 phần tử LÁ chứa đuôi file; loại nút "Chọn tệp tin" (không có đuôi file).
    const leaves = Array.from(cell.querySelectorAll("*")).filter(
      (el) => !el.children.length && fileRe.test(el.textContent || "")
    );
    const texts = leaves.length ? leaves.map((el) => el.textContent) : [];
    if (!texts.length) {
      const whole = nodeText(cell);
      if (fileRe.test(whole)) texts.push(whole);
    }
    return texts.map(attpDocFingerprint).filter((fp) => fp.length >= 6);
  }

  // Dòng ĐÃ có file trùng tài liệu này chưa? So 24 ký tự đầu (chịu được tên bị cắt "..." khi hiển thị).
  function attpRowHasDoc(row, item) {
    const want = attpDocFingerprint(item.documentName || item.fileName || "");
    if (want.length < 6) return false;
    const probe = want.slice(0, 24);
    return attpRowAttachedFingerprints(row).some(
      (fp) => fp.startsWith(probe) || probe.startsWith(fp.slice(0, 24))
    );
  }

  async function attachFilesByAttpRow(payloadFiles, attachments) {
    const fileNames = [];
    const skippedNames = [];
    const errors = [];
    // Gom item theo DÒNG (componentName) — 1 dòng có thể nhận NHIỀU file (vd "sức khỏe" = danh sách + sổ
    // KSK; GCN ATTP = nhiều bản). Set 1 lần với đủ file để không ghi đè lẫn nhau (ô upload là multiple).
    const groups = new Map();
    for (const item of attachments) {
      const key = foldChoiceText(item.componentName || item.documentName || item.fileName || "");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    }
    for (const items of groups.values()) {
      const first = items[0];
      const row = await waitFor(
        () => findAttachmentRowByComponent(first.componentName, first.componentIndex),
        2500,
        120
      );
      if (!row) { errors.push(`Không tìm thấy dòng "${first.documentName || first.componentName}".`); continue; }
      row.scrollIntoView?.({ block: "center" });
      // CHỐNG TRÙNG: dòng đã có file trùng tài liệu này (vd bấm "Đính kèm" 2 lần) → bỏ qua, không đính lại.
      const pending = items.filter((item) => {
        if (attpRowHasDoc(row, item)) {
          skippedNames.push(item.documentName || item.fileName || "");
          return false;
        }
        return true;
      });
      if (!pending.length) { markAttachmentResult(row, true); continue; }
      await tickAttpRowCheckbox(row);
      await setAttpRowLoaiBan(row, first.loaiBan);
      // Ô upload ở CUỐI dòng (không phải cells[2]) → tìm trong cả dòng.
      const input = row.querySelector('input[type="file"]');
      if (!input) { errors.push(`Dòng "${first.documentName}" không có ô upload.`); continue; }
      const files = [];
      const names = [];
      for (const item of pending) {
        const payload = payloadForPlanItem(payloadFiles, item);
        if (!payload) { errors.push(`Thiếu file cho "${item.fileName}".`); continue; }
        try { files.push(dataUrlToFile(payload, item.documentName)); names.push(item.fileName); }
        catch (e) { console.warn("[AutoFill-Attach] Đọc file lỗi:", item.fileName, e); errors.push(`Không đọc được tệp "${item.fileName}".`); }
      }
      if (!files.length) continue;
      const ok = setFilesOnInput(input, files, { assumeConsumed: true });
      markAttachmentResult(row, ok);
      if (ok) fileNames.push(...names);
      else errors.push(`Đính file thất bại cho "${first.documentName}".`);
      await sleep(500);
    }
    return {
      ok: !errors.length,
      method: "attp-row",
      attached: fileNames.length,
      skipped: skippedNames.length,
      fileNames,
      skippedNames,
      errors,
      error: errors.length ? errors.join("; ") : undefined,
    };
  }

  async function attachFilesByPlan(payloadFiles, attachments, procedure = "", opts = {}) {
    // Cổng Bắc Ninh: DOM đính kèm khác hẳn (checkbox + input file theo thành phần) → engine riêng.
    if (detectFormKind() === "bacninh" && typeof H.attachBacNinhByPlan === "function") {
      return H.attachBacNinhByPlan(payloadFiles, attachments, opts);
    }
    if (window.__AUTOFILL_HCC_ATTACH_BUSY__) {
      return { error: "Đang có lượt đính kèm khác đang chạy, vui lòng đợi hoàn tất." };
    }
    window.__AUTOFILL_HCC_ATTACH_BUSY__ = true;
    const splitMode = opts.mode === "split";
    try {
      const attachedNames = [];
      const skippedNames = [];
      const errors = [];
      let errorCode = null;
      const allAttachments = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
      let remainingAttachments = allAttachments;

      // Bảng-checkbox thuần (ATTP cấp lại...) vẫn dùng engine riêng như cũ.
      const attpItems = allAttachments.filter((item) => item.target === "attp-row");
      const addDocumentItems = allAttachments.filter((item) => item.target === "add-document-dialog");
      const genericNewItems = allAttachments.filter((item) =>
        item.target !== "add-document-dialog" &&
        (item.target === "new" || item.needsAddComponent === true)
      );

      // SPLIT + có dòng phải "Thêm thành phần" (flow file ảo Hải Châu): dọn các dòng đã thêm còn DÍNH từ
      // tab/hồ sơ trước để mỗi hồ sơ chỉ giữ đúng dòng của nó. No-op ở cổng không có nút xóa dạng này.
      if (splitMode && genericNewItems.length) {
        try { await clearAddedAttachmentRows(); } catch (e) { console.warn("[AutoFill-Attach] clear leftover rows:", e); }
      }

      if (attpItems.length && !addDocumentItems.length && !genericNewItems.length) {
        return await attachFilesByAttpRow(payloadFiles, attpItems);
      }

      // Cổng Quảng Ninh có thể vừa có các hàng cố định vừa có giấy tờ phải tạo bằng nút
      // "Thêm thành phần hồ sơ". Không return sau nhóm attp-row: giữ engine bảng đã ổn định cho
      // các hàng cố định, rồi chuyển riêng nhóm target=new xuống engine tạo hàng generic bên dưới.
      const onlyAttpAndGenericNew =
        attpItems.length + genericNewItems.length === allAttachments.length;
      if (attpItems.length && genericNewItems.length && onlyAttpAndGenericNew) {
        const fixedRowResult = await attachFilesByAttpRow(payloadFiles, attpItems);
        attachedNames.push(...(fixedRowResult.fileNames || []));
        skippedNames.push(...(fixedRowResult.skippedNames || []));
        if (fixedRowResult.error) {
          return {
            error: fixedRowResult.error,
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }
        remainingAttachments = genericNewItems;
      }

      // Cổng NNMT trộn hàng cố định với hàng phải tạo qua modal "Thêm giấy tờ". Chạy hàng cố định
      // trước; sau khi modal tạo xong hàng động, tái sử dụng chính engine attp-row để upload file.
      if (addDocumentItems.length) {
        // Cho phép kèm cả fixed-slot (ô upload cố định, vd Văn bản đề nghị hưu trí) — chạy TRƯỚC modal.
        const unsupported = allAttachments.filter((item) =>
          item.target !== "attp-row" && item.target !== "add-document-dialog" && item.target !== "fixed-slot"
        );
        if (unsupported.length) {
          return { error: "Kế hoạch đính kèm chứa target chưa hỗ trợ trong luồng hỗn hợp Thêm giấy tờ." };
        }

        const fixedSlotItems = allAttachments.filter((item) => item.target === "fixed-slot");
        if (fixedSlotItems.length) {
          const fixedResult = await attachFilesByFixedSlot(payloadFiles, fixedSlotItems);
          attachedNames.push(...(fixedResult.fileNames || []));
          skippedNames.push(...(fixedResult.skippedNames || []));
          if (fixedResult.error) {
            return {
              error: fixedResult.error,
              attached: attachedNames.length,
              skipped: skippedNames.length,
              fileNames: attachedNames,
              skippedNames,
            };
          }
        }

        if (attpItems.length) {
          const fixedRowResult = await attachFilesByAttpRow(payloadFiles, attpItems);
          attachedNames.push(...(fixedRowResult.fileNames || []));
          skippedNames.push(...(fixedRowResult.skippedNames || []));
          if (fixedRowResult.error) {
            return {
              error: fixedRowResult.error,
              attached: attachedNames.length,
              skipped: skippedNames.length,
              fileNames: attachedNames,
              skippedNames,
            };
          }
        }

        // Chính target từ BE là contract bật engine; không khóa theo procedure key vì nhiều thủ tục
        // trên cùng cổng MAE dùng chung modal này (xóa đăng ký tàu cá, cấp GCN ATTP...).
        if (typeof H.ensureMaeAddDocumentRows !== "function") {
          return {
            error: `Extension chưa nạp engine Thêm giấy tờ cho thủ tục "${procedure || "không xác định"}".`,
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }
        const ensureResult = await H.ensureMaeAddDocumentRows(addDocumentItems);
        if (ensureResult?.error) {
          return {
            error: ensureResult.error,
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }

        const dynamicRowItems = addDocumentItems.map((item) => ({
          ...item,
          target: "attp-row",
          needsAddComponent: false,
        }));
        const dynamicResult = await attachFilesByAttpRow(payloadFiles, dynamicRowItems);
        attachedNames.push(...(dynamicResult.fileNames || []));
        skippedNames.push(...(dynamicResult.skippedNames || []));
        if (dynamicResult.error) {
          return {
            error: dynamicResult.error,
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }
        return {
          ok: true,
          method: "attp-row+add-document-dialog",
          attached: attachedNames.length,
          skipped: skippedNames.length,
          fileNames: attachedNames,
          skippedNames,
        };
      }

      const fixedItems = remainingAttachments.filter((item) => item.target === "fixed-slot");
      const normalItems = remainingAttachments.filter((item) => item.target !== "fixed-slot");

      // Thủ tục có ô upload cố định vẫn có thể kèm giấy tờ thêm mới (vd cấp nước sạch có CCCD
      // ở "Giấy tờ khác"). Chạy fixed-slot trước rồi tiếp tục xử lý phần còn lại.
      if (fixedItems.length) {
        const fixedResult = await attachFilesByFixedSlot(payloadFiles, fixedItems);
        attachedNames.push(...(fixedResult.fileNames || []));
        if (fixedResult.error) errors.push(fixedResult.error);
        if (!normalItems.length) {
          if (errors.length) {
            return {
              error: errors.join("; "),
              attached: attachedNames.length,
              skipped: skippedNames.length,
              fileNames: attachedNames,
              skippedNames,
            };
          }
          return {
            ok: true,
            method: "fixed-slot",
            attached: attachedNames.length,
            skipped: skippedNames.length,
            fileNames: attachedNames,
            skippedNames,
          };
        }
      }

      // Hải Châu (Đà Nẵng): bundle split có file ẢO (virtualCopy) → GIỮ nguyên kế hoạch BE (giấy tờ thật
      // target=new, file ảo target=STT1), KHÔNG ép mọi file về STT1. Split thường vẫn ép hết về STT1.
      const plannedAttachments = (splitMode && !normalItems.some((it) => it && it.virtualCopy))
        ? normalItems.map(forceRow1PlanItem)   // split thường: mọi file ép về STT1
        : normalizeAttachmentPlan(normalItems, procedure);

      for (let i = 0; i < plannedAttachments.length; i++) {
        const item = plannedAttachments[i] || {};
        const payloadFile = payloadForPlanItem(payloadFiles, item, i);
        if (!payloadFile) {
          errors.push(`Không tìm thấy file ${item.fileName || i + 1} trong payload.`);
          break;
        }
        console.log("[AutoFill-AttachPlan] attaching", {
          fileIndex: item.fileIndex,
          payloadName: payloadFile.name,
          documentName: item.documentName,
          componentName: item.componentName,
          target: item.target,
        });

        const existingRow = findExistingAttachedRowForPlanItem(item, payloadFile);
        if (existingRow) {
          const existingName = rowAttachedFileName(existingRow);
          attachDebug("skip duplicate attachment", {
            existingName,
            item,
            payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
            row: describeAttachmentRowForLog(existingRow),
          });
          skippedNames.push(existingName || item.documentName || payloadFile.name);
          markAttachmentResult(existingRow, true);
          await sleep(150);
          continue;
        }

        if ((item.target === "new" || item.needsAddComponent) && hasOtherListFileAttachment()) {
          const result = await attachOneFileToOtherListFile(payloadFile, item);
          if (result?.error) {
            errors.push(result.error);
            break;
          }
          attachedNames.push(...(result.fileNames || []));
          await sleep(400);
          continue;
        }

        let row;
        try {
          row = await rowForPlanItem(item);
        } catch (e) {
          console.warn("[AutoFill-Attach] Tìm dòng hồ sơ lỗi:", e);
          errors.push(`Không mở được dòng hồ sơ "${item.componentName || ""}".`);
          break;
        }
        if (!row) {
          errors.push(`Không tìm thấy dòng hồ sơ "${item.componentName || ""}".`);
          break;
        }

        // Cổng moj đôi khi trả 504/timeout khi lưu vào ví giấy tờ → tự thử lại vài lần (backoff)
        // trước khi báo lỗi. Đóng modal dở + làm mới dòng hồ sơ giữa các lần thử để reset trạng thái.
        const MAX_ATTACH_ATTEMPTS = 3;
        let result = null;
        let persistedRetryUsed = false;
        for (let attempt = 1; attempt <= MAX_ATTACH_ATTEMPTS; attempt++) {
          result = await attachOneFileViaDocumentWallet(row, payloadFile, item);
          if (!result?.error) break;
          // Split tab: các trạng thái ví React bị treo không chữa được bằng cách click lại tại chỗ.
          // Trả ngay cho state machine để áp dụng giới hạn reload theo từng trạng thái.
          if (splitMode && isSplitReloadableWalletError(result.code)) break;
          // Modal đóng nhưng dòng vẫn trống: thử lại đúng MỘT lần. Không để vòng retry chung biến
          // lỗi này thành ba lượt rồi vẫn tô xanh/chuyển tab như trước.
          if (result.code === "wallet-file-not-persisted") {
            if (persistedRetryUsed) break;
            persistedRetryUsed = true;
          }
          if (attempt < MAX_ATTACH_ATTEMPTS) {
            console.warn(`[AutoFill-AttachPlan] thử lại đính kèm (${attempt}/${MAX_ATTACH_ATTEMPTS - 1}) do lỗi:`, result.error);
            await closeDocumentWalletDialogs();
            await sleep(2000 * attempt); // backoff tăng dần để cổng kịp hồi (504 thường transient)
            try { row = (await rowForPlanItem(item)) || row; } catch (_) { /* giữ row cũ */ }
          }
        }
        if (result?.error) {
          errorCode = errorCode || result.code || null;
          console.warn("[AutoFill-AttachPlan] attach item failed", {
            error: result.error,
            debug: result.debug,
            item,
            payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
          });
          errors.push(result.error);
          break;
        }
        attachedNames.push(...(result.fileNames || []));
        await sleep(600);
      }

      if (errors.length) {
        return {
          error: errors.join("; "),
          code: errorCode,
          attached: attachedNames.length,
          skipped: skippedNames.length,
          fileNames: attachedNames,
          skippedNames,
        };
      }
      return {
        ok: true,
        method: "wallet-plan",
        attached: attachedNames.length,
        skipped: skippedNames.length,
        fileNames: attachedNames,
        skippedNames,
      };
    } catch (e) {
      console.warn("[AutoFill-Attach] Lỗi đính kèm file theo plan:", e);
      return { error: "Không đính kèm được tài liệu vào hồ sơ. Vui lòng thử lại." };
    } finally {
      window.__AUTOFILL_HCC_ATTACH_BUSY__ = false;
    }
  }

  async function attachFilesToRequiredCopyCertification(payloadFiles) {
    try {
      const row = findCopyCertificationAttachmentRow();
      if (!row) {
        return { error: "Không tìm thấy thành phần hồ sơ bắt buộc để đính kèm file." };
      }

      // Không bơm thẳng vào input ẩn ở dòng hồ sơ: form này có nhánh preview/download
      // dễ serialize File object thành "[object File].html". Đi qua modal upload của trang
      // để dùng đúng handler upload/đính kèm nội bộ.
      return await attachFilesViaDocumentWalletModal(row, payloadFiles);
    } catch (e) {
      console.warn("[AutoFill-Attach] Lỗi đính kèm file:", e);
      return { error: "Không đính kèm được tệp. Vui lòng thử lại." };
    }
  }

  // Bôi xanh/đỏ component đã điền/không điền được, để dễ nhận biết trên UI.
  function injectAutofillStyles() {
    if (document.getElementById("autofill-style")) return;
    const st = document.createElement("style");
    st.id = "autofill-style";
    st.textContent = `
    .autofill-filled {
      background-color: #e8f5e9 !important;
      outline: 2px solid #4caf50 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
    .autofill-not-filled {
      background-color: #ffebee !important;
      outline: 2px solid #e53935 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
    .autofill-default {
      background-color: #fff8e1 !important;
      outline: 2px solid #f9a825 !important;
      outline-offset: 1px !important;
      border-radius: 3px !important;
      transition: background-color 0.3s, outline 0.3s;
    }
  `;
    (document.head || document.documentElement).appendChild(st);
  }

  function clearAutofillMarks() {
    document.querySelectorAll(".autofill-filled, .autofill-not-filled, .autofill-default").forEach((el) => {
      el.classList.remove("autofill-filled");
      el.classList.remove("autofill-not-filled");
      el.classList.remove("autofill-default");
    });
  }

  function markFilled(el) {
    if (el && el.classList) {
      el.classList.remove("autofill-not-filled");
      // Giữ viền vàng (giá trị mặc định) — không đè thành xanh.
      if (!el.classList.contains("autofill-default")) el.classList.add("autofill-filled");
    }
  }

  // Tô VIỀN VÀNG cho các field có default=true (giá trị BE điền mặc định, không từ giấy tờ).
  // Chạy SAU markAngularMarks: đổi mọi mark XANH bên trong container của field sang VÀNG
  // (vì các hàm điền tô xanh ở element khác nhau, không cố định 1 chỗ).
  function _convertGreenToYellow(container) {
    if (!container) return;
    const targets = [];
    if (container.classList && container.classList.contains("autofill-filled")) targets.push(container);
    if (container.querySelectorAll) targets.push(...container.querySelectorAll(".autofill-filled"));
    targets.forEach((el) => {
      el.classList.remove("autofill-filled");
      el.classList.remove("autofill-not-filled");
      el.classList.add("autofill-default");
    });
  }

  function markDefaultsYellow(fields) {
    for (const f of fields || []) {
      if (!f || !f.default) continue;
      if (f.comp === "radio-bylabel") {
        const want = norm(f.value);
        const btn = Array.from(document.querySelectorAll("mat-radio-button.mat-radio-checked"))
          .find((b) => { const t = norm(b.textContent); return t && (t.includes(want) || want.includes(t)); });
        _convertGreenToYellow(btn ? (btn.closest("mat-radio-group") || btn.parentElement) : null);
        continue;
      }
      _convertGreenToYellow(findFormControl(fieldCandidates(f)));
    }
  }

  function markUnfilled(el) {
    if (el && el.classList && !el.classList.contains("autofill-filled")) {
      el.classList.add("autofill-not-filled");
    }
  }

  function isVisible(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
    const rect = el.getBoundingClientRect();
    if ((rect.width > 0 || rect.height > 0) && el.getClientRects().length > 0) return true;
    return el.offsetParent !== null;
  }

  // Header dropdown thường có icon ▼/▲ ở cuối; lọc bỏ trước khi so.
  const ARROW_RE = /[▲▼▾▿]/g;
  function isPlaceholderText(t) {
    const s = (t || "").replace(ARROW_RE, "").trim().toLowerCase();
    if (!s) return true;
    if (s.startsWith("chọn ") || s.startsWith("chon ")) return true;
    if (/^-+\s*chọn\s*-*$/.test(s)) return true;       // -- Chọn -- / Chọn / ---
    if (s.includes("vui lòng chọn")) return true;       // Vui lòng chọn dữ liệu
    return false;
  }

  // Quét toàn bộ component trong frame; ô nào còn rỗng/-- Chọn -- → mark đỏ.
  // Đã filled (xanh) thì markUnfilled bỏ qua (không đè).
  function markAllEmptyFieldsRed() {
    // x-input + x-input-number + x-date + x-date-text: kiểm tra giá trị input
    document.querySelectorAll("x-input, x-input-number").forEach((c) => {
      if (!isVisible(c)) return;
      const inp = c.querySelector("input");
      if (!inp || !inp.value || !inp.value.trim()) markUnfilled(inp?.parentElement || c);
    });
    document.querySelectorAll("x-date").forEach((c) => {
      if (!isVisible(c)) return;
      const day = c.querySelector('input[name$="-day"]');
      const month = c.querySelector('input[name$="-month"]');
      const year = c.querySelector('input[name$="-year"]');
      const filled = [day, month, year].every((x) => x && x.value && x.value.trim());
      if (!filled) markUnfilled((day || month || year)?.parentElement || c);
    });
    document.querySelectorAll("x-date-text").forEach((c) => {
      if (!isVisible(c)) return;
      const day = c.querySelector('input[id$="-day"]');
      const month = c.querySelector('input[id$="-month"]');
      const year = c.querySelector('input[id$="-year"]');
      const filled = [day, month, year].every((x) => x && x.value && x.value.trim());
      const target = (day || month || year)?.parentElement || c;
      if (!filled) {
        markUnfilled(target);
      } else {
        // Đã có đủ giá trị (điền ở pass sau / form tự điền) → gỡ vệt đỏ pass-1, tô xanh.
        c.classList.remove("autofill-not-filled");
        markFilled(target);
        markFilled(c);
      }
    });
    // x-radio: chưa có checkbox nào checked
    document.querySelectorAll("x-radio").forEach((c) => {
      if (!isVisible(c)) return;
      if (!c.querySelector('input[type="checkbox"]:checked')) markUnfilled(c);
    });
    // x-select / x-select-default: header hiển thị "-- Chọn --" hoặc "Vui lòng chọn..."
    const checkSelectHeader = (header) => {
      if (!header || !isVisible(header)) return;
      if (isPlaceholderText(header.textContent)) markUnfilled(header);
    };
    document.querySelectorAll("x-select").forEach((c) => {
      if (!isVisible(c)) return;
      checkSelectHeader(c.querySelector(".input-field-select"));
    });
    document.querySelectorAll("x-select-default").forEach((c) => {
      if (!isVisible(c)) return;
      checkSelectHeader(c.querySelector("div[tabindex]"));
    });
    // x-select-area: từng sub-widget + ô địa chỉ
    document.querySelectorAll("x-select-area").forEach((c) => {
      if (!isVisible(c)) return;
      c.querySelectorAll('[id^="custom-select-"]').forEach((w) => {
        checkSelectHeader(w.querySelector(".input-field-select"));
      });
      const addr = c.querySelector("input.input-field");
      if (addr && isVisible(addr.parentElement || addr) && (!addr.value || !addr.value.trim())) {
        markUnfilled(addr.parentElement || addr);
      }
    });
  }

  function dispatchInputEvent(el, type, init = {}) {
    const EventCtor = typeof InputEvent === "function" && type === "input" ? InputEvent : Event;
    try {
      el.dispatchEvent(new EventCtor(type, { bubbles: true, ...init }));
    } catch {
      el.dispatchEvent(new Event(type, { bubbles: true }));
    }
  }

  function keyToKeyCode(key) {
    switch (key) {
      case "Enter": return 13;
      case "Tab": return 9;
      case "Escape": return 27;
      case "Backspace": return 8;
      case "ArrowDown": return 40;
      case "ArrowUp": return 38;
      default:
        return typeof key === "string" && key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0;
    }
  }

  function dispatchKeyboardEvent(el, type, key) {
    const keyCode = keyToKeyCode(key);
    try {
      const ev = new KeyboardEvent(type, { bubbles: true, cancelable: true, key });
      // KeyboardEvent constructor bỏ qua keyCode/which → ép qua getter. Nhiều lib (Choices.js,
      // jQuery-based) chốt phím Enter bằng event.keyCode === 13, thiếu nó thì nhánh Enter chết.
      if (keyCode) {
        Object.defineProperty(ev, "keyCode", { get: () => keyCode });
        Object.defineProperty(ev, "which", { get: () => keyCode });
      }
      el.dispatchEvent(ev);
    } catch {
      el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
    }
  }

  // Set value qua native setter để framework (React/web-component) nhận biết thay đổi.
  // Với input thường, có thể bật typing/commit để giống thao tác nhập tay hơn
  // (một số form mirror field ở keyup/blur thay vì chỉ input/change).
  function setNativeValue(el, value, options = {}) {
    const text = String(value ?? "");
    const key = text.slice(-1) || "Unidentified";
    if (options.typing && typeof el.focus === "function") el.focus();
    if (options.typing) {
      dispatchKeyboardEvent(el, "keydown", key);
      dispatchKeyboardEvent(el, "keypress", key);
      dispatchInputEvent(el, "beforeinput", { data: text, inputType: "insertReplacementText" });
    }
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, text);
    else el.value = text;
    dispatchInputEvent(el, "input", { data: text, inputType: "insertReplacementText" });
    if (options.typing) {
      dispatchKeyboardEvent(el, "keyup", key);
      el.dispatchEvent(new Event("compositionend", { bubbles: true }));
    }
    if (options.change !== false) el.dispatchEvent(new Event("change", { bubbles: true }));
    if (options.commit) el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  const LEGACY_MIRROR_FIELDS = [
    ["SoDinhDanhC", "SoGiayToDinhDanhC"],
    ["SoDinhDanhC", "SoGiayToTuyThanC"],
    ["SoDinhDanhC", "NYC_SoGiayToTuyThan"],
    ["NYC_SoDinhDanh", "NYC_SoGiayToTuyThan"],
    ["NYC_SoDinhDanh", "SoGiayToDinhDanhC"],
    ["SoDinhDanhC1", "SoGiayToDinhDanhC1"],
    ["SoDinhDanhC1", "SoGiayToTuyThanC1"],
    ["SoDinhDanhCha", "SoGiayToDinhDanhCha"],
    ["SoDinhDanhMe", "SoGiayToDinhDanhMe"],
    ["SoDinhDanh_BenNam", "SoGiayToDinhDanh_BenNam"],
    ["SoDinhDanh_BenNu", "SoGiayToDinhDanh_BenNu"],
    ["SoDinhDanh", "SoGiayToDinhDanh"],
  ];

  const FIELD_NAME_ALIASES = {
    LoaiDangKy: ["loaiDangKy"],
    loaiDangKy: ["LoaiDangKy"],
    SoGiayToDinhDanhC1: ["SoGiayToTuyThanC1", "SoDinhDanhC1"],
    SoGiayToTuyThanC1: ["SoGiayToDinhDanhC1", "SoDinhDanhC1"],
  };

  function fieldCandidates(f) {
    const names = [
      f.name,
      ...(Array.isArray(f.aliases) ? f.aliases : []),
      ...(FIELD_NAME_ALIASES[f.name] || []),
    ];
    return names.filter(Boolean).filter((n, i, arr) => arr.indexOf(n) === i);
  }

  function standardNameVariants(names) {
    const out = [];
    for (const raw of names) {
      const name = String(raw || "").trim();
      if (!name) continue;
      out.push(name);
      const dataKey = name.match(/^data\[([^\]]+)\]$/)?.[1];
      if (dataKey) out.push(dataKey);
      if (name.startsWith("CongDan_")) out.push(name.slice("CongDan_".length));
      else out.push("CongDan_" + name);
    }
    return out.filter(Boolean).filter((n, i, arr) => arr.indexOf(n) === i);
  }

  function formioStableRadioName(name) {
    // "Stable name" = tên radio Form.io đã BỎ đuôi [instance-id] ngẫu nhiên (vd cổng khuyết tật Lâm Đồng:
    // DOM name = data[khuyetTat1Obj][khuyetTatRadio1][ehzqddg-ew6asu7], BE gửi ...[khuyetTatRadio1]).
    // Nhận diện qua field-key chứa "radio". Trả cả khi name ĐÃ ổn định (không có đuôi id) để so khớp 2 chiều.
    const text = String(name || "").trim();
    if (!text.startsWith("data[")) return "";
    const parts = text.match(/\[[^\]]+\]/g) || [];
    if (parts.length < 2) return "";
    const last = parts[parts.length - 1].slice(1, -1).toLowerCase();
    const secondLast = parts[parts.length - 2].slice(1, -1).toLowerCase();
    if (last.includes("radio")) return "data" + parts.join("");                    // đã ổn định
    if (secondLast.includes("radio")) return "data" + parts.slice(0, -1).join(""); // bỏ đuôi [instance-id]
    return "";
  }

  function formioBaseDataName(name) {
    const text = String(name || "").trim();
    if (!text.startsWith("data[")) return "";
    const parts = text.match(/\[[^\]]+\]/g) || [];
    if (parts.length < 1) return "";
    return "data" + parts[0];
  }

  function formioRadioNameMatches(actualName, expectedName) {
    const actual = String(actualName || "").trim().toLowerCase();
    const expected = String(expectedName || "").trim().toLowerCase();
    if (!actual || !expected) return false;
    if (actual === expected) return true;

    // ƯU TIÊN radio LỒNG (field-key chứa "radio", vd data[khuyetTatNObj][khuyetTatRadioX][id]): so theo
    // STABLE name (đã bỏ đuôi [instance-id]) và phải khớp ĐÚNG field-key. KHÔNG dùng base data[khuyetTatNObj]
    // vì cha (khuyetTatRadio) và các con (khuyetTatRadio1..6) CHUNG base → sẽ khớp nhầm cha↔con, con↔con.
    const actualStable = formioStableRadioName(actual);
    const expectedStable = formioStableRadioName(expected);
    if (actualStable || expectedStable) {
      return (actualStable || actual) === (expectedStable || expected);
    }

    // Field radio ĐƠN (data[key] hoặc data[key][instance-id], key KHÔNG chứa "radio"): khớp theo base.
    const actualBase = formioBaseDataName(actual).toLowerCase();
    const expectedBase = formioBaseDataName(expected).toLowerCase();
    if (actualBase && expectedBase && actualBase === expectedBase) return true;
    if (expectedBase && actual.startsWith(expectedBase + "[")) return true;
    if (actualBase && expected.startsWith(actualBase + "[")) return true;
    return expected.startsWith("data[") && actual.startsWith(expected + "[");
  }

  function readInputLikeValue(names) {
    const candidates = standardNameVariants(Array.isArray(names) ? names : [names]);
    for (const n of candidates) {
      const escaped = CSS.escape(n);
      const el = document.querySelector(`input[name="${escaped}"], textarea[name="${escaped}"], select[name="${escaped}"]`);
      const value = el && String(el.value || "").trim();
      if (value && !isPlaceholderText(value)) return value;
    }
    for (const n of candidates) {
      const escaped = CSS.escape(n);
      const el = document.querySelector(`[formcontrolname="${escaped}"]`);
      const value = el && String(el.value || "").trim();
      if (value && !isPlaceholderText(value)) return value;
    }
    return "";
  }

  function readNgReflectValue(attrName) {
    const el = document.querySelector(`[${attrName}]`);
    return el ? String(el.getAttribute(attrName) || "").trim() : "";
  }

  // [Bắc Ninh] Trang tài khoản VNeID (/vneidsso): đọc ô prefill theo NAME suffix trong portlet
  // `_taikhoan_sso_vneid_` (bỏ hidden). Mốc để BE chọn ĐÚNG người trong giấy tờ upload.
  function readBacNinhAccountValue(key) {
    const nodes = document.querySelectorAll(`[name$="_${key}"]`);
    for (const el of nodes) {
      if (!(el.getAttribute("name") || "").includes("_taikhoan_sso_vneid_")) continue;
      if ((el.getAttribute("type") || "").toLowerCase() === "hidden") continue;
      const val = (el.value || "").trim();
      if (val) return val;
    }
    return "";
  }

  function collectFormContext() {
    const checkbox = document.querySelector('input[type="checkbox"][name="data[isOwnerDossierCheck]"]');
    const combinedVariant = detectCombinedBirthFormVariant();
    return {
      applicantFullname:
        readInputLikeValue("data[fullname]") ||
        readNgReflectValue("ng-reflect-fullname") ||
        // Form eform (vd Xác nhận TTHN, Khai tử): người yêu cầu cổng điền sẵn ở HoVaTenC.
        readInputLikeValue(["HoVaTenC", "NYC_HoVaTen"]) ||
        readBacNinhAccountValue("hoTen"),
      applicantIdentityNumber:
        readInputLikeValue("data[identityNumber]") ||
        readNgReflectValue("ng-reflect-identity-number") ||
        readInputLikeValue(["SoDinhDanhC", "SoGiayToDinhDanhC", "NYC_SoGiayToTuyThan"]) ||
        readBacNinhAccountValue("soDinhDanh"),
      ownerFullname: readInputLikeValue("data[ownerFullname]"),
      ownerIdentityNumber: readInputLikeValue("data[ownerIdentityNumber]"),
      ownerDossierChecked: !!checkbox?.checked,
      ...(combinedVariant || {}),
    };
  }

  function detectCombinedBirthFormVariant() {
    const hasNamedControl = (name) => !!document.querySelector(`[name="${CSS.escape(name)}"]`);
    const birthSignature = ["HoTenKS", "HoTenMeKS", "HoTenChaKS"];
    const recognitionSignature = ["HotenA", "hotenB", "loaiXacNhan"];
    const birthMatches = birthSignature.filter(hasNamedControl);
    const recognitionMatches = recognitionSignature.filter(hasNamedControl);

    let formVariant = "";
    let formSignature = [];
    if (birthMatches.length === birthSignature.length && recognitionMatches.length === 0) {
      formVariant = "birth_registration";
      formSignature = birthMatches;
    } else if (recognitionMatches.length === recognitionSignature.length && birthMatches.length === 0) {
      formVariant = "parent_child_recognition";
      formSignature = recognitionMatches;
    }
    if (!formVariant) return null;

    const titleNode = Array.from(document.querySelectorAll("h1, h2, h3, h4, legend, strong"))
      .find((node) => /khai sinh|nhận cha|nhận mẹ|nhận con/i.test(nodeText(node)));
    return {
      formVariant,
      formTitle: nodeText(titleNode) || document.title || "",
      formSignature,
    };
  }

  function findFormControl(names) {
    for (const n of names) {
      const el = document.querySelector(`[formcontrolname="${CSS.escape(n)}"]`);
      if (el) return el;
    }
    const wanted = new Set(names.map((n) => String(n).toLowerCase()));
    const byFormControl = Array.from(document.querySelectorAll("[formcontrolname]")).find((node) =>
      wanted.has(String(node.getAttribute("formcontrolname") || "").toLowerCase())
    );
    if (byFormControl) return byFormControl;

    // Một số ô Angular chỉ được render động sau khi chọn "Khác" và input con chỉ có `name`
    // (không có formcontrolname trên app-input). Trả container Angular gần nhất để các hàm fill/mark
    // vẫn thao tác giống control thông thường; fallback cuối là chính input.
    for (const n of names) {
      const escaped = CSS.escape(n);
      const named = document.querySelector(
        `input[name="${escaped}"], textarea[name="${escaped}"], select[name="${escaped}"]`
      );
      if (named) return named.closest("app-input, mat-form-field") || named;
    }
    return Array.from(document.querySelectorAll("input[name], textarea[name], select[name]")).map((node) => ({
      node,
      name: String(node.getAttribute("name") || "").toLowerCase(),
    })).find((item) => wanted.has(item.name))?.node || null;
  }

  // Tô VIỀN VÀNG cho field default trên form x-* (legacy). markDefaultsYellow gốc chỉ xử Angular
  // (formcontrolname); ở đây tìm container x-* theo name rồi đổi mọi mark xanh trong đó sang vàng.

  // ============================================================================
  // ENGINE FILL CHO FORM HTML THƯỜNG (input/select/textarea có name)
  // Dùng cho nhóm thủ tục đất đai không render Angular hoặc x-* web-component.
  // ============================================================================

  function standardControlVisible(el) {
    return !!el && (isVisible(standardMarkTarget(el)) || isVisible(el));
  }

  function standardOccurrence(value) {
    const n = Number(value);
    return Number.isInteger(n) && n >= 0 ? n : null;
  }

  function pickStandardControl(elements, occurrence = null) {
    const visible = elements.filter(standardControlVisible);
    const pool = visible.length ? visible : elements;
    const explicitOccurrence = standardOccurrence(occurrence);
    if (explicitOccurrence !== null) return pool[explicitOccurrence] || null;
    return pool.find((el) => !el.disabled) || pool[0] || null;
  }

  function collectStandardInputs(names) {
    const candidates = standardNameVariants(names);
    const found = [];
    const add = (el) => {
      if (el && ["input", "textarea"].includes(el.tagName?.toLowerCase?.()) && !found.includes(el)) found.push(el);
    };
    for (const n of candidates) {
      const escaped = CSS.escape(n);
      document.querySelectorAll(`input[name="${escaped}"], textarea[name="${escaped}"]`).forEach(add);
    }
    for (const n of candidates) {
      const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
      add(document.getElementById("_fc" + base));
      add(document.getElementById(base));
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    Array.from(document.querySelectorAll("input[name], textarea[name]")).forEach((node) => {
      if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
    });
    return found;
  }

  function findStandardInput(names, occurrence = null) {
    return pickStandardControl(collectStandardInputs(names), occurrence);
  }

  function findStandardInputForField(field, candidates, occurrence = null) {
    return findStandardInput(candidates, occurrence) || findStandardDatagridFallbackInput(field);
  }

  function collectStandardSelects(names) {
    const candidates = standardNameVariants(names);
    const found = [];
    const add = (el) => {
      if (el && el.tagName?.toLowerCase?.() === "select" && !found.includes(el)) found.push(el);
    };
    for (const n of candidates) {
      document.querySelectorAll(`select[name="${CSS.escape(n)}"]`).forEach(add);
    }
    for (const n of candidates) {
      const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
      add(document.getElementById("_fc" + base));
      add(document.getElementById(base));
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    Array.from(document.querySelectorAll("select[name]")).forEach((node) => {
      if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
    });
    return found;
  }

  function findStandardSelect(names, occurrence = null) {
    return pickStandardControl(collectStandardSelects(names), occurrence);
  }

  function findStandardSelects(names, occurrence = null) {
    const found = collectStandardSelects(names).filter(standardControlVisible);
    const explicitOccurrence = standardOccurrence(occurrence);
    if (explicitOccurrence !== null) {
      const selected = found[explicitOccurrence];
      return selected ? [selected] : [];
    }
    return found;
  }

  function findStandardCheckbox(names, optionValue = null) {
    const candidates = standardNameVariants(names);
    const wantedOption = optionValue == null ? "" : String(optionValue);
    for (const n of candidates) {
      const selector = `input[type="checkbox"][name="${CSS.escape(n)}"]`;
      const el = wantedOption
        ? Array.from(document.querySelectorAll(selector)).find((node) => String(node.value) === wantedOption)
        : document.querySelector(selector);
      if (el) return el;
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    return Array.from(document.querySelectorAll('input[type="checkbox"][name]')).find((node) =>
      wanted.has(String(node.getAttribute("name") || "").toLowerCase()) &&
      (!wantedOption || String(node.value) === wantedOption)
    ) || null;
  }

  function findStandardRadio(names) {
    const candidates = standardNameVariants(names);
    for (const n of candidates) {
      const el = document.querySelector(`input[type="radio"][name="${CSS.escape(n)}"]`);
      if (el) return el;
    }
    return Array.from(document.querySelectorAll('input[type="radio"][name]')).find((node) =>
      candidates.some((name) => formioRadioNameMatches(node.getAttribute("name"), name))
    ) || null;
  }

  function standardMarkTarget(el) {
    return el?.closest?.(".form-group") || el?.parentElement || el;
  }

  function refreshStandardSelectPlugins(select) {
    if (!window.jQuery) return;
    try {
      const $el = window.jQuery(select);
      $el.trigger("change");
      if (typeof $el.selectpicker === "function") $el.selectpicker("refresh");
      if (typeof $el.select2 === "function") $el.trigger("change.select2");
    } catch (e) {
      console.warn("[AutoFill-STD] Không refresh được select plugin:", e);
    }
  }

  function fillStandardInput(el, value, options = {}) {
    if (!el) return false;
    setNativeValue(el, value, {
      typing: true,
      commit: options.commit !== false,
      change: options.change,
    });
    markFilled(standardMarkTarget(el));
    return true;
  }

  function parseDmyDate(text) {
    const m = String(text || "").trim().match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/);
    if (!m) return null;
    const d = +m[1], mo = +m[2], y = +m[3];
    if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
    const obj = new Date(y, mo - 1, d);
    return isNaN(obj.getTime()) ? null : obj;
  }

  function fillStandardDate(el, value, opts = {}) {
    if (!el) return false;
    const text = String(value ?? "").trim();
    if (!text) return false;
    const group = standardMarkTarget(el);

    // Form.io datetime dùng flatpickr: set .value trực tiếp vào ô bị flatpickr GHI ĐÈ lại rỗng (→ báo
    // "bắt buộc"). Cách ổn định DUY NHẤT là gọi instance flatpickr `setDate` (tự set cả ô ẩn + ô hiển thị
    // theo dateFormat riêng của form, không quan trọng d/m/Y hay ISO, + bắn onChange cho Form.io/Angular).
    // Instance có thể nằm trên input ẩn HOẶC ô hiển thị (altInput) trong cùng component → tìm rộng.
    const dtContainer = el.closest?.(".formio-component-datetime") || el.closest?.(".formio-component") || group;
    const fpHost = el._flatpickr
      ? el
      : (dtContainer && Array.from(dtContainer.querySelectorAll("input")).find((n) => n._flatpickr))
      || (el.closest?.(".flatpickr-input")?._flatpickr && el.closest(".flatpickr-input"))
      || null;
    const fp = fpHost?._flatpickr;
    const dateObj = parseDmyDate(text);
    if (fp && dateObj) {
      // setDate GÁN giá trị (ô ẩn + ô hiển thị) TRƯỚC khi bắn onChange. Nếu onChange của TRANG lỗi sẵn
      // (vd cổng này custom-function "thongTinChung" throw liên tục) thì exception xảy ra SAU khi giá trị
      // đã set → vẫn coi là THÀNH CÔNG, KHÔNG rơi xuống gõ text (gõ dd/mm/yyyy vào ô format Y-m-d sẽ sai).
      try {
        fp.setDate(dateObj, true);   // triggerChange=true
      } catch (e) {
        console.warn("[AutoFill-STD] flatpickr.setDate onChange trang lỗi (giá trị vẫn được set):", e);
      }
      markFilled(group);
      return true;
    }

    // Không lấy được instance flatpickr → fallback GÕ giá trị. Định dạng theo LOẠI ô (BE báo qua opts.iso):
    // - opts.iso=true (ô datetime lưu ISO "Y-m-dTH:i:S", vd tuNgay/denNgay): set ISO + hiển thị "Y-m-d
    //   12:00 AM" (giờ mặc định 00:00). KHÔNG gõ dd/mm/yyyy (ô format Y-m-d sẽ parse sai → 2008-08-26).
    // - mặc định (ô lưu dd/MM/yyyy, vd birthday/identityDate): gõ dd/mm/yyyy như cũ.
    const visible = group?.querySelector?.('input:not([type="hidden"])');
    if (opts.iso && dateObj) {
      const pad = (n) => String(n).padStart(2, "0");
      const ymd = `${dateObj.getFullYear()}-${pad(dateObj.getMonth() + 1)}-${pad(dateObj.getDate())}`;
      setNativeValue(el, `${ymd}T00:00:00`, { typing: false, commit: true });
      if (visible && visible !== el) setNativeValue(visible, `${ymd} 12:00 AM`, { typing: false, commit: true });
      markFilled(group);
      return true;
    }
    setNativeValue(el, text, { typing: true, commit: true });
    if (visible && visible !== el) setNativeValue(visible, text, { typing: true, commit: true });
    markFilled(group);
    return true;
  }

  function choiceDisplayText(el) {
    if (!el) return "";
    const span = el.querySelector?.("span");
    const text = span ? span.textContent : el.textContent;
    return String(text || "").replace(/Remove item:.*/i, "").trim();
  }

  function foldChoiceText(value) {
    return norm(String(value || "")
      .replace(/Đ/g, "D")
      .replace(/đ/g, "d")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      // Đồng nhất MỌI dấu gạch (hyphen/en-dash/em-dash…) + khoảng trắng quanh → 1 space.
      // Tên xã sáp nhập "Phường Xuân Hương – Đà Lạt" (OCR ra en-dash) vs option "… - Đà Lạt"
      // (hyphen) trước đây không khớp → select địa bàn quay vòng chọn mãi không được.
      .replace(/\s*[-–—‐‑]+\s*/g, " "));
  }

  function stripAdminPrefix(value) {
    let text = String(value || "");
    let prev = "";
    while (text !== prev) {
      prev = text;
      text = text.replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|thi xa|huyen|quan)\s+/i, "");
    }
    return text.trim();
  }

  function choiceTextVariants(value) {
    const raw = norm(value);
    const folded = foldChoiceText(value);
    return [raw, folded, stripAdminPrefix(raw), stripAdminPrefix(folded)]
      .filter(Boolean)
      .filter((v, i, arr) => arr.indexOf(v) === i);
  }

  function choiceMatches(el, value) {
    const raw = String(value ?? "");
    const wants = choiceTextVariants(raw);
    const texts = choiceTextVariants(choiceDisplayText(el));
    const dataValues = choiceTextVariants(el?.getAttribute?.("data-value") || "");
    const foldedWant = foldChoiceText(raw);
    const genderValue = foldedWant === "nam" ? "1" : (foldedWant === "nu" ? "2" : "");
    return (
      dataValues.some((v) => wants.includes(v)) ||
      (!!genderValue && dataValues.includes(genderValue)) ||
      texts.some((text) => wants.some((want) => text === want || text.includes(want) || want.includes(text)))
    );
  }

  // Chấm ĐIỂM khớp option (cao = khớp tốt hơn). Dùng để CHỌN option tốt nhất thay cho .find() —
  // .find() lấy option ĐẦU khớp lỏng, nên "Điện Bàn Đông" bị chọn nhầm "Điện Bàn" (option ngắn là
  // CON của giá trị cần). Ưu tiên: khớp data-value/exact text > option CHỨA want > want CHỨA option.
  function choiceScore(optText, optDataValue, value) {
    const wants = choiceTextVariants(String(value ?? ""));
    const texts = choiceTextVariants(optText || "");
    const dataValues = choiceTextVariants(optDataValue || "");
    const foldedWant = foldChoiceText(String(value ?? ""));
    const genderValue = foldedWant === "nam" ? "1" : (foldedWant === "nu" ? "2" : "");
    if (dataValues.some((v) => wants.includes(v))) return 4;
    if (genderValue && dataValues.includes(genderValue)) return 4;
    if (texts.some((t) => wants.includes(t))) return 3;                    // text == want (chính xác)
    if (texts.some((t) => wants.some((w) => w && t.includes(w)))) return 2; // option CHỨA want
    if (texts.some((t) => wants.some((w) => t && w.includes(t)))) return 1; // want CHỨA option (lỏng)
    return 0;
  }

  // Chọn option KHỚP TỐT NHẤT trong danh sách. getText/getDataValue tuỳ loại phần tử (DOM option,
  // Choices item, hay object Form.io). Hoà điểm → option có TEXT DÀI HƠN (cụ thể hơn) thắng.
  function bestChoiceOption(options, value, getText, getDataValue) {
    let best = null, bestScore = 0, bestLen = -1;
    for (const o of options) {
      const text = getText ? getText(o) : choiceDisplayText(o);
      const dv = getDataValue ? getDataValue(o) : (o && o.getAttribute ? o.getAttribute("data-value") : "");
      const score = choiceScore(text, dv, value);
      if (score <= 0) continue;
      const len = foldChoiceText(text || "").length;
      if (score > bestScore || (score === bestScore && len > bestLen)) {
        best = o; bestScore = score; bestLen = len;
      }
    }
    return best;
  }

  function choiceSearchTerms(select, value) {
    const raw = String(value ?? "").trim();
    if (!raw) return [""];
    const terms = [raw];
    // Chuỗi dài (vd tên cơ quan cấp "Cục Cảnh sát Quản lý hành chính về trật tự xã hội") hay làm
    // fuzzy-search của Choices.js trượt → option không lọt vào danh sách render. Thử thêm cụm ngắn
    // đầu để LỌC ra, việc so khớp cuối vẫn dùng giá trị đầy đủ nên không chọn nhầm.
    const words = raw.split(/\s+/);
    if (words.length > 3) {
      const push = (t) => { if (t && !terms.includes(t)) terms.push(t); };
      push(words.slice(0, 3).join(" "));
      push(words.slice(0, 2).join(" "));
    }
    return terms;
  }

  function isAreaSelectName(name) {
    // village/ward = ô Phường/Xã (con cascade của Tỉnh) trên form Form.io moha — phải nhận là
    // ô địa chỉ để điền SAU Tỉnh và được retry chờ options con load. Thiếu thì điền hụt dù giá trị đúng.
    // maphuongxa: ô Phường/Xã của eForm Lai Châu (CongDan_maPhuongXa) — "maxa" KHÔNG khớp "maphuongxa"
    //   nên phải liệt kê riêng, nếu không ô Xã điền hụt do options con load bất đồng bộ ("lúc được lúc không").
    // tinhthanhphonopdon: ô "Tỉnh/TP nộp đơn" (Form.io ATTP cấp lại) là Choices.js REMOTE-SEARCH — chỉ vài
    //   option mặc định, phải gõ để nạp thêm qua API. Không nhận là area-select → chỉ thử 1 lần ~600ms,
    //   remote nạp chưa kịp thì bỏ. Nhận là area-select để được retry + timeout dài như ô Tỉnh.
    // tinhtp/px1/tinhthanhpho/quanhuyen: các ô Tỉnh/Phường-xã ở cổng Bộ GD&ĐT dvc.moet.gov.vn (Cấp bản sao
    //   văn bằng) — field-key riêng, phải nhận là area-select để cascade Tỉnh→Phường/Xã điền đủ.
    // change_owner_type_idfld: ô "Lý do thay đổi thông tin chủ hộ kinh doanh" (HkdOnline) là select con
    //   cascade theo "Loại đăng ký thay đổi" (CHANGE_OWNER_TYPE_TITLE_IDFld) — danh sách lý do nạp lại
    //   SAU khi đổi Loại, không nhận area-select thì thử 1 lần rồi bỏ, hụt mất "Khác" dù giá trị đúng.
    return /province|district|village|ward|matinh|maphuongxa|maxa|tinhthanhphonopdon|tinhthanhpho|quanhuyen|tinhtp|px1|country_idfld|city_idfld|ward_idfld|street_numberfld|addr[a-z]*ctl|change_owner_type_idfld/.test(String(name || "").toLowerCase());
  }

  function isAreaSelectField(f) {
    return f?.comp === "dom-select" && fieldCandidates(f).some(isAreaSelectName);
  }

  function isPostbackAddressField(f) {
    return fieldCandidates(f).some(isAreaSelectName);
  }

  function dispatchChoiceMouse(el, type) {
    // button 0 (chuột trái), buttons 1 khi nhấn giữ — vài handler bỏ qua click nếu button != 0.
    const init = { bubbles: true, cancelable: true, view: window, button: 0, buttons: type.endsWith("down") ? 1 : 0 };
    try {
      if (typeof PointerEvent === "function" && type.startsWith("pointer")) {
        el.dispatchEvent(new PointerEvent(type, init));
      } else {
        el.dispatchEvent(new MouseEvent(type, init));
      }
    } catch {
      el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
    }
  }

  function choicesVisibleOptions(choices) {
    return Array.from(choices?.querySelectorAll?.(".choices__item--choice") || [])
      .filter((o) => !o.classList.contains("has-no-choices"));
  }

  function choicesListSignature(choices) {
    return choicesVisibleOptions(choices).map(choiceDisplayText).join(" | ");
  }

  function choicesHasNoChoices(choices) {
    return !!choices?.querySelector?.(".choices__item--choice.has-no-choices");
  }

  function choicesDropdownOpen(choices) {
    return !!(
      choices?.classList?.contains("is-open") ||
      choices?.querySelector?.('.choices__list--dropdown[aria-expanded="true"]')
    );
  }

  function setInputValueDirect(el, value) {
    const text = String(value ?? "");
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, text);
    else el.value = text;
  }

  function dispatchPasteEvent(el, text) {
    try {
      const ev = new ClipboardEvent("paste", { bubbles: true, cancelable: true });
      Object.defineProperty(ev, "clipboardData", {
        get: () => ({ getData: () => String(text ?? "") }),
      });
      el.dispatchEvent(ev);
    } catch {
      el.dispatchEvent(new Event("paste", { bubbles: true, cancelable: true }));
    }
  }

  const STANDARD_AREA_FIELD_BUDGET_MS = 5000;
  const STANDARD_AREA_STABILIZE_BUDGET_MS = 1800;

  function standardSelectBudgetLeft(deadline = 0) {
    return deadline ? deadline - Date.now() : Infinity;
  }

  function standardSelectWaitMs(deadline, requested) {
    if (!deadline) return requested;
    return Math.max(0, Math.min(requested, standardSelectBudgetLeft(deadline)));
  }

  async function waitForStandardSelect(fn, timeout, interval, deadline = 0) {
    const allowed = standardSelectWaitMs(deadline, timeout);
    if (allowed <= 0) return null;
    return waitFor(fn, allowed, Math.min(interval, allowed));
  }

  async function sleepForStandardSelect(delay, deadline = 0) {
    const allowed = standardSelectWaitMs(deadline, delay);
    if (allowed <= 0) return false;
    await sleep(allowed);
    return allowed >= delay;
  }

  const searchedStandardSelects = new WeakSet();

  async function writeChoicesSearch(search, raw, choices, deadline = 0, select = null) {
    if (!search || search.disabled) return false;
    const text = String(raw ?? "");
    if (typeof search.focus === "function") search.focus();
    dispatchChoiceMouse(search, "pointerdown");
    dispatchChoiceMouse(search, "mousedown");
    dispatchChoiceMouse(search, "mouseup");
    dispatchChoiceMouse(search, "click");

    // Choices.js trên Form.io thỉnh thoảng không consume việc set value một phát:
    // input có chữ nhưng dropdown vẫn giữ list mặc định. Do đó mô phỏng paste trước,
    // nếu list không đổi mới fallback sang nhập từng ký tự.
    setInputValueDirect(search, "");
    dispatchInputEvent(search, "beforeinput", { data: null, inputType: "deleteContentBackward" });
    dispatchInputEvent(search, "input", { data: null, inputType: "deleteContentBackward" });
    search.dispatchEvent(new Event("change", { bubbles: true }));
    await sleepForStandardSelect(60, deadline);

    const before = choicesListSignature(choices);
    if (!text) return true;

    dispatchPasteEvent(search, text);
    dispatchInputEvent(search, "beforeinput", { data: text, inputType: "insertFromPaste" });
    setInputValueDirect(search, text);
    dispatchInputEvent(search, "input", { data: text, inputType: "insertFromPaste" });
    dispatchKeyboardEvent(search, "keyup", text.slice(-1) || "Unidentified");
    search.dispatchEvent(new Event("change", { bubbles: true }));

    const applied = await waitForStandardSelect(() => {
      if (String(search.value || "") !== text) return null;
      const after = choicesListSignature(choices);
      return after !== before || choicesHasNoChoices(choices) ? true : null;
    }, 450, 50, deadline);
    if (select) searchedStandardSelects.add(select);
    if (applied) return true;

    setInputValueDirect(search, "");
    dispatchInputEvent(search, "input", { data: null, inputType: "deleteContentBackward" });
    await sleepForStandardSelect(50, deadline);
    let typed = "";
    for (const ch of Array.from(text)) {
      typed += ch;
      dispatchKeyboardEvent(search, "keydown", ch);
      dispatchKeyboardEvent(search, "keypress", ch);
      dispatchInputEvent(search, "beforeinput", { data: ch, inputType: "insertText" });
      setInputValueDirect(search, typed);
      dispatchInputEvent(search, "input", { data: ch, inputType: "insertText" });
      dispatchKeyboardEvent(search, "keyup", ch);
      if (!await sleepForStandardSelect(8, deadline)) break;
    }
    search.dispatchEvent(new Event("change", { bubbles: true }));
    await waitForStandardSelect(() => {
      const after = choicesListSignature(choices);
      return after !== before || choicesHasNoChoices(choices) ? true : null;
    }, 450, 50, deadline);
    if (select) searchedStandardSelects.add(select);
    return true;
  }

  async function openChoicesDropdown(choices, raw, deadline = 0, select = null) {
    const opener =
      choices.querySelector(".form-control.ui.selection.dropdown, .form-control, .choices__inner, [role='combobox']") ||
      choices.querySelector(".choices__list--single") ||
      choices;
    if (!choicesDropdownOpen(choices)) {
      if (typeof opener.focus === "function") opener.focus();
      ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => dispatchChoiceMouse(opener, type));
      await waitForStandardSelect(() => choicesDropdownOpen(choices), 500, 40, deadline);
    }
    const search = await waitForStandardSelect(() => {
      const input = choices.querySelector(".choices__input--cloned");
      return input && !input.disabled ? input : null;
    }, 500, 40, deadline);
    if (search && !search.disabled) {
      await writeChoicesSearch(search, raw, choices, deadline, select);
    }
  }

  function currentChoicesValue(choices) {
    return choiceDisplayText(choices?.querySelector?.(".choices__list--single .choices__item"));
  }

  function currentStandardSelectMatches(select, value) {
    if (!select) return false;
    const group = standardMarkTarget(select);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    const currentChoice = currentChoicesValue(choices);
    if (currentChoice && !isPlaceholderText(currentChoice)) {
      return choiceMatches({ textContent: currentChoice, getAttribute: () => "" }, value);
    }
    const selected = select.selectedOptions?.[0];
    const selectedText = selected ? selected.textContent : "";
    return !!selectedText && !isPlaceholderText(selectedText) && choiceMatches(selected, value);
  }

  function formioKeyFromSelect(select, names = []) {
    const candidates = [select?.name, ...(Array.isArray(names) ? names : [])].filter(Boolean);
    for (const raw of candidates) {
      // Form.io key = segment trong cặp [] CUỐI CÙNG của name. Hỗ trợ cả key PHẲNG data[province]
      // lẫn key LỒNG data[panel_caNhanToChuc][dichVu] (getComponent dùng leaf key). Key phẳng cho leaf
      // y hệt regex cũ nên KHÔNG đổi hành vi thủ tục hiện có; chỉ THÊM khả năng khớp select lồng panel.
      const segments = [...String(raw || "").trim().matchAll(/\[([^\]]+)\]/g)].map((m) => m[1]);
      const leaf = segments.length ? segments[segments.length - 1] : "";
      if (leaf && leaf !== "data" && !leaf.includes("$")) return leaf;
    }
    for (const raw of candidates) {
      const text = String(raw || "").trim();
      if (text && !text.includes("[") && !text.includes("$")) return text;
    }
    return "";
  }

  function formioOptionText(option) {
    if (!option) return "";
    if (typeof option === "string") return option;
    if (typeof option !== "object") return String(option ?? "");
    const value = option.value;
    return String(
      option.label ||
      option.name ||
      option.text ||
      value?.label ||
      value?.name ||
      value?.text ||
      (typeof value === "string" ? value : "") ||
      ""
    ).replace(/<[^>]+>/g, "");
  }

  function formioFindHolderNear(el) {
    const roots = [];
    let node = el;
    while (node) {
      const ctx = node.__ngContext__ || node.__ng_context__ || node.ngContext;
      if (ctx) roots.push(ctx);
      node = node.parentElement;
    }
    if (!roots.length) return null;

    const seen = new WeakSet();
    const scan = (obj, depth = 0) => {
      if (!obj || typeof obj !== "object" || seen.has(obj) || depth > 6) return null;
      seen.add(obj);
      if (obj.submission?.data && obj.formio?.getComponent) return obj;

      let props = [];
      try { props = Object.getOwnPropertyNames(obj).slice(0, 180); } catch { return null; }
      for (const k of props) {
        let value;
        try { value = obj[k]; } catch { continue; }
        const hit = scan(value, depth + 1);
        if (hit) return hit;
      }
      if (Array.isArray(obj)) {
        for (const value of obj.slice(0, 180)) {
          const hit = scan(value, depth + 1);
          if (hit) return hit;
        }
      }
      return null;
    };

    for (const root of roots) {
      const hit = scan(root);
      if (hit) return hit;
    }
    return null;
  }

  function formioOptionToValue(option, comp = null) {
    if (!option || typeof option !== "object") return option;
    if (option.value && typeof option.value === "object") return option.value;
    if (option.name) return { name: option.name, id: option.id || option.name };
    if (option.value !== undefined && comp?.component?.dataSrc === "values") return option.value;
    if (option.value !== undefined && option.label) return { label: option.label, value: option.value };
    return option.value !== undefined ? option.value : option;
  }

  function knownIdentityAgencyValue(value) {
    const folded = foldChoiceText(value);
    const canonical =
      folded === "bo cong an" ? "Bộ Công an" :
        folded === "giay to khac" ? "Giấy tờ khác" :
          folded.includes("cuc canh sat quan ly hanh chinh ve trat tu xa hoi")
            ? "Cục Cảnh sát quản lý hành chính về trật tự xã hội" :
            "";
    return canonical ? { name: canonical, id: canonical } : null;
  }

  function ensureFormioSelectOption(comp, label, value) {
    const option = { label, value };
    if (Array.isArray(comp.selectOptions) && !comp.selectOptions.some((o) => choiceMatches({ textContent: formioOptionText(o), getAttribute: () => "" }, label))) {
      comp.selectOptions.push(option);
    }
    if (Array.isArray(comp.items) && !comp.items.some((o) => choiceMatches({ textContent: formioOptionText(o), getAttribute: () => "" }, label))) {
      comp.items.push(option);
    }
    const values = comp.component?.data?.values;
    if (Array.isArray(values) && !values.some((o) => choiceMatches({ textContent: formioOptionText(o), getAttribute: () => "" }, label))) {
      values.push(value);
    }
    return option;
  }

  async function fillFormioSelectComponent(select, value, names = [], deadline = 0) {
    if (!select) return false;
    const key = formioKeyFromSelect(select, names);
    if (!key) return false;
    const holder = formioFindHolderNear(select);
    const comp = holder?.formio?.getComponent?.(key);
    if (!holder || !comp) return false;

    const raw = String(value ?? "").trim();
    if (!raw) return false;
    const findOption = () => {
      const all = [
        ...(Array.isArray(comp.selectOptions) ? comp.selectOptions : []),
        ...(Array.isArray(comp.items) ? comp.items : []),
      ];
      return bestChoiceOption(all, raw, (option) => formioOptionText(option), () => "");
    };

    let option = null;
    const attempts = isAreaSelectName(select.name) ? 8 : 4;
    for (let i = 0; i < attempts; i++) {
      if (standardSelectBudgetLeft(deadline) <= 0) break;
      option = findOption();
      if (option) break;
      try { comp.updateItems?.(); } catch { /* ignore */ }
      try { comp.refreshItems?.(); } catch { /* ignore */ }
      if (!await sleepForStandardSelect(isAreaSelectName(select.name) ? 250 : 120, deadline)) break;
    }

    let finalValue = option ? formioOptionToValue(option, comp) : null;
    if (!finalValue && key === "identityAgency") {
      finalValue = knownIdentityAgencyValue(raw);
      if (finalValue) option = ensureFormioSelectOption(comp, finalValue.name, finalValue);
    }
    if (!finalValue) return false;

    holder.submission.data[key] = finalValue;
    try { comp.setValue(finalValue, { modified: true }); } catch (e) { console.warn("[AutoFill-STD] Form.io setValue lỗi:", key, e); }
    try { comp.updateValue(finalValue, { modified: true }); } catch (e) { console.warn("[AutoFill-STD] Form.io updateValue lỗi:", key, e); }
    try { comp.triggerChange?.({ modified: true }); } catch { /* ignore */ }
    try { comp.redraw?.(); } catch (e) { console.warn("[AutoFill-STD] Form.io redraw lỗi:", key, e); }

    const ok = await waitForStandardSelect(() => currentStandardSelectMatches(select, raw) ||
      choiceMatches({ textContent: formioOptionText(comp.dataValue || holder.submission.data[key]), getAttribute: () => "" }, raw),
      800,
      80,
      deadline
    );
    if (!ok) return false;
    markFilled(standardMarkTarget(select));
    return true;
  }

  // comp "dom-vehicle-add" (thủ tục "Cấp GP liên vận Việt-Lào") — bảng "Danh sách phương tiện":
  // - Biển số CÓ trong ô "Chọn phương tiện" (BienSoXeData, nạp từ hồ sơ xe của tài khoản) → chọn + bấm
  //   "Thêm" (themxe) để cổng TỰ đổ dòng đầy đủ.
  // - Biển số KHÔNG có trong tài khoản → bấm "Thêm mới" tạo dòng trống rồi ĐIỀN từng ô của dòng từ dữ liệu xe.
  // field.value = JSON mảng xe (bienSo/trongTai/namSanXuat/nhanHieu/soKhung/soMay/mauSon/hinhThucHoatDong/
  // cuaKhau/tuNgay/denNgay/nienHan). field.addButtonName = name nút thêm.
  function _plateKey(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/gi, "").toLowerCase();
  }

  function _datagridRows() {
    return [...document.querySelectorAll('.formio-component-DanhSachPhuongTien tbody tr[ref="datagrid-DanhSachPhuongTien-row"]')];
  }

  function _rowIndex(row) {
    const el = row?.querySelector('[name*="[DanhSachPhuongTien]["]');
    const m = el && String(el.getAttribute("name") || "").match(/\[DanhSachPhuongTien\]\[(\d+)\]/);
    return m ? m[1] : null;
  }

  function _rowBienSoInput(idx) {
    return idx == null
      ? null
      : document.querySelector(`[name="${CSS.escape(`data[panel_caNhanToChuc][DanhSachPhuongTien][${idx}][BienSoXe]`)}"]`);
  }

  // Đọc giá trị hiển thị hiện tại của 1 ô (input value hoặc Choices single item) để BIẾT ô đã điền đúng chưa.
  function _rowCellValue(base, sub) {
    const el = document.querySelector(`[name="${CSS.escape(base + sub)}"]`);
    if (!el) return "";
    const group = standardMarkTarget(el);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (choices) {
      const label = currentChoicesValue(choices);
      return label && !isPlaceholderText(label) ? label : "";
    }
    return String(el.value || "").trim();
  }

  function _cellMatches(base, sub, val) {
    if (val == null || val === "") return true;
    const cur = _rowCellValue(base, sub);
    if (!cur) return false;
    return choiceMatches({ textContent: cur, getAttribute: () => "" }, String(val));
  }

  // Điền các ô của MỘT dòng datagrid (theo index) từ object xe. Khớp ô bằng NAME đầy đủ (duy nhất theo index).
  //
  // Form.io datagrid VẼ LẠI (redraw) cả dòng sau MỖI thay đổi → ô điền trước có thể bị reset khi điền ô
  // sau (đặc biệt Choices select mở dropdown). Trong ISOLATED world không set được model qua API, nên
  // dùng vòng VERIFY-REFILL: điền → chờ ổn định → kiểm ô nào còn thiếu → điền lại, lặp tới khi đủ.
  async function _fillDatagridVehicleRow(idx, v) {
    const base = `data[panel_caNhanToChuc][DanhSachPhuongTien][${idx}]`;
    const q = (sub) => document.querySelector(`[name="${CSS.escape(base + sub)}"]`);
    const setText = (sub, val) => { if (val == null || val === "") return; const el = q(sub); if (el) fillStandardInput(el, String(val)); };
    const setDate = (sub, val) => { if (!val) return; const el = q(sub); if (el) fillStandardDate(el, String(val)); };
    const setSel = async (sub, val) => {
      if (!val) return; const name = base + sub; const el = document.querySelector(`select[name="${CSS.escape(name)}"]`);
      if (el) await fillStandardSelectAny(el, String(val), [name], 0);  // datagrid select → pickChoicesItem theo đúng element dòng
    };

    const textJobs = [
      ["[BienSoXe]", v.bienSo], ["[SoChoNgoi]", v.trongTai], ["[NamSanXuat]", v.namSanXuat],
      ["[NhanHieu]", v.nhanHieu], ["[SoKhung]", v.soKhung], ["[SoMay]", v.soMay],
      ["[NienHanSuDung]", v.nienHan || "0"],
    ];
    const dateJobs = [["[NgayCap]", v.tuNgay], ["[NgayHetHan]", v.denNgay]];
    const selJobs = [
      ["[MauSon]", v.mauSon], ["[HinhThucHoatDong]", v.hinhThucHoatDong], ["[CuaKhau]", v.cuaKhau],
    ];
    if (v.loaiPhuongTien) selJobs.push(["[LoaiPhuongTien]", v.loaiPhuongTien]);

    // Lặp tới 4 vòng: mỗi vòng CHỈ điền ô nào đang THIẾU (đã đúng thì bỏ qua → không kích redraw thừa).
    for (let attempt = 0; attempt < 4; attempt++) {
      for (const [sub, val] of textJobs) if (!_cellMatches(base, sub, val)) { setText(sub, val); await sleep(60); }
      for (const [sub, val] of dateJobs) if (!_cellMatches(base, sub, val)) { setDate(sub, val); await sleep(60); }
      // Chờ redraw do text/date settle rồi mới đụng Choices (mở dropdown lúc đang redraw sẽ trượt).
      await sleep(400);
      for (const [sub, val] of selJobs) {
        if (_cellMatches(base, sub, val)) continue;
        await setSel(sub, val);
        await sleep(250);  // để redraw sau khi chọn select này settle trước khi sang ô kế.
      }
      await sleep(300);
      const allDone =
        textJobs.every(([s, val]) => _cellMatches(base, s, val)) &&
        dateJobs.every(([s, val]) => _cellMatches(base, s, val)) &&
        selJobs.every(([s, val]) => _cellMatches(base, s, val));
      if (allDone) break;
    }
  }

  async function fillVehicleAddRows(field, candidates) {
    let vehicles = [];
    try {
      const parsed = JSON.parse(String(field?.value || ""));
      if (Array.isArray(parsed)) vehicles = parsed.filter((v) => v && typeof v === "object");
    } catch {
      // Tương thích ngược: value là danh sách biển số ngăn "|".
      vehicles = String(field?.value || "").split("|").map((s) => s.trim()).filter(Boolean).map((b) => ({ bienSo: b }));
    }
    if (!vehicles.length) return false;

    const rowCount = () => _datagridRows().length;
    const filledBienSo = () =>
      _datagridRows().filter((r) => { const el = _rowBienSoInput(_rowIndex(r)); return el && String(el.value || "").trim(); }).length;
    const findAddButton = () =>
      (field?.addButtonName ? document.querySelector(`button[name="${CSS.escape(field.addButtonName)}"]`) : null) ||
      document.querySelector(".formio-component-themxe button");
    const emptyRow = () =>
      _datagridRows().find((r) => { const el = _rowBienSoInput(_rowIndex(r)); return el && !String(el.value || "").trim(); });

    let done = 0;
    for (const v of vehicles) {
      const select =
        findStandardSelect(candidates, 0) || document.querySelector(`select[name="${CSS.escape(field.name)}"]`);
      const container = select ? standardMarkTarget(select) : null;
      const optionTexts = container
        ? [...container.querySelectorAll('.choices__list--dropdown [role="option"], .choices__item--choice')]
          .map((o) => (o.textContent || "").trim())
          .filter(Boolean)
        : [];
      const want = _plateKey(v.bienSo);
      const optionText = want
        ? optionTexts.find((t) => _plateKey(t) === want) ||
        optionTexts.find((t) => _plateKey(t) && (_plateKey(t).includes(want) || want.includes(_plateKey(t))))
        : null;

      if (select && optionText) {
        // (A) Xe CÓ trong tài khoản → chọn biển số + bấm Thêm, cổng tự đổ dòng.
        const before = { rows: rowCount(), filled: filledBienSo() };
        const picked =
          (await fillFormioSelectComponent(select, optionText, candidates)) ||
          (await fillStandardSelectAny(select, optionText, candidates, 0));
        const btn = findAddButton();
        if (picked && btn) {
          btn.click();
          await waitFor(() => rowCount() > before.rows || filledBienSo() > before.filled, 4000, 150);
          done++;
          continue;
        }
      }

      // (B) Xe KHÔNG có trong tài khoản → dùng dòng trống sẵn có, nếu không có thì bấm "Thêm mới".
      if (!v.bienSo) { console.warn("[AutoFill-STD] Bỏ qua 1 phương tiện thiếu biển số."); continue; }
      let row = emptyRow();
      if (!row) {
        const btn = findAddButton();
        if (!btn) { console.warn("[AutoFill-STD] Không thấy nút Thêm mới"); break; }
        const before = rowCount();
        btn.click();
        await waitFor(() => rowCount() > before, 4000, 150);
        const rows = _datagridRows();
        row = rows[rows.length - 1];
      }
      const idx = _rowIndex(row);
      if (idx == null) { console.warn("[AutoFill-STD] Không xác định được dòng phương tiện mới."); continue; }
      console.warn(`[AutoFill-STD] Biển số "${v.bienSo}" không có trong tài khoản → thêm mới + điền tay dòng ${idx}.`);
      await _fillDatagridVehicleRow(idx, v);
      done++;
    }
    return done > 0;
  }
  function shouldPreferFormioSelectComponent(select, names = []) {
    if (!select) return false;
    const group = standardMarkTarget(select);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (!choices?.classList?.contains("formio-choices")) return false;

    const key = formioKeyFromSelect(select, names).toLowerCase();
    const selectName = String(select.name || "");
    return (
      isAreaSelectName(selectName) ||
      key === "nation" ||
      key.includes("identityagency")
    );
  }

  function standardFieldIdentity(field) {
    const name = fieldCandidates(field)[0] || field?.name || "";
    const occurrence = standardOccurrence(field?.occurrence);
    return `${name}::${occurrence === null ? "auto" : occurrence}`;
  }

  function standardFieldDeadline(deadlines, field, budgetMs = STANDARD_AREA_FIELD_BUDGET_MS) {
    const key = standardFieldIdentity(field);
    if (!deadlines.has(key)) deadlines.set(key, Date.now() + budgetMs);
    return deadlines.get(key);
  }

  // Chỉ kết luận "không có giá trị" sớm khi nguồn option đã có tính quyết định:
  // - Form.io dùng danh sách tĩnh values/json;
  // - native select thuần đã có option;
  // - hoặc Choices.js đã thực hiện tìm kiếm và trả "không có lựa chọn".
  // Nguồn URL/resource/custom chưa ổn định vẫn được chờ hết ngân sách RIÊNG của ô.
  function standardSelectOptionState(select, value, names = []) {
    if (!select) return { settled: false, hasValue: false };
    const texts = [];
    const key = formioKeyFromSelect(select, names);
    const holder = key ? formioFindHolderNear(select) : null;
    const comp = holder?.formio?.getComponent?.(key);
    if (Array.isArray(comp?.selectOptions)) comp.selectOptions.forEach((o) => texts.push(formioOptionText(o)));
    if (Array.isArray(comp?.items)) comp.items.forEach((o) => texts.push(formioOptionText(o)));

    const group = standardMarkTarget(select);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (choices) choicesVisibleOptions(choices).forEach((o) => texts.push(choiceDisplayText(o)));
    Array.from(select.options || []).forEach((o) => texts.push(o.textContent));

    const real = [...new Set(texts.filter(Boolean))].filter((text) => {
      const folded = foldChoiceText(text);
      return folded && folded !== "chon" && !folded.includes("chon ") && !folded.startsWith("-");
    });
    const hasValue = real.some((text) => choiceMatches({ textContent: text, getAttribute: () => "" }, value));
    const dataSrc = String(comp?.component?.dataSrc || "").toLowerCase();
    const staticSource = dataSrc === "values" || dataSrc === "json";
    const hasChoicesSearch = !!choices?.querySelector?.(".choices__input--cloned");
    const plainNativeSource = !comp && !hasChoicesSearch && real.length > 0;
    const searchedEmpty = searchedStandardSelects.has(select) && choicesHasNoChoices(choices);
    const loading = !!(
      comp?.loading || comp?.isLoading ||
      choices?.classList?.contains("is-loading") ||
      choices?.getAttribute?.("aria-busy") === "true" ||
      choices?.querySelector?.('[aria-busy="true"], .is-loading, .spinner-border, .loading')
    );
    return { settled: !loading && (staticSource || plainNativeSource || searchedEmpty), hasValue };
  }

  async function pickChoicesItem(select, value, deadline = 0) {
    const group = standardMarkTarget(select);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (!choices || choices.classList.contains("is-disabled") || choices.getAttribute("aria-disabled") === "true") {
      return false;
    }
    if (standardSelectBudgetLeft(deadline) <= 0) return false;
    const raw = String(value ?? "");
    const current = choices.querySelector(".choices__list--single .choices__item");
    if (current && !isPlaceholderText(choiceDisplayText(current)) && choiceMatches(current, value)) {
      markFilled(group);
      return true;
    }

    let target = null;
    const isAreaSelect = isAreaSelectName(select.name);
    const targetTimeout = isAreaSelect ? 800 : 600;
    const terms = choiceSearchTerms(select, raw);
    for (let ti = 0; ti < terms.length; ti++) {
      if (standardSelectBudgetLeft(deadline) <= 0) break;
      await openChoicesDropdown(choices, terms[ti], deadline, select);
      // Term đầu (chuỗi đầy đủ) chỉ chờ ngắn vì search client-side gần như tức thì; nếu trượt thì
      // sang cụm ngắn hơn. Term cuối mới chờ đủ lâu (phòng options con cascade load bất đồng bộ).
      const isLast = ti === terms.length - 1;
      target = await waitForStandardSelect(() => {
        const options = Array.from(choices.querySelectorAll(".choices__item--choice"))
          .filter((o) => !o.classList.contains("has-no-choices"));
        return bestChoiceOption(options, value);
      }, isLast ? targetTimeout : 450, 100, deadline);
      if (target) break;
    }
    if (!target) {
      // Chưa thấy option khớp (có thể cascade con chưa nạp xong) → thử lại ở lượt retry/stabilize sau.
      // Không kết luận "vô vọng" nếu nguồn còn đang tải; deadline RIÊNG của ô chặn việc lặp quá lâu.
      return false;
    }

    if (typeof target.scrollIntoView === "function") target.scrollIntoView({ block: "nearest" });
    const search = choices.querySelector(".choices__input--cloned");
    const isSelected = () => {
      const label = currentChoicesValue(choices);
      return !!label && !isPlaceholderText(label) &&
        choiceMatches({ textContent: label, getAttribute: () => "" }, value);
    };

    // Cách 1 — click tổng hợp đúng option khi dropdown đang mở (ổn với select nhỏ như Giới tính,
    // không dùng Enter để tránh Enter đóng dropdown làm hụt lượt chọn).
    const clickTarget = target.querySelector("span") || target;
    ["mouseover", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
      dispatchChoiceMouse(target, type);
      if (clickTarget !== target) dispatchChoiceMouse(clickTarget, type);
    });
    let selected = await waitForStandardSelect(isSelected, 350, 60, deadline);
    if (!selected) {
      // Một số bản Choices/Form.io bỏ qua MouseEvent tự tạo nhưng vẫn chạy listener khi gọi click().
      try { clickTarget.click(); } catch { /* ignore */ }
      selected = await waitForStandardSelect(isSelected, 350, 60, deadline);
    }

    // Cách 2 — luồng bàn phím Choices.js: highlight bằng mouseover rồi Enter (đã có keyCode 13).
    // Re-query option vì click ở trên có thể đã đổi trạng thái danh sách.
    if (!selected) {
      const again = bestChoiceOption(
        Array.from(choices.querySelectorAll(".choices__item--choice"))
          .filter((o) => !o.classList.contains("has-no-choices")),
        value,
      ) || target;
      dispatchChoiceMouse(again, "mouseover");
      dispatchChoiceMouse(again, "mousemove");
      await sleepForStandardSelect(30, deadline);
      if (search && !search.disabled) {
        dispatchKeyboardEvent(search, "keydown", "Enter");
        dispatchKeyboardEvent(search, "keypress", "Enter");
        dispatchKeyboardEvent(search, "keyup", "Enter");
      } else {
        dispatchChoiceMouse(again, "click");
      }
      selected = await waitForStandardSelect(isSelected, 450, 70, deadline);
    }

    // Cách 3 — ép Enter trên container + đồng bộ Form.io lần cuối.
    if (!selected) {
      dispatchKeyboardEvent(choices, "keydown", "Enter");
      dispatchKeyboardEvent(choices, "keyup", "Enter");
      select.dispatchEvent(new Event("input", { bubbles: true }));
      select.dispatchEvent(new Event("change", { bubbles: true }));
      selected = await waitForStandardSelect(isSelected, 350, 70, deadline);
    }

    // Retry đúng hiện tượng thực tế: option đã có nhưng commit/search state của Choices bị kẹt.
    // Clear search rồi thử term có thêm khoảng trắng, sau đó xoá/điền lại term gốc như thao tác tay.
    if (!selected && search && !search.disabled) {
      for (const term of [raw + " ", raw]) {
        if (standardSelectBudgetLeft(deadline) <= 0) break;
        await openChoicesDropdown(choices, term, deadline, select);
        const again = await waitForStandardSelect(() =>
          bestChoiceOption(choicesVisibleOptions(choices), value),
          targetTimeout,
          80,
          deadline
        );
        if (!again) continue;
        if (typeof again.scrollIntoView === "function") again.scrollIntoView({ block: "nearest" });
        const againClickTarget = again.querySelector("span") || again;
        ["mouseover", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
          dispatchChoiceMouse(again, type);
          if (againClickTarget !== again) dispatchChoiceMouse(againClickTarget, type);
        });
        try { againClickTarget.click(); } catch { /* ignore */ }
        selected = await waitForStandardSelect(isSelected, 450, 60, deadline);
        if (selected) break;
        dispatchChoiceMouse(again, "mouseover");
        dispatchKeyboardEvent(search, "keydown", "Enter");
        dispatchKeyboardEvent(search, "keypress", "Enter");
        dispatchKeyboardEvent(search, "keyup", "Enter");
        selected = await waitForStandardSelect(isSelected, 450, 70, deadline);
        if (selected) break;
      }
    }
    if (!selected) return false;
    markFilled(group);
    return true;
  }

  function fillStandardSelect(el, value) {
    if (!el) return false;
    const raw = String(value ?? "");
    const want = norm(raw);
    const options = Array.from(el.options || []);
    let target =
      options.find((o) => String(o.value) === raw) ||
      options.find((o) => norm(o.textContent) === want) ||
      // Khớp lỏng: chọn option TỐT NHẤT (không lấy option đầu) để "Điện Bàn Đông" không dính "Điện Bàn".
      bestChoiceOption(options, raw, (o) => o.textContent, () => "");
    if (!target) {
      console.warn(`[AutoFill-STD] select[name="${el.name}"] không khớp "${raw}". Option:`,
        options.map((o) => `${o.value}:${o.textContent.trim()}`).filter(Boolean).slice(0, 25));
      return false;
    }

    const currentText = el.selectedOptions?.[0]?.textContent || "";
    const alreadySelected =
      choiceMatches(el.selectedOptions?.[0], raw) ||
      (norm(currentText) && norm(currentText) === norm(target.textContent));
    if (alreadySelected) {
      refreshStandardSelectPlugins(el);
      markFilled(standardMarkTarget(el));
      return true;
    }

    // Form.io select trên cổng này hay render mọi option value="[object Object]".
    // Set bằng `.value` sẽ chọn option đầu cùng value (vd "Bộ Công an") dù target text là
    // "Cục Cảnh sát...". Dùng selectedIndex mới trỏ đúng option đã match bằng text.
    const targetIndex = options.indexOf(target);
    if (targetIndex >= 0 && options.filter((o) => String(o.value) === String(target.value)).length > 1) {
      el.selectedIndex = targetIndex;
    } else {
      const desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
      if (desc && desc.set) desc.set.call(el, target.value);
      else el.value = target.value;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
    refreshStandardSelectPlugins(el);
    markFilled(standardMarkTarget(el));
    return true;
  }

  async function fillStandardSelectAny(el, value, names = [], occurrence = null, deadline = 0) {
    const isAreaSelect = names.some(isAreaSelectName) || isAreaSelectName(el?.name);
    if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
    if (!el && names.length) {
      el = await waitForStandardSelect(
        () => findStandardSelect(names, occurrence),
        isAreaSelect ? 3000 : 2500,
        100,
        deadline
      );
    }
    if (!el) return false;
    if (standardSelectBudgetLeft(deadline) <= 0) return false;
    const initialOptionState = isAreaSelect
      ? standardSelectOptionState(el, value, names)
      : { settled: false, hasValue: false };
    if (initialOptionState.settled && !initialOptionState.hasValue) return false;
    const enabled = await waitForStandardSelect(() => {
      const current = el || (names.length ? findStandardSelect(names, occurrence) : null);
      const group = standardMarkTarget(current);
      const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
      if (!current.disabled && (
        !choices ||
        (!choices.classList.contains("is-disabled") && choices.getAttribute("aria-disabled") !== "true")
      )) return current;
      return null;
    }, isAreaSelect ? 3000 : 2500, 100, deadline);
    if (enabled) el = enabled;
    const preferFormio = shouldPreferFormioSelectComponent(el, names);
    // Nguồn động chưa có option trong component: tìm qua Choices trước để tránh chờ Form.io nhiều vòng
    // rồi mới phát hiện giá trị không tồn tại. Nguồn tĩnh/đã có option vẫn giữ đường Form.io nhanh, ổn định.
    if (preferFormio && (!isAreaSelect || initialOptionState.hasValue) &&
      await fillFormioSelectComponent(el, value, names, deadline)) return true;
    if (await pickChoicesItem(el, value, deadline)) return true;
    const searchedOptionState = isAreaSelect
      ? standardSelectOptionState(el, value, names)
      : { settled: false, hasValue: false };
    if (searchedOptionState.settled && !searchedOptionState.hasValue) return false;
    if (await fillFormioSelectComponent(el, value, names, deadline)) return true;
    return fillStandardSelect(el, value);
  }

  async function fillStandardSelectAll(names, value, occurrence = null, deadline = 0) {
    const isAreaSelect = names.some(isAreaSelectName);
    if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
    let filledAny = false;
    for (const delay of [0, 250, 600, 1200]) {
      if (standardSelectBudgetLeft(deadline) <= 0) break;
      if (delay && !await sleepForStandardSelect(delay, deadline)) break;
      const selects = findStandardSelects(names, occurrence);
      if (!selects.length) continue;

      const states = selects.map((sel) => standardSelectOptionState(sel, value, names));
      if (isAreaSelect && states.every((state) => state.settled && !state.hasValue)) {
        console.warn(`[AutoFill-STD] Dừng sớm select "${names[0]}"="${value}" — danh sách đã ổn định và không có giá trị.`);
        break;
      }

      for (const sel of selects) {
        if (currentStandardSelectMatches(sel, value)) {
          markFilled(standardMarkTarget(sel));
          filledAny = true;
          continue;
        }
        const state = standardSelectOptionState(sel, value, names);
        if (isAreaSelect && state.settled && !state.hasValue) continue;
        if (await fillStandardSelectAny(sel, value, names, occurrence, deadline)) filledAny = true;
        await sleepForStandardSelect(120, deadline);
      }

      const latest = findStandardSelects(names, occurrence);
      if (latest.length && latest.every((sel) => currentStandardSelectMatches(sel, value))) {
        return true;
      }
    }
    return filledAny;
  }

  async function fillStandardCheckbox(el, value) {
    if (!el) return false;
    const wantTrue = value === true || String(value).toLowerCase() === "true" || String(value) === "1";
    const target = standardMarkTarget(el);
    if (el.checked !== wantTrue) {
      const label = el.closest("label") || target || el;
      label.click();
      await sleep(250);
      if (el.checked !== wantTrue) {
        el.checked = wantTrue;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } else {
      // Re-dispatch so Form.io runs dependent copy logic even when the checkbox
      // was already selected in the loaded form.
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
    markFilled(target);
    await sleep(350);
    return el.checked === wantTrue;
  }

  function radioLabelText(radio) {
    if (!radio) return "";
    const explicit = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
    const wrapping = radio.closest("label");
    return String(explicit?.textContent || wrapping?.textContent || radio.parentElement?.textContent || "").trim();
  }

  function radioValueMatches(radio, value) {
    const raw = String(value ?? "").trim();
    const folded = foldChoiceText(raw);
    const radioValue = foldChoiceText(radio?.value || "");
    const label = foldChoiceText(radioLabelText(radio));
    const wants = new Set([folded]);
    if (folded === "nam") wants.add("m");
    if (folded === "nu") wants.add("f");
    if (folded === "ca nhan") wants.add("p");
    if (folded === "phuong phap ke khai") wants.add("dec");
    return wants.has(radioValue) ||
      Array.from(wants).some((want) => label === want || label.includes(want) || want.includes(label));
  }

  async function fillStandardRadio(el, value) {
    if (!el) return false;
    const name = el.getAttribute("name");
    const findGroup = () => name
      ? Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
      : [el].filter(Boolean);
    const findTarget = () => {
      const group = findGroup();
      return group.find((radio) => radioValueMatches(radio, value)) || group[0] || null;
    };
    let target = findTarget();
    if (!target) return false;

    if (target.disabled) {
      const enabledTarget = await waitFor(() => {
        const current = findTarget();
        return current && !current.disabled ? current : null;
      }, 1200, 80);
      target = enabledTarget || findTarget();
      if (!target) return false;
      if (target.disabled) {
        target.disabled = false;
        target.removeAttribute("disabled");
        target.setAttribute("data-autofill-enabled-disabled-radio", "true");
        target.closest(".form-check")?.classList?.remove("disabled");
        target.closest("[ref='wrapper']")?.classList?.remove("disabled");
      }
    }
    if (!target.checked) {
      const label = target.id ? document.querySelector(`label[for="${CSS.escape(target.id)}"]`) : null;
      (label || target).click();
      await sleep(250);
    }
    if (!target.checked) {
      target.checked = true;
      target.dispatchEvent(new Event("click", { bubbles: true }));
    }
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
    target.dispatchEvent(new Event("blur", { bubbles: true }));
    markFilled(standardMarkTarget(target));
    return target.checked;
  }

  function isStandardEmptyControl(control) {
    if (!control || control.disabled) return false;
    if (String(control.name || "").includes("BUSINESS_ACT_TEXTFld")) {
      const code = findStandardInput(["ctl00$C$newBusinessLineCode"]);
      if (String(code?.value || "").trim() || hasAnyBusinessLineInList()) return false;
    }
    const tag = control.tagName.toLowerCase();
    if (tag === "select") {
      const selected = control.selectedOptions && control.selectedOptions[0];
      const text = selected ? selected.textContent : "";
      return !String(control.value || "").trim() || isPlaceholderText(text);
    }
    if (control.type === "hidden") return false;
    return !String(control.value || "").trim();
  }

  // Ô "bắt buộc": Form.io gắn class `required` trên .form-group + `aria-required="true"` trên control
  // + nhãn có dấu (*); các cổng khác có thể dùng `*`/(*) trong nhãn hoặc thuộc tính required.
  function isRequiredGroup(group, control) {
    if (control) {
      if (control.getAttribute("aria-required") === "true" || control.required) return true;
      if (control.getAttribute("aria-required") === "false") return false;
    }
    if (group.classList.contains("required")) return true;
    if (group.querySelector(".field-required")) return true;
    const label = group.querySelector("label, .col-form-label, .control-label");
    if (label && /[*＊]/.test(label.textContent || "")) return true;
    return false;
  }

  // Tô ĐỎ ô TRỐNG. Nếu form có đánh dấu ô bắt buộc (Form.io…) → CHỈ tô ô bắt buộc-mà-trống (để người
  // dùng biết trường buộc phải điền tay mà giấy tờ không có); form không có dấu bắt buộc → tô mọi ô trống.
  function markAllStandardEmptyFieldsRed() {
    const groups = Array.from(document.querySelectorAll(
      // Form.io render trong <div class="formio-form"> (KHÔNG phải <form>) → phải thêm .formio-form,
      // nếu không sẽ KHÔNG bắt được ô nào để tô đỏ trên các cổng Form.io (moha, GPXD…).
      "#form-content .form-group, .form-wrapper .form-group, form .form-group, " +
      ".formio-form .form-group, [ref='webform'] .form-group"
    ));
    const controlOf = (g) => g.querySelector("input[name]:not([type='hidden']), textarea[name], select[name]");
    const requiredOnly = groups.some((g) => isRequiredGroup(g, controlOf(g)));
    for (const group of groups) {
      if (!isVisible(group)) continue;
      const control = controlOf(group);
      if (!control) continue;
      if (!isStandardEmptyControl(control)) continue;
      if (requiredOnly && !isRequiredGroup(group, control)) continue;
      markUnfilled(group);
    }
  }

  function parseStandardDatagridName(name) {
    // Khớp cả grid ở gốc `data[GRID][i][field]` LẪN grid lồng trong panel `data[panel][GRID][i][field]`
    // (vd bảng kê cây xanh data[panel][tbantest][0][stt]). grid = đoạn ngay TRƯỚC [index] — ref DOM
    // (datagrid-<grid>-tbody/row/addRow) dùng đúng leaf này, không kèm tiền tố panel.
    const m = String(name || "").match(/^data(?:\[[^\]]+\])*\[([^\]]+)\]\[(\d+)\]\[([^\]]+)\]$/);
    if (!m) return null;
    return { grid: m[1], index: Number(m[2]), field: m[3] };
  }

  function standardDatagridRows(grid) {
    const escaped = CSS.escape(grid);
    const exactRef = `datagrid-${grid}-row`;
    const tbody =
      document.querySelector(`tbody[ref="datagrid-${escaped}-tbody"]`) ||
      document.querySelector(`tbody[data-key="datagrid-${escaped}"]`) ||
      document.querySelector(`button[ref="datagrid-${escaped}-addRow"]`)?.closest("table")?.querySelector("tbody");
    const rows = tbody
      ? Array.from(tbody.querySelectorAll(`tr[ref="${CSS.escape(exactRef)}"]`))
      : Array.from(document.querySelectorAll(`tr[ref="${CSS.escape(exactRef)}"]`));
    return rows.filter((row) => isVisible(row) || isVisible(row.closest("table")));
  }

  function standardDatagridAddButton(grid) {
    const escaped = CSS.escape(grid);
    return document.querySelector(`button[ref="datagrid-${escaped}-addRow"]`) ||
      Array.from(document.querySelectorAll("button.formio-button-add-row")).find((button) => {
        const table = button.closest("table");
        return !!table?.querySelector?.(`tbody[ref="datagrid-${escaped}-tbody"], tbody[data-key="datagrid-${escaped}"]`);
      }) ||
      null;
  }

  function standardDatagridFallbackColumn(fieldKey, controls) {
    const key = String(fieldKey || "");
    const hasStt = controls.some((el) => /\[stt\]$/i.test(String(el.name || "")));
    if (/^textField1$/i.test(key)) return hasStt ? 1 : 0;
    if (/^textField2$/i.test(key)) return hasStt ? 2 : 1;
    return null;
  }

  function findStandardDatagridFallbackInput(field) {
    for (const name of fieldCandidates(field || {})) {
      const parsed = parseStandardDatagridName(name);
      if (!parsed) continue;
      const row = standardDatagridRows(parsed.grid)[parsed.index];
      if (!row) continue;
      const controls = Array.from(row.querySelectorAll("input[name]:not([type='hidden']), textarea[name]"))
        .filter((el) => standardControlVisible(el) && !el.disabled);
      const col = standardDatagridFallbackColumn(parsed.field, controls);
      if (col == null) continue;
      const target = controls[col];
      if (target) return target;
    }
    return null;
  }

  async function ensureStandardDatagridRows(fields) {
    const maxByGrid = new Map();
    for (const f of fields || []) {
      for (const name of fieldCandidates(f)) {
        const parsed = parseStandardDatagridName(name);
        if (!parsed || !Number.isInteger(parsed.index)) continue;
        const current = maxByGrid.get(parsed.grid) ?? -1;
        if (parsed.index > current) maxByGrid.set(parsed.grid, parsed.index);
      }
    }

    for (const [grid, maxIndex] of maxByGrid.entries()) {
      if (maxIndex <= 0) continue;
      // Chờ datagrid render (panel có thể mở chậm) trước khi bấm "Thêm dòng".
      await waitFor(() => standardDatagridRows(grid).length > 0 || standardDatagridAddButton(grid), 2000, 100);
      for (let guard = 0; guard < 12 && standardDatagridRows(grid).length <= maxIndex; guard++) {
        const before = standardDatagridRows(grid).length;
        const button = standardDatagridAddButton(grid);
        if (!button || button.disabled) break;
        try { button.scrollIntoView({ block: "nearest" }); } catch (_) { /* ignore */ }
        // Form.io "Thêm dòng": một số bản BỎ QUA .click() thuần → bắn cả chuỗi sự kiện chuột rồi mới click().
        for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
          try { button.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window })); } catch (_) { /* ignore */ }
        }
        try { button.click(); } catch (_) { /* ignore */ }
        await waitFor(() => standardDatagridRows(grid).length > before, 1500, 80);
        await sleep(180);
      }
      if (standardDatagridRows(grid).length <= maxIndex) {
        console.warn(`[AutoFill-STD] Datagrid "${grid}": chỉ tạo được ${standardDatagridRows(grid).length}/${maxIndex + 1} dòng.`);
      }
    }
  }

  function isOwnerDossierCheckboxField(field) {
    if (field?.comp !== "dom-checkbox") return false;
    const candidates = fieldCandidates(field);
    return candidates.includes("data[isOwnerDossierCheck]") || candidates.includes("data[isOwnerDossier]");
  }

  function standardCheckboxWantsTrue(field) {
    return field?.value === true || String(field?.value).toLowerCase() === "true" || String(field?.value) === "1";
  }

  function orderStandardFields(fields) {
    const ownerCheckboxes = fields.filter(isOwnerDossierCheckboxField);
    const regularFields = fields.filter((field) => !isOwnerDossierCheckboxField(field));

    return [
      // Khi người nộp KHÁC chủ hồ sơ, bỏ tick trước để cổng mở các ô chủ hồ sơ rồi mới điền dữ liệu.
      ...ownerCheckboxes.filter((field) => !standardCheckboxWantsTrue(field)),
      ...regularFields.filter((field) => !isPostbackAddressField(field)),
      ...regularFields.filter((field) => isPostbackAddressField(field)),
      // Checkbox này tự sao chép người nộp sang chủ hồ sơ. Phải tick SAU KHI người nộp đã được điền,
      // nếu không cổng sẽ sao chép giá trị cũ đang có trên form và ghi đè chủ hồ sơ vừa bóc tách.
      ...ownerCheckboxes.filter(standardCheckboxWantsTrue),
    ];
  }

  async function fillFormStandard(fields) {
    injectAutofillStyles();
    clearAutofillMarks();
    await ensureStandardDatagridRows(fields);
    const result = { filled: 0, notFound: [], errors: [] };
    const areaDeadlines = new Map();
    const failedFieldKeys = new Set();
    const orderedFields = orderStandardFields(fields);

    for (const f of orderedFields) {
      const candidates = fieldCandidates(f);
      const occurrence = standardOccurrence(f.occurrence);
      // comp "dom-expect": ô extension CHỊU TRÁCH NHIỆM điền nhưng BE không có dữ liệu → KHÔNG điền, chỉ
      // TÔ ĐỎ nếu ô đang trống (để user biết cần điền tay), kể cả khi form không đánh dấu ô đó bắt buộc.
      // Không tính vào filled/notFound.
      if (f.comp === "dom-expect") {
        const el = findStandardInputForField(f, candidates, occurrence) || findStandardSelect(candidates, occurrence);
        if (el && isStandardEmptyControl(el)) markUnfilled(standardMarkTarget(el));
        continue;
      }
      // comp "dom-owner-copy": nút copy Phần I → Phần III (vd đính chính Lâm Đồng data[BUTTON3]). Bấm ở
      // hook post-fill reapplyOwnerDossierCopy (SAU khi Phần I + cascade ổn định), bỏ qua ở vòng chính
      // để không bị tính notFound.
      if (f.comp === "dom-owner-copy") continue;
      try {
        let ok = false;
        if (f.comp === "dom-vehicle-add") {
          ok = await fillVehicleAddRows(f, candidates);
        } else if (f.comp === "dom-checkbox") {
          const el = findStandardCheckbox(candidates, f.optionValue);
          ok = await fillStandardCheckbox(el, f.value);
        } else if (f.comp === "dom-radio") {
          // Radio có thể render ĐỘNG sau khi chọn radio cha (vd bảng dạng khuyết tật: chọn nhóm "Có" thì
          // Angular mới bật các radio con) → chờ như dom-input/date, tránh bỏ sót mục con render trễ.
          const el = findStandardRadio(candidates) || await waitFor(() => findStandardRadio(candidates), 1500, 80);
          ok = await fillStandardRadio(el, f.value);
        } else if (f.comp === "dom-select") {
          if (isAreaSelectField(f)) {
            const deadline = standardFieldDeadline(areaDeadlines, f);
            ok = await fillStandardSelectAll(candidates, f.value, occurrence, deadline);
          } else {
            const el = findStandardSelect(candidates, occurrence);
            ok = await fillStandardSelectAny(el, f.value, candidates, occurrence);
          }
        } else if (f.comp === "dom-date" || f.comp === "dom-datetime") {
          const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
          // Ô flatpickr trong panel render ĐỘNG: instance _flatpickr gắn TRỄ (có thể ở input ẩn HOẶC ô
          // hiển thị trong cùng component) → chờ đến khi có instance để dùng setDate (điền đủ ẩn+hiển thị,
          // format-agnostic). Nếu chờ theo mỗi el._flatpickr sẽ hụt vì instance nằm ở ô khác → dò RỘNG.
          if (el && el.classList?.contains("flatpickr-input")) {
            const dc = el.closest(".formio-component-datetime") || el.closest(".formio-component");
            const hasFp = () => el._flatpickr || (dc && Array.from(dc.querySelectorAll("input")).some((n) => n._flatpickr));
            if (!hasFp()) await waitFor(hasFp, 1500, 80);
          }
          // dom-datetime: ô lưu ISO có giờ (vd tuNgay/denNgay) → fallback set ISO 00:00:00; dom-date: ô
          // dd/MM/yyyy (vd birthday) → fallback gõ dd/mm/yyyy. setDate (khi có instance) đúng cho cả hai.
          ok = fillStandardDate(el, f.value, { iso: f.comp === "dom-datetime" });
        } else if (f.comp === "dom-input" || f.comp === "raw") {
          const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
          const postbackAddressInput = isPostbackAddressField(f);
          ok = fillStandardInput(el, f.value, postbackAddressInput ? { change: false, commit: false } : {});
        } else {
          const input = findStandardInputForField(f, candidates, occurrence);
          if (input) ok = fillStandardInput(input, f.value);
          else ok = await fillStandardSelectAny(findStandardSelect(candidates, occurrence), f.value, candidates, occurrence);
        }

        if (ok) result.filled++;
        else {
          failedFieldKeys.add(standardFieldIdentity(f));
          result.notFound.push(f.name);
          console.warn(`[AutoFill-STD] Không điền được ${f.name}`);
        }
      } catch (e) {
        result.errors.push(f.name);
        console.warn(`[AutoFill-STD] Lỗi điền ${f.name}:`, e);
      }
      await sleep(50);
    }

    await retryStandardAreaSelects(fields, result, areaDeadlines, failedFieldKeys);
    await stabilizeStandardAreaSelects(fields, result, failedFieldKeys);
    await reapplyEmptyStandardTextFields(fields);
    await reapplyOwnerDossierCopy(fields);
    markAllStandardEmptyFieldsRed();
    scheduleBusinessLineCodeSubmit(fields, result);
    console.log("[AutoFill-STD] Kết quả:", result);
    return result;
  }

  // Trạng thái option của 1 field địa bàn theo đúng occurrence; chỉ "settled" khi từng select cụ thể
  // đã có nguồn option quyết định. Field thất bại vẫn giữ notFound nhưng không ảnh hưởng deadline field khác.
  function areaSelectOptionState(f) {
    const candidates = fieldCandidates(f);
    const selects = findStandardSelects(candidates, standardOccurrence(f.occurrence));
    if (!selects.length || String(f.value ?? "") === "") return { loaded: false, settled: false, hasValue: false };
    const states = selects.map((select) => standardSelectOptionState(select, f.value, candidates));
    const settled = states.every((state) => state.settled);
    return { loaded: settled, settled, hasValue: states.some((state) => state.hasValue) };
  }

  function clearStandardFieldNotFound(result, failedFieldKeys, field) {
    failedFieldKeys.delete(standardFieldIdentity(field));
    const index = result.notFound.indexOf(field.name);
    if (index >= 0) result.notFound.splice(index, 1);
  }

  async function retryStandardAreaSelects(fields, result, deadlines, failedFieldKeys) {
    const pending = fields.filter((f) => isAreaSelectField(f) && failedFieldKeys.has(standardFieldIdentity(f)));
    if (!pending.length) return;

    for (const f of pending) {
      const deadline = standardFieldDeadline(deadlines, f);
      if (standardSelectBudgetLeft(deadline) <= 0) continue;
      const state = areaSelectOptionState(f);
      if (state.settled && !state.hasValue) continue;
      try {
        const ok = await fillStandardSelectAll(
          fieldCandidates(f),
          f.value,
          standardOccurrence(f.occurrence),
          deadline
        );
        if (ok) {
          result.filled++;
          clearStandardFieldNotFound(result, failedFieldKeys, f);
          console.log(`[AutoFill-STD] Retry OK ${f.name} occurrence=${standardOccurrence(f.occurrence)}`);
        }
      } catch (e) {
        console.warn(`[AutoFill-STD] Retry lỗi ${f.name}:`, e);
      }
    }
  }

  async function stabilizeStandardAreaSelects(fields, result, failedFieldKeys) {
    const targets = fields.filter((f) =>
      isAreaSelectField(f) && !failedFieldKeys.has(standardFieldIdentity(f))
    );
    if (!targets.length) return;
    const deadlines = new Map();

    const isStable = (f) => {
      const selects = findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence));
      return selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
    };

    for (const delay of [800, 1600]) {
      // Kiểm TRƯỚC: nếu mọi ô địa chỉ đã đúng thì thoát ngay, không ngủ (form moha không postback
      // xoá field nên vòng ổn định là thừa). Chỉ ngủ+sửa khi còn ô lệch (form postback HkdOnline).
      if (targets.every(isStable)) return;
      await sleep(delay);
      for (const f of targets) {
        const candidates = fieldCandidates(f);
        const occurrence = standardOccurrence(f.occurrence);
        const selects = findStandardSelects(candidates, occurrence);
        const matches = selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
        if (matches) continue;
        try {
          const deadline = standardFieldDeadline(deadlines, f, STANDARD_AREA_STABILIZE_BUDGET_MS);
          await fillStandardSelectAll(candidates, f.value, occurrence, deadline);
        } catch (e) {
          console.warn(`[AutoFill-STD] Stabilize lỗi ${f.name}:`, e);
        }
        await sleep(120);
      }
    }
  }

  // Postback của select địa chỉ (Tỉnh/Phường) render lại form từ ViewState → xoá các ô text đã
  // điền bằng JS (Họ tên, Ngày sinh, Số định danh, Số nhà...). Sau khi cascade địa chỉ ổn định,
  // điền lại các ô text/date đang trống; lặp vài lần phòng postback muộn xoá tiếp.
  async function reapplyEmptyStandardTextFields(fields) {
    const SIMPLE = new Set(["dom-input", "dom-date", "dom-datetime", "raw"]);
    const targets = fields.filter((f) => SIMPLE.has(f.comp) && !isAreaSelectField(f));
    if (!targets.length) return;

    for (const delay of [250, 600, 1000]) {
      await sleep(delay);
      let refilled = 0;
      for (const f of targets) {
        const candidates = fieldCandidates(f);
        const el = findStandardInputForField(f, candidates, standardOccurrence(f.occurrence));
        if (!el || el.disabled) continue;
        if (String(el.value || "").trim()) continue; // còn giá trị → bỏ qua
        // Ô "Số nhà" nằm trong khối địa chỉ: điền không commit để khỏi kích hoạt postback mới.
        const opts = isPostbackAddressField(f) ? { change: false, commit: false } : {};
        if (f.comp === "dom-date" || f.comp === "dom-datetime") fillStandardDate(el, f.value, { iso: f.comp === "dom-datetime" });
        else fillStandardInput(el, f.value, opts);
        refilled++;
      }
      if (!refilled) return; // không còn ô nào trống → xong
    }
  }

  async function reapplyOwnerDossierCopy(fields) {
    // (1) Dạng CHECKBOX "Người nộp là chủ hồ sơ" — tick để form tự copy Phần I → chủ hồ sơ. Tên field-key
    // khác nhau theo cổng: data[isOwnerDossierCheck] (đa số) và data[isOwnerDossier] (cổng Bộ GD&ĐT — Cấp
    // bản sao văn bằng). Re-dispatch change SAU khi Phần I + cascade ổn định để copy đủ dữ liệu.
    const ownerCheckField = fields.find((f) =>
      (fieldCandidates(f).includes("data[isOwnerDossierCheck]") || fieldCandidates(f).includes("data[isOwnerDossier]")) &&
      (f.value === true || String(f.value).toLowerCase() === "true" || String(f.value) === "1")
    );
    if (ownerCheckField) {
      const checkbox = findStandardCheckbox(fieldCandidates(ownerCheckField));
      // Postback địa chỉ có thể render lại checkbox sau vòng điền chính. Luôn áp lại trạng thái true tại
      // hook cuối; fillStandardCheckbox cũng re-dispatch change khi checkbox đã tick để copy dữ liệu mới.
      if (checkbox) await fillStandardCheckbox(checkbox, true);
    }

    // (2) Dạng NÚT bấm (comp dom-owner-copy, vd đính chính Lâm Đồng data[BUTTON3]) — bấm SAU khi Phần I
    // + cascade Tỉnh/Phường đã ổn định để form copy đủ thông tin xuống Phần III chủ hồ sơ.
    const ownerCopyBtnField = fields.find((f) => f.comp === "dom-owner-copy");
    if (ownerCopyBtnField) {
      const cands = fieldCandidates(ownerCopyBtnField);
      let btn = null;
      for (const n of cands) {
        btn = document.querySelector(`button[name="${CSS.escape(n)}"], input[name="${CSS.escape(n)}"]`);
        if (btn) break;
      }
      if (!btn) {
        btn = Array.from(document.querySelectorAll("button, input[type='button']")).find((b) =>
          foldChoiceText(nodeText(b)).includes("nguoi nop la chu ho so"));
      }
      if (btn) {
        clickLikeUser(btn);
        await sleep(400);
      } else {
        console.warn("[AutoFill-STD] Không tìm thấy nút 'Người nộp là chủ hồ sơ' (dom-owner-copy).");
      }
    }
  }

  function findBusinessLineCodeField(fields) {
    return fields.find((f) => fieldCandidates(f).includes("ctl00$C$newBusinessLineCode") && String(f.value || "").trim());
  }

  function hasBusinessLineInList(code) {
    const wanted = norm(code);
    if (!wanted) return false;
    const listing = document.getElementById("ctl00_C_PnlListing") || document;
    const rows = Array.from(listing.querySelectorAll("table tr"));
    return rows.some((row) => {
      const text = norm(row.textContent || "");
      return text && !text.includes("danh sách trống") && text.includes(wanted);
    });
  }

  function hasAnyBusinessLineInList() {
    const listing = document.getElementById("ctl00_C_PnlListing") || document;
    const rows = Array.from(listing.querySelectorAll("table tr"));
    return rows.some((row) => {
      const text = norm(row.textContent || "");
      return text &&
        !text.includes("danh sách trống") &&
        !text.includes("danh sách ngành nghề kinh doanh") &&
        !text.includes("mã số ngành");
    });
  }

  function scheduleBusinessLineCodeSubmit(fields, result) {
    const codeField = findBusinessLineCodeField(fields);
    if (!codeField) return;

    const code = String(codeField.value || "").trim();
    if (!code || hasBusinessLineInList(code)) return;

    const input = findStandardInput(["ctl00$C$newBusinessLineCode"]);
    const hidden = findStandardInput(["ctl00$C$newBusinessLineCodeVal"]);
    const addButton =
      document.querySelector('input[name="ctl00$C$BtnAddBl"], input#ctl00_C_BtnAddBl') ||
      Array.from(document.querySelectorAll('input[type="submit"], button')).find((button) =>
        norm(button.value || button.textContent || "").includes("thêm ngành nghề bằng mã số")
      );

    if (!input || !addButton) {
      result.notFound.push("ctl00$C$BtnAddBl");
      console.warn("[AutoFill-STD] Không tìm thấy nút Thêm ngành nghề bằng mã số để submit mã ngành.");
      return;
    }

    setNativeValue(input, code, { typing: true, commit: true });
    if (hidden) setNativeValue(hidden, code, { typing: false, commit: true });

    result.postActions = result.postActions || [];
    result.postActions.push(`submit business line code ${code}`);
    setTimeout(() => {
      try {
        console.log("[AutoFill-STD] Submit mã ngành nghề:", code);
        addButton.click();
      } catch (e) {
        console.warn("[AutoFill-STD] Không submit được mã ngành nghề:", e);
      }
    }, 250);
  }

  Object.assign(H, {
    sleep, norm, setNativeValue, dispatchInputEvent, dispatchKeyboardEvent, isVisible, waitFor,
    fieldCandidates, findFormControl, markFilled, markUnfilled, markDefaultsYellow,
    clearAutofillMarks, _convertGreenToYellow, injectAutofillStyles, markAllEmptyFieldsRed,
    FIELD_NAME_ALIASES, LEGACY_MIRROR_FIELDS,
    fillFormStandard, findStandardInput, findStandardSelect, isPostbackAddressField,
    isOwnerDossierCheckboxField, standardCheckboxWantsTrue, orderStandardFields,
    readAcctContact, dataUrlToFile, setFilesOnInput, payloadForPlanItem,
  });

})(); // end guard chống nạp trùng
