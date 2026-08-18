// content.js — KHUNG SIDEBAR "Trợ lý người dân" (push-layout, KHÔNG che nội dung trang).
// Làm theo spec ../01-sidebar-panel-push-layout.md (§3.1–3.7), đổi prefix tro-ly-nguoi-dan/__tlnd.
//
// Vai trò file này: dựng/thu/đóng sidebar + launcher + persist; ĐIỀU PHỐI message.
// Việc ĐIỀN FORM nằm ở content/fill-core.js + các engine fill-* (nạp TRƯỚC file này).
(() => {
  if (window.__TLND_CONTENT__) return; // guard chống inject trùng
  window.__TLND_CONTENT__ = true;

  const PANEL_ID = "tro-ly-nguoi-dan-panel";
  const BUBBLE_ID = "tro-ly-nguoi-dan-bubble";
  const IFRAME_ID = "tro-ly-nguoi-dan-iframe";
  const TW_OVERRIDE_ID = "tro-ly-nguoi-dan-tw-translate-override";
  const SIDEBAR_WIDTH = 400;               // px, = width panel = marginRight trang (cố định)
  const SS_OPEN_KEY = "__tlnd_panel_open"; // sessionStorage (cùng origin), chống giật khi reload
  const SS_DISMISS_KEY = "__tlnd_dismissed"; // bấm ✕ "tắt hẳn": ẩn cả bong bóng trong phiên origin này
  const LS_DISMISS_KEY = "tlnd_dismissed"; // chrome.storage.local: bấm ✕ ở 1 tab ⇒ ẩn trợ lý MỌI tab
  const IS_TOP_FRAME = window === window.top;

  let _origHtmlMarginRight = "";
  let _origHtmlTransition = "";
  let _origHtmlOverflowX = "";
  let _selfClosing = false; // tab này đang tự đóng (✕) → bỏ qua onChanged để giữ animation trượt ra

  // Robot logo (từ bot-toan-trinh-prototype.html) — dùng cho launcher.
  const LOGO_SVG = `<svg width="34" height="37" viewBox="0 0 120 132" xmlns="http://www.w3.org/2000/svg">
    <rect x="57" y="8" width="6" height="12" rx="3" fill="#2f7fbf"/><circle cx="60" cy="6" r="5" fill="#3b9be0"/>
    <path d="M28,40 Q60,14 92,40 L92,46 L28,46 Z" fill="#2f6bb0"/><rect x="28" y="43" width="64" height="7" rx="3" fill="#f4c11e"/>
    <rect x="32" y="46" width="56" height="46" rx="17" fill="#16233a"/>
    <circle cx="48" cy="70" r="8" fill="#54e0ff"/><circle cx="72" cy="70" r="8" fill="#54e0ff"/>
    <circle cx="48" cy="70" r="3" fill="#0a2b45"/><circle cx="72" cy="70" r="3" fill="#0a2b45"/>
    <path d="M52,82 Q60,89 68,82" stroke="#54e0ff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <rect x="36" y="94" width="48" height="34" rx="13" fill="#3b82c4"/><rect x="36" y="94" width="48" height="10" rx="5" fill="#2f6bb0"/>
    <circle cx="60" cy="114" r="8" fill="#f4c11e"/></svg>`;

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
    if (document.getElementById(PANEL_ID)) return;

    const host = document.createElement("div");
    host.id = PANEL_ID;
    const shadow = host.attachShadow({ mode: "open" });
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
        src="${chrome.runtime.getURL(`sidebar.html?embedded=1&tabId=${tabId}`)}"></iframe>`;

    (document.body || document.documentElement).appendChild(host);

    hideLauncher();
    applySidebarPushLayout();
    ensureTranslateOverrideStyle();
    requestAnimationFrame(() => host.classList.add("open")); // kích hoạt trượt vào
    persistOpen(true);
    persistDismissed(false); // mở lại (toolbar/bong bóng) = hết trạng thái "tắt hẳn"
    setGlobalDismissed(false); // mở lại = gỡ cờ đóng toàn cục (các tab khác lại sẵn sàng hiện)
  }

  function minimizePanel() {
    const host = document.getElementById(PANEL_ID);
    if (!host) return;
    host.classList.remove("open");   // trượt ra
    restoreSidebarPushLayout();      // trả lại layout ngay
    showLauncher();
    persistOpen(false);
    // Giữ iframe sống (không mất state chat) — chỉ ẩn sau khi trượt xong.
    setTimeout(() => { if (host) host.style.display = "none"; }, 320);
  }

  function restorePanel() {
    const host = document.getElementById(PANEL_ID);
    hideLauncher();
    if (!host) { togglePanel(); return; }
    host.style.display = "block";
    applySidebarPushLayout();
    requestAnimationFrame(() => host.classList.add("open"));
    persistOpen(true);
    persistDismissed(false);
    setGlobalDismissed(false);
  }

  function closePanel() {
    _selfClosing = true; // tab này chủ động đóng → onChanged bỏ qua để giữ animation trượt ra
    const host = document.getElementById(PANEL_ID);
    if (host) host.classList.remove("open");
    restoreSidebarPushLayout();
    removeTranslateOverrideStyle();
    // "Tắt hẳn" ≠ thu gọn: gỡ luôn bong bóng, nhớ trong phiên origin để reload không hiện lại.
    // Đóng ở 1 tab = TẮT trợ lý ở MỌI tab (cờ toàn cục) — bong bóng không còn bám tab khác.
    // Mở lại DUY NHẤT bằng icon extension trên toolbar.
    removeLauncher();
    persistDismissed(true);
    setGlobalDismissed(true);
    setTimeout(() => host?.remove(), 320); // gỡ hẳn iframe (mất state) — đúng nghĩa "đóng"
    persistOpen(false);
    // Người dân CHỦ ĐỘNG đóng → tắt auto-reopen xuyên origin (journey giữ để mở tay vẫn tiếp tục).
    chrome.runtime.sendMessage({ action: "getTabId" }, (res) => {
      if (chrome.runtime.lastError) return;
      const tabId = res?.tabId ?? "";
      chrome.storage.local.get(["tlnd_journey"], (st) => {
        const j = st?.tlnd_journey || {};
        if (j[tabId]) { j[tabId].keep_open = false; chrome.storage.local.set({ tlnd_journey: j }, () => void chrome.runtime.lastError); }
      });
    });
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

  // ── Launcher: bong bóng logo mép phải-dưới, hiện khi panel đóng/thu gọn ──
  function showLauncher() {
    if (!IS_TOP_FRAME) return;
    let b = document.getElementById(BUBBLE_ID);
    if (!b) {
      b = document.createElement("div");
      b.id = BUBBLE_ID;
      b.title = "Mở Trợ lý người dân";
      Object.assign(b.style, {
        position: "fixed", right: "18px", bottom: "22px",
        width: "56px", height: "56px", borderRadius: "50%",
        cursor: "pointer", zIndex: "2147483646",
        background: "linear-gradient(135deg,#12a06a,#2f7fbf)",
        boxShadow: "0 6px 20px rgba(15,40,80,.35)",
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "transform .15s ease",
      });
      b.innerHTML = LOGO_SVG;
      b.addEventListener("mouseenter", () => (b.style.transform = "scale(1.08)"));
      b.addEventListener("mouseleave", () => (b.style.transform = "scale(1)"));
      b.addEventListener("click", () => togglePanel());
      document.documentElement.appendChild(b);
    }
    b.style.display = "flex";
  }
  function hideLauncher() {
    const b = document.getElementById(BUBBLE_ID);
    if (b) b.style.display = "none";
  }
  function removeLauncher() {
    document.getElementById(BUBBLE_ID)?.remove();
  }

  // ── Persist theo phiên trang (cùng origin) + journey (XUYÊN origin — docs/07 §2.1) ──
  function persistOpen(open) {
    try { open ? sessionStorage.setItem(SS_OPEN_KEY, "1") : sessionStorage.removeItem(SS_OPEN_KEY); } catch (_) {}
  }
  function persistDismissed(on) {
    try { on ? sessionStorage.setItem(SS_DISMISS_KEY, "1") : sessionStorage.removeItem(SS_DISMISS_KEY); } catch (_) {}
  }
  function isDismissed() {
    try { return sessionStorage.getItem(SS_DISMISS_KEY) === "1"; } catch (_) { return false; }
  }
  // Cờ ĐÓNG TOÀN CỤC (chrome.storage.local): bấm ✕ ở 1 tab ⇒ ẩn trợ lý ở MỌI tab cho tới
  // khi mở lại bằng icon extension trên toolbar (createPanel/restorePanel gỡ cờ).
  function setGlobalDismissed(on) {
    try {
      if (on) chrome.storage.local.set({ [LS_DISMISS_KEY]: true }, () => void chrome.runtime.lastError);
      else chrome.storage.local.remove(LS_DISMISS_KEY, () => void chrome.runtime.lastError);
    } catch (_) {}
  }
  // Trang đăng nhập SSO/VNeID: khi ĐANG trong luồng (journey keep_open) → MỞ panel để bot đọc
  // kịch bản đăng nhập (mở VNeID → Quét QR); đọc xong sidebar tự thu gọn (collapse_after_tts) để
  // lộ mã QR. Ngoài luồng (tự vào trang SSO) → chỉ bong bóng, không chen màn quét QR.
  const IS_LOGIN_PAGE = /xacthuc|vneid|sso/.test(location.hostname);
  function restoreEarly() {
    if (!IS_TOP_FRAME) return;
    // Người dân đã bấm ✕ "tắt hẳn" trên origin này → reload cũng không hiện lại gì
    // (kể cả bong bóng). Mở lại duy nhất bằng icon extension trên toolbar.
    if (isDismissed()) return;
    // Đã ĐÓNG (✕) ở BẤT KỲ tab nào → cờ toàn cục bật → tab này cũng không hiện gì cho tới
    // khi mở lại bằng toolbar. Đọc TRƯỚC khi quyết hiện (async, nhưng chỉ tạo bong bóng
    // sau khi chắc chưa bị đóng ⇒ không nhấp nháy).
    chrome.storage.local.get([LS_DISMISS_KEY], (st) => {
      if (!chrome.runtime.lastError && st?.[LS_DISMISS_KEY]) return;
      showInitial();
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

  // ── Message: icon extension (background) + header sidebar (iframe) ──
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action === "togglePanel") { togglePanel(); sendResponse?.({ ok: true }); return; }
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
      const loginPage = !loggedIn && (/xacthuc|vneid|sso/.test(location.hostname)
        || (hasVisibleText("dang nhap") && hasVisibleText("quet ma qr")));
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
        infoModal,
        wizardStep,
        // Attach-only (chứng thực bản sao) không có form bước 2: nhận diện trực tiếp bảng
        // Thành phần hồ sơ để BE chuyển sang nhận tệp, kể cả khi stepper render chưa ổn định.
        attachmentTarget,
        // Nộp thành công: text xác nhận của cổng.
        submitted: body.includes("nop ho so thanh cong") || body.includes("gui ho so thanh cong")
          || (body.includes("thanh cong") && body.includes("ma ho so")),
      });
      return;
    }
  });
  // Lệnh từ header sidebar (iframe) → điều khiển khung ở content.
  window.addEventListener("message", (e) => {
    const t = e.data && e.data.__tlnd;
    if (t === "minimizePanel") minimizePanel();
    else if (t === "closePanel") closePanel();
  });

  // Đồng bộ trạng thái ĐÓNG giữa các tab TỨC THÌ (không đợi reload): tab khác bấm ✕ → cờ
  // toàn cục bật → tab này gỡ luôn bong bóng + panel. Tab tự đóng đã tự xử lý (giữ animation
  // trượt) nên _selfClosing bỏ qua 1 lần. Gỡ cờ (mở lại) KHÔNG tự bật bong bóng khắp nơi —
  // để lần tải sau quyết, tránh bong bóng nhảy lên bất ngờ.
  if (IS_TOP_FRAME) {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local" || !changes[LS_DISMISS_KEY]) return;
      if (!changes[LS_DISMISS_KEY].newValue) return; // chỉ xử lý khi BẬT cờ đóng
      if (_selfClosing) { _selfClosing = false; return; }
      removeLauncher();
      const host = document.getElementById(PANEL_ID);
      if (host) {
        host.classList.remove("open");
        restoreSidebarPushLayout();
        removeTranslateOverrideStyle();
        host.remove();
      }
      persistOpen(false);
    });
  }
})();
