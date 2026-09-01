// sidebar.js — UI chat "Trợ lý người dân" (Bước 3: hội thoại server-driven thật).
// Vòng lặp: ask(message, source) → BE trả {display_md, tts_text, chips, cards, actions, progress}
// → render + THI HÀNH actions. FE không quyết flow — chips[0] luôn là bước tốt nhất do BE chọn.
(() => {
  "use strict";

  // ── Ngữ cảnh nhúng: content.js nạp sidebar.html?embedded=1&tabId=<id> ──
  const params = new URLSearchParams(location.search);
  const TAB_ID = params.get("tabId") || "";
  const START_FRESH_ON_DVC_HOME = params.get("fresh") === "dvc-home";
  const DVC_HOME_URL = "https://dichvucong.gov.vn/";

  const $messages = document.getElementById("messages");
  const $status = document.getElementById("status");
  const $form = document.getElementById("chat-form");
  const $input = document.getElementById("chat-input");
  const $subtitle = document.querySelector(".bot-h .s");
  const $startScreen = document.getElementById("start-screen");
  const $startBtn = document.getElementById("start-btn");

  const api = new window.TlndApiClient();
  // Upload session chứa giấy tờ công dân nên mọi request từ extension phải mang Bearer.
  // Trang mobile dùng capability riêng nhúng trong QR, không đi qua helper này.
  const uploadSessionFetch = (url, init) => window.tlndAuth.authFetch(url, init);
  const JOURNEY_KEY = "tlnd_journey"; // { [tabId]: {conversation_id, ts} } — sống qua đổi origin
  const COMPLETION_LOGOUT_KEY_PREFIX = "tlnd_completion_logout:";
  const COMPLETION_LOGOUT_STORAGE_KEY = TAB_ID ? `${COMPLETION_LOGOUT_KEY_PREFIX}${TAB_ID}` : "";
  const ACTIVE_SPLIT_KEY = "tlnd_active_split_by_tab";
  const SPLIT_STAGE_KEY = "tro_ly_split_attach_queue_stage";
  const IDLE_TIMEOUT_MS = 10 * 60 * 1000;
  const IDLE_WARNING_MS = 30 * 1000;
  const IDLE_WARNING_TEXT = "⏳ Phiên sẽ tự kết thúc sau 30 giây nếu công dân không thao tác.";
  const ATTACH_SPLIT_DOCUMENTS_KEY = "tlnd_attach_split_documents";
  let attachSplitDocuments = false;
  const CLIENT_CAPABILITIES = Object.freeze({
    attachmentEngineVersion: 2,
    supportsSourceSegments: true,
    supportsAttachmentContext: true,
    supportsPageBoundDocsComplete: true,
    supportsAttachActionLease: true,
  });

  const BRAND_ICON_URL = chrome.runtime.getURL("assets/icons/icon-128.png");
  const BRAND_ICON = (size, className) => `<img class="${className}" src="${BRAND_ICON_URL}"
    width="${size}" height="${size}" alt="" aria-hidden="true" draggable="false">`;
  document.getElementById("bot-avatar").innerHTML = BRAND_ICON(30, "brand-icon-header");
  document.getElementById("start-avatar").innerHTML = BRAND_ICON(68, "brand-icon-start");

  // ── Render cơ bản ──
  function addBubble(role, html) {
    const el = document.createElement("div");
    el.className = `msg ${role}`;
    el.innerHTML = html;
    $messages.appendChild(el);
    $messages.scrollTop = $messages.scrollHeight;
    return el;
  }
  const addUserText = (t, hm) => addBubble("user", window.escapeHtml(t)
    + (hm ? `<span class="u-hm">${window.escapeHtml(hm)}</span>` : ""));
  // Tông màu card suy từ emoji mở đầu (✅ mốc xong / ⚠️ cảnh báo / ℹ️ giải thích) —
  // tất định theo text nên khôi phục phiên render y hệt, BE không cần đổi hợp đồng.
  function botTone(md) {
    const s = String(md || "").replace(/^[\s*_#>]+/, "");
    if (/^(✅|🎉)/.test(s)) return " ok";
    if (/^(⚠️|⚠|❗|🚫)/.test(s)) return " warn";
    if (/^(ℹ️|ℹ|💡|📌)/.test(s)) return " info";
    return "";
  }
  const addBotMd = (md) => addBubble("bot" + botTone(md), window.renderMarkdown(md));
  function addNode(el) {
    $messages.appendChild(el);
    $messages.scrollTop = $messages.scrollHeight;
  }
  function showProcedurePickerFromTop() {
    // Danh sách thủ tục dài nên các hàm render chung sẽ cuộn tới phần tử cuối. Riêng màn
    // chào phải đưa công dân về đầu để đọc lời giới thiệu và kiểm tra tỉnh/xã trước.
    requestAnimationFrame(() => { $messages.scrollTop = 0; });
  }
  function setStatus(msg, isErr) {
    if (!msg) { $status.hidden = true; return; }
    $status.hidden = false;
    $status.textContent = msg;
    $status.classList.toggle("err", !!isErr);
  }
  let $typing = null;
  function showTyping() {
    hideTyping();
    $typing = document.createElement("div");
    $typing.className = "msg bot typing";
    $typing.innerHTML = "<i></i><i></i><i></i>";
    addNode($typing);
  }
  function hideTyping() { $typing?.remove(); $typing = null; }

  // ── Journey: con trỏ phiên sống qua đổi trang/origin (docs/03a §1) ──
  // Mọi lượt ghi journey trong CÙNG sidebar phải nối đuôi nhau. Nếu saveJourney chạy nền
  // đồng thời với clearJourney, callback get cũ có thể ghi ngược phiên vừa xóa trở lại.
  let journeyWriteChain = Promise.resolve();
  function mutateJourney(mutator) {
    if (!TAB_ID) return Promise.resolve();
    const run = () => new Promise((resolve) => {
      chrome.storage.local.get([JOURNEY_KEY], (res) => {
        const j = res?.[JOURNEY_KEY] || {};
        mutator(j);
        chrome.storage.local.set({ [JOURNEY_KEY]: j }, () => {
          void chrome.runtime.lastError;
          resolve();
        });
      });
    });
    journeyWriteChain = journeyWriteChain.then(run, run);
    return journeyWriteChain;
  }

  function saveJourney({ touch = false } = {}) {
    const conversationId = api.conversationId;
    if (!TAB_ID || !conversationId) return Promise.resolve();
    return mutateJourney((j) => {
      const now = Date.now();
      // keep_open: sang origin khác content.js tự dựng lại sidebar (docs/07 §2.1).
      j[TAB_ID] = {
        ...(j[TAB_ID] || {}),
        conversation_id: conversationId,
        ts: now,
        keep_open: true,
        last_activity_at: touch ? now : (j[TAB_ID]?.last_activity_at || lastActivityAt || now),
      };
    });
  }
  async function loadJourney() {
    await journeyWriteChain.catch(() => {});
    return new Promise((resolve) => {
      if (!TAB_ID) return resolve(null);
      chrome.storage.local.get([JOURNEY_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve(res?.[JOURNEY_KEY]?.[TAB_ID] || null);
      });
    });
  }

  function clearJourney() {
    return mutateJourney((j) => { delete j[TAB_ID]; });
  }

  function readCompletionLogoutState() {
    return new Promise((resolve) => {
      if (!COMPLETION_LOGOUT_STORAGE_KEY) return resolve(null);
      chrome.storage.local.get([COMPLETION_LOGOUT_STORAGE_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve(res?.[COMPLETION_LOGOUT_STORAGE_KEY] || null);
      });
    });
  }

  async function writeCompletionLogoutState(value) {
    await new Promise((resolve) => {
      if (!COMPLETION_LOGOUT_STORAGE_KEY) return resolve();
      const done = () => { void chrome.runtime.lastError; resolve(); };
      if (value) chrome.storage.local.set({ [COMPLETION_LOGOUT_STORAGE_KEY]: value }, done);
      else chrome.storage.local.remove([COMPLETION_LOGOUT_STORAGE_KEY], done);
    });
    if (!value) {
      // Dọn khóa lồng của bản extension cũ để reload giữa lúc chuyển phiên không thể
      // khôi phục nhầm bộ đếm đã được hủy.
      await mutateJourney((journeys) => {
        const current = journeys[TAB_ID];
        if (!current?.completion_logout) return;
        const next = { ...current };
        delete next.completion_logout;
        journeys[TAB_ID] = next;
      });
    }
  }

  // ── Hết phiên sau 10 phút không có hoạt động thật ──
  // Activity từ trang cổng được content.js ghi cùng last_activity_at; sidebar đọc lại mỗi nhịp.
  let sessionActive = false;
  let lastActivityAt = 0;
  let lastActivityWriteAt = 0;
  let idleTimer = null;
  let idleWarningShown = false;
  let endingSession = false;

  function persistActivity(now) {
    if (!TAB_ID || !api.conversationId || now - lastActivityWriteAt < 3000) return;
    lastActivityWriteAt = now;
    saveJourney({ touch: true });
  }

  function markActivity() {
    if (!sessionActive) return;
    const now = Date.now();
    lastActivityAt = now;
    persistActivity(now);
    if (idleWarningShown) {
      idleWarningShown = false;
      if ($status.textContent === IDLE_WARNING_TEXT) setStatus("");
    }
  }

  function stopIdleTracking() {
    sessionActive = false;
    if (idleTimer) { clearInterval(idleTimer); idleTimer = null; }
    idleWarningShown = false;
    if ($status.textContent === IDLE_WARNING_TEXT) setStatus("");
  }

  function startIdleTracking(at = Date.now()) {
    sessionActive = true;
    lastActivityAt = Number(at) || Date.now();
    if (idleTimer) clearInterval(idleTimer);
    idleTimer = setInterval(async () => {
      if (!sessionActive || endingSession || busy) return;
      const journey = await loadJourney();
      const storedAt = Number(journey?.last_activity_at || 0);
      if (storedAt > lastActivityAt) lastActivityAt = storedAt;
      const idleFor = Date.now() - lastActivityAt;
      if (idleFor >= IDLE_TIMEOUT_MS) {
        await returnToStart("idle");
      } else if (idleFor >= IDLE_TIMEOUT_MS - IDLE_WARNING_MS && !idleWarningShown) {
        idleWarningShown = true;
        setStatus(IDLE_WARNING_TEXT);
      } else if (idleFor < IDLE_TIMEOUT_MS - IDLE_WARNING_MS && idleWarningShown) {
        idleWarningShown = false;
        if ($status.textContent === IDLE_WARNING_TEXT) setStatus("");
      }
    }, 5000);
  }

  for (const eventName of ["pointerdown", "keydown", "input", "change"]) {
    document.addEventListener(eventName, (event) => {
      if (event.isTrusted) markActivity();
    }, { passive: true });
  }

  // ── Gửi lệnh xuống content script của tab chứa sidebar ──
  function sendToContent(payload) {
    return new Promise((resolve) => {
      const id = Number(TAB_ID);
      if (!id) return resolve(null);
      try {
        chrome.tabs.sendMessage(id, payload, (res) => {
          void chrome.runtime.lastError;
          resolve(res ?? null);
        });
      } catch (_) { resolve(null); }
    });
  }

  function sendToBackground(payload) {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage(payload, (response) => {
          void chrome.runtime.lastError;
          resolve(response ?? null);
        });
      } catch (_) { resolve(null); }
    });
  }

  chrome.runtime.onMessage.addListener((message, sender) => {
    if (message?.action !== "citizenManualLogoutDetected") return;
    if (Number(sender?.tab?.id) !== Number(TAB_ID)) return;
    void resolveCompletionLogout("manual_logout_click", { notify: true });
  });

  function readActiveSplit() {
    return new Promise((resolve) => {
      if (!TAB_ID) return resolve(null);
      chrome.storage.local.get([ACTIVE_SPLIT_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve(res?.[ACTIVE_SPLIT_KEY]?.[TAB_ID] || null);
      });
    });
  }

  function writeActiveSplit(value) {
    return new Promise((resolve) => {
      if (!TAB_ID) return resolve();
      chrome.storage.local.get([ACTIVE_SPLIT_KEY], (res) => {
        const map = res?.[ACTIVE_SPLIT_KEY] || {};
        if (value) map[TAB_ID] = value;
        else delete map[TAB_ID];
        chrome.storage.local.set({ [ACTIVE_SPLIT_KEY]: map }, () => resolve());
      });
    });
  }

  // ── Vòng hội thoại trung tâm ──
  // busy: chống double-submit khi GÕ; chip/card VÀ sự kiện hệ thống đến giữa lượt thì
  // XẾP HÀNG chạy sau — nuốt im lặng là mất thao tác của người dùng.
  let busy = false;
  let pendingReturnReason = "";
  const pendingQueue = [];
  async function ask(message, source = "text", displayText = "", uiOptions = {}) {
    const userInitiated = source === "text" || source === "voice" || source === "chip";
    if (userInitiated) markActivity();
    if (busy) {
      if (source === "system" || source === "chip") {
        // Trả Promise chỉ resolve sau khi lượt xếp hàng THỰC SỰ gọi xong backend. Queue tách hồ sơ
        // dựa vào đây để chưa xóa recovery marker trước khi attach_report được ghi nhận.
        return await new Promise((resolve) => pendingQueue.push([
          message, source, displayText, uiOptions, resolve,
        ]));
      }
      return;
    }
    // Chọn nơi làm thủ tục/đối tượng chỉ cập nhật cấu hình tại chỗ. Nếu dùng render chung,
    // bubble "đang trả lời" sẽ ép danh sách thủ tục dài cuộn xuống cuối dù backend trả im lặng.
    const preserveScroll = uiOptions?.preserveScroll === true;
    const preservedScrollTop = preserveScroll ? $messages.scrollTop : null;
    const restorePreservedScroll = () => {
      if (preservedScrollTop === null) return;
      $messages.scrollTop = preservedScrollTop;
    };
    busy = true;
    if (!preserveScroll) showTyping();
    try {
      // Form context và cấu trúc bảng đính kèm là hai hợp đồng độc lập. Luôn gửi capability
      // để backend không phát sourceSegments cho extension cũ chưa có engine tách trang.
      const [formResult, attachmentResult, pageResult, declarationResult] = await Promise.all([
        sendToContent({ action: "collectFormContext" }),
        sendToContent({ action: "collectAttachmentContext" }),
        sendToContent({ action: "getPageContext" }),
        sendToContent({ action: "getDeclarationContext" }),
      ]);
      const effectivePageResult = {
        ...(pageResult || {}),
        ...(declarationResult?.ok ? declarationResult : {}),
      };
      const clientContext = {
        url: attachmentResult?.url || effectivePageResult?.url || "",
        detected_procedure: lastReplyData?.procedure_key || undefined,
        // Gửi cùng chính câu lệnh của công dân để backend không dùng docs_target cũ trong
        // khoảng giữa hai nhịp watcher khi SPA vừa chuyển Kê khai → Thành phần hồ sơ.
        page_context: {
          ...docsCompletePagePayload(effectivePageResult),
          // attachmentTarget một mình có thể chỉ là nút "Chọn tệp" ngoài bảng hồ sơ.
          // Số dòng lấy từ collectAttachmentContext là bằng chứng cấu trúc mạnh hơn.
          attachmentComponentCount: Array.isArray(
            attachmentResult?.attachmentContext?.components
          ) ? attachmentResult.attachmentContext.components.length : 0,
        },
        form_context: formResult?.formContext || {},
        attachment_context: attachmentResult?.attachmentContext || {},
        // Đây là tùy chọn tách giấy tờ BÊN TRONG một file, độc lập với splitMode của
        // hai thủ tục chứng thực (splitMode mở nhiều hồ sơ/tab).
        attachment_preferences: { splitDocuments: attachSplitDocuments },
        capabilities: CLIENT_CAPABILITIES,
      };
      if (clientContext.page_context.attachmentTarget
          || clientContext.page_context.attachmentComponentCount > 0) {
        // Các chip sửa Kê khai thuộc bubble cũ nhưng chat là append-only. Khi DOM xác nhận
        // đã sang Thành phần hồ sơ, gỡ chúng để không chạy nhầm pipeline kê khai.
        hideStaleDeclarationActions();
      }
      // Phiên MỚI (Bắt đầu / Trò chuyện mới / về trang chủ) sinh ra với đúng ngôn ngữ đang
      // chọn → câu chào đầu tiên đã là tiếng Mông, không phải chào tiếng Việt rồi mới đổi.
      const preferredLang = (voiceLang === "hmong" && _hmongAllowed()) ? "hmong" : "";
      const data = await api.ask(message, { source, displayText, clientContext, preferredLang });
      hideTyping();
      await saveJourney({ touch: userInitiated });
      renderReply(data);
      restorePreservedScroll();
      await runActions(data.actions || []);
      return data;
    } catch (e) {
      hideTyping();
      setStatus(`Không gọi được trợ lý: ${e?.message || e}. Kiểm tra backend đang chạy?`, true);
      setTimeout(() => setStatus(""), 5000);
    } finally {
      restorePreservedScroll();
      if (preserveScroll) requestAnimationFrame(restorePreservedScroll);
      busy = false;
      if (pendingReturnReason) {
        const reason = pendingReturnReason;
        pendingReturnReason = "";
        returnToStart(reason);
        return;
      }
      if (pendingQueue.length) {
        const [m, s, dt, queuedUiOptions, resolve] = pendingQueue.shift();
        ask(m, s, dt, queuedUiOptions).then(resolve);
      }
    }
  }

  let lastState = "";
  let lastReplyData = null; // reply gần nhất — dùng để đọc lại câu chào khi bật rảnh tay ở màn chào
  let replyTtsInFlight = 0;
  let completionReturnTimer = null;
  let completionLogoutMonitor = null;
  let completionLogoutState = null;
  let completionLogoutGeneration = 0;
  let chatBootStarted = false;
  let chatBootFinished = false;

  function completionChoiceButtons() {
    return Array.from(document.querySelectorAll(".chips.logout-choice .chip"));
  }

  function setCompletionChoiceDisabled(disabled) {
    completionChoiceButtons().forEach((button) => { button.disabled = !!disabled; });
  }

  async function completionPrincipalFingerprint(principal) {
    const raw = String(principal?.cccd || principal?.name || "")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/Đ/g, "D").replace(/đ/g, "d").replace(/\s+/g, " ").trim().toUpperCase();
    if (!raw || !globalThis.crypto?.subtle) return "";
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function stopCompletionLogoutRuntime() {
    completionLogoutGeneration += 1;
    if (completionReturnTimer) { clearTimeout(completionReturnTimer); completionReturnTimer = null; }
    if (completionLogoutMonitor) { clearInterval(completionLogoutMonitor); completionLogoutMonitor = null; }
  }

  async function resolveCompletionLogout(reason, { notify = false } = {}) {
    if (!completionLogoutState) return;
    stopCompletionLogoutRuntime();
    completionLogoutState = null;
    await writeCompletionLogoutState(null);
    if (notify) {
      setCompletionChoiceDisabled(true);
      setStatus("Đã phát hiện công dân đăng xuất thủ công — em đã hủy bộ đếm tự động đăng xuất.");
      setTimeout(() => setStatus(""), 5000);
    }
    console.info("[TLND] kết thúc chờ đăng xuất", { reason });
  }

  async function completionContextChanged(ctx, state, { countLoggedOut = false } = {}) {
    if (!ctx?.ok) return false; // Mất kết nối DOM không được tự suy ra đã logout.
    if (ctx.loginPage) return true;
    const currentPrincipal = await completionPrincipalFingerprint(ctx.principal);
    if (state.principal && currentPrincipal && state.principal !== currentPrincipal) return true;
    if (state.startedLoggedIn && !ctx.loggedIn && !ctx.submitted) {
      state.loggedOutChecks = countLoggedOut ? Number(state.loggedOutChecks || 0) + 1 : 2;
      return state.loggedOutChecks >= 2;
    }
    state.loggedOutChecks = 0;
    return false;
  }

  function armCompletionLogout(state) {
    stopCompletionLogoutRuntime();
    completionLogoutState = { ...state, phase: "pending", loggedOutChecks: 0 };
    const generation = completionLogoutGeneration;
    const remainingMs = Math.max(0, Number(completionLogoutState.deadline) - Date.now());
    completionReturnTimer = setTimeout(async () => {
      completionReturnTimer = null;
      if (generation !== completionLogoutGeneration || completionLogoutState?.phase !== "pending") return;
      const ctx = await readPageContext();
      if (generation !== completionLogoutGeneration || completionLogoutState?.phase !== "pending") return;
      if (await completionContextChanged(ctx, completionLogoutState)) {
        await resolveCompletionLogout("portal_session_changed", { notify: true });
        return;
      }
      // Deadline chỉ được phép xóa đúng phiên vẫn còn hiệu lực tại thời điểm kiểm tra cuối.
      await resolveCompletionLogout("timeout");
      await returnToStart("completed");
    }, remainingMs);

    completionLogoutMonitor = setInterval(async () => {
      if (generation !== completionLogoutGeneration || completionLogoutState?.phase !== "pending") return;
      const ctx = await readPageContext();
      if (generation !== completionLogoutGeneration || completionLogoutState?.phase !== "pending") return;
      if (await completionContextChanged(ctx, completionLogoutState, { countLoggedOut: true })) {
        await resolveCompletionLogout("manual_logout", { notify: true });
      }
    }, 2500);
  }

  async function beginCompletionLogoutWait(delayMs, restored = null) {
    const ctx = restored ? null : await readPageContext();
    const deadline = Number(restored?.deadline) || (Date.now() + delayMs);
    const state = {
      deadline,
      conversationId: restored?.conversationId || api.conversationId || "",
      principal: restored?.principal || await completionPrincipalFingerprint(ctx?.principal),
      startedLoggedIn: restored ? restored.startedLoggedIn === true : ctx?.loggedIn === true,
      phase: "pending",
    };
    submittedReported = true;
    if (watcherTimer) { clearInterval(watcherTimer); watcherTimer = null; }
    stopIdleTracking();
    handsfree = false;
    emptyTurns = 0;
    $hfBtn?.classList.remove("active");
    stopVoice?.();
    await writeCompletionLogoutState(state);
    armCompletionLogout(state);
  }

  async function claimCompletionChoice() {
    if (completionLogoutState?.phase !== "pending") return false;
    const state = { ...completionLogoutState, phase: "deciding" };
    stopCompletionLogoutRuntime();
    completionLogoutState = state;
    await writeCompletionLogoutState(state);
    return true;
  }

  async function resumeCompletionChoice() {
    if (!completionLogoutState || completionLogoutState.phase !== "deciding") return;
    const state = { ...completionLogoutState, phase: "pending" };
    await writeCompletionLogoutState(state);
    armCompletionLogout(state);
    setCompletionChoiceDisabled(false);
  }
  async function waitForChatBoot(timeoutMs = 10000) {
    const deadline = Date.now() + timeoutMs;
    while (!chatBootFinished && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return chatBootFinished && !!api.conversationId;
  }
  function stopReplyTts() {
    replyTtsInFlight = 0;
    window.__hccTTS?.stop?.();
  }
  const $meterBar = document.getElementById("step-meter-bar");
  function setProgress(p) {
    if (!p?.label) return;
    // Chế độ tiếng Mông: nối nhãn bước tiếng Mông sau nhãn Việt (BE gắn labelHmong).
    const hm = p.labelHmong ? ` · ${p.labelHmong}` : "";
    $subtitle.textContent = `Bước ${p.step}/${p.total} · ${p.label}${hm}`;
    if ($meterBar && p.total) {
      $meterBar.style.width = `${Math.min(100, Math.round((p.step / p.total) * 100))}%`;
    }
  }
  function renderReply(d, opts) {
    lastReplyData = d;
    if (d.lang) syncLangUI(d.lang); // BE là nguồn sự thật về chế độ tiếng Mông
    maybeRestoreHmongLang(d); // phiên MỚI (lang=vi) + máy đã lưu tiếng Mông → khôi phục im lặng
    const prevState = lastState;
    if (d.state) { lastState = d.state; schedulePageWatcher(); }
    const hasLogoutChoice = (d.chips || []).some((chip) => [
      "__action:logout_citizen", "__action:continue_dossiers",
    ].includes(chip.send));
    const duplicateLogoutChoice = hasLogoutChoice && !!document.querySelector(".chips.logout-choice");
    if (d.display_md && !duplicateLogoutChoice) addBotMd(d.display_md);
    // ĐỌC XONG câu này thì THU GỌN panel (kịch bản đăng nhập trên trang SSO → lộ mã QR để quét).
    // Chỉ áp cho reply LIVE (không phải khôi phục phiên noTts, kẻo mở lại tay bị auto-thu-gọn).
    const collapseAfter = !opts?.noTts && (d.actions || []).some((a) => a.type === "collapse_after_tts");
    const willSpeak = !duplicateLogoutChoice && !!d.tts_text && voiceCfg.tts && !ttsMuted;
    // noTts: render lại reply CŨ khi khôi phục phiên — không đọc lại câu đã đọc rồi.
    if (opts?.noTts) { /* bỏ đọc */ }
    else if (!duplicateLogoutChoice && d.tts_text && voiceCfg.tts) {
      // fill_report đến ngay sau action điền form. Đây là phần tiếp nối của fields_ready nên
      // phải xếp hàng để đọc HẾT câu "Xong rồi ạ..." trước; các chuyển trạng thái khác vẫn
      // cắt câu cũ để bot không đọc hướng dẫn đã hết hiệu lực.
      const queueAfterFillReady = prevState === "filling" && d.state === "reviewing"
        && replyTtsInFlight > 0;
      if (!queueAfterFillReady) stopReplyTts();
      else console.debug("[TLND] xếp TTS rà soát sau câu báo đọc xong giấy tờ");
      replyTtsInFlight += 1;
      // Rảnh tay: đọc xong tự mở mic nghe lượt kế (docs/03a §5). onDone KHÔNG bắn khi bị ngắt lời.
      window.__hccTTS?.speak?.(d.tts_text, d.tts_lang || "vi", () => {
        replyTtsInFlight = Math.max(0, replyTtsInFlight - 1);
        if (collapseAfter && willSpeak) minimizePanel(); // đọc THẬT xong → thu gọn (mute thì onDone bắn ngay, bỏ qua)
        // Nếu còn câu nối tiếp trong hàng đợi thì chưa mở mic, tránh ASR barge-in cắt câu sau.
        if (handsfree && !completionReturnTimer && replyTtsInFlight === 0) startVoice();
      });
    } else if (handsfree) {
      startVoice(); // không đọc được (tts tắt) vẫn phải mở mic để vòng không đứng
    }
    // Không đọc (tts tắt/mute) mà vẫn cần thu gọn → cho ~7s đọc chữ rồi thu gọn.
    if (collapseAfter && !willSpeak) setTimeout(minimizePanel, 7000);
    if (!duplicateLogoutChoice) (d.cards || []).forEach(renderCard);
    if (!duplicateLogoutChoice && d.chips?.length) renderChips(d.chips);
    setProgress(d.progress);
    // Khôi phục phiên (noTts) không dựng card tiến trình — không có WS để chốt nó.
    if (!opts?.noTts) updatePipeFromState(prevState, d);
  }

  function renderChips(chips) {
    // Ẩn nút hoàn thành thủ công còn sót trong last_reply của phiên cũ. Luồng mới chỉ
    // kết thúc khi watcher đọc được xác nhận nộp thành công từ chính cổng dịch vụ công.
    chips = chips.filter((c) => c.send !== "__action:finish_procedure");
    if (!chips.length) return;
    const wrap = document.createElement("div");
    const isLogoutChoice = chips.some((c) => [
      "__action:logout_citizen", "__action:continue_dossiers",
    ].includes(c.send));
    wrap.className = "chips" + (isLogoutChoice ? " logout-choice" : "");
    chips.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip" + (c.solid ? " solid" : "");
      b.dataset.send = c.send || "";
      b.dataset.renderState = lastState || "";
      b.textContent = c.label;
      if (c.labelHmong) { // chế độ tiếng Mông: dòng nghiêng nhỏ dưới nhãn Việt
        const hm = document.createElement("span");
        hm.className = "chip-hm";
        hm.textContent = c.labelHmong;
        b.appendChild(hm);
      }
      // "Đã đưa đủ giấy tờ, xử lý đi": khoá đến khi nhận ≥1 tệp (renderDocProgress mở khoá).
      // Tránh bấm chốt xử lý lúc chưa tải gì lên (nút hiện sẵn ngay khi vừa chọn cách tải).
      if (c.send === "__action:docs_done") {
        $docsDoneChip = b;
        if (!docsReceived) {
          b.disabled = true;
          b.title = "Công dân tải giấy tờ lên trước, em mới xử lý được ạ";
        }
      }
      b.addEventListener("click", () => {
        // 1 nhóm chip chỉ bấm 1 lần — disable cả nhóm rồi gửi.
        wrap.querySelectorAll("button").forEach((x) => (x.disabled = true));
        // Nút chốt giấy tờ được chuyển sang holder riêng dưới checklist; vẫn khoá cả
        // chính nó lẫn nhóm nút phụ ban đầu để không bấm đổi cách gửi khi đang xử lý.
        b.closest(".chips")?.querySelectorAll("button").forEach((x) => (x.disabled = true));
        // Làm thủ tục khác → xóa phiên thật và về màn bắt đầu.
        if (c.send === "__action:new_procedure") { resetConversation(); return; }
        addUserText(c.label, c.labelHmong);
        if (["__action:logout_citizen", "__action:continue_dossiers"].includes(c.send)) {
          void (async () => {
            await claimCompletionChoice();
            const data = await ask(c.send, "chip", c.label);
            const expectedAction = c.send === "__action:logout_citizen"
              ? "logout_citizen" : "continue_dossiers";
            if (!(data?.actions || []).some((action) => action.type === expectedAction)) {
              await resumeCompletionChoice();
            }
          })();
          return;
        }
        if (c.send === "__action:docs_done" || c.send === "__event:docs_complete") {
          void submitDocsComplete(c.send, "chip", c.label);
          return;
        }
        ask(c.send, "chip", c.label);
      });
      wrap.appendChild(b);
    });
    addNode(wrap);
    placeDocsDoneAfterProgress();
  }

  function hideStaleDeclarationActions() {
    document.querySelectorAll([
      '.chip[data-send="__action:refill"]',
      '.chip[data-send="__action:add_documents"]',
    ].join(",")).forEach((button) => {
      // Nút Điều chỉnh được render sau khi đính xong là action hợp lệ của state done,
      // không phải chip Kê khai bị lưu lại trong lịch sử chat.
      if (button.dataset.send === "__action:add_documents"
          && button.dataset.renderState === "done") return;
      const wrap = button.closest(".chips");
      button.remove();
      if (wrap && !wrap.querySelector("button")) wrap.remove();
    });
  }

  // ── Page watcher (docs/07 §2.2): tự nhận đăng-nhập-xong / nộp-thành-công — bỏ chip tay ──
  let watcherTimer = null;
  let watcherTicks = 0;
  let watcherPageStatusInFlight = false;
  let fallbackChipShown = false;
  let infoModalTries = 0;
  let submittedReported = false;

  // Báo BE trạng thái trang (__event:page_status) — BE nhìn tín hiệu THẬT để quyết bước
  // tiếp (chọn cơ quan / xác nhận modal / nhắc điền chủ hồ sơ / vào kê khai), sidebar
  // không tự suy diễn. Trang React render dần → chờ đến khi có tín hiệu có nghĩa mới gửi.
  const pageSignal = (c) => !!(c && (
    c.formKind || c.declarationTarget || c.agencyBlock || c.loginPage || c.vneidLoginCodePrompt
      || c.vneidDataSharingPrompt || c.vneidPasscodePrompt
      || c.infoModal || c.wizardStep || c.attachmentTarget || c.businessHost
  ));
  let lastVneidSidebarDebugSignature = "";
  async function readPageContext() {
    const [page, modal, business, declaration] = await Promise.all([
      sendToContent({ action: "getPageContext" }),
      sendToContent({ action: "getVneidModalContext" }),
      sendToContent({ action: "getBusinessRuntimeContext" }),
      sendToContent({ action: "getDeclarationContext" }),
    ]);
    const merged = {
      ...(page || {}),
      ...(business?.ok ? business : {}),
      ...(declaration?.ok ? declaration : {}),
    };
    if (modal?.ok) {
      const signature = modal.vneidLoginCodePrompt ? "login-code"
        : modal.vneidDataSharingPrompt ? "data-sharing"
          : modal.vneidPasscodePrompt ? "passcode" : "";
      if (signature && signature !== lastVneidSidebarDebugSignature) {
        console.info("[TLND-VNeID][sidebar] received-modal-context", {
          modal: signature,
          state: lastState,
          conversationId: api.conversationId || null,
        });
        lastVneidSidebarDebugSignature = signature;
      }
      return { ...merged, ...modal, ok: true };
    }
    if (lastVneidSidebarDebugSignature) {
      console.info("[TLND-VNeID][sidebar] modal-closed", {
        previous: lastVneidSidebarDebugSignature,
        state: lastState,
      });
      lastVneidSidebarDebugSignature = "";
    }
    return business?.ok ? { ...merged, ok: true } : page;
  }

  function docsCompletePagePayload(ctx) {
    return {
      // Backend phân biệt context vừa đọc thất bại với lệnh giọng nói dùng target đã lưu.
      pageContextCaptured: !!ctx?.ok,
      wizardStep: Number(ctx?.wizardStep) || 0,
      formKind: String(ctx?.formKind || ""),
      declarationTarget: !!ctx?.declarationTarget,
      attachmentTarget: !!ctx?.attachmentTarget,
      businessHost: !!ctx?.businessHost,
      businessStage: String(ctx?.businessStage || ""),
    };
  }

  async function submitDocsComplete(command, source = "system", displayText = "") {
    const ctx = await readPageContext();
    const payload = docsCompletePagePayload(ctx);
    return ask(`${command}:${JSON.stringify(payload)}`, source, displayText);
  }
  async function sendPageStatus(pre) {
    let c = pre || null;
    for (let i = 0; !c && i < 12; i++) {
      const got = await readPageContext();
      if (got?.ok && pageSignal(got)) { c = got; break; }
      c = null;
      await new Promise((r) => setTimeout(r, 900));
      if (i === 11) c = got; // hết kiên nhẫn → gửi trạng thái cuối (BE im lặng nếu không có gì)
    }
    if (!c?.ok) return;
    // Stepper có thể ở top-frame nhưng khối "Thông tin định danh" nằm trong frame con.
    // Hỏi riêng toàn tab; portal-dvc chỉ trả lời từ frame thật sự chứa khối này.
    if (c.wizardStep === 1 && !c.ownerContext) {
      const owner = await sendToContent({ action: "getOwnerContext" });
      if (owner?.ok && owner.ownerContext) c.ownerContext = owner.ownerContext;
    }
    const pageStatus = {
      loggedIn: !!c.loggedIn, formKind: c.formKind || "",
      declarationTarget: !!c.declarationTarget,
      agencyBlock: !!c.agencyBlock, loginPage: !!c.loginPage,
      vneidLoginCodePrompt: !!c.vneidLoginCodePrompt,
      vneidDataSharingPrompt: !!c.vneidDataSharingPrompt,
      vneidPasscodePrompt: !!c.vneidPasscodePrompt,
      infoModal: !!c.infoModal, wizardStep: c.wizardStep || 0,
      attachmentTarget: !!c.attachmentTarget,
      businessHost: !!c.businessHost,
      businessStage: c.businessStage || "",
      businessProcedureHint: c.businessProcedureHint || "",
      businessActive: !!c.businessActive,
      businessResult: c.businessResult || null,
      // Chủ thể dữ liệu VNeID content đọc từ cổng — BE lưu vào conv, ghi biên bản consent.
      principal: c.principal || null,
      // Định danh ở chính khối "Thông tin chủ hồ sơ" — backend dùng để chọn đúng người.
      ownerContext: c.ownerContext || null,
      // Chỉ có khi công dân chủ động bấm kiểm tra lại. Backend dùng cờ này để trả lời
      // rõ đang còn ở đăng nhập hay chưa tới hồ sơ, thay vì im lặng như watcher nền.
      manualCheck: !!c.manualCheck,
    };
    const hasVneidModal = pageStatus.vneidLoginCodePrompt
      || pageStatus.vneidDataSharingPrompt || pageStatus.vneidPasscodePrompt;
    if (hasVneidModal) {
      console.info("[TLND-VNeID][sidebar] send-page-status", {
        state: lastState,
        loginCode: pageStatus.vneidLoginCodePrompt,
        dataSharing: pageStatus.vneidDataSharingPrompt,
        passcode: pageStatus.vneidPasscodePrompt,
      });
    }
    const reply = await ask(`__event:page_status:${JSON.stringify(pageStatus)}`, "system");
    if (hasVneidModal) {
      console.info("[TLND-VNeID][sidebar] backend-reply", JSON.stringify({
        received: !!reply,
        state: reply?.state || lastState,
        hasGuide: !!reply?.display_md,
        actions: (reply?.actions || []).map((action) => action.type),
      }));
    }
  }

  async function verifyPortalState() {
    let ctx = null;
    try {
      ctx = await readPageContext();
    } catch (error) {
      console.warn("[TLND] Không đọc được trạng thái trang khi công dân yêu cầu kiểm tra", error);
    }
    // Không đọc được content script cũng là "chưa xác minh được", tuyệt đối không được
    // suy ra đã đăng nhập. Gửi context rỗng để backend trả lời rõ thay vì nút bấm im lặng.
    await sendPageStatus({ ...(ctx?.ok ? ctx : { ok: true }), manualCheck: true });
  }

  let lastPageSig = "";
  const WATCH_STATES = [
    "guide_login", "ask_doc_method", "qr_waiting", "collecting_docs",
    "owner_waiting_next", "attaching", "done", "filling",
  ];
  const isWatchedState = () => WATCH_STATES.includes(lastState)
    && (lastState !== "filling" || lastReplyData?.procedure_key === "dang-ky-kinh-doanh");
  function schedulePageWatcher() {
    if (!isWatchedState()) {
      if (watcherTimer) { clearInterval(watcherTimer); watcherTimer = null; }
      return;
    }
    if (watcherTimer) return; // đang chạy
    watcherTicks = 0;
    watcherTimer = setInterval(async () => {
      watcherTicks += 1;
      // Không tự hết hạn watcher theo từng chặng. Công dân có thể cần nhiều phút để đăng
      // nhập, chụp giấy tờ, rà soát chủ hồ sơ/kê khai hoặc nộp hồ sơ; nếu dừng sau 60 nhịp
      // thì lần chuyển trang sau đó sẽ bị bỏ lỡ. Vòng đời chung đã được chặn bởi idle timeout,
      // đổi phiên và returnToStart nên không cần thêm một timeout cục bộ dễ làm đứt luồng.
      if (!isWatchedState()) {
        clearInterval(watcherTimer); watcherTimer = null; return;
      }
      const ctx = await readPageContext();
      if (!ctx?.ok) return;
      // Trang SPA đổi bước không reload → theo dõi CHỮ KÝ tín hiệu, đổi mới báo BE
      // (loggedIn không tính: trang chi tiết cũng có user-dropdown khi đã đăng nhập).
      const businessResultSig = ctx.businessResult
        ? `${ctx.businessResult.createdAt || 0}:${ctx.businessResult.ok ? 1 : 0}` : "";
      const sig = `${ctx.formKind}|${ctx.wizardStep || 0}|${ctx.declarationTarget ? 1 : 0}|${ctx.infoModal ? 1 : 0}|${ctx.agencyBlock ? 1 : 0}|${ctx.attachmentTarget ? 1 : 0}|${ctx.vneidLoginCodePrompt ? 1 : 0}|${ctx.vneidDataSharingPrompt ? 1 : 0}|${ctx.vneidPasscodePrompt ? 1 : 0}|${ctx.businessStage || ""}|${ctx.businessActive ? 1 : 0}|${businessResultSig}`;
      const watchesDocsTarget = ["ask_doc_method", "qr_waiting", "collecting_docs"].includes(lastState);
      // Trong bước đính kèm, probe lại định kỳ kể cả chữ ký DOM không đổi. Đây là đường
      // phục hồi bền nếu attach_ready/pipeline_error bị mất lúc WebSocket rớt.
      const attachRecoveryProbe = lastState === "attaching"
        && (ctx.wizardStep === 3 || ctx.attachmentTarget)
        && watcherTicks % 5 === 0;
      if ((lastState === "guide_login" || watchesDocsTarget
          || lastState === "owner_waiting_next" || lastState === "attaching"
          || (lastState === "filling" && ctx.businessHost))
          && pageSignal(ctx) && (sig !== lastPageSig || attachRecoveryProbe)
          && !watcherPageStatusInFlight) {
        lastPageSig = sig;
        watcherPageStatusInFlight = true;
        // QR guide đã thu gọn panel nhưng giữ iframe sống. Khi một trong ba modal xác thực
        // xuất hiện, đánh thức đúng iframe/conversation cũ trước khi phát câu hướng dẫn.
        if (lastState === "guide_login" && (
          ctx.vneidLoginCodePrompt || ctx.vneidDataSharingPrompt || ctx.vneidPasscodePrompt
        )) restorePanel();
        try {
          await sendPageStatus(ctx);
        } finally {
          watcherPageStatusInFlight = false;
        }
      } else if (lastState === "guide_login" && watcherTicks >= 17 && !fallbackChipShown) {
        // ~60s chưa tự nhận ra → cho công dân yêu cầu kiểm tra DOM lại, không coi đây
        // là lời xác nhận đã đăng nhập hay đã vào hồ sơ.
        fallbackChipShown = true;
        renderChips([{ label: "Kiểm tra lại trang hiện tại", send: "__event:sso_success", solid: true }]);
      } else if (lastState === "done" && ctx.submitted && !submittedReported) {
        // Chốt TRƯỚC khi gọi BE: trang thành công giữ nguyên text rất lâu; nếu để reply
        // state=done khởi động watcher lại thì cùng hồ sơ sẽ sinh nhiều card hoàn tất.
        submittedReported = true;
        clearInterval(watcherTimer); watcherTimer = null;
        ask("__event:submitted", "system");
      }
    }, 3500);
  }

  // ── Cards (docs/03 §2.1) ──
  function renderCard(card) {
    if (card.kind === "service_list") return renderServiceList(card);
    if (card.kind === "location_picker") return renderLocationPicker(card);
    if (card.kind === "doc_options") return renderDocOptions(card);
    // Contract cũ từng xin SĐT sau khi nộp hồ sơ. Đã ngừng hoàn toàn; bỏ qua cả card
    // còn sót trong last_reply của phiên được tạo trước khi extension cập nhật.
    if (card.kind === "phone_form") return;
    if (card.kind === "consent_form") return renderConsentForm(card);
    console.warn("[TLND] card chưa hỗ trợ:", card.kind);
  }

  // Card xin phép xử lý dữ liệu cá nhân (Luật 91/2025) — chữ nghĩa 100% server-driven,
  // FE chỉ dựng checkbox + nút. Tích đủ 2 ô mới mở nút Đồng ý; toàn văn luật nằm trong
  // khối mở rộng (sidebar 400px không dùng modal).
  function renderConsentForm(card) {
    const el = document.createElement("div");
    el.className = "consent-card";
    // Chế độ tiếng Mông: BE gắn card.hmong (bản HỖ TRỢ HIỂU — tiếng Việt vẫn là bản pháp lý
    // chính, toàn văn Điều 4 giữ tiếng Việt). Dòng Mông nghiêng dưới từng phần.
    const hm = card.hmong || null;
    const hmDiv = (text, cls = "c-hm") => (hm && text
      ? `<div class="${cls}">${window.escapeHtml(text)}</div>` : "");
    const docs = (card.documents || []).map((d) => `
      <div class="cdoc"><span class="ci">${window.escapeHtml(d.icon || "📄")}</span>
        <span class="cn">${window.escapeHtml(d.name)}${hm && d.nameHmong
          ? `<i class="cn-hm">${window.escapeHtml(d.nameHmong)}</i>` : ""}</span>${d.sides === 2 ? '<span class="ctag">2 mặt</span>' : ""}</div>`).join("");
    const checks = (card.checks || []).map((t, i) => `
      <label class="ccheck"><input type="checkbox" data-i="${i}">
        <span>${window.escapeHtml(t)}${hm?.checks?.[i]
          ? `<i class="cn-hm">${window.escapeHtml(hm.checks[i])}</i>` : ""}</span></label>`).join("");
    el.innerHTML = `
      <span class="cbadge">🔒 Xác nhận trên Trợ lý người dân</span>
      <div class="ctitle">Cho phép em đọc giấy tờ và tự động điền biểu mẫu</div>
      ${hmDiv(hm?.title, "ctitle-hm")}
      <div class="ctext">${window.renderMarkdown(card.intro_md || "")}${hmDiv(hm?.intro_md)}</div>
      <div class="cdocs-box">
        <div class="clist-t">📋 Giấy tờ em sẽ đọc — ${window.escapeHtml(card.procedure || "thủ tục này")}${hm?.docs_title
          ? ` <i class="cn-hm">${window.escapeHtml(hm.docs_title)}</i>` : ""}</div>
        <div class="cdocs">${docs}</div>
      </div>
      <div class="cscope">${window.renderMarkdown(card.scope_md || "")}${hmDiv(hm?.scope_md)}</div>
      <div class="cpurpose">${window.renderMarkdown(card.purpose_md || "")}${hmDiv(hm?.purpose_md)}</div>
      <details class="clegal"><summary>Quyền, nghĩa vụ của chủ thể dữ liệu (Điều 4, Luật 91/2025/QH15)${hm?.legal_title
        ? ` <i class="cn-hm">${window.escapeHtml(hm.legal_title)}</i>` : ""}</summary>
        <div class="clegal-b">${window.renderMarkdown(card.legal_md || "")}</div></details>
      <button type="button" class="chip callall">✓ Chọn tất cả${hm?.select_all
        ? ` · ${window.escapeHtml(hm.select_all)}` : ""}</button>
      ${checks}
      <div class="cactions">
        <button type="button" class="chip cdecline">${window.escapeHtml(card.decline_label || "Không đồng ý · Tự nhập")}${hm?.decline_label
          ? `<span class="chip-hm">${window.escapeHtml(hm.decline_label)}</span>` : ""}</button>
        <button type="button" class="chip solid caccept" disabled>${window.escapeHtml(card.accept_label || "Đồng ý và tự động điền")}${hm?.accept_label
          ? `<span class="chip-hm">${window.escapeHtml(hm.accept_label)}</span>` : ""}</button>
      </div>
      <div class="cver">Bản nội dung v${window.escapeHtml(String(card.version || "1.0"))} — sự đồng ý được ghi nhật ký, công dân rút lại được bất cứ lúc nào.${hmDiv(hm?.ver_note)}</div>`;
    const boxes = [...el.querySelectorAll('input[type="checkbox"]')];
    const $accept = el.querySelector(".caccept");
    const sync = () => { $accept.disabled = !boxes.every((b) => b.checked); };
    boxes.forEach((b) => b.addEventListener("change", sync));
    el.querySelector(".callall").addEventListener("click", () => {
      boxes.forEach((b) => { b.checked = true; });
      sync();
    });
    const finish = (accepted, label, labelHmong) => {
      el.querySelectorAll("button, input").forEach((x) => { x.disabled = true; });
      addUserText(label, labelHmong);
      ask(`__action:consent:${JSON.stringify({ accepted, checks: boxes.map((b) => b.checked) })}`, "chip", label);
    };
    const viLabel = (btn, fallback) => btn.childNodes[0]?.textContent?.trim() || fallback;
    $accept.addEventListener("click", () => finish(true, viLabel($accept, "Đồng ý và tự động điền"),
      card.hmong?.accept_label));
    const $decline = el.querySelector(".cdecline");
    $decline.addEventListener("click", () => finish(false, viLabel($decline, "Không đồng ý · Tự nhập"),
      card.hmong?.decline_label));
    addNode(el);
  }

  function renderServiceList(card) {
    (card.items || []).forEach((it) => {
      const el = document.createElement("div");
      el.className = "svc2";
      // Chế độ tiếng Mông: BE gắn titleHmong → dòng nghiêng dưới tên tiếng Việt (mockup).
      const hmongLine = it.titleHmong
        ? `<div class="tt-hm">${window.escapeHtml(it.titleHmong)}</div>` : "";
      el.innerHTML = `<div class="ico">${window.escapeHtml(it.icon || "📄")}</div>
        <div class="st"><div class="tt">${window.escapeHtml(it.title)}</div>${hmongLine}
        <div class="ss">${window.escapeHtml(it.subtitle || "")}</div></div><div class="arr">›</div>`;
      el.addEventListener("click", () => {
        addUserText(it.title, it.titleHmong);
        ask(`__action:pick_procedure:${JSON.stringify({ key: it.key })}`, "chip", it.title);
      });
      addNode(el);
    });
  }

  // Combobox tìm kiếm cho danh sách dài (34 tỉnh / cả trăm xã): gõ để lọc (không dấu vẫn
  // khớp), danh sách cao ~6 dòng cuộn được — select trần sổ full rất dài và vướng mắt.
  function makeSearchSelect({ placeholder, onPick }) {
    const wrap = document.createElement("div");
    wrap.className = "ssel";
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = placeholder;
    input.autocomplete = "off";
    input.spellcheck = false;
    const list = document.createElement("div");
    list.className = "ssel-list";
    list.hidden = true;
    let options = [];
    let value = "";
    const fold = (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d")
      .normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    function render(q) {
      const ql = fold(q).trim();
      list.innerHTML = "";
      const subset = options.filter((o) => !ql || fold(o.label).includes(ql));
      if (!subset.length) {
        const d = document.createElement("div");
        d.className = "ssel-empty";
        d.textContent = "Không tìm thấy";
        list.appendChild(d);
        return;
      }
      subset.forEach((o) => {
        const it = document.createElement("div");
        it.className = "ssel-item" + (o.label === value ? " on" : "");
        it.textContent = o.label;
        if (o.sub) { // dòng phụ tiếng Mông (chế độ song ngữ) — chỉ hiển thị, không tham gia lọc
          const sub = document.createElement("div");
          sub.className = "ssel-sub";
          sub.textContent = o.sub;
          it.appendChild(sub);
        }
        it.__opt = o;
        // mousedown + preventDefault: chọn TRƯỚC khi input blur kịp đóng danh sách.
        it.addEventListener("mousedown", (e) => { e.preventDefault(); pick(o); });
        list.appendChild(it);
      });
    }
    function pick(o) {
      value = o.label;
      input.value = o.label;
      list.hidden = true;
      input.blur();
      onPick(o);
    }
    input.addEventListener("focus", () => { input.select(); render(""); list.hidden = false; });
    input.addEventListener("input", () => { render(input.value); list.hidden = false; });
    // Blur không chọn gì → trả lại giá trị đang chọn (chữ đang gõ chỉ là bộ lọc).
    input.addEventListener("blur", () => { list.hidden = true; input.value = value; });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const first = list.querySelector(".ssel-item");
        if (first && !list.hidden) pick(first.__opt);
      } else if (e.key === "Escape") input.blur();
    });
    wrap.append(input, list);
    return {
      el: wrap,
      setOptions(next) { options = next || []; },
      setValue(v) { value = v || ""; input.value = value; },
      setDisabled(d) { input.disabled = !!d; },
      get value() { return value; },
    };
  }

  function renderLocationPicker(card) {
    const el = document.createElement("div");
    el.className = "loc";
    const cur = card.current || {};
    // Chế độ tiếng Mông: BE gắn card.hmong (nhãn + subject_options) → nhãn song ngữ.
    const hm = card.hmong || null;
    const label = (viText, hmText) => `${window.escapeHtml(viText)}${
      hm && hmText ? ` <i class="lb-hm">· ${window.escapeHtml(hmText)}</i>` : ""}`;
    el.innerHTML = `<div class="loc-t">📍 ${label("Nơi làm thủ tục", hm?.title)}</div>`;
    const provinces = card.provinces || [];
    const subjectConfig = card.executionSubject || {};
    const subjectOptions = Array.isArray(subjectConfig.options) ? subjectConfig.options : [];
    let provSlug = "";

    const provRow = document.createElement("div");
    provRow.className = "sel";
    provRow.innerHTML = `<span>${label("Tỉnh/Thành phố", hm?.province)}</span>`;
    const wardRow = document.createElement("div");
    wardRow.className = "sel";
    wardRow.innerHTML = `<span>${label("Phường/Xã", hm?.ward)}</span>`;
    const subjectRow = document.createElement("div");
    subjectRow.className = "sel";
    subjectRow.innerHTML = `<span>${label("Đối tượng thực hiện", hm?.subject)}</span>`;

    const wardBox = makeSearchSelect({
      placeholder: "Gõ để tìm xã/phường…",
      onPick: (o) => {
        if (!provSlug) return;
        ask(`__action:set_location:${JSON.stringify({ province_slug: provSlug, ward: o.label })}`,
          "chip", `Chọn nơi làm thủ tục: ${o.label}, ${provBox.value}`, { preserveScroll: true });
      },
    });
    const provBox = makeSearchSelect({
      placeholder: "Gõ để tìm tỉnh/thành…",
      onPick: (o) => { provSlug = o.slug; wardBox.setValue(""); loadWards(); },
    });
    const subjectBox = makeSearchSelect({
      placeholder: "Chọn đối tượng thực hiện…",
      onPick: (o) => {
        ask(`__action:set_execution_subject:${JSON.stringify({ key: o.key })}`,
          "chip", `Đối tượng thực hiện: ${o.label}`, { preserveScroll: true });
      },
    });
    provBox.setOptions(provinces.map((p) => ({ label: p.text, slug: p.slug })));
    subjectBox.setOptions(subjectOptions.map((option) => ({
      key: option.key,
      label: option.label,
      // Dòng phụ tiếng Mông trong dropdown (input vẫn giữ nhãn tiếng Việt khi chọn).
      sub: hm?.subject_options?.[option.key] || "",
    })));
    provRow.appendChild(provBox.el);
    wardRow.appendChild(wardBox.el);
    subjectRow.appendChild(subjectBox.el);
    el.append(provRow, wardRow);
    if (subjectOptions.length) el.append(subjectRow);
    addNode(el);

    async function loadWards() {
      wardBox.setOptions([]);
      wardBox.setDisabled(true);
      const data = await api.getWards(provSlug);
      const names = (data?.communes || [])
        .map((w) => (typeof w === "string" ? w : (w?.text || w?.name || "")))
        .filter(Boolean);
      wardBox.setOptions(names.map((n) => ({ label: n })));
      wardBox.setDisabled(false);
    }

    // Nơi hiện tại của phiên (acc gắn tỉnh/xã hoặc đã chọn trước đó) → hiện sẵn, vẫn đổi được.
    const curProv = provinces.find((p) => p.text === cur.province);
    if (curProv) {
      provSlug = curProv.slug;
      provBox.setValue(curProv.text);
      wardBox.setValue(cur.ward || "");
      loadWards();
    } else {
      wardBox.setDisabled(true); // chọn tỉnh trước rồi mới có danh sách xã
    }
    const currentSubject = subjectOptions.find((option) => option.key === subjectConfig.current)
      || subjectOptions[0];
    subjectBox.setValue(currentSubject?.label || "");
  }

  const DOC_OPTIONS = {
    qr: { icon: "📱", title: "Chụp bằng điện thoại (quét QR)", desc: "Quét mã QR, chụp hoặc chọn ảnh giấy tờ ngay trên điện thoại — nhanh nhất." },
    scan: { icon: "📷", title: "Scan tại quầy", desc: "Đặt giấy tờ bản cứng lên máy quét tại quầy." },
    profile: { icon: "📁", title: "Lấy dữ liệu đã lưu", desc: "Đã từng làm và lưu hồ sơ → không cần cung cấp lại." },
  };
  function renderDocOptions(card) {
    (card.options || []).forEach((key) => {
      const meta = DOC_OPTIONS[key];
      if (!meta) return;
      // Chế độ tiếng Mông: BE gắn card.hmong[key] → dòng nghiêng dưới tên lựa chọn.
      const hmTitle = card.hmong?.[key]?.title || "";
      const hmLine = hmTitle ? `<div class="ot-hm">${window.escapeHtml(hmTitle)}</div>` : "";
      const el = document.createElement("div");
      el.className = "opt";
      el.innerHTML = `<div class="oi">${meta.icon}</div><div>
        <div class="ot">${window.escapeHtml(meta.title)}</div>${hmLine}
        <div class="od">${window.escapeHtml(meta.desc)}</div></div>`;
      el.addEventListener("click", () => {
        addUserText(meta.title, hmTitle);
        ask(`__action:doc_method:${JSON.stringify({ value: key })}`, "chip", meta.title);
      });
      addNode(el);
    });
  }

  // ── Card tiến trình xử lý giấy tờ (thường 30–90s) ──
  // Chặng chủ hồ sơ vẫn diễn giải 4 bước; chặng điền tờ khai chỉ hiện một dòng gọn.
  const PIPE_STAGES = [
    { from: 0, label: "Kiểm tra ảnh đã nhận", hm: "Xyuas cov duab" },
    { from: 3, label: "Đọc chữ trên giấy tờ (OCR)", hm: "Nyeem ntawv (OCR)" },
    { from: 22, label: "Bóc tách và đối chiếu thông tin", hm: "Muab thiab piv cov ntaub ntawv" },
    { from: 45, label: "Chuẩn bị điền biểu mẫu", hm: "Npaj sau daim foos" },
  ];
  let $pipe = null;
  let pipeTimer = null;
  let pipeT0 = 0;
  let pipeFinished = false;

  function renderPipeSteps(elapsed, doneAll) {
    $pipe?.querySelectorAll(".pipe-step").forEach((row, i) => {
      const started = elapsed >= PIPE_STAGES[i].from;
      const ended = doneAll || (i + 1 < PIPE_STAGES.length && elapsed >= PIPE_STAGES[i + 1].from);
      row.className = "pipe-step" + (ended ? " done" : started ? " active" : "");
      row.querySelector(".pic").textContent = ended ? "✓" : String(i + 1);
      row.querySelector(".ps").innerHTML = !ended && started ? '<span class="pipe-spin"></span>' : "";
    });
  }

  function showPipelineCard(label, detailed = false) {
    if ($pipe && !pipeFinished) return; // đang chạy rồi — không dựng card thứ 2
    pipeFinished = false;
    pipeT0 = Date.now();
    $pipe = document.createElement("div");
    $pipe.className = "pipe-card";
    $pipe.dataset.label = label;
    $pipe.dataset.detailed = detailed ? "1" : "0";
    $pipe.innerHTML = `
      <div class="pipe-h">🤖 ${window.escapeHtml(label)}</div>
      <div class="prog"><i style="width:4%"></i></div>
      ${detailed ? PIPE_STAGES.map((stage, i) => `
        <div class="pipe-step"><span class="pic">${i + 1}</span>
          <span class="pl">${stage.label}${voiceLang === "hmong" && stage.hm
            ? `<i class="pl-hm">${stage.hm}</i>` : ""}</span><span class="ps"></span></div>`).join("") : ""}`;
    addNode($pipe);
    if (detailed) renderPipeSteps(0, false);
    clearInterval(pipeTimer);
    pipeTimer = setInterval(() => {
      const t = (Date.now() - pipeT0) / 1000;
      const bar = $pipe?.querySelector(".prog i");
      // Tiệm cận 94% — không bao giờ "đầy" trước khi có mốc thật.
      if (bar) bar.style.width = `${Math.min(94, Math.round(100 * (1 - Math.exp(-t / 30))))}%`;
      if (detailed) renderPipeSteps(t, false);
    }, 1000);
  }

  function pipeStop() { clearInterval(pipeTimer); pipeTimer = null; pipeFinished = true; }
  function pipeDone() {
    if (!$pipe || pipeFinished) return;
    pipeStop();
    const detailed = $pipe.dataset.detailed === "1";
    if (detailed) renderPipeSteps(Infinity, true);
    const bar = $pipe.querySelector(".prog i");
    if (bar) bar.style.width = "100%";
    $pipe.classList.add("done");
    $pipe.querySelector(".pipe-h").textContent = detailed
      ? "✅ Đã đọc xong giấy tờ"
      : `✅ ${$pipe.dataset.label || "Đã xử lý xong"}`;
    $messages.scrollTop = $messages.scrollHeight;
  }
  function pipeFail() {
    if (!$pipe || pipeFinished) return;
    pipeStop();
    $pipe.classList.add("err");
    $pipe.querySelector(".pipe-h").textContent = "⚠️ Xử lý giấy tờ chưa xong được";
  }

  // BE vào owner_filling/filling = pipeline bắt đầu chạy. Chỉ dựng card chờ khi phản hồi
  // chưa có action điền tức thời; áp dụng cả lần xử lý đầu và lần điền lại thông tin.
  function updatePipeFromState(prev, d) {
    const st = d.state || prev;
    const willFill = (d.actions || []).some((a) =>
      a.type === "fill_fields" || a.type === "fill_owner_fields");
    if ((st === "owner_filling" || st === "filling") && prev !== st && !willFill) {
      if (st === "owner_filling") {
        showPipelineCard("Em đang đọc và bóc tách giấy tờ — công dân chờ em chút ạ…", true);
      } else {
        showPipelineCard("Bóc tách thông tin và điền biểu mẫu", false);
      }
    }
    else if ($pipe && !pipeFinished) {
      if (willFill || st === "owner_waiting_next" || st === "reviewing" || st === "attaching" || st === "done") pipeDone();
      else if (st === "collecting_docs" || st === "qr_waiting") pipeFail();
    }
  }

  // Chú giải màu ô sau khi điền: xanh = đọc từ giấy tờ, vàng = giá trị mặc định
  // (khớp viền vàng trên form), đỏ = chưa tìm thấy ô. Đếm từ chính payload fill.
  function renderFillLegend(fields, res) {
    const filled = res?.filled || 0;
    if (!filled) return;
    const yellow = Math.min((fields || []).filter((f) => f && f.default).length, filled);
    const red = (res?.notFound || []).length;
    const el = document.createElement("div");
    el.className = "legend";
    el.innerHTML = `
      <span><i class="dot g"></i>${filled - yellow} ô đọc từ giấy tờ</span>
      <span><i class="dot y"></i>${yellow} ô mặc định — kiểm tra lại</span>
      ${red ? `<span><i class="dot r"></i>${red} ô chưa điền được</span>` : ""}`;
    addNode(el);
  }

  // ── Phiên tải giấy tờ qua QR (Bước 5 — docs/05) ──
  let uploadWs = null;
  let uploadWsGeneration = 0;
  let uploadWsReconnectTimer = null;
  let $docProgress = null;
  let uploadSid = null; // phiên đang mở — dùng cho nhánh "Scan tại quầy" (upload từ máy tính)
  // Cổng cho nút "Đã đưa đủ giấy tờ, xử lý đi": chỉ mở khi phiên đã nhận ≥1 tệp.
  let docsReceived = false;
  let $docsDoneChip = null;
  const $fileListScrim = document.getElementById("file-list-scrim");
  const $fileListDialog = document.getElementById("file-list-dialog");
  const $fileListTitle = document.getElementById("file-list-title");
  const $fileListSummary = document.getElementById("file-list-summary");
  const $fileListIcon = document.getElementById("file-list-icon");
  const $fileListBody = document.getElementById("file-list-body");
  const $fileListError = document.getElementById("file-list-error");
  const $fileListClose = document.getElementById("file-list-close");
  let uploadSessionFiles = [];
  let uploadSessionProgress = null;
  let activeFileGroup = null; // {docKey, name, icon, unknown}
  let fileListReturnFocus = null;
  let fileListLoadSeq = 0;
  const deletingFileIds = new Set();

  function updateDocsDoneChipLabel(label, labelHmong) {
    if (!$docsDoneChip || !label) return;
    $docsDoneChip.textContent = label;
    if (labelHmong) { // giữ dòng Mông khi BE đổi nhãn nút chốt giấy tờ theo bước
      const hm = document.createElement("span");
      hm.className = "chip-hm";
      hm.textContent = labelHmong;
      $docsDoneChip.appendChild(hm);
    }
    $docsDoneChip.setAttribute("aria-label", label);
  }

  function uploadFileIcon(name) {
    const ext = String(name || "").split(".").pop().toLowerCase();
    if (["jpg", "jpeg", "png", "webp", "heic", "gif"].includes(ext)) return "🖼️";
    if (ext === "pdf") return "📄";
    if (["doc", "docx"].includes(ext)) return "📝";
    if (["xls", "xlsx"].includes(ext)) return "📊";
    return "📎";
  }

  function filesInActiveGroup() {
    if (!activeFileGroup) return [];
    return uploadSessionFiles.filter((file) => activeFileGroup.unknown
      ? !file.doc_key
      : file.doc_key === activeFileGroup.docKey);
  }

  function setFileListError(message = "") {
    if (!$fileListError) return;
    $fileListError.hidden = !message;
    $fileListError.textContent = message;
  }

  function renderUploadFileList({ loading = false } = {}) {
    if (!$fileListBody || !activeFileGroup) return;
    const files = filesInActiveGroup();
    const locked = !!uploadSessionProgress?.complete;
    $fileListTitle.textContent = activeFileGroup.name;
    $fileListIcon.textContent = activeFileGroup.icon || (activeFileGroup.unknown ? "⚠️" : "📄");
    $fileListSummary.textContent = loading
      ? "Đang tải danh sách…"
      : locked
        ? `${files.length} tệp đã nhận · Hồ sơ đang được xử lý`
        : `${files.length} tệp đã nhận`;
    $fileListBody.replaceChildren();
    if (loading) {
      const state = document.createElement("div");
      state.className = "file-list-loading";
      state.textContent = "Đang tải danh sách tệp…";
      $fileListBody.appendChild(state);
      return;
    }
    if (!files.length) {
      const state = document.createElement("div");
      state.className = "file-list-empty";
      state.textContent = "Chưa có tệp nào trong mục này.";
      $fileListBody.appendChild(state);
      return;
    }
    files.forEach((file) => {
      const row = document.createElement("div");
      row.className = `file-list-row${deletingFileIds.has(file.fid) ? " deleting" : ""}`;

      const icon = document.createElement("span");
      icon.className = "file-kind";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = uploadFileIcon(file.name);

      const name = document.createElement("span");
      name.className = "file-list-name";
      name.textContent = file.name || "Tệp không có tên";
      name.title = file.name || "Tệp không có tên";

      row.append(icon, name);
      if (locked) {
        const lock = document.createElement("span");
        lock.className = "file-list-lock";
        lock.textContent = "Đã chốt";
        row.appendChild(lock);
      } else {
        const remove = document.createElement("button");
        remove.className = "file-list-delete";
        remove.type = "button";
        remove.textContent = "✕";
        remove.title = `Xóa ${file.name || "tệp"}`;
        remove.setAttribute("aria-label", `Xóa tệp ${file.name || "không có tên"}`);
        remove.disabled = deletingFileIds.has(file.fid);
        remove.addEventListener("click", () => void deleteUploadSessionFile(file));
        row.appendChild(remove);
      }
      $fileListBody.appendChild(row);
    });
  }

  function closeUploadFileList({ restoreFocus = true } = {}) {
    if (!$fileListScrim || $fileListScrim.hidden) return;
    $fileListScrim.hidden = true;
    activeFileGroup = null;
    setFileListError();
    if (restoreFocus && fileListReturnFocus?.isConnected) fileListReturnFocus.focus();
    fileListReturnFocus = null;
  }

  async function loadUploadSessionFiles({ showLoading = false } = {}) {
    const sid = uploadSid;
    if (!sid) return null;
    const seq = ++fileListLoadSeq;
    if (showLoading && activeFileGroup) renderUploadFileList({ loading: true });
    const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${encodeURIComponent(sid)}`);
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(data?.detail || `Không đọc được danh sách tệp (HTTP ${res.status}).`);
    if (sid !== uploadSid || seq !== fileListLoadSeq) return null;
    uploadSessionFiles = Array.isArray(data?.files) ? data.files : [];
    uploadSessionProgress = data?.progress || uploadSessionProgress;
    if (data?.progress) renderDocProgress(data.progress, { preserveScroll: true });
    if (activeFileGroup) renderUploadFileList();
    return data;
  }

  async function openUploadFileList(group, trigger) {
    if (!$fileListScrim || !uploadSid) return;
    activeFileGroup = group;
    fileListReturnFocus = trigger || document.activeElement;
    setFileListError();
    $fileListScrim.hidden = false;
    renderUploadFileList({ loading: true });
    $fileListDialog?.focus();
    try {
      await loadUploadSessionFiles();
    } catch (error) {
      if (activeFileGroup) {
        renderUploadFileList();
        setFileListError(error?.message || "Không tải được danh sách tệp.");
      }
    }
  }

  async function deleteUploadSessionFile(file) {
    const sid = uploadSid;
    if (!sid || !file?.fid || uploadSessionProgress?.complete || deletingFileIds.has(file.fid)) return;
    deletingFileIds.add(file.fid);
    setFileListError();
    renderUploadFileList();
    try {
      const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(file.fid)}`,
        { method: "DELETE" });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || `Không xóa được tệp (HTTP ${res.status}).`);
      if (sid !== uploadSid) return;
      uploadSessionFiles = uploadSessionFiles.filter((item) => item.fid !== file.fid);
      renderUploadFileList();
      await loadUploadSessionFiles();
    } catch (error) {
      if (sid === uploadSid && activeFileGroup) {
        setFileListError(error?.message || "Không xóa được tệp. Công dân thử lại giúp em ạ.");
      }
    } finally {
      deletingFileIds.delete(file.fid);
      if (sid === uploadSid && activeFileGroup) renderUploadFileList();
    }
  }

  function resetUploadFileListState() {
    fileListLoadSeq += 1;
    closeUploadFileList({ restoreFocus: false });
    uploadSessionFiles = [];
    uploadSessionProgress = null;
    deletingFileIds.clear();
  }

  function setUploadSession(sid) {
    if (uploadSid !== sid) resetUploadFileListState();
    uploadSid = sid;
    // Khi sidebar được dựng lại giữa phiên, WS không phát lại tiến trình cũ. Đọc snapshot
    // ngay để checklist và nút xem file vẫn khôi phục đủ, không chờ công dân tải thêm tệp.
    return loadUploadSessionFiles().catch((error) => {
      console.warn("[TLND] Không khôi phục được danh sách tệp upload session", error?.message || error);
      return null;
    });
  }

  $fileListClose?.addEventListener("click", () => closeUploadFileList());
  $fileListScrim?.addEventListener("click", (event) => {
    if (event.target === $fileListScrim) closeUploadFileList();
  });
  document.addEventListener("keydown", (event) => {
    if ($fileListScrim?.hidden) return;
    if (event.key === "Escape") {
      closeUploadFileList();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...$fileListDialog.querySelectorAll("button:not(:disabled)")];
    if (!focusable.length) {
      event.preventDefault();
      $fileListDialog.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  function placeDocsDoneAfterProgress() {
    const progress = document.getElementById("doc-progress-card");
    if (!progress || !$docsDoneChip) return;

    let holder = document.getElementById("docs-done-actions");
    if (!holder) {
      holder = document.createElement("div");
      holder.id = "docs-done-actions";
      holder.className = "chips docs-done-actions";
    }
    const oldWrap = $docsDoneChip.parentElement;
    // Progress WS có thể tới trước hoặc sau reply chứa chips. Khi nút còn nằm trong
    // nhóm gốc, neo checklist ngay sau nhóm nút phụ để thứ tự luôn là: phụ → giấy tờ → chốt.
    if (oldWrap && oldWrap !== holder && oldWrap.classList.contains("chips")) {
      oldWrap.insertAdjacentElement("afterend", progress);
    }
    // replaceChildren bảo đảm chỉ còn một CTA mới nhất khi QR/Scan render reply lại.
    if (holder.firstElementChild !== $docsDoneChip) holder.replaceChildren($docsDoneChip);
    progress.insertAdjacentElement("afterend", holder);
    if (oldWrap && oldWrap !== holder && oldWrap.classList.contains("chips") && !oldWrap.children.length) {
      oldWrap.remove();
    }
  }

  // Nhánh SCAN: chọn tệp từ máy tính → upload thẳng vào phiên (cùng endpoint với mobile).
  const $fileInput = document.getElementById("file-input");
  $fileInput?.addEventListener("change", async (e) => {
    const files = [...(e.target.files || [])];
    e.target.value = "";
    if (!files.length || !uploadSid) return;
    markActivity();
    const totalBytes = files.reduce((sum, file) => sum + Number(file.size || 0), 0);
    const totalMb = totalBytes / (1024 * 1024);
    const uploadStartedAt = performance.now();
    // Đây chỉ là chặng truyền/lưu file. Phân loại OCR/LLM (nếu thủ tục cần) chạy ở chặng
    // xử lý sau khi người dân bấm "Đã đưa đủ", không được làm chậm cửa sổ chọn tệp.
    setStatus(`⏳ Đang tải ${files.length} tệp lên hệ thống…`);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f, f.name));
      const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${uploadSid}/files`,
        { method: "POST", body: fd });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      console.log("[TLND] upload session files", {
        fileCount: files.length,
        totalBytes,
        elapsedMs: Math.round(performance.now() - uploadStartedAt),
        accepted: (data?.accepted || []).map((item) => item.doc_key || null),
      });
      setStatus("");
      if (data?.progress) renderDocProgress(data.progress, { preserveScroll: !$fileListScrim?.hidden });
      if (!$fileListScrim?.hidden) void loadUploadSessionFiles();
      const unknown = (data?.accepted || []).filter((a) => !a.doc_key).length;
      if (unknown) addBotMd(`⚠️ **${unknown} tệp** em chưa nhận ra loại — công dân scan lại rõ hơn hoặc cứ bấm "Đã đưa đủ" để em xử lý phần nhận được ạ.`);
    } catch (err) {
      setStatus(`⚠️ Tải tệp lỗi: ${err?.message || err}`, true);
      setTimeout(() => setStatus(""), 5000);
    }
  });

  function renderQrCard(a) {
    const el = document.createElement("div");
    el.className = "qr-card";
    el.innerHTML = `
      <img class="qr-img" alt="Mã QR tải giấy tờ" src="data:image/png;base64,${a.qr_png_base64}">
      <div class="qr-cap">Quét bằng camera điện thoại → mở trang tải ảnh<br>
        <span>Phiên ${window.escapeHtml(a.session_id)}</span></div>
      <div class="prog"><i style="width:0"></i></div>
      <div class="qr-stat">Đang chờ công dân quét mã…</div>`;
    addNode(el);
    $docProgress = el; // progress bar + status cập nhật qua WS
  }

  function renderDocProgress(p, { preserveScroll = false } = {}) {
    const preservedScrollTop = preserveScroll ? $messages.scrollTop : null;
    uploadSessionProgress = p || uploadSessionProgress;
    // Nhận được tệp ĐẦU TIÊN (kể cả tệp chưa nhận ra loại / slot tuỳ chọn) → mở khoá nút
    // "Đã đưa đủ giấy tờ, xử lý đi". BE dặn cứ bấm nút này để xử lý cả phần chưa nhận ra
    // loại, nên chỉ cần có bất kỳ tệp nào là cho chốt — không đợi đủ giấy bắt buộc.
    const gotAny = ((p.docs || []).reduce((n, d) => n + (d.received || 0), 0) + (p.unknown || 0)) > 0;
    docsReceived = gotAny;
    if ($docsDoneChip) {
      $docsDoneChip.disabled = !gotAny;
      if (gotAny) $docsDoneChip.removeAttribute("title");
      else $docsDoneChip.title = "Công dân tải giấy tờ lên trước, em mới xử lý được ạ";
    }
    // Card danh sách giấy tờ (thay/đặt dưới card QR) — kiểu .doc-row prototype.
    let wrap = document.getElementById("doc-progress-card");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "doc-progress-card";
      wrap.style.cssText = "align-self:stretch;display:flex;flex-direction:column;gap:7px;";
      addNode(wrap);
    }
    const rows = (p.docs || []).map((d) => {
      const repeatable = !!d.repeatable;
      const done = !repeatable && d.received >= d.sides;
      const count = Number(d.receivedCount ?? d.received) || 0;
      const row = document.createElement("div");
      row.className = `doc-row ${done ? "done-row" : ""}`;

      const icon = document.createElement("div");
      icon.className = "ic";
      icon.textContent = d.icon || "📄";
      const name = document.createElement("div");
      name.className = "nm";
      name.textContent = d.name || "Giấy tờ";
      if (voiceLang === "hmong" && d.nameHmong) { // chế độ tiếng Mông: dòng nghiêng dưới tên
        const hm = document.createElement("div");
        hm.className = "nm-hm";
        hm.textContent = d.nameHmong;
        name.appendChild(hm);
      }
      row.append(icon, name);

      if (count > 0) {
        const view = document.createElement("button");
        view.type = "button";
        view.className = "doc-files-btn";
        view.textContent = voiceLang === "hmong"
          ? `Đã nhận ${count} tệp · Txais tau ${count} daim ›`
          : `Đã nhận ${count} tệp ›`;
        view.setAttribute("aria-label", `Xem ${count} tệp ${d.name || "giấy tờ"}`);
        view.addEventListener("click", () => void openUploadFileList({
          docKey: d.key, name: d.name || "Giấy tờ đã nhận", icon: d.icon || "📄", unknown: false,
        }, view));
        row.appendChild(view);
      } else {
        const status = document.createElement("span");
        status.className = "st";
        status.textContent = repeatable
          ? (voiceLang === "hmong" ? "Đã nhận 0 tệp · Tsis tau txais" : "Đã nhận 0 tệp")
          : `${d.received}/${d.sides}${d.sides > 1 ? " mặt" : ""}`;
        row.appendChild(status);
      }
      return row;
    });
    if ((p.unknown || 0) > 0) {
      const row = document.createElement("div");
      row.className = "doc-row unknown-row";
      const icon = document.createElement("div");
      icon.className = "ic";
      icon.textContent = "⚠️";
      const name = document.createElement("div");
      name.className = "nm";
      name.textContent = voiceLang === "hmong"
        ? "Tệp chưa nhận ra loại · Tsis paub yam twg" : "Tệp chưa nhận ra loại";
      const view = document.createElement("button");
      view.type = "button";
      view.className = "doc-files-btn";
      view.textContent = `Đã nhận ${p.unknown} tệp ›`;
      view.setAttribute("aria-label", `Xem ${p.unknown} tệp chưa nhận ra loại`);
      view.addEventListener("click", () => void openUploadFileList({
        docKey: null, name: "Tệp chưa nhận ra loại", icon: "⚠️", unknown: true,
      }, view));
      row.append(icon, name, view);
      rows.push(row);
    }
    wrap.replaceChildren(...rows);
    if (!$fileListScrim?.hidden) renderUploadFileList();
    placeDocsDoneAfterProgress();
    if ($docProgress) {
      const bar = $docProgress.querySelector(".prog i");
      const stat = $docProgress.querySelector(".qr-stat");
      if (bar && p.total) bar.style.width = `${(p.received / p.total) * 100}%`;
      // Chỉ hiện số đã nhận (không "/tổng" — tổng gồm slot tuỳ chọn dễ gây hiểu lầm còn thiếu).
      // TỔNG tệp (cả tuỳ chọn/chưa nhận ra loại), không chỉ giấy bắt buộc.
      const gotFiles = p.files_count ?? p.received ?? 0;
      if (stat) stat.textContent = p.complete
        ? `✅ Đã nhận ${gotFiles} tệp`
        : `Đã nhận ${gotFiles} tệp`;
    }
    $messages.scrollTop = preservedScrollTop ?? $messages.scrollHeight;
  }

  function stopUploadSubscription() {
    uploadWsGeneration += 1;
    if (uploadWsReconnectTimer) {
      clearTimeout(uploadWsReconnectTimer);
      uploadWsReconnectTimer = null;
    }
    if (uploadWs) {
      // Chủ động đóng khi đổi/xóa phiên: gỡ onclose trước để socket cũ không tự nối lại.
      uploadWs.onclose = null;
      uploadWs.onerror = null;
      try { uploadWs.close(); } catch (_) { /* đã đóng */ }
      uploadWs = null;
    }
  }

  function subscribeUploadSession(sid) {
    // Phiên upload mới: chưa nhận tệp nào → khoá lại nút "đủ giấy tờ" (renderChips vừa render
    // nó ở lượt này nên $docsDoneChip trỏ đúng nút hiện tại; khoá kể cả khi phiên trước đã mở).
    docsReceived = false;
    if ($docsDoneChip) {
      $docsDoneChip.disabled = true;
      $docsDoneChip.title = "Công dân tải giấy tờ lên trước, em mới xử lý được ạ";
    }
    stopUploadSubscription();
    const generation = uploadWsGeneration;
    const wsUrl = `${window.tlndWsBase(BASE_URL)}/ws/upload-sessions/${sid}`;
    let mobileConnectedSent = false;
    let completeSent = false;
    let reconnectAttempt = 0;
    let reconnectStatusShown = false;

    function scheduleReconnect() {
      if (generation !== uploadWsGeneration || sid !== uploadSid || !api.conversationId) return;
      const delay = Math.min(1000 * (2 ** reconnectAttempt), 10000);
      reconnectAttempt += 1;
      if (uploadWsReconnectTimer) clearTimeout(uploadWsReconnectTimer);
      uploadWsReconnectTimer = setTimeout(connect, delay);
      console.warn(`[TLND] WS phiên ${sid} bị ngắt, thử nối lại sau ${delay}ms`);
    }

    function connect() {
      if (generation !== uploadWsGeneration || sid !== uploadSid) return;
      uploadWsReconnectTimer = null;
      let ws;
      try {
        ws = new WebSocket(wsUrl);
      } catch (_) {
        scheduleReconnect();
        return;
      }
      uploadWs = ws;
      ws.onopen = () => {
        if (reconnectStatusShown) setStatus("");
        reconnectStatusShown = false;
        reconnectAttempt = 0;
      };
      ws.onmessage = (ev) => {
        let d;
        try { d = JSON.parse(ev.data); } catch (_) { return; }
        // Ảnh từ điện thoại và tiến trình OCR/điền là hoạt động của phiên, không được timeout giữa chừng.
        if (["session_opened", "progress", "complete", "owner_fields_ready", "fields_ready", "attach_ready", "business_ready"].includes(d.type)) {
          markActivity();
        }
        if (d.type === "session_opened" && !mobileConnectedSent) {
          mobileConnectedSent = true;
          ask("__event:mobile_connected", "system");
        } else if (d.type === "progress") {
          renderDocProgress(d, { preserveScroll: !$fileListScrim?.hidden });
          if (!$fileListScrim?.hidden) void loadUploadSessionFiles();
        } else if (d.type === "complete" && !completeSent) {
          // Lưới chắn đua /complete vs /files: nếu BE lỡ phát complete lúc phiên CHƯA có file
          // nào (upload còn đang bay), KHÔNG bắn docs_complete — tránh xử lý phiên rỗng "0 file,
          // thử lại lần 2 mới được". Chờ tới khi progress có file thật rồi complete lại.
          const got = (d.docs || []).reduce((n, x) => n + (x.received || 0), 0) + (d.unknown || 0);
          if (got <= 0) { renderDocProgress(d); return; }
          completeSent = true;
          renderDocProgress(d);
          void submitDocsComplete("__event:docs_complete", "system");
        } else if (d.type === "owner_fields_ready") {
          pipeDone();
          ask("__event:owner_fields_ready", "system");
        } else if (d.type === "fields_ready") {
          pipeDone(); // mốc thật: dữ liệu đã bóc xong
          ask("__event:fields_ready", "system");   // BE trả action fill_fields (docs/06)
        } else if (d.type === "attach_ready") {
          pipeDone();
          ask("__event:attach_ready", "system");   // BE trả action attach_plan
        } else if (d.type === "business_ready") {
          pipeDone();
          ask("__event:business_ready", "system"); // BE trả một action chạy 8 trang + đính kèm
        } else if (d.type === "pipeline_error") {
          pipeFail();
          ask("__event:pipeline_error", "system");
        }
      };
      ws.onerror = () => {
        reconnectStatusShown = true;
        setStatus("⚠️ Mất kết nối tiến trình giấy tờ, em đang tự nối lại…", true);
      };
      ws.onclose = () => {
        if (uploadWs === ws) uploadWs = null;
        scheduleReconnect();
      };
    }

    connect();
  }

  // ── Đính kèm tự động (Bước 6b — docs/06 §3.3) ──
  // Lấy file từ PHIÊN upload (đúng THỨ TỰ như pipeline đã thấy — fileIndex khớp),
  // chuyển thành dataUrl rồi giao engine attach-core thao tác DOM.
  async function fetchSessionFilesAsPayload(sid) {
    const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${sid}`);
    if (!res.ok) throw new Error(`Không đọc được phiên giấy tờ (HTTP ${res.status}).`);
    const sess = await res.json();
    const out = [];
    for (const f of sess.files || []) {
      const fr = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${sid}/files/${f.fid}`);
      if (!fr.ok) throw new Error(`Không tải được tệp ${f.name}.`);
      const blob = await fr.blob();
      const dataUrl = await new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result);
        r.onerror = reject;
        r.readAsDataURL(blob);
      });
      out.push({ name: f.name, type: blob.type || "image/jpeg", dataUrl });
    }
    return out;
  }

  // Dựng payload theo hợp đồng BE: sourceSegments trích đúng trang; sourceFileIndexes là
  // contract legacy gộp nguyên file. Tách trang lỗi phải dừng, không đính cả PDF hỗn hợp.
  async function preparePdfPayload(files, attachments) {
    if (!window.PdfConvert || !window.PDFLib) {
      const requiresPageSplit = (attachments || []).some((item) =>
        Array.isArray(item?.sourceSegments) && item.sourceSegments.length
      );
      if (requiresPageSplit) {
        throw new Error("Thiếu bộ xử lý PDF để tách đúng các giấy tờ trong file.");
      }
      return { files, attachments };
    }
    const outFiles = [];
    const outAtts = [];
    for (const item of attachments || []) {
      const segments = Array.isArray(item.sourceSegments) && item.sourceSegments.length
        ? item.sourceSegments
        : null;
      const src = Array.isArray(item.sourceFileIndexes) && item.sourceFileIndexes.length
        ? item.sourceFileIndexes : [item.fileIndex];
      const sources = src.map((i) => files[i]).filter(Boolean);
      if (!segments && !sources.length) continue;
      let file = segments ? files[Number(segments[0]?.fileIndex)] : sources[0];
      if (segments) {
        const composed = await PdfConvert.composeSegmentsToPdf(
          files,
          segments,
          item.documentName || file?.name || "tai-lieu"
        );
        file = { ...(file || {}), ...composed };
      } else {
        try {
          if (sources.length > 1) {
            const merged = await PdfConvert.mergeToPdf(sources, item.documentName || sources[0].name);
            file = { ...sources[0], ...merged };
          } else if (file.dataUrl && PdfConvert.isImage(file.type, file.name)) {
            const pdf = await PdfConvert.imageToPdf(file.dataUrl, file.name, file.type);
            file = { ...file, ...pdf };
          }
        } catch (e) {
          console.warn("[TLND] Chuyển/gộp PDF legacy thất bại, giữ file gốc:", file.name, e);
        }
      }
      const newIndex = outFiles.length;
      outFiles.push(file);
      const rewritten = { ...item, fileIndex: newIndex, sourceFileIndexes: [newIndex] };
      delete rewritten.sourceSegments;
      outAtts.push(rewritten);
    }
    return { files: outFiles, attachments: outAtts };
  }

  const SPLIT_ATTACH_PROCEDURES = new Set(["chung-thuc-ban-sao", "chung-thuc-chu-ky"]);

  function supportsSplitAttach(procedure) {
    return SPLIT_ATTACH_PROCEDURES.has(String(procedure || ""));
  }

  function planItemForSplitFile(attachments, originalIndex, file, bundleIndex = 0) {
    const item = (attachments || []).find((entry) => entry?.fileIndex === originalIndex)
      || (attachments || []).find((entry) =>
        Array.isArray(entry?.sourceFileIndexes) && entry.sourceFileIndexes.includes(originalIndex))
      || {};
    return {
      ...item,
      fileIndex: bundleIndex,
      sourceFileIndexes: [bundleIndex],
      fileName: file?.name || item.fileName,
      documentName: item.documentName || file?.name,
      detectedType: item.detectedType || item.documentName || file?.name,
    };
  }

  function buildCopyCertificationSplitBundles(files, attachments) {
    const bundles = [];
    for (let index = 0; index < (attachments || []).length; index++) {
      const item = attachments[index] || {};
      const file = Number.isInteger(item.fileIndex) ? files[item.fileIndex] : files[index];
      if (!file) continue;
      bundles.push({
        files: [file],
        attachments: [{
          ...item,
          fileIndex: 0,
          sourceFileIndexes: [0],
          fileName: file.name || item.fileName,
          documentName: item.documentName || file.name,
        }],
      });
    }
    return bundles;
  }

  function isSignatureIdentityPlanItem(item) {
    if (item?.bundleRole === "identity") return true;
    if (item?.bundleRole === "signature_document") return false;
    const normalize = (value) => String(value || "").normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    const values = [normalize(item?.detectedType), normalize(item?.documentName)];
    const exact = new Set([
      "can cuoc", "can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "cmnd",
      "ho chieu", "passport", "giay chung nhan can cuoc", "giay to tuy than",
    ]);
    const component = normalize(item?.componentName);
    return Number(item?.componentIndex) === 2 ||
      values.some((value) => exact.has(value) || value.startsWith("ho chieu ") || value.startsWith("passport ")) ||
      ["giay to tuy than", "can cuoc dien tu", "the can cuoc", "ho chieu"]
        .some((marker) => component.includes(marker));
  }

  // Chứng thực chữ ký: mỗi hồ sơ có đúng một văn bản STT1. Plan mới dùng bundleId để identity
  // matched đi đúng người ký và identity shared chỉ xuất hiện ở bundle đầu. Contract cũ chỉ được
  // fallback khi có tối đa một identity dùng chung.
  async function buildSignatureSplitBundles(files, attachments) {
    const entries = files.map((file, index) => ({
      file,
      planItem: planItemForSplitFile(attachments, index, file),
    }));
    const identityEntries = entries.filter((entry) => isSignatureIdentityPlanItem(entry.planItem));
    const documentEntries = entries.filter((entry) => !isSignatureIdentityPlanItem(entry.planItem));
    if (!documentEntries.length) {
      return { error: "Không tìm thấy giấy tờ, văn bản cần chứng thực chữ ký để đính vào STT1." };
    }

    const hasBundleContract = entries.some((entry) =>
      entry.planItem?.bundleId || entry.planItem?.bundleRole || entry.planItem?.identityScope);
    if (hasBundleContract) {
      const invalid = entries.find((entry) =>
        !entry.planItem?.bundleId ||
        !["signature_document", "identity"].includes(entry.planItem?.bundleRole));
      if (invalid) {
        return {
          error: `Kế hoạch nhiều hồ sơ thiếu quan hệ bundle cho ${invalid.file?.name || "một tệp"}.`,
        };
      }

      const bundleOrder = [];
      const grouped = new Map();
      for (const entry of entries) {
        const bundleId = String(entry.planItem.bundleId);
        if (!grouped.has(bundleId)) grouped.set(bundleId, []);
        grouped.get(bundleId).push(entry);
        if (entry.planItem.bundleRole === "signature_document" && !bundleOrder.includes(bundleId)) {
          bundleOrder.push(bundleId);
        }
      }
      if (bundleOrder.length !== grouped.size) {
        return { error: "Có bundle giấy tờ tùy thân nhưng thiếu văn bản cần chứng thực chữ ký." };
      }

      const bundles = [];
      for (const bundleId of bundleOrder) {
        const group = grouped.get(bundleId) || [];
        const documents = group.filter((entry) => entry.planItem.bundleRole === "signature_document");
        const identities = group.filter((entry) => entry.planItem.bundleRole === "identity");
        if (documents.length !== 1) {
          return { error: `Bundle ${bundleId} phải có đúng một văn bản cần chứng thực chữ ký.` };
        }
        if (identities.length > 1) {
          return { error: `Bundle ${bundleId} có nhiều nhóm giấy tờ tùy thân chưa được backend gộp.` };
        }

        const ordered = [...documents, ...identities];
        const bundleFiles = ordered.map((entry) => entry.file);
        const bundleAttachments = ordered.map((entry, bundleIndex) => ({
          ...entry.planItem,
          fileIndex: bundleIndex,
          sourceFileIndexes: [bundleIndex],
          fileName: entry.file?.name || entry.planItem.fileName,
          documentName: entry.planItem.documentName || entry.file?.name,
          target: "existing",
          componentIndex: entry.planItem.bundleRole === "identity" ? 2 : 1,
          needsAddComponent: false,
          appendOnOccupied: false,
        }));
        bundles.push({ files: bundleFiles, attachments: bundleAttachments });
      }
      return { bundles };
    }

    if (identityEntries.length > 1) {
      return { error: "Backend chưa trả quan hệ ghép hồ sơ cho nhiều giấy tờ tùy thân." };
    }

    let sharedIdentityFile = null;
    let sharedIdentityPlan = null;
    if (identityEntries.length) {
      sharedIdentityFile = identityEntries[0].file;
      sharedIdentityPlan = identityEntries[0].planItem;
    }

    return {
      bundles: documentEntries.map((entry, bundleIndex) => {
        const bundleFiles = [entry.file];
        const bundleAttachments = [{
          ...entry.planItem,
          fileIndex: 0,
          sourceFileIndexes: [0],
          fileName: entry.file?.name || entry.planItem.fileName,
          documentName: entry.planItem.documentName || entry.file?.name,
        }];
        if (bundleIndex === 0 && sharedIdentityFile && sharedIdentityPlan) {
          bundleFiles.push(sharedIdentityFile);
          bundleAttachments.push({
            ...sharedIdentityPlan,
            fileIndex: 1,
            sourceFileIndexes: [1],
            fileName: sharedIdentityFile.name || sharedIdentityPlan.fileName,
            target: "existing",
            componentIndex: 2,
            needsAddComponent: false,
            appendOnOccupied: false,
          });
        }
        return { files: bundleFiles, attachments: bundleAttachments };
      }),
    };
  }

  function splitQueueReport(status, dispatchId = "") {
    const errors = (status?.results || [])
      .filter((item) => !item?.ok)
      .map((item) => `Hồ sơ ${item.ordinal || "?"}: ${item.error || item.code || "đính kèm thất bại"}`);
    return {
      attached: Number(status?.succeeded) || 0,
      errors,
      mode: "split",
      queueId: status?.queueId || "",
      dossiersTotal: Number(status?.total) || 0,
      dossiersSucceeded: Number(status?.succeeded) || 0,
      dossiersFailed: Number(status?.failed) || 0,
      ...(dispatchId ? { dispatch_id: dispatchId } : {}),
    };
  }

  async function sendAttachLeaseSignal(eventName, dispatchId) {
    if (!dispatchId || !api.conversationId) return false;
    try {
      // Gọi thẳng API vì ask() đang busy trong lúc thi hành action. Reply của ACK/heartbeat
      // luôn rỗng; không render và không chen vào lịch sử hội thoại.
      await api.ask(`__event:${eventName}:${JSON.stringify({ dispatch_id: dispatchId })}`, {
        source: "system",
      });
      return true;
    } catch (error) {
      console.warn(`[TLND-AttachLease] ${eventName} thất bại`, error);
      return false;
    }
  }

  let activeSplitMonitor = null;
  async function monitorSplitQueue(queueId, totalHint = 0, dispatchId = "") {
    if (!queueId) return;
    if (activeSplitMonitor?.queueId === queueId) {
      // Plan được phát lại sau reload/mất ACK: tiếp quản lease mới nhưng không tạo vòng poll thứ hai.
      if (dispatchId) activeSplitMonitor.dispatchId = dispatchId;
      return;
    }
    const monitor = { queueId, dispatchId };
    activeSplitMonitor = monitor;
    const deadline = Date.now() + 30 * 60 * 1000;
    let missingCount = 0;
    let nextHeartbeatAt = 0;
    try {
      for (;;) {
        if (monitor.dispatchId && Date.now() >= nextHeartbeatAt) {
          await sendAttachLeaseSignal("attach_heartbeat", monitor.dispatchId);
          nextHeartbeatAt = Date.now() + 10000;
        }
        const status = await sendToBackground({ action: "getSplitAttachQueueStatus", queueId });
        if (status?.status === "done") {
          markActivity();
          setStatus("");
          // Chỉ báo backend sau khi TOÀN BỘ tab terminal; đây là điểm khác với popup auto-fill.
          const acknowledged = await ask(
            `__action:attach_report:${JSON.stringify(splitQueueReport(status, monitor.dispatchId))}`, "system"
          );
          if (!acknowledged) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            continue; // mạng lỗi: giữ marker + retry, không làm mất báo cáo terminal
          }
          await writeActiveSplit(null);
          return;
        }
        if (status?.status === "running") {
          markActivity(); // hàng đợi đang làm việc thật → không timeout giữa nhiều hồ sơ
          missingCount = 0;
          const ordinal = status.activeOrdinal || Math.min((status.completed || 0) + 1, status.total || 1);
          setStatus(`📎 Đang đính kèm hồ sơ ${ordinal}/${status.total || "?"}…`);
        } else if (!status?.status) {
          missingCount += 1;
        }
        if (Date.now() > deadline || missingCount >= 10) {
          setStatus("");
          const acknowledged = await ask(`__action:attach_report:${JSON.stringify({
            attached: 0,
            errors: ["Không còn đọc được trạng thái hàng đợi tách hồ sơ."],
            mode: "split",
            queueId,
            dossiersTotal: totalHint,
            dossiersSucceeded: 0,
            dossiersFailed: totalHint,
            ...(monitor.dispatchId ? { dispatch_id: monitor.dispatchId } : {}),
          })}`, "system");
          if (!acknowledged) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            continue;
          }
          await writeActiveSplit(null);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1200));
      }
    } finally {
      if (activeSplitMonitor === monitor) activeSplitMonitor = null;
    }
  }

  async function runSplitAttachPlan(a, files, attachments) {
    const built = a.procedure === "chung-thuc-chu-ky"
      ? await buildSignatureSplitBundles(files, attachments)
      : { bundles: buildCopyCertificationSplitBundles(files, attachments) };
    if (built.error) return { report: { attached: 0, errors: [built.error], mode: "split" } };
    const bundles = built.bundles || [];
    if (!bundles.length) return { report: { attached: 0, errors: ["Không có tài liệu để tách hồ sơ."], mode: "split" } };

    const prepared = await sendToBackground({ action: "prepareSplitAttachQueue" });
    if (prepared?.error) return { report: { attached: 0, errors: [prepared.error], mode: "split" } };
    const urlRes = await sendToContent({ action: "getDossierUrl" });
    if (!urlRes?.url) {
      return { report: { attached: 0,
        errors: [urlRes?.error || "Không lấy được URL để mở hồ sơ mới."], mode: "split" } };
    }

    const queueId = `split-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
    const first = bundles[0];
    const rest = bundles.slice(1);
    setStatus(`📎 Đang đính kèm hồ sơ 1/${bundles.length}…`);
    const firstRes = await sendToContent({
      action: "attachFilesByPlan",
      files: first.files,
      attachments: first.attachments,
      procedure: a.procedure || "",
      mode: "split",
    });

    const reloadable = new Set([
      "wallet-stale-modal", "wallet-modal-not-opened", "wallet-device-upload-not-opened",
    ]);
    const needsRecovery = !!firstRes?.error && reloadable.has(String(firstRes?.code || ""));
    let waitForTabId = null;
    const initialResults = [];
    if (needsRecovery) {
      waitForTabId = Number(TAB_ID) || null;
      const staged = await sendToBackground({
        action: "stageDossierTabAttach",
        queueId,
        tabId: waitForTabId,
        files: first.files,
        attachments: first.attachments,
        procedure: a.procedure || "",
        recoveryCode: firstRes.code,
      });
      if (staged?.error) {
        return { report: { attached: 0, errors: [staged.error], mode: "split",
          dossiersTotal: bundles.length, dossiersSucceeded: 0, dossiersFailed: bundles.length } };
      }
    } else {
      initialResults.push({
        ok: !!firstRes?.ok && !firstRes?.error,
        ordinal: 1,
        code: firstRes?.code || null,
        error: firstRes?.error || null,
      });
    }

    // Một tài liệu, thao tác trực tiếp đã terminal → không cần dựng queue.
    if (!rest.length && !needsRecovery) {
      const ok = initialResults[0]?.ok;
      return { report: {
        attached: ok ? 1 : 0,
        errors: ok ? [] : [initialResults[0]?.error || "Đính kèm thất bại."],
        mode: "split",
        dossiersTotal: 1,
        dossiersSucceeded: ok ? 1 : 0,
        dossiersFailed: ok ? 0 : 1,
      } };
    }

    const items = rest.map((bundle, index) => ({
      ordinal: index + 2,
      url: urlRes.url,
      files: bundle.files,
      attachments: bundle.attachments,
      procedure: a.procedure || "",
    }));
    await chrome.storage.local.set({ [SPLIT_STAGE_KEY]: { items, stagedAt: Date.now() } });
    const started = await sendToBackground({
      action: "startSplitAttachQueue",
      queueId,
      total: bundles.length,
      waitForTabId,
      initialResults,
      itemsStorageKey: SPLIT_STAGE_KEY,
    });
    try { await chrome.storage.local.remove(SPLIT_STAGE_KEY); } catch (_) { /* background cũng dọn */ }
    if (started?.error) return { report: { attached: 0, errors: [started.error], mode: "split" } };

    await writeActiveSplit({
      queueId, total: bundles.length, ts: Date.now(), dispatch_id: a.dispatch_id || "",
    });
    monitorSplitQueue(queueId, bundles.length, a.dispatch_id || ""); // chạy nền, giữ lease qua nhiều tab
    if (needsRecovery) {
      const reload = await sendToBackground({ action: "reloadDossierTabAttach", tabId: waitForTabId });
      if (reload?.error) console.warn("[TLND-Split] Không reload được tab đầu:", reload.error);
    }
    return { queued: true, queueId };
  }

  async function runAttachPlan(a) {
    const dispatchId = String(a.dispatch_id || "");
    let heartbeatTimer = null;
    let heartbeatPromise = Promise.resolve();
    try {
      await sendAttachLeaseSignal("attach_started", dispatchId);
      // Wizard hồ sơ: trang còn ở bước kê khai (chưa sang "Thành phần hồ sơ") mà chạy
      // engine sẽ ra "0 tệp" vô nghĩa → báo BE dặn người dân chuyển bước, watcher thấy
      // đúng bước sẽ tự đính lại. Trang không phải wizard (wizardStep=0) chạy như thường.
      const pre = await sendToContent({ action: "getPageContext" });
      if (pre?.ok && pre.wizardStep && pre.wizardStep !== 3) {
        ask(`__event:attach_blocked:${JSON.stringify({
          wizardStep: pre.wizardStep, ...(dispatchId ? { dispatch_id: dispatchId } : {}),
        })}`, "system");
        return;
      }
      // Đóng dấu chữ ký trang hiện tại — watcher không bắn lại page_status cho đúng
      // trang này nữa (tránh BE phát lệnh đính kèm lần 2 khi engine đang chạy).
      if (pre?.ok) {
        lastPageSig = `${pre.formKind}|${pre.wizardStep || 0}|${pre.declarationTarget ? 1 : 0}|${pre.infoModal ? 1 : 0}|${pre.agencyBlock ? 1 : 0}|${pre.attachmentTarget ? 1 : 0}`;
      }
      if (a.mode === "split" && supportsSplitAttach(a.procedure)) {
        const active = await readActiveSplit();
        if (active?.queueId) {
          // Reload/panel dựng lại có thể làm watcher phát lại attach_plan. Queue cũ vẫn là nguồn
          // chân lý; tuyệt đối không khởi động lượt thứ hai hoặc báo attached=0 đè kết quả đang chạy.
          setStatus(`📎 Đang tiếp tục hàng đợi ${active.total || "?"} hồ sơ…`);
          await writeActiveSplit({ ...active, dispatch_id: dispatchId || active.dispatch_id || "" });
          monitorSplitQueue(active.queueId, active.total || 0, dispatchId || active.dispatch_id || "");
          return;
        }
      }
      if (dispatchId) {
        heartbeatTimer = setInterval(() => {
          // Nối đuôi để heartbeat cuối không ghi Mongo muộn hơn attach_report.
          heartbeatPromise = heartbeatPromise.then(
            () => sendAttachLeaseSignal("attach_heartbeat", dispatchId),
          );
        }, 10000);
      }
      setStatus("📎 Đang đính kèm giấy tờ vào hồ sơ…");
      const raw = await fetchSessionFilesAsPayload(a.session_id || uploadSid);
      const { files, attachments } = await preparePdfPayload(raw, a.attachments);
      if (a.mode === "split" && supportsSplitAttach(a.procedure)) {
        const split = await runSplitAttachPlan(a, files, attachments);
        if (split?.queued) return;
        setStatus("");
        await heartbeatPromise;
        const splitReport = split?.report || {
          attached: 0, errors: ["Không khởi động được chế độ nhiều hồ sơ."], mode: "split",
        };
        ask(`__action:attach_report:${JSON.stringify({
          ...splitReport, ...(dispatchId ? { dispatch_id: dispatchId } : {}),
        })}`, "system");
        return;
      }
      const res = await sendToContent({
        action: "attachFilesByPlan",
        files,
        attachments,
        procedure: a.procedure || "",
        mode: a.mode || "merge",
      });
      setStatus("");
      const report = {
        attached: res?.attached ?? res?.results?.filter?.((x) => x?.ok)?.length ?? 0,
        // Lượt bổ sung gửi lại toàn bộ danh sách còn lại. attach-core tự bỏ qua những
        // file đã có trên cổng; báo số skip để backend không hiểu nhầm "0 file mới" là lỗi.
        skipped: Number(res?.skipped) || 0,
        errors: res?.error ? [res.error] : (res?.errors || []),
      };
      await heartbeatPromise;
      ask(`__action:attach_report:${JSON.stringify({
        ...report, mode: a.mode || "merge", ...(dispatchId ? { dispatch_id: dispatchId } : {}),
      })}`, "system");
    } catch (e) {
      setStatus("");
      await heartbeatPromise;
      ask(`__action:attach_report:${JSON.stringify({
        attached: 0,
        errors: [String(e?.message || e)],
        ...(dispatchId ? { dispatch_id: dispatchId } : {}),
      })}`, "system");
    } finally {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    }
  }

  // ── Thi hành actions từ BE (tuần tự) ──
  async function runActions(actions) {
    for (const a of actions) {
      if (a.type === "navigate" && a.url) {
        // Phải chờ storage ghi xong trước khi điều hướng; nếu iframe bị hủy sớm ở lượt đầu,
        // trang đích không thấy journey và sẽ chỉ hiện launcher.
        await saveJourney();
        setStatus("Đang chuyển trang…");
        await sendToContent({ action: "navigate", url: a.url });
      } else if (a.type === "verify_portal_state") {
        // ask() còn busy tới khi runActions kết thúc. Chạy ở lượt event-loop kế tiếp để
        // page_status không bị xếp hàng rồi chờ ngược chính request hiện tại.
        setTimeout(() => { void verifyPortalState(); }, 0);
      } else if (a.type === "prepare_business_registration") {
        setStatus("Đang mở trang kê khai Thành lập mới hộ kinh doanh…");
        const res = await sendToContent({ action: "prepareBusinessRegistration" });
        if (res?.error) {
          setStatus("", false);
          addBotMd(`⚠️ ${res.error}`);
        }
      } else if (a.type === "start_business_registration" && a.pages) {
        pipeDone();
        setStatus("Đang chuẩn bị 8 khối dữ liệu và giấy tờ đính kèm…");
        try {
          const rawFiles = a.session_id
            ? await fetchSessionFilesAsPayload(a.session_id || uploadSid) : [];
          const prepared = Array.isArray(a.attachments) && a.attachments.length
            ? await preparePdfPayload(rawFiles, a.attachments)
            : { files: [], attachments: [] };
          const res = await sendToContent({
            action: "startBusinessRegistration",
            pages: a.pages,
            files: prepared.files,
            attachments: prepared.attachments,
            businessDefaults: a.businessDefaults || null,
          });
          if (res?.error || !res?.ok) {
            setStatus("");
            const message = res?.error || "Trang HkdOnline chưa nhận lệnh tự điền.";
            ask(`__action:business_report:${JSON.stringify({
              ok: false, filledPages: 0, attached: 0, phase: "start", errors: [message],
            })}`, "system");
          }
        } catch (e) {
          setStatus("");
          ask(`__action:business_report:${JSON.stringify({
            ok: false, filledPages: 0, attached: 0, phase: "start",
            errors: [String(e?.message || e)],
          })}`, "system");
        }
      } else if (a.type === "fill_owner_fields" && Array.isArray(a.fields)) {
        pipeDone();
        setStatus("Đang điền thông tin chủ hồ sơ…");
        const traceId = `owner-${Date.now().toString(36)}`;
        console.log("[TLND-OwnerFill][sidebar] send", {
          traceId,
          fields: a.fields.map((field) => ({
            key: field.key || field.name || field.label || "?",
            comp: field.comp || "",
            hasValue: field.value !== null && field.value !== undefined && field.value !== "",
          })),
        });
        const res = await sendToContent({
          action: "fillOwnerFields", fields: a.fields, traceId,
        });
        console.log("[TLND-OwnerFill][sidebar] response", { traceId, res });
        setStatus("");
        if (res?.error) addBotMd(`⚠️ ${res.error}`);
        const noFrameError = !res ? "Không tìm thấy frame chứa các ô Thông tin chủ hồ sơ." : "";
        const report = {
          filled: res?.filled || 0,
          kept: res?.kept || 0,
          filledLabels: res?.filledLabels || [],
          keptLabels: res?.keptLabels || [],
          notFound: res?.notFound || [],
          errors: res?.errors || (res?.error ? [res.error] : (noFrameError ? [noFrameError] : [])),
        };
        ask(`__action:owner_fill_report:${JSON.stringify(report)}`, "system");
      } else if (a.type === "fill_fields" && Array.isArray(a.fields)) {
        pipeDone(); // dữ liệu về tới nơi — card tiến trình chốt ✓ dù WS có rớt
        setStatus("Đang điền form…");
        const res = await sendToContent({ action: "fillFields", fields: a.fields });
        setStatus("");
        if (res?.error) addBotMd(`⚠️ ${res.error}`);
        renderFillLegend(a.fields, res);
        // Báo BE kết quả điền THẬT (engine trả {filled, notFound, errors}) → bot sang rà soát.
        const report = { filled: res?.filled || 0, notFound: res?.notFound || [], errors: res?.errors || [] };
        ask(`__action:fill_report:${JSON.stringify(report)}`, "system");
      } else if (a.type === "select_agency") {
        // Cổng React mới: engine content/portal-dvc.js chọn Tỉnh/Xã + bấm "Đồng ý".
        // Không chụp trạng thái đăng nhập trước khi bấm: phiên trên DVCQG không chứng minh
        // cổng đích sẽ bỏ qua SSO. Watcher sẽ đọc chính trang đích để quyết định tiếp.
        setStatus("Đang chọn cơ quan thực hiện…");
        const res = await sendToContent({ action: "selectAgency", province: a.province, ward: a.ward });
        setStatus("");
        if (res?.ok) ask("__event:agency_selected", "system");
        else ask(`__event:agency_failed:${res?.error || "trang chưa sẵn sàng"}`, "system");
      } else if (a.type === "fill_agency_plan" && Array.isArray(a.plan)) {
        // Liên thông khai sinh: engine content/fill-angular.js điền hộ khối chọn cơ quan
        // (loại khai sinh, tỉnh/xã, trường hợp, tick "Cùng địa bàn") theo plan từ BE. KHÁC
        // select_agency (cổng React) — đây là Angular Material, KHÔNG tự bấm "Chuyển bước tiếp
        // theo" (để người dân rà lại). Chỉ báo BE khi LỖI (BE dặn chọn tay); thành công thì im.
        setStatus("Đang chọn cơ quan thực hiện…");
        const res = await sendToContent({ action: "fillAgencyByPlan", fields: a.plan });
        if (res?.ok) {
          setStatus("Đã chọn cơ quan xong ✓");
          setTimeout(() => setStatus(""), 4000);
        } else {
          setStatus("");
          ask(`__event:agency_failed:${res?.error || "trang chưa sẵn sàng"}`, "system");
        }
      } else if (a.type === "confirm_info_modal") {
        // Modal "Thông tin chung": chọn đúng Đối tượng thực hiện do backend cấp rồi mới
        // bấm Xác nhận. Quá 3 lần vẫn lỗi → nhờ công dân chọn tay, không submit sai lựa chọn.
        setStatus("Đang xác nhận thông tin chung của hồ sơ…");
        infoModalTries += 1;
        const res = await sendToContent({
          action: "confirmInfoModal",
          executionSubject: a.executionSubject || null,
        });
        await new Promise((r) => setTimeout(r, 1200));
        setStatus("");
        if (!res?.ok) {
          console.warn("[TLND-InfoModal][sidebar]", {
            attempt: infoModalTries,
            executionSubject: a.executionSubject || null,
            error: res?.error || "Không nhận được phản hồi từ trang",
          });
          if (infoModalTries <= 3) sendPageStatus();
          else {
            setStatus("⚠️ Công dân chọn Đối tượng thực hiện rồi bấm Xác nhận giúp em ạ.", true);
            setTimeout(() => setStatus(""), 5000);
          }
        } else if (infoModalTries <= 3) {
          sendPageStatus();
        } else {
          setStatus("⚠️ Công dân bấm nút Xác nhận trên trang giúp em ạ.", true);
          setTimeout(() => setStatus(""), 4000);
        }
      } else if (a.type === "attach_plan" && Array.isArray(a.attachments)) {
        await runAttachPlan(a);
      } else if (a.type === "show_qr") {
        setUploadSession(a.session_id);
        renderQrCard(a);
        subscribeUploadSession(a.session_id);
      } else if (a.type === "resume_upload_session" && a.session_id) {
        // Điều chỉnh giấy tờ: dựng ngay checklist của CHÍNH phiên cũ. QR/Scan chỉ là
        // lựa chọn thêm tệp; công dân có thể chỉ xóa rồi bấm hoàn tất điều chỉnh.
        const snapshotPromise = setUploadSession(a.session_id);
        subscribeUploadSession(a.session_id);
        await snapshotPromise;
      } else if (a.type === "pick_files" && a.session_id) {
        // Scan tại quầy: mở hộp chọn tệp của máy tính, kết quả đổ vào cùng phiên upload.
        setUploadSession(a.session_id);
        subscribeUploadSession(a.session_id);
        $fileInput?.click();
      } else if (a.type === "update_docs_done_chip" && a.label) {
        updateDocsDoneChipLabel(a.label, a.labelHmong);
      } else if (a.type === "collapse_after_tts") {
        /* Thu gọn panel sau khi đọc xong — đã xử lý trong renderReply (onDone của TTS). */
      } else if (a.type === "await_logout_choice") {
        // Cổng đã xác nhận nộp thành công: giữ trang nguyên trạng để cán bộ chọn giữ phiên
        // hay logout. Deadline được lưu theo tab để reload sidebar không làm mất bộ đếm.
        const delayMs = Math.max(0, Math.min(Number(a.delay_ms) || 120000, 10 * 60 * 1000));
        submittedReported = true;
        if (watcherTimer) { clearInterval(watcherTimer); watcherTimer = null; }
        // Event submitted trùng chỉ dùng để nối lại runtime đã mất; không được cộng lại
        // hai phút hoặc ghi đè fingerprint của đúng công dân đang chờ lựa chọn.
        if (["pending", "deciding"].includes(completionLogoutState?.phase)) continue;
        await beginCompletionLogoutWait(delayMs);
      } else if (a.type === "logout_citizen") {
        await resolveCompletionLogout("chosen_logout");
        returnToStart("completed");
      } else if (a.type === "continue_dossiers") {
        await resolveCompletionLogout("chosen_continue");
        returnToStart("continue");
      } else {
        console.warn("[TLND] action chưa hỗ trợ:", a.type);
      }
    }
  }

  // ── Header: thu gọn / đóng / TTS mute / cuộc trò chuyện mới ──
  // Màn login che header nên có cặp nút riêng — chung một hành vi thu gọn/đóng.
  const minimizePanel = () => window.parent.postMessage({ __tlnd: "minimizePanel" }, "*");
  const restorePanel = () => window.parent.postMessage({ __tlnd: "restorePanel" }, "*");
  const closePanel = () => window.parent.postMessage({ __tlnd: "closePanel" }, "*");
  document.getElementById("min-btn")?.addEventListener("click", minimizePanel);
  document.getElementById("close-btn")?.addEventListener("click", closePanel);
  document.getElementById("login-min-btn")?.addEventListener("click", minimizePanel);
  document.getElementById("login-close-btn")?.addEventListener("click", closePanel);

  function showStartScreen() {
    stopIdleTracking();
    document.body.classList.add("start-mode");
    $startScreen.hidden = false;
    $startBtn.disabled = false;
    $subtitle.textContent = "Sẵn sàng hỗ trợ công dân";
    if ($meterBar) $meterBar.style.width = "0";
  }

  function showChatScreen(activityAt = Date.now()) {
    document.body.classList.remove("start-mode");
    $startScreen.hidden = true;
    $subtitle.textContent = "Hỗ trợ thủ tục hành chính công";
    startIdleTracking(activityAt);
  }

  // Một đường dọn phiên dùng chung cho: hoàn thành, timeout và nút Trò chuyện mới.
  async function returnToStart(reason = "manual") {
    if (endingSession) return;
    if (busy) { pendingReturnReason = reason; return; }
    endingSession = true;
    try {
      const shouldClearCitizenCookies = reason === "completed";
      const shouldOpenProcedurePicker = reason === "continue";
      stopCompletionLogoutRuntime();
      completionLogoutState = null;
      await writeCompletionLogoutState(null);
      stopIdleTracking();
      stopVoice?.();
      stopReplyTts();
      setHandsfree?.(false);
      if (completionReturnTimer) { clearTimeout(completionReturnTimer); completionReturnTimer = null; }
      if (watcherTimer) { clearInterval(watcherTimer); watcherTimer = null; }
      stopUploadSubscription();
      // HkdOnline là WebForms full-postback và có state machine sống qua reload. Dọn nó
      // trước khi xóa conversation để phiên cũ không tự điền tiếp sau "Trò chuyện mới".
      await sendToContent({ action: "clearBusinessRegistrationState" });
      resetUploadFileListState();
      await api.deleteConversation();
      await clearJourney();
      await writeActiveSplit(null);
      $messages.innerHTML = "";
      pipeStop();
      $pipe = null; // node đã bị xoá cùng $messages — bỏ tham chiếu để card mới dựng lại được
      uploadSid = null;
      $docProgress = null;
      $docsDoneChip = null;
      docsReceived = false;
      lastState = "";
      lastReplyData = null;
      lastPageSig = "";
      fallbackChipShown = false;
      submittedReported = false;
      pendingReturnReason = "";
      if (shouldOpenProcedurePicker) {
        // “Không, nộp thêm hồ sơ” và “Trò chuyện mới” trong lúc chờ logout đều giữ
        // nguyên VNeID/trang thành công, nhưng phải mở ngay một conversation sạch để
        // cán bộ chọn thủ tục tiếp theo — không bắt quay qua màn giới thiệu.
        showChatScreen(Date.now());
        await ask("", "system");
        showProcedurePickerFromTop();
      } else {
        showStartScreen();
        // "Trò chuyện mới" thủ công: đưa CẢ trang web về trang chủ DVCQG cho lượt công dân
        // mới (không chỉ màn bắt đầu của sidebar). Đang ở trang chủ rồi (fresh=dvc-home)
        // thì thôi — navigate nữa chỉ reload thừa. Hết 10 phút (idle) giữ nguyên trang.
        if (reason === "manual" && !START_FRESH_ON_DVC_HOME) {
          const navigation = await sendToContent({ action: "navigate", url: DVC_HOME_URL });
          if (!navigation?.ok) {
            console.warn("[TLND] Không thể tự trở về trang chủ DVCQG", navigation);
            setStatus("⚠️ Không thể tự trở về trang chủ Dịch vụ công Quốc gia. Công dân vui lòng mở trang chủ giúp em ạ.", true);
          }
        }
      }
      if (shouldClearCitizenCookies) {
        const cookieCleanup = await sendToBackground({ action: "clearCitizenDvcCookies" });
        if (!cookieCleanup?.ok) {
          console.warn("[TLND] Chưa xóa hết phiên công dân", {
            found: Number(cookieCleanup?.found) || 0,
            removed: Number(cookieCleanup?.removed) || 0,
            failed: Number(cookieCleanup?.failed) || 0,
            failedQueries: Number(cookieCleanup?.failedQueries) || 0,
            storageCleared: cookieCleanup?.storageCleared === true,
            storageError: cookieCleanup?.storageError || "",
            failedTabs: Number(cookieCleanup?.failedTabs) || 0,
          });
          setStatus("⚠️ Chưa xóa hết phiên đăng nhập DVC/VNeID/Bộ Tư pháp. Cán bộ vui lòng kiểm tra trước khi tiếp nhận công dân tiếp theo.", true);
        } else {
          console.log(
            `[TLND] Đã xóa ${Number(cookieCleanup.removed) || 0} cookie và dữ liệu phiên web trên `
            + `${Number(cookieCleanup.clearedTabs) || 0} tab công dân.`,
          );
        }
        // Dọn xong phiên công dân rồi mới điều hướng CHÍNH tab đang làm thủ tục. Action
        // navigate đã phản hồi trước khi location.assign nên không làm đóng message channel.
        const navigation = await sendToContent({ action: "navigate", url: DVC_HOME_URL });
        if (!navigation?.ok) {
          console.warn("[TLND] Không thể tự trở về trang chủ DVCQG", navigation);
          setStatus("⚠️ Không thể tự trở về trang chủ Dịch vụ công Quốc gia. Công dân vui lòng mở trang chủ giúp em ạ.", true);
        }
      }
    } finally {
      endingSession = false;
    }
  }

  // 🔄 Trò chuyện mới: kết thúc phiên hiện tại và quay về màn hình bắt đầu.
  async function resetConversation() {
    if (busy) return;
    // Trong hai phút chờ logout, "Trò chuyện mới" đồng nghĩa giữ phiên VNeID để nộp tiếp.
    await returnToStart(completionLogoutState ? "continue" : "manual");
  }
  document.getElementById("reset-btn")?.addEventListener("click", resetConversation);

  $startBtn?.addEventListener("click", async () => {
    if (busy || endingSession) return;
    $startBtn.disabled = true;
    showChatScreen(Date.now());
    markActivity();
    await ask("", "system"); // chỉ lúc này mới tạo conversation và phát câu chào hiện tại
    showProcedurePickerFromTop();
    $startBtn.disabled = false;
  });

  const TTS_MUTED_KEY = "tlnd_tts_muted";
  const $ttsBtn = document.getElementById("tts-btn");
  let ttsMuted = false;
  function renderTtsBtn() {
    // Nút giờ có icon + nhãn (span) → chỉ đổi từng phần, không xoá cả textContent (mất nhãn).
    const ic = $ttsBtn.querySelector(".tbi");
    const lb = $ttsBtn.querySelector(".tbl");
    if (ic) ic.textContent = ttsMuted ? "🔇" : "🔊";
    if (lb) lb.textContent = ttsMuted ? "Bật tiếng" : "Âm thanh";
    const hm = $ttsBtn.querySelector(".tbl-hm");
    if (hm) hm.textContent = ttsMuted ? "Qhib suab" : "Lub suab";
    $ttsBtn.title = ttsMuted ? "Đang tắt đọc — bấm để bật" : "Đang bật đọc — bấm để tắt";
  }
  chrome.storage?.local.get([TTS_MUTED_KEY], (res) => { ttsMuted = !!res?.[TTS_MUTED_KEY]; renderTtsBtn(); });
  $ttsBtn?.addEventListener("click", () => {
    ttsMuted = !ttsMuted;
    renderTtsBtn();
    chrome.storage?.local.set({ [TTS_MUTED_KEY]: ttsMuted }, () => void chrome.runtime.lastError);
    if (ttsMuted) replyTtsInFlight = 0;
    window.__hccTTS?.setMuted?.(ttsMuted);
  });

  const soon = (msg) => () => { setStatus(msg); setTimeout(() => setStatus(""), 2500); };
  // Nút 📷: đang có phiên upload → mở lại hộp chọn tệp; chưa có → nhắc chọn cách gửi trong chat.
  document.getElementById("doc-btn")?.addEventListener("click", () => {
    if (uploadSid) $fileInput?.click();
    else soon("📷 Công dân chọn cách cung cấp giấy tờ trong hội thoại trước ạ.")();
  });

  // ══════════════ VOICE (Bước 4 — docs/04) ══════════════
  // Mic chạy trong OFFSCREEN document (iframe bị chặn getUserMedia) — sidebar chỉ gửi lệnh
  // asr-start/asr-stop qua background và nghe asr-event. Cơ chế port từ bản A Bảo (production).
  // tts mặc định TRUE: tin nhắn đầu (khôi phục phiên trên trang mới) thường đến TRƯỚC khi
  // fetch /voice/config xong — nuốt mất câu đọc. Server tắt TTS thì lệnh speak fail êm.
  let voiceCfg = { asr: false, tts: true };
  let voiceListening = false;
  let handsfree = false;
  let emptyTurns = 0; // rảnh tay: 2 lượt liên tiếp không nghe thấy gì → tự tắt
  let BASE_URL = "";
  const $micBtn = document.getElementById("mic-btn");
  const $hfBtn = document.getElementById("handsfree-btn");

  // ── Chế độ tiếng Mông (Hmong) — BE quyết định qua conv.lang; sidebar chỉ mirror ──
  // Switch CHỈ hiện khi: BE bật hmong (/voice/config.langs) VÀ tài khoản thuộc tỉnh Lai Châu.
  // Lựa chọn LƯU THEO MÁY QUẦY (chrome.storage tlnd_lang): phiên chat bị tạo mới (reload
  // trang chủ DVC, hết 10 phút, "Trò chuyện mới") thì tự khôi phục lặng lẽ — trước đây
  // trạng thái chỉ sống trong conversation nên reload là switch tắt.
  let voiceLang = "vi"; // "vi" | "hmong" — dùng cho ASR (asr-start) + fallback giọng đọc
  let voiceCfgLoaded = false; // chưa fetch xong /voice/config thì KHÔNG được reset switch
  let hmongRestoredConv = ""; // đã tự khôi phục cho conversation nào (chống gửi lặp)
  const LANG_KEY = "tlnd_lang";
  const $langBar = document.getElementById("lang-bar");
  const $langSwitch = document.getElementById("lang-switch");
  const $langState = document.getElementById("lang-state");

  function _foldVi(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/Đ/g, "D").replace(/đ/g, "d").toLowerCase().trim();
  }

  function syncLangUI(lang) {
    voiceLang = lang === "hmong" ? "hmong" : "vi";
    const on = voiceLang === "hmong";
    $langSwitch?.classList.toggle("on", on);
    $langSwitch?.setAttribute("aria-checked", on ? "true" : "false");
    if ($langState) $langState.textContent = on ? "Bật (Qhib)" : "Tắt (Tshum)";
  }

  function _hmongAllowed() {
    const tinh = _foldVi(window.tlndAuth?.user?.tinh);
    return (voiceCfg.langs || []).includes("hmong") && tinh.includes("lai chau");
  }

  function updateLangBar() {
    if (!$langBar) return;
    const allowed = _hmongAllowed();
    $langBar.hidden = !allowed;
    // Khung tĩnh (toolbar, placeholder, màn bắt đầu) song ngữ NGAY khi là quầy Lai Châu —
    // không đợi bật switch (mockup hiện song ngữ cả ở trạng thái "Tắt (Tshum)").
    document.body.classList.toggle("hmong-region", allowed);
    // Chỉ reset khi ĐÃ có config thật (đổi acc / server tắt hmong). renderAccount chạy
    // TRƯỚC khi fetch /voice/config xong — lúc đó langs còn rỗng, reset ở đây là tắt oan.
    if (voiceCfgLoaded && !allowed && voiceLang === "hmong") syncLangUI("vi");
  }

  $langSwitch?.addEventListener("click", () => {
    const next = voiceLang === "hmong" ? "vi" : "hmong";
    syncLangUI(next); // đổi UI ngay; BE xác nhận bằng reply (d.lang) ngay sau
    // Nhớ lựa chọn theo MÁY (không theo phiên) — reload/phiên mới vẫn giữ tiếng Mông.
    chrome.storage?.local.set({ [LANG_KEY]: next }, () => void chrome.runtime.lastError);
    hmongRestoredConv = api.conversationId || ""; // người dùng tự chọn → đừng auto-đổi lại
    ask(`__action:set_lang:${JSON.stringify({ lang: next })}`, "chip",
      next === "hmong" ? "Bật tiếng Mông (Lus Hmoob)" : "Tắt tiếng Mông", { preserveScroll: true });
  });

  // Mở sidebar: hiện đúng trạng thái đã lưu NGAY (không đợi reply đầu) — switch "Bật" liền
  // tay nếu máy đang ở chế độ tiếng Mông; conversation sẽ xác nhận/đồng bộ ngay sau đó.
  chrome.storage?.local.get([LANG_KEY], (res) => {
    if (!chrome.runtime.lastError && res?.[LANG_KEY] === "hmong") syncLangUI("hmong");
  });

  // Phiên mới sinh ra lang="vi" nhưng máy quầy đã lưu tiếng Mông → gửi set_lang IM LẶNG
  // (BE trả reply rỗng, không bubble/không đọc) để phiên khớp lại. Mỗi conversation thử 1 lần.
  function maybeRestoreHmongLang(d) {
    if (d?.lang !== "vi" || !_hmongAllowed()) return;
    const convId = api.conversationId || "";
    if (!convId || hmongRestoredConv === convId) return;
    chrome.storage?.local.get([LANG_KEY], (res) => {
      if (chrome.runtime.lastError) return;
      if (res?.[LANG_KEY] !== "hmong" || hmongRestoredConv === convId) return;
      hmongRestoredConv = convId;
      syncLangUI("hmong");
      ask(`__action:set_lang:${JSON.stringify({ lang: "hmong", silent: true })}`,
        "system", "", { preserveScroll: true });
    });
  }

  function setMicUI(listening, label) {
    voiceListening = listening;
    $micBtn?.classList.toggle("listening", listening);
    if (label) setStatus(label); else setStatus("");
  }

  async function startVoice() {
    // asr-stop phát event "stopped" bất đồng bộ; nếu đang ở Cài đặt, vòng rảnh tay
    // không được tự nối lại micro cho tới khi người dùng quay về hội thoại.
    if (document.body.classList.contains("settings-mode") || !voiceCfg.asr || voiceListening) return;
    stopReplyTts(); // đang đọc mà mở mic = ngắt lời (barge-in)
    setMicUI(true, "🎤 Đang kết nối…");
    const accessToken = await window.tlndAuth?.getAccessToken?.();
    // Trong lúc refresh, người dùng có thể dừng mic hoặc mở Cài đặt.
    if (!voiceListening || document.body.classList.contains("settings-mode")) return;
    if (!accessToken) {
      setMicUI(false, "⚠️ Phiên đăng nhập đã hết hạn.");
      return;
    }
    // voiceLang="hmong" → BE nối server ASR tiếng Mông (ws_asr đọc lang từ frame start).
    chrome.runtime.sendMessage({
      type: "asr-start",
      lang: voiceLang,
      baseUrl: BASE_URL,
      accessToken,
    },
      () => void chrome.runtime.lastError);
  }
  function stopVoice() {
    chrome.runtime.sendMessage({ type: "asr-stop" }, () => void chrome.runtime.lastError);
    setMicUI(false);
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === "businessProgress") {
      markActivity();
      setStatus(String(msg.text || "Đang xử lý hồ sơ hộ kinh doanh…"));
      return;
    }
    if (msg?.type === "businessDraftReady") {
      markActivity();
      setStatus("Đã tạo hồ sơ nháp hộ kinh doanh ✓");
      setTimeout(() => {
        setStatus("");
        sendPageStatus();
      }, 500);
      return;
    }
    if (msg?.type === "businessFlowCancelled") {
      markActivity();
      setStatus("Đã dừng tiến trình tự động kê khai.");
      setTimeout(() => setStatus(""), 3500);
      return;
    }
    if (msg?.type === "businessFlowFinished" && msg.report) {
      const report = msg.report;
      setStatus(
        report.ok
          ? "Đã tự điền và đính kèm xong ✓"
          : (report.cancelled ? "Đã dừng tiến trình tự động kê khai." : "⚠️ Luồng hộ kinh doanh đang dừng"),
        !report.ok && !report.cancelled
      );
      void (async () => {
        // iframe vừa được dựng lại sau postback có thể nhận runtime message trước khi bootChat
        // lấy conversation_id từ journey. Gửi sớm với conversationId=null sẽ tạo cuộc trò chuyện
        // mới và chèn màn chào/chọn thủ tục vào cuối phiên cũ.
        const restored = await waitForChatBoot();
        if (!restored) {
          setStatus("⚠️ Chưa khôi phục được cuộc trò chuyện để ghi nhận kết quả hồ sơ.", true);
          return;
        }
        markActivity();
        // Không dựa vào lastState: mode/phase từ RUN_KEY là dấu hiệu chắc chắn đây là kết quả
        // của lượt điền 8 khối cần đưa thành một tin nhắn trong chat.
        const isFullRun = report.mode === "full" || ["fill", "attach"].includes(report.phase);
        if (isFullRun) {
          const reply = await ask(`__action:business_report:${JSON.stringify(report)}`, "system");
          if (reply) sendToContent({ action: "ackBusinessResult" });
          else setTimeout(() => sendPageStatus(), 500);
        } else {
          // Lỗi ở chặng bootstrap (state guide_login): page_status mang result về backend
          // để hiện đúng hướng dẫn/thử lại, không biến thành kết quả điền hồ sơ.
          sendPageStatus();
        }
      })();
      return;
    }
    if (msg?.type !== "asr-event") return;
    if (msg.event === "state") {
      if (msg.state === "listening") setMicUI(true, "🎤 Đang lắng nghe… công dân nói đi ạ");
      else if (msg.state === "stopped") {
        // Server đóng mà không có final (không nghe thấy gì).
        setMicUI(false);
        if (handsfree) {
          emptyTurns += 1;
          if (emptyTurns >= 2) { setHandsfree(false); addBotMd("Em tạm tắt chế độ rảnh tay vì không nghe thấy công dân nói ạ. Bấm 🎙️ để bật lại nhé."); }
          else startVoice();
        }
      }
    } else if (msg.event === "partial") {
      $input.value = msg.text || "";
    } else if (msg.event === "final") {
      setMicUI(false);
      $input.value = "";
      const text = (msg.text || "").trim();
      if (text) {
        emptyTurns = 0;
        addUserText(text);
        ask(text, "voice");
      } else if (handsfree) {
        emptyTurns += 1;
        if (emptyTurns >= 2) setHandsfree(false);
        else startVoice();
      }
    } else if (msg.event === "error") {
      setMicUI(false);
      if (msg.name === "NotAllowedError" || msg.error === "not-allowed") {
        setStatus("⚠️ Chưa có quyền micro — đang mở trang cấp quyền…", true);
        window.open(chrome.runtime.getURL("permission.html"), "_blank");
      } else {
        setStatus(`⚠️ Lỗi giọng nói: ${msg.error || "không rõ"}`, true);
        setTimeout(() => setStatus(""), 4000);
      }
      if (handsfree) setHandsfree(false);
    }
  });

  $micBtn?.addEventListener("click", () => {
    if (!voiceCfg.asr) { soon("🎤 Máy chủ chưa bật giọng nói.")(); return; }
    if (voiceListening) stopVoice(); else startVoice();
  });

  function setHandsfree(on) {
    handsfree = on;
    emptyTurns = 0;
    $hfBtn?.classList.toggle("active", on);
    if (on) {
      // Bật rảnh tay ngay ở màn chào → đọc lại câu chào (công dân nghe + thấy) rồi tự mở mic nghe.
      if (lastState === "greet" && lastReplyData?.tts_text && voiceCfg.tts && !ttsMuted) {
        stopReplyTts();
        window.__hccTTS?.speak?.(lastReplyData.tts_text, lastReplyData.tts_lang || "vi", () => startVoice());
        return;
      }
      startVoice();
    } else { stopVoice(); stopReplyTts(); }
  }
  $hfBtn?.addEventListener("click", () => {
    if (!voiceCfg.asr) { soon("🎙️ Máy chủ chưa bật giọng nói.")(); return; }
    setHandsfree(!handsfree);
  });

  // Hỏi BE bật kênh voice nào + có tiếng Mông không. /voice/config YÊU CẦU đăng nhập
  // (backend gộp), nên chỉ gọi khi ĐÃ có token: gọi lúc chưa login → 401 → tưởng server tắt
  // voice → ẩn mic/Rảnh tay, không có langs → switch tiếng Mông ẩn, và không fetch lại sau
  // login → cài lần đầu phải reload trang mới hiện. Gọi lại sau MỖI lần đăng nhập thành công.
  let voiceCfgLoading = null;
  function loadVoiceConfig() {
    if (voiceCfgLoading) return voiceCfgLoading;
    voiceCfgLoading = (async () => {
      try {
        const res = await window.tlndAuth.authFetch(`${BASE_URL}/api/v1/voice/config`);
        if (res.ok) voiceCfg = await res.json();
      } catch (_) { /* BE chưa chạy → giữ tắt */ }
      voiceCfgLoaded = true; // từ giờ updateLangBar mới được phép reset switch tiếng Mông
      // Hiện/ẩn 2 CHIỀU: lần trước ẩn (server tắt/chưa login) mà giờ bật thì phải hiện lại.
      const asrOn = !!voiceCfg.asr;
      if ($micBtn) $micBtn.hidden = !asrOn;
      if ($hfBtn) $hfBtn.hidden = !asrOn;
      updateLangBar(); // config về xong mới biết server có tiếng Mông không
      window.__hccTTS?.setMuted?.(ttsMuted);
    })().finally(() => { voiceCfgLoading = null; });
    return voiceCfgLoading;
  }

  // Init voice: lấy base URL cho tts.js/asr; đã có token thì hỏi config ngay, chưa thì chờ login.
  (async () => {
    BASE_URL = await window.tlndBaseUrl();
    window.HCC_BASE_URL = BASE_URL; // services/tts.js đọc biến này để dựng URL /ws/tts
    const st = await window.tlndAuth.load();
    if (st?.access) await loadVoiceConfig();
    else window.__hccTTS?.setMuted?.(ttsMuted);
  })();

  // ── Nhập tay ──
  function submitText() {
    const text = ($input.value || "").trim();
    if (!text || busy) return;
    $input.value = "";
    addUserText(text);
    ask(text, "text");
  }
  $form?.addEventListener("submit", (e) => { e.preventDefault(); submitText(); });
  document.getElementById("send-btn")?.addEventListener("click", submitText);

  // ── Khởi động: journey còn hoạt động → khôi phục; không có/hết 10 phút → màn bắt đầu ──
  // Chỉ chạy SAU khi đã đăng nhập; token chết giữa chừng đăng nhập lại thì
  // KHÔNG boot lại (khung chat + phiên đang dở giữ nguyên phía sau màn login).
  async function bootChat() {
    if (chatBootStarted) return;
    chatBootStarted = true;
    try {
      const j = await loadJourney();
      let storedCompletionLogout = await readCompletionLogoutState();
      if (START_FRESH_ON_DVC_HOME) {
        // Quay về đúng trang chủ DVC = bắt đầu lượt công dân mới. Xóa cả conversation BE và
        // con trỏ journey của tab; KHÔNG xóa cookie DVC vì đây không phải tín hiệu nộp thành công.
        if (j?.conversation_id) {
          api.conversationId = j.conversation_id;
          await api.deleteConversation();
        }
        await clearJourney();
        await writeCompletionLogoutState(null);
        await writeActiveSplit(null);
        showStartScreen();
        console.log("[TLND] về trang chủ DVC → làm mới cuộc trò chuyện");
        return;
      }
      if (j?.conversation_id) {
        const activityAt = Number(j.last_activity_at || j.ts || 0);
        if (!activityAt || Date.now() - activityAt >= IDLE_TIMEOUT_MS) {
          api.conversationId = j.conversation_id;
          await api.deleteConversation();
          await clearJourney();
          await writeCompletionLogoutState(null);
          showStartScreen();
          console.log(`[TLND] phiên ${j.conversation_id} đã quá 10 phút → màn bắt đầu`);
          return;
        }
        const conv = await api.getConversation(j.conversation_id).catch(() => null);
        if (conv) {
          showChatScreen(activityAt);
          if (conv.lang) syncLangUI(conv.lang); // khôi phục chế độ tiếng Mông của phiên
          maybeRestoreHmongLang({ lang: conv.lang }); // phiên đang "vi" + máy lưu hmong → bật lại ngay
          const activeSplit = await readActiveSplit();
          if (activeSplit?.queueId) {
            // Tab đầu có thể vừa reload để phục hồi ví tài liệu; nối lại poll queue thay vì báo mất lượt.
            monitorSplitQueue(
              activeSplit.queueId, activeSplit.total || 0, activeSplit.dispatch_id || "",
            );
          }
          // Mở lại khi CÒN Ở MÀN CHÀO (chưa làm gì) → chào lại + ĐỌC (handsfree nghe được câu chào),
          // không khôi phục im lặng như các bước giữa chừng. last_reply màn chào đã gồm card nơi/thủ tục.
          if (conv.state === "greet") {
            lastState = "greet";
            if (conv.last_reply) renderReply(conv.last_reply, {});
            showProcedurePickerFromTop();
            setProgress(conv.progress);
            console.log(`[TLND] mở lại ở màn chào ${conv.conversation_id} → chào lại`);
            return;
          }
          // Bản cũ từng ghi lặp cùng lời hỏi đăng xuất vào history. Khi last_reply đang
          // là lựa chọn logout, bỏ toàn bộ bản sao trong history rồi dựng đúng một lần
          // từ last_reply để cả lời nhắn lẫn hai nút luôn đi cùng nhau.
          const restoresLogoutChoice = (conv.last_reply?.chips || []).some((chip) => [
            "__action:logout_citizen", "__action:continue_dossiers",
          ].includes(chip.send));
          const isLegacyLogoutPrompt = (text) => {
            const folded = String(text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
              .replace(/Đ/g, "D").replace(/đ/g, "d").toLowerCase();
            return folded.includes("hoan thanh viec nop ho so")
              && folded.includes("dang xuat tai khoan");
          };
          // Render lại đuôi hội thoại + reply cuối (chips/cards còn bấm được).
          (conv.history || []).slice(0, -1).forEach((h) => {
            if (restoresLogoutChoice && h.role === "bot" && isLegacyLogoutPrompt(h.text)) return;
            if (h.role === "user") addUserText(h.text);
            else addBotMd(h.text);
          });
          if (conv.last_reply) renderReply(conv.last_reply, { noTts: true });
          lastState = conv.state || lastState;
          if (conv.upload_session_id) {
            // Full navigation/F5 dựng lại sidebar và làm mất WebSocket cũ. Nối lại đúng
            // phiên để nhận tín hiệu mới; watcher attaching bên dưới sẽ lấy lại plan đã
            // hoàn tất trước khi kết nối lại.
            setUploadSession(conv.upload_session_id);
            subscribeUploadSession(conv.upload_session_id);
          }
          if (storedCompletionLogout?.conversationId
              && storedCompletionLogout.conversationId !== j.conversation_id) {
            await writeCompletionLogoutState(null);
            storedCompletionLogout = null;
          }
          const restoredCompletionLogout = storedCompletionLogout || j.completion_logout;
          if (restoredCompletionLogout) {
            // Sidebar có thể reload trong hai phút chờ lựa chọn. Nối lại đúng deadline cũ,
            // không cộng thêm hai phút và không phát lại event submitted.
            submittedReported = true;
            await beginCompletionLogoutWait(
              Math.max(0, Number(restoredCompletionLogout.deadline) - Date.now()),
              { ...restoredCompletionLogout, phase: "pending" },
            );
          } else {
            schedulePageWatcher();
          }
          setProgress(conv.progress);
          console.log(`[TLND] khôi phục phiên ${conv.conversation_id} state=${conv.state}`);
          // Đang ở chặng mở trang/đăng nhập → báo trạng thái trang cho BE quyết bước tiếp
          // (chọn cơ quan / nhắc QR / vào thẳng kê khai) — không bắt người dân bấm gì thêm.
          if (conv.state === "guide_login") {
            setTimeout(sendPageStatus, 500);
          }
          return;
        }
        await clearJourney();
      }
      await writeCompletionLogoutState(null);
      showStartScreen();
    } finally {
      // Runtime message kết quả HkdOnline chỉ được phép gọi backend sau mốc này; khi đó
      // api.conversationId đã được khôi phục hoặc boot đã kết luận không còn phiên hợp lệ.
      chatBootFinished = true;
    }
  }

  // ── Đăng nhập quầy (bắt buộc, mọi role) — api/auth.js giữ token, ở đây chỉ UI ──
  const $scrim = document.getElementById("login-scrim");
  const $loginForm = document.getElementById("login-form");
  const $loginUser = document.getElementById("login-user");
  const $loginPass = document.getElementById("login-pass");
  const $loginErr = document.getElementById("login-err");
  const $loginBtn = document.getElementById("login-btn");
  const $rememberLogin = document.getElementById("remember-login");
  const $forgetLoginBtn = document.getElementById("forget-login-btn");
  const $settingsBtn = document.getElementById("settings-btn");
  const $settingsScreen = document.getElementById("settings-screen");
  const $settingsBackBtn = document.getElementById("settings-back-btn");
  const $attachSplitSwitch = document.getElementById("attach-split-switch");
  const $settingsSaved = document.getElementById("settings-saved");
  const $accBtn = document.getElementById("acc-btn");
  const $accPop = document.getElementById("acc-pop");
  let settingsReturnScrollTop = 0;
  let settingsPreviousSubtitle = "";
  let settingsResumeHandsfree = false;
  let settingsSavedTimer = null;
  const CAN_REMEMBER_LOGIN = chrome.extension?.inIncognitoContext !== true;
  let rememberedLoginLoaded = false;
  let loginPrefillRun = 0;
  document.getElementById("login-avatar").innerHTML = BRAND_ICON(46, "brand-icon-login");

  function setLoginNotice(message, kind = "error") {
    if (!$loginErr) return;
    $loginErr.textContent = message || "";
    $loginErr.hidden = !message;
    $loginErr.classList.toggle("ok", kind === "ok");
  }

  function renderRememberedLoginState(hasSaved) {
    rememberedLoginLoaded = Boolean(hasSaved);
    $rememberLogin.checked = Boolean(hasSaved) && CAN_REMEMBER_LOGIN;
    $rememberLogin.disabled = !CAN_REMEMBER_LOGIN;
    $forgetLoginBtn.hidden = !hasSaved || !CAN_REMEMBER_LOGIN;
    if (!CAN_REMEMBER_LOGIN) {
      $rememberLogin.title = "Không thể ghi nhớ đăng nhập trong cửa sổ ẩn danh.";
    }
  }

  async function prefillLogin() {
    const run = ++loginPrefillRun;
    try {
      await window.RememberedLoginStore.clearLegacyPrefill();
      if (!CAN_REMEMBER_LOGIN) {
        if (run === loginPrefillRun) renderRememberedLoginState(false);
        return false;
      }
      const saved = await window.RememberedLoginStore.get();
      if (run !== loginPrefillRun) return false;
      renderRememberedLoginState(Boolean(saved));
      if (!saved) return false;
      if (!$loginUser.value) $loginUser.value = saved.username;
      if (!$loginPass.value) $loginPass.value = saved.password;
      return true;
    } catch (_) {
      if (run === loginPrefillRun) renderRememberedLoginState(false);
      return false;
    }
  }

  async function clearRememberedLogin({ clearFields = false, announce = false } = {}) {
    ++loginPrefillRun;
    try {
      await window.RememberedLoginStore.clear();
      renderRememberedLoginState(false);
      if (clearFields) {
        $loginUser.value = "";
        $loginPass.value = "";
        $loginUser.focus();
      }
      if (announce) setLoginNotice("Đã xóa thông tin đăng nhập được ghi nhớ.", "ok");
    } catch (error) {
      console.warn("[TLND-Login] Không xóa được thông tin đăng nhập đã nhớ:", error);
      if (announce) setLoginNotice("Chưa xóa được thông tin đã nhớ. Công dân thử lại giúp em ạ.");
    }
  }

  function renderAttachmentSettings() {
    $attachSplitSwitch?.classList.toggle("on", attachSplitDocuments);
    $attachSplitSwitch?.setAttribute("aria-checked", attachSplitDocuments ? "true" : "false");
  }

  function restoreAttachmentSettings() {
    return new Promise((resolve) => {
      chrome.storage.local.get([ATTACH_SPLIT_DOCUMENTS_KEY], (res) => {
        if (!chrome.runtime.lastError) {
          attachSplitDocuments = res?.[ATTACH_SPLIT_DOCUMENTS_KEY] === true;
        }
        renderAttachmentSettings();
        resolve();
      });
    });
  }

  function announceAttachmentSettingsSaved() {
    if (!$settingsSaved) return;
    $settingsSaved.textContent = "Đã lưu cài đặt.";
    if (settingsSavedTimer) clearTimeout(settingsSavedTimer);
    settingsSavedTimer = setTimeout(() => { $settingsSaved.textContent = ""; }, 1800);
  }

  function saveAttachmentSettings(value) {
    attachSplitDocuments = value === true;
    renderAttachmentSettings();
    chrome.storage.local.set(
      { [ATTACH_SPLIT_DOCUMENTS_KEY]: attachSplitDocuments },
      () => {
        if (chrome.runtime.lastError) {
          if ($settingsSaved) $settingsSaved.textContent = "Chưa lưu được cài đặt.";
          return;
        }
        announceAttachmentSettingsSaved();
      },
    );
  }

  function openSettingsScreen() {
    if (!$settingsScreen || !$scrim?.hidden) return;
    settingsReturnScrollTop = $messages.scrollTop;
    settingsPreviousSubtitle = $subtitle.textContent;
    settingsResumeHandsfree = handsfree;
    stopVoice();
    stopReplyTts();
    $accPop.hidden = true;
    $accBtn.classList.remove("active");
    $settingsScreen.hidden = false;
    document.body.classList.add("settings-mode");
    $settingsBtn.classList.add("active");
    $settingsBtn.setAttribute("aria-label", "Đóng cài đặt");
    $subtitle.textContent = "Cài đặt";
    markActivity();
    requestAnimationFrame(() => $settingsBackBtn?.focus());
  }

  function closeSettingsScreen({ resumeVoice = true, restoreFocus = true } = {}) {
    if (!$settingsScreen || $settingsScreen.hidden) return;
    $settingsScreen.hidden = true;
    document.body.classList.remove("settings-mode");
    $settingsBtn.classList.remove("active");
    $settingsBtn.setAttribute("aria-label", "Mở cài đặt");
    $subtitle.textContent = settingsPreviousSubtitle
      || (document.body.classList.contains("start-mode")
        ? "Sẵn sàng hỗ trợ công dân" : "Hỗ trợ thủ tục hành chính công");
    requestAnimationFrame(() => {
      $messages.scrollTop = settingsReturnScrollTop;
      if (restoreFocus) $settingsBtn?.focus();
    });
    if (resumeVoice && settingsResumeHandsfree && handsfree && voiceCfg.asr) startVoice();
    settingsResumeHandsfree = false;
  }

  $settingsBtn?.addEventListener("click", () => {
    if ($settingsScreen?.hidden) openSettingsScreen();
    else closeSettingsScreen();
  });
  $settingsBackBtn?.addEventListener("click", () => closeSettingsScreen());
  $attachSplitSwitch?.addEventListener("click", () => {
    markActivity();
    saveAttachmentSettings(!attachSplitDocuments);
  });
  chrome.storage?.onChanged?.addListener((changes, areaName) => {
    if (areaName !== "local" || !changes[ATTACH_SPLIT_DOCUMENTS_KEY]) return;
    attachSplitDocuments = changes[ATTACH_SPLIT_DOCUMENTS_KEY].newValue === true;
    renderAttachmentSettings();
  });

  function showLogin() {
    closeSettingsScreen({ resumeVoice: false, restoreFocus: false });
    $scrim.hidden = false;
    $settingsBtn.hidden = true;
    $accBtn.hidden = true;
    $accBtn.classList.remove("active");
    $accPop.hidden = true;
    stopVoice();
    stopReplyTts();
    setHandsfree(false);
    void prefillLogin().then((hasSaved) => {
      setTimeout(() => {
        if ($scrim.hidden) return;
        if (hasSaved && $loginUser.value && $loginPass.value) $loginBtn?.focus();
        else $loginUser?.focus();
      }, 60);
    });
  }

  function renderAccount() {
    const u = window.tlndAuth.user;
    updateLangBar(); // switch tiếng Mông gate theo tỉnh của tài khoản (Lai Châu)
    if (!u) { $settingsBtn.hidden = true; $accBtn.hidden = true; return; }
    $settingsBtn.hidden = false;
    $accBtn.hidden = false;
    document.getElementById("acc-name").textContent = u.name || u.username;
    const place = [u.xa, u.tinh].filter(Boolean).join(", ");
    document.getElementById("acc-sub").textContent = place || u.username;
  }

  $accBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = $accPop.hidden;
    $accPop.hidden = !willOpen;
    $accBtn.classList.toggle("active", willOpen);
  });
  document.addEventListener("click", (e) => {
    if (!$accPop.hidden && !$accPop.contains(e.target)) {
      $accPop.hidden = true;
      $accBtn.classList.remove("active");
    }
  });
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    await window.tlndAuth.logout();
    showLogin();
  });

  $loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = ($loginUser.value || "").trim();
    const p = $loginPass.value || "";
    if (!u || !p || $loginBtn.disabled) return;
    $loginBtn.disabled = true;
    setLoginNotice("");
    try {
      await window.tlndAuth.login(u, p);
      if (CAN_REMEMBER_LOGIN && $rememberLogin.checked) {
        try {
          await window.RememberedLoginStore.save(u, p);
          renderRememberedLoginState(true);
        } catch (error) {
          console.warn("[TLND-Login] Đăng nhập thành công nhưng không lưu được thông tin ghi nhớ:", error);
          renderRememberedLoginState(false);
        }
      } else {
        await clearRememberedLogin();
      }
      $loginPass.value = "";
      $scrim.hidden = true;
      renderAccount();
      // BASE_URL có thể chưa sẵn nếu người dùng đăng nhập cực nhanh — chờ init voice xong.
      if (!BASE_URL) BASE_URL = await window.tlndBaseUrl();
      window.HCC_BASE_URL = BASE_URL;
      void loadVoiceConfig(); // /voice/config cần token → mới gọi được từ lúc này
      bootChat();
    } catch (err) {
      const invalidRememberedLogin = rememberedLoginLoaded
        && (err?.status === 401 || err?.data?.error === "INVALID_CREDENTIALS");
      if (invalidRememberedLogin) {
        await clearRememberedLogin();
        $loginPass.value = "";
      }
      const message = err?.message || "Đăng nhập thất bại";
      setLoginNotice(invalidRememberedLogin
        ? `${message} Thông tin đã nhớ đã được xóa.`
        : message);
    } finally {
      $loginBtn.disabled = false;
    }
  });

  $rememberLogin?.addEventListener("change", async () => {
    if (!$rememberLogin.checked) await clearRememberedLogin();
  });

  $forgetLoginBtn?.addEventListener("click", async () => {
    await clearRememberedLogin({ clearFields: true, announce: true });
  });

  // authFetch hết đường refresh (401 lần 2) → bật lại màn đăng nhập, chat giữ nguyên.
  window.addEventListener("tlnd-auth-required", showLogin);

  (async () => {
    await restoreAttachmentSettings();
    const st = await window.tlndAuth.load();
    if (st?.access) { renderAccount(); bootChat(); }
    else showLogin();
  })();

  console.log(`[TLND] sidebar sẵn sàng — tabId=${TAB_ID}`);
})();
