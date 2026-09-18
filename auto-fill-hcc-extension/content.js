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
  const DROP_MASK_ID = "autofill-hcc-drop-mask"; // mask che kín panel lúc kéo file từ ngoài vào (xem wireExternalFileDrop)
  const UPDATE_BTN_ID = "autofill-hcc-cap-nhat";               // nút "Cập nhật" trên header (xem veNutCapNhat)
  const UPDATE_CONFIRM_ID = "autofill-hcc-cap-nhat-xac-nhan";
  const KHOA_BAN_CHO = "hcc_ban_moi_cho";                      // background (kiemBanMoi) ghi / xoá
  const IS_TOP_FRAME = window === window.top;
  const PANEL_MIN_H = 160; // chiều cao tối thiểu của iframe (px)
  // Nhãn phiên bản ở header panel = "<số> · <ngày phát hành>".
  //
  // SỐ đọc thẳng từ manifest, không gõ tay: bản trước gõ tay và đã trôi thật —
  // header hiện "1.17 · 8/9" trong khi manifest đã là 1.17.0.6. Đúng lúc cần trả
  // lời "bản vá đã tới máy này chưa?" thì nhãn lại nói sai.
  // NGÀY vẫn ghi tay (để hỗ trợ), đổi cùng mục đầu changelog.js — tests/release-version.test.js kiểm.
  const APP_RELEASE_DATE = "14/9";
  const APP_VERSION_LABEL = (() => {
    let v = "?";
    try { v = chrome.runtime.getManifest().version; } catch (e) { /* context đã mất */ }
    return `${v} · ${APP_RELEASE_DATE}`;
  })();
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
    goPreview(); // dong panel thi khong de khung xem truoc lo lung tren trang
    document.getElementById(PANEL_ID)?.remove();
    document.getElementById(BUBBLE_ID)?.remove();
    setPanelOpen(false);
    setPanelMinimized(false); // đóng hẳn → xoá luôn cờ thu nhỏ
    clearAutoMinState();
  }

  // ---- Trang này có mở được panel không? -----------------------------------
  //
  // `web_accessible_resources.matches` trong manifest mới là thứ quyết định,
  // KHÔNG phải `content_scripts.matches`. Panel là một
  // <iframe src="chrome-extension://…/popup.html">, và Chromium TỪ CHỐI nạp nó
  // từ trang không nằm trong danh sách đó.
  //
  // Phải kiểm vì có một đường đi vòng: bấm biểu tượng extension thì background
  // dùng activeTab + chrome.scripting tiêm content.js vào BẤT KỲ trang nào, kể
  // cả trang ngoài danh sách (xem chrome.action.onClicked). Khi đó content.js
  // dựng được khung panel nhưng iframe bên trong bị chặn — cán bộ nhận một cái
  // hộp CHẾT, không một lời giải thích, còn console chỉ có đúng một dòng
  // "Denying load of chrome-extension://…". Gặp thật 2026-09-11.
  function khopMauMatch(mau, url) {
    if (mau === "<all_urls>") return true;
    const m = /^(\*|https?|file|ftp):\/\/(\*|(?:\*\.)?[^/*]+)?(\/.*)$/.exec(mau);
    if (!m) return false;
    const [, giaoThuc, host, duong] = m;
    let u;
    try { u = new URL(url); } catch (e) { return false; }
    if (giaoThuc !== "*" && u.protocol !== giaoThuc + ":") return false;
    if (host && host !== "*") {
      if (host.startsWith("*.")) {
        const goc = host.slice(2);
        if (u.hostname !== goc && !u.hostname.endsWith("." + goc)) return false;
      } else if (u.hostname !== host) {
        return false;
      }
    }
    const re = new RegExp("^" + duong.split("*").map((x) => x.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*") + "$");
    return re.test(u.pathname + u.search);
  }

  function trangDuocHoTro(url) {
    let khoi;
    try { khoi = chrome.runtime.getManifest().web_accessible_resources || []; }
    catch (e) { return true; } // không đọc được manifest thì đừng tự chặn
    const dia = url || location.href;
    for (const b of khoi) {
      if (!(b && Array.isArray(b.matches))) continue;
      if (!(Array.isArray(b.resources) && b.resources.some((r) => r === "popup.html"))) continue;
      if (b.matches.some((mau) => khopMauMatch(mau, dia))) return true;
    }
    return false;
  }

  function togglePanel() {
    if (!IS_TOP_FRAME) return;
    // Đang mở (kể cả đang thu nhỏ) → coi như đóng hẳn.
    if (document.getElementById(PANEL_ID) || document.getElementById(BUBBLE_ID)) {
      removeUI();
      return;
    }
    if (!trangDuocHoTro()) {
      showPageToast(
        "Trang này không nằm trong danh sách cổng dịch vụ công được hỗ trợ nên không mở được bảng trợ lý. " +
        "Hãy mở đúng trang cổng dịch vụ công rồi bấm lại.", "warn");
      console.warn("[AutoFill] Không mở panel: %s không khớp web_accessible_resources.matches trong manifest.", location.href);
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

  // ---- Nút "Cập nhật" chủ động ---------------------------------------------
  // background (kiemBanMoi) ghi "bản mới đang chờ" vào storage mỗi nhịp kiểm; ở đây chỉ vẽ nút và hỏi xác
  // nhận. Cập nhật = nạp lại extension, mà content script bản mới chỉ được tiêm khi trang tải lại →
  // background tải lại đúng tab này sau khi nạp. Vì thế PHẢI hỏi: nội dung chưa lưu trên trang có thể mất.
  function veNutCapNhat() {
    const btn = document.getElementById(UPDATE_BTN_ID);
    if (!btn) return;
    let dangChay = "";
    try { dangChay = chrome.runtime.getManifest().version; } catch (e) { return; } // context đã mất
    chrome.storage.local.get(KHOA_BAN_CHO, (res) => {
      if (chrome.runtime.lastError) return;
      const v = res?.[KHOA_BAN_CHO]?.version;
      const hien = typeof v === "string" && !!v && v !== dangChay;
      btn.style.display = hien ? "inline-flex" : "none";
      btn.dataset.version = hien ? v : "";
      btn.title = hien ? `Đã có bản ${v} (đang dùng ${dangChay}) — bấm để cập nhật ngay` : "";
      // Header chỉ rộng 360px: đang có nút Cập nhật thì tạm cất "★ Lịch sử" cho khỏi tràn.
      const lichSu = btn.previousElementSibling;
      if (lichSu && lichSu.tagName === "BUTTON") lichSu.style.display = hien ? "none" : "";
      if (hien) {
        batNhapNhay(btn);
      } else {
        btn.__nhay?.cancel();
        btn.__nhay = null;
        document.getElementById(UPDATE_CONFIRM_ID)?.remove();
      }
    });
  }

  function batNhapNhay(btn) {
    if (btn.__nhay) return;
    // Máy bật "giảm chuyển động" thì chỉ giữ màu nổi, không nhấp nháy.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    btn.__nhay = btn.animate(
      [
        { boxShadow: "0 0 0 0 rgba(255, 193, 7, .95)", transform: "scale(1)" },
        { boxShadow: "0 0 0 7px rgba(255, 193, 7, 0)", transform: "scale(1.06)" },
      ],
      { duration: 1300, iterations: Infinity, easing: "ease-out" },
    );
  }

  function moXacNhanCapNhat() {
    const btn = document.getElementById(UPDATE_BTN_ID);
    const root = document.getElementById(PANEL_ID);
    const version = btn?.dataset.version;
    if (!root || !version) return;
    document.getElementById(UPDATE_CONFIRM_ID)?.remove();
    const header = root.firstElementChild;
    const hop = document.createElement("div");
    hop.id = UPDATE_CONFIRM_ID;
    hop.setAttribute("role", "alertdialog");
    Object.assign(hop.style, {
      position: "absolute", left: "8px", right: "8px", top: `${(header?.offsetHeight || 32) + 6}px`,
      zIndex: "3", background: "#fff", color: "#1f2937", border: "1px solid #f4c04e",
      borderRadius: "8px", boxShadow: "0 8px 24px rgba(0,0,0,.2)", padding: "10px 12px",
      font: "12.5px/1.45 system-ui, 'Segoe UI', sans-serif", cursor: "default",
    });
    const tieuDe = document.createElement("div");
    tieuDe.textContent = `Cập nhật Trợ lý lên bản ${version}?`;
    Object.assign(tieuDe.style, { fontWeight: "700", marginBottom: "4px" });
    const moTa = document.createElement("div");
    moTa.textContent = "Trang sẽ tải lại để nạp bản mới. Nội dung đang nhập trên trang mà chưa lưu có thể mất.";
    const canhBao = document.createElement("div");
    canhBao.dataset.vai = "canh-bao-ban";
    canhBao.textContent = "⚠️ Trợ lý đang xử lý dở (điền / đính kèm) — nên bấm Để sau, chờ xong rồi cập nhật.";
    Object.assign(canhBao.style, { display: "none", marginTop: "6px", color: "#92400e", fontWeight: "600" });
    const hang = document.createElement("div");
    Object.assign(hang.style, { display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "10px" });
    const kieuNut = { borderRadius: "6px", padding: "6px 12px", fontSize: "12px", fontWeight: "700", cursor: "pointer" };
    const deSau = document.createElement("button");
    deSau.type = "button";
    deSau.textContent = "Để sau";
    Object.assign(deSau.style, kieuNut, { border: "1px solid #d1d5db", background: "#fff", color: "#1f2937" });
    deSau.addEventListener("click", (e) => { e.stopPropagation(); hop.remove(); });
    const ngay = document.createElement("button");
    ngay.type = "button";
    ngay.textContent = "Cập nhật ngay";
    Object.assign(ngay.style, kieuNut, { border: "0", background: "#d97706", color: "#fff" });
    ngay.addEventListener("click", (e) => { e.stopPropagation(); capNhatNgay(ngay, hop); });
    hang.append(deSau, ngay);
    hop.append(tieuDe, moTa, canhBao, hang);
    root.appendChild(hop);
    // Hỏi panel có đang xử lý dở không — cờ bận nằm trong iframe popup, trang này không đọc được.
    document.getElementById(IFRAME_ID)?.contentWindow?.postMessage({ type: "autofill-hcc-hoi-ban" }, "*");
  }

  function hienCanhBaoBan(ban) {
    const el = document.querySelector(`#${UPDATE_CONFIRM_ID} [data-vai="canh-bao-ban"]`);
    if (el) el.style.display = ban ? "block" : "none";
  }

  function capNhatNgay(nut, hop) {
    nut.disabled = true;
    nut.textContent = "Đang cập nhật…";
    const loi = (chu) => { hop.remove(); showPageToast(chu, "warn"); veNutCapNhat(); };
    try {
      chrome.runtime.sendMessage({ action: "hccCapNhatNgay", tabId: CURRENT_TAB_ID }, (res) => {
        if (chrome.runtime.lastError) { loi("Không gửi được lệnh cập nhật — thử lại sau."); return; }
        if (res?.ok) return; // extension sắp nạp lại: panel bị gỡ rồi trang tự tải lại
        if (res?.lyDo === "da-moi-nhat") {
          hop.remove();
          showPageToast("Trợ lý đã ở bản mới nhất.", "success");
          veNutCapNhat();
          return;
        }
        loi("Chưa kết nối được agent — thử lại sau.");
      });
    } catch (e) {
      loi("Không gửi được lệnh cập nhật — thử lại sau.");
    }
  }

  function createPanel(tabId) {
    if (document.getElementById(PANEL_ID)) return;
    // Chốt chặn cuối: dựng khung panel trên trang không được phép nạp iframe chỉ
    // tạo ra một cái hộp chết. Thà không dựng gì.
    if (!trangDuocHoTro()) {
      console.warn("[AutoFill] Bỏ dựng panel: %s không khớp web_accessible_resources.matches.", location.href);
      return;
    }
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
    titleText.textContent = "Trợ lý nhân dân";
    // Pill version mờ ngay sau tiêu đề — nhận biết nhanh phiên bản khi hỗ trợ, không chiếm dòng riêng.
    const ver = document.createElement("span");
    ver.textContent = "v" + APP_VERSION_LABEL;
    // Tooltip cho lúc hỗ trợ từ xa: ID extension cho biết Chrome đang nạp đúng
    // bản nào (bản tự host và bản trên store có ID khác nhau).
    try { ver.title = "Phiên bản " + APP_VERSION_LABEL + " · ID " + chrome.runtime.id; } catch (e) { /* ignore */ }
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
    // Nút "Cập nhật" — chỉ hiện khi agent đã tải bản MỚI về máy mà extension chưa nạp (cán bộ đang làm nên
    // cơ chế tự nạp lại lúc máy rảnh chưa chạy). Nhấp nháy để cán bộ để ý. Xem veNutCapNhat.
    const capNhatBtn = document.createElement("button");
    capNhatBtn.type = "button";
    capNhatBtn.id = UPDATE_BTN_ID;
    capNhatBtn.textContent = "⬆ Cập nhật";
    Object.assign(capNhatBtn.style, {
      display: "none", flex: "0 0 auto", fontSize: "10px", fontWeight: "800", lineHeight: "1",
      padding: "3px 8px", borderRadius: "999px", whiteSpace: "nowrap", cursor: "pointer",
      background: "#ffc107", color: "#3b2a00", border: "1px solid #ffe08a",
    });
    capNhatBtn.addEventListener("click", (e) => { e.stopPropagation(); moXacNhanCapNhat(); });
    title.append(logo, titleText, ver, histBtn, capNhatBtn);
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
    setTimeout(veNutCapNhat, 0); // chờ panel gắn vào trang xong mới tìm được nút theo id

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

    // Mask kéo-thả phía TRANG GỐC. Phải trông GIỐNG HỆT `.drop-overlay` trong popup.css: hai lớp
    // phủ nằm ở hai document khác nhau (bắt buộc — sự kiện kéo-thả không qua được biên iframe, mỗi
    // bên phải tự vẽ lấy), nhưng cán bộ chỉ nhìn thấy MỘT panel nên phải ra đúng một hình.
    //
    // Kéo file vào từ header → chỉ content.js thấy sự kiện → mask này hiện. Kéo thẳng vào giữa
    // iframe → chỉ popup.js thấy → lớp phủ của popup hiện. Trước đây hai lớp lệch nhau cả KIỂU
    // (viền 1px/2px, bo 5px/8px, nền .88/.92, đậm 600/700, icon 26px/28px, chỉ bên này có blur) lẫn
    // KHUNG (mask cũ `inset: 6px` tính theo CẢ panel nên trùm luôn header, còn lớp phủ trong iframe
    // chỉ trùm phần iframe) — nên tuỳ đường con trỏ đi vào mà hiện ra hai overlay trông khác hẳn
    // nhau. Giờ khung mask khớp đúng khung iframe (top đặt lại theo iframe.offsetTop trong
    // showMask) và kiểu chép đúng popup.css. Sửa kiểu ở đây thì phải sửa kèm bên popup.css.
    //
    // Tông XANH DƯƠNG trùng màu header panel (#1565c0) — không dùng xanh lá vì màu đó đã có nghĩa
    // riêng "đã kết nối máy quét" trong popup.js. Ẩn mặc định, KHÔNG chặn click (pointer-events
    // none) khi ẩn để không cản thao tác bình thường trên panel/iframe.
    const dropMask = document.createElement("div");
    dropMask.id = DROP_MASK_ID;
    const dropMaskIcon = document.createElement("div");
    dropMaskIcon.textContent = "📥";
    Object.assign(dropMaskIcon.style, { fontSize: "28px", lineHeight: "1" });
    const dropMaskText = document.createElement("div");
    dropMaskText.textContent = "Thả file vào đây để đính kèm";
    dropMask.append(dropMaskIcon, dropMaskText);
    Object.assign(dropMask.style, {
      // top là giá trị tạm — showMask() đặt lại theo mép trên iframe trước mỗi lần hiện.
      position: "absolute", left: "6px", right: "6px", bottom: "6px", top: "6px", zIndex: "1",
      display: "none", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: "6px",
      background: "rgba(255,255,255,.92)", border: "2px dashed #1565c0", borderRadius: "5px",
      color: "#1565c0", fontSize: "13px", fontWeight: "700", lineHeight: "1.35", textAlign: "center",
      padding: "12px", pointerEvents: "none",
      backdropFilter: "blur(6px)", WebkitBackdropFilter: "blur(6px)",
      opacity: "0", transition: "opacity 140ms ease",
    });
    root.appendChild(dropMask);
    console.log("[AutoFill][DnD] mask kéo-thả đã dựng:", DROP_MASK_ID, dropMask);
    wireExternalFileDrop(root, iframe, dropMask);

    document.documentElement.appendChild(root);
    enableDrag(root, header);
    setPanelOpen(true);
    setPanelMinimized(false); // dựng panel FULL → không còn ở trạng thái thu nhỏ
    clearAutoMinState();
  }

  // ===== Kéo-thả file từ NGOÀI (Finder/Explorer) vào thẳng panel =====
  // CHỈ gắn trên chính panel (root = #autofill-hcc-panel), KHÔNG gắn trên document/trang gốc —
  // gắn ở document sẽ preventDefault() MỌI kéo-file trên cả trang, kể cả lúc cán bộ không hề định
  // thả vào extension (có thể phá luôn ô tải file khác của chính trang cổng dịch vụ công).
  //
  // Panel chứa iframe (popup.html) chiếm gần hết diện tích — nếu con trỏ rơi ĐÚNG vào vùng iframe
  // ngay từ đầu thì `content.js` không thấy được (iframe là document riêng, sự kiện kéo-thả không
  // tự nổi bọt qua biên iframe) — NHƯNG lúc đó bản thân iframe (popup.js) mới là nơi nhận đúng sự
  // kiện, không cần content.js can thiệp. `root` chỉ cần lo phần diện tích THẬT SỰ thuộc trang gốc
  // (header, viền quanh iframe) — đúng những gì con trỏ phải đi qua để vào tới panel từ ngoài.
  //
  // Gọi lại MỖI LẦN tạo panel (createPanel tạo `root` mới mỗi lần) — không dùng cờ dedup trên
  // window nữa vì listener giờ gắn trên phần tử `root` cụ thể (bị gỡ khỏi DOM cùng lúc panel đóng),
  // không phải trên document sống mãi suốt trang.
  function isFileDrag(e) {
    const types = e.dataTransfer?.types;
    return !!types && Array.from(types).includes("Files");
  }
  function wireExternalFileDrop(root, iframe, mask) {
    console.log("[AutoFill][DnD] wireExternalFileDrop: đã gắn listener trên #" + PANEL_ID + ".");
    let dragCount = 0;
    const showMask = () => {
      // Khớp khung với lớp phủ BÊN TRONG iframe (`.drop-overlay`, popup.css): cùng lùi 6px so với
      // mép iframe, nên kéo vào từ header hay kéo thẳng vào iframe đều ra đúng một hình ở đúng một
      // chỗ — không còn cảnh "hiện thêm một overlay mới" khi con trỏ đi qua biên iframe. Đọc lại
      // offsetTop mỗi lần hiện chứ không đo một lần lúc dựng: header cao thấp khác nhau tuỳ tiêu đề
      // có xuống dòng hay không, và panel dựng xong mới biết chiều cao thật.
      mask.style.top = (iframe.offsetTop + 6) + "px";
      mask.style.display = "flex";
      mask.style.pointerEvents = "auto";
      // display:none -> flex rồi đổi opacity NGAY trong cùng 1 nhịp sẽ không transition (trình
      // duyệt gộp 2 thay đổi cùng frame) — chờ 1 frame để "flex" áp dụng xong mới bật opacity.
      requestAnimationFrame(() => { mask.style.opacity = "1"; });
    };
    const hideMask = () => {
      dragCount = 0;
      mask.style.opacity = "0";
      mask.style.pointerEvents = "none";
      setTimeout(() => { if (mask.style.opacity === "0") mask.style.display = "none"; }, 150);
    };
    root.addEventListener("dragenter", (e) => {
      const fileDrag = isFileDrag(e);
      console.log("[AutoFill][DnD] dragenter (trên panel)", { fileDrag, types: e.dataTransfer?.types });
      if (!fileDrag) return;
      dragCount++;
      showMask();
    });
    root.addEventListener("dragover", (e) => {
      if (isFileDrag(e)) e.preventDefault(); // bat buoc de "drop" ban ra dung vi tri
    });
    root.addEventListener("dragleave", (e) => {
      if (!isFileDrag(e)) return;
      dragCount = Math.max(0, dragCount - 1);
      console.log("[AutoFill][DnD] dragleave (trên panel), dragCount còn:", dragCount);
      if (dragCount === 0) hideMask();
    });
    root.addEventListener("drop", (e) => {
      const fileDrag = isFileDrag(e);
      console.log("[AutoFill][DnD] drop (trên panel)", {
        fileDrag, maskDisplay: mask.style.display,
        target: e.target, isMaskTarget: e.target === mask,
        fileCount: e.dataTransfer?.files?.length,
      });
      if (!fileDrag) return;
      e.preventDefault(); // rơi trong root la chac chan thuoc panel - luon nhan, khong can kiem target === mask
      hideMask();
      const files = e.dataTransfer?.files;
      if (!files || !files.length) return;
      console.log("[AutoFill][DnD] gửi", files.length, "file sang iframe, iframe tồn tại:", !!iframe?.contentWindow);
      if (iframe?.contentWindow) {
        iframe.contentWindow.postMessage({ type: "autofill-hcc-drop-files", files: [...files] }, "*");
      }
    });
  }

  // ===== Xem trước giấy tờ TRÊN TRANG GỐC =====
  // Panel chỉ rộng 360px, không xem nổi một tờ A4 — nên khung xem trước phải nằm ngoài panel,
  // trên chính trang gốc, mới đủ chỗ.
  //
  // Nội dung là một iframe trỏ tới trang CỦA EXTENSION (preview.html) chứ không phải blob PDF
  // nhét thẳng vào trang gốc: cách sau phụ thuộc frame-src/object-src trong CSP của từng cổng
  // dịch vụ công, cổng nào siết là hỏng im lặng. Nhúng iframe chrome-extension:// thì đã được
  // chứng minh chạy trên cả 21 cổng — chính panel này là một iframe như vậy.
  const PREVIEW_ID = "autofill-hcc-preview";
  // Ân hạn sau khi rời DÒNG FILE: chuyển động trong khoảng này không tính là "đã đi chỗ khác", vì
  // con trỏ còn đang vượt khe từ panel sang khung (xem choChuotRoiDi).
  const PREVIEW_AN_HAN_MS = 500;
  let previewBox = null;      // khung noi tren trang goc
  let previewFrame = null;    // iframe preview.html ben trong
  let previewSanSang = false; // preview.js da bao ready chua
  let previewChoVe = null;    // du lieu xep hang cho toi khi iframe san sang
  let previewChoRoiDi = false; // đang xem tạm, con trỏ đã rời dòng file — chờ bằng chứng nó đi chỗ khác
  let previewTinTuLuc = 0;      // mốc hết ân hạn
  // Key file ĐANG GHIM ("" = không ghim). Cán bộ nhấn vào dòng file → ghim: khung không tự tắt khi
  // rời chuột nữa, chỉ đóng bằng ✕ / bấm ra ngoài / Esc (xem dongPreview).
  let previewGhimKey = "";
  const previewCache = new Map(); // key -> {name, mime, dataUrl}, khoi gui lai megabyte moi lan hover

  function dungPreview() {
    if (previewBox) return previewBox;
    const box = document.createElement("div");
    box.id = PREVIEW_ID;
    Object.assign(box.style, {
      position: "fixed", display: "none", zIndex: "2147483645", // duoi panel 1 bac, khong che panel
      background: "#fff", border: "1px solid #ccc", borderRadius: "8px", overflow: "hidden",
      boxShadow: "0 8px 32px rgba(0,0,0,.22)",
    });
    const f = document.createElement("iframe");
    f.id = PREVIEW_ID + "-iframe";
    f.src = chrome.runtime.getURL("preview.html");
    Object.assign(f.style, { border: "0", width: "100%", height: "100%", display: "block", background: "#f4f6f9" });
    box.appendChild(f);
    document.documentElement.appendChild(box);
    previewBox = box;
    previewFrame = f;
    return box;
  }

  // Đặt khung xem trước vào KHOẢNG TRỐNG LỚN NHẤT quanh panel.
  //
  // Bản đầu chốt CỠ trước (0.48vw × 0.7vh) rồi mới tìm chỗ — sai gốc: khi không đủ chỗ hai bên,
  // nhánh dự phòng kẹp khung về `vw - w` tức là đặt ĐÈ LÊN PANEL. Màn hẹp (<735px) luôn rơi vào
  // nhánh đó, và panel kéo ra giữa màn cũng vậy. Giờ làm ngược lại: đo 4 khoảng trống quanh panel
  // trước, chọn ô dùng được lớn nhất, rồi mới co khung cho vừa ô đó — không bao giờ đè lên panel.
  const PREVIEW_LE = 10;      // le voi mep man hinh
  const PREVIEW_KHE = 10;     // khe giua khung va panel
  const PREVIEW_W_MAX = 720, PREVIEW_H_MAX = 900;
  const PREVIEW_W_MIN = 260, PREVIEW_H_MIN = 200; // duoi muc nay thi xem cung khong ra gi

  function oTrongQuanhPanel(p, vw, vh) {
    return [
      { ten: "trai", x: PREVIEW_LE, y: PREVIEW_LE, w: p.left - PREVIEW_KHE - PREVIEW_LE, h: vh - 2 * PREVIEW_LE },
      { ten: "phai", x: p.right + PREVIEW_KHE, y: PREVIEW_LE, w: vw - PREVIEW_LE - (p.right + PREVIEW_KHE), h: vh - 2 * PREVIEW_LE },
      { ten: "tren", x: PREVIEW_LE, y: PREVIEW_LE, w: vw - 2 * PREVIEW_LE, h: p.top - PREVIEW_KHE - PREVIEW_LE },
      { ten: "duoi", x: PREVIEW_LE, y: p.bottom + PREVIEW_KHE, w: vw - 2 * PREVIEW_LE, h: vh - PREVIEW_LE - (p.bottom + PREVIEW_KHE) },
    ];
  }

  // Trả {x,y,w,h,deLen}. deLen=true nghĩa là không còn ô nào dùng được (màn quá bé / panel quá to)
  // nên đành phủ cả màn và nâng lên TRÊN panel — thà che panel còn hơn hiện một khung 100px vô dụng.
  function tinhChoPreview(vw, vh, p) {
    const caMan = { x: PREVIEW_LE, y: PREVIEW_LE, w: vw - 2 * PREVIEW_LE, h: vh - 2 * PREVIEW_LE };
    let o = null;
    if (p) {
      // Diện tích DÙNG ĐƯỢC (đã chặn trần theo cỡ tối đa): một ô rộng mênh mông nhưng cao 150px
      // không hơn gì ô 700x800 — chặn trần rồi mới so mới ra đúng thứ tự ưu tiên.
      const dienTich = (c) => Math.min(c.w, PREVIEW_W_MAX) * Math.min(c.h, PREVIEW_H_MAX);
      const hopLe = oTrongQuanhPanel(p, vw, vh).filter((c) => c.w >= PREVIEW_W_MIN && c.h >= PREVIEW_H_MIN);
      if (hopLe.length) o = hopLe.reduce((a, b) => (dienTich(b) > dienTich(a) ? b : a));
    } else {
      o = caMan; // panel dang thu nho/dong -> ca man hinh la cua minh
    }
    const deLen = !o;
    if (!o) o = caMan;
    const w = Math.max(1, Math.min(o.w, PREVIEW_W_MAX));
    const h = Math.max(1, Math.min(o.h, PREVIEW_H_MAX));
    // ÁP SÁT PANEL, không canh giữa ô trống. Canh giữa nhìn cân nhưng đẩy khung ra xa: màn 1920,
    // panel left=1548 → ô trái rộng 1528, khung 720 canh giữa nằm ở x=414, mép phải 1134, tức
    // CÁCH PANEL 414px — rê chuột từ dòng file sang khung không kịp trước khi hết giờ ẩn.
    // Áp sát thì khoảng phải vượt luôn đúng bằng PREVIEW_KHE (10px).
    const kep = (v, min, max) => Math.max(min, Math.min(v, max));
    let x, y;
    if (o.ten === "trai") { x = o.x + o.w - w; y = kep(p ? p.top : o.y, PREVIEW_LE, vh - PREVIEW_LE - h); }
    else if (o.ten === "phai") { x = o.x; y = kep(p ? p.top : o.y, PREVIEW_LE, vh - PREVIEW_LE - h); }
    else if (o.ten === "tren") { y = o.y + o.h - h; x = kep(p ? p.left : o.x, PREVIEW_LE, vw - PREVIEW_LE - w); }
    else if (o.ten === "duoi") { y = o.y; x = kep(p ? p.left : o.x, PREVIEW_LE, vw - PREVIEW_LE - w); }
    else { x = Math.round(o.x + (o.w - w) / 2); y = Math.round(o.y + (o.h - h) / 2); } // ca man / de len
    return { w, h, x: Math.round(x), y: Math.round(y), deLen, phia: o.ten || "caman" };
  }

  function rectPanelHienTai() {
    const panel = document.getElementById(PANEL_ID);
    if (!panel || panel.style.display === "none") return null; // dang thu nho -> coi nhu khong co
    const r = panel.getBoundingClientRect();
    return r.width && r.height ? r : null;
  }

  function datChoPreview(box) {
    const c = tinhChoPreview(window.innerWidth, window.innerHeight, rectPanelHienTai());
    Object.assign(box.style, {
      width: c.w + "px", height: c.h + "px", left: c.x + "px", top: c.y + "px",
      zIndex: c.deLen ? "2147483647" : "2147483645",
    });
  }

  function guiChoPreview(payload) {
    if (!previewSanSang) { previewChoVe = payload; return; } // xep hang, gui khi iframe bao ready
    previewFrame?.contentWindow?.postMessage({ type: "autofill-hcc-preview-render", ...payload }, "*");
  }

  function hienPreview(dl) {
    const box = dungPreview();
    previewChoRoiDi = false;
    datChoPreview(box);
    box.style.display = "block";
    guiChoPreview({ ...dl, ghim: !!previewGhimKey });
  }

  // Đóng HẲN. Khác chuotDaRoiDi: hàm kia là "xem tạm mà con trỏ đã đi chỗ khác" và bị bỏ qua khi
  // đang ghim; hàm này là quyết định của cán bộ (✕, bấm ra ngoài, Esc) nên luôn đóng và bỏ ghim.
  function dongPreview() {
    previewChoRoiDi = false;
    previewGhimKey = "";
    if (!previewBox || previewBox.style.display === "none") return;
    previewBox.style.display = "none";
    baoPanelDaAnPreview();
  }

  // Rời DÒNG file (chưa ghim) thì CHƯA ẩn — con trỏ có thể đang đi sang khung để cuộn xem trang 2, 3.
  // Chỉ ẩn khi có BẰNG CHỨNG con trỏ đã đi chỗ khác: trang gốc hoặc panel nhận lại mousemove.
  //
  // Vì sao không dựa vào mouseenter của khung như bản trước: khung chứa iframe KHÁC TIẾN TRÌNH
  // (preview.html, trong đó lồng trình xem PDF). Đo 2026-09-13 bằng sự kiện chuột của chính trình
  // duyệt: rê từ trang vào khung KHÔNG bắn một mouseenter nào lên khung ở trang cha — chỉ viền 1px là
  // của trang cha, đường rê bình thường nhảy qua. Hẹn giờ ẩn cũ vì thế luôn nổ và khung tắt ngay dưới
  // tay cán bộ. Còn khi con trỏ nằm trên khung thì trang cha và panel đều im lặng — tín hiệu đáng tin.
  function choChuotRoiDi() {
    if (previewGhimKey || !previewBox || previewBox.style.display === "none") return;
    previewChoRoiDi = true;
    previewTinTuLuc = Date.now() + PREVIEW_AN_HAN_MS;
  }

  function chuotDaRoiDi() {
    if (!previewChoRoiDi || previewGhimKey || Date.now() < previewTinTuLuc) return;
    previewChoRoiDi = false;
    if (!previewBox || previewBox.style.display === "none") return;
    previewBox.style.display = "none";
    baoPanelDaAnPreview();
  }

  // Đổi cỡ cửa sổ / zoom / kéo panel trong lúc đang xem: ô trống quanh panel đổi theo, phải tính
  // lại chứ không để khung nằm sai chỗ (hoặc đè lên panel) cho tới lần hover sau.
  window.addEventListener("resize", () => {
    // Thu nhỏ cửa sổ cũng đẩy panel ra ngoài y như kéo quá tay — kẹp lại. Chỉ áp cho panel ĐÃ
    // được kéo (có `left` tường minh); panel chưa kéo vẫn neo theo `right`, trình duyệt tự lo.
    const panel = document.getElementById(PANEL_ID);
    if (panel && panel.style.left && panel.style.right === "auto") {
      const v = kepPanelTrongMan(panel, parseFloat(panel.style.left) || 0, parseFloat(panel.style.top) || 0);
      panel.style.left = v.left + "px";
      panel.style.top = v.top + "px";
    }
    if (previewBox && previewBox.style.display !== "none") datChoPreview(previewBox);
  });

  // Panel tự tô sáng dòng file đang xem, nhưng nó KHÔNG biết lúc nào khung tắt (khung do
  // content.js quản, còn giữ mở khi con trỏ rê lên khung). Phải báo ngược thì panel mới bỏ
  // tô đúng lúc — không thì dòng sáng mãi dù khung đã tắt từ đời nào.
  // ---- Báo hoạt động của TRANG GỐC cho panel ------------------------------
  //
  // Panel nằm trong iframe nên nó mù với mọi thứ xảy ra ngoài khung: cán bộ gõ
  // vào form trên cổng thì `document.hasFocus()` của panel trả false và panel
  // tưởng cán bộ đã bỏ đi. Hai tín hiệu dưới đây vá đúng chỗ mù đó.
  //
  // `document.hasFocus()` gọi ở ĐÂY (document của trang gốc) mới đúng: theo
  // spec nó trả true khi focus nằm ở tài liệu này HOẶC bất kỳ frame con nào —
  // tức là "cửa sổ này có đang được dùng không", đúng thứ cần biết.
  const NHIP_BAO_HOAT_DONG_MS = 2000;
  let lucBaoHoatDongCuoi = 0;
  let lucHoatDongTrangCuoi = Date.now(); // dùng cho câu hỏi "tab này có đang được dùng không"

  function guiToiPanel(msg) {
    const f = document.getElementById(IFRAME_ID);
    f?.contentWindow?.postMessage(msg, "*");
  }

  function baoHoatDongTrang() {
    const gio = Date.now();
    lucHoatDongTrangCuoi = gio;
    if (gio - lucBaoHoatDongCuoi < NHIP_BAO_HOAT_DONG_MS) return; // gom bớt: mousemove bắn liên tục
    lucBaoHoatDongCuoi = gio;
    guiToiPanel({ type: "autofill-hcc-hoat-dong" });
  }

  function baoTrangThaiTrang() {
    guiToiPanel({
      type: "autofill-hcc-trang-thai-trang",
      focus: document.hasFocus(),
      an: document.visibilityState === "hidden",
    });
  }

  if (IS_TOP_FRAME) {
    for (const ev of ["mousemove", "mousedown", "keydown", "wheel", "touchstart", "click", "scroll"]) {
      document.addEventListener(ev, baoHoatDongTrang, { passive: true, capture: true });
    }
    window.addEventListener("focus", baoTrangThaiTrang);
    window.addEventListener("blur", baoTrangThaiTrang);
    document.addEventListener("visibilitychange", baoTrangThaiTrang);
    // Nhịp đều: panel có thể được dựng SAU khi trang đã mất/được focus từ lâu,
    // lúc đó không còn event nào để nó bám vào.
    setInterval(baoTrangThaiTrang, 3000);
  }

  function baoPanelDaAnPreview() {
    const f = document.getElementById(IFRAME_ID);
    f?.contentWindow?.postMessage({ type: "autofill-hcc-preview-hidden" }, "*");
  }

  function goPreview() {
    baoPanelDaAnPreview();
    previewChoRoiDi = false;
    previewBox?.remove();
    previewBox = null;
    previewFrame = null;
    previewSanSang = false;
    previewChoVe = null;
    previewGhimKey = "";
  }

  window.addEventListener("message", (e) => {
    const d = e.data;
    if (!d || typeof d.type !== "string") return;
    // preview.js (iframe con): bấm ✕ hoặc Esc trong khung.
    if (d.type === "autofill-hcc-preview-close" && previewFrame && e.source === previewFrame.contentWindow) {
      dongPreview();
      return;
    }
    // preview.js (iframe con) bao da san sang nhan du lieu.
    if (d.type === "autofill-hcc-preview-ready" && previewFrame && e.source === previewFrame.contentWindow) {
      previewSanSang = true;
      if (previewChoVe) { const tmp = previewChoVe; previewChoVe = null; guiChoPreview(tmp); }
      return;
    }
    // popup.js (panel) yeu cau hien/an. Chi nhan tu dung iframe panel.
    const panelFrame = document.getElementById(IFRAME_ID);
    if (!panelFrame || e.source !== panelFrame.contentWindow) return;
    if (d.type === "autofill-hcc-tra-loi-ban") { hienCanhBaoBan(!!d.ban); return; }
    if (d.type === "autofill-hcc-preview-show") {
      // Co dataUrl thi cache lai; lan sau popup chi gui `key` (PDF 3MB ~ 4MB base64, gui moi
      // lan hover la phi bang thua).
      if (d.dataUrl) previewCache.set(d.key, { name: d.name, mime: d.mime, dataUrl: d.dataUrl });
      const dl = previewCache.get(d.key);
      // Sửa tên file xong thì panel gửi lại `preview-show` với tên MỚI nhưng KHÔNG kèm dataUrl
      // (nội dung có đổi đâu, gửi lại megabyte làm gì). Phải vá tên vào bản cache, không thì
      // khung vẫn treo tên cũ cho tới lúc rê sang file khác rồi rê về.
      if (dl && d.name && d.name !== dl.name) dl.name = d.name;
      // Ghim: nhấn dòng file (ghim=true) thì chuyển ghim sang file đó. Rê chuột qua file KHÁC trong
      // lúc đang ghim thì bỏ qua — ghim là để đọc lâu, khung không được giật theo con trỏ.
      // Cache ở trên vẫn phải chạy trước: lần sau nhấn vào file đó thì khỏi gửi lại megabyte.
      if (d.ghim) previewGhimKey = d.key;
      else if (previewGhimKey && d.key !== previewGhimKey) return;
      if (!dl) { previewFrame && guiChoPreview({ name: d.name, mime: d.mime, dataUrl: "" }); return; }
      hienPreview(dl);
    } else if (d.type === "autofill-hcc-preview-hide") {
      choChuotRoiDi(); // rời dòng file: CHƯA ẩn, chờ bằng chứng con trỏ đi chỗ khác
    } else if (d.type === "autofill-hcc-preview-chuot-o-panel") {
      chuotDaRoiDi();  // con trỏ đang ở chỗ khác trong panel
    } else if (d.type === "autofill-hcc-preview-close") {
      dongPreview(); // panel: bấm ra ngoài dòng file / Esc trong panel
    }
  });

  // Bấm ra ngoài khung xem trước trên TRANG GỐC, hoặc Esc → đóng. Bấm vào panel thì không xử lý ở
  // đây: bấm TRONG iframe panel không tới được document này, còn bấm vào viền/tay kéo panel là
  // đang thao tác với panel chứ không phải "bỏ đi" — popup.js tự quyết phần bên trong.
  if (IS_TOP_FRAME) {
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
    // hay viền/tay kéo panel thì chưa tính — phần bên trong panel do popup.js tự báo.
    document.addEventListener("mousemove", (e) => {
      if (!previewChoRoiDi || !previewBox || previewBox.contains(e.target)) return;
      const panel = document.getElementById(PANEL_ID);
      if (panel && panel.contains(e.target)) return;
      chuotDaRoiDi();
    }, { capture: true, passive: true });
    // background ghi / xoá "bản mới đang chờ" → vẽ lại nút Cập nhật trên header panel.
    try {
      chrome.storage.onChanged.addListener((thayDoi, vung) => {
        if (vung === "local" && KHOA_BAN_CHO in thayDoi) veNutCapNhat();
      });
    } catch (e) { /* context mất */ }
  }

  // Dựng bubble góc phải trên (nếu chưa có). Tách riêng để nhánh khôi phục sau reload gọi được mà
  // KHÔNG cần panel tồn tại — reload lúc đang thu nhỏ chỉ dựng lại bubble, không bung panel che form.
  function showBubble() {
    if (document.getElementById(BUBBLE_ID)) return;
    const bubble = document.createElement("div");
    bubble.id = BUBBLE_ID;
    bubble.title = "Mở Trợ lý nhân dân";
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

  // Kẹp panel nằm TRỌN trong màn hình. Bản cũ chỉ kẹp `Math.max(0, ...)` — chặn được mép trái và
  // mép trên, bỏ ngỏ mép phải/dưới: kéo quá tay là panel ra hẳn ngoài màn và KHÔNG CÓ CÁCH NÀO
  // kéo lại (thanh tiêu đề để nắm cũng ra ngoài luôn), chỉ còn nước đóng mở lại hoặc F5.
  function kepPanelTrongMan(root, left, top) {
    const r = root.getBoundingClientRect();
    // Panel cao hơn cả màn (danh sách file dài) thì maxTop = 0 — cho dính mép trên, không âm.
    const maxLeft = Math.max(0, window.innerWidth - r.width);
    const maxTop = Math.max(0, window.innerHeight - r.height);
    return {
      left: Math.min(Math.max(0, left), maxLeft),
      top: Math.min(Math.max(0, top), maxTop),
    };
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
      const v = kepPanelTrongMan(root, startLeft + e.clientX - startX, startTop + e.clientY - startY);
      root.style.left = v.left + "px";
      root.style.top = v.top + "px";
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
    // Trả lời cho background trước khi extension tự nạp lại (xem popup.js khối
    // extUpdate*). Nạp lại giữa lúc panel đang mở KHÔNG làm panel biến mất —
    // đo 2026-09-11: iframe vẫn hiển thị y nguyên, nhưng mọi chrome.* bên trong
    // ném "Extension context invalidated" và content script này thành mồ côi.
    // Cán bộ bấm nút mà không có gì xảy ra, không một dấu hiệu nào. Vì vậy còn
    // panel mở là KHÔNG được nạp lại.
    // Tab này có đang được dùng không — dùng để quyết định lúc nào được nạp lại
    // extension. Chỉ frame chính trả lời: iframe con không có panel, mà cũng
    // không đại diện cho "cửa sổ có đang được dùng".
    if (msg?.action === "hccTabDangLamViec") {
      if (!IS_TOP_FRAME) return;
      const gio = Date.now();
      sendResponse({
        coPanel: !!document.getElementById(PANEL_ID) || !!document.getElementById(BUBBLE_ID),
        focus: document.hasFocus(),
        an: document.visibilityState === "hidden",
        imLangMs: gio - (lucHoatDongTrangCuoi || 0),
      });
      return;
    }
    // Gỡ panel NGAY TRƯỚC khi extension nạp lại.
    //
    // Đo 2026-09-11: nạp lại KHÔNG làm panel biến mất — nó ở nguyên đó nhưng mọi
    // chrome.* bên trong ném "Extension context invalidated". Cán bộ bấm nút mà
    // không có gì xảy ra, không một dấu hiệu nào. Gỡ đi thì hỏng trở nên NHÌN
    // THẤY ĐƯỢC, mà lại tự lành: cờ "panel đang mở" trong chrome.storage được
    // GIỮ NGUYÊN, nên lần điều hướng kế tiếp content script mới được tiêm vào và
    // tự mở lại panel (xem nhánh đọc panelOpenKey lúc khởi tạo).
    if (msg?.action === "hccGoPanelTruocKhiNapLai") {
      if (!IS_TOP_FRAME) { sendResponse({ ok: true }); return; }
      try {
        document.getElementById(PANEL_ID)?.remove();
        document.getElementById(BUBBLE_ID)?.remove();
      } catch (e) { /* ignore */ }
      sendResponse({ ok: true });
      return;
    }
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
        order: withFinalTaxPass([...BUSINESS_PAGE_ORDER], pages),
        pages,
        step: 0,
        retries: 0,
        phase: "fill",
        filledStep: -1,
        // Default theo tài khoản/phường (vd Xuân Hương) do popup truyền xuống; giữ trong state để sống qua postback.
        businessDefaults: (msg && msg.businessDefaults) || null,
        // Gộp đính kèm: điền xong 8 trang → tự chạy state machine đính kèm (nếu popup gửi kèm).
        attachPayload: (msg && msg.attachPayload) || null,
        // Còn đứng ở wizard (Chọn loại đăng ký / Xác nhận) thì tự bấm Thành lập mới → Tiếp theo → Bắt đầu
        // trước khi điền; đã ở trong hồ sơ thì bước này tự đánh dấu xong ngay lượt đầu.
        createBootstrap: true,
        bootstrapDone: false,
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
      const order = withFinalTaxPass(Array.isArray(flow.pageOrder) && flow.pageOrder.length
        ? [...flow.pageOrder] : ["nguoi-nop-ho-so"], pages);
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
    const isStandardField = (f) =>
      String(f?.comp || "").startsWith("dom-") || String(f?.name || "").startsWith("data[");
    const isLegacyField = (f) => String(f?.comp || "").startsWith("x-");
    // Một thủ tục có thể trả HAI bộ ô cho hai frame (vd Xác nhận thông tin hộ tịch: trang cổng Form.io
    // data[...] + eForm hộ tịch x-* trong iframe tokhaidientu). Không tách thì ô data[...] ép frame eForm
    // sang engine standard và toàn bộ ô x-* bị bỏ. Frame nào chỉ giữ bộ của mình; không còn ô nào thì im
    // lặng để frame kia trả lời popup.
    if (fields.some(isStandardField) && fields.some(isLegacyField)) {
      fields = formKind === "legacy"
        ? fields.filter((f) => !isStandardField(f))
        : fields.filter((f) => !isLegacyField(f));
      if (!fields.length) return;
    }
    const forceStandard = fields.some(isStandardField);
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

  // ===== Mốc "cán bộ bấm Gửi hồ sơ" =====
  // Chỉ CHẤM MỐC kết thúc hồ sơ, không can thiệp cú bấm. Đặt ở content script (không ở popup)
  // để vẫn ghi được khi panel đã đóng. Luật do BE cấp (portal_submit.py) → thêm cổng mới không
  // phải phát hành lại extension.
  if (IS_TOP_FRAME) {
    let submitRules = null;
    let lastSubmitClickAt = 0;
    // SUBMIT_WATCH_KEY vốn do api/config.js cấp. Nếu content.js bị inject THIẾU file đó, tham chiếu
    // trần sẽ ném ReferenceError ngay tại top-level → IIFE dừng giữa chừng, các const phía sau
    // (sleep, FIELD_NAME_ALIASES...) không kịp khởi tạo và MỌI lần điền sau đó đều hỏng. Đọc qua
    // window + fallback hằng để một file thiếu không giết cả content script.
    const SUBMIT_WATCH_KEY = (typeof window !== "undefined" && window.SUBMIT_WATCH_KEY)
      || "autofill_submit_watch";
    const SUBMIT_CLICKABLE = 'button, a, input[type="submit"], input[type="button"]';

    const foldSubmitLabel = (s) => String(s || "")
      .replace(/Đ/g, "D").replace(/đ/g, "d")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/\s+/g, " ").trim().toLowerCase();

    chrome.storage.local.get([SUBMIT_WATCH_KEY], (res) => {
      void chrome.runtime.lastError;
      submitRules = res?.[SUBMIT_WATCH_KEY]?.rules || null;
    });
    // Popup nạp /procedures sau khi content script đã chạy → nghe thay đổi để khỏi lỡ hồ sơ đầu.
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local" || !changes[SUBMIT_WATCH_KEY]) return;
      submitRules = changes[SUBMIT_WATCH_KEY].newValue?.rules || null;
    });

    document.addEventListener("click", (e) => {
      if (!submitRules) return;
      const rule = submitRules[location.hostname];
      if (!rule) return;
      // input[type=submit]: cổng HkdOnline (ASP.NET) dùng input chứ không phải button/a.
      const el = e.target?.closest?.(SUBMIT_CLICKABLE);
      if (!el) return;
      // Cổng chặn BẮT BUỘC: chỉ đúng trang nộp hồ sơ. Nút chữ giống nhau ở trang chủ/tra cứu
      // mà tính nhầm là thổi phồng số hồ sơ — sai kiểu đó không ai phát hiện ra.
      let ref = "";
      if (rule.urlPattern) {
        // pathname + hash: cổng SPA (liên thông) để đường dẫn trong hash, bỏ hash là không
        // phân biệt nổi trang nào. Query cố ý bỏ — nó đổi liên tục theo phiên.
        let m = null;
        try { m = new RegExp(rule.urlPattern).exec(location.pathname + location.hash); }
        catch (_) { return; }
        if (!m) return;
        ref = m[1] || "";
      }
      // <input> không có textContent — nhãn nằm ở value.
      const label = foldSubmitLabel(el.tagName === "INPUT" ? el.value : el.textContent);
      let hit = (rule.buttonIds || []).includes(String(el.id || ""))
        || (rule.buttonText || []).some((t) => label === t);
      // Nền tảng Form.io: nút cuối không có id và nhãn đổi theo thủ tục ("Nộp hồ sơ" vs
      // "Thanh toán") → chỉ còn thuộc tính là mỏ neo ổn định.
      if (!hit && rule.buttonSelector) {
        try { hit = el.matches(rule.buttonSelector); } catch (_) {}
      }
      if (!hit) return;
      if (Date.now() - lastSubmitClickAt < 3000) return; // bấm dồn / double-click
      lastSubmitClickAt = Date.now();
      try {
        chrome.runtime.sendMessage(
          { action: "dossierSubmitClicked", host: location.hostname, ref },
          () => void chrome.runtime.lastError,
        );
      } catch (_) {}
    }, true); // capture: cổng có handler riêng có thể stopPropagation
  }

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

  /**
   * Hồ sơ kê "Địa chỉ nhận thông báo thuế" = "Giống địa chỉ trụ sở chính": cổng KHÔNG chép địa chỉ
   * trụ sở sang khối thuế ở lượt lưu đầu. Xếp thêm một lượt "Thông tin về thuế" ở CUỐI (sau trang
   * người nộp hồ sơ, ngay trước đính kèm) để quay lại tick "Địa chỉ khác" rồi tick lại "Giống địa
   * chỉ trụ sở chính" và Lưu — lúc đó cổng mới ghi địa chỉ thật. Hồ sơ kê "Địa chỉ khác" đã điền
   * cascade tay nên không cần lượt này.
   */
  function withFinalTaxPass(order, pages) {
    const taxKey = H.TAX_PAGE_KEY || "thong-tin-ve-thue";
    const skip = (why) => {
      console.log("[FillAll] KHÔNG chèn lượt chốt địa chỉ thuế:", why);
      return order;
    };
    if (typeof H.taxWantsSameAsHeadOffice !== "function") return skip("thiếu business-registration.js");
    if (!order.includes(taxKey)) return skip("luồng không đi qua trang thuế");
    if (!H.taxWantsSameAsHeadOffice((pages && pages[taxKey]) || [])) {
      return skip('hồ sơ không kê "Giống địa chỉ trụ sở chính"');
    }
    console.log("[FillAll] chèn lượt chốt địa chỉ thuế vào cuối order");
    return [...order, taxKey];
  }

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
      // Cổng QN "miền núi hải đảo" (vd ĐK tài sản gắn liền đất): bảng thành phần hồ sơ KHÔNG có dòng
      // sẵn, chỉ có nút "Thêm thành phần hồ sơ" để tự thêm từng dòng → vẫn là trang đính kèm hợp lệ.
      // Thiếu nhánh này thì collectAttachmentContext bị gate trượt → không sendResponse → "Không kết nối được trang".
      findButtonByText(document, ["Thêm thành phần hồ sơ"]) ||
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

  /** Lý do THẬT từ cổng (toast/alert), vd "Upload thất bại (File Service): Upload failed: 500".
   *  Không có dòng này thì cán bộ chỉ thấy "cổng chưa ghi nhận" — đúng nhưng không đủ để biết
   *  nên thử lại hay báo quản trị cổng. Cắt 200 ký tự: toast dài thường là nội dung trang. */
  function readPortalUploadError() {
    const nodes = Array.from(document.querySelectorAll(
      '[role="alert"], [role="status"], [class*="toast" i], [class*="notification" i], [class*="snackbar" i]'
    )).filter((node) => isVisible(node));
    for (const node of nodes) {
      const text = String(node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
      if (!text || text.length > 300) continue;
      if (/that bai|failed|loi|error|500|502|503|504/.test(foldChoiceText(text))) return text.slice(0, 200);
    }
    return "";
  }

  async function waitForPersistedAttachment(row, planItem = {}, previousName = "", timeout = 25000) {
    // Modal đóng chỉ chứng minh thao tác click đã chạy. Cổng React có thể đóng modal nhưng request
    // lưu file thất bại; chỉ tên file xuất hiện thật trên dòng hồ sơ mới là hậu điều kiện thành công.
    // Cổng moj hay ĐƠ (block main thread) rất lâu sau "Thêm vào ví & Chọn": nới thời gian (freeze
    // có thể >12s) VÀ CHECK LẦN CUỐI sau khi hết đơ (Date.now vượt hạn ngay trong lúc đơ; thoát mà
    // không kiểm lại là bỏ sót đúng lúc dòng vừa gắn xong → báo "chưa ghi nhận" oan).
    const start = Date.now();
    const probe = () => {
      const liveRow = liveAttachmentRowForVerification(row, planItem);
      if (!liveRow) return null;
      const attachedName = rowAttachedFileName(liveRow);
      if (!attachedName || attachedName === previousName) return null;
      return { row: liveRow, fileName: attachedName };
    };
    while (Date.now() - start < timeout) {
      const hit = probe();
      if (hit) return hit;
      await sleep(150);
    }
    return probe(); // lần cuối: dòng có thể vừa cập nhật ngay khi cổng hết đơ
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

  // Thành phần thêm mới TRÙNG TÊN thành phần đã có (vd bản dịch CTV gộp 1 hồ sơ: nhiều dòng
  // "Bản dịch và giấy tờ, văn bản cần dịch.") → đánh số tăng dần " 2", " 3"… cho tên không trùng.
  // Chỉ kích hoạt khi THỰC SỰ trùng nên không ảnh hưởng thủ tục đặt tên theo từng tài liệu.
  function uniqueComponentName(componentName) {
    const base = String(componentName || "").trim();
    if (!base) return base;
    const existing = findAttachmentRows()
      .map((row) => foldChoiceText(attachmentComponentName(row)))
      .filter(Boolean);
    if (!existing.includes(foldChoiceText(base))) return base;
    for (let n = 2; n < 100; n++) {
      const candidate = `${base} ${n}`;
      if (!existing.includes(foldChoiceText(candidate))) return candidate;
    }
    return base;
  }

  async function addAttachmentComponent(componentName) {
    // Đặt tên duy nhất TRƯỚC khi thêm để mỗi lần thêm là một số mới (2, 3, 4…), tránh trùng tên dòng.
    const uniqueName = uniqueComponentName(componentName);
    const reusableBlankRow = findReusableBlankAttachmentRow();
    if (reusableBlankRow) {
      const beforeRows = findAttachmentCandidateRows();
      await fillAttachmentComponentName(reusableBlankRow, uniqueName);
      const row = await waitFor(() => {
        if (document.documentElement.contains(reusableBlankRow) && componentTextMatches(reusableBlankRow, uniqueName)) {
          return reusableBlankRow;
        }
        const rows = findAttachmentRows();
        return rows.find((candidate) =>
          !beforeRows.includes(candidate) && componentTextMatches(candidate, uniqueName)
        ) || null;
      }, 3000, 100);
      if (row) {
        // KHÔNG tô xanh ở đây: mới thêm được DÒNG TRỐNG, chưa có tệp nào vào. Bước đính sau đó
        // hỏng thì dòng vẫn giữ màu xanh cũ và cán bộ tưởng đã xong.
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
        await fillAttachmentComponentName(dialog, uniqueName);
        await submitComponentName(dialog);
      }
    } else {
      const newRow = await waitFor(() => {
        const rows = findAttachmentCandidateRows();
        if (rows.length > beforeCount) return rows[rows.length - 1];
        return null;
      }, 1500, 100);
      if (newRow && findComponentNameInput(newRow)) {
        await fillAttachmentComponentName(newRow, uniqueName);
        await submitComponentName(newRow);
      }
    }

    const row = await waitFor(() => {
      const rows = findAttachmentCandidateRows();
      if (rows.length > beforeCount) {
        const newRows = rows.filter((row) => !beforeRows.includes(row));
        const matched = newRows.find((candidate) =>
          componentTextMatches(candidate, uniqueName) && !rowHasAttachedFile(candidate)
        );
        return matched || newRows.find((candidate) => !rowHasAttachedFile(candidate)) || null;
      }
      return rows.find((candidate) =>
        componentTextMatches(candidate, uniqueName) && !rowHasAttachedFile(candidate)
      ) || null;
    }, 4000, 120);

    if (!row) throw new Error(`Không thêm được thành phần hồ sơ "${uniqueName}".`);
    // Như trên: tạo được dòng CHƯA PHẢI là đính xong. Màu xanh chỉ được đặt sau khi
    // waitForPersistedAttachment thấy tên tệp hiện thật trên dòng.
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
      const portalError = readPortalUploadError();
      markAttachmentResult(liveRow || dialog, false);
      return {
        error: `Cổng chưa ghi nhận file ${file.name} vào dòng hồ sơ; ô vẫn chưa có tên file`
          + (portalError ? ` — cổng báo: ${portalError}` : "."),
        code: "wallet-file-not-persisted",
        portalError,
        fileNames: [file.name],
        debug: {
          uploadCompleted,
          dialogClosed,
          portalError,
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

  // Hàng trống mà form TỰ THÊM sẵn (tên preset trùng hàng đã có — vd bản dịch CTV gộp 1 hồ sơ):
  // nếu tên đang TRÙNG KHÍT một hàng khác VÀ ô tên SỬA được → đánh số " 2"/" 3"… trước khi đính,
  // để các thành phần thêm mới không trùng tên. Hàng cố định (tên là <p>, không có ô nhập) giữ nguyên.
  async function ensureUniqueEmptyRowName(row, baseName) {
    const base = String(baseName || "").trim();
    if (!base || !findComponentNameInput(row)) return;
    const foldBase = foldChoiceText(base);
    const hasDuplicate = findAttachmentRows().some(
      (other) => other !== row && foldChoiceText(attachmentComponentName(other)) === foldBase
    );
    if (!hasDuplicate) return; // chưa trùng (thường là hàng đầu tiên) → giữ tên gốc
    const uniqueName = uniqueComponentName(base);
    if (uniqueName && foldChoiceText(uniqueName) !== foldBase) {
      await fillAttachmentComponentName(row, uniqueName);
    }
  }

  // LƯỢT CHỐT sau khi đính xong: dòng thành phần THÊM MỚI có ô TÊN là <input> (vd bản dịch CTV
  // nhiều dòng) hay bị cổng để CÙNG một tên → đánh số " 2"/" 3"… vào các input TRÙNG (giữ lần đầu
  // làm gốc). Chạy CUỐI (không có thao tác đính nào sau đó) để React không revert giữa chừng: input
  // controlled + cổng commit tên có debounce ~500ms nên set xong phải CHỜ cho lưu.
  function componentNameInputsOfRow(row) {
    const cell = (row && row.cells && row.cells[1]) || row;
    if (!cell) return [];
    return Array.from(cell.querySelectorAll("input:not([type='file']):not([type='hidden']), textarea"))
      .filter((el) => el.getAttribute("name") !== "documentName");
  }

  // Base (tên gốc, bỏ số đuôi) của ô input tên trong 1 dòng; "" nếu dòng không có ô input.
  function componentNameInputBase(row) {
    const inputs = componentNameInputsOfRow(row);
    if (!inputs.length) return "";
    const primary = inputs.find(isVisible) || inputs[0];
    return String(primary.value || "").trim().replace(/\s+\d+$/, "").trim();
  }

  async function renumberDuplicateComponentNameInputs() {
    const rows = findAttachmentRows();
    if (rows.length < 2) return;
    // Tập base SẠCH lấy từ các ô input (giá trị input không lẫn tên file như text dòng cố định).
    const bases = new Set();
    for (const row of rows) {
      const base = componentNameInputBase(row);
      if (base) bases.add(base);
    }
    for (const base of bases) {
      const foldBase = foldChoiceText(base);
      // Đếm theo THỨ TỰ dòng: dòng CỐ ĐỊNH (tên <p>, không ô input) mà text CHỨA base tính là lần
      // đầu (số 1); mỗi ô input cùng base tăng số → dòng thêm mới thành 2, 3, 4… Dòng cố định giữ nguyên.
      let count = 0;
      for (const row of rows) {
        const inputs = componentNameInputsOfRow(row);
        if (!inputs.length) {
          if (foldChoiceText(attachmentComponentName(row)).includes(foldBase)) count += 1;
          continue;
        }
        if (foldChoiceText(componentNameInputBase(row)) !== foldBase) continue; // input của base khác
        count += 1;
        if (count >= 2) {
          const target = `${base} ${count}`;
          for (const input of inputs) setNativeValue(input, target, { typing: true, commit: true });
          await sleep(650); // > debounce ~500ms để cổng commit tenHoSoKemTheo, tránh bị revert
        }
      }
    }
  }

  async function rowForPlanItem(planItem) {
    const componentName = planItem?.componentName || "Tài liệu chứng thực";
    const emptyExistingRow = findEmptyAttachmentRowByComponent(componentName);
    if (emptyExistingRow) {
      await ensureUniqueEmptyRowName(emptyExistingRow, componentName);
      return emptyExistingRow;
    }
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

  // Bảng thành phần chia NHÁNH ("a) Đối với trường hợp…", "b) Đối với trường hợp…", vd Lào Cai 1.115667):
  // các nhánh lặp lại cùng tên giấy tờ → chỉ giữ input thuộc các dòng nằm giữa tiêu đề nhánh của item và
  // tiêu đề nhánh kế tiếp. Không thấy tiêu đề → rỗng (không đoán sang nhánh khác).
  // Hai kiểu tiêu đề nhóm đã gặp: "a) Đối với trường hợp…" (1.115667/1.115668), "(1) Hồ sơ đề nghị…" (1.115651).
  const FIXED_SLOT_SECTION_RE = /(^|\s)(?:[a-z]\) doi voi truong hop|\(\d+\) ho so de nghi)/;

  function fixedSlotSectionInputs(inputs, sectionHeader) {
    const header = foldChoiceText(sectionHeader);
    const rows = Array.from(document.querySelectorAll("tr"));
    // Lấy dòng tiêu đề TRONG CÙNG (text ngắn nhất): bảng lồng trong <tr> layout thì dòng ngoài cũng chứa header.
    let start = -1;
    rows.forEach((row, i) => {
      const text = foldChoiceText(nodeText(row));
      if (text.includes(header) && (start < 0 || text.length < foldChoiceText(nodeText(rows[start])).length)) start = i;
    });
    if (start < 0) return [];
    let end = rows.length;
    for (let i = start + 1; i < rows.length; i++) {
      if (FIXED_SLOT_SECTION_RE.test(foldChoiceText(nodeText(rows[i])))) {
        end = i;
        break;
      }
    }
    const sectionRows = new Set(rows.slice(start + 1, end));
    return inputs.filter((el) => sectionRows.has(el.closest("tr")));
  }

  // Tích checkbox chọn giấy tờ của dòng (cổng iGate VNPT bọc bằng iCheck: input ẩn, click vào lớp phủ).
  async function tickFixedSlotRow(row) {
    const cb = row?.querySelector?.('input[type="checkbox"]');
    if (!cb || cb.checked) return;
    const helper = cb.parentElement?.querySelector?.("ins.iCheck-helper");
    clickLikeUser(helper || cb.closest("label") || cb);
    await sleep(150);
    if (!cb.checked) {
      cb.checked = true;
      cb.dispatchEvent(new Event("click", { bubbles: true }));
      cb.dispatchEvent(new Event("change", { bubbles: true }));
      if (helper) cb.parentElement.classList.add("checked");
      await sleep(100);
    }
  }

  // Dự phòng: khoanh nhánh trên CHÍNH danh sách dòng thành phần mà findAttachmentRows() nhận ra (cùng nguồn với
  // attachmentContext gửi BE), khớp tên dòng theo từ khóa rồi lấy input file bất kỳ trong dòng.
  function findSectionAttachmentRow(item) {
    const header = foldChoiceText(item.sectionHeader);
    const keywords = (item.slotKeywords || []).map(foldChoiceText).filter(Boolean);
    const rows = findAttachmentRows();
    const names = rows.map((row) => foldChoiceText(attachmentComponentName(row)));
    const start = names.findIndex((name) => name.includes(header));
    if (start < 0 || !keywords.length) return null;
    for (let i = start + 1; i < rows.length; i++) {
      if (FIXED_SLOT_SECTION_RE.test(names[i])) break;
      if (keywords.some((kw) => names[i].includes(kw))) return rows[i];
    }
    return null;
  }

  function findFixedSlotInput(item, usedInputs) {
    if (item.sectionHeader) {
      const scoped = fixedSlotSectionInputs(fixedSlotUploadInputs(), item.sectionHeader)
        .filter((el) => !usedInputs.has(el));
      const keywords = (item.slotKeywords || []).map(foldChoiceText).filter(Boolean);
      if (!keywords.length) return null;
      const byScope = scoped.find((el) => keywords.some((kw) => fixedSlotRowText(el).includes(kw)));
      if (byScope) return byScope;
      const row = findSectionAttachmentRow(item);
      const rowInputs = row ? Array.from(row.querySelectorAll('input[type="file"]')) : [];
      const input = rowInputs.find((el) => !usedInputs.has(el)) || null;
      console.log("[AutoFill-FixedSlot] tra ô theo nhánh", {
        slot: item.slotName,
        scopedInputs: scoped.length,
        rowFound: !!row,
        rowInputs: rowInputs.length,
        rowHtml: row && !input ? row.outerHTML.slice(0, 4000) : undefined,
      });
      return input;
    }
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
    // GÁN THẲNG trước: trên cổng iGate VNPT (Lai Châu/Lào Cai) bấm option "Chọn tệp tin" MỞ HỘP THOẠI FILE
    // của hệ điều hành (chặn UI). Chỉ bấm khi gán hụt, và không bao giờ bấm với bảng chia nhánh.
    let ok = setFilesOnInput(input, [file], { assumeConsumed: true });
    if (!ok && !planItem.noChooserClick) {
      await chooseBootstrapFileOptionForInput(input);
      ok = setFilesOnInput(input, [file], { assumeConsumed: true });
    }
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
    const failedSlots = [];
    const fail = (item, message) => {
      errors.push(message);
      const label = String(item.slotName || item.componentName || "");
      failedSlots.push((label.match(/^[a-z]-\d+/) || [])[0] || label.slice(0, 40));
    };

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
        fail(item, `Không tìm thấy file cho ô "${slotLabel}".`);
        continue;
      }
      const fileNames = files.map((f) => f.name);

      // (1) Ô upload trực tiếp: input ẩn cạnh .btn_upload (vd mai táng).
      let input = findFixedSlotInput(item, usedInputs);
      if (input && item.tickRow) {
        const row = input.closest("tr");
        await tickFixedSlotRow(row);
        // Tích có thể làm cổng dựng lại ô upload của dòng → lấy lại input còn gắn trong DOM.
        if (!input.isConnected && row?.isConnected) {
          input = Array.from(row.querySelectorAll('input[type="file"]')).find(isUploadSlotInput) || null;
        }
      }
      if (input) {
        if (!item.repeatUpload) usedInputs.add(input);
        console.log("[AutoFill-FixedSlot] attaching (input)", { slotIndex: item.slotIndex, slotName: slotLabel, fileNames });
        // GÁN THẲNG bằng DataTransfer TRƯỚC (input ẩn vẫn set được). Nếu đã gán → KHÔNG click "Chọn tệp tin":
        // ở cổng Lai Châu click option đó MỞ HỘP THOẠI FILE GỐC của OS (thừa, chặn UI). Chỉ khi gán hụt
        // (cổng chỉ nhận file sau khi mở dropdown, vd mai táng) mới click rồi thử lại.
        // assumeConsumed: form mai táng reset input.files sau khi đọc → lấy kết quả gán trước dispatch.
        let ok = setFilesOnInput(input, files, { assumeConsumed: true });
        if (!ok && !item.sectionHeader && !item.noChooserClick) {
          await chooseBootstrapFileOptionForInput(input);
          ok = setFilesOnInput(input, files, { assumeConsumed: true });
        }
        await sleep(600);
        const markTarget = input.closest("tr") || input.closest("td") || input.parentElement || input;
        markAttachmentResult(markTarget, ok);
        if (ok) attachedNames.push(...fileNames);
        else fail(item, `Không gắn được file vào ô "${slotLabel}".`);
        continue;
      }

      // Dòng khoanh theo nhánh: không có input trong nhánh thì báo lỗi, KHÔNG rơi xuống menu (fallback
      // "ô trống đầu tiên" sẽ đính nhầm sang nhánh khác).
      if (item.sectionHeader) {
        fail(item, `Không tìm thấy ô đính kèm "${slotLabel}".`);
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
          fail(item, `Không mở được ô đính kèm "${slotLabel}".`);
          continue;
        }
        const ok = setFilesOnInput(menuInput, files, { assumeConsumed: true });
        await sleep(600);
        await closeOpenMenu();
        const markTarget = trigger.closest("tr") || trigger.closest("td") || trigger.parentElement || trigger;
        markAttachmentResult(markTarget, ok);
        if (ok) attachedNames.push(...fileNames);
        else fail(item, `Không gắn được file vào ô "${slotLabel}".`);
        continue;
      }

      fail(item, `Không tìm thấy ô đính kèm "${slotLabel}".`);
    }

    if (errors.length) {
      console.warn("[AutoFill-FixedSlot] lỗi đính kèm", errors);
      // Bảng chia nhánh: ô nào không đính được thì BỎ QUA, vẫn tính là xong nếu có ít nhất một tệp vào được.
      if (attachments.some((it) => it.sectionHeader) && attachedNames.length) {
        return {
          ok: true,
          method: "fixed-slot",
          attached: attachedNames.length,
          skipped: 0,
          fileNames: attachedNames,
          skippedNames: [],
          failedNames: failedSlots.map((label) => `ô ${label}`),
        };
      }
      return {
        // Bảng chia nhánh (Lào Cai): nhiều lỗi nối dài > 160 ký tự sẽ bị friendlyError thay bằng câu chung
        // → báo gọn các ô hỏng, chi tiết để console.
        error: attachments.some((it) => it.sectionHeader)
          ? `Chưa đính kèm được ô: ${failedSlots.join(", ")}.`
          : errors.join("; "),
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
      // Tệp KHÔNG đính được nhưng kế hoạch cho phép bỏ qua (Lào Cai) — khác skippedNames (= đã có sẵn).
      const failedNames = [];
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
        skippedNames.push(...(fixedResult.skippedNames || []));
        failedNames.push(...(fixedResult.failedNames || []));
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

      // ROUND-ROBIN: hỏng thì HOÃN lại rồi đi tiếp, hết lượt mới quay lại thử phần hoãn.
      // Thay cho vòng thử-lại-tại-chỗ cũ, vì (1) cổng vừa trả 500 thì thử ngay cũng 500,
      // (2) sleep(2000*attempt) tại chỗ là thời gian chết, (3) quan trọng nhất: `break` cũ làm
      // MỘT tệp hỏng chặn hết các tệp còn lại — lô 4 tệp gặp 500 xen kẽ thì chỉ vào được 2-3.
      // Khoảng cách giữa hai lần thử của cùng một tệp giờ = thời gian đính các tệp khác, giãn
      // hơn nhiều so với sleep cũ.
      // 3 lượt: File Service của cổng hay trả 500/đơ ở bước "Thêm vào ví" — 2 lượt quá ít cho lỗi
      // TẠM THỜI. Không thử lại TẠI CHỖ (cổng vừa 500 thì thử ngay cũng 500); round-robin giãn cách
      // bằng thời gian đính tệp khác + backoff tăng dần để server kịp hồi. Hỏng 1 tệp không chặn tệp khác.
      const MAX_ROUNDS = 3;
      const lastErrorByIndex = new Map();
      let queue = plannedAttachments.map((item, index) => ({ item: item || {}, index }));
      // Split tab: ví React treo thì click lại tại chỗ không chữa được — dừng cả lượt và trả
      // ngay cho state machine để nó áp giới hạn reload theo từng trạng thái.
      let splitAbort = false;

      for (let round = 1; round <= MAX_ROUNDS && queue.length && !splitAbort; round++) {
        const deferred = [];
        if (round > 1) {
          console.warn(`[AutoFill-AttachPlan] lượt ${round}: thử lại ${queue.length} tệp bị hoãn`);
          await closeDocumentWalletDialogs();
          // BACKOFF TĂNG DẦN: cổng 500/đơ cần thời gian hồi (thử lại ngay cũng 500). Tệp CUỐI/DUY NHẤT
          // chờ lâu hơn vì round-robin không có tệp khác chen vào tạo khoảng nghỉ. Lượt sau chờ lâu hơn.
          const backoffMs = (round - 1) * 3000 + (queue.length <= 1 ? 2500 : 0);
          await sleep(backoffMs);
        }
        for (const { item, index: i } of queue) {
          const payloadFile = payloadForPlanItem(payloadFiles, item, i);
          if (!payloadFile) {
            // Thiếu file trong payload là lỗi dữ liệu, thử lại vòng sau cũng vậy → báo luôn.
            errors.push(`Không tìm thấy file ${item.fileName || i + 1} trong payload.`);
            continue;
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
            let result;
            try {
              result = await attachOneFileToOtherListFile(payloadFile, item);
            } catch (e) {
              console.warn("[AutoFill-AttachPlan] Giấy tờ khác lỗi:", e);
              result = { error: `Không thêm được Giấy tờ khác "${item.documentName || payloadFile.name}".` };
            }
            if (result?.error && item.noChooserClick) {
              // Kế hoạch cho phép bỏ qua (Lào Cai): không thử lại, không chặn các tệp khác.
              console.warn("[AutoFill-AttachPlan] bỏ qua tệp Giấy tờ khác", result.error);
              failedNames.push(item.documentName || payloadFile.name);
              continue;
            }
            if (result?.error) {
              lastErrorByIndex.set(i, result.error);
              deferred.push({ item, index: i });
              continue;
            }
            lastErrorByIndex.delete(i);
            attachedNames.push(...(result.fileNames || []));
            await sleep(400);
            continue;
          }
          if ((item.target === "new" || item.needsAddComponent) && item.noChooserClick) {
            // Cổng iGate VNPT không có luồng "ví giấy tờ": rơi xuống đó chỉ bấm lung tung (mở hộp thoại file).
            console.warn("[AutoFill-AttachPlan] không có mục Giấy tờ khác → bỏ qua", item.documentName);
            failedNames.push(item.documentName || payloadFile.name);
            continue;
          }

          let row;
          try {
            row = await rowForPlanItem(item);
          } catch (e) {
            console.warn("[AutoFill-Attach] Tìm dòng hồ sơ lỗi:", e);
            lastErrorByIndex.set(i, `Không mở được dòng hồ sơ "${item.componentName || ""}".`);
            deferred.push({ item, index: i });
            continue;
          }
          if (!row) {
            lastErrorByIndex.set(i, `Không tìm thấy dòng hồ sơ "${item.componentName || ""}".`);
            deferred.push({ item, index: i });
            continue;
          }

          const result = await attachOneFileViaDocumentWallet(row, payloadFile, item);
          if (result?.error) {
            errorCode = errorCode || result.code || null;
            console.warn("[AutoFill-AttachPlan] attach item failed", {
              round,
              error: result.error,
              portalError: result.portalError || null,
              debug: result.debug,
              item,
              payloadFile: { name: payloadFile?.name, type: payloadFile?.type },
            });
            lastErrorByIndex.set(i, result.error);
            deferred.push({ item, index: i });
            if (splitMode && isSplitReloadableWalletError(result.code)) {
              splitAbort = true;
              break;
            }
            await closeDocumentWalletDialogs();
            continue;
          }
          lastErrorByIndex.delete(i);
          attachedNames.push(...(result.fileNames || []));
          await sleep(600);
        }
        queue = deferred;
      }

      // Hết lượt mà còn hoãn = hỏng thật. Báo TỪNG tệp để cán bộ biết phải đính tay ô nào,
      // thay vì một câu lỗi chung rồi im lặng bỏ qua phần còn lại như trước.
      for (const { index } of queue) {
        const message = lastErrorByIndex.get(index);
        if (message) errors.push(message);
      }

      // Lượt chốt: đánh số các dòng thành phần thêm mới trùng tên (vd bản dịch CTV nhiều dòng →
      // "… 2", "… 3"…). No-op với thủ tục không có ô tên editable hoặc tên đã khác nhau.
      try { await renumberDuplicateComponentNameInputs(); }
      catch (e) { console.warn("[AutoFill-Attach] đánh số tên thành phần lỗi:", e); }

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
      if (!attachedNames.length && failedNames.length) {
        return {
          error: "Không đính kèm được tệp nào vào bảng thành phần hồ sơ.",
          attached: 0,
          skipped: skippedNames.length,
          fileNames: [],
          skippedNames,
          failedNames,
        };
      }
      return {
        ok: true,
        method: "wallet-plan",
        failedNames,
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
      // Form.io selectboxes đặt CÙNG một name "data[key][]" cho mọi option (phân biệt bằng value/nhãn)
      // → thử cả hai dạng để BE gửi "data[key]" hay "data[key][]" đều khớp.
      if (dataKey) out.push(dataKey, `data[${dataKey}][]`);
      const arrayKey = name.match(/^data\[([^\]]+)\]\[\]$/)?.[1];
      if (arrayKey) out.push(arrayKey, `data[${arrayKey}]`);
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
        // Cổng iGate VNPT (Nth.FormBuilder, vd Lào Cai): khối người nộp prefill từ tài khoản định danh.
        readInputLikeValue("CongDan_tenCongDan") ||
        readBacNinhAccountValue("hoTen"),
      applicantIdentityNumber:
        readInputLikeValue("data[identityNumber]") ||
        readNgReflectValue("ng-reflect-identity-number") ||
        readInputLikeValue(["SoDinhDanhC", "SoGiayToDinhDanhC", "NYC_SoGiayToTuyThan"]) ||
        readInputLikeValue("CongDan_soCmnd") ||
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

  // getElementById chỉ có ở document; trong một khối con phải tra bằng querySelector.
  function standardById(root, id) {
    if (!id) return null;
    if (root === document) return document.getElementById(id);
    try {
      return root.querySelector(`#${CSS.escape(id)}`);
    } catch (e) {
      return null;
    }
  }

  function collectStandardInputs(names, root = document) {
    const candidates = standardNameVariants(names);
    const found = [];
    const add = (el) => {
      if (el && ["input", "textarea"].includes(el.tagName?.toLowerCase?.()) && !found.includes(el)) found.push(el);
    };
    for (const n of candidates) {
      const escaped = CSS.escape(n);
      root.querySelectorAll(`input[name="${escaped}"], textarea[name="${escaped}"]`).forEach(add);
    }
    for (const n of candidates) {
      const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
      add(standardById(root, "_fc" + base));
      add(standardById(root, base));
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    Array.from(root.querySelectorAll("input[name], textarea[name]")).forEach((node) => {
      if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
    });
    return found;
  }

  function findStandardInput(names, occurrence = null, root = document) {
    return pickStandardControl(collectStandardInputs(names, root), occurrence);
  }

  function findStandardInputForField(field, candidates, occurrence = null, root = document) {
    return findStandardInput(candidates, occurrence, root) || findStandardDatagridFallbackInput(field);
  }

  function collectStandardSelects(names, root = document) {
    const candidates = standardNameVariants(names);
    const found = [];
    const add = (el) => {
      if (el && el.tagName?.toLowerCase?.() === "select" && !found.includes(el)) found.push(el);
    };
    for (const n of candidates) {
      root.querySelectorAll(`select[name="${CSS.escape(n)}"]`).forEach(add);
    }
    for (const n of candidates) {
      const base = n.startsWith("CongDan_") ? n.slice("CongDan_".length) : n;
      add(standardById(root, "_fc" + base));
      add(standardById(root, base));
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    Array.from(root.querySelectorAll("select[name]")).forEach((node) => {
      if (wanted.has(String(node.getAttribute("name") || "").toLowerCase())) add(node);
    });
    return found;
  }

  function findStandardSelect(names, occurrence = null, root = document) {
    return pickStandardControl(collectStandardSelects(names, root), occurrence);
  }

  function findStandardSelects(names, occurrence = null, root = document) {
    const found = collectStandardSelects(names, root).filter(standardControlVisible);
    const explicitOccurrence = standardOccurrence(occurrence);
    if (explicitOccurrence !== null) {
      const selected = found[explicitOccurrence];
      return selected ? [selected] : [];
    }
    return found;
  }

  // Nhãn của MỘT option trong nhóm selectboxes: chữ trong <label> bọc chính ô đó (bỏ dấu câu cuối câu).
  function checkboxOptionLabel(el) {
    const label = el?.closest?.("label") || el?.parentElement;
    return foldChoiceText(nodeText(label)).replace(/[.,;:]+$/g, "").trim();
  }

  function findStandardCheckbox(names, optionValue = null, optionLabel = null, root = document) {
    const candidates = standardNameVariants(names);
    const wantedOption = optionValue == null ? "" : String(optionValue);
    // Nhóm selectboxes (vd 12 phạm vi hành nghề thú y) dùng CHUNG name "data[deNghi][]", chỉ khác value
    // (a, b, c…) và nhãn. Key value do Form.io sinh nên BE không đoán được → khớp theo NHÃN mới chắc.
    const wantedLabel = optionLabel == null
      ? ""
      : foldChoiceText(optionLabel).replace(/[.,;:]+$/g, "").trim();
    const matchesOption = (node) => {
      if (wantedOption && String(node.value) === wantedOption) return true;
      if (!wantedLabel) return !wantedOption;
      return checkboxOptionLabel(node) === wantedLabel;
    };
    for (const n of candidates) {
      const selector = `input[type="checkbox"][name="${CSS.escape(n)}"]`;
      const nodes = Array.from(root.querySelectorAll(selector));
      const el = (wantedOption || wantedLabel) ? nodes.find(matchesOption) : nodes[0];
      if (el) return el;
    }
    const wanted = new Set(candidates.map((n) => String(n).toLowerCase()));
    return Array.from(root.querySelectorAll('input[type="checkbox"][name]')).find((node) =>
      wanted.has(String(node.getAttribute("name") || "").toLowerCase()) && matchesOption(node)
    ) || null;
  }

  function findStandardRadio(names, root = document) {
    const candidates = standardNameVariants(names);
    for (const n of candidates) {
      const el = root.querySelector(`input[type="radio"][name="${CSS.escape(n)}"]`);
      if (el) return el;
    }
    return Array.from(root.querySelectorAll('input[type="radio"][name]')).find((node) =>
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

  // Chọn ngày trên LỊCH flatpickr như người dùng: mở lịch → gõ năm → chọn tháng → bấm ô ngày. Instance
  // `el._flatpickr` do script TRANG gắn nên content script (isolated world) KHÔNG đọc được, còn inline script
  // bị CSP cổng chặn; nhưng sự kiện DOM thì tới được listener của flatpickr → flatpickr tự setDate (điền đủ
  // ô ẩn + ô hiển thị theo format riêng của form, bắn onChange cho Form.io). Mọi bước flatpickr xử lý đồng bộ.
  // Trả false khi không mở được lịch / lịch không có dropdown tháng / ngày bị khoá → để fallback gõ chữ.
  function pickFlatpickrCalendarDate(el, dateObj) {
    if (!el || !dateObj) return false;
    const container = el.closest?.(".formio-component-datetime") || el.closest?.(".formio-component") || standardMarkTarget(el);
    const inputs = container ? Array.from(container.querySelectorAll("input")) : [el];
    const visible = inputs.find((n) => n.type !== "hidden" && n.classList.contains("input")) ||
      inputs.find((n) => n.type !== "hidden") || el;
    if (visible.disabled) return false;

    const openBefore = new Set(document.querySelectorAll(".flatpickr-calendar.open"));
    visible.dispatchEvent(new FocusEvent("focus"));
    visible.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    // CHỈ nhận lịch của CHÍNH ô này: lịch nằm trong component, hoặc lịch VỪA mở sau cú bấm. Lấy bừa
    // ".flatpickr-calendar.open" đầu trang là bấm ngày vào lịch của ô KHÁC → ghi sai ngày sang ô đó.
    const calendar = container?.querySelector(".flatpickr-calendar.open") ||
      Array.from(document.querySelectorAll(".flatpickr-calendar.open")).find((c) => !openBefore.has(c));
    if (!calendar) return false;

    const close = () => document.body?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    const year = calendar.querySelector(".cur-year");
    const month = calendar.querySelector("select.flatpickr-monthDropdown-months");
    if (!year || !month) {
      close();
      return false;
    }
    setNativeValue(year, String(dateObj.getFullYear()), { change: false });
    year.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: "Enter" }));
    month.value = String(dateObj.getMonth());
    month.dispatchEvent(new Event("change", { bubbles: true }));

    const day = Array.from(calendar.querySelectorAll(".dayContainer .flatpickr-day")).find((node) =>
      !node.classList.contains("prevMonthDay") &&
      !node.classList.contains("nextMonthDay") &&
      node.textContent.trim() === String(dateObj.getDate())
    );
    if (!day || day.classList.contains("flatpickr-disabled")) {
      close();
      return false;
    }
    day.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    if (calendar.classList.contains("open")) close();
    // flatpickr ghi ngày vào ô ẩn gốc theo dateFormat của form (d/m/Y, ISO...) → chỉ cần thấy đúng năm.
    return String(el.value || visible.value || "").includes(String(dateObj.getFullYear()));
  }

  function fillStandardDate(el, value, opts = {}) {
    if (!el) return false;
    const text = String(value ?? "").trim();
    if (!text) return false;
    const group = standardMarkTarget(el);

    // Form.io datetime dùng flatpickr: set .value trực tiếp vào ô bị flatpickr GHI ĐÈ lại rỗng (→ báo
    // "bắt buộc"). Chọn trên lịch để chính flatpickr setDate — không phụ thuộc d/m/Y hay ISO của form.
    const dateObj = parseDmyDate(text);
    if (dateObj && el.classList?.contains("flatpickr-input") && pickFlatpickrCalendarDate(el, dateObj)) {
      markFilled(group);
      return true;
    }

    // Không chọn được trên lịch → fallback GÕ giá trị. Định dạng theo LOẠI ô (BE báo qua opts.iso):
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

  async function fillStandardSelectAny(el, value, names = [], occurrence = null, deadline = 0, root = document) {
    const isAreaSelect = names.some(isAreaSelectName) || isAreaSelectName(el?.name);
    if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
    if (!el && names.length) {
      el = await waitForStandardSelect(
        () => findStandardSelect(names, occurrence, root),
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
      const current = el || (names.length ? findStandardSelect(names, occurrence, root) : null);
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

  async function fillStandardSelectAll(names, value, occurrence = null, deadline = 0, root = document) {
    const isAreaSelect = names.some(isAreaSelectName);
    if (isAreaSelect && !deadline) deadline = Date.now() + STANDARD_AREA_FIELD_BUDGET_MS;
    let filledAny = false;
    for (const delay of [0, 250, 600, 1200]) {
      if (standardSelectBudgetLeft(deadline) <= 0) break;
      if (delay && !await sleepForStandardSelect(delay, deadline)) break;
      const selects = findStandardSelects(names, occurrence, root);
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
        if (await fillStandardSelectAny(sel, value, names, occurrence, deadline, root)) filledAny = true;
        await sleepForStandardSelect(120, deadline);
      }

      const latest = findStandardSelects(names, occurrence, root);
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

  // Chữ đi liền SAU một ô radio, dừng ở ô radio kế tiếp — đúng thứ mắt người đọc là nhãn của ô đó.
  // Cần vì hai kiểu markup mà `parentElement.textContent` xử lý sai, đều gặp trên cổng ĐKKD
  // (dangkyquamang.dkkd.gov.vn, trang TaxInformation.aspx, nhóm "Phương pháp tính thuế"):
  //   1. input và chữ nằm ở HAI ô <td> khác nhau -> thẻ cha của input KHÔNG có chữ nào, nhãn đọc ra
  //      rỗng, mà nhãn rỗng thì radioValueMatches cố tình KHÔNG khớp -> không ô nào được tick;
  //   2. CẢ BỐN ô nằm chung MỘT thẻ cha -> mọi ô đều trả về đúng một chuỗi gộp cả bốn nhãn, nên ô
  //      nào cũng "khớp" và bộ điền tick nhầm ô đầu danh sách.
  // Leo lên cấp cha chỉ khi chưa nhặt được chữ nào, và chặn ở TR/TABLE/FORM/BODY để không vơ sang
  // nhãn của nhóm radio khác trên cùng trang.
  function radioTrailingText(radio) {
    // Chỉ leo TỐI ĐA một cấp: đủ cho kiểu hai ô <td>, mà không đi lạc sang nhãn của nhóm khác khi
    // một ô radio thật sự không có chữ nào đi kèm.
    let node = radio;
    for (let hop = 0; hop < 2 && node; hop++) {
      const parts = [];
      for (let sib = node.nextSibling; sib; sib = sib.nextSibling) {
        if (sib.nodeType === 3) {
          parts.push(sib.nodeValue || "");
          continue;
        }
        if (sib.nodeType !== 1) continue;
        if (sib.matches?.('input[type="radio"]') || sib.querySelector?.('input[type="radio"]')) break;
        parts.push(sib.textContent || "");
      }
      const text = parts.join(" ").trim();
      if (text) return text;
      node = node.parentElement;
      if (!node || ["TR", "TABLE", "FORM", "BODY"].includes(node.tagName)) return "";
    }
    return "";
  }

  function radioLabelText(radio) {
    if (!radio) return "";
    const explicit = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
    const wrapping = radio.closest("label");
    return String(
      explicit?.textContent ||
      wrapping?.textContent ||
      radioTrailingText(radio) ||
      radio.parentElement?.textContent ||
      ""
    ).trim();
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
    // Nhãn RỖNG (radio không có <label for> và thẻ cha chỉ chứa mỗi input) thì KHÔNG được coi là
    // khớp: "".includes bất kỳ chuỗi nào cũng đúng, nên một ô nhãn rỗng sẽ nuốt MỌI giá trị và ô
    // đó bị tick bất kể người ta muốn chọn gì.
    return wants.has(radioValue) ||
      (!!label && Array.from(wants).some(
        (want) => !!want && (label === want || label.includes(want) || want.includes(label))));
  }

  async function fillStandardRadio(el, value) {
    if (!el) return false;
    const name = el.getAttribute("name");
    const findGroup = () => name
      ? Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
      : [el].filter(Boolean);
    const findTarget = () => {
      const group = findGroup();
      const matched = group.find((radio) => radioValueMatches(radio, value));
      if (matched) return matched;
      // Nhóm chỉ có MỘT ô thì không có gì để chọn nhầm — vẫn tick như cũ.
      if (group.length === 1) return group[0];
      return null;
    };
    let target = findTarget();
    if (!target) {
      // TUYỆT ĐỐI không tick đại ô đầu tiên. Đây là hồ sơ pháp lý: bỏ trống rồi báo "không điền
      // được" thì cán bộ còn nhìn thấy mà sửa, chứ tick sai một ô là hồ sơ nộp đi mang câu trả lời
      // mà không ai kê khai. Lỗi thật đã gặp: đơn ghi "Khấu trừ", cổng lại nhận "Không phải nộp
      // thuế GTGT". In luôn các ô đang có để lần sau biết cổng đặt tên/nhãn thế nào.
      const group = findGroup();
      console.warn(`[AutoFill-STD] radio không khớp giá trị ${JSON.stringify(value)} — KHÔNG tick ô nào.`,
        group.map((radio) => ({ value: radio.value, nhan: radioLabelText(radio) })));
      return false;
    }

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

  // Panel Form.io "collapsible" (vd khối "Địa chỉ thửa đất/ địa chỉ xây dựng" của cổng Quảng Ngãi) mặc
  // định ĐÓNG: header có aria-expanded="false" và phần thân chưa mở nên các ô bên trong không điền
  // được (BE trả field nhưng FE báo notFound). Bấm header để mở TRƯỚC khi điền. Chỉ nhắm panel của
  // Form.io (.formio-component-panel) nên không đụng accordion khác của trang.
  async function expandCollapsedFormioPanels() {
    const headers = Array.from(
      document.querySelectorAll('.formio-component-panel [aria-expanded="false"][role="button"]')
    ).filter((el) => el.querySelector?.(".formio-collapse-icon") || el.classList?.contains("card-header"));
    let opened = 0;
    for (const header of headers) {
      try {
        header.click();
        opened += 1;
      } catch { /* panel lỗi không được chặn cả lượt điền */ }
    }
    // Form.io render thân panel sau một nhịp; chờ ngắn để querySelector thấy ô bên trong.
    if (opened) await sleep(300);
    return opened;
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

  // "scope" = CSS selector của KHỐI chứa ô, giới hạn vùng dò DOM cho đúng MỘT ô.
  //
  // Cổng DVCQG dựng nhiều khối trên CÙNG một trang bằng các form Form.io riêng nên field-key lặp lại:
  // data[fullname] vừa là "Họ và tên người nộp hồ sơ" (cổng tự đổ tài khoản VNeID đang đăng nhập), vừa
  // là "Họ và tên" trong mục Thông tin chung của tờ đơn — hai ô đó là HAI NGƯỜI khác nhau khi nộp thay.
  // Không giới hạn vùng dò thì querySelector luôn trúng ô ĐẦU TIÊN theo thứ tự tài liệu, tức khối người
  // nộp, và ta ghép họ tên người này với giấy tờ tùy thân người kia — nhìn vào vẫn thấy "đủ dữ liệu"
  // nên không ai soát ra.
  //
  // "scopeAway" = tên ô CHỈ có ở KHỐI CẤM (vd ô tích "Người nộp hồ sơ là chủ hồ sơ" chỉ có ở khối
  // người nộp). Selector scope có thể trỏ vào panel BỌC cả khối cấm (Form.io đặt tên panel theo key
  // nên panel tờ đơn có thể là panel gốc của cả trang) — lúc đó querySelector vẫn trúng ô ĐẦU TIÊN,
  // tức ô của khối cấm. Khai scopeAway để phát hiện vùng dò còn quá rộng và thu hẹp lại.
  //
  // "scopeNear" = tên một ô CÙNG KHỐI với ô đang điền nhưng KHÔNG trùng tên với khối cấm (vd
  // data[bangCapChuyenMon] chỉ có trong tờ đơn). Dùng làm neo để leo ngược lên đúng khối.
  //
  // Trả về: document (không khai scope) | Element (khối cần dò) | null (không tách được → BỎ ô).
  function standardScopeRoot(field) {
    const selector = String(field?.scope || "").trim();
    const away = standardScopeAwayNames(field);
    let root = document;
    if (selector) {
      try {
        root = document.querySelector(selector);
      } catch (e) {
        // Selector hỏng (hoặc trình duyệt quá cũ không hiểu :has) → KHÔNG được rơi về cả trang: ô khai
        // scope là ô có field-key trùng với khối cấm, dò cả trang là ghi đè thẳng lên khối đó.
        console.warn(`[AutoFill-STD] scope không hợp lệ "${selector}" → bỏ ô ${field?.name}:`, e);
        return null;
      }
    }
    if (!away.length) return root;
    // Vùng dò không chứa khối cấm (hoặc trang này không render khối cấm) → đã đủ hẹp.
    if (root && !standardScopeHasControl(root, away)) return root;
    const narrowed = standardAnchoredScopeRoot(field?.scopeNear, away);
    if (narrowed) return narrowed;
    // Thà bỏ trống cho cán bộ điền tay còn hơn ghi đè nhân thân người khác vào khối cấm.
    console.warn(
      `[AutoFill-STD] ${field?.name}: không tách được vùng dò khỏi khối "${away.join(", ")}" → bỏ ô.`,
    );
    return null;
  }

  function standardScopeAwayNames(field) {
    const raw = field?.scopeAway;
    return (Array.isArray(raw) ? raw : [raw]).map((name) => String(name ?? "").trim()).filter(Boolean);
  }

  function standardScopeHasControl(root, names) {
    if (!root) return false;
    // PHẢI dò theo cùng bộ biến thể tên mà vòng điền dùng (standardNameVariants). Khối người nộp hồ sơ
    // do Angular dựng nên ô mang name TRẦN "ownerFullname", còn BE gửi khoá Form.io "data[ownerFullname]";
    // so khớp nguyên văn thì không thấy mốc nào, vùng dò tưởng đã đủ hẹp và ô của tờ đơn rơi thẳng vào
    // khối người nộp.
    return standardNameVariants(names).some((name) => {
      try {
        return !!root.querySelector(`[name="${CSS.escape(name)}"]`);
      } catch (e) {
        return false;
      }
    });
  }

  // Khối cần dò = tổ tiên CAO NHẤT của ô neo mà vẫn CHƯA chứa khối cấm.
  function standardAnchoredScopeRoot(near, away) {
    const anchorName = String(near ?? "").trim();
    if (!anchorName || !away.length) return null;
    let anchor = null;
    try {
      anchor = document.querySelector(`[name="${CSS.escape(anchorName)}"]`);
    } catch (e) {
      anchor = null;
    }
    let node = anchor?.parentElement || null;
    let root = null;
    while (node && node !== document.body && node !== document.documentElement) {
      if (standardScopeHasControl(node, away)) break;
      root = node;
      node = node.parentElement;
    }
    return root;
  }

  // ---- KHỐI NHÂN THÂN CẤM GHI (vd "Thông tin người nộp hồ sơ" = tài khoản VNeID đang đăng nhập) ----
  //
  // BE không phát ô nào của khối này nên MỌI giá trị của ta xuất hiện ở đó đều là ghi đè ngoài ý muốn.
  // Nguyên nhân có thể là vùng dò trượt sang khối cấm, vòng điền lại, HOẶC chính cổng tự sao chép sang
  // sau khi ta điền khối khác — scope chỉ chặn được nguyên nhân đầu. Cách chặn không phụ thuộc nguyên
  // nhân: chụp giá trị khối cấm TRƯỚC khi điền, xong xuôi ô nào đổi thành ĐÚNG dữ liệu ta vừa ghi thì
  // trả lại giá trị cũ. Giá trị lạ (do cổng tự đổi) không đụng tới.
  //
  // Nhận diện khối cấm từ chính payload, không hardcode thủ tục: mốc scopeAway nào KHÔNG phải ô dữ liệu
  // ta sẽ điền thì chỉ có ở khối cấm. Leo ngược từ mốc đó, dừng ngay trước khi vùng dò chạm ô dữ liệu
  // của khối ĐƯỢC PHÉP điền (ô không khai scope — vd data[ownerFullname] của khối chủ hồ sơ).
  const STANDARD_DATA_COMPS = new Set(["dom-input", "dom-date", "dom-datetime", "dom-select", "raw"]);

  function standardUnscopedDataNames(fields) {
    const names = new Set();
    for (const f of fields || []) {
      // Ô khai scope dùng chung field-key với khối cấm (data[fullname] của tờ đơn) → không phải mốc.
      // Checkbox/radio không phải ô dữ liệu nhân thân: ô tích "Người nộp hồ sơ là chủ hồ sơ" nằm NGAY
      // trong khối cấm và ta có chạm để mở khoá khối sau, lấy nó làm mốc dừng thì khối cấm hụt mất.
      if (f?.scope || f?.scopeNear || !STANDARD_DATA_COMPS.has(f?.comp)) continue;
      for (const n of fieldCandidates(f)) names.add(String(n));
    }
    return names;
  }

  function standardForbiddenRoots(fields) {
    const allowed = standardUnscopedDataNames(fields);
    const guards = new Set();
    for (const f of fields || []) {
      for (const name of standardScopeAwayNames(f)) {
        if (!allowed.has(name)) guards.add(name);
      }
    }
    const stop = Array.from(allowed);
    const roots = [];
    for (const guard of guards) {
      let marker = null;
      try {
        marker = document.querySelector(`[name="${CSS.escape(guard)}"]`);
      } catch (e) {
        marker = null;
      }
      if (!marker) continue;
      let node = marker.parentElement;
      let root = null;
      while (node && node !== document.body && node !== document.documentElement) {
        if (stop.length && standardScopeHasControl(node, stop)) break;
        root = node;
        node = node.parentElement;
      }
      if (root && !roots.includes(root)) roots.push(root);
    }
    return roots;
  }

  function standardInsideForbidden(roots, node) {
    if (!node || node === document) return false;
    return (roots || []).some((root) => root === node || (root.contains && root.contains(node)));
  }

  function standardControlText(el) {
    if (!el) return "";
    if (String(el.tagName || "").toLowerCase() === "select") {
      const option = el.options ? el.options[el.selectedIndex] : null;
      return String((option && option.text) ?? el.value ?? "");
    }
    return String(el.value ?? "");
  }

  function snapshotStandardControls(roots) {
    const snapshot = [];
    for (const root of roots || []) {
      const controls = root.querySelectorAll ? root.querySelectorAll("input, textarea, select") : [];
      Array.from(controls).forEach((el) => {
        snapshot.push({ el, value: el.value, text: standardControlText(el) });
      });
    }
    return snapshot;
  }

  // Khoá so khớp "giá trị này là của ta": bỏ dấu, bỏ khoảng trắng để "Tỉnh Lai Châu" (ta gửi) khớp
  // được nhãn option "Tỉnh Lai Châu" đang hiển thị trên ô select của khối cấm.
  function standardValueKey(value) {
    return foldChoiceText(String(value ?? "")).replace(/\s+/g, "");
  }

  function standardWrittenValueKeys(fields) {
    const keys = new Set();
    const add = (value) => {
      if (value === true || value === false || value === null || value === undefined) return;
      const key = standardValueKey(value);
      if (key.length >= 2) keys.add(key);
    };
    for (const f of fields || []) {
      const value = f?.value;
      if (value && typeof value === "object") Object.values(value).forEach(add);
      else add(value);
    }
    return keys;
  }

  function restoreStandardForbidden(snapshot, writtenKeys) {
    const reverted = [];
    for (const item of snapshot || []) {
      const el = item?.el;
      if (!el || el.isConnected === false) continue;
      const now = standardControlText(el);
      if (now === item.text) continue;
      if (!writtenKeys.has(standardValueKey(now))) continue;
      try {
        el.value = item.value;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      } catch (e) {
        continue;
      }
      const target = standardMarkTarget(el);
      if (target && target.classList) target.classList.remove("autofill-filled");
      reverted.push(el.name || el.id || "(?)");
    }
    return reverted;
  }

  // Vùng dò của ô khai scope, CÓ CHỜ khối render. Xem chú thích ở vòng điền: khối tờ đơn do Form.io
  // dựng trễ hơn khối Angular đầu trang, không chờ thì ô của tờ đơn bị bỏ trắng oan.
  async function standardScopeRootWaiting(field) {
    const root = standardScopeRoot(field);
    if (root || !field?.scope) return root;
    return await waitFor(() => standardScopeRoot(field), 3000, 100);
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

  // Báo cáo lần điền gần nhất, GHI RA DOM (thuộc tính trên <html>) chứ không phải biến JS: content
  // script chạy ở "isolated world" nên script dán vào Console của trang KHÔNG đọc được biến của nó,
  // còn DOM thì dùng chung. Nhờ vậy docs/crawl-eform.js đọc được extension đã quyết định gì cho từng ô:
  // vùng dò ra khối nào, ô nào bị bỏ, và bản extension nào đang chạy.
  function publishStandardFillReport(result, scopeLog) {
    try {
      const report = {
        version: APP_VERSION_LABEL,
        at: new Date().toISOString(),
        filled: result.filled,
        notFound: result.notFound,
        errors: result.errors,
        scope: scopeLog,
      };
      document.documentElement.setAttribute("data-autofill-report", JSON.stringify(report));
    } catch (e) {
      console.warn("[AutoFill-STD] Không ghi được báo cáo ra DOM:", e);
    }
  }

  async function fillFormStandard(fields) {
    injectAutofillStyles();
    clearAutofillMarks();
    await expandCollapsedFormioPanels();
    await ensureStandardDatagridRows(fields);
    // Chụp khối nhân thân cấm ghi TRƯỚC khi điền ô nào (xem standardForbiddenRoots).
    const forbiddenRoots = standardForbiddenRoots(fields);
    const forbiddenSnapshot = snapshotStandardControls(forbiddenRoots);
    const result = { filled: 0, notFound: [], errors: [] };
    const areaDeadlines = new Map();
    const failedFieldKeys = new Set();
    const scopeLog = [];
    const orderedFields = orderStandardFields(fields);

    for (const f of orderedFields) {
      // Ô khai scope mà trang không có khối đó → bỏ qua, không tính notFound (xem standardScopeRoot).
      //
      // ⚠ Khối khai trong scope render TRỄ: Form.io dựng panel tờ đơn SAU khi khối Angular ở đầu trang
      // đã hiện. Trước đây vùng dò không thấy khối là bỏ ô NGAY, trong khi ô không khai scope lại có
      // vòng chờ riêng (waitFor 1s) nên vẫn điền được — kết quả: giữa cùng một panel, ô "Bằng cấp
      // chuyên môn" và "Kính gửi" có chữ còn Họ tên/Ngày sinh/Nơi cư trú của tờ đơn bị bỏ trắng. Phải
      // chờ khối xuất hiện rồi mới quyết định bỏ ô.
      let root = await standardScopeRootWaiting(f);
      // Chốt chặn cuối, không phụ thuộc vì sao vùng dò trượt: ô khai scope mà vùng dò lại nằm trong
      // khối cấm ghi (vd "Thông tin người nộp hồ sơ") thì BỎ ô. Thà để trống cho cán bộ gõ tay còn hơn
      // ghép nhân thân người trong hồ sơ vào giấy tờ tùy thân của tài khoản đang đăng nhập.
      const hitForbidden = !!(f.scope && standardInsideForbidden(forbiddenRoots, root));
      if (hitForbidden) {
        console.warn(`[AutoFill-STD] ${f.name}: vùng dò rơi vào khối cấm ghi → bỏ ô.`);
        root = null;
      }
      scopeLog.push({
        name: f.name,
        scope: f.scope || "",
        root: hitForbidden ? "khoi-cam" : root === document ? "ca-trang" : root ? "dung-khoi" : "bo-o",
      });
      if (f.scope || f.scopeAway) {
        console.log(
          `[AutoFill-STD] scope ${f.name} → "${f.scope || "(theo ô neo)"}": ${root === document ? "dò cả trang" : root ? "thấy khối" : "KHÔNG tách được khối, bỏ qua ô"}`,
        );
      }
      if (!root) continue;
      const candidates = fieldCandidates(f);
      const occurrence = standardOccurrence(f.occurrence);
      // comp "dom-expect": ô extension CHỊU TRÁCH NHIỆM điền nhưng BE không có dữ liệu → KHÔNG điền, chỉ
      // TÔ ĐỎ nếu ô đang trống (để user biết cần điền tay), kể cả khi form không đánh dấu ô đó bắt buộc.
      // Không tính vào filled/notFound.
      if (f.comp === "dom-expect") {
        const el = findStandardInputForField(f, candidates, occurrence, root) || findStandardSelect(candidates, occurrence, root);
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
          const el = findStandardCheckbox(candidates, f.optionValue, f.optionLabel, root);
          ok = await fillStandardCheckbox(el, f.value);
        } else if (f.comp === "dom-radio") {
          // Radio có thể render ĐỘNG sau khi chọn radio cha (vd bảng dạng khuyết tật: chọn nhóm "Có" thì
          // Angular mới bật các radio con) → chờ như dom-input/date, tránh bỏ sót mục con render trễ.
          const el = findStandardRadio(candidates, root) || await waitFor(() => findStandardRadio(candidates, root), 1500, 80);
          ok = await fillStandardRadio(el, f.value);
        } else if (f.comp === "dom-select") {
          if (isAreaSelectField(f)) {
            const deadline = standardFieldDeadline(areaDeadlines, f);
            ok = await fillStandardSelectAll(candidates, f.value, occurrence, deadline, root);
          } else {
            const el = findStandardSelect(candidates, occurrence, root);
            ok = await fillStandardSelectAny(el, f.value, candidates, occurrence, 0, root);
          }
        } else if (f.comp === "dom-date" || f.comp === "dom-datetime") {
          const el = findStandardInputForField(f, candidates, occurrence, root) || await waitFor(() => findStandardInputForField(f, candidates, occurrence, root), 1000, 80);
          // Ô flatpickr trong panel render ĐỘNG: lịch (.flatpickr-calendar) dựng TRỄ sau input → chờ lịch có
          // trong DOM rồi mới chọn ngày trên lịch (xem pickFlatpickrCalendarDate).
          if (el && el.classList?.contains("flatpickr-input")) {
            const hasCalendar = () => !!document.querySelector(".flatpickr-calendar");
            if (!hasCalendar()) await waitFor(hasCalendar, 1500, 80);
          }
          // dom-datetime: ô lưu ISO có giờ (vd tuNgay/denNgay) → fallback set ISO 00:00:00; dom-date: ô
          // dd/MM/yyyy (vd birthday) → fallback gõ dd/mm/yyyy. Chọn trên lịch đúng cho cả hai.
          ok = fillStandardDate(el, f.value, { iso: f.comp === "dom-datetime" });
        } else if (f.comp === "dom-input" || f.comp === "raw") {
          const el = findStandardInputForField(f, candidates, occurrence, root) || await waitFor(() => findStandardInputForField(f, candidates, occurrence, root), 1000, 80);
          const postbackAddressInput = isPostbackAddressField(f);
          ok = fillStandardInput(el, f.value, postbackAddressInput ? { change: false, commit: false } : {});
        } else {
          const input = findStandardInputForField(f, candidates, occurrence, root);
          if (input) ok = fillStandardInput(input, f.value);
          else ok = await fillStandardSelectAny(findStandardSelect(candidates, occurrence, root), f.value, candidates, occurrence, 0, root);
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
    // Trả lại khối cấm ghi trước khi tô đỏ, để ô vừa hoàn nguyên được đánh dấu đúng là đang trống.
    const reverted = restoreStandardForbidden(forbiddenSnapshot, standardWrittenValueKeys(fields));
    if (reverted.length) {
      console.warn(`[AutoFill-STD] Hoàn nguyên khối không được ghi đè: ${reverted.join(", ")}`);
    }
    markAllStandardEmptyFieldsRed();
    scheduleBusinessLineCodeSubmit(fields, result);
    publishStandardFillReport(result, scopeLog);
    console.log("[AutoFill-STD] Kết quả:", result);
    return result;
  }

  // Trạng thái option của 1 field địa bàn theo đúng occurrence; chỉ "settled" khi từng select cụ thể
  // đã có nguồn option quyết định. Field thất bại vẫn giữ notFound nhưng không ảnh hưởng deadline field khác.
  function areaSelectOptionState(f, root = document) {
    const candidates = fieldCandidates(f);
    const selects = findStandardSelects(candidates, standardOccurrence(f.occurrence), root);
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
      // Vòng retry cũng phải tôn trọng scope: không thì select Tỉnh/Phường của tờ đơn sẽ rơi vào ô
      // Tỉnh/Phường ĐẦU TIÊN trên trang, tức khối người nộp hồ sơ (nhân thân tài khoản VNeID).
      const root = standardScopeRoot(f);
      if (!root) continue;
      const deadline = standardFieldDeadline(deadlines, f);
      if (standardSelectBudgetLeft(deadline) <= 0) continue;
      const state = areaSelectOptionState(f, root);
      if (state.settled && !state.hasValue) continue;
      try {
        const ok = await fillStandardSelectAll(
          fieldCandidates(f),
          f.value,
          standardOccurrence(f.occurrence),
          deadline,
          root
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

  // Cổng ASP.NET (dkkd.gov.vn: hộ kinh doanh, đăng ký doanh nghiệp qua mạng) để select địa bàn ở
  // AutoPostBack: mỗi lần đổi Tỉnh/Phường-Xã là một AJAX partial postback dựng LẠI node select và
  // xoá các ô đã điền bằng script. NGAY sau khi ta chọn, ô vẫn đang đúng giá trị nhưng postback
  // CHƯA về — kết luận "đã ổn định" ở khoảnh khắc đó là lượt sau bấm Lưu giữa lúc postback đang
  // chạy, cổng dựng lại khối và hồ sơ đi với Phường/Xã rỗng (đúng lỗi "điền nhanh nên hụt xã").
  // Form Form.io (moha/moet/Lai Châu) không có __VIEWSTATE và không postback → giữ nguyên đường
  // thoát nhanh như cũ, không ngủ thêm giây nào.
  function isAspNetPostbackForm() {
    return !!document.querySelector('input[name="__VIEWSTATE"], #__VIEWSTATE');
  }

  function standardAreaFingerprint(fields) {
    return fields.map((f) => {
      const root = standardScopeRoot(f);
      if (!root) return "-";
      return findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence), root)
        .map((sel) => `${sel.options?.length || 0}/${sel.value || ""}`)
        .join("|");
    }).join(";");
  }

  // Chờ khối địa bàn đứng yên: danh sách option + giá trị không đổi qua hai nhịp liền, VÀ không
  // thoát trước STANDARD_AREA_POSTBACK_MIN_MS. Chờ tối thiểu là bắt buộc: lúc postback đang bay
  // thì DOM chưa đổi gì cả, "đứng yên" ở nhịp đầu không phân biệt được với "đã xong".
  const STANDARD_AREA_POSTBACK_MIN_MS = 1500;
  const STANDARD_AREA_POSTBACK_MAX_MS = 6000;

  async function waitStandardAreaQuiet(fields) {
    const minUntil = Date.now() + STANDARD_AREA_POSTBACK_MIN_MS;
    const maxUntil = Date.now() + STANDARD_AREA_POSTBACK_MAX_MS;
    let last = standardAreaFingerprint(fields);
    while (Date.now() < maxUntil) {
      await sleep(250);
      const now = standardAreaFingerprint(fields);
      const quiet = now === last;
      last = now;
      if (quiet && Date.now() >= minUntil) return true;
    }
    return false;
  }

  async function stabilizeStandardAreaSelects(fields, result, failedFieldKeys) {
    const targets = fields.filter((f) =>
      isAreaSelectField(f) && !failedFieldKeys.has(standardFieldIdentity(f))
    );
    if (!targets.length) return;
    const deadlines = new Map();

    const isStable = (f) => {
      const root = standardScopeRoot(f);
      if (!root) return true; // Ô bị scope loại khỏi trang này → không có gì để ổn định.
      const selects = findStandardSelects(fieldCandidates(f), standardOccurrence(f.occurrence), root);
      return selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
    };

    // Cổng ASP.NET: chờ postback cuối cùng của cascade về TRƯỚC khi kết luận gì (xem
    // waitStandardAreaQuiet) — không thì vòng dưới thấy ô còn đúng giá trị ta vừa set và thoát
    // ngay, trong khi postback đang bay và sẽ xoá mất Phường/Xã.
    if (isAspNetPostbackForm()) await waitStandardAreaQuiet(targets);

    for (const delay of [800, 1600]) {
      // Kiểm TRƯỚC: nếu mọi ô địa chỉ đã đúng thì thoát ngay, không ngủ (form moha không postback
      // xoá field nên vòng ổn định là thừa). Chỉ ngủ+sửa khi còn ô lệch (form postback HkdOnline).
      if (targets.every(isStable)) return;
      await sleep(delay);
      for (const f of targets) {
        const root = standardScopeRoot(f);
        if (!root) continue;
        const candidates = fieldCandidates(f);
        const occurrence = standardOccurrence(f.occurrence);
        const selects = findStandardSelects(candidates, occurrence, root);
        const matches = selects.length && selects.every((sel) => currentStandardSelectMatches(sel, f.value));
        if (matches) continue;
        try {
          const deadline = standardFieldDeadline(deadlines, f, STANDARD_AREA_STABILIZE_BUDGET_MS);
          await fillStandardSelectAll(candidates, f.value, occurrence, deadline, root);
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
        const root = standardScopeRoot(f);
        if (!root) continue;
        const candidates = fieldCandidates(f);
        const el = findStandardInputForField(f, candidates, standardOccurrence(f.occurrence), root);
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
