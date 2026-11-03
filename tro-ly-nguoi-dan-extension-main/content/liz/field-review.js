// Bổ sung ô còn trống trên trang nộp một trang của cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn, form liz — Angular
// Material, DOM đã strip formcontrolname). Cùng giao thức fieldReviewMark / fieldReviewNext / fieldReviewStop với
// content/field-review.js nên sidebar và BE (chat/field_review) dùng chung; file này chỉ khác cách đọc / ghi ô:
//   - mỗi ô là một mat-form-field ĐANG HIỆN, sửa được; khoá của ô = thuộc tính name (ô khung trang: biên lai, người
//     nhận bưu điện…) hoặc nhãn <mat-label> (ô form động không có name) — BE khai REQUIRED / NO_ASK theo đúng khoá đó;
//   - nhãn lặp giữa khối người nộp / khối ủy quyền (Email, Ngày sinh…) → phân biệt bằng tiêu đề khối (.group-header)
//     và thứ tự xuất hiện;
//   - ô bắt buộc = dấu * của Angular Material (mat-mdc-form-field-required-marker / required) hoặc tên BE khai;
//   - lựa chọn của mat-select chỉ có khi mở overlay → mở một nhịp để đọc rồi đóng; ô có ô lọc (danh sách xã hàng nghìn
//     dòng, chỉ nạp một phần) hỏi như ô gõ tự do, điền bằng engine lọc của fill-liz.js;
//   - điền câu trả lời bằng H.fillLizFieldElement (content/fill-liz.js) cho đúng ô đó;
//   - con trỏ + khung gợi ý dùng chung H.fieldReviewPointer của content/field-review.js.
(() => {
  if (window.__TLND_FIELD_REVIEW_LIZ__) return;
  window.__TLND_FIELD_REVIEW_LIZ__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.bvhttdl.gov.vn";
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-liz-field-review-style";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s+/g, " ").trim();
  const fold = (s) => cleanLabel(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d")
    .replace(/[\s.:]+$/, "");
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const ourPage = () => location.hostname === HOST && H.detectFormKind?.() === "liz";

  function injectStyles() {
    if (typeof H.injectAutofillStyles === "function") H.injectAutofillStyles();
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .${OPTIONAL} { background-color: #fff3e0 !important; outline: 2px solid #fb8c00 !important;
        outline-offset: 1px !important; border-radius: 3px !important; }
      .${ASKING} { outline: 3px solid #1e66f5 !important; outline-offset: 2px !important;
        box-shadow: 0 0 0 6px rgba(30, 102, 245, .22) !important; border-radius: 4px !important; }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  // ── Đọc ô ──

  function labelOf(mf, control) {
    const own = textOf(mf.querySelector("mat-label"));
    if (own) return cleanLabel(own);
    const floating = textOf(mf.querySelector(".mdc-floating-label, .mat-form-field-label, label"));
    if (floating) return cleanLabel(floating);
    return cleanLabel(control?.getAttribute("data-placeholder") || control?.getAttribute("placeholder")
      || control?.getAttribute("aria-label") || "");
  }

  function sectionOf(mf) {
    return cleanLabel(textOf(mf.closest(".group")?.querySelector(".group-header")));
  }

  const kindOf = (mf) => {
    if (mf.querySelector("mat-select")) return "select";
    if (mf.closest("liz-datepicker, liz-date") || mf.querySelector("mat-datepicker-toggle, .mat-datepicker-toggle,"
      + " input[matdatepicker], .mat-datepicker-input")) return "date";
    return "text";
  };

  const locked = (mf, control, kind) => (kind === "select"
    ? control.getAttribute("aria-disabled") === "true" || control.classList.contains("mat-mdc-select-disabled")
    : control.disabled || control.readOnly);

  const marked = (mf, control) => !!mf.querySelector(".mat-mdc-form-field-required-marker, "
    + ".mat-form-field-required-marker") || control.required || control.getAttribute("aria-required") === "true";

  function valueReader(mf, control, kind) {
    if (kind === "select") {
      return () => cleanLabel(textOf(mf.querySelector(".mat-mdc-select-value-text, .mat-select-value-text")));
    }
    return () => String(control.value || "").trim();
  }

  // Lựa chọn đã đọc theo khoá ô (đọc lại mỗi lần sẽ phải mở overlay liên tục). null = chưa đọc; free = ô có ô lọc.
  const optionCache = new Map();

  // Mọi ô ĐANG HIỆN, sửa được, theo thứ tự trên trang.
  function slots(noAsk) {
    const skip = new Set((noAsk || []).map(fold));
    const counts = new Map();
    const out = [];
    for (const mf of document.querySelectorAll("mat-form-field")) {
      if (!shown(mf) || mf.closest(".cdk-overlay-container")) continue;
      const kind = kindOf(mf);
      const control = kind === "select" ? mf.querySelector("mat-select") : mf.querySelector("input, textarea");
      if (!control || locked(mf, control, kind)) continue;
      const label = labelOf(mf, control);
      const name = cleanLabel(control.getAttribute("name") || "") || label;
      if (!name || skip.has(fold(name)) || skip.has(fold(label))) continue;
      const section = sectionOf(mf);
      const base = `${fold(section)}||${fold(label) || fold(name)}`;
      const occurrence = counts.get(base) || 0;
      counts.set(base, occurrence + 1);
      out.push({
        key: occurrence ? `${base}#${occurrence}` : base, name, label: label || name, section, kind, mf, control,
        marker: marked(mf, control), value: valueReader(mf, control, kind),
      });
    }
    return out;
  }

  const overlayOptions = () => Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"))
    .filter(shown);

  async function closeOverlay() {
    document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
    await sleep(150);
    document.querySelector(".cdk-overlay-backdrop")?.click();
    await sleep(150);
  }

  // Mở overlay của ô chọn một nhịp để đọc lựa chọn rồi đóng, không đổi giá trị.
  async function loadOptions(slot) {
    if (optionCache.has(slot.key)) return optionCache.get(slot.key);
    const trigger = slot.control.querySelector(".mat-mdc-select-trigger, .mat-select-trigger") || slot.control;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    for (let waited = 0; waited < 2500 && !overlayOptions().length; waited += 150) await sleep(150);
    const search = document.querySelector(".cdk-overlay-container input[type=text]");
    const options = [...new Set(overlayOptions().filter((o) => !o.querySelector("input"))
      .map((o) => cleanLabel(textOf(o))).filter(Boolean))];
    await closeOverlay();
    const entry = search ? { free: true, options: [] } : { free: false, options: options.slice(0, 400) };
    if (entry.free || entry.options.length) optionCache.set(slot.key, entry);
    return entry;
  }

  // ── Tô màu ──

  function clearMarks() {
    document.querySelectorAll(MARKS.map((m) => `.${m}`).join(",")).forEach((el) => el.classList.remove(...MARKS));
  }

  function markAll(msg) {
    injectStyles();
    clearMarks();
    const need = new Set((msg.required || []).map(fold));
    const stats = { filled: 0, optional: 0, required: 0 };
    const list = slots(msg.noAsk);
    for (const slot of list) {
      slot.required = need.has(fold(slot.name)) || need.has(fold(slot.label)) || slot.marker;
      if (slot.value()) { slot.mf.classList.add("autofill-filled"); stats.filled += 1; }
      else if (slot.required) { slot.mf.classList.add("autofill-not-filled"); stats.required += 1; }
      else { slot.mf.classList.add(OPTIONAL); stats.optional += 1; }
    }
    lastStatsKey = JSON.stringify(stats);
    return { list, stats };
  }

  // Công dân gõ / chọn thẳng trên trang → ~1 giây sau tô lại, báo sidebar khi số ô đổi (như content/field-review.js).
  const WATCH_DEBOUNCE_MS = 1000;
  let watchRules = null;
  let watchTimer = null;
  let lastStatsKey = "";
  function onFormEdited() {
    if (!watchRules || !ourPage()) return;
    clearTimeout(watchTimer);
    watchTimer = setTimeout(() => {
      const before = lastStatsKey;
      const { stats } = markAll(watchRules);
      if (lastStatsKey === before) return;
      try {
        chrome.runtime.sendMessage({ __tlnd: "fieldReviewStats", stats }, () => void chrome.runtime.lastError);
      } catch (_) { /* extension vừa reload: bỏ lượt báo này */ }
    }, WATCH_DEBOUNCE_MS);
  }
  document.addEventListener("input", onFormEdited, true);
  document.addEventListener("change", onFormEdited, true);

  // ── Điền một ô ──

  async function applyValue(slot, value) {
    if (typeof H.fillLizFieldElement !== "function") return false;
    try {
      await H.fillLizFieldElement(slot.mf, value);
    } catch (e) {
      console.warn("[TLND] bổ sung ô liz lỗi:", e);
      return false;
    }
    await sleep(300);
    const fresh = slots(watchRules?.noAsk).find((s) => s.key === slot.key);
    return !!fresh?.value();
  }

  function publicField(slot) {
    const entry = optionCache.get(slot.key);
    const choices = slot.kind === "select" && entry && !entry.free ? entry.options : [];
    return {
      key: slot.key, name: slot.name, role: "", kind: slot.kind === "select" && !choices.length ? "text" : slot.kind,
      yearOnly: false, partialDate: false, label: slot.label, group: "", section: slot.section || "",
      required: !!slot.required, options: choices, value: slot.value(),
    };
  }

  function unfocus() {
    document.querySelectorAll(`.${ASKING}`).forEach((el) => el.classList.remove(ASKING));
    H.fieldReviewPointer?.unfocus();
  }

  async function focusSlot(slot) {
    unfocus();
    await H.fieldReviewPointer?.focus(slot.mf);
    slot.mf.classList.add(ASKING);
  }

  async function next(msg) {
    const skip = new Set(Array.isArray(msg.skip) ? msg.skip : []);
    let applied = null;
    if (msg.apply && msg.apply.key) {
      const target = slots(msg.noAsk).find((s) => s.key === msg.apply.key);
      const ok = target ? await applyValue(target, String(msg.apply.value ?? "")) : false;
      applied = { key: msg.apply.key, ok };
      // Điền không được thì không hỏi lại ô đó ngay ở lượt này (BE cũng ghi vào danh sách bỏ qua).
      if (!ok) skip.add(msg.apply.key);
      await sleep(400); // khối ô của lựa chọn vừa chọn vẽ sau một nhịp
    }
    const { list, stats } = markAll(msg);
    // focus: công dân xin sửa một ô đã hỏi → về đúng ô đó dù đã có giá trị; không thì ô trống kế tiếp.
    // requiredFirst: hỏi hết ô bắt buộc trống trước rồi mới tới ô không bắt buộc.
    const askable = (s) => !s.value() && !skip.has(s.key);
    const slot = (msg.focus && list.find((s) => s.key === msg.focus || s.name === msg.focus))
      || (msg.requiredFirst && list.find((s) => s.required && askable(s)))
      || list.find(askable);
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats }; }
    if (slot.kind === "select") await loadOptions(slot);
    await focusSlot(slot);
    return { ok: true, applied, field: publicField(slot), stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // Chỉ trang nộp liz của cổng Bộ VHTTDL trả lời; eForm / SurveyJS / Form.io có bộ đọc riêng.
    if (!ourPage()) return;
    if (action === "fieldReviewMark") {
      watchRules = msg;
      optionCache.clear();
      sendResponse({ ok: true, stats: markAll(msg).stats });
      return;
    }
    if (action === "fieldReviewStop") {
      unfocus();
      sendResponse({ ok: true });
      return;
    }
    if (action === "fieldReviewNext") {
      watchRules = watchRules || msg;
      next(msg).then(sendResponse).catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
      return true;
    }
  });
})();
