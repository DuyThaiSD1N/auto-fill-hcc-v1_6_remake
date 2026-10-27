// Bổ sung ô còn trống trên tờ khai cổng liên thông (lienthong.dichvucong.gov.vn, Angular Material: app-input
// [formcontrolname] bọc mat-form-field / mat-select / ng-select / ô ngày / khối địa chỉ). Cùng giao thức
// fieldReviewMark / fieldReviewNext / fieldReviewStop với content/field-review.js (eForm) nên sidebar và BE
// (chat/field_review) dùng chung; file này chỉ khác cách đọc / ghi ô:
//   - ô bắt buộc = dấu * của mat-form-field, class "required" của ng-select (vài ô chọn không hiện *), ô cổng tô vàng
//     báo lỗi sau khi bấm "Chuyển bước tiếp theo" (.text-danger / mat-form-field-invalid / ng-select.is-invalid),
//     hoặc tên BE khai (registry REQUIRED);
//   - ô khoá (người yêu cầu đổ từ VNeID, ô "Ghi bằng chữ" tự sinh) không tô, không hỏi; ô tích không hỏi;
//   - khối địa chỉ tách từng ô con (Tỉnh / Xã / Chi tiết), hỏi kèm tên khối;
//   - điền câu trả lời bằng chính engine fill-angular (H.fillFormAngular) cho đúng một ô;
//   - con trỏ + khung gợi ý dùng chung H.fieldReviewPointer của content/field-review.js.
(() => {
  if (window.__TLND_FIELD_REVIEW_NG__) return;
  window.__TLND_FIELD_REVIEW_NG__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "lienthong.dichvucong.gov.vn";
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-ng-field-review-style";
  const REQUIRED_MARK = ".mat-form-field-required-marker, .mat-placeholder-required, ng-select.required, "
    + "mat-select.required, [required]";
  // Lỗi cổng hiện sau khi bấm chuyển bước: div.text-danger "Trường không được để trống" + nền vàng. Cổng còn dùng
  // .text-danger cho ghi chú tĩnh (vd quy định người đăng ký cư trú cho trẻ) → chỉ tin chữ báo lỗi.
  const ERROR_TEXT = /khong duoc de trong|bat buoc|khong hop le|vui long/;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d").replace(/\s+/g, " ").trim().toLowerCase();
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s+/g, " ").trim();
  const ourPage = () => location.hostname === HOST && H.detectFormKind?.() === "angular"
    && !!document.querySelector("app-input[formcontrolname]");

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

  // Tên khối ("Thông tin người mẹ đẻ…", "Nơi sinh"…) = tiêu đề div.title gần nhất phía trên ô.
  function titles() {
    return Array.from(document.querySelectorAll("div.title, .title"))
      .filter((el) => shown(el) && textOf(el) && textOf(el).length <= 160);
  }

  function sectionOf(box, list) {
    let found = "";
    for (const t of list) {
      if (t.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING) found = textOf(t);
      else break;
    }
    return found;
  }

  const visibleInputs = (scope) => Array.from(scope.querySelectorAll("input"))
    .filter((i) => i.type !== "hidden" && i.type !== "checkbox" && i.type !== "radio" && i.style.display !== "none");

  function labelOf(host, input) {
    return cleanLabel(textOf(host.querySelector("mat-label")) || textOf(host.querySelector("label"))
      || textOf(host.querySelector(".ng-placeholder")) || host.querySelector("ng-select")?.getAttribute("placeholder")
      || input?.getAttribute("data-placeholder") || input?.getAttribute("placeholder"));
  }

  const hasError = (scope) => !!scope.querySelector(".mat-form-field-invalid, ng-select.is-invalid")
    || scope.matches?.(".mat-form-field-invalid") === true
    || Array.from(scope.querySelectorAll(".text-danger")).some((el) => shown(el) && ERROR_TEXT.test(fold(textOf(el))));

  function locked(host, input) {
    return !!(input?.disabled || input?.readOnly || host.hasAttribute("disabled")
      || host.querySelector(".mat-select-disabled, .ng-select-disabled, .mat-form-field-disabled"));
  }

  function selectSlot(host, name, section) {
    const ng = host.querySelector("ng-select");
    const ms = host.querySelector("mat-select");
    const box = ng || host.querySelector("mat-form-field") || ms;
    if (!box || !shown(box) || locked(host, ng ? null : visibleInputs(host)[0])) return null;
    const read = () => textOf(host.querySelector(".ng-value-label, .ng-value, .mat-select-value-text"));
    return {
      key: name, name, comp: "select", kind: "select", label: labelOf(host), section, box, host, ng, ms,
      marker: !!host.querySelector(REQUIRED_MARK) || hasError(host), value: read,
    };
  }

  function inputSlot(host, name, section, type) {
    // Ô ngày có thêm ô của datepicker: ô gõ được là ô maxlength 10 (như fill-angular fillNgDate).
    const inputs = visibleInputs(host).filter((i) => !i.closest("mat-select"));
    const input = inputs.find((i) => i.getAttribute("maxlength") === "10") || inputs[0] || null;
    const box = input?.closest("mat-form-field") || input;
    if (!input || !shown(box) || locked(host, input)) return null;
    const date = type === "date" || type === "ngaysinh";
    return {
      key: name, name, comp: type === "ngaysinh" ? "ngaysinh" : date ? "date" : type === "number" ? "raw" : "text",
      kind: date ? "date" : "text", partialDate: type === "ngaysinh", label: labelOf(host, input), section, box,
      host, marker: !!host.querySelector(REQUIRED_MARK) || hasError(host),
      value: () => String(input.value || "").trim(),
    };
  }

  function radioSlot(host, name, section) {
    const buttons = Array.from(host.querySelectorAll("mat-radio-button"));
    if (!buttons.length || !shown(host)) return null;
    const label = (b) => textOf(b.querySelector(".mat-radio-label-content") || b);
    return {
      key: name, name, comp: "radio", kind: "radio", label: labelOf(host) || "", section, box: host, host,
      options: buttons.map(label).filter(Boolean), marker: !!host.querySelector(REQUIRED_MARK),
      value: () => label(buttons.find((b) => b.classList.contains("mat-radio-checked")) || null),
    };
  }

  function areaRole(label) {
    const t = fold(label);
    if (/\btinh\b|thanh pho/.test(t)) return "tinh";
    if (/\bxa\b|phuong/.test(t)) return "xa";
    return "diaChi";
  }

  function areaSlots(host, name, section) {
    const out = [];
    for (const ff of host.querySelectorAll("mat-form-field")) {
      const input = visibleInputs(ff)[0];
      if (!input || !shown(ff) || input.disabled || input.readOnly) continue;
      const label = cleanLabel(textOf(ff.querySelector("mat-label"))) || input.getAttribute("placeholder") || "";
      const role = areaRole(label);
      out.push({
        key: `${name}#${role}`, name, comp: "diachi", kind: "text", role, label: label || "Địa chỉ", group: section,
        section, box: ff, host, marker: !!ff.querySelector(REQUIRED_MARK) || ff.classList.contains("mat-form-field-invalid"),
        value: () => String(input.value || "").trim(),
      });
    }
    return out;
  }

  // Ô số lượng bản sao: input mang formcontrolname riêng nằm trong khối radio "Đề nghị cấp bản sao".
  function nestedInputSlot(input, name, section) {
    const box = input.closest("mat-form-field") || input;
    if (!shown(box) || input.disabled || input.readOnly) return null;
    return {
      key: name, name, comp: "raw", kind: "text", label: cleanLabel(textOf(box.querySelector?.("mat-label")))
        || input.getAttribute("data-placeholder") || input.getAttribute("placeholder") || name,
      section, box, host: input,
      marker: input.required || !!box.querySelector?.(REQUIRED_MARK) || hasError(box),
      value: () => String(input.value || "").trim(),
    };
  }

  // Mọi ô ĐANG HIỆN và sửa được, theo thứ tự trên trang.
  function slots(noAsk) {
    const skip = new Set(noAsk || []);
    const heads = titles();
    const out = [];
    for (const host of document.querySelectorAll("app-input[formcontrolname], input[formcontrolname]")) {
      const name = host.getAttribute("formcontrolname");
      if (!name || skip.has(name) || name === "hours" || name === "minutes") continue;
      if (host.tagName === "INPUT") {
        const owner = host.closest("app-input[formcontrolname]");
        if (!owner || owner.getAttribute("formcontrolname") === name) continue;
      }
      const type = host.tagName === "INPUT" ? "number" : String(host.getAttribute("type") || "text").toLowerCase();
      if (type === "checkbox") continue;
      const section = sectionOf(host, heads);
      let found;
      if (host.tagName === "INPUT") found = [nestedInputSlot(host, name, section)];
      else if (type === "diachi") found = areaSlots(host, name, section);
      else if (type === "radio" || host.querySelector(":scope mat-radio-group")) found = [radioSlot(host, name, section)];
      else if (type === "select") found = [selectSlot(host, name, section)];
      else found = [inputSlot(host, name, section, type)];
      for (const slot of found) if (slot) out.push(slot);
    }
    return out;
  }

  // ── Tô màu ──

  function clearMarks() {
    document.querySelectorAll(MARKS.map((m) => `.${m}`).join(",")).forEach((el) => el.classList.remove(...MARKS));
  }

  function markAll(msg) {
    injectStyles();
    clearMarks();
    const need = new Set(msg.required || []);
    const stats = { filled: 0, optional: 0, required: 0 };
    const list = slots(msg.noAsk);
    for (const slot of list) {
      slot.required = need.has(slot.name) || slot.marker;
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
  // mat-select / ng-select đổi giá trị bằng cú bấm vào lựa chọn, không bắn input/change trên ô.
  document.addEventListener("click", onFormEdited, true);

  // ── Lựa chọn của ô chọn ──

  const ngOptions = () => Array.from(document.querySelectorAll("ng-dropdown-panel .ng-option, .ng-dropdown-panel .ng-option"));
  const matOptions = () => Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"));
  const usable = (t) => t && !/^(khong co|dang tai)/.test(fold(t));

  async function readOptions(slot) {
    if (slot.kind === "radio") return slot.options || [];
    if (slot.kind !== "select") return [];
    let options = [];
    if (slot.ng) {
      const ctrl = slot.ng.querySelector(".ng-select-container") || slot.ng;
      ctrl.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      for (let waited = 0; waited < 2500 && !ngOptions().length; waited += 150) await sleep(150);
      options = ngOptions().map(textOf).filter(usable);
      slot.ng.querySelector("input")?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      if (ngOptions().length) ctrl.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    } else if (slot.ms) {
      const trigger = slot.ms.querySelector(".mat-select-trigger") || slot.ms;
      trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      trigger.click();
      for (let waited = 0; waited < 2500 && !matOptions().length; waited += 150) await sleep(150);
      options = matOptions().map(textOf).filter(usable);
      document.querySelector(".cdk-overlay-backdrop")?.click();
    }
    await sleep(200);
    // Danh sách quốc gia hơn 200 nước — cắt ngắn là mất các nước vần cuối.
    return [...new Set(options)].slice(0, 400);
  }

  // ── Điền một ô bằng engine fill-angular ──

  // Ô Tỉnh / Xã của khối địa chỉ là mat-autocomplete: gõ rồi chọn đúng lựa chọn. Làm thẳng trên ô đang hỏi vì
  // khối địa chỉ của cha, mẹ, nơi sinh… không có placeholder để engine điền tìm ô theo chữ.
  const autoOptions = () => Array.from(document.querySelectorAll(".mat-autocomplete-panel mat-option, .cdk-overlay-pane mat-option"));
  const bare = (s) => fold(s).replace(/^(tinh|thanh pho|tp\.?|phuong|xa|thi tran|dac khu)\s+/, "").replace(/[‐-―]/g, "-");

  async function pickArea(input, value) {
    const type = async (text) => {
      input.focus();
      H.setNativeValue(input, String(text));
      input.dispatchEvent(new Event("input", { bubbles: true }));
      for (let waited = 0; waited < 2500 && !autoOptions().length; waited += 150) await sleep(150);
    };
    await type(value);
    if (!autoOptions().length) await type(bare(value));
    const want = bare(value);
    const hit = autoOptions().find((o) => bare(textOf(o)) === want) || autoOptions().find((o) => bare(textOf(o)).includes(want));
    if (!hit) return false;
    hit.click();
    await sleep(600);
    return true;
  }

  async function applyArea(slot, value) {
    const input = visibleInputs(slot.box)[0];
    if (!input || typeof H.setNativeValue !== "function") return false;
    if (slot.role === "tinh" || slot.role === "xa") return pickArea(input, value);
    H.setNativeValue(input, String(value));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    return true;
  }

  async function applyValue(slot, value) {
    if (slot.comp !== "diachi" && typeof H.fillFormAngular !== "function") return false;
    try {
      if (slot.comp === "diachi") await applyArea(slot, value);
      else await H.fillFormAngular([{ name: slot.name, comp: slot.comp, value }]);
    } catch (e) {
      console.warn("[TLND] bổ sung ô lỗi:", e);
      return false;
    }
    await sleep(300);
    const fresh = slots(watchRules?.noAsk).find((s) => s.key === slot.key);
    return !!fresh?.value();
  }

  function publicField(slot, options) {
    return {
      key: slot.key, name: slot.name, role: slot.role || "", kind: slot.kind, yearOnly: false,
      partialDate: !!slot.partialDate, label: slot.label, group: slot.group || "", section: slot.section || "",
      required: !!slot.required, options, value: slot.value(),
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

  async function next(msg) {
    const skip = new Set(Array.isArray(msg.skip) ? msg.skip : []);
    let applied = null;
    if (msg.apply && msg.apply.key) {
      const target = slots(msg.noAsk).find((s) => s.key === msg.apply.key);
      const ok = target ? await applyValue(target, String(msg.apply.value ?? "")) : false;
      applied = { key: msg.apply.key, ok };
      // Điền không được thì không hỏi lại ô đó ngay ở lượt này (BE cũng ghi vào danh sách bỏ qua).
      if (!ok) skip.add(msg.apply.key);
      await sleep(350); // ô phụ thuộc (số lượng bản sao, xã theo tỉnh) hiện ra sau một nhịp vẽ của Angular
    }
    const { list, stats } = markAll(msg);
    // focus: công dân xin sửa một ô đã hỏi → về đúng ô đó dù đã có giá trị; không thì ô trống kế tiếp.
    // requiredFirst: hỏi hết ô bắt buộc trống trước rồi mới tới ô không bắt buộc.
    const slot = (msg.focus && list.find((s) => s.key === msg.focus || s.name === msg.focus))
      || (msg.requiredFirst && list.find((s) => !s.value() && s.required && !skip.has(s.key)))
      || list.find((s) => !s.value() && !skip.has(s.key));
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats }; }
    const options = await readOptions(slot);
    await focusSlot(slot);
    return { ok: true, applied, field: publicField(slot, options), stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // Chỉ trang liên thông trả lời; eForm và SurveyJS có bộ đọc riêng.
    if (!ourPage()) return;
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
