// Bổ sung ô còn trống trên tờ khai Form.io của cổng Bộ Xây dựng (dvc.moc.gov.vn) và cổng Bộ Y tế cùng nền iGate
// (dichvucongbyt.moh.gov.vn): form người nộp + eForm thủ tục, ô name="data[...]", select Choices.js, ngày flatpickr,
// radio, bảng datagrid data[grid][N][cột]. Cùng giao thức
// fieldReviewMark / fieldReviewNext / fieldReviewStop với content/field-review.js nên sidebar và BE (chat/field_review)
// dùng chung; file này chỉ khác cách đọc / ghi ô:
//   - ô bắt buộc = Form.io gắn class "required" cho component (Bộ Y tế: nhãn label.field-required), hoặc component đang
//     báo lỗi sau khi bấm Tiếp tục (has-error / formio-error-wrapper / is-invalid), hoặc tên BE khai (registry REQUIRED);
//   - chỉ ô đang hiện (khối của loại hình công trình đang chọn; khối ẩn formio-hidden không vẽ ô con), ô khoá không hỏi,
//     ô tích không hỏi;
//   - ô trùng tên (tỉnh / xã của người nộp và của công trình) phân biệt bằng thứ tự xuất hiện (occurrence);
//   - điền câu trả lời bằng chính engine Form.io của extension (H.fillFormStandard) cho đúng một ô;
//   - con trỏ + khung gợi ý dùng chung H.fieldReviewPointer của content/field-review.js.
(() => {
  if (window.__TLND_FIELD_REVIEW_FORMIO__) return;
  window.__TLND_FIELD_REVIEW_FORMIO__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOSTS = ["dvc.moc.gov.vn", "dichvucongbyt.moh.gov.vn", "dichvucongbnv.moha.gov.vn", "dvc.moet.gov.vn"];
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-formio-field-review-style";
  const CONTROL = 'input[name^="data["], select[name^="data["], textarea[name^="data["]';
  const SKIP_TYPES = /formio-component-(checkbox|selectboxes|button|hidden|file|signature|survey)\b/;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const ourPage = () => HOSTS.includes(location.hostname) && !!document.querySelector(".formio-component " + CONTROL);

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

  const kindOf = (comp) => {
    const cls = comp.className || "";
    if (/formio-component-select\b/.test(cls)) return "select";
    if (/formio-component-datetime\b/.test(cls)) return "date";
    if (/formio-component-radio\b/.test(cls)) return "radio";
    if (/formio-component-number\b/.test(cls)) return "number";
    return "text";
  };

  // data[a][0][b] → "b"; radio data[key][hậu-tố-ngẫu-nhiên] → "key".
  function keyOf(name, kind) {
    const parts = String(name || "").match(/\[([^\]]+)\]/g)?.map((p) => p.slice(1, -1)) || [];
    if (kind === "radio" && parts.length > 1 && /-/.test(parts[parts.length - 1])) parts.pop();
    return parts.filter((p) => !/^\d+$/.test(p)).pop() || "";
  }

  // Tên điền cho engine: radio bỏ hậu tố ngẫu nhiên (engine khớp theo tiền tố), còn lại giữ nguyên.
  function fillName(name, kind) {
    if (kind !== "radio") return name;
    return String(name).replace(/\[[^\]]*-[^\]]*\]$/, "");
  }

  // Nhãn ô số có chữ ẩn cho trình đọc màn hình (span.sr-only ", numeric only,"); đơn vị ("tháng", "m²") nằm ở
  // input-group cạnh ô, không nằm trong nhãn → nối vào cuối nhãn để công dân biết đơn vị khi được hỏi.
  function labelOf(comp, control) {
    const own = comp.querySelector(":scope > label, :scope > .col-form-label, :scope label.col-form-label");
    const copy = own?.cloneNode(true);
    copy?.querySelectorAll(".sr-only").forEach((el) => el.remove());
    const unit = cleanLabel(textOf(comp.querySelector(".input-group-append, .input-group-prepend")));
    const text = cleanLabel(textOf(copy));
    if (text) return unit ? `${text} (${unit})` : text;
    // Ô trong bảng datagrid: nhãn nằm ở dòng tiêu đề của bảng, theo đúng cột.
    const cell = comp.closest("td");
    const table = cell?.closest("table");
    if (cell && table) {
      const index = Array.from(cell.parentElement.children).indexOf(cell);
      const head = table.querySelectorAll("thead th")[index];
      if (textOf(head)) return cleanLabel(textOf(head));
    }
    return cleanLabel(control.getAttribute("placeholder") || "");
  }

  function sectionOf(comp) {
    const panel = comp.closest(".formio-component-panel, .formio-component-fieldset");
    const title = panel?.querySelector(".card-title, .panel-title, .card-header, legend");
    return cleanLabel(textOf(title));
  }

  const hasError = (comp) => comp.classList.contains("has-error") || comp.classList.contains("formio-error-wrapper")
    || !!comp.querySelector(".is-invalid") || Array.from(comp.querySelectorAll(".formio-errors .error, .invalid-feedback"))
      .some((el) => shown(el) && textOf(el));

  function valueReader(comp, control, kind) {
    if (kind === "radio") {
      return () => {
        const checked = comp.querySelector('input[type="radio"]:checked');
        return checked ? (cleanLabel(textOf(checked.closest("label"))) || checked.value) : "";
      };
    }
    if (kind === "select") {
      return () => {
        // Choices.js trống vẫn giữ <option> ẩn mang đúng chữ gợi ý ("Chọn giới tính") làm value → không đọc <select>
        // khi ô hiển thị đang là chữ gợi ý (choices__placeholder). Chữ của mục đã chọn (có khi bọc trong thẻ con) bỏ
        // nút xoá "Remove item".
        const single = comp.querySelector(".choices__list--single");
        if (single) {
          const picked = single.querySelector(".choices__item:not(.choices__placeholder)");
          if (!picked) return "";
          const copy = picked.cloneNode(true);
          copy.querySelectorAll("button").forEach((b) => b.remove());
          return cleanLabel(textOf(copy) || picked.getAttribute("data-value") || "");
        }
        const sel = comp.querySelector("select");
        return sel && sel.value ? cleanLabel(sel.selectedOptions?.[0]?.textContent || sel.value) : "";
      };
    }
    if (kind === "date") {
      return () => {
        const visible = Array.from(comp.querySelectorAll("input")).find((i) => i.type !== "hidden" && shown(i));
        return String((visible || control).value || "").trim();
      };
    }
    return () => String(control.value || "").trim();
  }

  function optionsOf(comp, kind) {
    if (kind === "radio") {
      return Array.from(comp.querySelectorAll('input[type="radio"]'))
        .map((r) => cleanLabel(textOf(r.closest("label"))) || r.value).filter(Boolean);
    }
    if (kind !== "select") return [];
    // Choices.js chưa có lựa chọn (ô xã chờ chọn tỉnh) vẫn vẽ một dòng "No choices to choose from" (has-no-choices).
    const items = Array.from(comp.querySelectorAll(".choices__list--dropdown .choices__item--choice"))
      .filter((el) => !["choices__placeholder", "has-no-results", "has-no-choices"].some((c) => el.classList.contains(c)))
      .map((el) => cleanLabel(textOf(el))).filter(Boolean);
    // <select> ẩn của Choices.js chỉ giữ mục đang chọn — khi trống là đúng chữ gợi ý ("Chọn Phường/Xã"), nhãn có khi
    // còn nguyên thẻ "<span>…</span>" dạng chữ.
    const select = comp.querySelector("select");
    const hints = new Set([select?.getAttribute("placeholder"), select?.getAttribute("aria-label")].map(cleanLabel));
    const fromSelect = Array.from(comp.querySelectorAll("select option"))
      .map((o) => cleanLabel(String(o.textContent || "").replace(/<[^>]*>/g, "")))
      .filter((label) => label && !hints.has(label));
    return [...new Set(items.length ? items : fromSelect)].slice(0, 400);
  }

  // Ô chọn lazyLoad của Form.io (ô Phường/Xã cổng Bộ GD&ĐT) chỉ tải danh sách khi Choices.js mở dropdown → mở một nhịp
  // để cổng tải rồi đóng lại, sau đó mới đọc lựa chọn.
  async function loadLazyOptions(slot) {
    const box = slot.comp.querySelector(".choices");
    if (!box || box.classList.contains("is-disabled")) return;
    const trigger = box.querySelector(".choices__inner, .form-control") || box;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    for (let waited = 0; waited < 2000 && !slot.options().length; waited += 150) await sleep(150);
    const input = box.querySelector("input.choices__input--cloned");
    input?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
    input?.blur();
    if (box.classList.contains("is-open")) document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  }

  // Mọi ô ĐANG HIỆN, sửa được, theo thứ tự trên trang.
  function slots(noAsk) {
    const skip = new Set(noAsk || []);
    const seen = new Set();
    const counts = new Map();
    const out = [];
    for (const control of document.querySelectorAll(CONTROL)) {
      const comp = control.closest(".formio-component");
      if (!comp || seen.has(comp)) continue;
      seen.add(comp);
      if (SKIP_TYPES.test(comp.className) || comp.closest(".formio-hidden") || !shown(comp)) continue;
      const kind = kindOf(comp);
      const name = fillName(control.getAttribute("name"), kind);
      const occurrence = counts.get(name) || 0;
      counts.set(name, occurrence + 1);
      const key = keyOf(control.getAttribute("name"), kind);
      if (!key || skip.has(key)) continue;
      const input = kind === "select" ? null : control;
      // Ô ngày flatpickr để readonly nhưng vẫn chọn được → chỉ coi khoá khi disabled.
      if (input && (input.disabled || (kind !== "date" && input.readOnly))) continue;
      if (kind === "select" && comp.querySelector(".choices.is-disabled, select[disabled]")) continue;
      const box = kind === "select" ? (comp.querySelector(".choices") || comp)
        : kind === "radio" ? comp : (Array.from(comp.querySelectorAll("input, textarea")).find((i) => i.type !== "hidden"
          && shown(i)) || control);
      out.push({
        key: occurrence ? `${name}#${occurrence}` : name, name: key, fillName: name, occurrence, kind, comp, box,
        label: labelOf(comp, control), section: sectionOf(comp),
        // Cổng Bộ Y tế không gắn class "required" cho component mà đánh dấu nhãn (label.field-required, dấu * đỏ).
        marker: comp.classList.contains("required") || !!comp.querySelector(":scope > label.field-required")
          || hasError(comp),
        value: valueReader(comp, control, kind), options: () => optionsOf(comp, kind),
      });
    }
    // Chỉ tên xuất hiện NHIỀU lần mới cần occurrence khi điền.
    for (const slot of out) slot.duplicate = (counts.get(slot.fillName) || 0) > 1;
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

  // ── Điền một ô bằng engine Form.io ──

  const COMP_BY_KIND = { text: "dom-input", number: "dom-input", select: "dom-select", date: "dom-date", radio: "dom-radio" };

  async function applyValue(slot, value) {
    if (typeof H.fillFormStandard !== "function") return false;
    const field = { name: slot.fillName, comp: COMP_BY_KIND[slot.kind], value };
    if (slot.duplicate) field.occurrence = slot.occurrence;
    try {
      await H.fillFormStandard([field]);
    } catch (e) {
      console.warn("[TLND] bổ sung ô lỗi:", e);
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

  async function next(msg) {
    const skip = new Set(Array.isArray(msg.skip) ? msg.skip : []);
    let applied = null;
    if (msg.apply && msg.apply.key) {
      const target = slots(msg.noAsk).find((s) => s.key === msg.apply.key);
      const ok = target ? await applyValue(target, String(msg.apply.value ?? "")) : false;
      applied = { key: msg.apply.key, ok };
      // Điền không được thì không hỏi lại ô đó ngay ở lượt này (BE cũng ghi vào danh sách bỏ qua).
      if (!ok) skip.add(msg.apply.key);
      await sleep(400); // khối ô của lựa chọn vừa chọn (loại hình công trình, Tổ chức / Cá nhân) vẽ sau một nhịp
    }
    const { list, stats } = markAll(msg);
    // focus: công dân xin sửa một ô đã hỏi → về đúng ô đó dù đã có giá trị; không thì ô trống kế tiếp.
    // requiredFirst: hỏi hết ô bắt buộc trống trước rồi mới tới ô không bắt buộc.
    // Ô chọn chưa có lựa chọn: thử mở cho cổng tải (lazyLoad); vẫn trống (danh sách xã chờ chọn tỉnh) thì chưa hỏi được
    // → hỏi ô khác trước, lượt sau quét lại.
    const askable = async (s) => {
      if (s.value() || skip.has(s.key)) return false;
      if (s.kind !== "select" || s.options().length) return true;
      await loadLazyOptions(s);
      return s.options().length > 0;
    };
    const firstAskable = async (requiredOnly) => {
      for (const s of list) if ((!requiredOnly || s.required) && await askable(s)) return s;
      return null;
    };
    const slot = (msg.focus && list.find((s) => s.key === msg.focus || s.name === msg.focus))
      || (msg.requiredFirst && await firstAskable(true))
      || await firstAskable(false);
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats }; }
    await focusSlot(slot);
    return { ok: true, applied, field: publicField(slot), stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // Chỉ tờ khai Form.io của cổng Bộ Xây dựng trả lời; eForm / SurveyJS / liên thông có bộ đọc riêng.
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
