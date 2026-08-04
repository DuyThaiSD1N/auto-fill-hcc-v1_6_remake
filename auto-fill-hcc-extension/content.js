// Nhận lệnh từ popup và điền dữ liệu cứng vào form hộ tịch điện tử.

// Guard chống nạp trùng: nếu content script bị inject lại (vd background re-inject sau khi
// reload extension), KHÔNG đăng ký listener lần 2 → tránh 1 click toggle 2 lần (mở rồi đóng ngay).
(() => {
  const CONTENT_VERSION = "auto-detect-persist-v2";
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

// ===== Floating panel (chỉ trong top frame) =====
const PANEL_ID = "autofill-hcc-panel";
const BUBBLE_ID = "autofill-hcc-bubble";
const IFRAME_ID = "autofill-hcc-iframe";
const IS_TOP_FRAME = window === window.top;
const PANEL_MIN_H = 160; // chiều cao tối thiểu của iframe (px)
const APP_VERSION_LABEL = "1.9 · 4/8"; // hiện ở header panel; đổi tay mỗi lần phát hành (kèm ngày để hỗ trợ)
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

// sessionStorage: ĐỒNG BỘ, sống qua reload TRONG CÙNG TAB, tab MỚI không kế thừa → dùng để dựng lại
// panel NGAY LẬP TỨC khi reload (không chờ async getTabId/storage → hết giật "ẩn rồi hiện").
const SS_OPEN = "__af_panel_open";
const SS_MIN = "__af_panel_min"; // đang thu nhỏ (bubble) — song song SS_OPEN, đồng bộ để reload giữ nguyên bubble
const SS_TAB = "__af_tab_id";
// Phiên "điền 8 trang" đang chạy (đồng bộ, sống qua reload trong cùng tab). Khi bật, KHÔNG mount lại
// panel/iframe (nặng → nhấp nháy mỗi postback); chỉ hiện banner tiến độ nhẹ "Đang điền X/8".
const SS_FILLALL = "__af_fillall_active";
const SS_FILLALL_STEP = "__af_fillall_step"; // vd "3/8" — để dựng banner NGAY lúc reload, khỏi khe trống
// Khóa trạng thái phiên fill-all trong chrome.storage.local (phải TRÙNG FILLALL_KEY ở business-registration.js).
// Sống suốt phiên bất kể sessionStorage → dùng làm chốt chặn mount panel ở nhánh async khôi phục.
const FILLALL_STATE_KEY = "autofill_fillall_state";
// Tương tự cho phiên "đính kèm nhiều bước" (đăng ký hộ kinh doanh) — cũng ẩn panel + hiện tiến độ.
const ATTACHALL_STATE_KEY = "autofill_attachall_state";
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

function removeUI() {
  document.getElementById(PANEL_ID)?.remove();
  document.getElementById(BUBBLE_ID)?.remove();
  setPanelOpen(false);
  setPanelMinimized(false); // đóng hẳn → xoá luôn cờ thu nhỏ
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
function minimizePanel() {
  const panel = document.getElementById(PANEL_ID);
  if (panel) panel.style.display = "none";
  showBubble();
  setPanelMinimized(true);
}

// Bấm bubble → hiện lại panel (tạo mới nếu chưa có) + xoá cờ thu nhỏ.
function restorePanel() {
  document.getElementById(BUBBLE_ID)?.remove();
  setPanelMinimized(false);
  const panel = document.getElementById(PANEL_ID);
  if (panel) panel.style.display = "flex";
  else chrome.runtime.sendMessage({ action: "getTabId" }, (res) => createPanel(res?.tabId ?? ""));
}

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
  try { chrome.storage.local.remove([FILLALL_STATE_KEY, ATTACHALL_STATE_KEY]); } catch (e) { /* ignore */ }
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

// Cổng dvc là SPA: đổi thủ tục = đổi URL KHÔNG reload trang → panel nổi không tự nhận diện lại.
// Theo dõi đổi URL rồi báo panel (popup.html embedded) để nó nhận diện lại thủ tục theo trang mới.
// LƯU Ý: content script ở isolated world nên KHÔNG patch được history.pushState của trang (main world);
// cách bắt chắc chắn là POLL location.href, kèm popstate/hashchange cho phản hồi tức thì.
if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_URLWATCH__) {
  window.__AUTOFILL_HCC_URLWATCH__ = true;
  let lastHref = location.href;
  const notifyPanelUrlChanged = () => {
    if (location.href === lastHref) return;
    lastHref = location.href;
    const iframe = document.getElementById(IFRAME_ID);
    if (iframe && iframe.contentWindow) {
      try {
        iframe.contentWindow.postMessage(
          { type: "autofill-hcc-url-changed", url: location.href },
          "*"
        );
      } catch (_) { /* ignore */ }
    }
  };
  window.addEventListener("popstate", notifyPanelUrlChanged);
  window.addEventListener("hashchange", notifyPanelUrlChanged);
  setInterval(notifyPanelUrlChanged, 1000);
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
    const files = Array.isArray(msg.files) ? msg.files : [];
    const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
    if (!files.length) {
      sendResponse({ error: "Không có file nào để đính kèm." });
      return;
    }
    if (!attachments.length) {
      sendResponse({ error: "Không có kế hoạch đính kèm từ backend." });
      return;
    }
    attachFilesByPlan(files, attachments, msg.procedure || "", { mode: msg.mode || "merge" }).then(sendResponse);
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
      sendResponse({ error: e?.message || String(e) });
    }
    return;
  }
  if (msg?.action === "detectProcedure") {
    // Chỉ frame TRÊN CÙNG trả lời (URL + heading nằm ở trang gốc, không phải iframe con).
    if (window.top !== window) return;
    sendResponse({ ok: true, signals: collectProcedureSignals() });
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
  if (msg.action !== "fillFields") return;
  // Content script chạy trên mọi frame; chỉ frame thật sự chứa form mới xử lý.
  // Phát hiện loại form: Angular mới ([formcontrolname]), web-component cũ (x-*),
  // hoặc form HTML thường (input/select[name]) của các thủ tục đất đai.
  const formKind = detectFormKind();
  if (!formKind) return; // frame không chứa form thật
  const fields = Array.isArray(msg.fields) ? msg.fields : [];
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
    .catch((e) => sendResponse({ error: `Lỗi điền: ${e?.message || e}` }));
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
      chrome.storage.local.get([panelOpenKey(), panelMinKey(), FILLALL_STATE_KEY, ATTACHALL_STATE_KEY], (res) => {
        if (chrome.runtime.lastError) return;
        const fillSt = res && res[FILLALL_STATE_KEY];
        const attachSt = res && res[ATTACHALL_STATE_KEY];
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
        // Đang thu nhỏ (per-tab qua chrome.storage, chuẩn hơn sessionStorage vốn có thể bị reset) → giữ bubble,
        // không mount panel full. sessionStorage đồng bộ lại để nhánh restoreEarly nhịp sau cũng biết.
        if ((res && res[panelMinKey()]) || sessGet(SS_MIN) === "1") {
          sessSet(SS_MIN, "1");
          // Nếu nhánh đồng bộ lỡ dựng panel full (hiếm: SS_MIN mất mà SS_OPEN còn) → thu lại về bubble.
          if (document.getElementById(PANEL_ID)) minimizePanel();
          else showBubble();
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

// ===== Tách hồ sơ (split): tab hồ sơ mới tự đính file (từ hàng đợi background) khi tới Bước 3 =====
// Trang nộp hồ sơ reload/chuyển bước → content script chạy lại; mỗi lần load kiểm tra pending của tab.
// Portal React (cổng mới): tab mới dừng ở "Thông tin chủ hồ sơ" → tự bấm "Bước tiếp theo" để qua
// trang đính kèm. Chỉ bấm khi CHƯA tới bảng đính kèm; cap tối đa vài lần để không lỡ vượt qua Bước 3.
// eForm cũ KHÔNG có nút này (data-e2e/id không khớp) → no-op, giữ nguyên hành vi user tự điều hướng.
if (IS_TOP_FRAME && !window.__AUTOFILL_HCC_SPLIT_POLLER__) {
  window.__AUTOFILL_HCC_SPLIT_POLLER__ = true;
  try {
    chrome.runtime.sendMessage({ action: "getPendingAttach" }, (res) => {
      if (chrome.runtime.lastError) return;
      const pending = res?.pending;
      if (!pending?.file || !pending?.planItem) return;
      const deadline = Date.now() + 5 * 60 * 1000; // hết hạn 5 phút để tránh poll vô tận
      let busy = false;
      let nextClicks = 0;
      let lastNextClick = 0;
      const clickNextStep = () => {
        // Nút "Bước tiếp theo" ở bước Thông tin chủ hồ sơ (cổng React).
        const btn = document.querySelector(
          'button[id^="kt_buoc-tiep-theo"], button[data-e2e="btn-next"]'
        );
        if (btn && !btn.disabled && typeof isVisible === "function" && isVisible(btn)) {
          btn.click();
          return true;
        }
        return false;
      };
      const tick = async () => {
        if (Date.now() > deadline) return;
        if (!busy && typeof hasAttachmentTarget === "function" && hasAttachmentTarget()) {
          busy = true; // TỚI BƯỚC 3 (có bảng thành phần hồ sơ) → tự đính STT1
          try {
            const r = await attachFilesByPlan([pending.file], [pending.planItem], pending.procedure || "", { mode: "split" });
            if (r?.ok || r?.attached) {
              chrome.runtime.sendMessage({ action: "clearPendingAttach" });
              return;
            }
          } catch (e) { /* thử lại vòng sau */ }
          busy = false;
        } else if (!busy && nextClicks < 3 && Date.now() - lastNextClick > 2500) {
          // Chưa tới bảng đính kèm → thử bấm "Bước tiếp theo" để qua trang đính kèm.
          if (clickNextStep()) { nextClicks++; lastNextClick = Date.now(); }
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
  const seen = new Set();
  const push = (raw) => {
    const s = String(raw || "").replace(/\s+/g, " ").trim();
    if (s.length >= 6 && s.length <= 250 && !seen.has(s)) {
      seen.add(s);
      headings.push(s);
    }
  };
  // Heading chuẩn của eForm hộ tịch/chứng thực (moj) = đúng tên thủ tục; kèm h1/h2 dự phòng.
  document.querySelectorAll(".text-2xl.font-bold, h1, h2").forEach((el) => push(nodeText(el)));
  // Văn bản hiển thị (cắt ngắn) — để nhận diện cổng SPA không có heading (vd laichau): khớp tên thủ tục.
  const bodyText = String(document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 6000);
  // HkdOnline có cùng URL/domain cho nhiều loại hồ sơ. Hint dựa vào marker của ACTIVE wizard step
  // và loại hồ sơ đang hiển thị, tránh suy thủ tục chỉ vì tên option xuất hiện trong body.
  const businessProcedureHint = typeof H.detectBusinessProcedureHint === "function"
    ? H.detectBusinessProcedureHint() : "";
  return { url: location.href, title: document.title || "", headings, bodyText, businessProcedureHint };
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
  const base = String(documentName || "").trim() || attachmentDocumentName(payload);
  const ext = fileExtension(payload?.name);
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
  const safeName = String(documentName || "").trim() || "Tài liệu chứng thực";
  setNativeValue(input, safeName, { typing: true, commit: true });
  await sleep(150);
  return true;
}

async function waitForUploadCompletion(dialog, previousText) {
  await waitFor(() => {
    const doneButton = findWalletUploadDoneButton(dialog);
    if (!doneButton) return true;
    if (!document.documentElement.contains(dialog)) return true;
    const text = foldedNodeText(doneButton);
    return !text.includes("dang tai len") && !doneButton.disabled && text !== previousText;
  }, 20000, 150);
}

async function waitForWalletDialogClosed(dialog) {
  await waitFor(() =>
    !document.documentElement.contains(dialog) ||
    dialog.getAttribute("data-state") === "closed" ||
    !isVisible(dialog),
    12000,
    100
  );
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
  await waitFor(() => !findLatestDialogByText("Danh sách tài liệu điện tử"), 3000, 100);
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

function attachmentTextKey(value) {
  return foldChoiceText(value || "")
    .replace(/\.(pdf|jpe?g|png|webp|xml|docx?|xlsx?|mp3|mp4|wav|mov)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function attachmentKeyMatches(a, b) {
  const left = attachmentTextKey(a);
  const right = attachmentTextKey(b);
  if (!left || !right) return false;
  if (left === right) return true;
  if (Math.min(left.length, right.length) < 4) return false;
  return left.includes(right) || right.includes(left);
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
      return componentTextMatches(row, expectedNewComponent) &&
        labels.some((label) => attachmentKeyMatches(attachedName, label));
    }
    // Với các dòng cố định, tên thành phần hồ sơ thường là mô tả dài và có thể chứa
    // nhãn của dòng khác (vd dòng 1 có cụm "giao dịch đã được chứng thực"). Nếu dùng
    // componentName để bắt trùng, file của dòng 2 sẽ bị skip nhầm khi dòng 1 đã có file.
    return labels.some((label) => attachmentKeyMatches(attachedName, label));
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
  if (!liveRow) return { error: "Không tìm thấy dòng hồ sơ để chọn tệp." };

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
  if (!buttons.length) return { error: "Không tìm thấy nút Chọn tệp đính kèm.", row: liveRow };

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
      clickLikeUser(button);
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

async function attachOneFileViaDocumentWallet(row, payloadFile, planItem = {}) {
  const intendedDocumentName = planItem.documentName || attachmentDocumentName(payloadFile);
  row = await resolveLiveAttachmentRow(row, planItem);
  if (!row) return { error: `Không tìm thấy dòng hồ sơ "${planItem.componentName || ""}".`, fileNames: [payloadFile.name] };
  await closeDocumentWalletDialogs();
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
    return { error: openResult.error, fileNames: [payloadFile.name], debug: openResult.debug };
  }
  const dialog = openResult.dialog;
  row = openResult.row || row;

  const firstUploadButton = findButtonByText(dialog, ["Tải lên từ thiết bị"]);
  if (firstUploadButton) {
    firstUploadButton.click();
    await sleep(400);
  }

  const uploadInput = await waitFor(() =>
    dialog.querySelector("#upload-container input[type='file']") ||
    dialog.querySelector("input[type='file']"),
    12000,
    100
  );
  if (!uploadInput) return { error: "Không tìm thấy input tải tệp trong modal." };

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
  await waitForUploadCompletion(dialog, previousText);
  await waitForWalletDialogClosed(dialog);
  if (document.documentElement.contains(dialog) && isVisible(dialog)) {
    await closeDocumentWalletDialogs();
  }
  await sleep(700);
  markAttachmentResult(row || dialog, true);
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

  if (procedure === "chung-thuc-ban-sao" && items.length > 1) {
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
  if (isIdentityAttachmentItem(item)) {
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

async function attachFilesByAttpRow(payloadFiles, attachments) {
  const fileNames = [];
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
    await tickAttpRowCheckbox(row);
    await setAttpRowLoaiBan(row, first.loaiBan);
    // Ô upload ở CUỐI dòng (không phải cells[2]) → tìm trong cả dòng.
    const input = row.querySelector('input[type="file"]');
    if (!input) { errors.push(`Dòng "${first.documentName}" không có ô upload.`); continue; }
    const files = [];
    const names = [];
    for (const item of items) {
      const payload = payloadForPlanItem(payloadFiles, item);
      if (!payload) { errors.push(`Thiếu file cho "${item.fileName}".`); continue; }
      try { files.push(dataUrlToFile(payload, item.documentName)); names.push(item.fileName); }
      catch (e) { errors.push(`Lỗi đọc file "${item.fileName}": ${e?.message || e}`); }
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
    skipped: 0,
    fileNames,
    skippedNames: [],
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
    const allAttachments = Array.isArray(attachments) ? attachments.filter(Boolean) : [];

    // Bảng-checkbox thuần (ATTP cấp lại...) vẫn dùng engine riêng như cũ.
    const attpItems = allAttachments.filter((item) => item.target === "attp-row");
    const addDocumentItems = allAttachments.filter((item) => item.target === "add-document-dialog");
    if (attpItems.length && !addDocumentItems.length) {
      return await attachFilesByAttpRow(payloadFiles, attpItems);
    }

    // Cổng NNMT trộn hàng cố định với hàng phải tạo qua modal "Thêm giấy tờ". Chạy hàng cố định
    // trước; sau khi modal tạo xong hàng động, tái sử dụng chính engine attp-row để upload file.
    if (addDocumentItems.length) {
      const unsupported = allAttachments.filter((item) =>
        item.target !== "attp-row" && item.target !== "add-document-dialog"
      );
      if (unsupported.length) {
        return { error: "Kế hoạch đính kèm NNMT chứa target chưa hỗ trợ trong luồng hỗn hợp." };
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

    const fixedItems = allAttachments.filter((item) => item.target === "fixed-slot");
    const normalItems = allAttachments.filter((item) => item.target !== "fixed-slot");

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

    const plannedAttachments = splitMode
      ? normalItems.map(forceRow1PlanItem)   // split: mọi file ép về STT1
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
        errors.push(e?.message || String(e));
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
      for (let attempt = 1; attempt <= MAX_ATTACH_ATTEMPTS; attempt++) {
        result = await attachOneFileViaDocumentWallet(row, payloadFile, item);
        if (!result?.error) break;
        if (attempt < MAX_ATTACH_ATTEMPTS) {
          console.warn(`[AutoFill-AttachPlan] thử lại đính kèm (${attempt}/${MAX_ATTACH_ATTEMPTS - 1}) do lỗi:`, result.error);
          await closeDocumentWalletDialogs();
          await sleep(2000 * attempt); // backoff tăng dần để cổng kịp hồi (504 thường transient)
          try { row = (await rowForPlanItem(item)) || row; } catch (_) { /* giữ row cũ */ }
        }
      }
      if (result?.error) {
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
    return { error: "Lỗi đính kèm file theo plan: " + (e?.message || e) };
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
    return { error: "Lỗi đính kèm file: " + (e?.message || e) };
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
  const text = String(name || "").trim();
  if (!text.startsWith("data[")) return "";
  const parts = text.match(/\[[^\]]+\]/g) || [];
  if (parts.length < 3) return "";
  const fieldKey = parts[parts.length - 2].slice(1, -1).toLowerCase();
  if (!fieldKey.includes("radio")) return "";
  return "data" + parts.slice(0, -1).join("");
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

  const actualBase = formioBaseDataName(actual).toLowerCase();
  const expectedBase = formioBaseDataName(expected).toLowerCase();
  if (actualBase && expectedBase && actualBase === expectedBase) return true;
  if (expectedBase && actual.startsWith(expectedBase + "[")) return true;
  if (actualBase && expected.startsWith(actualBase + "[")) return true;

  const actualStable = formioStableRadioName(actual).toLowerCase();
  const expectedStable = formioStableRadioName(expected).toLowerCase();
  if (expectedStable && actualStable === expectedStable) return true;
  if (expectedStable && actual.startsWith(expectedStable + "[")) return true;
  if (actualStable && expected === actualStable) return true;
  if (actualStable && expected.startsWith(actualStable + "[")) return true;

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

function collectFormContext() {
  const checkbox = document.querySelector('input[type="checkbox"][name="data[isOwnerDossierCheck]"]');
  const combinedVariant = detectCombinedBirthFormVariant();
  return {
    applicantFullname:
      readInputLikeValue("data[fullname]") ||
      readNgReflectValue("ng-reflect-fullname") ||
      // Form eform (vd Xác nhận TTHN, Khai tử): người yêu cầu cổng điền sẵn ở HoVaTenC.
      readInputLikeValue(["HoVaTenC", "NYC_HoVaTen"]),
    applicantIdentityNumber:
      readInputLikeValue("data[identityNumber]") ||
      readNgReflectValue("ng-reflect-identity-number") ||
      readInputLikeValue(["SoDinhDanhC", "SoGiayToDinhDanhC", "NYC_SoGiayToTuyThan"]),
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
  return Array.from(document.querySelectorAll("[formcontrolname]")).find((node) =>
    wanted.has(String(node.getAttribute("formcontrolname") || "").toLowerCase())
  ) || null;
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

function fillStandardDate(el, value) {
  if (!el) return false;
  const text = String(value ?? "").trim();
  if (!text) return false;
  const group = standardMarkTarget(el);

  // Form.io datetime dùng flatpickr: set .value trực tiếp vào ô bị flatpickr GHI ĐÈ lại rỗng (→ báo
  // "bắt buộc"). Cách ổn định DUY NHẤT là gọi instance flatpickr `setDate` (tự set cả ô ẩn + ô hiển thị
  // theo dateFormat riêng của form, không quan trọng d/m/Y hay ISO, + bắn onChange cho Form.io/Angular).
  const fpHost = el._flatpickr
    ? el
    : (group?.querySelector?.("input.flatpickr-input")?._flatpickr && group.querySelector("input.flatpickr-input"))
      || (el.closest?.(".flatpickr-input")?._flatpickr && el.closest(".flatpickr-input"))
      || null;
  const fp = fpHost?._flatpickr;
  const dateObj = parseDmyDate(text);
  if (fp && dateObj) {
    try {
      fp.setDate(dateObj, true);   // triggerChange=true
      markFilled(group);
      return true;
    } catch (e) {
      console.warn("[AutoFill-STD] flatpickr.setDate lỗi:", e);
    }
  }

  // Fallback: input date thường (không phải flatpickr / không truy cập được instance).
  setNativeValue(el, text, { typing: true, commit: true });
  const visible = group?.querySelector?.('input:not([type="hidden"])');
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
  return /province|district|village|ward|matinh|maphuongxa|maxa|tinhthanhphonopdon|country_idfld|city_idfld|ward_idfld|street_numberfld|addr[a-z]*ctl/.test(String(name || "").toLowerCase());
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

async function writeChoicesSearch(search, raw, choices) {
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
  await sleep(60);

  const before = choicesListSignature(choices);
  if (!text) return true;

  dispatchPasteEvent(search, text);
  dispatchInputEvent(search, "beforeinput", { data: text, inputType: "insertFromPaste" });
  setInputValueDirect(search, text);
  dispatchInputEvent(search, "input", { data: text, inputType: "insertFromPaste" });
  dispatchKeyboardEvent(search, "keyup", text.slice(-1) || "Unidentified");
  search.dispatchEvent(new Event("change", { bubbles: true }));

  const applied = await waitFor(() => {
    if (String(search.value || "") !== text) return null;
    const after = choicesListSignature(choices);
    return after !== before || choicesHasNoChoices(choices) ? true : null;
  }, 450, 50);
  if (applied) return true;

  setInputValueDirect(search, "");
  dispatchInputEvent(search, "input", { data: null, inputType: "deleteContentBackward" });
  await sleep(50);
  let typed = "";
  for (const ch of Array.from(text)) {
    typed += ch;
    dispatchKeyboardEvent(search, "keydown", ch);
    dispatchKeyboardEvent(search, "keypress", ch);
    dispatchInputEvent(search, "beforeinput", { data: ch, inputType: "insertText" });
    setInputValueDirect(search, typed);
    dispatchInputEvent(search, "input", { data: ch, inputType: "insertText" });
    dispatchKeyboardEvent(search, "keyup", ch);
    await sleep(8);
  }
  search.dispatchEvent(new Event("change", { bubbles: true }));
  await waitFor(() => {
    const after = choicesListSignature(choices);
    return after !== before || choicesHasNoChoices(choices) ? true : null;
  }, 450, 50);
  return true;
}

async function openChoicesDropdown(choices, raw) {
  const opener =
    choices.querySelector(".form-control.ui.selection.dropdown, .form-control, .choices__inner, [role='combobox']") ||
    choices.querySelector(".choices__list--single") ||
    choices;
  if (!choicesDropdownOpen(choices)) {
    if (typeof opener.focus === "function") opener.focus();
    ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => dispatchChoiceMouse(opener, type));
    await waitFor(() => choicesDropdownOpen(choices), 500, 40);
  }
  const search = await waitFor(() => {
    const input = choices.querySelector(".choices__input--cloned");
    return input && !input.disabled ? input : null;
  }, 500, 40);
  if (search && !search.disabled) {
    await writeChoicesSearch(search, raw, choices);
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

async function fillFormioSelectComponent(select, value, names = []) {
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
    return all.find((option) => choiceMatches({ textContent: formioOptionText(option), getAttribute: () => "" }, raw));
  };

  let option = null;
  const attempts = isAreaSelectName(select.name) ? 8 : 4;
  for (let i = 0; i < attempts; i++) {
    option = findOption();
    if (option) break;
    try { comp.updateItems?.(); } catch { /* ignore */ }
    try { comp.refreshItems?.(); } catch { /* ignore */ }
    await sleep(isAreaSelectName(select.name) ? 250 : 120);
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

  const ok = await waitFor(() => currentStandardSelectMatches(select, raw) ||
    choiceMatches({ textContent: formioOptionText(comp.dataValue || holder.submission.data[key]), getAttribute: () => "" }, raw),
    800,
    80
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

// Điền các ô của MỘT dòng datagrid (theo index) từ object xe. Khớp ô bằng NAME đầy đủ (duy nhất theo index).
async function _fillDatagridVehicleRow(idx, v) {
  const base = `data[panel_caNhanToChuc][DanhSachPhuongTien][${idx}]`;
  const q = (sub) => document.querySelector(`[name="${CSS.escape(base + sub)}"]`);
  const setText = (sub, val) => { if (val == null || val === "") return; const el = q(sub); if (el) fillStandardInput(el, String(val)); };
  const setDate = (sub, val) => { if (!val) return; const el = q(sub); if (el) fillStandardDate(el, String(val)); };
  const setSel = async (sub, val) => {
    if (!val) return; const name = base + sub; const el = document.querySelector(`select[name="${CSS.escape(name)}"]`);
    if (el) await fillStandardSelectAny(el, String(val), [name], 0);  // datagrid select → pickChoicesItem theo đúng element dòng
  };
  setText("[BienSoXe]", v.bienSo);
  setText("[SoChoNgoi]", v.trongTai);
  setText("[NamSanXuat]", v.namSanXuat);
  setText("[NhanHieu]", v.nhanHieu);
  setText("[SoKhung]", v.soKhung);
  setText("[SoMay]", v.soMay);
  setText("[NienHanSuDung]", v.nienHan || "0");
  await setSel("[MauSon]", v.mauSon);
  await setSel("[HinhThucHoatDong]", v.hinhThucHoatDong);
  await setSel("[CuaKhau]", v.cuaKhau);
  if (v.loaiPhuongTien) await setSel("[LoaiPhuongTien]", v.loaiPhuongTien);
  setDate("[NgayCap]", v.tuNgay);
  setDate("[NgayHetHan]", v.denNgay);
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

// HẠN THỜI GIAN TỔNG cho toàn bộ việc điền select địa bàn (Tỉnh/Xã cascade). Đặt ở đầu fillFormStandard.
// Quá hạn thì thôi thử (để tô đỏ cho user tự chọn) — chặn "chọn đi chọn lại mấy phút" mà KHÔNG bỏ nhầm
// select đang cần thêm thời gian cascade (khác cách "doom" trước đây hay bỏ non).
let _areaSelectDeadline = 0;
function _areaBudgetLeft() {
  return _areaSelectDeadline ? _areaSelectDeadline - Date.now() : Infinity;
}

async function pickChoicesItem(select, value) {
  const group = standardMarkTarget(select);
  const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
  if (!choices || choices.classList.contains("is-disabled") || choices.getAttribute("aria-disabled") === "true") {
    return false;
  }
  if (isAreaSelectName(select.name) && _areaBudgetLeft() <= 0) return false;  // hết hạn → bỏ, tô đỏ sau
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
    await openChoicesDropdown(choices, terms[ti]);
    // Term đầu (chuỗi đầy đủ) chỉ chờ ngắn vì search client-side gần như tức thì; nếu trượt thì
    // sang cụm ngắn hơn. Term cuối mới chờ đủ lâu (phòng options con cascade load bất đồng bộ).
    const isLast = ti === terms.length - 1;
    target = await waitFor(() => {
      const options = Array.from(choices.querySelectorAll(".choices__item--choice"))
        .filter((o) => !o.classList.contains("has-no-choices"));
      return options.find((o) => choiceMatches(o, value));
    }, isLast ? targetTimeout : 450, 100);
    if (target) break;
  }
  if (!target) {
    // Chưa thấy option khớp (có thể cascade con chưa nạp xong) → thử lại ở lượt retry/stabilize sau.
    // Không kết luận "vô vọng" ở đây (tránh bỏ nhầm phường/xã đang load). Hạn thời gian tổng lo phần
    // chặn lặp quá lâu.
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
  let selected = await waitFor(isSelected, 350, 60);
  if (!selected) {
    // Một số bản Choices/Form.io bỏ qua MouseEvent tự tạo nhưng vẫn chạy listener khi gọi click().
    try { clickTarget.click(); } catch { /* ignore */ }
    selected = await waitFor(isSelected, 350, 60);
  }

  // Cách 2 — luồng bàn phím Choices.js: highlight bằng mouseover rồi Enter (đã có keyCode 13).
  // Re-query option vì click ở trên có thể đã đổi trạng thái danh sách.
  if (!selected) {
    const again = Array.from(choices.querySelectorAll(".choices__item--choice"))
      .filter((o) => !o.classList.contains("has-no-choices"))
      .find((o) => choiceMatches(o, value)) || target;
    dispatchChoiceMouse(again, "mouseover");
    dispatchChoiceMouse(again, "mousemove");
    await sleep(30);
    if (search && !search.disabled) {
      dispatchKeyboardEvent(search, "keydown", "Enter");
      dispatchKeyboardEvent(search, "keypress", "Enter");
      dispatchKeyboardEvent(search, "keyup", "Enter");
    } else {
      dispatchChoiceMouse(again, "click");
    }
    selected = await waitFor(isSelected, 450, 70);
  }

  // Cách 3 — ép Enter trên container + đồng bộ Form.io lần cuối.
  if (!selected) {
    dispatchKeyboardEvent(choices, "keydown", "Enter");
    dispatchKeyboardEvent(choices, "keyup", "Enter");
    select.dispatchEvent(new Event("input", { bubbles: true }));
    select.dispatchEvent(new Event("change", { bubbles: true }));
    selected = await waitFor(isSelected, 350, 70);
  }

  // Retry đúng hiện tượng thực tế: option đã có nhưng commit/search state của Choices bị kẹt.
  // Clear search rồi thử term có thêm khoảng trắng, sau đó xoá/điền lại term gốc như thao tác tay.
  if (!selected && search && !search.disabled) {
    for (const term of [raw + " ", raw]) {
      await openChoicesDropdown(choices, term);
      const again = await waitFor(() =>
        choicesVisibleOptions(choices).find((o) => choiceMatches(o, value)),
        targetTimeout,
        80
      );
      if (!again) continue;
      if (typeof again.scrollIntoView === "function") again.scrollIntoView({ block: "nearest" });
      const againClickTarget = again.querySelector("span") || again;
      ["mouseover", "mousemove", "pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
        dispatchChoiceMouse(again, type);
        if (againClickTarget !== again) dispatchChoiceMouse(againClickTarget, type);
      });
      try { againClickTarget.click(); } catch { /* ignore */ }
      selected = await waitFor(isSelected, 450, 60);
      if (selected) break;
      dispatchChoiceMouse(again, "mouseover");
      dispatchKeyboardEvent(search, "keydown", "Enter");
      dispatchKeyboardEvent(search, "keypress", "Enter");
      dispatchKeyboardEvent(search, "keyup", "Enter");
      selected = await waitFor(isSelected, 450, 70);
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
    options.find((o) => {
      const text = norm(o.textContent);
      return !!text && (text.includes(want) || want.includes(text));
    });
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

async function fillStandardSelectAny(el, value, names = [], occurrence = null) {
  const isAreaSelect = names.some(isAreaSelectName) || isAreaSelectName(el?.name);
  if (!el && names.length) {
    el = await waitFor(() => findStandardSelect(names, occurrence), isAreaSelect ? 3000 : 2500);
  }
  if (!el) return false;
  if (isAreaSelect && _areaBudgetLeft() <= 0) return false;  // hết hạn tổng → bỏ (tô đỏ sau)
  const enabled = await waitFor(() => {
    const current = el || (names.length ? findStandardSelect(names, occurrence) : null);
    const group = standardMarkTarget(current);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (!current.disabled && (
      !choices ||
      (!choices.classList.contains("is-disabled") && choices.getAttribute("aria-disabled") !== "true")
    )) return current;
    return null;
  }, isAreaSelect ? 3000 : 2500);
  if (enabled) el = enabled;
  if (shouldPreferFormioSelectComponent(el, names) && await fillFormioSelectComponent(el, value, names)) return true;
  if (await pickChoicesItem(el, value)) return true;
  if (await fillFormioSelectComponent(el, value, names)) return true;
  return fillStandardSelect(el, value);
}

async function fillStandardSelectAll(names, value, occurrence = null) {
  let filledAny = false;
  for (const delay of [0, 250, 600, 1200]) {
    if (_areaBudgetLeft() <= 0) break;  // hết hạn tổng → dừng (ô chưa khớp sẽ được tô đỏ)
    if (delay) await sleep(delay);
    const selects = findStandardSelects(names, occurrence);
    if (!selects.length) continue;

    for (const sel of selects) {
      if (currentStandardSelectMatches(sel, value)) {
        markFilled(standardMarkTarget(sel));
        filledAny = true;
        continue;
      }
      if (await fillStandardSelectAny(sel, value, [])) filledAny = true;
      await sleep(120);
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
  const m = String(name || "").match(/^data\[([^\]]+)\]\[(\d+)\]\[[^\]]+\]$/);
  if (!m) return null;
  const fieldMatch = String(name || "").match(/^data\[[^\]]+\]\[\d+\]\[([^\]]+)\]$/);
  return { grid: m[1], index: Number(m[2]), field: fieldMatch ? fieldMatch[1] : "" };
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
    for (let guard = 0; guard < 8 && standardDatagridRows(grid).length <= maxIndex; guard++) {
      const before = standardDatagridRows(grid).length;
      const button = standardDatagridAddButton(grid);
      if (!button || button.disabled) break;
      button.click();
      await waitFor(() => standardDatagridRows(grid).length > before, 1200, 80);
      await sleep(150);
    }
  }
}

async function fillFormStandard(fields) {
  injectAutofillStyles();
  clearAutofillMarks();
  // Ngân sách thời gian cho việc điền các select địa bàn (Tỉnh/Xã cascade) — chặn lặp quá lâu.
  _areaSelectDeadline = Date.now() + 18000;
  await ensureStandardDatagridRows(fields);
  const result = { filled: 0, notFound: [], errors: [] };
  const orderedFields = [
    ...fields.filter((f) => !isPostbackAddressField(f)),
    ...fields.filter((f) => isPostbackAddressField(f)),
  ];

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
        const el = findStandardRadio(candidates);
        ok = await fillStandardRadio(el, f.value);
      } else if (f.comp === "dom-select") {
        if (isAreaSelectField(f)) {
          ok = await fillStandardSelectAll(candidates, f.value, occurrence);
        } else {
          const el = findStandardSelect(candidates, occurrence);
          ok = await fillStandardSelectAny(el, f.value, candidates, occurrence);
        }
      } else if (f.comp === "dom-date") {
        const el = findStandardInputForField(f, candidates, occurrence) || await waitFor(() => findStandardInputForField(f, candidates, occurrence), 1000, 80);
        ok = fillStandardDate(el, f.value);
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
        result.notFound.push(f.name);
        console.warn(`[AutoFill-STD] Không điền được ${f.name}`);
      }
    } catch (e) {
      result.errors.push(f.name);
      console.warn(`[AutoFill-STD] Lỗi điền ${f.name}:`, e);
    }
    await sleep(50);
  }

  await retryStandardAreaSelects(fields, result);
  await stabilizeStandardAreaSelects(fields, result);
  await reapplyEmptyStandardTextFields(fields);
  await reapplyOwnerDossierCopy(fields);
  markAllStandardEmptyFieldsRed();
  scheduleBusinessLineCodeSubmit(fields, result);
  console.log("[AutoFill-STD] Kết quả:", result);
  return result;
}

// Trạng thái option của 1 ô địa bàn: đã load đủ danh sách chưa + có chứa giá trị cần không.
// Form.io giữ danh sách đầy đủ trong comp.selectOptions dù native <select> chỉ có 1 option → phải đọc
// từ component. Dùng để BỎ SỚM ô mà options ĐÃ LOAD nhưng KHÔNG có giá trị (vd "Phường 9" bị đổi tên do
// sáp nhập) — tránh retry vô ích ăn hết ngân sách, làm ô hợp lệ khác (vd "Tỉnh Hà Tĩnh") không kịp điền.
function areaSelectOptionState(f) {
  const candidates = fieldCandidates(f);
  const selects = findStandardSelects(candidates, standardOccurrence(f.occurrence));
  const raw = String(f.value ?? "");
  if (!raw) return { loaded: false, hasValue: false };
  let maxCount = 0;
  let hasValue = false;
  for (const sel of selects) {
    const texts = [];
    const key = formioKeyFromSelect(sel, candidates);
    const holder = key ? formioFindHolderNear(sel) : null;
    const comp = holder?.formio?.getComponent?.(key);
    if (comp) {
      if (Array.isArray(comp.selectOptions)) comp.selectOptions.forEach((o) => texts.push(formioOptionText(o)));
      if (Array.isArray(comp.items)) comp.items.forEach((o) => texts.push(formioOptionText(o)));
    }
    const group = standardMarkTarget(sel);
    const choices = group?.classList?.contains("choices") ? group : group?.querySelector?.(".choices");
    if (choices) choicesVisibleOptions(choices).forEach((o) => texts.push(choiceDisplayText(o)));
    Array.from(sel.options || []).forEach((o) => texts.push(o.textContent));
    const real = [...new Set(texts.filter(Boolean))].filter((t) => {
      const ft = foldChoiceText(t);
      return ft && !ft.includes("chon ") && ft !== "chon" && !ft.startsWith("-");
    });
    maxCount = Math.max(maxCount, real.length);
    if (real.some((t) => choiceMatches({ textContent: t, getAttribute: () => "" }, raw))) hasValue = true;
  }
  return { loaded: maxCount >= 3, hasValue };
}

async function retryStandardAreaSelects(fields, result) {
  let pending = fields.filter((f) => isAreaSelectField(f) && result.notFound.includes(f.name));
  if (!pending.length) return;

  for (const delay of [700, 1400, 2400]) {
    if (_areaBudgetLeft() <= 0) break;  // hết ngân sách thời gian → dừng, tô đỏ ô còn lại
    await sleep(delay);
    // BỎ SỚM ô đã load options mà KHÔNG có giá trị (đổi tên do sáp nhập) → nhường ngân sách cho ô hợp lệ.
    pending = pending.filter((f) => {
      const st = areaSelectOptionState(f);
      if (st.loaded && !st.hasValue) {
        console.warn(`[AutoFill-STD] Bỏ ô "${f.name}"="${f.value}" — danh sách đã load nhưng KHÔNG có giá trị (đổi tên do sáp nhập?). Tô đỏ để chọn tay.`);
        return false;  // giữ trong notFound (đã tô đỏ), thôi retry để không phí thời gian
      }
      return true;
    });
    if (!pending.length) return;
    const stillPending = [];
    for (const f of pending) {
      const candidates = fieldCandidates(f);
      try {
        const ok = await fillStandardSelectAll(candidates, f.value, standardOccurrence(f.occurrence));
        if (ok) {
          result.filled++;
          result.notFound = result.notFound.filter((name) => name !== f.name);
          console.log(`[AutoFill-STD] Retry OK ${f.name}`);
        } else {
          stillPending.push(f);
        }
      } catch (e) {
        stillPending.push(f);
        console.warn(`[AutoFill-STD] Retry lỗi ${f.name}:`, e);
      }
      await sleep(120);
    }
    pending = stillPending;
    if (!pending.length) return;
  }
}

async function stabilizeStandardAreaSelects(fields, result) {
  const targets = fields.filter((f) => isAreaSelectField(f));
  if (!targets.length) return;

  const isStable = (f) => {
    const selects = findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence));
    return selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
  };

  for (const delay of [800, 1600]) {
    if (_areaBudgetLeft() <= 0) return;  // hết ngân sách thời gian → dừng
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
        const wasNotFound = result.notFound.includes(f.name);
        const ok = await fillStandardSelectAll(candidates, f.value, occurrence);
        if (ok && wasNotFound) {
          result.filled++;
          result.notFound = result.notFound.filter((name) => name !== f.name);
        }
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
  const SIMPLE = new Set(["dom-input", "dom-date", "raw"]);
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
      if (f.comp === "dom-date") fillStandardDate(el, f.value);
      else fillStandardInput(el, f.value, opts);
      refilled++;
    }
    if (!refilled) return; // không còn ô nào trống → xong
  }
}

async function reapplyOwnerDossierCopy(fields) {
  // (1) Dạng CHECKBOX "Người nộp là chủ hồ sơ" (data[isOwnerDossierCheck]) — tick để form tự copy.
  const ownerCheckField = fields.find((f) =>
    fieldCandidates(f).includes("data[isOwnerDossierCheck]") &&
    (f.value === true || String(f.value).toLowerCase() === "true" || String(f.value) === "1")
  );
  if (ownerCheckField) {
    const checkbox = findStandardCheckbox(fieldCandidates(ownerCheckField));
    if (checkbox && checkbox.checked) {
      checkbox.dispatchEvent(new Event("input", { bubbles: true }));
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      await sleep(300);
    }
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
  readAcctContact, dataUrlToFile, setFilesOnInput, payloadForPlanItem,
});

})(); // end guard chống nạp trùng
