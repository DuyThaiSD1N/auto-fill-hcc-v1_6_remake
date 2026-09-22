// sidebar.js — UI chat "Trợ lý nhân dân" (Bước 3: hội thoại server-driven thật).
// Vòng lặp: ask(message, source) → BE trả {display_md, tts_text, chips, cards, actions, progress}
// → render + THI HÀNH actions. FE không quyết flow — chips[0] luôn là bước tốt nhất do BE chọn.
(() => {
  "use strict";

  // ── Ngữ cảnh nhúng: content.js nạp sidebar.html?embedded=1&tabId=<id> ──
  const params = new URLSearchParams(location.search);
  const TAB_ID = params.get("tabId") || "";
  // embedded=0 → đang chạy trong KHUNG BÊN của trình duyệt, không có iframe cha.
  // Ba nút thu gọn/đóng gửi lệnh lên window.parent nên vô nghĩa ở đó (xem panelMode).
  const EMBEDDED = params.get("embedded") !== "0";
  const START_FRESH_ON_DVC_HOME = params.get("fresh") === "dvc-home";
  const DVC_HOME_URL = "https://dichvucong.gov.vn/";

  const $messages = document.getElementById("messages");
  // Nhãn phiên bản đọc từ manifest (bản cũ ghi cứng "v1.2 · 01/09/2026").
  try {
    const v = chrome.runtime.getManifest().version;
    const $rm = document.getElementById("release-meta");
    if ($rm && v) {
      const ngay = $rm.dataset.ngay || ""; // dd/mm/yyyy, ghi tay trong sidebar.html
      const [d, m, y] = ngay.split("/");
      $rm.textContent = ngay ? `v${v} · ${ngay}` : `v${v}`;
      $rm.setAttribute("aria-label", ngay
        ? `Phiên bản ${v}, phát hành ngày ${Number(d)} tháng ${Number(m)} năm ${y}`
        : `Phiên bản ${v}`);
    }
  } catch (_) { /* context mất — để trống còn hơn ghi sai */ }
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
  // phiên tự kết thúc giữa chừng là mất cả hồ sơ đang làm dở.
  const IDLE_TIMEOUT_MS = 20 * 60 * 1000;
  const IDLE_WARNING_MS = 30 * 1000;
  const IDLE_WARNING_TEXT = "⏳ Phiên sẽ tự kết thúc sau 30 giây nếu công dân không thao tác.";
  const ATTACH_SPLIT_DOCUMENTS_KEY = "tlnd_attach_split_documents";
  let attachSplitDocuments = false;
  // Cách đính kèm chứng thực (merge = 1 hồ sơ, split = mỗi tài liệu 1 hồ sơ) — chọn sẵn ở
  // màn Cài đặt thay cho câu hỏi giữa luồng; BE cũ không đọc key này thì vẫn hỏi chip như cũ.
  const ATTACH_MODE_KEY = "tlnd_attach_mode";
  let attachMode = "merge";
  // Ưu tiên Scan tại quầy: bật → bước tải giấy tự vào Scan (bỏ hỏi QR/Scan). Mặc định tắt.
  const PREFER_SCAN_KEY = "tlnd_prefer_scan";
  let preferScan = false;
  // Reply đang render có phải LIVE (không phải khôi phục phiên noTts) — để renderDocOptions chỉ
  // TỰ chọn Scan khi là lượt thật, khôi phục phiên thì không tự bấm lại.
  let renderingLiveReply = true;
  const CLIENT_CAPABILITIES = Object.freeze({
    attachmentEngineVersion: 2,
    supportsSourceSegments: true,
    supportsAttachmentContext: true,
    supportsPageBoundDocsComplete: true,
    supportsAttachActionLease: true,
    // Scan tại quầy tự chốt sau đợt chọn tệp — BE chỉ bật pick_files.auto_run (+ câu "em tự
    // xử lý luôn") khi client khai cờ này; extension cũ không khai → BE giữ luồng bấm tay.
    supportsScanAutoRun: true,
    // Hiểu card "rating" (đánh giá trải nghiệm trước đăng xuất). BE chỉ chèn bước đánh giá khi
    // client khai cờ này; extension cũ không khai → BE ra thẳng 2 nút đăng xuất như trước.
    supportsRating: true,
    // Hiểu nút chuyển bước / gửi hồ sơ do BE điều phối (guided_click_next, guided_submit) và
    // biết đọc giá trị ô chủ hồ sơ trước khi chuyển bước. BE chỉ bật luồng dẫn từng bước cho
    // client khai cờ này; bản trên chợ không khai → giữ nguyên câu "công dân tự bấm nút trang".
    supportsGuidedSteps: true,
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
  function showProcedurePicker() {
    // Màn chọn thủ tục: cuộn XUỐNG ĐÁY để người dân thấy đủ lưới ô + nút "NÓI" + thanh
    // "Xem tất cả" (các nút hành động nằm dưới cùng khối, cuộn lên đầu sẽ bị khuất).
    requestAnimationFrame(() => { $messages.scrollTop = $messages.scrollHeight; });
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

  // ── Hết phiên sau 20 phút không có hoạt động thật ──
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

  // ── Mốc "công dân bấm Gửi hồ sơ" ──
  // Luật nhận diện nút do BE gửi (action arm_submit_watch, nguồn registry.PORTAL_SUBMIT).
  // Cache lại vì chuyển trang sẽ dựng lại content script và mất luật; boot sau đó nạp lại
  // ngay, không phải chờ hết một hồ sơ mới có.
  const SUBMIT_RULES_KEY = "tlnd_submit_rules";

  async function armSubmitWatch(rules) {
    if (!rules || typeof rules !== "object") return;
    try { await chrome.storage.local.set({ [SUBMIT_RULES_KEY]: rules }); } catch (_) {}
    await sendToContent({ action: "setSubmitRules", rules });
  }

  async function restoreSubmitWatch() {
    try {
      const res = await chrome.storage.local.get([SUBMIT_RULES_KEY]);
      const rules = res?.[SUBMIT_RULES_KEY];
      if (rules) await sendToContent({ action: "setSubmitRules", rules });
    } catch (_) {}
  }

  // Content script bắn cú bấm về ĐÂY. Dùng chrome.runtime (không phải postMessage): trang web
  // không gửi được runtime message vào extension nên số liệu không bị trang giả mạo.
  chrome.runtime.onMessage.addListener((msg, sender) => {
    let fromThisDossier = false;
    if (msg?.__tlnd === "submitClicked") {
      // Cú bấm ngay trên tab của sidebar này.
      fromThisDossier = String(sender?.tab?.id || "") === String(TAB_ID);
    } else if (msg?.__tlnd === "submitClickedRelay") {
      // Cú bấm ở tab TÁCH (chứng thực nhiều hồ sơ) — background chuyển tiếp về đây vì tab tách
      // không có sidebar mang phiên trò chuyện. Mỗi lần là MỘT hồ sơ riêng trên cổng; BE ghi
      // thành sự kiện nộp riêng nên đếm đủ số hồ sơ thay vì chỉ tab đầu.
      fromThisDossier = String(msg.originTabId || "") === String(TAB_ID);
    }
    if (!fromThisDossier) return;                                 // tab khác → kệ
    if (!api.conversationId) return;                              // chưa có hồ sơ nào để chấm
    void ask(`__event:submit_clicked:${JSON.stringify({
      host: String(msg.host || ""), ref: String(msg.ref || ""),
    })}`, "system");
  });

  // Cổng trả lỗi khi đính kèm, engine đang hoãn tệp để thử lại → nói cho công dân biết đang chờ gì,
  // không thì họ tưởng máy treo. Câu cục bộ (không qua BE) vì phải báo NGAY giữa lượt đính kèm.
  // Chặn lặp 30s: chứng thực tách N tab mỗi tab tự báo một lần, không được đọc N lần liền.
  const ATTACH_RETRY_TEXT = "Dạ dịch vụ công đang lỗi, công dân chờ chút em đính kèm lại ạ.";
  let attachRetrySaidAt = 0;
  chrome.runtime.onMessage.addListener((msg, sender) => {
    let mine = false;
    if (msg?.__tlnd === "attachRetrying") mine = String(sender?.tab?.id || "") === String(TAB_ID);
    else if (msg?.__tlnd === "attachRetryingRelay") mine = String(msg.originTabId || "") === String(TAB_ID);
    if (!mine || Date.now() - attachRetrySaidAt < 30000) return;
    attachRetrySaidAt = Date.now();
    addBotMd(`⚠️ ${ATTACH_RETRY_TEXT}`);
    setStatus("📎 Dịch vụ công đang lỗi — đang đính kèm lại…");
    if (voiceCfg.tts && !ttsMuted) window.__hccTTS?.speak?.(ATTACH_RETRY_TEXT, "vi", () => {});
  });

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
        attachment_preferences: { splitDocuments: attachSplitDocuments, attachMode },
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
    renderingLiveReply = !opts?.noTts; // khôi phục phiên (noTts) → renderDocOptions không tự chọn Scan
    if (d.lang) syncLangUI(d.lang); // BE là nguồn sự thật về chế độ tiếng Mông
    maybeRestoreHmongLang(d); // phiên MỚI (lang=vi) + máy đã lưu tiếng Mông → khôi phục im lặng
    const prevState = lastState;
    if (d.state) { lastState = d.state; schedulePageWatcher(); }
    // Đã vào chặng làm việc (đã chốt thủ tục) → nối máy quét ở quầy để sẵn sàng bắt tệp. Gọi
    // lại nhiều lần không mở kết nối trùng (connectScanAgent tự canh). Bước chọn/đăng nhập/kết
    // thúc thì không cần theo dõi máy quét.
    if (["guide_login", "ask_doc_method", "qr_waiting", "collecting_docs"].includes(lastState)) {
      connectScanAgent();
    }
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
      // Mặc định chuyển bước là CẮT câu cũ, để bot không đọc hướng dẫn đã hết hiệu lực.
      // Hai trường hợp xếp hàng thay vì cắt:
      //   1. fill_report đến ngay sau action điền form — nó là phần tiếp nối của fields_ready,
      //      cắt là mất vế "Xong rồi ạ...".
      //   2. Quầy mà BE bật finishSentenceBeforeNext (Lai Châu): công dân nghe qua lời dịch
      //      tiếng Mông, mất nửa câu là mất hẳn ý.
      // Ngắt lời bằng micro (barge-in) thì VẪN cắt ở cả hai — người nói được ưu tiên.
      const queueThisReply = replyTtsInFlight > 0
        && ((prevState === "filling" && d.state === "reviewing")
          || voiceCfg?.finishSentenceBeforeNext === true);
      if (!queueThisReply) stopReplyTts();
      else console.debug("[TLND] xếp TTS sau câu đang đọc, không cắt ngang");
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
    // Nút "Kiểm tra lại trang hiện tại" đã bỏ khỏi UI (yêu cầu 22/09/2026). Lọc ở FE chứ
    // không gỡ ở backend: backend còn phải phục vụ bản extension cũ trên chợ đang dùng nút
    // này. Cơ chế verify_portal_state vẫn sống, chỉ không còn nút cho công dân bấm.
    chips = chips.filter((c) => c.send !== "__event:sso_success");
    if (!chips.length) return;
    // Chỉ được có MỘT nút chuyển bước sống trên màn hình. Nút cũ có thể còn sót do khôi phục
    // phiên dựng lại last_reply, hoặc do hai tab cùng phiên cùng báo trạng thái trang — bấm
    // nhầm nút của bước trước là đẩy cổng đi sai bước.
    if (chips.some((c) => c.cta)) {
      document.querySelectorAll(".chip.cta").forEach((el) => el.remove());
    }
    const wrap = document.createElement("div");
    const isLogoutChoice = chips.some((c) => [
      "__action:logout_citizen", "__action:continue_dossiers",
    ].includes(c.send));
    wrap.className = "chips" + (isLogoutChoice ? " logout-choice" : "");
    chips.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      // cta: nút chuyển bước/gửi hồ sơ — to tràn ngang, nổi bật vì đây là việc DUY NHẤT
      // công dân cần làm ở bước đó.
      b.className = "chip" + (c.solid ? " solid" : "") + (c.cta ? " cta" : "");
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
        // "Chọn thêm tệp từ máy": mở hộp chọn tệp NGAY trong cú bấm (Chrome chỉ cho mở hộp chọn tệp
        // khi còn trong thao tác người dùng — đợi BE trả lời rồi mới mở là hay bị chặn). Không qua BE:
        // lệnh pick_files của BE bỏ qua hộp chọn khi đã nối máy quét, nên trước đây bấm nút này
        // không có tác dụng gì. Nút dùng lại được nhiều lần → không khoá nhóm chip.
        if (c.send === "__action:pick_files_again" && uploadSid && $fileInput) {
          $fileInput.click();
          return;
        }
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
        // Nút chuyển bước: đọc giá trị các ô bắt buộc NGAY trên trang rồi mới gửi, để backend
        // chặn trước và gọi đúng tên ô còn thiếu thay vì để cổng nháy toast rồi thôi.
        if (c.send === "__action:guided_next") {
          void (async () => {
            const payload = { phase: c.phase || "" };
            if (c.collect === "ownerFields") {
              const res = await sendToContent({
                action: "readOwnerFields", fields: c.fields || [],
              });
              payload.ownerFields = res?.values || {};
            }
            await ask(`__action:guided_next:${JSON.stringify(payload)}`, "chip", c.label);
          })();
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
      || c.maeAgencyBlock
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
      // Trang "chọn nơi và loại" của cổng Bộ NN&MT — BE phát lệnh fill_mae_agency.
      maeAgencyBlock: !!c.maeAgencyBlock,
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

  // ── Luồng dẫn từng bước: bấm hộ nút của cổng ──
  // Hai hàm này CHẠY NGOÀI lượt ask() (runActions gọi qua setTimeout 0). Gọi ask() từ trong
  // runActions là tự khoá: cờ busy của lượt ngoài chưa tắt nên lượt mới chỉ xếp hàng chờ.
  async function runGuidedNext(phase, expect) {
    setStatus("Đang chuyển bước trên trang…");
    // Bấm và dò song song: engine content còn rình toast vài giây, chờ nó xong mới dò thì
    // trường hợp THÀNH CÔNG (đa số) cũng phải chờ đủ chừng ấy.
    const press = sendToContent({ action: "guidedClickNext" });
    // Bấm xong chưa chắc đã qua bước (cổng có thể chặn im lặng) → đối chiếu số bước thật
    // trên thanh bước, dùng chính bộ đọc mà watcher trang đang dùng.
    let wizardStep = 0;
    let moved = !expect;
    for (let i = 0; i < 12 && !moved; i++) {
      await new Promise((r) => setTimeout(r, 300));
      const ctx = await sendToContent({ action: "getPageContext" });
      wizardStep = Number(ctx?.wizardStep) || 0;
      if (wizardStep === expect) moved = true;
    }
    const res = moved ? null : await press; // chỉ cần lời cổng báo khi KHÔNG qua được bước
    setStatus("");
    await ask(`__action:guided_step_report:${JSON.stringify({
      phase, ok: moved, message: res?.message || "", wizardStep,
    })}`, "system");
    // Sang bước chủ hồ sơ → thành phần hồ sơ: đẩy trạng thái trang lên NGAY để bot hỏi cách
    // gửi giấy tờ liền, thay vì chờ tới nhịp watcher kế tiếp (3,5 giây).
    if (moved && phase === "owner") await verifyPortalState();
  }

  async function runGuidedSubmit() {
    setStatus("Đang gửi hồ sơ…");
    const res = await sendToContent({ action: "guidedSubmit" });
    setStatus("");
    // Nộp được hay không do chính cổng trả lời (màn xác nhận / event submitted). Ở đây chỉ
    // báo cú bấm có ăn không: không bấm được, hoặc cổng nháy toast báo thiếu.
    await ask(`__action:guided_submit_report:${JSON.stringify({
      ok: !!res?.clicked && !res?.message, message: res?.message || "",
    })}`, "system");
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
      const sig = `${ctx.formKind}|${ctx.wizardStep || 0}|${ctx.declarationTarget ? 1 : 0}|${ctx.infoModal ? 1 : 0}|${ctx.agencyBlock ? 1 : 0}|${ctx.attachmentTarget ? 1 : 0}|${ctx.vneidLoginCodePrompt ? 1 : 0}|${ctx.vneidDataSharingPrompt ? 1 : 0}|${ctx.vneidPasscodePrompt ? 1 : 0}|${ctx.businessStage || ""}|${ctx.businessActive ? 1 : 0}|${businessResultSig}|${ctx.maeAgencyBlock ? 1 : 0}`;
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
        // ~60s chưa tự nhận ra → tự đọc lại DOM một lần thay vì hiện nút cho công dân bấm
        // (nút "Kiểm tra lại trang hiện tại" đã bỏ khỏi UI, yêu cầu 22/09/2026).
        fallbackChipShown = true;
        void verifyPortalState();
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
    if (card.kind === "rating") return renderRatingCard(card);
    console.warn("[TLND] card chưa hỗ trợ:", card.kind);
  }

  // Card đánh giá trải nghiệm (mockup 5) — hiện sau khi nộp thành công, TRƯỚC 2 nút đăng xuất.
  // 2 bước làm TRỌN trong card: chọn 1/5 mức → hiện chip lý do (nhánh theo mức) + ô ý kiến +
  // nút NÓI (ASR). Gửi/Bỏ qua → 1 action về BE. Ẩn danh, không bắt buộc.
  const RATING_FACE_COLOR = { 5: "#12a06a", 4: "#5da76a", 3: "#c2941f", 2: "#c4702f", 1: "#bd3b2e" };
  function ratingFaceSvg(v) {
    const c = RATING_FACE_COLOR[v] || "#12a06a";
    const mouth = v === 5
      ? `<path d="M17 37 Q32 59 47 37 Z" fill="${c}"/>`
      : `<path d="${{ 4: "M21 41 Q32 51 43 41", 3: "M22 44 L42 44", 2: "M22 48 Q32 41 42 48", 1: "M19 51 Q32 37 45 51" }[v]}" stroke="${c}" stroke-width="3.8" stroke-linecap="round" fill="none"/>`;
    const eye = v === 5
      ? `<path d="M17 29 Q22.5 23 28 29 M36 29 Q41.5 23 47 29" stroke="${c}" stroke-width="3.4" stroke-linecap="round" fill="none"/>`
      : v <= 2
        ? `<path d="M18 26 L27 30 M46 26 L37 30" stroke="${c}" stroke-width="3.4" stroke-linecap="round" fill="none"/>`
        : `<circle cx="22.5" cy="28" r="3.6" fill="${c}"/><circle cx="41.5" cy="28" r="3.6" fill="${c}"/>`;
    return `<svg viewBox="0 0 64 64" aria-hidden="true">${eye}${mouth}</svg>`;
  }
  function renderRatingCard(card) {
    const scale = card.scale || [];
    const goodThreshold = card.goodThreshold || 4;
    const esc = window.escapeHtml;
    let level = null;
    const reasons = new Set();
    let note = "";
    let capturing = false;
    let thanked = false;
    let curReasons = [];

    const el = document.createElement("div");
    el.className = "rating-card";
    addNode(el);

    const syncNote = () => { const ta = el.querySelector(".rating-note"); if (ta) note = ta.value; };
    const stopCapture = () => {
      if (!capturing) return;
      capturing = false; ratingNoteSink = null;
      try { stopVoice(); } catch (_) { /* bỏ qua */ }
    };
    const finish = (action, label) => {
      stopCapture();
      // Đổi NGAY TRONG card sang trạng thái "cảm ơn" (không đẻ bong bóng echo/cảm ơn) rồi mới
      // gửi action. Card vẫn là 1 khối tự morph.
      thanked = true;
      draw();
      ask(action, "chip", label);
    };

    // Sau mỗi lần card ĐỔI nội dung, đưa phần mới vào tầm nhìn (cuộn xuống đáy khung chat) —
    // card nằm cuối trong lúc đánh giá nên cuộn đáy là thấy đúng nút vừa hiện.
    const scrollDown = () => requestAnimationFrame(() => {
      $messages.scrollTop = $messages.scrollHeight;
    });

    function draw() {
      // Trạng thái cuối: cảm ơn — thay TOÀN BỘ nội dung (thang mức đã biến mất).
      if (thanked) {
        el.innerHTML = `<div class="rating-thanks">
          <span class="rating-thanks-face">${ratingFaceSvg(level || 5)}</span>
          <div class="rating-thanks-tt">${esc(card.thanks || "Cảm ơn công dân đã đánh giá!")}</div>
          <div class="rating-thanks-sub">${esc(card.thanksSub || "")}</div></div>`;
        scrollDown();
        return;
      }
      // BƯỚC 1 — chọn mức (thái độ). Chưa chọn thì CHỈ hiện thang mức.
      if (level == null) {
        el.innerHTML = `
          <div class="rating-title">${esc(card.title || "")}</div>
          <div class="rating-sub">${esc(card.subtitle || "")}</div>
          <div class="rating-scale">
            ${scale.map((m) => `
              <button type="button" class="rating-opt" data-lv="${m.value}" style="--rc:${RATING_FACE_COLOR[m.value] || "#12a06a"}">
                <span class="rating-face">${ratingFaceSvg(m.value)}</span>
                <span class="rating-nm">${esc(m.label)}</span>
                <span class="rating-chk">✓</span></button>`).join("")}
          </div>
          <div class="rating-privacy">🔒 ${esc(card.privacy || "")}</div>
          <div class="rating-actions">
            <button type="button" class="rating-skip" data-skip="1">${esc(card.skipLabel || "Bỏ qua")}</button>
          </div>`;
        scrollDown();
        return;
      }
      // BƯỚC 2 — lý do. Thang mức BIẾN MẤT, chỉ còn tóm tắt mức đã chọn (+ Chọn lại) và phần lý do.
      const good = level >= goodThreshold;
      curReasons = good ? (card.reasonsGood || []) : (card.reasonsBad || []);
      const showMic = !!(voiceCfg && voiceCfg.asr);
      const picked = scale.find((s) => s.value === level);
      el.innerHTML = `
        <div class="rating-picked" style="--rc:${RATING_FACE_COLOR[level] || "#12a06a"}">
          <span class="rating-face">${ratingFaceSvg(level)}</span>
          <span class="rating-picked-nm">${esc(picked ? picked.label : "")}</span>
          <button type="button" class="rating-change" data-change="1">Chọn lại</button>
        </div>
        <div class="rating-reason-h">${esc(good ? (card.reasonPromptGood || "") : (card.reasonPromptBad || ""))}</div>
        <div class="rating-sub">${esc(card.reasonHint || "")}</div>
        <div class="rating-chips">
          ${curReasons.map((t, k) => `<button type="button" class="rating-chip${reasons.has(t) ? " sel" : ""}" data-rs="${k}">
            <span class="rating-bx">${reasons.has(t) ? "✓" : ""}</span><span>${esc(t)}</span></button>`).join("")}
        </div>
        <textarea class="rating-note" rows="2" placeholder="${esc(card.notePlaceholder || "")}">${esc(note)}</textarea>
        ${showMic ? `<button type="button" class="rating-mic${capturing ? " on" : ""}" data-mic="1">🎤 ${esc(capturing ? "Đang nghe… bấm để dừng" : (card.voiceHint || "Nói ý kiến"))}</button>` : ""}
        <div class="rating-privacy">🔒 ${esc(card.privacy || "")}</div>
        <div class="rating-actions">
          <button type="button" class="rating-skip" data-skip="1">${esc(card.skipLabel || "Bỏ qua")}</button>
          <button type="button" class="rating-submit" data-submit="1">${esc(card.submitLabel || "Gửi")} ➤</button>
        </div>`;
      scrollDown();
    }

    function toggleMic() {
      if (!voiceCfg || !voiceCfg.asr) return;
      if (capturing) { stopCapture(); draw(); return; }
      syncNote();
      capturing = true;
      ratingNoteSink = (text, isFinal) => {
        const ta = el.querySelector(".rating-note");
        if (!ta) return;
        if (isFinal) {
          note = (note ? `${note} ` : "") + text;
          ta.value = note;
          capturing = false; ratingNoteSink = null; draw();
        } else {
          ta.value = (note ? `${note} ` : "") + text; // xem trước phần đang nghe
        }
      };
      draw();
      startVoice();
    }

    // Chốt đánh giá đầy đủ (mức + lý do + ý kiến) — dùng cho cả nút Gửi và Bỏ-qua-ở-bước-2.
    const submitRating = () => {
      syncNote();
      const label = scale.find((s) => s.value === level)?.label || "Đã đánh giá";
      finish(`__action:rate:${JSON.stringify({ level, reasons: [...reasons], note: note.trim() })}`, `Đánh giá: ${label}`);
    };

    el.addEventListener("click", (e) => {
      const opt = e.target.closest("[data-lv]");
      if (opt) {
        level = Number(opt.getAttribute("data-lv")); reasons.clear(); draw();
        // LOG mức NGAY (bước 1), chạy nền — dù công dân bỏ dở bước 2 thì mức vẫn được ghi.
        // Gọi thẳng api.ask (không qua ask() UI) để không nháy typing / không kéo cuộn.
        void api.ask(`__action:rate_level:${JSON.stringify({ level })}`, {
          source: "chip", clientContext: { capabilities: CLIENT_CAPABILITIES },
        }).catch(() => {});
        return;
      }
      if (e.target.closest("[data-change]")) { // Chọn lại → về BƯỚC 1 (thang mức)
        stopCapture(); syncNote(); level = null; reasons.clear(); draw(); return;
      }
      const chip = e.target.closest("[data-rs]");
      if (chip) { const t = curReasons[Number(chip.getAttribute("data-rs"))]; if (t) { reasons.has(t) ? reasons.delete(t) : reasons.add(t); draw(); } return; }
      if (e.target.closest("[data-mic]")) { toggleMic(); return; }
      if (e.target.closest("[data-skip]")) {
        // Bước 2 (đã chọn mức) → Bỏ qua = chốt GIỮ mức, không lý do. Bước 1 → bỏ qua hẳn.
        if (level == null) finish("__action:rate_skip", "Bỏ qua đánh giá");
        else submitRating();
        return;
      }
      if (e.target.closest("[data-submit]")) submitRating();
    });
    el.addEventListener("input", (e) => { if (e.target.classList.contains("rating-note")) note = e.target.value; });

    draw();
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
      <span class="cbadge">🔒 Xác nhận trên Trợ lý nhân dân</span>
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

  // Bỏ dấu để lọc tìm kiếm (khớp cả khi gõ không dấu). Dùng chung cho sheet "tất cả thủ tục".
  function foldVi(s) {
    return String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d")
      .normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  // Chọn 1 thủ tục — dùng chung cho ô (tile) và dòng trong sheet.
  function pickProcedure(it) {
    addUserText(it.title, it.titleHmong);
    ask(`__action:pick_procedure:${JSON.stringify({ key: it.key })}`, "chip", it.title);
  }

  // Màn chọn thủ tục kiểu mockup: 8 ô "hay dùng" (grid) + thanh "Xem tất cả" mở sheet có ô
  // tìm kiếm. BE gắn frequent/frequentOrder; phần cấu hình (8 ô, khóa tỉnh) nằm ở registry BE
  // nên đổi về sau KHÔNG phải phát hành lại extension.
  function renderServiceList(card) {
    const all = card.items || [];
    if (!all.length) return;
    // Ô hay dùng: theo frequentOrder BE trả; nếu BE cũ chưa gắn frequent → lấy tối đa 8 đầu.
    let tiles = all.filter((it) => it.frequent)
      .sort((a, b) => (a.frequentOrder ?? 99) - (b.frequentOrder ?? 99));
    if (!tiles.length) tiles = all.slice(0, 8);

    const el = document.createElement("div");
    el.className = "svc-block";

    const grid = document.createElement("div");
    grid.className = "svc-grid";
    tiles.forEach((it) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tl";
      // Chế độ tiếng Mông: BE gắn titleHmong → dòng nghiêng dưới tên tiếng Việt (mockup).
      const hmongLine = it.titleHmong
        ? `<span class="tl-hm">${window.escapeHtml(it.titleHmong)}</span>` : "";
      b.innerHTML = `<span class="tl-ic">${window.escapeHtml(it.icon || "📄")}</span>
        <span class="tl-tn">${window.escapeHtml(it.title)}</span>${hmongLine}`;
      b.addEventListener("click", () => pickProcedure(it));
      grid.appendChild(b);
    });
    el.appendChild(grid);

    // Nút NÓI to, hiện ngay bước chọn thủ tục cho người dân dễ thấy (mockup). Dùng chung
    // hành vi với nút mic ở footer: bấm là bật/tắt nghe; server tắt ASR thì tự báo toast.
    const voiceBtn = document.createElement("button");
    voiceBtn.type = "button";
    voiceBtn.className = "svc-voice";
    voiceBtn.innerHTML = `<span class="svc-voice-ic">🎤</span>
      <span class="svc-voice-tx">Hoặc bấm vào đây rồi <b>NÓI</b> tên thủ tục</span>`;
    voiceBtn.addEventListener("click", () => { $micBtn?.click(); });
    el.appendChild(voiceBtn);

    // Thanh mở danh sách đầy đủ (có ô tìm kiếm) — chỉ hiện khi còn thủ tục ngoài các ô.
    if (all.length > tiles.length) {
      const bar = document.createElement("button");
      bar.type = "button";
      bar.className = "allbar";
      bar.innerHTML = `<span class="allbar-ic">📋</span>
        <span class="allbar-tx"><span class="allbar-tn">Xem tất cả ${all.length} thủ tục</span>
          <span class="allbar-ss">Có ô tìm kiếm · chạm vào tên để chọn</span></span>
        <span class="allbar-ch">›</span>`;
      bar.addEventListener("click", () => openServiceSheet(all));
      el.appendChild(bar);
    }
    addNode(el);
  }

  // ── Sheet "Tất cả thủ tục" (singleton trong sidebar.html) ──
  let serviceSheetItems = [];
  let serviceSheetWired = false;
  function ensureServiceSheetWired() {
    if (serviceSheetWired) return;
    serviceSheetWired = true;
    const scrim = document.getElementById("svc-sheet-scrim");
    const closeBtn = document.getElementById("svc-sheet-close");
    const input = document.getElementById("svc-search-input");
    if (!scrim) return;
    closeBtn?.addEventListener("click", closeServiceSheet);
    scrim.addEventListener("click", (e) => { if (e.target === scrim) closeServiceSheet(); });
    input?.addEventListener("input", () => renderServiceSheetList(input.value));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !scrim.hidden) closeServiceSheet();
    });
  }
  function openServiceSheet(items) {
    ensureServiceSheetWired();
    const scrim = document.getElementById("svc-sheet-scrim");
    const input = document.getElementById("svc-search-input");
    if (!scrim) return;
    serviceSheetItems = items || [];
    if (input) input.value = "";
    renderServiceSheetList("");
    scrim.hidden = false;
    requestAnimationFrame(() => input?.focus());
  }
  function closeServiceSheet() {
    const scrim = document.getElementById("svc-sheet-scrim");
    if (scrim) scrim.hidden = true;
  }
  function renderServiceSheetList(query) {
    const list = document.getElementById("svc-slist");
    if (!list) return;
    const ql = foldVi(query).trim();
    const subset = serviceSheetItems.filter((it) => !ql || foldVi(it.title).includes(ql)
      || foldVi(it.subtitle).includes(ql));
    list.innerHTML = "";
    if (!subset.length) {
      const none = document.createElement("div");
      none.className = "snone";
      none.textContent = "Không tìm thấy thủ tục phù hợp. Công dân thử từ khoá khác nhé.";
      list.appendChild(none);
      return;
    }
    subset.forEach((it) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "srow";
      const hmongLine = it.titleHmong
        ? `<span class="srow-hm">${window.escapeHtml(it.titleHmong)}</span>` : "";
      const sub = it.subtitle
        ? `<span class="srow-sd">${window.escapeHtml(it.subtitle)}</span>` : "";
      row.innerHTML = `<span class="srow-ic">${window.escapeHtml(it.icon || "📄")}</span>
        <span class="srow-tx"><span class="srow-tn">${highlightMatch(it.title, query)}</span>${hmongLine}${sub}</span>
        <span class="srow-ch">›</span>`;
      row.addEventListener("click", () => { closeServiceSheet(); pickProcedure(it); });
      list.appendChild(row);
    });
  }
  // Tô vàng đoạn khớp khi gõ CÓ dấu (khớp trực tiếp); gõ không dấu vẫn lọc ra nhưng không tô
  // (map vị trí qua bỏ dấu dễ lệch) — an toàn hơn là tô sai.
  function highlightMatch(title, query) {
    const q = String(query || "").trim();
    const esc = window.escapeHtml(title);
    if (!q) return esc;
    const i = title.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc;
    const a = window.escapeHtml(title.slice(0, i));
    const b = window.escapeHtml(title.slice(i, i + q.length));
    const c = window.escapeHtml(title.slice(i + q.length));
    return `${a}<mark>${b}</mark>${c}`;
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
    scan: { icon: "🖨️", title: "Scan tại quầy", desc: "Đặt giấy tờ bản cứng lên máy quét tại quầy." },
    profile: { icon: "📁", title: "Lấy dữ liệu đã lưu", desc: "Đã từng làm và lưu hồ sơ → không cần cung cấp lại." },
  };
  function renderDocOptions(card) {
    const options = card.options || [];
    // Cài đặt "Ưu tiên Scan tại quầy": lượt LIVE + có option scan → TỰ chọn Scan, bỏ câu hỏi.
    // Khôi phục phiên (noTts) thì KHÔNG tự bấm (tránh lặp lệnh).
    if (preferScan && renderingLiveReply && options.includes("scan")) {
      const el = document.createElement("div");
      el.className = "doc-auto-scan";
      const hasQr = options.includes("qr");
      el.innerHTML = `<span>⚙️ Theo cài đặt, em dùng <b>Scan tại quầy</b> ạ.</span>${
        hasQr ? '<button type="button" class="doc-auto-qr" data-qr="1">📱 Đổi sang chụp điện thoại (QR)</button>' : ""}`;
      if (hasQr) el.querySelector("[data-qr]")?.addEventListener("click", () => {
        addUserText("Đổi sang chụp điện thoại (QR)");
        ask(`__action:doc_method:${JSON.stringify({ value: "qr" })}`, "chip", "Chụp bằng điện thoại (quét QR)");
      });
      addNode(el);
      renderScanGuideCard();
      ask(`__action:doc_method:${JSON.stringify({ value: "scan" })}`, "chip", "Scan tại quầy");
      return;
    }
    options.forEach((key) => {
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
        // Chọn Scan tại quầy → dựng thẻ hướng dẫn (ảnh + lời) NGAY, TRƯỚC khi BE trả checklist/nút
        // → thẻ nằm TRÊN, danh sách giấy tờ + nút "Đã đưa đủ" nằm DƯỚI CÙNG.
        if (key === "scan") renderScanGuideCard();
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
  // Phiên scan tại quầy được BE cho phép TỰ CHỐT sau mỗi đợt chọn tệp (pick_files.auto_run):
  // đợt tệp đã phân loại xong ngay trong request /files → gửi docs_complete như bấm nút
  // "Đã đưa đủ", khỏi bắt công dân bấm tay. QR / lượt Điều chỉnh giấy tờ: rỗng = chốt tay.
  let uploadAutoRunSid = "";
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
  // rel trên đĩa ↔ fid trên phiên cho tệp từ máy quét. Xem lib/scanDongBo.js: chuyển file vào thư
  // mục con bắn CẶP removed+added; bản cũ xoá theo TÊN nên để lại hai bản hoặc xoá nhầm tệp trùng
  // tên của công dân.
  const scanDongBo = window.TLNDScanDongBo ? window.TLNDScanDongBo.tao() : null;
  // Xem trước: nội dung lấy từ BE, chỉ tệp ĐANG XEM (xem preview.js). fid -> Promise<{mime,dataUrl}>.
  const previewDuLieu = new Map();
  let previewDangMo = false;
  let previewGhim = false;          // khung đang GHIM (mở bằng nhấn) hay chỉ xem tạm lúc rê chuột
  let previewHenHien = null;
  const PREVIEW_TRE_MS = 350;        // rê lướt qua danh sách thì không nháy khung liên tục

  // Rê chuột lên dòng tệp trong sheet → xem tạm (giống autofill). Đang ghim thì không đổi khung.
  function batDauRePreview(nhom, chiSo) {
    if (previewGhim) return;
    if (previewHenHien) clearTimeout(previewHenHien);
    previewHenHien = setTimeout(() => {
      previewHenHien = null;
      void moPreviewNhom(nhom, chiSo, { ghim: false });
    }, PREVIEW_TRE_MS);
  }
  function ketThucRePreview() {
    if (previewHenHien) { clearTimeout(previewHenHien); previewHenHien = null; }
    // Chỉ XIN ẩn: content.js biết con trỏ có đang ở trên khung không (rê sang để cuộn thì giữ).
    if (previewDangMo && !previewGhim) void sendToContent({ action: "tlndPreviewHide" });
  }

  // ── Tên tệp đã sửa (theo phiên) ──
  // BE không có API đổi tên tệp trong phiên → giữ tên mới ở đây và áp vào MỌI chỗ tên đó đi ra:
  // danh sách, khung xem trước, và payload đính kèm lên cổng (fetchSessionFilesAsPayload).
  const KHOA_TEN_SUA = "tlnd_ten_tep_sua"; // { [sid]: { luc, ten: { [fid]: name } } }
  let tenSuaTheoFid = new Map();
  function tenHienThi(file) {
    return tenSuaTheoFid.get(file?.fid) || file?.name || "";
  }
  async function napTenSua(sid) {
    try {
      const res = await chrome.storage.local.get(KHOA_TEN_SUA);
      if (sid !== uploadSid) return;
      const m = res?.[KHOA_TEN_SUA]?.[sid]?.ten;
      if (!m || typeof m !== "object") return;
      for (const [fid, ten] of Object.entries(m)) {
        if (typeof ten === "string" && ten && !tenSuaTheoFid.has(fid)) tenSuaTheoFid.set(fid, ten);
      }
      if (activeFileGroup) renderUploadFileList();
    } catch (_) { /* mất tên đã sửa chỉ làm hiện lại tên gốc */ }
  }
  async function luuTenSua() {
    const sid = uploadSid;
    if (!sid) return;
    try {
      const res = await chrome.storage.local.get(KHOA_TEN_SUA);
      const m = res?.[KHOA_TEN_SUA] || {};
      const gio = Date.now();
      for (const k of Object.keys(m)) if (gio - Number(m[k]?.luc || 0) > 24 * 60 * 60 * 1000) delete m[k];
      m[sid] = { luc: gio, ten: Object.fromEntries(tenSuaTheoFid) };
      await chrome.storage.local.set({ [KHOA_TEN_SUA]: m });
    } catch (_) { /* ignore */ }
  }

  // ── Sổ sách tệp quét: sống qua lần dựng lại iframe ──
  // Ở chế độ đẩy trang, iframe sidebar bị dựng lại MỖI LẦN chuyển trang. Sổ rel→fid chỉ nằm trong bộ
  // nhớ thì sau một lần điều hướng, file.removed không tìm được fid để gỡ → trùng bản quay lại. Cùng
  // lý do, watermark và bộ nhớ "đã gỡ tay" cũng phải xuống storage (autofill cũng làm vậy).
  const KHOA_SO_SACH_SCAN = "tlnd_scan_so_sach";                     // { [sid]: { luc, tep } }
  const KHOA_WATERMARK_SCAN = `tlnd_scan_watermark_${TAB_ID || "khong-tab"}`;
  const KHOA_DA_GO_SCAN = "tlnd_scan_da_go";                         // [{ hash, rel, luc }]
  const SCAN_DA_GO_MAX = 200;
  const SCAN_TTL_MS = 24 * 60 * 60 * 1000;
  let scanDaGo = new Map();            // hash -> { rel, luc }: nội dung đã bị GỠ TAY
  let scanAgentHelpers = null;         // { listFiles, fetchBlob, renameFile, caps } từ onConnected
  let scanAgentCaps = [];
  let scanLoDaThuSid = "";             // mỗi phiên chỉ gom lô một lần
  let scanDoiSoatSid = "";             // mỗi phiên chỉ đối soát một lần
  let scanRecentPending = [];          // [{ rel, name, mtimeMs }] chờ cán bộ chọn tay
  const scanDangDoiTen = new Set();    // rel cũ/mới của lần đổi tên do CHÍNH mình — bỏ qua cặp event
  const $scanRecent = document.getElementById("scan-recent-list");
  const $hoSoTruoc = document.getElementById("prev-session-offer");

  async function napSoSachScan(sid) {
    if (!scanDongBo || !sid) return;
    try {
      const res = await chrome.storage.local.get(KHOA_SO_SACH_SCAN);
      if (sid !== uploadSid) return;
      scanDongBo.nap(res?.[KHOA_SO_SACH_SCAN]?.[sid]?.tep);
    } catch (_) { /* mất sổ chỉ làm mất khả năng gỡ tệp đã chuyển đi */ }
  }
  async function luuSoSachScan() {
    const sid = uploadSid;
    if (!scanDongBo || !sid) return;
    try {
      const res = await chrome.storage.local.get(KHOA_SO_SACH_SCAN);
      const m = res?.[KHOA_SO_SACH_SCAN] || {};
      const gio = Date.now();
      for (const k of Object.keys(m)) if (gio - Number(m[k]?.luc || 0) > SCAN_TTL_MS) delete m[k];
      m[sid] = { luc: gio, tep: scanDongBo.xuat() };
      await chrome.storage.local.set({ [KHOA_SO_SACH_SCAN]: m });
    } catch (_) { /* ignore */ }
  }
  async function napWatermarkScan() {
    try {
      const res = await chrome.storage.local.get(KHOA_WATERMARK_SCAN);
      const ms = Number(res?.[KHOA_WATERMARK_SCAN] || 0);
      if (Number.isFinite(ms) && ms > scanWatermarkMs) scanWatermarkMs = ms;
    } catch (_) { /* ignore */ }
  }
  async function napDaGoScan() {
    try {
      const res = await chrome.storage.local.get(KHOA_DA_GO_SCAN);
      const ds = Array.isArray(res?.[KHOA_DA_GO_SCAN]) ? res[KHOA_DA_GO_SCAN] : [];
      const gio = Date.now();
      for (const e of ds) {
        if (e && typeof e.hash === "string" && gio - Number(e.luc || 0) < SCAN_TTL_MS && !scanDaGo.has(e.hash)) {
          scanDaGo.set(e.hash, { rel: e.rel || null, luc: Number(e.luc) || gio });
        }
      }
    } catch (_) { /* mất bộ nhớ này chỉ làm mất phép chặn, không làm hỏng gì */ }
  }
  function luuDaGoScan() {
    try {
      const ds = [...scanDaGo.entries()]
        .map(([hash, v]) => ({ hash, rel: v.rel, luc: v.luc }))
        .sort((a, b) => b.luc - a.luc)
        .slice(0, SCAN_DA_GO_MAX);
      scanDaGo = new Map(ds.map((e) => [e.hash, { rel: e.rel, luc: e.luc }]));
      void chrome.storage.local.set({ [KHOA_DA_GO_SCAN]: ds });
    } catch (_) { /* ignore */ }
  }
  // Gỡ tay là một QUYẾT ĐỊNH: nhớ theo NỘI DUNG để lô gom / đối soát sau không tự đưa lại.
  function ghiNhanDaGo(hash, rel) {
    if (!hash) return;
    scanDaGo.set(hash, { rel: rel || null, luc: Date.now() });
    luuDaGoScan();
  }

  async function sha256Hex(blob) {
    const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function formatRelativeTime(ms) {
    const phut = Math.max(0, Math.round((Date.now() - ms) / 60000));
    if (phut < 1) return "vừa xong";
    if (phut < 60) return `${phut} phút trước`;
    return `${Math.round(phut / 60)} giờ trước`;
  }

  // ── Tệp quét gần đây: cán bộ chọn tay ──
  // Hiện khi KHÔNG tự tin gom lô (không rõ ranh giới giữa hai công dân) hoặc lô đã quá cũ — hệ thống
  // không đoán liều, cán bộ nhìn tên + giờ rồi quyết.
  function hienDanhSachGanDay() {
    if (!$scanRecent) return;
    $scanRecent.replaceChildren();
    if (!scanRecentPending.length || !uploadSid) { $scanRecent.hidden = true; return; }
    const dau = document.createElement("div");
    dau.className = "scan-recent-head";
    const goiY = document.createElement("span");
    goiY.className = "scan-recent-hint";
    goiY.textContent = "🖨️ Máy quét có tệp gần đây, chưa chắc của công dân này — chọn đúng tệp cần tải lên:";
    const tatCa = document.createElement("button");
    tatCa.type = "button";
    tatCa.className = "scan-recent-add-all";
    tatCa.textContent = "+ Thêm tất cả";
    tatCa.addEventListener("click", () => void themTuDanhSachGanDay([...scanRecentPending]));
    dau.append(goiY, tatCa);
    $scanRecent.appendChild(dau);
    for (const f of scanRecentPending) {
      const row = document.createElement("div");
      row.className = "scan-recent-row";
      const nhan = document.createElement("span");
      nhan.textContent = `${f.name} — ${formatRelativeTime(f.mtimeMs)}`;
      nhan.title = f.rel;
      const them = document.createElement("button");
      them.type = "button";
      them.textContent = "+";
      them.title = "Tải tệp này lên hồ sơ";
      them.setAttribute("aria-label", `Tải lên ${f.name}`);
      them.addEventListener("click", () => void themTuDanhSachGanDay([f]));
      row.append(nhan, them);
      $scanRecent.appendChild(row);
    }
    $scanRecent.hidden = false;
  }

  async function themTuDanhSachGanDay(ds) {
    markActivity();
    for (const f of ds) {
      scanRecentPending = scanRecentPending.filter((x) => x.rel !== f.rel);
      hienDanhSachGanDay();
      if (!scanAgentHelpers) break;
      // tuDong=false: quyết định của cán bộ — không bị watermark / trần tuổi / "đã gỡ tay" chặn.
      await onScanFile({ rel: f.rel, mtimeMs: f.mtimeMs }, () => scanAgentHelpers.fetchBlob(f.rel), { tuDong: false });
    }
  }

  // Gom LÔ tệp quét đã có sẵn trong thư mục lúc vừa nối máy quét / vừa vào bước tải giấy tờ (cán bộ
  // quét trước rồi mới mở Trợ lý). Quyết định ở lib/scanLo.js (chép từ autofill).
  async function thuGomLoQuet() {
    const sid = uploadSid;
    if (!sid || !scanAgentHelpers || !window.TLNDScanLo || scanLoDaThuSid === sid) return;
    if (uploadSessionProgress?.complete) return;
    scanLoDaThuSid = sid; // chốt TRƯỚC await: onConnected và setUploadSession gọi gần như cùng lúc
    let trenDia;
    try {
      trenDia = await scanAgentHelpers.listFiles();
    } catch (e) {
      console.warn("[TLND] Không đọc được /v1/files để gom lô quét:", e?.message || e);
      scanLoDaThuSid = ""; // lỗi tạm thời — lần sau thử lại
      return;
    }
    if (sid !== uploadSid) return;
    const daCo = new Set((scanDongBo?.danhSach() || []).map((x) => x.rel));
    const kq = window.TLNDScanLo.quyetDinh({ trenDia, daCo, watermarkMs: scanWatermarkMs });
    // Nhật ký quyết định: "vì sao tệp này bị/không bị tự tải" trả lời được bằng một dòng console.
    console.info("[TLND] Gom lô quét:", {
      ...kq.nhatKy,
      watermark: scanWatermarkMs ? new Date(scanWatermarkMs).toLocaleString() : "chưa có",
      quyet_dinh: kq.lyDo || kq.hanhDong,
    });
    if (kq.hanhDong === "tu-them") {
      for (const f of kq.tuThem) {
        if (sid !== uploadSid) return;
        await onScanFile({ rel: f.rel, mtimeMs: f.mtimeMs }, () => scanAgentHelpers.fetchBlob(f.rel));
      }
    } else if (kq.hanhDong === "chon-tay") {
      scanRecentPending = kq.chonTay;
      hienDanhSachGanDay();
    }
  }

  // Đối soát MỘT LẦN mỗi phiên: tệp đã tải lên (sổ rel→fid) với trạng thái THẬT trên đĩa — bắt đúng ca
  // "bị xoá/ghi đè trong lúc Trợ lý đóng", thứ SSE sống không thấy được.
  async function doiSoatTepQuet() {
    const sid = uploadSid;
    if (!sid || !scanAgentHelpers || !scanDongBo || scanDoiSoatSid === sid) return;
    const ds = scanDongBo.danhSach();
    if (!ds.length) return;
    scanDoiSoatSid = sid;
    let trenDia;
    try {
      trenDia = await scanAgentHelpers.listFiles();
    } catch (_) {
      scanDoiSoatSid = "";
      return;
    }
    // Chốt chặn XOÁ OAN: listFiles() trả {files: []} KHÔNG kèm folder khi request hỏng (chưa chọn
    // thư mục, ổ mạng rớt…). Tin danh sách rỗng đó là gỡ sạch giấy tờ của công dân.
    if (typeof trenDia?.folder !== "string" || sid !== uploadSid) { scanDoiSoatSid = ""; return; }
    const con = new Set((trenDia.files || []).map((f) => f?.rel).filter(Boolean));
    for (const muc of ds) {
      if (sid !== uploadSid || uploadSessionProgress?.complete) return;
      if (!con.has(muc.rel)) {
        const fid = scanDongBo.daXoa(muc.rel);
        if (fid) await deleteUploadSessionFile({ fid, name: scanBaseName(muc.rel) });
        continue;
      }
      // Còn trên đĩa: onScanFile tự so hash — trùng thì bỏ qua, khác thì tải bản mới rồi gỡ bản cũ.
      await onScanFile({ rel: muc.rel }, () => scanAgentHelpers.fetchBlob(muc.rel));
    }
    void luuSoSachScan();
  }

  // ── "Hồ sơ trước": dùng lại giấy tờ bằng một chạm ──
  // Cùng bài toán với autofill (mục 4.11): watermark chặn đúng việc kéo giấy người trước sang hồ sơ
  // người sau, nhưng chặn luôn ca hợp lệ "cùng công dân làm thủ tục thứ hai".
  // KHÁC autofill: chỉ cất THAM CHIẾU (sid + fid), không chép nội dung giấy tờ vào extension. BE giữ
  // phiên 24 giờ (upload_session_ttl_hours) — dùng lại thì tải từ phiên cũ sang phiên mới.
  const KHOA_HO_SO_TRUOC = `tlnd_ho_so_truoc_${TAB_ID || "khong-tab"}`;
  const HO_SO_TRUOC_TTL_MS = 30 * 60 * 1000;

  function catHoSoTruoc() {
    // Chụp ĐỒNG BỘ trước mọi await: bên gọi dọn danh sách tệp ngay sau lệnh này.
    const sid = uploadSid;
    const tep = (uploadSessionFiles || []).filter((f) => f?.fid).map((f) => ({ fid: f.fid, name: tenHienThi(f) }));
    if (!sid || !tep.length) return;
    void (async () => {
      let ten = null;
      try { ten = (await readPageContext())?.principal?.name || null; } catch (_) { /* còn số tệp + giờ */ }
      try { await chrome.storage.local.set({ [KHOA_HO_SO_TRUOC]: { sid, tep, luc: Date.now(), ten } }); }
      catch (_) { /* ignore */ }
    })();
  }
  async function docHoSoTruoc() {
    try {
      const res = await chrome.storage.local.get(KHOA_HO_SO_TRUOC);
      const snap = res?.[KHOA_HO_SO_TRUOC];
      if (!snap?.sid || !Array.isArray(snap.tep) || !snap.tep.length) return null;
      if (Date.now() - Number(snap.luc || 0) > HO_SO_TRUOC_TTL_MS) { void boHoSoTruoc(); return null; }
      return snap;
    } catch (_) { return null; }
  }
  async function boHoSoTruoc() {
    try { await chrome.storage.local.remove(KHOA_HO_SO_TRUOC); } catch (_) { /* ignore */ }
  }
  async function hienLoiMoiHoSoTruoc(soTepGoi) {
    if (!$hoSoTruoc) return;
    const sid = uploadSid;
    if (!sid || uploadSessionProgress?.complete) { $hoSoTruoc.hidden = true; return; }
    const soTep = Number.isFinite(soTepGoi) ? soTepGoi
      : ((uploadSessionFiles || []).length || Number(uploadSessionProgress?.files_count) || 0);
    // Lời mời CHỈ có nghĩa khi phiên mới còn trống. Đã có tệp = đang làm hồ sơ cụ thể rồi → dọn luôn
    // ngăn lưu, không để tham chiếu giấy của công dân trước nằm lại.
    if (soTep > 0) {
      if (!$hoSoTruoc.hidden) { $hoSoTruoc.hidden = true; void boHoSoTruoc(); }
      return;
    }
    const snap = await docHoSoTruoc();
    if (!snap || snap.sid === sid || sid !== uploadSid) { $hoSoTruoc.hidden = true; return; }
    const gio = new Date(snap.luc).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    const nhan = document.createElement("span");
    nhan.className = "prev-offer-label";
    nhan.textContent = `📎 Hồ sơ trước — ${snap.ten ? `${snap.ten} · ` : ""}${snap.tep.length} giấy tờ · ${gio}`;
    const nut = document.createElement("button");
    nut.type = "button";
    nut.className = "prev-offer-use";
    nut.textContent = "Dùng lại";
    nut.title = "Tải lại toàn bộ giấy tờ của hồ sơ trước vào phiên này (khi CÙNG công dân làm thủ tục tiếp theo)";
    nut.addEventListener("click", () => void dungLaiHoSoTruoc());
    // CỐ Ý không có nút "×": bấm nhầm là mất hẳn lời mời, mà nó vốn tự ẩn khi phiên có tệp.
    $hoSoTruoc.replaceChildren(nhan, nut);
    $hoSoTruoc.hidden = false;
  }
  async function dungLaiHoSoTruoc() {
    markActivity();
    const sid = uploadSid;
    const snap = await docHoSoTruoc();
    if (!snap || !sid) { void hienLoiMoiHoSoTruoc(); return; }
    if ($hoSoTruoc) $hoSoTruoc.hidden = true;
    await boHoSoTruoc(); // dùng rồi thì thôi, không mời lại
    setStatus(`⏳ Đang lấy lại ${snap.tep.length} giấy tờ của hồ sơ trước…`);
    const tepMoi = [];
    let hong = 0;
    for (const t of snap.tep) {
      try {
        const res = await uploadSessionFetch(
          `${BASE_URL}/api/v1/upload-sessions/${encodeURIComponent(snap.sid)}/files/${encodeURIComponent(t.fid)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        tepMoi.push(new File([blob], t.name || "giay-to", { type: blob.type || "application/octet-stream" }));
      } catch (e) {
        hong += 1;
        console.warn("[TLND] Không lấy lại được tệp của hồ sơ trước", t.fid, e?.message || e);
      }
    }
    if (sid !== uploadSid) return;
    if (!tepMoi.length) {
      setStatus("⚠️ Không lấy lại được giấy tờ của hồ sơ trước — phiên cũ có thể đã hết hạn.", true);
      return;
    }
    setStatus("");
    const data = await uploadFilesToSession(tepMoi, { source: "reuse" });
    if (data) {
      showToast(`📎 Đã dùng lại ${tepMoi.length} giấy tờ của hồ sơ trước${hong ? ` (${hong} tệp không lấy được)` : ""}.`, { ms: 4000 });
    }
  }

  // ── Sửa tên tệp ngay trong danh sách ──
  // Tệp từ máy quét: đổi luôn tên trên đĩa qua agent (caps "rename") — giống autofill mục 4.13.
  function batDauSuaTen(file, nameEl) {
    if (nameEl.parentElement?.querySelector(".file-list-rename-input")) return;
    const o = document.createElement("input");
    o.type = "text";
    o.className = "file-list-rename-input";
    o.value = tenHienThi(file);
    o.setAttribute("aria-label", "Tên tệp mới");
    let xong = false;
    const huy = () => { if (!xong) { xong = true; renderUploadFileList(); } };
    o.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (!xong) { xong = true; void ketThucSuaTen(file, o.value); }
      } else if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation(); // Esc chỉ huỷ sửa tên, không đóng luôn danh sách
        huy();
      }
    });
    o.addEventListener("blur", huy); // bấm ra ngoài = huỷ, không tự lưu (tránh sửa nhầm mà không hay)
    nameEl.replaceWith(o);
    o.focus();
    const cham = o.value.lastIndexOf(".");
    o.setSelectionRange(0, cham > 0 ? cham : o.value.length);
  }

  async function ketThucSuaTen(file, tenNhap) {
    const ten = String(tenNhap || "").trim();
    if (!ten || ten === tenHienThi(file)) { renderUploadFileList(); return; }
    const goc = scanDongBo?.timTheoFid(file.fid);
    if (goc) {
      if (!scanAgentHelpers?.renameFile) {
        setStatus("⚠️ Chưa kết nối được máy quét nên chưa đổi tên tệp trên đĩa được.", true);
        renderUploadFileList();
        return;
      }
      const relCu = goc.rel;
      let relMoi = relCu;
      scanDangDoiTen.add(relCu);
      try {
        const res = await scanAgentHelpers.renameFile(relCu, ten);
        relMoi = res?.rel || relCu.replace(/[^/]*$/, ten);
        scanDangDoiTen.add(relMoi); // chặn luôn cặp removed+added do chính lần đổi tên này sinh ra
        scanDongBo.doiRel(relCu, relMoi);
        void luuSoSachScan();
      } catch (e) {
        const msg = e?.code === "NAME_EXISTS"
          ? `Trong thư mục quét đã có tệp tên "${ten}" rồi — đặt tên khác ạ.`
          : e?.code === "BAD_NAME"
            ? "Tên không hợp lệ: phải là tên tệp trần và giữ đuôi .pdf."
            : `Không đổi tên được trên đĩa: ${e?.message || e}`;
        console.warn("[TLND] Đổi tên tệp máy quét lỗi:", relCu, e);
        setStatus(`⚠️ ${msg}`, true);
        renderUploadFileList();
        return;
      } finally {
        // Nới sau một nhịp để cặp event do chính lần đổi tên này sinh ra kịp đi qua.
        setTimeout(() => { scanDangDoiTen.delete(relCu); scanDangDoiTen.delete(relMoi); }, 5000);
      }
    }
    tenSuaTheoFid.set(file.fid, ten);
    void luuTenSua();
    renderUploadFileList();
    showToast(goc ? `✎ Đã đổi tên thành "${ten}" (cả trên đĩa).` : `✎ Đã đổi tên thành "${ten}".`);
  }

  // ── Kéo-thả tệp vào Trợ lý ──
  // Lối vào thủ công SONG SONG với nút 📷 chọn tệp — đi đúng một đường tải lên (uploadFilesToSession).
  // Nghe trên document CỦA CHÍNH sidebar (iframe đẩy trang hoặc khung bên), không nghe trên trang
  // cổng: nghe ở trang là preventDefault luôn ô tải tệp của chính cổng dịch vụ công.
  // Khác autofill: không cần tầng content.js — khung đẩy trang của handfree là iframe phủ kín, không
  // có tiêu đề/viền thuộc trang gốc mà con trỏ phải đi qua.
  const $dropOverlay = document.getElementById("drop-overlay");
  if ($dropOverlay) {
    let doSau = 0; // dragenter/dragleave lồng nhau khi rê qua phần tử con — đếm thay vì bật/tắt
    const laKeoTep = (e) => Array.from(e.dataTransfer?.types || []).includes("Files");
    const hienLop = () => {
      $dropOverlay.hidden = false;
      requestAnimationFrame(() => $dropOverlay.classList.add("hien"));
    };
    const anLop = () => {
      doSau = 0;
      $dropOverlay.classList.remove("hien");
      setTimeout(() => { if (!$dropOverlay.classList.contains("hien")) $dropOverlay.hidden = true; }, 150);
    };
    document.addEventListener("dragenter", (e) => {
      if (!laKeoTep(e)) return;
      e.preventDefault();
      doSau += 1;
      hienLop();
    });
    document.addEventListener("dragover", (e) => { if (laKeoTep(e)) e.preventDefault(); });
    document.addEventListener("dragleave", (e) => {
      if (!laKeoTep(e)) return;
      doSau = Math.max(0, doSau - 1);
      if (!doSau) anLop();
    });
    document.addEventListener("drop", (e) => {
      if (!laKeoTep(e)) return;
      e.preventDefault();
      anLop();
      const ds = [...(e.dataTransfer?.files || [])];
      if (!ds.length) return;
      markActivity();
      if (!uploadSid || uploadSessionProgress?.complete) {
        setStatus("⚠️ Chưa tới bước tải giấy tờ — chọn thủ tục và cách nộp giấy tờ trước rồi kéo tệp vào ạ.", true);
        setTimeout(() => setStatus(""), 5000);
        return;
      }
      void uploadFilesToSession(ds, { source: "drop" });
    });
  }

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

  function filesInGroup(group) {
    if (!group) return [];
    return uploadSessionFiles.filter((file) => group.unknown
      ? !file.doc_key
      : file.doc_key === group.docKey);
  }

  function filesInActiveGroup() {
    return filesInGroup(activeFileGroup);
  }

  // ── Xem trước giấy tờ: khung nổi TRÊN TRANG do content.js dựng ──
  async function moPreviewNhom(group, chiSo = 0, { ghim = true } = {}) {
    if (!uploadSid || !group) return;
    markActivity();
    let tep = filesInGroup(group);
    // Doc-row dựng từ progress (WS) có thể tới trước danh sách tệp (REST) → nạp rồi thử lại.
    if (!tep.length) {
      try { await loadUploadSessionFiles(); } catch (_) { /* báo ngay dưới */ }
      tep = filesInGroup(group);
    }
    if (!tep.length) {
      setStatus("⚠️ Chưa tải được danh sách tệp để xem trước.", true);
      return;
    }
    previewDangMo = true;
    previewGhim = ghim;
    await sendToContent({
      action: "tlndPreviewOpen",
      ghim,
      tieuDe: group.name || "Giấy tờ",
      bieuTuong: group.icon || "📄",
      tep: tep.map((f) => ({ fid: f.fid, name: tenHienThi(f) })),
      chiSo: Math.max(0, Math.min(Number(chiSo) || 0, tep.length - 1)),
    });
  }

  function taiDuLieuPreview(fid) {
    if (!previewDuLieu.has(fid)) {
      const sid = uploadSid;
      const p = (async () => {
        const res = await uploadSessionFetch(
          `${BASE_URL}/api/v1/upload-sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fid)}`);
        if (!res.ok) throw new Error(`Không tải được tệp (HTTP ${res.status}).`);
        const blob = await res.blob();
        return { mime: blob.type || "", dataUrl: await blobToDataUrl(blob) };
      })();
      // Lỗi thì không giữ trong bộ nhớ — lần xem sau thử lại, không kẹt lỗi cũ.
      p.catch(() => previewDuLieu.delete(fid));
      previewDuLieu.set(fid, p);
    }
    return previewDuLieu.get(fid);
  }

  function dongPreviewTuSidebar() {
    if (previewHenHien) { clearTimeout(previewHenHien); previewHenHien = null; }
    if (!previewDangMo) return;
    previewDangMo = false;
    previewGhim = false;
    void sendToContent({ action: "tlndPreviewClose" });
  }

  chrome.runtime.onMessage.addListener((msg, sender) => {
    if (Number(sender?.tab?.id) !== Number(TAB_ID)) return; // tab khác → kệ
    if (msg?.action === "tlndPreviewCan") {
      const fid = String(msg.fid || "");
      if (!fid || !uploadSid) return;
      taiDuLieuPreview(fid)
        .then((d) => sendToContent({ action: "tlndPreviewData", fid, ...d }))
        .catch((e) => sendToContent({ action: "tlndPreviewData", fid, loi: e?.message || "Không tải được tệp." }));
    } else if (msg?.action === "tlndPreviewDaDong") {
      previewDangMo = false;
      previewGhim = false;
    }
  });

  // Bấm ra ngoài khung xem trước — kể cả chỗ khác TRONG Trợ lý — là đóng. Trừ bấm vào doc-row /
  // dòng tệp: đó là mở hoặc chuyển xem trước. Capture để nút nào tự chặn lan truyền cũng không nuốt.
  document.addEventListener("pointerdown", (e) => {
    if (!previewDangMo || e.target.closest?.(".doc-row.co-xem, .file-list-name.co-xem")) return;
    dongPreviewTuSidebar();
  }, true);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dongPreviewTuSidebar();
  });
  // Con trỏ TRONG Trợ lý nhưng ngoài dòng tệp → bằng chứng đã rời khung xem tạm (khi con trỏ nằm trên
  // khung, sidebar không nhận được mousemove nào). Xem choChuotRoiDi trong content.js.
  let lucBaoChuotORaNgoai = 0;
  document.addEventListener("mousemove", (e) => {
    if (!previewDangMo || previewGhim || e.target.closest?.(".file-list-row")) return;
    const gio = Date.now();
    if (gio - lucBaoChuotORaNgoai < 150) return; // mousemove bắn liên tục — gom bớt
    lucBaoChuotORaNgoai = gio;
    void sendToContent({ action: "tlndPreviewChuotOSidebar" });
  }, { capture: true, passive: true });

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
      name.textContent = tenHienThi(file) || "Tệp không có tên";
      name.title = `Xem trước ${tenHienThi(file) || "tệp không có tên"}`;
      name.classList.add("co-xem");
      name.setAttribute("role", "button");
      name.tabIndex = 0;
      const nhom = activeFileGroup;
      const chiSo = files.indexOf(file);
      const moXem = () => void moPreviewNhom(nhom, chiSo);
      row.addEventListener("mouseenter", () => batDauRePreview(nhom, chiSo));
      row.addEventListener("mouseleave", ketThucRePreview);
      name.addEventListener("click", moXem);
      name.addEventListener("keydown", (e) => {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        moXem();
      });

      row.append(icon, name);
      if (locked) {
        const lock = document.createElement("span");
        lock.className = "file-list-lock";
        lock.textContent = "Đã chốt";
        row.appendChild(lock);
      } else {
        const goc = scanDongBo?.timTheoFid(file.fid);
        // Tệp máy quét: chỉ sửa được khi agent khai caps "rename" (agent bản cũ trả 404 cho route đó).
        if (!goc || scanAgentCaps.includes("rename")) {
          const sua = document.createElement("button");
          sua.className = "file-list-rename";
          sua.type = "button";
          sua.textContent = "✎";
          sua.title = goc ? "Sửa tên tệp (đổi luôn tên trên đĩa trong thư mục quét)" : "Sửa tên tệp";
          sua.setAttribute("aria-label", `Sửa tên tệp ${tenHienThi(file) || ""}`);
          sua.addEventListener("click", () => batDauSuaTen(file, name));
          row.appendChild(sua);
        }
        const remove = document.createElement("button");
        remove.className = "file-list-delete";
        remove.type = "button";
        remove.textContent = "✕";
        remove.title = `Xóa ${file.name || "tệp"}`;
        remove.setAttribute("aria-label", `Xóa tệp ${file.name || "không có tên"}`);
        remove.disabled = deletingFileIds.has(file.fid);
        remove.addEventListener("click", () => void deleteUploadSessionFile(file, { thuCong: true }));
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

  async function deleteUploadSessionFile(file, { thuCong = false } = {}) {
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
      if (thuCong) {
        // Gỡ TAY tệp từ máy quét → nhớ nội dung, lô gom / đối soát sau không tự đưa lại.
        const goc = scanDongBo?.timTheoFid(file.fid);
        if (goc?.hash) ghiNhanDaGo(goc.hash, goc.rel);
      }
      scanDongBo?.quenFid(file.fid);
      void luuSoSachScan();
      previewDuLieu.delete(file.fid);
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
    scanDongBo?.datLai();
    previewDuLieu.clear();
    dongPreviewTuSidebar(); // không để giấy của công dân trước treo trên màn hình
    tenSuaTheoFid = new Map();
    scanRecentPending = [];
    hienDanhSachGanDay();
    scanLoDaThuSid = "";
    scanDoiSoatSid = "";
    if ($hoSoTruoc) $hoSoTruoc.hidden = true;
  }

  function setUploadSession(sid) {
    if (uploadSid !== sid) resetUploadFileListState();
    uploadSid = sid;
    // Sổ rel→fid + tên đã sửa của phiên này sống qua lần dựng lại iframe. Nạp xong MỚI đối soát và
    // gom lô, để lô không tải lại những tệp đã có.
    void napTenSua(sid);
    void napSoSachScan(sid).then(async () => {
      await doiSoatTepQuet();
      await thuGomLoQuet();
      void hienLoiMoiHoSoTruoc();
    });
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
  // Tải MỘT đợt tệp lên upload session — DÙNG CHUNG cho: chọn tệp tay (#file-input) và máy quét
  // tự động (scan-bridge, source="scan"). Chỉ chặng truyền/lưu; phân loại OCR/LLM chạy ở chặng
  // xử lý sau khi bấm "Đã đưa đủ".
  async function uploadFilesToSession(files, { source = "picker" } = {}) {
    files = [...(files || [])];
    if (!files.length || !uploadSid) return null;
    markActivity();
    const totalBytes = files.reduce((sum, file) => sum + Number(file.size || 0), 0);
    const uploadStartedAt = performance.now();
    setStatus(`⏳ Đang tải ${files.length} tệp lên hệ thống…`);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f, f.name));
      const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${uploadSid}/files`,
        { method: "POST", body: fd });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      console.log("[TLND] upload session files", {
        source,
        fileCount: files.length,
        totalBytes,
        elapsedMs: Math.round(performance.now() - uploadStartedAt),
        accepted: (data?.accepted || []).map((item) => item.doc_key || null),
      });
      setStatus("");
      // Bytes vừa upload VẪN ĐANG trong tay → giữ lại, lúc đính khỏi tải ngược từ máy chủ.
      // CHỜ xong ở đây (không bắn-rồi-quên): giữ Blob là thao tác tức thời, mà nếu để chạy
      // nền thì cán bộ bấm "Đã đưa đủ" ngay là cache chưa kịp ghi → vẫn phải tải.
      await cacheUploadedBlobs(uploadSid, files, data?.accepted);
      if (data?.progress) renderDocProgress(data.progress, { preserveScroll: !$fileListScrim?.hidden });
      if (!$fileListScrim?.hidden) void loadUploadSessionFiles();
      const unknown = (data?.accepted || []).filter((a) => !a.doc_key).length;
      if (unknown) addBotMd(`⚠️ **${unknown} tệp** em chưa nhận ra loại — công dân scan lại rõ hơn hoặc cứ bấm "Đã đưa đủ" để em xử lý phần nhận được ạ.`);
      // Scan tại quầy (BE bật auto_run): đợt tệp đã tải + PHÂN LOẠI xong ngay trong request
      // này → tự chốt như bấm "Đã đưa đủ" (submitDocsComplete kèm page context để BE chọn
      // đúng bước: điền chủ hồ sơ / điền tờ khai / đính kèm). Guard theo state nên đợt tệp
      // sau đó (pipeline đang chạy, state đã rời collecting_docs) không bắn trùng.
      // MÁY QUÉT (source="scan") tệp về LẺ TẺ → KHÔNG tự chốt, để công dân bấm "Đã đưa đủ".
      const sessionFiles = Number(data?.progress?.files_count) || 0;
      if (source !== "scan" && source !== "reuse" && uploadSid && uploadSid === uploadAutoRunSid
          && lastState === "collecting_docs" && sessionFiles > 0) {
        setStatus("⏳ Đã nhận đợt tệp — em xử lý luôn ạ…");
        // __action:docs_done = đúng lệnh của nút "Đã đưa đủ" (BE chốt phiên rồi chạy pipeline).
        void submitDocsComplete("__action:docs_done", "system");
      }
      return data;
    } catch (err) {
      setStatus(`⚠️ Tải tệp lỗi: ${err?.message || err}`, true);
      setTimeout(() => setStatus(""), 5000);
      return null;
    }
  }
  $fileInput?.addEventListener("change", async (e) => {
    const files = [...(e.target.files || [])];
    e.target.value = "";
    await uploadFilesToSession(files, { source: "picker" });
  });

  // ── Máy quét tại quầy (scan-bridge agent) ──
  // Agent Go chạy nền trên máy cán bộ, theo dõi thư mục máy quét, bắn SSE khi có tệp mới. Ta nối
  // agent → tải tệp về → đổ vào CÙNG upload session (như chọn tệp tay) mà không cần bấm chọn.
  const $scanStatus = document.getElementById("scan-agent-status");
  let scanConn = null;               // { stop() } — 1 kết nối/sidebar
  let scanAgentConnected = false;    // đã handshake SSE + đã chọn thư mục
  let scanPickerTimer = null;        // hẹn bật hộp chọn tệp NẾU không có agent
  let scanWatermarkMs = 0;           // mốc chặn: chỉ nhận tệp MỚI HƠN (không kéo giấy người trước)
  let scanNewestMs = 0;              // mtime mới nhất phiên này đã nhận
  const scanUploadingRel = new Set(); // chặn tải trùng cùng rel đang bay
  let scanGuideShown = false;        // thẻ hướng dẫn đặt giấy (ảnh + lời) đã dựng chưa
  let scanReceivedCount = 0;         // số tệp máy quét đã nhận phiên này (để báo "đã nhận N tệp")
  void napWatermarkScan();
  void napDaGoScan();

  // ── Trạng thái panel (lib/trangThai.js — dùng chung với autofill) ──
  // "Đang làm việc" = request đang chạy + thao tác trên panel/trang gốc + con trỏ trong ô nhập + cờ bận
  // nghiệp vụ. Background không hỏi thẳng được iframe/khung bên, nên panel tự ghi nhịp theo TAB vào
  // storage — kiemBanMoi đọc để không nạp lại giữa lúc đang tải tệp quét lên.
  if (window.HccTrangThai && TAB_ID) {
    window.HccTrangThai.batDau({
      layCoBanNgoai: () => busy || scanUploadingRel.size > 0 || deletingFileIds.size > 0,
    });
    const khoTrangThai = chrome.storage?.session || chrome.storage?.local;
    const khoaTrangThai = `tlnd_trang_thai_panel:${TAB_ID}`;
    const ghiNhip = () => {
      try {
        khoTrangThai?.set({ [khoaTrangThai]: { tt: window.HccTrangThai.hienTai(), luc: Date.now() } },
          () => void chrome.runtime.lastError);
      } catch (_) { /* context mất — background coi nhịp cũ là hết hạn */ }
    };
    window.HccTrangThai.theoDoi(ghiNhip);
    setInterval(ghiNhip, 3000);
    ghiNhip();
  }

  // ── Nút "Cập nhật" chủ động ──
  // background (kiemBanMoi) ghi "bản mới đang chờ" vào storage mỗi nhịp kiểm; ở đây chỉ vẽ nút và hỏi xác
  // nhận. Cập nhật = nạp lại extension, mà content script bản mới chỉ được tiêm khi trang tải lại →
  // background tải lại đúng tab này sau khi nạp. Vì thế PHẢI hỏi: nội dung chưa lưu trên trang có thể mất.
  // Mặc định vẫn là tự nạp lại khi máy rảnh 60 giây — nút chỉ dành cho lúc cán bộ đang làm liên tục.
  const KHOA_BAN_CHO = "hcc_ban_moi_cho";
  const $capNhatBtn = document.getElementById("cap-nhat-btn");
  const $capNhatXn = document.getElementById("cap-nhat-xac-nhan");
  const $capNhatTieuDe = document.getElementById("cap-nhat-tieu-de");
  const $capNhatCanhBao = document.getElementById("cap-nhat-canh-bao");
  const $capNhatNgay = document.getElementById("cap-nhat-ngay");
  let banMoiCho = "";

  function veNutCapNhat() {
    let dangChay = "";
    try { dangChay = chrome.runtime.getManifest().version; } catch (_) { return; } // context đã mất
    chrome.storage.local.get(KHOA_BAN_CHO, (res) => {
      if (chrome.runtime.lastError) return;
      const v = res?.[KHOA_BAN_CHO]?.version;
      banMoiCho = typeof v === "string" && v && v !== dangChay ? v : "";
      if ($capNhatBtn) {
        $capNhatBtn.hidden = !banMoiCho;
        $capNhatBtn.title = banMoiCho ? `Đã có bản ${banMoiCho} (đang dùng ${dangChay}) — bấm để cập nhật ngay` : "";
      }
      if (!banMoiCho && $capNhatXn) $capNhatXn.hidden = true;
    });
  }

  function dangXuLyDo() {
    return busy || scanUploadingRel.size > 0 || deletingFileIds.size > 0
      || (window.HccTrangThai?.soRequestDangChay?.() || 0) > 0;
  }

  $capNhatBtn?.addEventListener("click", () => {
    if (!banMoiCho || !$capNhatXn) return;
    markActivity();
    $capNhatTieuDe.textContent = `Cập nhật Trợ lý lên bản ${banMoiCho}?`;
    $capNhatCanhBao.hidden = !dangXuLyDo();
    $capNhatNgay.disabled = false;
    $capNhatNgay.textContent = "Cập nhật ngay";
    $capNhatXn.hidden = false;
  });
  document.getElementById("cap-nhat-de-sau")?.addEventListener("click", () => {
    if ($capNhatXn) $capNhatXn.hidden = true;
  });
  $capNhatNgay?.addEventListener("click", () => {
    $capNhatNgay.disabled = true;
    $capNhatNgay.textContent = "Đang cập nhật…";
    const loi = (chu) => {
      $capNhatXn.hidden = true;
      setStatus(chu, true);
      setTimeout(() => setStatus(""), 5000);
      veNutCapNhat();
    };
    try {
      chrome.runtime.sendMessage({ action: "hccCapNhatNgay", tabId: Number(TAB_ID) || 0 }, (res) => {
        if (chrome.runtime.lastError) { loi("⚠️ Không gửi được lệnh cập nhật — thử lại sau."); return; }
        if (res?.ok) return; // extension sắp nạp lại: panel bị gỡ rồi trang tự tải lại
        if (res?.lyDo === "da-moi-nhat") {
          $capNhatXn.hidden = true;
          showToast("Trợ lý đã ở bản mới nhất.");
          veNutCapNhat();
          return;
        }
        loi("⚠️ Chưa kết nối được agent — thử lại sau.");
      });
    } catch (_) {
      loi("⚠️ Không gửi được lệnh cập nhật — thử lại sau.");
    }
  });
  chrome.storage.onChanged.addListener((thayDoi, vung) => {
    if (vung === "local" && KHOA_BAN_CHO in thayDoi) veNutCapNhat();
  });
  veNutCapNhat();

  // Thẻ hướng dẫn đặt giấy lên máy quét (ảnh + lời) — dựng MỘT lần khi máy quét sẵn sàng, đúng
  // như mockup panelScan. Ảnh là asset của chính extension (assets/scan-guide.jpg).
  // Dự phòng khi gặp server cũ chưa cấp scanGuide — CHỈ tiếng Việt, cùng lý do với
  // SCAN_FEEDBACK_FALLBACK: bản Mông chỉ có một nguồn là script_mong.py.
  const SCAN_GUIDE_FALLBACK = {
    heading: "🖨️ Đặt giấy tờ lên máy quét ở quầy",
    body: "Công dân đặt giấy lên máy scan **theo hướng dẫn trong hình** rồi ấn nút **Scan** ạ.",
    alt: "Hướng dẫn scan: đặt giấy úp mặt cần scan xuống rồi ấn nút Scan",
    zoom: "🔍 Bấm để xem hình to",
    note: "Chỉ đặt **từng tờ một** — máy tự kéo giấy vào. Xong hết thì bấm **\"Đã đưa đủ\"** giúp em.",
  };

  // Escape TRƯỚC rồi mới đổi **…** thành <b> — chữ do BE cấp không chèn được thẻ vào panel.
  function inlineBold(s) {
    return window.escapeHtml(String(s || "")).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  }

  function renderScanGuideCard() {
    if (scanGuideShown) return;
    scanGuideShown = true;
    const pack = voiceCfg?.scanGuide || {};
    const viG = pack.vi || SCAN_GUIDE_FALLBACK;
    // Chỉ chú thích Mông khi ĐANG bật tiếng Mông VÀ BE có gửi bản đó xuống.
    const hmG = (voiceLang === "hmong" && _hmongAllowed()) ? pack.hmong : null;
    // Chú thích Mông đi NGAY DƯỚI dòng Việt tương ứng — thẻ này là các dòng rời, không
    // gộp được thành một khối cuối như câu chat.
    const hm = (key) => (hmG?.[key] ? `<div class="scan-guide-hm">${inlineBold(hmG[key])}</div>` : "");
    const el = document.createElement("div");
    el.className = "scan-guide";
    const img = chrome.runtime.getURL("assets/scan-guide.jpg");
    // alt của ảnh dùng bản Mông khi có: trình đọc màn hình đang ở tiếng Mông.
    const alt = window.escapeHtml(hmG?.alt || viG.alt || "");
    el.innerHTML = `
      <div class="scan-guide-h">${inlineBold(viG.heading)}</div>${hm("heading")}
      <div class="scan-guide-p">${inlineBold(viG.body)}</div>${hm("body")}
      <div class="scan-guide-pic" data-zoom="1" title="${window.escapeHtml(viG.zoom || "")}">
        <img class="scan-guide-img" src="${img}" alt="${alt}">
        <span class="scan-guide-zoom">${inlineBold(hmG?.zoom || viG.zoom)}</span>
      </div>
      <div class="scan-guide-note">${inlineBold(viG.note)}</div>${hm("note")}`;
    el.querySelector("[data-zoom]")?.addEventListener("click", () => openImageZoom(img, alt));
    addNode(el);
  }

  // Toast thoáng qua (tự biến mất) — mount 1 container vào body của sidebar.
  let $toastWrap = null;
  function showToast(text, { ms = 2600 } = {}) {
    if (!$toastWrap) {
      $toastWrap = document.createElement("div");
      $toastWrap.className = "tlnd-toasts";
      $toastWrap.setAttribute("aria-live", "polite");
      document.body.appendChild($toastWrap);
    }
    const t = document.createElement("div");
    t.className = "tlnd-toast";
    t.textContent = text;
    $toastWrap.appendChild(t);
    requestAnimationFrame(() => t.classList.add("show"));
    setTimeout(() => { t.classList.remove("show"); setTimeout(() => t.remove(), 250); }, ms);
  }

  // Thông báo mỗi lần máy quét trả tệp: TEXT (chèn NGAY TRÊN danh sách giấy tờ, luôn thấy gần
  // nút "Đã đưa đủ") + VOICE (đọc hướng dẫn). Một node duy nhất, cập nhật tại chỗ theo tổng số tệp.
  // BE chưa cấp scanFeedback (server cũ) thì vẫn phải có chữ. Bản dự phòng CHỈ tiếng Việt:
  // không nhúng bản Mông ở đây để lời thoại Mông chỉ có một nguồn duy nhất (script_mong.py).
  const SCAN_FEEDBACK_FALLBACK = {
    md: "🖨️ Em đã nhận **{count} tệp** giấy tờ từ máy quét.\n\n"
      + "- Còn giấy tờ cần scan thì công dân **đặt tiếp tờ nữa** vào máy — em tự nhận ạ.\n"
      + "- Đã đủ rồi thì bấm **\"Đã đưa đủ giấy tờ\"** ở dưới để em bắt đầu xử lý ạ.",
    tts: "Em đã nhận được một tệp giấy tờ. Nếu còn giấy tờ, công dân đặt tiếp vào máy scan,"
      + " em sẽ tự nhận. Xong hết thì bấm nút Đã đưa đủ giấy tờ ạ.",
    ttsMore: "Em đã nhận thêm một tệp, tổng cộng {count} tệp. Còn nữa thì công dân đặt tiếp"
      + " vào máy scan, đủ rồi bấm nút Đã đưa đủ giấy tờ để em thực hiện xử lý ạ.",
  };

  function renderScanFeedback() {
    const n = scanReceivedCount;
    const pack = voiceCfg?.scanFeedback || {};
    const viPack = pack.vi || SCAN_FEEDBACK_FALLBACK;
    // Chỉ dùng bản Mông khi ĐANG bật tiếng Mông VÀ BE thực sự gửi bản đó xuống. Thiếu bản
    // dịch thì nói tiếng Việt bằng giọng Việt — KHÔNG đọc chữ Việt bằng giọng Mông.
    const hmPack = (voiceLang === "hmong" && _hmongAllowed()) ? pack.hmong : null;
    const fill = (s) => String(s || "").replace(/\{count\}/g, String(n));
    let md = fill(viPack.md);
    // Khối Mông in nghiêng ở CUỐI, đúng bố cục câu chat do BE dựng.
    if (hmPack?.md) md += `\n\n*${fill(hmPack.md)}*`;
    let el = document.getElementById("scan-feedback-card");
    if (!el) {
      el = document.createElement("div");
      el.id = "scan-feedback-card";
      el.className = "scan-feedback";
      const anchor = document.getElementById("doc-progress-card"); // chèn NGAY TRÊN danh sách
      if (anchor?.parentNode) anchor.parentNode.insertBefore(el, anchor);
      else addNode(el);
    }
    el.innerHTML = window.renderMarkdown ? window.renderMarkdown(md) : md;
    $messages.scrollTop = $messages.scrollHeight;
    // Đọc thành tiếng (rảnh tay). Tệp đầu đọc đủ hướng dẫn; các tệp sau đọc gọn để đỡ rườm.
    const spoken = hmPack || viPack;
    const tts = fill(n <= 1 ? spoken.tts : (spoken.ttsMore || spoken.tts));
    if (voiceCfg?.tts && !ttsMuted && tts) {
      try { stopReplyTts(); } catch (_) { /* ignore */ }
      window.__hccTTS?.speak?.(tts, hmPack ? "hmong" : "vi");
    }
  }

  // Lightbox phóng to ảnh — click nền hoặc Esc để đóng.
  function openImageZoom(src, alt) {
    const scrim = document.createElement("div");
    scrim.className = "img-zoom-scrim";
    scrim.innerHTML = `<img class="img-zoom-img" src="${src}" alt="${window.escapeHtml(alt || "")}">
      <button class="img-zoom-close" type="button" aria-label="Đóng">✕</button>`;
    const close = () => { scrim.remove(); document.removeEventListener("keydown", onKey); };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    scrim.addEventListener("click", close);
    document.addEventListener("keydown", onKey);
    document.body.appendChild(scrim);
  }

  function setScanAgentStatus(state) {
    if (!$scanStatus) return;
    // da_ket_noi: KHÔNG hiện dòng "đang theo dõi" (thẻ hướng dẫn + thông báo mỗi tệp đã lo).
    // Chỉ hiện khi cần cán bộ thao tác: chưa chọn thư mục quét.
    const text = state === "chua_chon_thu_muc"
      ? "🖨️ Máy quét chưa chọn thư mục lưu ảnh — mở agent ở khay hệ thống chọn giúp em ạ."
      : "";
    $scanStatus.textContent = text;
    $scanStatus.hidden = !text;
  }
  const scanFileMtimeMs = (evt) => Number(evt?.mtimeMs) || Date.parse(evt?.at || "") || 0;
  const scanBaseName = (rel) => String(rel || "").split(/[\\/]/).pop() || "tep-quet";

  // MỘT chỗ duy nhất cho mọi đường đưa tệp quét lên phiên: event file.added, lô gom lúc nối máy quét,
  // đối soát, và cán bộ bấm "+" ở danh sách gần đây (tuDong=false). Chốt chặn đặt ở đây để đường
  // thêm về sau không quên — cùng lý do với importOneScanFile bên autofill. Trả true khi phiên thật
  // sự có thêm/đổi tệp.
  async function onScanFile(evt, fetchBlob, { tuDong = true } = {}) {
    const rel = evt?.rel;
    if (!rel || !uploadSid || scanUploadingRel.has(rel) || scanDangDoiTen.has(rel)) return false;
    const mtime = scanFileMtimeMs(evt);
    // Watermark: bỏ tệp cũ hơn mốc (giấy của công dân TRƯỚC). Cán bộ tự chọn tay thì không chặn.
    if (tuDong && scanWatermarkMs && mtime && mtime <= scanWatermarkMs) return false;
    // Trần tuổi — CHỈ khi có mtimeMs (lô gom từ /v1/files). Event SSE không mang mtimeMs: chính sự
    // kiện là bằng chứng "vừa xuất hiện", siết theo mtime sẽ chặn nhầm tệp cũ vừa được chép vào.
    const tuoiToiDa = window.TLNDScanLo?.BATCH_AUTO_MAX_AGE_MS || 30 * 60 * 1000;
    if (tuDong && Number(evt.mtimeMs) && Date.now() - Number(evt.mtimeMs) > tuoiToiDa) return false;
    scanUploadingRel.add(rel);
    const sid = uploadSid;
    const ve = scanDongBo?.batDauTai(rel); // chốt TRƯỚC await đầu tiên — xem scanDongBo.taiXong
    try {
      if (uploadSessionProgress?.complete) return false;   // phiên đã chốt → không nhận thêm
      const blob = await fetchBlob();
      if (!blob || !blob.size) return false;               // bỏ tệp 0 byte (máy đang ghi dở)
      const hash = await sha256Hex(blob);
      if (tuDong) {
        // Nội dung này đã bị GỠ TAY → không tự đưa lại (gỡ là một quyết định, không phải thao tác tạm).
        if (scanDaGo.has(hash)) {
          console.info("[TLND] scan: bỏ qua tệp đã bị gỡ tay", rel);
          return false;
        }
      } else if (scanDaGo.delete(hash)) {
        luuDaGoScan(); // chủ động thêm lại → bỏ dấu, lần sau tự tải bình thường
      }
      // Cùng rel, cùng nội dung đã nằm trên phiên (agent bắn lại added khi mtime đổi mà nội dung y
      // nguyên, hoặc đối soát) → không tải lại.
      if (scanDongBo?.hashCua(rel) === hash) return false;
      const file = new File([blob], scanBaseName(rel), { type: blob.type || "application/octet-stream" });
      const data = await uploadFilesToSession([file], { source: "scan" });
      if (mtime > scanNewestMs) scanNewestMs = mtime;
      // BE trả `accepted` theo đúng thứ tự tệp gửi lên (router.upload_files) → gửi 1 tệp là accepted[0].
      const fid = data?.accepted?.[0]?.fid;
      let biGoNgay = false;
      let laCapNhat = false;
      if (scanDongBo && fid && sid === uploadSid) {
        for (const phaiXoa of scanDongBo.taiXong(ve, fid, hash)) {
          if (phaiXoa === fid) biGoNgay = true;      // tệp đã bị xoá khỏi đĩa trong lúc đang tải
          else laCapNhat = true;                     // máy quét ghi đè cùng tên → gỡ bản cũ
          await deleteUploadSessionFile({ fid: phaiXoa, name: scanBaseName(rel) });
        }
        void luuSoSachScan();
      }
      if (!data || biGoNgay) return false;
      if (scanRecentPending.some((f) => f.rel === rel)) {
        scanRecentPending = scanRecentPending.filter((f) => f.rel !== rel);
        hienDanhSachGanDay();
      }
      if (laCapNhat) {
        showToast(`🖨️ Đã cập nhật bản mới: ${scanBaseName(rel)}`);
      } else {
        scanReceivedCount += 1;
        showToast(`🖨️ Đã nhận: ${scanBaseName(rel)}`);
        renderScanFeedback(); // text (trên danh sách) + voice hướng dẫn, cập nhật tổng số tệp
      }
      return true;
    } catch (err) {
      console.warn("[TLND] scan: không tải được tệp từ máy quét", rel, err?.message || err);
      return false;
    } finally {
      scanUploadingRel.delete(rel);
    }
  }
  async function onScanFileRemoved(evt) {
    const rel = evt?.rel;
    if (!rel) return;
    // Cặp event do CHÍNH mình đổi tên — tệp vẫn là tệp đó, sổ đã dời sang rel mới (ketThucSuaTen).
    if (scanDangDoiTen.has(rel)) return;
    if (scanRecentPending.some((f) => f.rel === rel)) {
      scanRecentPending = scanRecentPending.filter((f) => f.rel !== rel);
      hienDanhSachGanDay();
    }
    if (!uploadSid || uploadSessionProgress?.complete) return;
    // Gỡ ĐÚNG tệp mình đã tải lên cho rel này. Không đoán theo tên như bản cũ: tệp trùng tên có thể là
    // giấy công dân tự tải từ điện thoại. rel không do mình tải lên → daXoa trả null → không gỡ.
    const fid = scanDongBo?.daXoa(rel);
    void luuSoSachScan();
    if (fid) await deleteUploadSessionFile({ fid, name: scanBaseName(rel) });
  }
  function connectScanAgent() {
    if (scanConn || !window.ScanAgent) return;
    scanConn = window.ScanAgent.connect({
      onStatus: (state) => {
        scanAgentConnected = state === "da_ket_noi";
        if (scanAgentConnected && scanPickerTimer) { clearTimeout(scanPickerTimer); scanPickerTimer = null; }
        setScanAgentStatus(state);
      },
      onFile: (evt, fetchBlob) => { void onScanFile(evt, fetchBlob); },
      onFileRemoved: (evt) => { void onScanFileRemoved(evt); },
      // Agent báo bản extension trên đĩa ≠ bản đang chạy → nhờ background kiểm NGAY. Background giữ
      // mọi luật "chỉ nạp lại khi rảnh" và gỡ panel trước khi nạp; thiếu đường này thì chờ nhịp 1 phút.
      onExtensionVersion: (v) => {
        try {
          if (v && v !== chrome.runtime.getManifest().version) {
            const p = chrome.runtime.sendMessage({ action: "hccKiemBanMoiNgay" }, () => void chrome.runtime.lastError);
            if (p && typeof p.catch === "function") p.catch(() => {}); // trình duyệt trả Promise dù có callback
          }
        } catch (_) { /* context mất — background tự lo theo nhịp */ }
      },
      onConnected: (helpers) => {
        scanAgentHelpers = helpers;
        // Agent bản cũ không khai caps → mảng rỗng → nút sửa tên tệp quét bị ẩn (khỏi bấm rồi ăn 404).
        const caps = Array.isArray(helpers?.caps) ? helpers.caps : [];
        const doiCaps = caps.join() !== scanAgentCaps.join();
        scanAgentCaps = caps;
        if (doiCaps && activeFileGroup) renderUploadFileList();
        void (async () => {
          await doiSoatTepQuet();
          await thuGomLoQuet();
        })();
      },
    });
  }
  function disconnectScanAgent() {
    if (scanPickerTimer) { clearTimeout(scanPickerTimer); scanPickerTimer = null; }
    try { scanConn?.stop(); } catch (_) { /* ignore */ }
    scanConn = null;
    scanAgentConnected = false;
    scanUploadingRel.clear();
    scanAgentHelpers = null;
    scanAgentCaps = [];
    scanLoDaThuSid = "";
    scanDoiSoatSid = "";
    scanGuideShown = false;
    scanReceivedCount = 0;
    setScanAgentStatus("");
  }
  // Nâng mốc khi bắt đầu phục vụ CÔNG DÂN MỚI (trò chuyện mới / thủ tục khác / logout) → không
  // tự kéo lại giấy tờ đã quét của người trước.
  function bumpScanWatermark() {
    if (scanNewestMs > scanWatermarkMs) scanWatermarkMs = scanNewestMs;
    scanNewestMs = 0;
    scanUploadingRel.clear();
    scanDongBo?.datLai();
    scanRecentPending = [];
    hienDanhSachGanDay();
    // Lưu mốc: iframe dựng lại sau điều hướng mà mất mốc là quay lại đúng lỗi "kéo giấy người trước".
    try { void chrome.storage.local.set({ [KHOA_WATERMARK_SCAN]: scanWatermarkMs }); } catch (_) { /* ignore */ }
  }

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

  // Doc-row có tệp: nhấn CẢ DÒNG để xem trước (nút "Đã nhận N tệp ›" vẫn mở danh sách như cũ).
  function batXemTruocChoDong(row, group) {
    row.classList.add("co-xem");
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.title = "Nhấn để xem trước các tệp đã nhận";
    row.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      void moPreviewNhom(group, 0);
    });
    row.addEventListener("keydown", (e) => {
      if (e.target !== row || (e.key !== "Enter" && e.key !== " ")) return;
      e.preventDefault();
      void moPreviewNhom(group, 0);
    });
  }

  function renderDocProgress(p, { preserveScroll = false } = {}) {
    queueMicrotask(() => void hienLoiMoiHoSoTruoc(Number(p?.files_count)));
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
        batXemTruocChoDong(row, {
          docKey: d.key, name: d.name || "Giấy tờ đã nhận", icon: d.icon || "📄", unknown: false,
        });
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
      batXemTruocChoDong(row, {
        docKey: null, name: "Tệp chưa nhận ra loại", icon: "⚠️", unknown: true,
      });
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
          // Kéo ngầm NGAY khi tệp về, trong lúc công dân còn đang chụp tệp sau → tới bước đính
          // thì phần lớn đã nằm sẵn trên máy, không phải ngồi chờ tải.
          void prefetchSessionFiles(uploadSid);
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
  // ===== Kho bytes tại chỗ =====
  // Đính kèm từng phải TẢI LẠI toàn bộ giấy tờ từ máy chủ, trong khi:
  //   - Scan/chọn tệp: bytes VỐN nằm trong sidebar trước khi upload → tải lại là phí 100%.
  //   - QR: tệp về từ lúc công dân còn đang chụp → kéo sẵn thì tới lúc đính đã có ở máy.
  //
  // Cache giữ BLOB chứ không giữ dataUrl: Blob là tham chiếu, trình duyệt tự đẩy xuống đĩa khi
  // cần → không phình heap, nhờ vậy KHÔNG cần trần dung lượng và đường scan mới dám nói là
  // không tải lại lần nào. Base64 để tới lúc đính mới làm (≈50-150ms cho 9MB, chạy song song).
  let fileCache = new Map();        // fid -> { name, type, blob }
  let fileCacheSid = "";
  const fileInFlight = new Map();   // fid -> Promise — gộp prefetch với lần tải lúc đính

  function resetFileCache(sid) {
    if (fileCacheSid === sid) return;
    fileCacheSid = sid || "";
    fileCache = new Map();
    fileInFlight.clear();
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      // FileReader.error là DOMException (NotReadableError / NotFoundError…). PHẢI reject NÓ, KHÔNG
      // reject cái ProgressEvent (onerror nhận event) — String(event) = "[object ProgressEvent]"
      // nuốt mất lý do thật, khiến trợ lý báo "[object ProgressEvent]" vô nghĩa.
      r.onerror = () => reject(r.error || new Error("Không đọc được nội dung tệp."));
      try { r.readAsDataURL(blob); }
      catch (e) { reject(e instanceof Error ? e : new Error("Không đọc được nội dung tệp.")); }
    });
  }

  /** Tải 1 tệp, thử lại khi chớp mạng. Không có retry thì một cú 502 giết cả lượt đính kèm. */
  async function downloadSessionFile(sid, fid, name) {
    let lastError = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const fr = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${sid}/files/${fid}`);
        if (fr.ok) {
          const blob = await fr.blob();
          return { name, type: blob.type || "image/jpeg", blob };
        }
        // 4xx = tệp không còn/không có quyền → thử lại vô ích.
        if (fr.status >= 400 && fr.status < 500) throw new Error(`HTTP ${fr.status}`);
        lastError = new Error(`HTTP ${fr.status}`);
      } catch (e) {
        lastError = e;
        if (String(e?.message || "").startsWith("HTTP 4")) break;
      }
      if (attempt < 3) await new Promise((ok) => setTimeout(ok, 800 * attempt));
    }
    throw new Error(`Không tải được tệp ${name}${lastError ? ` (${lastError.message})` : ""}.`);
  }

  /** Một fid chỉ tải ĐÚNG MỘT LẦN dù prefetch và bước đính cùng hỏi. */
  function ensureFileBytes(sid, fid, name) {
    resetFileCache(sid);
    const hit = fileCache.get(fid);
    if (hit) return Promise.resolve(hit);
    const flying = fileInFlight.get(fid);
    if (flying) return flying;
    const job = downloadSessionFile(sid, fid, name)
      .then((entry) => { fileCache.set(fid, entry); return entry; })
      .finally(() => fileInFlight.delete(fid));
    fileInFlight.set(fid, job);
    return job;
  }

  /** Giữ lại bytes ĐANG cầm trên tay (scan/chọn tệp) — đường này không tải về lần nào. */
  async function cacheUploadedBlobs(sid, files, accepted) {
    resetFileCache(sid);
    // Ghép fid với tệp theo THỨ TỰ; lệch độ dài thì BỎ cache hẳn. Ghép nhầm sẽ đính NHẦM
    // giấy tờ — hậu quả nặng hơn nhiều so với việc phải tải lại.
    if (!Array.isArray(accepted) || accepted.length !== files.length) {
      console.warn("[TLND] accepted lệch số tệp, bỏ cache bytes", {
        accepted: accepted?.length, files: files.length,
      });
      return;
    }
    for (let i = 0; i < accepted.length; i++) {
      const fid = accepted[i]?.fid;
      if (!fid || fileCache.has(fid)) continue;
      // BE trả kèm `name` → đối chiếu được, không tin mù vào thứ tự.
      const serverName = accepted[i]?.name;
      if (serverName && files[i]?.name && serverName !== files[i].name) {
        console.warn("[TLND] tên tệp lệch, bỏ cache bytes", { serverName, local: files[i].name });
        return;
      }
      fileCache.set(fid, {
        name: files[i].name,
        type: files[i].type || "application/octet-stream",
        blob: files[i],
      });
    }
  }

  /** Kéo ngầm tệp vừa về (QR) để lúc đính đã có sẵn. Lỗi thì im lặng — lúc đính tải lại. */
  async function prefetchSessionFiles(sid) {
    if (!sid) return;
    try {
      const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${sid}`);
      if (!res.ok) return;
      const sess = await res.json();
      resetFileCache(sid);
      await Promise.all((sess.files || [])
        .filter((f) => f?.fid && !fileCache.has(f.fid))
        .map((f) => ensureFileBytes(sid, f.fid, f.name).catch(() => null)));
    } catch (_) { /* prefetch hỏng không ảnh hưởng luồng chính */ }
  }

  /** Đọc MỘT tệp thành dataUrl BỀN BỈ. Blob đang cầm (cache cục bộ/scan) có thể không đọc được
   *  (tệp trên đĩa đã đổi/mất, blob rỗng/hỏng, hoặc RAM dồn). Server LUÔN giữ bản đã nhận hợp lệ
   *  → hỏng thì tải lại từ phiên rồi đọc lại, thử vài vòng. Chỉ khi cạn mọi cách mới ném lỗi
   *  TIẾNG VIỆT nêu rõ tệp nào để cán bộ quét/chọn lại. Nhờ vậy hầu như không bao giờ đính hụt. */
  async function readEntryToDataUrl(sid, f, entry) {
    if (entry?.blob && entry.blob.size) {
      try { return { entry, dataUrl: await blobToDataUrl(entry.blob) }; }
      catch (e) { console.warn("[TLND] đọc blob cục bộ lỗi, sẽ tải lại từ phiên:", f?.name, e?.name || e?.message || e); }
    }
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        fileCache.delete(f.fid);
        const fresh = await downloadSessionFile(sid, f.fid, f.name);   // đã tự retry mạng 3 lần
        if (!fresh?.blob || !fresh.blob.size) throw new Error("tệp rỗng từ hệ thống");
        const dataUrl = await blobToDataUrl(fresh.blob);
        fileCache.set(f.fid, fresh);
        return { entry: fresh, dataUrl };
      } catch (e) {
        console.warn(`[TLND] tải lại+đọc tệp lỗi (vòng ${attempt}):`, f?.name, e?.name || e?.message || e);
        await new Promise((ok) => setTimeout(ok, 600 * attempt));
      }
    }
    throw new Error(
      `Không đọc được tệp "${f?.name || "giấy tờ"}" (đã thử lấy lại từ hệ thống nhiều lần). `
      + `Công dân vui lòng quét hoặc chọn lại tệp này rồi bấm đính kèm lại giúp em ạ.`
    );
  }

  async function fetchSessionFilesAsPayload(sid) {
    const res = await uploadSessionFetch(`${BASE_URL}/api/v1/upload-sessions/${sid}`);
    if (!res.ok) throw new Error(`Không lấy được danh sách giấy tờ của phiên (mã ${res.status}). Vui lòng thử lại.`);
    const sess = await res.json();
    resetFileCache(sid);
    const list = sess.files || [];
    // ĐỌC TUẦN TỰ (KHÔNG Promise.all): đọc nhiều tệp lớn thành base64 CÙNG LÚC làm dồn RAM →
    // FileReader lỗi. Tuần tự chậm hơn chút nhưng không bao giờ vỡ vì bộ nhớ.
    const out = [];
    for (let i = 0; i < list.length; i++) {
      const f = list[i];
      setStatus(`📥 Đang chuẩn bị giấy tờ ${i + 1}/${list.length}…`);
      const entry = await ensureFileBytes(sid, f.fid, f.name);
      const { entry: readEntry, dataUrl } = await readEntryToDataUrl(sid, f, entry);
      // Tên cán bộ đã sửa (tenHienThi) phải đi vào payload đính kèm, không chỉ hiện trên danh sách.
      out.push({ name: tenHienThi(f) || readEntry.name, type: readEntry.type, dataUrl });
    }
    setStatus("");
    return out;
  }

  /** Đổi MỌI lỗi (kể cả DOMException tiếng Anh của trình duyệt) thành câu TIẾNG VIỆT người dân
   *  hiểu được, đúng tình huống. Câu ta tự ném (đã có dấu tiếng Việt) thì giữ nguyên. */
  function viAttachError(e) {
    const raw = String(e?.message ?? e ?? "").trim();
    if (!raw) return "Chưa chuẩn bị được giấy tờ để đính kèm. Công dân vui lòng thử đính kèm lại ạ.";
    if (/[^\x00-\x7F]/.test(raw)) return raw; // có ký tự tiếng Việt = câu của mình → giữ nguyên
    const low = raw.toLowerCase();
    if (/notreadable|could not be read|not be read/.test(low))
      return "Không đọc được nội dung một tệp giấy tờ (tệp có thể đã bị di chuyển hoặc thay đổi trên máy). Công dân vui lòng quét/chọn lại tệp rồi đính kèm lại ạ.";
    if (/notfound|no such file|not found/.test(low))
      return "Một tệp giấy tờ không còn tìm thấy trên máy. Công dân vui lòng quét/chọn lại tệp rồi đính kèm lại ạ.";
    if (/network|failed to fetch|load failed|http [45]\d\d|timeout|timed out/.test(low))
      return "Mất kết nối khi lấy giấy tờ từ hệ thống. Công dân kiểm tra mạng rồi bấm đính kèm lại giúp em ạ.";
    if (/quota|memory|allocation/.test(low))
      return "Giấy tờ quá lớn nên máy xử lý chưa xong. Công dân thử đính lại từng tệp giúp em ạ.";
    return "Chưa đính được giấy tờ do sự cố kỹ thuật. Công dân vui lòng bấm đính kèm lại giúp em ạ.";
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

  // giấy tờ thật xuống dòng "Thêm thành phần". Ô cố định STT1 nhận 1 file ẢO = COPY (đổi tên) của 1
  // file thật (DÙNG LẠI fileIndex → không tốn payload). No-op (null) cho account/thủ tục khác.
  function buildStt1VirtualItem(directive, source, files) {
    if (!directive || !source) return null;
    const idx = Number.isInteger(source.fileIndex) ? source.fileIndex : -1;
    if (idx < 0 || !Array.isArray(files) || !files[idx]) return null;
    const srcName = files[idx]?.name || source.documentName || "tai-lieu";
    return {
      ...source,
      virtualCopy: true,
      target: "existing",
      componentIndex: directive.componentIndex || 1,
      componentName: directive.componentName || source.componentName || "",
      needsAddComponent: false,
      appendOnOccupied: false,
      documentName: directive.documentName || srcName,
      fileIndex: idx,
      sourceFileIndexes: [idx],
      fileName: srcName,
    };
  }

  function buildCopyCertificationSplitBundles(files, attachments, stt1Virtual = null) {
    const bundles = [];
    for (let index = 0; index < (attachments || []).length; index++) {
      const item = attachments[index] || {};
      const file = Number.isInteger(item.fileIndex) ? files[item.fileIndex] : files[index];
      if (!file) continue;
      const real = {
        ...item,
        fileIndex: 0,
        sourceFileIndexes: [0],
        fileName: file.name || item.fileName,
        documentName: item.documentName || file.name,
      };
      const bundleAttachments = [real];
      // Hải Châu: mỗi tab thêm 1 file ẢO vào STT1 = copy chính file của tab (fileIndex 0 trong bundle).
      if (stt1Virtual) {
        const virtual = buildStt1VirtualItem(stt1Virtual, real, [file]);
        if (virtual) bundleAttachments.push(virtual);
      }
      bundles.push({ files: [file], attachments: bundleAttachments });
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
      // Tệp không có quan hệ hồ sơ (vd giấy tùy thân không khớp người ký nào) thì BỎ RIÊNG tệp đó
      // rồi đính tiếp phần còn lại. Trước đây hủy cả lượt: hỏng 1 tệp là mất cả 4, mà kế hoạch được
      // phát lại y nguyên nên bấm "Đính kèm lại" hỏng mãi (sự cố Nghĩa Hưng 21/09/2026).
      const usable = entries.filter((entry) => entry.planItem?.bundleId
        && ["signature_document", "identity"].includes(entry.planItem?.bundleRole));
      const skippedNames = entries.filter((entry) => !usable.includes(entry))
        .map((entry) => entry.file?.name || entry.planItem?.fileName || "một tệp");
      if (!usable.some((entry) => entry.planItem.bundleRole === "signature_document")) {
        return { error: "Kế hoạch nhiều hồ sơ không có giấy tờ, văn bản cần chứng thực chữ ký." };
      }
      if (skippedNames.length) {
        console.warn("[TLND-Split] bỏ tệp không có quan hệ hồ sơ:", skippedNames);
      }

      const bundleOrder = [];
      const grouped = new Map();
      for (const entry of usable) {
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
      return { bundles, skippedNames };
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
      : { bundles: buildCopyCertificationSplitBundles(files, attachments, a.stt1VirtualCopy) };
    if (built.error) return { report: { attached: 0, errors: [built.error], mode: "split" } };
    // Nói rõ tệp bị bỏ ngay tại chỗ: BE chỉ biết những tệp CHÍNH NÓ loại, còn tệp rơi ở đây là
    // phần BE bản cũ vẫn gửi sang. Không đọc thành tiếng — không phải việc công dân phải xử lý.
    if (built.skippedNames?.length) {
      addBotMd(`⚠️ Em bỏ qua ${built.skippedNames.length} tệp chưa xếp được vào hồ sơ nào: `
        + built.skippedNames.join(", ") + ". Các hồ sơ còn lại em đính bình thường ạ.");
    }
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
      // Tab của sidebar này — background chuyển tiếp mốc "Nộp" của các tab tách về đây.
      originTabId: Number(TAB_ID) || null,
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
      // Bước "Thành phần hồ sơ" KHÁC nhau theo cổng (tư pháp = 3, MAE = 2) → BE gửi kèm
      // attach_step theo wizard của thủ tục; thiếu thì giữ mặc định 3 như trước.
      const attachStep = Number(a.attach_step) || 3;
      const pre = await sendToContent({ action: "getPageContext" });
      if (pre?.ok && pre.wizardStep && pre.wizardStep !== attachStep) {
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
      // Hải Châu merge 1 tab: chèn 1 file ẢO vào STT1 (BE đã đẩy giấy tờ thật xuống dòng "Thêm
      // thành phần"). Directive chỉ có với account đó → account khác giữ nguyên `attachments`.
      let sendAttachments = attachments;
      if (a.stt1VirtualCopy) {
        const src = attachments.find((x) => x && Number.isInteger(x.fileIndex) && files[x.fileIndex])
          || attachments[0];
        const virtual = buildStt1VirtualItem(a.stt1VirtualCopy, src, files);
        if (virtual) sendAttachments = [virtual, ...attachments];
      }
      const res = await sendToContent({
        action: "attachFilesByPlan",
        files,
        attachments: sendAttachments,
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
      // Lỗi ra cho người dân PHẢI là tiếng Việt, đúng tình huống — không để lọt "[object …]" hay
      // câu lỗi tiếng Anh của trình duyệt.
      ask(`__action:attach_report:${JSON.stringify({
        attached: 0,
        errors: [viAttachError(e)],
        ...(dispatchId ? { dispatch_id: dispatchId } : {}),
      })}`, "system");
    } finally {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    }
  }

  // ── Thi hành actions từ BE (tuần tự) ──
  async function runActions(actions) {
    for (const a of actions) {
      if (a.type === "arm_submit_watch") {
        await armSubmitWatch(a.rules);
      } else if (a.type === "new_conversation") {
        // Công dân NÓI "làm thủ tục khác" (chip đã tự xử ở renderChips). Một conversation =
        // một hồ sơ, nên đi đúng luồng của chip: xoá phiên rồi mở phiên mới.
        await returnToStart("manual");
        return;
      } else if (a.type === "navigate" && a.url) {
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
        setStatus(a.workflow === "change"
          ? "Đang mở luồng Đăng ký thay đổi hộ kinh doanh…"
          : "Đang mở trang kê khai Thành lập mới hộ kinh doanh…");
        const res = await sendToContent({
          action: "prepareBusinessRegistration",
          workflow: a.workflow || "",
          stop_at: a.stop_at || "",
        });
        if (res?.error) {
          setStatus("", false);
          addBotMd(`⚠️ ${res.error}`);
        }
      } else if (a.type === "start_business_registration" && a.pages) {
        pipeDone();
        setStatus("Đang chuẩn bị các khối dữ liệu và giấy tờ đính kèm…");
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
            // Luồng thay đổi HKD: adapter cần workflow + businessFlow (khóa tra cứu hộ KD,
            // pageOrder động) — thiếu là nó bootstrap nhầm CREATE rồi đứng im ở màn tra cứu.
            workflow: a.workflow || "",
            businessFlow: a.businessFlow || null,
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
            errors: [viAttachError(e)],
          })}`, "system");
        }
      } else if (a.type === "guided_click_next") {
        // Hoãn khỏi lượt hiện tại: runActions chạy BÊN TRONG ask() lúc cờ busy còn bật, nên
        // ask() lồng bên trong chỉ nằm lại pendingQueue và chờ ask() ngoài xong — mà ask()
        // ngoài lại đang chờ chính runActions → khoá cứng, bot im luôn sau khi bấm nút.
        const phase = a.phase || "";
        const expect = Number(a.expectStep) || 0;
        setTimeout(() => { void runGuidedNext(phase, expect); }, 0);
      } else if (a.type === "guided_submit") {
        setTimeout(() => { void runGuidedSubmit(); }, 0);
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
        const res = await sendToContent({
          action: "selectAgency",
          province: a.province,
          ward: a.ward,
          // Cổng bộ ngành (GD&ĐT...): chuyển toggle "Sở" (không chọn sở cụ thể) rồi Đồng ý.
          soMode: a.soMode === true,
        });
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
        uploadAutoRunSid = ""; // QR: ảnh về lần lượt từ điện thoại — không tự chốt theo đợt
        setUploadSession(a.session_id);
        renderQrCard(a);
        subscribeUploadSession(a.session_id);
      } else if (a.type === "resume_upload_session" && a.session_id) {
        // Điều chỉnh giấy tờ: dựng ngay checklist của CHÍNH phiên cũ. QR/Scan chỉ là
        // lựa chọn thêm tệp; công dân có thể chỉ xóa rồi bấm hoàn tất điều chỉnh.
        uploadAutoRunSid = "";
        const snapshotPromise = setUploadSession(a.session_id);
        subscribeUploadSession(a.session_id);
        await snapshotPromise;
      } else if (a.type === "pick_files" && a.session_id) {
        // Scan tại quầy: ưu tiên MÁY QUÉT (scan-bridge) — file quét ra tự vào cùng phiên upload,
        // không cần bấm. Nếu máy CHƯA cài agent (không kết nối trong ~1.5s) thì mở hộp chọn tệp
        // như cũ để vẫn dùng được. Agent đã kết nối sẵn (nối từ chặng trước) → bỏ qua hộp chọn.
        uploadAutoRunSid = a.auto_run === true ? a.session_id : "";
        setUploadSession(a.session_id);
        subscribeUploadSession(a.session_id);
        connectScanAgent();
        // Thẻ hướng dẫn đã dựng lúc chọn "Scan tại quầy" (renderDocOptions) — ở trên checklist.
        renderScanGuideCard(); // guard scanGuideShown → no-op nếu đã dựng; cứu ca khôi phục phiên
        if (scanPickerTimer) clearTimeout(scanPickerTimer);
        if (scanAgentConnected) { /* đang theo dõi máy quét → không bật hộp chọn tệp */ }
        else scanPickerTimer = setTimeout(() => {
          scanPickerTimer = null;
          if (!scanAgentConnected) $fileInput?.click();
        }, 1500);
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
      } else if (a.type === "fill_mae_agency") {
        // Cổng Bộ NN&MT: engine content/portal-mae.js điền Tỉnh + Sở + Trường hợp giải quyết
        // rồi bấm "Đồng ý và tiếp tục". Thành công thì SPA tự chuyển trang kê khai — im lặng
        // để watcher đọc page_status; chỉ báo BE khi LỖI (BE dặn chọn tay).
        setStatus("Đang chọn cơ quan và trường hợp giải quyết…");
        const res = await sendToContent({
          action: "fillMaeAgency",
          province: a.province || "",
          agency: a.agency || "",
          variant: a.variant || "",
          variantMatch: a.variantMatch || "",
          variantAvoid: a.variantAvoid || "",
        });
        if (res?.ok) {
          setStatus("Đã chọn cơ quan và trường hợp xong ✓");
          setTimeout(() => setStatus(""), 4000);
        } else {
          setStatus("");
          ask(`__event:mae_agency_failed:${res?.error || "trang chưa sẵn sàng"}`, "system");
        }
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
  if (EMBEDDED) {
    document.getElementById("min-btn")?.addEventListener("click", minimizePanel);
    document.getElementById("close-btn")?.addEventListener("click", closePanel);
    document.getElementById("login-min-btn")?.addEventListener("click", minimizePanel);
    document.getElementById("login-close-btn")?.addEventListener("click", closePanel);
  } else {
    // Khung bên do trình duyệt sở hữu: đóng/thu gọn là việc của nó. Để nút ở đó mà
    // bấm không ăn gì còn tệ hơn không có nút.
    for (const id of ["min-btn", "close-btn", "login-min-btn", "login-close-btn"]) {
      const b = document.getElementById(id);
      if (b) b.hidden = true;
    }
    // Giữ một port tới background suốt đời khung bên: port đứt = khung đã đóng → background báo
    // content.js hiện lại nút tròn. Chrome dọn service worker cũng làm đứt port trong khi khung vẫn
    // mở → tự nối lại để background dựng lại trạng thái "đang mở".
    const noiKhungBen = () => {
      if (!TAB_ID || !chrome.runtime?.id) return; // extension vừa được nạp lại — dừng hẳn
      try {
        const port = chrome.runtime.connect({ name: `tlnd-khung-ben:${TAB_ID}` });
        port.onDisconnect.addListener(() => {
          void chrome.runtime.lastError;
          setTimeout(noiKhungBen, 1000);
        });
      } catch (_) { setTimeout(noiKhungBen, 3000); }
    };
    noiKhungBen();
  }

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

  // Xóa phiên đăng nhập của công dân rồi đưa trang về DVCQG cho lượt tiếp theo.
  // Tách khỏi returnToStart và gọi trong finally: đây là việc KHÔNG được phép lỡ — lỡ một lần
  // là công dân sau ngồi vào máy còn nguyên đăng nhập của người trước. Trước đây khối này nằm
  // CUỐI một try…finally không có catch, nên bất kỳ bước dọn nào ở trên ném lỗi là nó bị bỏ
  // qua hoàn toàn, không một dòng cảnh báo.
  async function clearCitizenSessionAndGoHome() {
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

  // Một đường dọn phiên dùng chung cho: hoàn thành, timeout và nút Trò chuyện mới.
  async function returnToStart(reason = "manual") {
    if (endingSession) return;
    if (busy) { pendingReturnReason = reason; return; }
    endingSession = true;
    try {
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
      // Kết thúc CÓ CHỦ ĐÍCH một hồ sơ (bấm Trò chuyện mới / nộp xong) → cất tham chiếu giấy tờ để cùng
      // công dân làm thủ tục tiếp dùng lại. Hết giờ vì bỏ đi (idle) thì không mời.
      if (reason === "manual" || reason === "completed") catHoSoTruoc();
      resetUploadFileListState();
      // Công dân MỚI: nâng mốc watermark (chặn kéo lại giấy người trước) + ngắt máy quét để
      // chặng sau nối lại sạch.
      bumpScanWatermark();
      disconnectScanAgent();
      // Lý do kết thúc đi kèm để BE đóng sổ hồ sơ dở dang đúng nguyên nhân.
      await api.deleteConversation(reason || "manual");
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
        showProcedurePicker();
      } else {
        showStartScreen();
      }
      // "Trò chuyện mới" THỦ CÔNG: đưa CẢ trang web về trang chủ DVCQG cho lượt công dân mới
      // (không chỉ màn bắt đầu của sidebar). Đang ở trang chủ rồi thì thôi (navigate = reload
      // thừa); hết 20 phút (idle) giữ nguyên trang; "completed" điều hướng ở finally bên dưới.
      const alreadyOnDvcHome = START_FRESH_ON_DVC_HOME;
      if (reason === "manual" && !alreadyOnDvcHome) {
        const homeNav = await sendToContent({ action: "navigate", url: DVC_HOME_URL });
        if (!homeNav?.ok) {
          console.warn("[TLND] Không thể tự trở về trang chủ DVCQG", homeNav);
          setStatus("⚠️ Không thể tự trở về trang chủ Dịch vụ công Quốc gia. Công dân vui lòng mở trang chủ giúp em ạ.", true);
        }
      }
    } catch (error) {
      // Không nuốt im: returnToStart được gọi không await ở nhiều nơi nên lỗi ở đây từng biến
      // thành unhandled rejection lẫn trong console của trang, rất khó lần ra.
      console.error(`[TLND] Lỗi khi kết thúc phiên (reason=${reason})`, error);
    } finally {
      // finally chứ không phải cuối thân try: một bước dọn ở trên ném lỗi cũng KHÔNG được
      // phép làm lỡ việc xóa phiên công dân. Vẫn giữ đúng thứ tự "dọn phiên rồi mới điều
      // hướng" vì cả hai nằm trong clearCitizenSessionAndGoHome.
      if (reason === "completed") {
        try {
          await clearCitizenSessionAndGoHome();
        } catch (error) {
          console.error("[TLND] Lỗi khi xóa phiên công dân", error);
          setStatus("⚠️ Chưa xóa được phiên đăng nhập của công dân. Cán bộ vui lòng đăng xuất thủ công trên cổng trước khi tiếp nhận người tiếp theo.", true);
        }
      }
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
    showProcedurePicker();
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
  // Khi card đánh giá bật ghi âm ý kiến: ASR đổ transcript vào ĐÂY (ô ý kiến) thay vì gửi chat.
  // (text, isFinal) => void; null = ASR chạy như bình thường (câu hỏi hội thoại).
  let ratingNoteSink = null;
  let emptyTurns = 0; // rảnh tay: 2 lượt liên tiếp không nghe thấy gì → tự tắt
  let BASE_URL = "";
  const $micBtn = document.getElementById("mic-btn");
  const $hfBtn = document.getElementById("handsfree-btn");

  // ── Chế độ tiếng Mông (Hmong) — BE quyết định qua conv.lang; sidebar chỉ mirror ──
  // Switch CHỈ hiện khi: BE bật hmong (/voice/config.langs) VÀ tài khoản thuộc tỉnh Lai Châu.
  // Lựa chọn LƯU THEO MÁY QUẦY (chrome.storage tlnd_lang): phiên chat bị tạo mới (reload
  // trang chủ DVC, hết 20 phút, "Trò chuyện mới") thì tự khôi phục lặng lẽ — trước đây
  // trạng thái chỉ sống trong conversation nên reload là switch tắt.
  let voiceLang = "vi"; // "vi" | "hmong" — dùng cho ASR (asr-start) + fallback giọng đọc
  let voiceCfgLoaded = false; // chưa fetch xong /voice/config thì KHÔNG được reset switch
  let hmongRestoredConv = ""; // đã tự khôi phục cho conversation nào (chống gửi lặp)
  const LANG_KEY = "tlnd_lang";
  // Giọng đọc máy quầy đã chọn, THEO TỪNG NGÔN NGỮ: { vi: "...", hmong: "..." }. Lưu theo máy
  // (không theo phiên) giống tlnd_lang — phiên mới/reload vẫn giữ đúng giọng cán bộ quen nghe.
  const VOICE_KEY = "tlnd_voice";
  let voiceChoice = {};
  const $voiceCard = document.getElementById("voice-card");
  const $voiceGroup = document.getElementById("voice-group");
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

  // ── Giọng đọc ──
  // Danh mục do BE cấp (/voice/config → voices) nên thêm giọng KHÔNG phải phát hành lại
  // extension. Ẩn cả thẻ khi ngôn ngữ chỉ có MỘT giọng: bày một ô chọn duy nhất bấm vào
  // không đổi gì là làm cán bộ tưởng hỏng.
  function renderVoiceSettings() {
    if (!$voiceCard || !$voiceGroup) return;
    const list = (voiceCfg?.voices || {})[voiceLang] || [];
    $voiceCard.hidden = list.length < 2;
    if ($voiceCard.hidden) { $voiceGroup.replaceChildren(); return; }
    const current = voiceChoice[voiceLang] || (voiceCfg?.defaultVoice || {})[voiceLang] || "";
    $voiceGroup.replaceChildren(...list.map((v) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", String(v.id === current));
      // aria-checked chỉ trình đọc màn hình nghe được. Ô đang chọn phải TÔ bằng .on như mọi
      // .settings-seg khác, nếu không cán bộ nhìn hai ô giống hệt nhau, bấm rồi cũng không
      // biết đã đổi chưa.
      btn.classList.toggle("on", v.id === current);
      btn.textContent = `${v.gender === "nam" ? "👨" : "👩"} ${v.label}`;
      btn.addEventListener("click", () => saveVoice(v.id));
      return btn;
    }));
  }

  function saveVoice(id) {
    voiceChoice = { ...voiceChoice, [voiceLang]: id };
    renderVoiceSettings();
    window.__hccTTS?.setVoice?.(voiceChoice);
    chrome.storage?.local.set({ [VOICE_KEY]: voiceChoice }, () => {
      if (chrome.runtime.lastError) {
        if ($settingsSaved) $settingsSaved.textContent = "Chưa lưu được cài đặt.";
        return;
      }
      announceAttachmentSettingsSaved();
    });
  }

  chrome.storage?.local.get([VOICE_KEY], (res) => {
    if (chrome.runtime.lastError) return;
    const saved = res?.[VOICE_KEY];
    if (saved && typeof saved === "object") voiceChoice = saved;
    window.__hccTTS?.setVoice?.(voiceChoice);
    renderVoiceSettings();
  });

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
    // Mỗi ngôn ngữ một danh mục giọng riêng → đổi ngôn ngữ phải vẽ lại ô chọn.
    renderVoiceSettings();
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
    // Card đánh giá đang ghi âm ý kiến → đổ transcript vào ô ý kiến, KHÔNG gửi thành câu hội
    // thoại (tách hẳn khỏi vòng rảnh tay để không kích hoạt gửi chat / auto-nghe lại).
    if (ratingNoteSink) {
      if (msg.event === "partial") ratingNoteSink(msg.text || "", false);
      else if (msg.event === "final") { setMicUI(false); ratingNoteSink((msg.text || "").trim(), true); }
      else if (msg.event === "state") {
        if (msg.state === "listening") setMicUI(true, "🎤 Đang nghe ý kiến…");
        else if (msg.state === "stopped") setMicUI(false);
      } else if (msg.event === "error") {
        setMicUI(false);
        setStatus("⚠️ Không ghi được ý kiến — công dân gõ giúp em nhé.", true);
        setTimeout(() => setStatus(""), 3000);
      }
      return;
    }
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
      renderVoiceSettings(); // danh mục giọng cũng nằm trong config này
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

  // ── Khởi động: journey còn hoạt động → khôi phục; không có/hết 20 phút → màn bắt đầu ──
  // Chỉ chạy SAU khi đã đăng nhập; token chết giữa chừng đăng nhập lại thì
  // KHÔNG boot lại (khung chat + phiên đang dở giữ nguyên phía sau màn login).
  // Quay về đúng trang chủ DVC = bắt đầu lượt công dân mới. Xóa cả conversation BE và
  // con trỏ journey của tab; KHÔNG xóa cookie DVC vì đây không phải tín hiệu nộp thành công.
  async function lamMoiVeTrangChuDVC(j) {
    if (j?.conversation_id) {
      api.conversationId = j.conversation_id;
      await api.deleteConversation("dvc-home");
    }
    await clearJourney();
    await writeCompletionLogoutState(null);
    await writeActiveSplit(null);
    showStartScreen();
    console.log("[TLND] về trang chủ DVC → làm mới cuộc trò chuyện");
  }

  // Khung ĐẨY TRANG bị dựng lại ở mỗi lần điều hướng nên đọc được ?fresh=dvc-home.
  // Khung BÊN thì sống xuyên điều hướng — không có lần dựng lại nào để đọc tham số
  // đó, nên content.js báo bằng message. Thiếu đường này, công dân về trang chủ DVC
  // ở chế độ khung bên vẫn dính nguyên hồ sơ của người trước.
  chrome.runtime.onMessage.addListener((msg, sender) => {
    if (EMBEDDED || msg?.action !== "dvcHomeReached") return;
    if (Number(sender?.tab?.id) !== Number(TAB_ID)) return;
    void (async () => {
      const j = await loadJourney();
      if (!j?.conversation_id) return;   // chưa có hồ sơ nào để làm mới
      await lamMoiVeTrangChuDVC(j);
    })();
  });

  async function bootChat() {
    if (chatBootStarted) return;
    chatBootStarted = true;
    // Chuyển trang dựng lại content script → nạp lại luật nhận nút nộp NGAY, không chờ hồ sơ mới.
    void restoreSubmitWatch();
    try {
      const j = await loadJourney();
      let storedCompletionLogout = await readCompletionLogoutState();
      if (START_FRESH_ON_DVC_HOME) { await lamMoiVeTrangChuDVC(j); return; }
      if (j?.conversation_id) {
        const activityAt = Number(j.last_activity_at || j.ts || 0);
        if (!activityAt || Date.now() - activityAt >= IDLE_TIMEOUT_MS) {
          api.conversationId = j.conversation_id;
          await api.deleteConversation("idle");
          await clearJourney();
          await writeCompletionLogoutState(null);
          showStartScreen();
          console.log(`[TLND] phiên ${j.conversation_id} đã quá 20 phút → màn bắt đầu`);
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
            showProcedurePicker();
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
  const $preferScanSwitch = document.getElementById("prefer-scan-switch");
  const $attachModeMerge = document.getElementById("attach-mode-merge");
  const $attachModeSplit = document.getElementById("attach-mode-split");
  const $panelModePush = document.getElementById("panel-mode-push");
  const $panelModeSide = document.getElementById("panel-mode-side");
  const $panelModeNote = document.getElementById("panel-mode-note");
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
    $preferScanSwitch?.classList.toggle("on", preferScan);
    $preferScanSwitch?.setAttribute("aria-checked", preferScan ? "true" : "false");
    const split = attachMode === "split";
    $attachModeMerge?.classList.toggle("on", !split);
    $attachModeMerge?.setAttribute("aria-checked", split ? "false" : "true");
    $attachModeSplit?.classList.toggle("on", split);
    $attachModeSplit?.setAttribute("aria-checked", split ? "true" : "false");
  }

  function restoreAttachmentSettings() {
    return new Promise((resolve) => {
      chrome.storage.local.get([ATTACH_SPLIT_DOCUMENTS_KEY, ATTACH_MODE_KEY, PREFER_SCAN_KEY], (res) => {
        if (!chrome.runtime.lastError) {
          attachSplitDocuments = res?.[ATTACH_SPLIT_DOCUMENTS_KEY] === true;
          attachMode = res?.[ATTACH_MODE_KEY] === "split" ? "split" : "merge";
          preferScan = res?.[PREFER_SCAN_KEY] === true;
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

  function savePreferScan(value) {
    preferScan = value === true;
    renderAttachmentSettings();
    chrome.storage.local.set(
      { [PREFER_SCAN_KEY]: preferScan },
      () => {
        if (chrome.runtime.lastError) {
          if ($settingsSaved) $settingsSaved.textContent = "Chưa lưu được cài đặt.";
          return;
        }
        announceAttachmentSettingsSaved();
      },
    );
  }

  function saveAttachMode(value) {
    attachMode = value === "split" ? "split" : "merge";
    renderAttachmentSettings();
    chrome.storage.local.set(
      { [ATTACH_MODE_KEY]: attachMode },
      () => {
        if (chrome.runtime.lastError) {
          if ($settingsSaved) $settingsSaved.textContent = "Chưa lưu được cài đặt.";
          return;
        }
        announceAttachmentSettingsSaved();
      },
    );
  }

  // ── Vị trí khung: đẩy trang ↔ khung bên trình duyệt ──
  // Nguồn sự thật là lib/panelMode.js (nạp trước file này). Ở đây chỉ vẽ và lưu.
  const PM = globalThis.__TLND_PANEL_MODE__ || null;
  let panelMode = "push";

  function renderPanelMode() {
    if (!$panelModePush || !$panelModeSide) return;
    const hoTro = !!PM && PM.hoTroKhungBen();
    const ben = panelMode === "sidepanel";
    $panelModePush.classList.toggle("on", !ben);
    $panelModePush.setAttribute("aria-checked", ben ? "false" : "true");
    $panelModeSide.classList.toggle("on", ben);
    $panelModeSide.setAttribute("aria-checked", ben ? "true" : "false");
    $panelModeSide.disabled = !hoTro;
    if ($panelModeNote) {
      $panelModeNote.hidden = hoTro;
      if (!hoTro) {
        $panelModeNote.textContent =
          "Trình duyệt này chưa có khung bên (cần Chrome/Edge 114 trở lên). "
          + "Trợ lý sẽ luôn dùng chế độ đẩy trang.";
      }
    }
  }

  async function restorePanelMode() {
    if (!PM) return;
    panelMode = await PM.cheDoHieuLuc();
    renderPanelMode();
  }

  async function chuyenCheDo(value, daMoKhungBen) {
    if (!PM) return;
    const truoc = panelMode;
    if (value === truoc) return;
    panelMode = value;
    renderPanelMode();
    try {
      await PM.ghiCheDo(value);
    } catch (_) {
      panelMode = truoc;
      renderPanelMode();
      if ($settingsSaved) $settingsSaved.textContent = "Chưa lưu được cài đặt.";
      return;
    }
    announceAttachmentSettingsSaved();
    // background nghe storage.onChanged rồi đặt openPanelOnActionClick, đường sidebar
    // cho từng tab, VÀ báo panelModeChanged cho mọi tab. Đường riêng dưới đây chỉ thêm
    // moKhung cho đúng tab công dân vừa bấm — tab đó phải thấy khung mở ra ngay.
    await sendToContent({ action: "panelModeChanged", mode: value, moKhung: value === "push" });
    if (value === "sidepanel") {
      // Khung đẩy trang (chính là cái đang chạy đoạn code này) sắp bị content.js gỡ.
      if (EMBEDDED && !daMoKhungBen) {
        setStatus("Đã chuyển sang khung bên. Bấm biểu tượng Trợ lý trên thanh công cụ để mở.", true);
      }
      return;
    }
    if (!EMBEDDED) {
      // Đang Ở TRONG khung bên mà chọn đẩy trang: content.js vừa dựng khung trên
      // trang, đóng khung bên này lại — để cả hai cùng sống là hai bản sidebar
      // cùng thao tác trên một hồ sơ.
      setTimeout(() => { try { window.close(); } catch (_) {} }, 150);
    }
  }

  $panelModePush?.addEventListener("click", () => {
    markActivity();
    void chuyenCheDo("push", false);
  });

  $panelModeSide?.addEventListener("click", () => {
    markActivity();
    if (!PM || panelMode === "sidepanel" || $panelModeSide.disabled) return;
    // sidePanel.open() phải nằm TRONG cú bấm: mọi await phía trước đều làm mất user
    // gesture và Chrome từ chối thẳng. Vì thế mở trước, ghi cài đặt sau — ngược lại
    // thứ tự thông thường, nhưng đây là ràng buộc của trình duyệt chứ không phải
    // lựa chọn. Chrome < 116 không có open() → daMo=false và báo cách mở bằng tay.
    let daMo = false;
    const tab = Number(TAB_ID);
    if (EMBEDDED && PM.hoTroMoNgay() && tab) {
      try {
        chrome.sidePanel
          .setOptions({ tabId: tab, path: PM.duongSidebar(tab), enabled: true })
          .catch(() => {});
        chrome.sidePanel.open({ tabId: tab }).catch(() => {});
        daMo = true;
      } catch (_) { daMo = false; }
    }
    void chuyenCheDo("sidepanel", daMo);
  });

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
  $preferScanSwitch?.addEventListener("click", () => {
    savePreferScan(!preferScan);
  });
  $attachSplitSwitch?.addEventListener("click", () => {
    markActivity();
    saveAttachmentSettings(!attachSplitDocuments);
  });
  $attachModeMerge?.addEventListener("click", () => {
    markActivity();
    saveAttachMode("merge");
  });
  $attachModeSplit?.addEventListener("click", () => {
    markActivity();
    saveAttachMode("split");
  });
  chrome.storage?.onChanged?.addListener((changes, areaName) => {
    if (areaName !== "local") return;
    let dirty = false;
    if (changes[ATTACH_SPLIT_DOCUMENTS_KEY]) {
      attachSplitDocuments = changes[ATTACH_SPLIT_DOCUMENTS_KEY].newValue === true;
      dirty = true;
    }
    if (changes[ATTACH_MODE_KEY]) {
      attachMode = changes[ATTACH_MODE_KEY].newValue === "split" ? "split" : "merge";
      dirty = true;
    }
    if (dirty) renderAttachmentSettings();
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
    // Rời phiên → ngừng theo dõi máy quét + nâng mốc (không kéo lại giấy đã quét sau khi
    // đăng nhập lại).
    bumpScanWatermark();
    disconnectScanAgent();
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
    await restorePanelMode();
    const st = await window.tlndAuth.load();
    if (st?.access) { renderAccount(); bootChat(); }
    else showLogin();
  })();

  console.log(`[TLND] sidebar sẵn sàng — tabId=${TAB_ID}`);
})();
