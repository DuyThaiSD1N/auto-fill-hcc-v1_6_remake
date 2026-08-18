// sidebar.js — UI chat "Trợ lý người dân" (Bước 3: hội thoại server-driven thật).
// Vòng lặp: ask(message, source) → BE trả {display_md, tts_text, chips, cards, actions, progress}
// → render + THI HÀNH actions. FE không quyết flow — chips[0] luôn là bước tốt nhất do BE chọn.
(() => {
  "use strict";

  // ── Ngữ cảnh nhúng: content.js nạp sidebar.html?embedded=1&tabId=<id> ──
  const params = new URLSearchParams(location.search);
  const TAB_ID = params.get("tabId") || "";

  const $messages = document.getElementById("messages");
  const $status = document.getElementById("status");
  const $form = document.getElementById("chat-form");
  const $input = document.getElementById("chat-input");
  const $subtitle = document.querySelector(".bot-h .s");

  const api = new window.TlndApiClient();
  const JOURNEY_KEY = "tlnd_journey"; // { [tabId]: {conversation_id, ts} } — sống qua đổi origin
  const ACTIVE_SPLIT_KEY = "tlnd_active_split_by_tab";
  const SPLIT_STAGE_KEY = "tro_ly_split_attach_queue_stage";

  const ROBOT = (w) => `<svg width="${w}" height="${Math.round(w * 1.1)}" viewBox="0 0 120 132" xmlns="http://www.w3.org/2000/svg">
    <rect x="57" y="8" width="6" height="12" rx="3" fill="#2f7fbf"/><circle cx="60" cy="6" r="5" fill="#3b9be0"/>
    <path d="M28,40 Q60,14 92,40 L92,46 L28,46 Z" fill="#2f6bb0"/><rect x="28" y="43" width="64" height="7" rx="3" fill="#f4c11e"/>
    <rect x="32" y="46" width="56" height="46" rx="17" fill="#16233a"/>
    <circle cx="48" cy="70" r="8" fill="#54e0ff"/><circle cx="72" cy="70" r="8" fill="#54e0ff"/>
    <circle cx="48" cy="70" r="3" fill="#0a2b45"/><circle cx="72" cy="70" r="3" fill="#0a2b45"/>
    <path d="M52,82 Q60,89 68,82" stroke="#54e0ff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <rect x="36" y="94" width="48" height="34" rx="13" fill="#3b82c4"/><rect x="36" y="94" width="48" height="10" rx="5" fill="#2f6bb0"/>
    <circle cx="60" cy="114" r="8" fill="#f4c11e"/></svg>`;
  document.getElementById("bot-avatar").innerHTML = ROBOT(30);

  // ── Render cơ bản ──
  function addBubble(role, html) {
    const el = document.createElement("div");
    el.className = `msg ${role}`;
    el.innerHTML = html;
    $messages.appendChild(el);
    $messages.scrollTop = $messages.scrollHeight;
    return el;
  }
  const addUserText = (t) => addBubble("user", window.escapeHtml(t));
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
  function saveJourney() {
    if (!TAB_ID || !api.conversationId) return;
    chrome.storage.local.get([JOURNEY_KEY], (res) => {
      const j = res?.[JOURNEY_KEY] || {};
      // keep_open: sang origin khác content.js tự dựng lại sidebar (docs/07 §2.1).
      j[TAB_ID] = { conversation_id: api.conversationId, ts: Date.now(), keep_open: true };
      chrome.storage.local.set({ [JOURNEY_KEY]: j }, () => void chrome.runtime.lastError);
    });
  }
  function loadJourney() {
    return new Promise((resolve) => {
      if (!TAB_ID) return resolve(null);
      chrome.storage.local.get([JOURNEY_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve(res?.[JOURNEY_KEY]?.[TAB_ID] || null);
      });
    });
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
  const pendingQueue = [];
  async function ask(message, source = "text", displayText = "") {
    if (busy) {
      if (source === "system" || source === "chip") {
        // Trả Promise chỉ resolve sau khi lượt xếp hàng THỰC SỰ gọi xong backend. Queue tách hồ sơ
        // dựa vào đây để chưa xóa recovery marker trước khi attach_report được ghi nhận.
        return await new Promise((resolve) => pendingQueue.push([message, source, displayText, resolve]));
      }
      return;
    }
    busy = true;
    showTyping();
    try {
      const data = await api.ask(message, { source, displayText });
      hideTyping();
      saveJourney();
      renderReply(data);
      await runActions(data.actions || []);
      return data;
    } catch (e) {
      hideTyping();
      setStatus(`Không gọi được trợ lý: ${e?.message || e}. Kiểm tra backend đang chạy?`, true);
      setTimeout(() => setStatus(""), 5000);
    } finally {
      busy = false;
      if (pendingQueue.length) {
        const [m, s, dt, resolve] = pendingQueue.shift();
        ask(m, s, dt).then(resolve);
      }
    }
  }

  let lastState = "";
  let lastReplyData = null; // reply gần nhất — dùng để đọc lại câu chào khi bật rảnh tay ở màn chào
  let replyTtsInFlight = 0;
  function stopReplyTts() {
    replyTtsInFlight = 0;
    window.__hccTTS?.stop?.();
  }
  const $meterBar = document.getElementById("step-meter-bar");
  function setProgress(p) {
    if (!p?.label) return;
    $subtitle.textContent = `Bước ${p.step}/${p.total} · ${p.label}`;
    if ($meterBar && p.total) {
      $meterBar.style.width = `${Math.min(100, Math.round((p.step / p.total) * 100))}%`;
    }
  }
  function renderReply(d, opts) {
    lastReplyData = d;
    const prevState = lastState;
    if (d.state) { lastState = d.state; schedulePageWatcher(); }
    if (d.display_md) addBotMd(d.display_md);
    // ĐỌC XONG câu này thì THU GỌN panel (kịch bản đăng nhập trên trang SSO → lộ mã QR để quét).
    // Chỉ áp cho reply LIVE (không phải khôi phục phiên noTts, kẻo mở lại tay bị auto-thu-gọn).
    const collapseAfter = !opts?.noTts && (d.actions || []).some((a) => a.type === "collapse_after_tts");
    const willSpeak = !!d.tts_text && voiceCfg.tts && !ttsMuted;
    // noTts: render lại reply CŨ khi khôi phục phiên — không đọc lại câu đã đọc rồi.
    if (opts?.noTts) { /* bỏ đọc */ }
    else if (d.tts_text && voiceCfg.tts) {
      // fill_report đến ngay sau action điền form. Đây là phần tiếp nối của fields_ready nên
      // phải xếp hàng để đọc HẾT câu "Xong rồi ạ..." trước; các chuyển trạng thái khác vẫn
      // cắt câu cũ để bot không đọc hướng dẫn đã hết hiệu lực.
      const queueAfterFillReady = prevState === "filling" && d.state === "reviewing"
        && replyTtsInFlight > 0;
      if (!queueAfterFillReady) stopReplyTts();
      else console.debug("[TLND] xếp TTS rà soát sau câu báo đọc xong giấy tờ");
      replyTtsInFlight += 1;
      // Rảnh tay: đọc xong tự mở mic nghe lượt kế (docs/03a §5). onDone KHÔNG bắn khi bị ngắt lời.
      window.__hccTTS?.speak?.(d.tts_text, "vi", () => {
        replyTtsInFlight = Math.max(0, replyTtsInFlight - 1);
        if (collapseAfter && willSpeak) minimizePanel(); // đọc THẬT xong → thu gọn (mute thì onDone bắn ngay, bỏ qua)
        // Nếu còn câu nối tiếp trong hàng đợi thì chưa mở mic, tránh ASR barge-in cắt câu sau.
        if (handsfree && replyTtsInFlight === 0) startVoice();
      });
    } else if (handsfree) {
      startVoice(); // không đọc được (tts tắt) vẫn phải mở mic để vòng không đứng
    }
    // Không đọc (tts tắt/mute) mà vẫn cần thu gọn → cho ~7s đọc chữ rồi thu gọn.
    if (collapseAfter && !willSpeak) setTimeout(minimizePanel, 7000);
    (d.cards || []).forEach(renderCard);
    if (d.chips?.length) renderChips(d.chips);
    setProgress(d.progress);
    // Khôi phục phiên (noTts) không dựng card tiến trình — không có WS để chốt nó.
    if (!opts?.noTts) updatePipeFromState(prevState, d);
  }

  function renderChips(chips) {
    const wrap = document.createElement("div");
    wrap.className = "chips";
    chips.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip" + (c.solid ? " solid" : "");
      b.textContent = c.label;
      // "Đã đưa đủ giấy tờ, xử lý đi": khoá đến khi nhận ≥1 tệp (renderDocProgress mở khoá).
      // Tránh bấm chốt xử lý lúc chưa tải gì lên (nút hiện sẵn ngay khi vừa chọn cách tải).
      if (c.send === "__action:docs_done") {
        $docsDoneChip = b;
        if (!docsReceived) {
          b.disabled = true;
          b.title = "Bà con tải giấy tờ lên trước, em mới xử lý được ạ";
        }
      }
      b.addEventListener("click", () => {
        // 1 nhóm chip chỉ bấm 1 lần — disable cả nhóm rồi gửi.
        wrap.querySelectorAll("button").forEach((x) => (x.disabled = true));
        // Nút chốt giấy tờ được chuyển sang holder riêng dưới checklist; vẫn khoá cả
        // chính nó lẫn nhóm nút phụ ban đầu để không bấm đổi cách gửi khi đang xử lý.
        b.closest(".chips")?.querySelectorAll("button").forEach((x) => (x.disabled = true));
        // "Làm thủ tục khác"/"Thủ tục mới" → LÀM MỚI THẬT: xóa phiên + lịch sử, về màn "Xin chào bà
        // con" (không reset mềm giữ lịch sử). Dùng cùng đường với nút 🔄 Trò chuyện mới.
        if (c.send === "__action:new_procedure") { resetConversation(); return; }
        addUserText(c.label);
        ask(c.send, "chip", c.label);
      });
      wrap.appendChild(b);
    });
    addNode(wrap);
    placeDocsDoneAfterProgress();
  }

  // ── Page watcher (docs/07 §2.2): tự nhận đăng-nhập-xong / nộp-thành-công — bỏ chip tay ──
  let watcherTimer = null;
  let watcherTicks = 0;
  let fallbackChipShown = false;
  let infoModalTries = 0;

  // Báo BE trạng thái trang (__event:page_status) — BE nhìn tín hiệu THẬT để quyết bước
  // tiếp (chọn cơ quan / xác nhận modal / nhắc điền chủ hồ sơ / vào kê khai), sidebar
  // không tự suy diễn. Trang React render dần → chờ đến khi có tín hiệu có nghĩa mới gửi.
  const pageSignal = (c) => !!(c && (
    c.formKind || c.agencyBlock || c.loginPage || c.infoModal || c.wizardStep || c.attachmentTarget
  ));
  async function sendPageStatus(pre) {
    let c = pre || null;
    for (let i = 0; !c && i < 12; i++) {
      const got = await sendToContent({ action: "getPageContext" });
      if (got?.ok && pageSignal(got)) { c = got; break; }
      c = null;
      await new Promise((r) => setTimeout(r, 900));
      if (i === 11) c = got; // hết kiên nhẫn → gửi trạng thái cuối (BE im lặng nếu không có gì)
    }
    if (!c?.ok) return;
    ask(`__event:page_status:${JSON.stringify({
      loggedIn: !!c.loggedIn, formKind: c.formKind || "",
      agencyBlock: !!c.agencyBlock, loginPage: !!c.loginPage,
      infoModal: !!c.infoModal, wizardStep: c.wizardStep || 0,
      attachmentTarget: !!c.attachmentTarget,
      // Chủ thể dữ liệu VNeID content đọc từ cổng — BE lưu vào conv, ghi biên bản consent.
      principal: c.principal || null,
    })}`, "system");
  }

  let lastPageSig = "";
  const WATCH_STATES = ["guide_login", "attaching", "done"]; // attaching: chờ sang bước Thành phần hồ sơ
  function schedulePageWatcher() {
    if (!WATCH_STATES.includes(lastState)) {
      if (watcherTimer) { clearInterval(watcherTimer); watcherTimer = null; }
      return;
    }
    if (watcherTimer) return; // đang chạy
    watcherTicks = 0;
    watcherTimer = setInterval(async () => {
      watcherTicks += 1;
      if (watcherTicks > 60 || !WATCH_STATES.includes(lastState)) {
        clearInterval(watcherTimer); watcherTimer = null; return;
      }
      const ctx = await sendToContent({ action: "getPageContext" });
      if (!ctx?.ok) return;
      // Trang SPA đổi bước không reload → theo dõi CHỮ KÝ tín hiệu, đổi mới báo BE
      // (loggedIn không tính: trang chi tiết cũng có user-dropdown khi đã đăng nhập).
      const sig = `${ctx.formKind}|${ctx.wizardStep || 0}|${ctx.infoModal ? 1 : 0}|${ctx.agencyBlock ? 1 : 0}|${ctx.attachmentTarget ? 1 : 0}`;
      if ((lastState === "guide_login" || lastState === "attaching") && pageSignal(ctx) && sig !== lastPageSig) {
        lastPageSig = sig;
        sendPageStatus(ctx);
      } else if (lastState === "guide_login" && watcherTicks >= 17 && !fallbackChipShown) {
        // ~60s chưa tự nhận ra → đưa nút phao cho người dân tự xác nhận.
        fallbackChipShown = true;
        renderChips([{ label: "Tôi đã vào trang làm hồ sơ", send: "__event:sso_success", solid: true }]);
      } else if (lastState === "done" && ctx.submitted) {
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
    if (card.kind === "phone_form") return renderPhoneForm(card);
    if (card.kind === "consent_form") return renderConsentForm(card);
    console.warn("[TLND] card chưa hỗ trợ:", card.kind);
  }

  // Card xin phép xử lý dữ liệu cá nhân (Luật 91/2025) — chữ nghĩa 100% server-driven,
  // FE chỉ dựng checkbox + nút. Tích đủ 2 ô mới mở nút Đồng ý; toàn văn luật nằm trong
  // khối mở rộng (sidebar 400px không dùng modal).
  function renderConsentForm(card) {
    const el = document.createElement("div");
    el.className = "consent-card";
    const docs = (card.documents || []).map((d) => `
      <div class="cdoc"><span class="ci">${window.escapeHtml(d.icon || "📄")}</span>
        <span class="cn">${window.escapeHtml(d.name)}</span>${d.sides === 2 ? '<span class="ctag">2 mặt</span>' : ""}</div>`).join("");
    const checks = (card.checks || []).map((t, i) => `
      <label class="ccheck"><input type="checkbox" data-i="${i}">
        <span>${window.escapeHtml(t)}</span></label>`).join("");
    el.innerHTML = `
      <span class="cbadge">🔒 Xác nhận trên Trợ lý người dân</span>
      <div class="ctitle">Cho phép em đọc giấy tờ và tự động điền biểu mẫu</div>
      <div class="ctext">${window.renderMarkdown(card.intro_md || "")}</div>
      <div class="cdocs-box">
        <div class="clist-t">📋 Giấy tờ em sẽ đọc — ${window.escapeHtml(card.procedure || "thủ tục này")}</div>
        <div class="cdocs">${docs}</div>
      </div>
      <div class="cscope">${window.renderMarkdown(card.scope_md || "")}</div>
      <div class="cpurpose">${window.renderMarkdown(card.purpose_md || "")}</div>
      <details class="clegal"><summary>Quyền, nghĩa vụ của chủ thể dữ liệu (Điều 4, Luật 91/2025/QH15)</summary>
        <div class="clegal-b">${window.renderMarkdown(card.legal_md || "")}</div></details>
      <button type="button" class="chip callall">✓ Chọn tất cả</button>
      ${checks}
      <div class="cactions">
        <button type="button" class="chip cdecline">${window.escapeHtml(card.decline_label || "Không đồng ý · Tự nhập")}</button>
        <button type="button" class="chip solid caccept" disabled>${window.escapeHtml(card.accept_label || "Đồng ý và tự động điền")}</button>
      </div>
      <div class="cver">Bản nội dung v${window.escapeHtml(String(card.version || "1.0"))} — sự đồng ý được ghi nhật ký, bà con rút lại được bất cứ lúc nào.</div>`;
    const boxes = [...el.querySelectorAll('input[type="checkbox"]')];
    const $accept = el.querySelector(".caccept");
    const sync = () => { $accept.disabled = !boxes.every((b) => b.checked); };
    boxes.forEach((b) => b.addEventListener("change", sync));
    el.querySelector(".callall").addEventListener("click", () => {
      boxes.forEach((b) => { b.checked = true; });
      sync();
    });
    const finish = (accepted, label) => {
      el.querySelectorAll("button, input").forEach((x) => { x.disabled = true; });
      addUserText(label);
      ask(`__action:consent:${JSON.stringify({ accepted, checks: boxes.map((b) => b.checked) })}`, "chip", label);
    };
    $accept.addEventListener("click", () => finish(true, $accept.textContent));
    const $decline = el.querySelector(".cdecline");
    $decline.addEventListener("click", () => finish(false, $decline.textContent));
    addNode(el);
  }

  // Card nhập SĐT (state done — docs/08): đăng ký nhận thông báo tiến độ.
  function renderPhoneForm(_card) {
    const el = document.createElement("div");
el.style.cssText = "align-self:stretch;display:flex;gap:8px;";
    el.innerHTML = `
      <input type="tel" placeholder="Số điện thoại của bà con…" inputmode="numeric"
             style="flex:1;border:1px solid #cfe6da;border-radius:10px;padding:10px 12px;font-size:13px;outline:none">
      <button type="button" style="background:var(--teal);color:#fff;border:0;border-radius:10px;padding:0 16px;font-weight:700;cursor:pointer">Đăng ký</button>`;
    const $inp = el.querySelector("input");
    const $btn = el.querySelector("button");
    const submit = () => {
      const phone = ($inp.value || "").trim();
      if (!phone) return;
      $btn.disabled = true;
      addUserText(phone);
      ask(`__action:subscribe_phone:${JSON.stringify({ phone })}`, "chip", phone);
    };
    $btn.addEventListener("click", submit);
    $inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } });
    addNode(el);
  }

  function renderServiceList(card) {
    (card.items || []).forEach((it) => {
      const el = document.createElement("div");
      el.className = "svc2";
      el.innerHTML = `<div class="ico">${window.escapeHtml(it.icon || "📄")}</div>
        <div class="st"><div class="tt">${window.escapeHtml(it.title)}</div>
        <div class="ss">${window.escapeHtml(it.subtitle || "")}</div></div><div class="arr">›</div>`;
      el.addEventListener("click", () => {
        addUserText(it.title);
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
    el.innerHTML = `<div class="loc-t">📍 Nơi làm thủ tục</div>`;
    const provinces = card.provinces || [];
    let provSlug = "";

    const provRow = document.createElement("div");
    provRow.className = "sel";
    provRow.innerHTML = `<span>Tỉnh/Thành phố</span>`;
    const wardRow = document.createElement("div");
    wardRow.className = "sel";
    wardRow.innerHTML = `<span>Phường/Xã</span>`;

    const wardBox = makeSearchSelect({
      placeholder: "Gõ để tìm xã/phường…",
      onPick: (o) => {
        if (!provSlug) return;
        ask(`__action:set_location:${JSON.stringify({ province_slug: provSlug, ward: o.label })}`,
          "chip", `Chọn nơi làm thủ tục: ${o.label}, ${provBox.value}`);
      },
    });
    const provBox = makeSearchSelect({
      placeholder: "Gõ để tìm tỉnh/thành…",
      onPick: (o) => { provSlug = o.slug; wardBox.setValue(""); loadWards(); },
    });
    provBox.setOptions(provinces.map((p) => ({ label: p.text, slug: p.slug })));
    provRow.appendChild(provBox.el);
    wardRow.appendChild(wardBox.el);
    el.append(provRow, wardRow);
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
      const el = document.createElement("div");
      el.className = "opt";
      el.innerHTML = `<div class="oi">${meta.icon}</div><div>
        <div class="ot">${window.escapeHtml(meta.title)}</div>
        <div class="od">${window.escapeHtml(meta.desc)}</div></div>`;
      el.addEventListener("click", () => {
        addUserText(meta.title);
        ask(`__action:doc_method:${JSON.stringify({ value: key })}`, "chip", meta.title);
      });
      addNode(el);
    });
  }

  // ── Card tiến trình xử lý giấy tờ (docs_complete → fields_ready thường 30–90s) ──
  // Staging theo thời gian ƯỚC LƯỢNG để bà con thấy máy đang chạy; mốc THẬT
  // (fields_ready / attach_ready / action fill_fields / pipeline_error) đến thì chốt ✓/⚠️ ngay.
  const PIPE_STAGES = [
    { from: 0, label: "Kiểm tra ảnh đã nhận" },
    { from: 3, label: "Đọc chữ trên giấy tờ (OCR)" },
    { from: 22, label: "Bóc tách và đối chiếu thông tin" },
    { from: 45, label: "Chuẩn bị điền biểu mẫu" },
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

  function showPipelineCard() {
    if ($pipe && !pipeFinished) return; // đang chạy rồi — không dựng card thứ 2
    pipeFinished = false;
    pipeT0 = Date.now();
    $pipe = document.createElement("div");
    $pipe.className = "pipe-card";
    $pipe.innerHTML = `
      <div class="pipe-h">🤖 Em đang đọc và bóc tách giấy tờ — bà con chờ em chút ạ…</div>
      <div class="prog"><i style="width:4%"></i></div>
      ${PIPE_STAGES.map((s, i) => `<div class="pipe-step"><span class="pic">${i + 1}</span>
        <span class="pl">${s.label}</span><span class="ps"></span></div>`).join("")}`;
    addNode($pipe);
    renderPipeSteps(0, false);
    clearInterval(pipeTimer);
    pipeTimer = setInterval(() => {
      const t = (Date.now() - pipeT0) / 1000;
      const bar = $pipe?.querySelector(".prog i");
      // Tiệm cận 94% — không bao giờ "đầy" trước khi có mốc thật.
      if (bar) bar.style.width = `${Math.min(94, Math.round(100 * (1 - Math.exp(-t / 30))))}%`;
      renderPipeSteps(t, false);
    }, 1000);
  }

  function pipeStop() { clearInterval(pipeTimer); pipeTimer = null; pipeFinished = true; }
  function pipeDone() {
    if (!$pipe || pipeFinished) return;
    pipeStop();
    renderPipeSteps(Infinity, true);
    const bar = $pipe.querySelector(".prog i");
    if (bar) bar.style.width = "100%";
    $pipe.classList.add("done");
    $pipe.querySelector(".pipe-h").textContent = "✅ Đã đọc xong giấy tờ";
    $messages.scrollTop = $messages.scrollHeight;
  }
  function pipeFail() {
    if (!$pipe || pipeFinished) return;
    pipeStop();
    $pipe.classList.add("err");
    $pipe.querySelector(".pipe-h").textContent = "⚠️ Xử lý giấy tờ chưa xong được";
  }

  // BE vào state "filling" = pipeline bắt đầu chạy (cả đường WS docs_complete lẫn gõ "điền đi").
  // Reply refill từ rà soát cũng state filling nhưng kèm luôn action fill_fields → không dựng card.
  function updatePipeFromState(prev, d) {
    const st = d.state || prev;
    const willFill = (d.actions || []).some((a) => a.type === "fill_fields");
    if (st === "filling" && prev !== "filling" && !willFill) showPipelineCard();
    else if ($pipe && !pipeFinished) {
      if (willFill || st === "reviewing" || st === "attaching" || st === "done") pipeDone();
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
  let $docProgress = null;
  let uploadSid = null; // phiên đang mở — dùng cho nhánh "Scan tại quầy" (upload từ máy tính)
  // Cổng cho nút "Đã đưa đủ giấy tờ, xử lý đi": chỉ mở khi phiên đã nhận ≥1 tệp.
  let docsReceived = false;
  let $docsDoneChip = null;

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
    const totalBytes = files.reduce((sum, file) => sum + Number(file.size || 0), 0);
    const totalMb = totalBytes / (1024 * 1024);
    const uploadStartedAt = performance.now();
    // Đây chỉ là chặng truyền/lưu file. Phân loại OCR/LLM (nếu thủ tục cần) chạy ở chặng
    // xử lý sau khi người dân bấm "Đã đưa đủ", không được làm chậm cửa sổ chọn tệp.
    setStatus(`⏳ Đang tải ${files.length} tệp lên hệ thống…`);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f, f.name));
      const res = await fetch(`${BASE_URL}/api/v1/upload-sessions/${uploadSid}/files`,
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
      if (data?.progress) renderDocProgress(data.progress);
      const unknown = (data?.accepted || []).filter((a) => !a.doc_key).length;
      if (unknown) addBotMd(`⚠️ **${unknown} tệp** em chưa nhận ra loại — bà con scan lại rõ hơn hoặc cứ bấm "Đã đưa đủ" để em xử lý phần nhận được ạ.`);
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
      <div class="qr-stat">Đang chờ bà con quét mã…</div>`;
    addNode(el);
    $docProgress = el; // progress bar + status cập nhật qua WS
  }

  function renderDocProgress(p) {
    // Nhận được tệp ĐẦU TIÊN (kể cả tệp chưa nhận ra loại / slot tuỳ chọn) → mở khoá nút
    // "Đã đưa đủ giấy tờ, xử lý đi". BE dặn cứ bấm nút này để xử lý cả phần chưa nhận ra
    // loại, nên chỉ cần có bất kỳ tệp nào là cho chốt — không đợi đủ giấy bắt buộc.
    const gotAny = ((p.docs || []).reduce((n, d) => n + (d.received || 0), 0) + (p.unknown || 0)) > 0;
    if (gotAny && !docsReceived) {
      docsReceived = true;
      if ($docsDoneChip) { $docsDoneChip.disabled = false; $docsDoneChip.removeAttribute("title"); }
    }
    // Card danh sách giấy tờ (thay/đặt dưới card QR) — kiểu .doc-row prototype.
    let wrap = document.getElementById("doc-progress-card");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "doc-progress-card";
      wrap.style.cssText = "align-self:stretch;display:flex;flex-direction:column;gap:7px;";
      addNode(wrap);
    }
    wrap.innerHTML = (p.docs || []).map((d) => {
      const repeatable = !!d.repeatable;
      const done = !repeatable && d.received >= d.sides;
      const st = repeatable ? `<span class="st ok">Đã nhận ${d.receivedCount || 0} tệp</span>`
        : done ? '<span class="st ok">✓ Đã nhận</span>'
        : `<span class="st">${d.received}/${d.sides}${d.sides > 1 ? " mặt" : ""}</span>`;
      return `<div class="doc-row ${done ? "done-row" : ""}"><div class="ic">${d.icon || "📄"}</div>
        <div class="nm">${window.escapeHtml(d.name)}</div>${st}</div>`;
    }).join("");
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
    $messages.scrollTop = $messages.scrollHeight;
  }

  function subscribeUploadSession(sid) {
    // Phiên upload mới: chưa nhận tệp nào → khoá lại nút "đủ giấy tờ" (renderChips vừa render
    // nó ở lượt này nên $docsDoneChip trỏ đúng nút hiện tại; khoá kể cả khi phiên trước đã mở).
    docsReceived = false;
    if ($docsDoneChip) {
      $docsDoneChip.disabled = true;
      $docsDoneChip.title = "Bà con tải giấy tờ lên trước, em mới xử lý được ạ";
    }
    if (uploadWs) { try { uploadWs.close(); } catch (_) {} uploadWs = null; }
    const wsUrl = `${window.tlndWsBase(BASE_URL)}/ws/upload-sessions/${sid}`;
    let mobileConnectedSent = false;
    let completeSent = false;
    try {
      uploadWs = new WebSocket(wsUrl);
      uploadWs.onmessage = (ev) => {
        let d;
        try { d = JSON.parse(ev.data); } catch (_) { return; }
        if (d.type === "session_opened" && !mobileConnectedSent) {
          mobileConnectedSent = true;
          ask("__event:mobile_connected", "system");
        } else if (d.type === "progress") {
          renderDocProgress(d);
        } else if (d.type === "complete" && !completeSent) {
          // Lưới chắn đua /complete vs /files: nếu BE lỡ phát complete lúc phiên CHƯA có file
          // nào (upload còn đang bay), KHÔNG bắn docs_complete — tránh xử lý phiên rỗng "0 file,
          // thử lại lần 2 mới được". Chờ tới khi progress có file thật rồi complete lại.
          const got = (d.docs || []).reduce((n, x) => n + (x.received || 0), 0) + (d.unknown || 0);
          if (got <= 0) { renderDocProgress(d); return; }
          completeSent = true;
          renderDocProgress(d);
          ask("__event:docs_complete", "system");
        } else if (d.type === "fields_ready") {
          pipeDone(); // mốc thật: dữ liệu đã bóc xong
          ask("__event:fields_ready", "system");   // BE trả action fill_fields (docs/06)
        } else if (d.type === "attach_ready") {
          pipeDone();
          ask("__event:attach_ready", "system");   // BE trả action attach_plan
        } else if (d.type === "pipeline_error") {
          pipeFail();
          ask("__event:pipeline_error", "system");
        }
      };
      uploadWs.onerror = () => setStatus("⚠️ Mất kết nối tiến trình giấy tờ (WS).", true);
    } catch (e) {
      setStatus("⚠️ Không mở được kênh tiến trình.", true);
    }
  }

  // ── Đính kèm tự động (Bước 6b — docs/06 §3.3) ──
  // Lấy file từ PHIÊN upload (đúng THỨ TỰ như pipeline đã thấy — fileIndex khớp),
  // chuyển thành dataUrl rồi giao engine attach-core thao tác DOM.
  async function fetchSessionFilesAsPayload(sid) {
    const res = await fetch(`${BASE_URL}/api/v1/upload-sessions/${sid}`);
    if (!res.ok) throw new Error(`Không đọc được phiên giấy tờ (HTTP ${res.status}).`);
    const sess = await res.json();
    const out = [];
    for (const f of sess.files || []) {
      const fr = await fetch(`${BASE_URL}/api/v1/upload-sessions/${sid}/files/${f.fid}`);
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

  // Cổng chỉ nhận 1 tệp/ô hồ sơ: nhóm sourceFileIndexes>1 (vd 2-4 ảnh CCCD) gộp thành
  // 1 PDF đúng thứ tự, ảnh lẻ cũng chuyển PDF 1 trang (lossless — lib/imageToPdf.js),
  // rồi đánh lại fileIndex cho khớp danh sách file mới. Lỗi chuyển/gộp → giữ file gốc.
  async function preparePdfPayload(files, attachments) {
    if (!window.PdfConvert || !window.PDFLib) return { files, attachments };
    const outFiles = [];
    const outAtts = [];
    for (const item of attachments || []) {
      const src = Array.isArray(item.sourceFileIndexes) && item.sourceFileIndexes.length
        ? item.sourceFileIndexes : [item.fileIndex];
      const sources = src.map((i) => files[i]).filter(Boolean);
      if (!sources.length) continue;
      let file = sources[0];
      try {
        if (sources.length > 1) {
          const merged = await PdfConvert.mergeToPdf(sources, item.documentName || sources[0].name);
          file = { ...sources[0], ...merged };
        } else if (file.dataUrl && PdfConvert.isImage(file.type, file.name)) {
          const pdf = await PdfConvert.imageToPdf(file.dataUrl, file.name, file.type);
          file = { ...file, ...pdf };
        }
      } catch (e) {
        console.warn("[TLND] Chuyển/gộp PDF thất bại, giữ file gốc:", file.name, e);
      }
      const newIndex = outFiles.length;
      outFiles.push(file);
      outAtts.push({ ...item, fileIndex: newIndex, sourceFileIndexes: [newIndex] });
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
    return Number(item?.componentIndex) === 2;
  }

  // Chứng thực chữ ký: mỗi hồ sơ có đúng một văn bản STT1; giấy tờ tùy thân STT2
  // được dùng chung cho mọi hồ sơ. preparePdfPayload đã gộp sourceFileIndexes của CCCD/Hộ chiếu;
  // nhánh merge dưới đây là lớp bảo vệ khi payload đi vào helper mà chưa qua bước chuẩn hóa đó.
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

    let sharedIdentityFile = null;
    let sharedIdentityPlan = null;
    if (identityEntries.length) {
      sharedIdentityFile = identityEntries[0].file;
      sharedIdentityPlan = identityEntries[0].planItem;
      if (identityEntries.length > 1) {
        if (!window.PdfConvert) {
          return { error: "Không thể gộp các tệp giấy tờ tùy thân để dùng chung cho STT2." };
        }
        try {
          const merged = await PdfConvert.mergeToPdf(
            identityEntries.map((entry) => entry.file),
            sharedIdentityPlan.documentName || sharedIdentityFile.name
          );
          sharedIdentityFile = { ...sharedIdentityFile, ...merged };
        } catch (e) {
          return { error: `Không thể gộp các tệp giấy tờ tùy thân cho STT2: ${e?.message || e}` };
        }
      }
    }

    return {
      bundles: documentEntries.map((entry) => {
        const bundleFiles = [entry.file];
        const bundleAttachments = [{
          ...entry.planItem,
          fileIndex: 0,
          sourceFileIndexes: [0],
          fileName: entry.file?.name || entry.planItem.fileName,
          documentName: entry.planItem.documentName || entry.file?.name,
        }];
        if (sharedIdentityFile && sharedIdentityPlan) {
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

  function splitQueueReport(status) {
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
    };
  }

  async function monitorSplitQueue(queueId, totalHint = 0) {
    if (!queueId) return;
    const deadline = Date.now() + 30 * 60 * 1000;
    let missingCount = 0;
    for (;;) {
      const status = await sendToBackground({ action: "getSplitAttachQueueStatus", queueId });
      if (status?.status === "done") {
        setStatus("");
        // Chỉ báo backend sau khi TOÀN BỘ tab terminal; đây là điểm khác với popup auto-fill.
        const acknowledged = await ask(
          `__action:attach_report:${JSON.stringify(splitQueueReport(status))}`, "system"
        );
        if (!acknowledged) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          continue; // mạng lỗi: giữ marker + retry, không làm mất báo cáo terminal
        }
        await writeActiveSplit(null);
        return;
      }
      if (status?.status === "running") {
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

    await writeActiveSplit({ queueId, total: bundles.length, ts: Date.now() });
    monitorSplitQueue(queueId, bundles.length); // chạy nền để chat không bị khóa khi nhiều tab hoạt động
    if (needsRecovery) {
      const reload = await sendToBackground({ action: "reloadDossierTabAttach", tabId: waitForTabId });
      if (reload?.error) console.warn("[TLND-Split] Không reload được tab đầu:", reload.error);
    }
    return { queued: true, queueId };
  }

  async function runAttachPlan(a) {
    try {
      // Wizard hồ sơ: trang còn ở bước kê khai (chưa sang "Thành phần hồ sơ") mà chạy
      // engine sẽ ra "0 tệp" vô nghĩa → báo BE dặn người dân chuyển bước, watcher thấy
      // đúng bước sẽ tự đính lại. Trang không phải wizard (wizardStep=0) chạy như thường.
      const pre = await sendToContent({ action: "getPageContext" });
      if (pre?.ok && pre.wizardStep && pre.wizardStep !== 3) {
        ask(`__event:attach_blocked:${JSON.stringify({ wizardStep: pre.wizardStep })}`, "system");
        return;
      }
      // Đóng dấu chữ ký trang hiện tại — watcher không bắn lại page_status cho đúng
      // trang này nữa (tránh BE phát lệnh đính kèm lần 2 khi engine đang chạy).
      if (pre?.ok) {
        lastPageSig = `${pre.formKind}|${pre.wizardStep || 0}|${pre.infoModal ? 1 : 0}|${pre.agencyBlock ? 1 : 0}|${pre.attachmentTarget ? 1 : 0}`;
      }
      if (a.mode === "split" && supportsSplitAttach(a.procedure)) {
        const active = await readActiveSplit();
        if (active?.queueId) {
          // Reload/panel dựng lại có thể làm watcher phát lại attach_plan. Queue cũ vẫn là nguồn
          // chân lý; tuyệt đối không khởi động lượt thứ hai hoặc báo attached=0 đè kết quả đang chạy.
          setStatus(`📎 Đang tiếp tục hàng đợi ${active.total || "?"} hồ sơ…`);
          return;
        }
      }
      setStatus("📎 Đang đính kèm giấy tờ vào hồ sơ…");
      const raw = await fetchSessionFilesAsPayload(a.session_id || uploadSid);
      const { files, attachments } = await preparePdfPayload(raw, a.attachments);
      if (a.mode === "split" && supportsSplitAttach(a.procedure)) {
        const split = await runSplitAttachPlan(a, files, attachments);
        if (split?.queued) return;
        setStatus("");
        ask(`__action:attach_report:${JSON.stringify(split?.report || {
          attached: 0, errors: ["Không khởi động được chế độ nhiều hồ sơ."], mode: "split",
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
        errors: res?.error ? [res.error] : (res?.errors || []),
      };
      ask(`__action:attach_report:${JSON.stringify({ ...report, mode: a.mode || "merge" })}`, "system");
    } catch (e) {
      setStatus("");
      ask(`__action:attach_report:${JSON.stringify({ attached: 0, errors: [String(e?.message || e)] })}`, "system");
    }
  }

  // ── Thi hành actions từ BE (tuần tự) ──
  async function runActions(actions) {
    for (const a of actions) {
      if (a.type === "navigate" && a.url) {
        saveJourney(); // giữ con trỏ phiên TRƯỚC khi trang đổi (iframe sẽ bị hủy)
        setStatus("Đang chuyển trang…");
        await sendToContent({ action: "navigate", url: a.url });
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
        // Chụp loggedIn TRƯỚC khi bấm nộp (trang sẽ điều hướng đi) — BE dựa vào đây
        // chọn lời dặn: vào thẳng kê khai hay hướng dẫn quét QR.
        setStatus("Đang chọn cơ quan thực hiện…");
        const pre = await sendToContent({ action: "getPageContext" });
        const res = await sendToContent({ action: "selectAgency", province: a.province, ward: a.ward });
        setStatus("");
        if (res?.ok) ask(`__event:agency_selected:${JSON.stringify({ loggedIn: !!pre?.loggedIn })}`, "system");
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
        // Modal "Thông tin chung" đã điền sẵn đúng cơ quan → bấm Xác nhận hộ, rồi báo lại
        // trạng thái trang để BE dẫn bước kế. Quá 3 lần modal vẫn còn → nhờ bà con bấm tay,
        // ngừng vòng thử (watcher sẽ tiếp tục khi trang thật sự đổi).
        setStatus("Đang xác nhận thông tin chung của hồ sơ…");
        infoModalTries += 1;
        await sendToContent({ action: "confirmInfoModal" });
        await new Promise((r) => setTimeout(r, 1200));
        setStatus("");
        if (infoModalTries <= 3) sendPageStatus();
        else {
          setStatus("⚠️ Bà con bấm nút Xác nhận trên trang giúp em ạ.", true);
          setTimeout(() => setStatus(""), 4000);
        }
      } else if (a.type === "attach_plan" && Array.isArray(a.attachments)) {
        await runAttachPlan(a);
      } else if (a.type === "show_qr") {
        uploadSid = a.session_id;
        renderQrCard(a);
        subscribeUploadSession(a.session_id);
      } else if (a.type === "pick_files" && a.session_id) {
        // Scan tại quầy: mở hộp chọn tệp của máy tính, kết quả đổ vào cùng phiên upload.
        uploadSid = a.session_id;
        subscribeUploadSession(a.session_id);
        $fileInput?.click();
      } else if (a.type === "collapse_after_tts") {
        /* Thu gọn panel sau khi đọc xong — đã xử lý trong renderReply (onDone của TTS). */
      } else {
        console.warn("[TLND] action chưa hỗ trợ:", a.type);
      }
    }
  }

  // ── Header: thu gọn / đóng / TTS mute / cuộc trò chuyện mới ──
  // Màn login che header nên có cặp nút riêng — chung một hành vi thu gọn/đóng.
  const minimizePanel = () => window.parent.postMessage({ __tlnd: "minimizePanel" }, "*");
  const closePanel = () => window.parent.postMessage({ __tlnd: "closePanel" }, "*");
  document.getElementById("min-btn")?.addEventListener("click", minimizePanel);
  document.getElementById("close-btn")?.addEventListener("click", closePanel);
  document.getElementById("login-min-btn")?.addEventListener("click", minimizePanel);
  document.getElementById("login-close-btn")?.addEventListener("click", closePanel);

  // 🔄 Cuộc trò chuyện mới: xoá phiên BE + journey của tab → chào lại từ đầu.
  // (Nút ✕ chỉ ĐÓNG khung — phiên GIỮ NGUYÊN để mở lại làm tiếp; xoá thật là nút này.)
  async function resetConversation() {
    if (busy) return;
    stopVoice?.();
    stopReplyTts();
    setHandsfree?.(false);
    await api.deleteConversation();
    if (TAB_ID) {
      chrome.storage.local.get([JOURNEY_KEY], (res) => {
        const j = res?.[JOURNEY_KEY] || {};
        delete j[TAB_ID];
        chrome.storage.local.set({ [JOURNEY_KEY]: j }, () => void chrome.runtime.lastError);
      });
    }
    $messages.innerHTML = "";
    pipeStop();
    $pipe = null; // node đã bị xoá cùng $messages — bỏ tham chiếu để card mới dựng lại được
    $subtitle.textContent = "Hỗ trợ thủ tục hành chính công";
    if ($meterBar) $meterBar.style.width = "0";
    ask("", "system"); // phiên MỚI → BE chào lại + card chọn nơi/thủ tục
  }
  document.getElementById("reset-btn")?.addEventListener("click", resetConversation);

  const TTS_MUTED_KEY = "tlnd_tts_muted";
  const $ttsBtn = document.getElementById("tts-btn");
  let ttsMuted = false;
  function renderTtsBtn() {
    // Nút giờ có icon + nhãn (span) → chỉ đổi từng phần, không xoá cả textContent (mất nhãn).
    const ic = $ttsBtn.querySelector(".tbi");
    const lb = $ttsBtn.querySelector(".tbl");
    if (ic) ic.textContent = ttsMuted ? "🔇" : "🔊";
    if (lb) lb.textContent = ttsMuted ? "Bật tiếng" : "Âm thanh";
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
    else soon("📷 Bà con chọn cách cung cấp giấy tờ trong hội thoại trước ạ.")();
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

  function setMicUI(listening, label) {
    voiceListening = listening;
    $micBtn?.classList.toggle("listening", listening);
    if (label) setStatus(label); else setStatus("");
  }

  function startVoice() {
    if (!voiceCfg.asr || voiceListening) return;
    stopReplyTts(); // đang đọc mà mở mic = ngắt lời (barge-in)
    setMicUI(true, "🎤 Đang kết nối…");
    chrome.runtime.sendMessage({ type: "asr-start", lang: "vi", baseUrl: BASE_URL },
      () => void chrome.runtime.lastError);
  }
  function stopVoice() {
    chrome.runtime.sendMessage({ type: "asr-stop" }, () => void chrome.runtime.lastError);
    setMicUI(false);
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type !== "asr-event") return;
    if (msg.event === "state") {
      if (msg.state === "listening") setMicUI(true, "🎤 Đang lắng nghe… bà con nói đi ạ");
      else if (msg.state === "stopped") {
        // Server đóng mà không có final (không nghe thấy gì).
        setMicUI(false);
        if (handsfree) {
          emptyTurns += 1;
          if (emptyTurns >= 2) { setHandsfree(false); addBotMd("Em tạm tắt chế độ rảnh tay vì không nghe thấy bà con nói ạ. Bấm 🎙️ để bật lại nhé."); }
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
      // Bật rảnh tay ngay ở màn chào → đọc lại câu chào (bà con nghe + thấy) rồi tự mở mic nghe.
      if (lastState === "greet" && lastReplyData?.tts_text && voiceCfg.tts && !ttsMuted) {
        stopReplyTts();
        window.__hccTTS?.speak?.(lastReplyData.tts_text, "vi", () => startVoice());
        return;
      }
      startVoice();
    } else { stopVoice(); stopReplyTts(); }
  }
  $hfBtn?.addEventListener("click", () => {
    if (!voiceCfg.asr) { soon("🎙️ Máy chủ chưa bật giọng nói.")(); return; }
    setHandsfree(!handsfree);
  });

  // Init voice: lấy base URL cho tts.js/asr + hỏi BE bật kênh nào; tắt thì ẩn nút.
  (async () => {
    BASE_URL = await window.tlndBaseUrl();
    window.HCC_BASE_URL = BASE_URL; // services/tts.js đọc biến này để dựng URL /ws/tts
    try {
      const res = await fetch(`${BASE_URL}/api/v1/voice/config`);
      if (res.ok) voiceCfg = await res.json();
    } catch (_) { /* BE chưa chạy → giữ tắt */ }
    if (!voiceCfg.asr) {
      if ($micBtn) $micBtn.hidden = true;
      if ($hfBtn) $hfBtn.hidden = true;
    }
    window.__hccTTS?.setMuted?.(ttsMuted);
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

  // ── Khởi động chat: có journey → khôi phục phiên; không → chào mới ──
  // Chỉ chạy SAU khi đã đăng nhập; token chết giữa chừng đăng nhập lại thì
  // KHÔNG boot lại (khung chat + phiên đang dở giữ nguyên phía sau màn login).
  let booted = false;
  async function bootChat() {
    if (booted) return;
    booted = true;
    const j = await loadJourney();
    if (j?.conversation_id) {
      const conv = await api.getConversation(j.conversation_id).catch(() => null);
      if (conv) {
        const activeSplit = await readActiveSplit();
        if (activeSplit?.queueId) {
          // Tab đầu có thể vừa reload để phục hồi ví tài liệu; nối lại poll queue thay vì báo mất lượt.
          monitorSplitQueue(activeSplit.queueId, activeSplit.total || 0);
        }
        // Mở lại khi CÒN Ở MÀN CHÀO (chưa làm gì) → chào lại + ĐỌC (handsfree nghe được câu chào),
        // không khôi phục im lặng như các bước giữa chừng. last_reply màn chào đã gồm card nơi/thủ tục.
        if (conv.state === "greet") {
          lastState = "greet";
          if (conv.last_reply) renderReply(conv.last_reply, {});
          setProgress(conv.progress);
          console.log(`[TLND] mở lại ở màn chào ${conv.conversation_id} → chào lại`);
          return;
        }
        // Render lại đuôi hội thoại + reply cuối (chips/cards còn bấm được).
        (conv.history || []).slice(0, -1).forEach((h) => {
          if (h.role === "user") addUserText(h.text);
          else addBotMd(h.text);
        });
        if (conv.last_reply) renderReply(conv.last_reply, { noTts: true });
        lastState = conv.state || lastState;
        schedulePageWatcher();
        setProgress(conv.progress);
        console.log(`[TLND] khôi phục phiên ${conv.conversation_id} state=${conv.state}`);
        // Đang ở chặng mở trang/đăng nhập → báo trạng thái trang cho BE quyết bước tiếp
        // (chọn cơ quan / nhắc QR / vào thẳng kê khai) — không bắt người dân bấm gì thêm.
        if (conv.state === "guide_login") {
          setTimeout(sendPageStatus, 500);
        }
        return;
      }
    }
    ask("", "system"); // phiên mới → BE trả màn chào + card chọn nơi/thủ tục
  }

  // ── Đăng nhập quầy (bắt buộc, mọi role) — api/auth.js giữ token, ở đây chỉ UI ──
  const $scrim = document.getElementById("login-scrim");
  const $loginForm = document.getElementById("login-form");
  const $loginUser = document.getElementById("login-user");
  const $loginPass = document.getElementById("login-pass");
  const $loginErr = document.getElementById("login-err");
  const $loginBtn = document.getElementById("login-btn");
  const $accBtn = document.getElementById("acc-btn");
  const $accPop = document.getElementById("acc-pop");
  document.getElementById("login-avatar").innerHTML = ROBOT(34);

  function showLogin() {
    $scrim.hidden = false;
    $accBtn.hidden = true;
    $accBtn.classList.remove("active");
    $accPop.hidden = true;
    stopVoice();
    stopReplyTts();
    setHandsfree(false);
    setTimeout(() => $loginUser?.focus(), 60);
  }

  function renderAccount() {
    const u = window.tlndAuth.user;
    if (!u) { $accBtn.hidden = true; return; }
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
    $loginErr.hidden = true;
    try {
      await window.tlndAuth.login(u, p);
      $loginPass.value = "";
      $scrim.hidden = true;
      renderAccount();
      bootChat();
    } catch (err) {
      $loginErr.textContent = err?.message || "Đăng nhập thất bại";
      $loginErr.hidden = false;
    } finally {
      $loginBtn.disabled = false;
    }
  });

  // authFetch hết đường refresh (401 lần 2) → bật lại màn đăng nhập, chat giữ nguyên.
  window.addEventListener("tlnd-auth-required", showLogin);

  (async () => {
    const st = await window.tlndAuth.load();
    if (st?.access) { renderAccount(); bootChat(); }
    else showLogin();
  })();

  console.log(`[TLND] sidebar sẵn sàng — tabId=${TAB_ID}`);
})();
