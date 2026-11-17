// Bổ sung ô còn trống + nút Nộp hồ sơ trên trang cổng DVC Bộ Công an (dichvucong.dancuquocgia.gov.vn: jQuery + bootstrap
// + select2; form, đính kèm, ô cam kết và nút nộp cùng một trang). Cùng giao thức fieldReviewMark / fieldReviewNext /
// fieldReviewStop với content/field-review.js nên sidebar và BE (chat/field_review) dùng chung; file này chỉ khác cách
// đọc / ghi ô:
//   - mỗi ô là input / select / textarea ĐANG HIỆN, sửa được, có id hoặc name (select2: thẻ <select> gốc bị ẩn, ô công dân
//     thấy là .select2-container ngay sau); radio gộp theo name; ô tích (cam kết, tuỳ chọn) không hỏi;
//   - nhãn: label[for], hoặc nhãn gần nhất phía trước trong khối của ô (không vượt qua ô khác), ô trong bảng lấy tiêu đề
//     cột; ô không có nhãn riêng (ô chọn cơ quan) lấy chữ gợi ý "Chọn …";
//   - ô bắt buộc = dấu * trên nhãn (cổng tô đỏ), thuộc tính required, hoặc tên BE khai (REQUIRED);
//   - điền câu trả lời bằng engine chuẩn của extension (H.fillFormStandard: dom-input / dom-select / dom-date / dom-radio)
//     cho đúng một ô;
//   - con trỏ + khung gợi ý dùng chung H.fieldReviewPointer của content/field-review.js;
//   - nút Nộp hồ sơ của trợ lý (lệnh bcaSubmit): soát lại ô bắt buộc + ô cam kết, đủ thì bấm nút nộp của cổng; trang căn
//     cước Bước 1 chưa có nút nộp thì bấm "Lưu và Tiếp tục" (nextIds) sang Bước 2 đặt lịch. Cổng hỏi xác nhận thì để công
//     dân tự bấm Đồng ý — trợ lý không bấm thay câu xác nhận nộp.
(() => {
  if (window.__TLND_FIELD_REVIEW_BCA__) return;
  window.__TLND_FIELD_REVIEW_BCA__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.dancuquocgia.gov.vn";
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-bca-field-review-style";
  const SKIP_TYPES = /^(hidden|button|submit|reset|file|image|checkbox|password|search|color|range)$/;
  const LABEL_SEL = "label, .control-label, .col-form-label, .title-input";
  const FOLLOWING = Node.DOCUMENT_POSITION_FOLLOWING;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const cleanLabel = (s) => String(s || "").replace(/[*＊]/g, "").replace(/\s+/g, " ").replace(/[\s:]+$/, "").trim();
  const fold = (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const ourPage = () => location.hostname === HOST && window.top === window && H.detectFormKind?.() === "standard";

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

  // Dòng gợi ý của ô chọn ("Chọn", "-- Chọn tỉnh --", "Chọn cơ quan Công an cấp Tỉnh/TP") không phải giá trị.
  const isPlaceholder = (text) => {
    const t = fold(text).replace(/[-–—.…:]+/g, " ").trim();
    return !t || /^chon\b/.test(t) || t.startsWith("vui long chon") || t.startsWith("khong tim thay");
  };

  // Ô công dân thấy: select2 ẩn <select> gốc và vẽ .select2-container ngay sau (bản cũ: #s2id_<id> đứng trước).
  function boxOf(el) {
    if (el.tagName === "SELECT") {
      const next = el.nextElementSibling;
      if (next?.classList?.contains("select2")) return next.querySelector(".select2-selection") || next;
      const old = el.id ? document.getElementById(`s2id_${el.id}`) : null;
      if (old) return old;
    }
    return el;
  }

  const isDateInput = (el) => el.tagName === "INPUT" && (
    /date|birth/i.test(`${el.id} ${el.name} ${el.className}`) || /dd\s*\/\s*mm/i.test(el.placeholder || "")
    || !!el.closest(".date, .input-group.date, .datepicker"));

  function radioLabel(radio) {
    const own = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
    const text = textOf(own) || textOf(radio.closest("label"));
    if (text) return cleanLabel(text);
    let node = radio.nextSibling;
    while (node && node.nodeType === Node.TEXT_NODE && !node.textContent.trim()) node = node.nextSibling;
    return cleanLabel(node?.nodeType === Node.TEXT_NODE ? node.textContent : textOf(node)) || String(radio.value || "");
  }

  // Nhãn của một lựa chọn (ô radio / ô tích) — không phải nhãn của ô.
  function optionLabel(label) {
    if (label.querySelector("input, select, textarea")) return true;
    const target = label.htmlFor ? document.getElementById(label.htmlFor) : null;
    return target?.type === "radio" || target?.type === "checkbox";
  }

  // Phần tử chung nhỏ nhất chứa cả nhóm radio.
  function commonBox(nodes) {
    let box = nodes[0]?.parentElement || null;
    while (box && !nodes.every((n) => box.contains(n))) box = box.parentElement;
    return box;
  }

  const controlsIn = (root) => Array.from(root.querySelectorAll("input, select, textarea"));
  // Radio tự vẽ (ô gốc ẩn, nhãn hiện) vẫn là ô đang hiện.
  const radioShown = (r) => shown(r) || shown(r.closest("label")) || shown(r.parentElement);
  const counted = (c) => !SKIP_TYPES.test(c.type || "") && !c.closest(".select2-container")
    && (c.type === "radio" ? radioShown(c) : shown(boxOf(c)));

  // Nhãn gần nhất phía trước `target` trong `container`; giữa nhãn và ô có ô khác (không tính các radio cùng nhóm
  // `group`) thì nhãn đó là của ô khác → null.
  function precedingLabel(container, target, group = []) {
    const labels = Array.from(container.querySelectorAll(LABEL_SEL)).filter((l) => !target.contains(l)
      && !l.contains(target) && !optionLabel(l) && textOf(l) && shown(l) && (l.compareDocumentPosition(target) & FOLLOWING));
    const label = labels[labels.length - 1];
    if (!label) return null;
    const between = controlsIn(container).some((c) => !target.contains(c) && c !== target && !group.includes(c)
      && counted(c) && (label.compareDocumentPosition(c) & FOLLOWING) && (c.compareDocumentPosition(target) & FOLLOWING));
    return between ? null : label;
  }

  // Ô trong bảng (thành viên hộ, người lưu trú): nhãn ở dòng tiêu đề theo đúng cột.
  function columnLabel(el) {
    const cell = el.closest("td");
    const table = cell?.closest("table");
    if (!cell || !table) return "";
    const index = Array.from(cell.parentElement.children).indexOf(cell);
    return cleanLabel(textOf(table.querySelectorAll("thead th")[index]));
  }

  // Ô chọn không có nhãn riêng: chữ gợi ý "Chọn cơ quan Công an cấp Tỉnh/TP" → "Cơ quan Công an cấp Tỉnh/TP".
  function hintOf(el) {
    const raw = el.tagName === "SELECT" ? textOf(el.options?.[0]) : String(el.placeholder || "");
    const text = cleanLabel(raw.replace(/^[-–—\s]*(chọn|nhập)\s*/i, "").replace(/[-–—\s]+$/, ""));
    return text ? text[0].toUpperCase() + text.slice(1) : "";
  }

  const markedLabel = (label) => !!label && (/[*＊]/.test(label.textContent || "")
    || !!label.querySelector(".required, .text-danger, .red, .star"));

  // → { text, marked }: nhãn của ô + nhãn có dấu * hay không. Radio: `anchor` = radio đầu nhóm, `group` = cả nhóm.
  function labelOf(el, anchor, group = []) {
    if (el.id && el.type !== "radio") {
      const own = Array.from(document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`)).find((l) => textOf(l));
      if (own) return { text: cleanLabel(textOf(own)), marked: markedLabel(own) };
    }
    const column = columnLabel(el);
    if (column) return { text: column, marked: false };
    let level = 0;
    for (let node = anchor.parentElement; node && level < 5; node = node.parentElement, level += 1) {
      if (level === 2) {
        // Hai cấp gần nhất không có nhãn: ô chọn cơ quan / ô ghi chú đứng dưới nhãn chung → chữ gợi ý rõ nghĩa hơn.
        const hint = hintOf(el);
        if (hint) return { text: hint, marked: false };
      }
      const label = precedingLabel(node, anchor, group);
      if (label) return { text: cleanLabel(textOf(label)), marked: markedLabel(label) };
      if (node.matches?.(".box, fieldset, form")) break;
    }
    return { text: hintOf(el), marked: false };
  }

  function sectionOf(el) {
    const box = el.closest(".box, fieldset, .panel, .card");
    if (!box) return "";
    const head = Array.from(box.querySelectorAll(".box-header, .box-title, .title-box, .panel-heading, .card-header, "
      + "legend, h2, h3, h4, h5")).find((h) => !h.querySelector("input, select, textarea") && textOf(h)
      && (h.compareDocumentPosition(el) & FOLLOWING));
    return cleanLabel(textOf(head)).slice(0, 80);
  }

  function selectValue(sel) {
    const option = sel.selectedOptions?.[0];
    if (!option || !String(sel.value || "").trim() || sel.value === "-1") return "";
    const text = cleanLabel(textOf(option));
    return isPlaceholder(text) ? "" : text;
  }

  const selectOptions = (sel) => [...new Set(Array.from(sel.options || [])
    .filter((o) => String(o.value || "").trim() && o.value !== "-1" && !o.disabled)
    .map((o) => cleanLabel(textOf(o))).filter((t) => t && !isPlaceholder(t)))].slice(0, 400);

  // Mọi ô ĐANG HIỆN, sửa được, theo thứ tự trên trang.
  function slots(noAsk) {
    const skip = new Set(noAsk || []);
    const seenRadio = new Set();
    const counts = new Map();
    const out = [];
    for (const el of controlsIn(document)) {
      if (!counted(el) || el.disabled || el.closest("[id^='tlnd'], .tlnd-panel")) continue;
      const kind = el.tagName === "SELECT" ? "select" : el.type === "radio" ? "radio" : isDateInput(el) ? "date"
        : "text";
      // Ô chỉ đọc (địa chỉ trạm công an tự hiện theo cơ quan…) không hỏi; ô ngày của datepicker có khi để readonly.
      if (el.readOnly && kind !== "date") continue;
      const name = el.getAttribute("name") || el.id || "";
      if (!name || skip.has(name) || (el.id && skip.has(el.id))) continue;
      let box = boxOf(el);
      let group = [];
      let value;
      let options = () => [];
      if (kind === "radio") {
        if (seenRadio.has(name)) continue;
        seenRadio.add(name);
        group = Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
          .filter(radioShown);
        if (!group.length || group.every((r) => r.disabled)) continue;
        // Khung tô = khối chung nhỏ nhất của nhóm; khối đó chứa cả ô khác (ô chọn cơ quan dưới radio cấp) thì chỉ tô
        // lựa chọn đầu.
        box = commonBox(group) || el.parentElement || el;
        if (controlsIn(box).some((c) => !group.includes(c) && counted(c))) {
          box = group[0].closest(".radio, label") || group[0].parentElement || group[0];
        }
        value = () => {
          const checked = group.find((r) => r.checked);
          return checked ? radioLabel(checked) : "";
        };
        options = () => group.map(radioLabel).filter(Boolean);
      } else if (kind === "select") {
        value = () => selectValue(el);
        options = () => selectOptions(el);
      } else {
        value = () => String(el.value || "").trim();
      }
      const { text, marked } = labelOf(el, group[0] || el, group);
      const occurrence = counts.get(name) || 0;
      counts.set(name, occurrence + 1);
      out.push({
        key: occurrence ? `${name}#${occurrence}` : name, name, id: el.id || "", kind, el, box, occurrence,
        label: text || name, section: sectionOf(el),
        marker: marked || el.required || el.getAttribute("aria-required") === "true",
        value, options,
      });
    }
    for (const slot of out) slot.duplicate = (counts.get(slot.name) || 0) > 1;
    return out;
  }

  // ── Tô màu ──

  function clearMarks() {
    document.querySelectorAll(MARKS.map((m) => `.${m}`).join(",")).forEach((el) => el.classList.remove(...MARKS));
  }

  function markAll(msg) {
    injectStyles();
    clearMarks();
    const need = new Set((msg?.required || []).map(String));
    const stats = { filled: 0, optional: 0, required: 0 };
    const list = slots(msg?.noAsk);
    for (const slot of list) {
      slot.required = need.has(slot.name) || (!!slot.id && need.has(slot.id)) || slot.marker;
      if (slot.value()) { slot.box.classList.add("autofill-filled"); stats.filled += 1; }
      else if (slot.required) { slot.box.classList.add("autofill-not-filled"); stats.required += 1; }
      else { slot.box.classList.add(OPTIONAL); stats.optional += 1; }
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

  // Ô cam kết cuối trang (BE gửi commitId / commitLabel kèm lệnh tô ô): công dân tự tích / bỏ tích → báo sidebar để trợ
  // lý hiện / rút nút Nộp hồ sơ. Cú tích của chính trợ lý (content.js tickCommitBox đặt cờ) đã có câu trả lời riêng.
  document.addEventListener("change", (event) => {
    const target = event.target;
    if (!watchRules || target?.type !== "checkbox" || window.__TLND_COMMIT_BY_ASSISTANT__ || !ourPage()) return;
    if (!(watchRules.commitId || watchRules.commitLabel)) return;
    if (commitBox(watchRules.commitId, watchRules.commitLabel) !== target) return;
    try {
      chrome.runtime.sendMessage({ __tlnd: "bcaCommitChanged", checked: !!target.checked },
        () => void chrome.runtime.lastError);
    } catch (_) { /* extension vừa reload: bỏ lượt báo này */ }
  }, true);

  // ── Điền một ô bằng engine chuẩn ──

  const COMP_BY_KIND = { text: "dom-input", select: "dom-select", date: "dom-date", radio: "dom-radio" };

  async function applyValue(slot, value) {
    if (typeof H.fillFormStandard !== "function") return false;
    const field = { name: slot.name, comp: COMP_BY_KIND[slot.kind], value };
    if (slot.duplicate) field.occurrence = slot.occurrence;
    try {
      await H.fillFormStandard([field]);
    } catch (e) {
      console.warn("[TLND] bổ sung ô Bộ Công an lỗi:", e);
      return false;
    }
    await sleep(300);
    const fresh = slots(watchRules?.noAsk).find((s) => s.key === slot.key);
    return !!fresh?.value();
  }

  function publicField(slot) {
    return {
      key: slot.key, name: slot.name, role: "", kind: slot.kind, yearOnly: false, partialDate: false,
      label: slot.label, group: "", section: slot.section || "", required: !!slot.required,
      options: slot.options(), value: slot.value(),
    };
  }

  function unfocus() {
    document.querySelectorAll(`.${ASKING}`).forEach((el) => el.classList.remove(ASKING));
    H.fieldReviewPointer?.unfocus();
  }

  async function focusSlot(slot) {
    unfocus();
    await H.fieldReviewPointer?.focus(slot.box);
    slot.box.classList.add(ASKING);
  }

  function catalogOf(msg, list) {
    if (!msg?.catalog) return {};
    return { catalog: list.map(publicField) };
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
      await sleep(400); // chọn Tỉnh → cổng nạp danh sách Xã; chọn lý do → khối ô mới hiện sau một nhịp
    }
    const { list, stats } = markAll(msg);
    // Ô chọn chưa có lựa chọn (danh sách Xã chờ chọn Tỉnh) chưa hỏi được → hỏi ô khác trước, lượt sau quét lại.
    const askable = (s) => !s.value() && !skip.has(s.key) && (s.kind !== "select" || s.options().length > 0);
    const slot = (msg.focus && list.find((s) => s.key === msg.focus || s.name === msg.focus))
      || (msg.requiredFirst && list.find((s) => s.required && askable(s)))
      || list.find(askable);
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats, ...catalogOf(msg, list) }; }
    await focusSlot(slot);
    return { ok: true, applied, field: publicField(slot), stats, ...catalogOf(msg, list) };
  }

  // ── Nút Nộp hồ sơ ──

  // Ô cam kết cuối trang: theo id BE gửi, không thấy thì theo nhãn (trang căn cước chưa biết id ô cam đoan).
  function commitBox(id, label) {
    const byId = id ? document.getElementById(id) : null;
    if (byId?.type === "checkbox") return byId;
    const want = fold(cleanLabel(label));
    if (!want) return null;
    return Array.from(document.querySelectorAll('input[type="checkbox"]')).find((box) => [
      ...Array.from(box.labels || []).map((l) => l.textContent), box.closest("label")?.textContent,
      box.parentElement?.textContent,
    ].some((t) => fold(t).includes(want))) || null;
  }

  const commitShown = (box) => shown(box) || shown(box.parentElement) || Array.from(box.labels || []).some(shown);
  const usable = (b) => !!b && shown(b) && !b.disabled && !b.classList.contains("disabled");
  const buttonText = (b) => fold(textOf(b) || b.value || "").replace(/[<>›»‹«]+/g, "").trim();

  function submitButton(msg) {
    for (const id of msg.buttonIds || []) {
      const button = document.getElementById(id);
      if (usable(button)) return { el: button, stage: "submit" };
    }
    const texts = new Set((msg.buttonText || []).map(fold));
    const byText = Array.from(document.querySelectorAll("button, input[type='button'], input[type='submit'], a.btn"))
      .find((b) => usable(b) && texts.has(buttonText(b)));
    if (byText) return { el: byText, stage: "submit" };
    for (const id of msg.nextIds || []) {
      const button = document.getElementById(id);
      if (usable(button)) return { el: button, stage: "next" };
    }
    return null;
  }

  // Lời cổng hiện sau cú bấm: hộp thoại bootstrap / jconfirm / toast / sweetalert đang hiện.
  const ALERT_SEL = ".modal.in, .modal.show, .jconfirm-box, .toast, .toast-message, .swal2-popup, .bootbox, "
    + ".alert-danger, .noty_body";
  function alerts() {
    return Array.from(document.querySelectorAll(ALERT_SEL)).filter(shown).map((el) => {
      const body = el.querySelector(".modal-body, .jconfirm-content, .swal2-html-container, .bootbox-body") || el;
      const buttons = Array.from(el.querySelectorAll("button, a.btn")).filter(shown).map(buttonText);
      return { el, text: textOf(body).slice(0, 300), buttons };
    }).filter((a) => a.text);
  }

  // Hộp hỏi lại "Bạn có chắc chắn nộp hồ sơ?" (có nút Đồng ý / Xác nhận / Có) — để công dân tự bấm.
  const isConfirm = (a) => /\?|chac chan|xac nhan/.test(fold(a.text))
    && a.buttons.some((b) => /^(dong y|xac nhan|co|ok|nop)\b/.test(b));

  async function submit(msg) {
    const rules = msg.fieldReview || {};
    watchRules = watchRules || rules;
    const { stats } = markAll(rules);
    if (stats.required) return { clicked: false, missing: ["required"], stats };
    const box = commitBox(msg.commitId, msg.commitLabel);
    if (box && commitShown(box) && !box.checked) {
      box.scrollIntoView({ block: "center", behavior: "smooth" });
      return { clicked: false, missing: ["commit"], stats };
    }
    const pick = submitButton(msg);
    if (!pick) return { clicked: false, stats };
    const before = new Set(alerts().map((a) => a.el));
    pick.el.scrollIntoView({ block: "center", behavior: "smooth" });
    await sleep(300);
    pick.el.click();
    let shownAlert = null;
    for (let waited = 0; waited < 3000 && !shownAlert; waited += 250) {
      await sleep(250);
      shownAlert = alerts().find((a) => !before.has(a.el)) || null;
    }
    const button = cleanLabel(textOf(pick.el) || pick.el.value || "");
    if (shownAlert && isConfirm(shownAlert)) return { clicked: true, stage: pick.stage, button, confirm: true };
    const message = shownAlert && !/thanh cong/.test(fold(shownAlert.text)) ? shownAlert.text : "";
    // Cổng chặn vì ô trống thì tô lỗi dưới ô → tô lại theo 3 màu cho BE biết số ô đỏ.
    return { clicked: true, stage: pick.stage, button, message, stats: markAll(rules).stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (action !== "bcaSubmit" && !action.startsWith("fieldReview")) return;
    // Chỉ trang chính của cổng Bộ Công an trả lời; eForm / SurveyJS / Form.io / liz có bộ đọc riêng.
    if (!ourPage()) return;
    if (action === "bcaSubmit") {
      submit(msg).then(sendResponse).catch((e) => sendResponse({ clicked: false, error: String(e?.message || e) }));
      return true;
    }
    if (action === "fieldReviewMark") {
      watchRules = msg;
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
