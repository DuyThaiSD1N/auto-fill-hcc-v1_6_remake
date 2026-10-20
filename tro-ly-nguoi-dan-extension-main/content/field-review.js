// Bổ sung ô còn trống trên tờ khai eForm cũ (x-input / x-select / x-select-area… trong iframe
// tokhaidientu) sau khi điền. Điều phối và câu thoại ở BE (chat/field_review); file này chỉ:
//   - tô TỪNG ô (không tô cả khối địa chỉ): có giá trị → xanh, trống không bắt buộc → cam, trống
//     bắt buộc → đỏ; đếm số ô mỗi loại;
//   - tìm ô trống kế tiếp từ trên xuống, đưa con trỏ tới ô, viền ô đang hỏi, đọc danh sách lựa chọn;
//   - điền giá trị công dân trả lời bằng chính engine fill-legacy (H.fillForm) cho đúng một ô.
// Ô bắt buộc = tên BE khai (registry fieldReview.required) HOẶC chấm đỏ "Trường này không được bỏ
// trống" (.validate-hiden) cổng chèn cạnh ô — chấm này chỉ có sau khi bấm "Xem trước".
(() => {
  if (window.__TLND_FIELD_REVIEW__) return;
  window.__TLND_FIELD_REVIEW__ = true;
  const H = window.__TLND__ || {};

  const SLOT_SELECTOR = [
    "x-input[name]", "x-input-number[name]", "x-select[name]", "x-select-default[name]",
    "x-date[name]", "x-date-text[name]", "x-radio[name]", "x-select-area[name]",
  ].join(",");
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", "tlnd-fr-optional"];
  const ASKING = "tlnd-fr-asking";
  const STYLE_ID = "tlnd-field-review-style";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d").replace(/Đ/g, "D").replace(/\s+/g, " ").trim().toLowerCase();
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const isPlaceholder = (text) => {
    const t = fold(text).replace(/[▲▼▾▿]/g, "").trim();
    return !t || /^-+\s*chon\s*-+$/.test(t) || t === "vui long chon du lieu";
  };
  const visible = (el) => !!el && el.getClientRects().length > 0;

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    if (typeof H.injectAutofillStyles === "function") H.injectAutofillStyles();
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .tlnd-fr-optional { background-color: #fff3e0 !important; outline: 2px solid #fb8c00 !important;
        outline-offset: 1px !important; border-radius: 3px !important; }
      .${ASKING} { outline: 3px solid #1e66f5 !important; outline-offset: 2px !important;
        box-shadow: 0 0 0 6px rgba(30, 102, 245, .22) !important; border-radius: 4px !important; }
      #tlnd-fr-cursor { position: fixed; left: 0; top: 0; z-index: 2147483646; pointer-events: none;
        width: 26px; height: 26px; opacity: 0; transition: transform .6s ease, opacity .2s; }
      #tlnd-fr-cursor.show { opacity: 1; }
      #tlnd-fr-cursor::after { content: ""; position: absolute; left: -9px; top: -9px; width: 18px; height: 18px;
        border-radius: 50%; border: 2px solid #1e66f5; opacity: 0; }
      #tlnd-fr-cursor.click::after { animation: tlnd-fr-ripple .5s ease-out; }
      @keyframes tlnd-fr-ripple { from { opacity: .9; transform: scale(.4); } to { opacity: 0; transform: scale(1.6); } }
      #tlnd-fr-hint { position: fixed; z-index: 2147483645; max-width: 360px; padding: 6px 10px;
        background: #1e66f5; color: #fff; font: 600 13px/1.4 system-ui, sans-serif; border-radius: 6px;
        box-shadow: 0 4px 14px rgba(0,0,0,.18); pointer-events: none; }
      @media (prefers-reduced-motion: reduce) { #tlnd-fr-cursor { transition: none; } }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  // ── Đọc ô ──

  // Nhãn đứng ngay trước một ô trong cùng đoạn: gom chữ của các nút anh em phía trước, dừng ở ô x-*
  // trước đó (nhiều ô chung một <p>: "(8) Giới tính: <x-select> (9) Dân tộc: <x-select>").
  function labelBefore(node) {
    let text = "";
    for (let n = node.previousSibling; n; n = n.previousSibling) {
      if (n.nodeType === Node.ELEMENT_NODE) {
        if (/^X-/.test(n.tagName) || n.querySelector?.("[name]")) break;
        if (n.classList?.contains("input-hidden") || n.classList?.contains("hidden")) continue;
      }
      text = `${n.textContent || ""} ${text}`;
    }
    return text.replace(/\s+/g, " ").trim();
  }

  // Nhãn của ô con trong khối địa chỉ: <label>/<span> chữ gần nhất phía trước (bỏ span giá trị ẩn).
  function areaLabel(node) {
    for (let n = node.previousElementSibling; n; n = n.previousElementSibling) {
      if (n.classList.contains("input-hidden") || n.classList.contains("hidden")) continue;
      const t = textOf(n);
      if (t) return t;
    }
    return "";
  }

  function areaRole(label) {
    const t = fold(label);
    if (/\btinh\b|thanh pho/.test(t)) return "tinh";
    if (/\bxa\b|phuong/.test(t)) return "xa";
    return "quocGia";
  }

  const markerAfter = (el) => !!el?.nextElementSibling?.classList?.contains("validate-hiden");

  function selectHeader(widget) {
    return widget?.querySelector(".input-field-select") || widget?.querySelector("div[tabindex]") || null;
  }

  function selectValue(header) {
    const t = textOf(header?.querySelector("span") || header);
    return isPlaceholder(t) ? "" : t;
  }

  function dateParts(container) {
    const pick = (suffix) => [...container.querySelectorAll("input")]
      .find((i) => String(i.id || i.name || "").endsWith(suffix));
    return [pick("-day"), pick("-month"), pick("-year")];
  }

  function areaSlots(area, name) {
    const out = [];
    const widgets = [...area.querySelectorAll('[id^="custom-select-"]')];
    if (!widgets.length) {
      // Khối x-select-area KHÔNG có dropdown là một ô chữ trơn đi kèm ô khác ("Số lượng: [ ] bản" sau "Đề nghị
      // cấp bản sao", "Quan hệ khác"…) — không phải ô Địa chỉ của khối địa chỉ.
      const input = area.querySelector("input.input-field, input:not([type]), input[type='text'], input[type='number']");
      if (!input || input.disabled || input.readOnly) return out;
      out.push({
        key: name, name, comp: "x-select-area", role: "", kind: "text", plain: true,
        label: labelBefore(input) || labelBefore(input.parentElement) || labelBefore(area),
        box: visible(input) ? input : (input.parentElement || input), area,
        value: () => String(input.value || "").trim(), marker: markerAfter(input),
      });
      return out;
    }
    const group = widgets.length ? areaLabel(widgets[0]) : "";
    for (const widget of widgets) {
      const label = areaLabel(widget);
      const role = areaRole(label);
      const header = selectHeader(widget);
      out.push({
        key: `${name}#${role}`, name, comp: "x-select-area", role, kind: "select", label, group,
        box: header || widget, widget, header, area,
        value: () => selectValue(header), marker: markerAfter(widget),
      });
    }
    const addr = area.querySelector("input.input-field");
    if (addr) {
      out.push({
        key: `${name}#diaChi`, name, comp: "x-select-area", role: "diaChi", kind: "text",
        label: areaLabel(addr) || "Địa chỉ", group, box: visible(addr) ? addr : (addr.parentElement || addr), area,
        value: () => String(addr.value || "").trim(),
        marker: markerAfter(addr) || !!addr.parentElement?.querySelector(":scope > .validate-hiden"),
      });
    }
    return out;
  }

  function simpleSlot(c, name, tag) {
    const base = { key: name, name, comp: tag, label: labelBefore(c),
      marker: !!c.querySelector(".validate-hiden") };
    if (tag === "x-input" || tag === "x-input-number") {
      const input = c.querySelector("input");
      if (!input || input.disabled || input.readOnly) return null;
      return { ...base, kind: "text", box: input.parentElement || c, value: () => String(input.value || "").trim() };
    }
    if (tag === "x-select" || tag === "x-select-default") {
      const widget = c.querySelector('[id^="custom-select-"]');
      const header = selectHeader(widget);
      if (!header) return null;
      return { ...base, kind: "select", box: header, widget, header, value: () => selectValue(header) };
    }
    if (tag === "x-date" || tag === "x-date-text") {
      const parts = dateParts(c);
      if (!parts.some(Boolean)) return null;
      // Ô ngày dạng chữ của tờ khai tư pháp (năm sinh cha/mẹ) nhận riêng năm: có năm là đã điền, và
      // engine điền được giá trị chỉ có năm. Ô x-date thì cổng cần đủ ngày-tháng-năm.
      const yearOnly = tag === "x-date-text";
      const read = (p) => String(p?.value || "").trim();
      return {
        ...base, kind: "date", yearOnly, box: parts.find(Boolean).parentElement || c,
        value: () => {
          if (parts.every((p) => p && read(p))) return parts.map(read).join("/");
          return yearOnly ? read(parts[2]) : "";
        },
      };
    }
    if (tag === "x-radio") {
      const boxes = [...c.querySelectorAll('input[type="checkbox"]')];
      if (!boxes.length) return null;
      const labelOf = (box) => textOf(c.querySelector(`label[for="${CSS.escape(box.id)}"]`)) || box.value || "";
      return {
        ...base, kind: "radio", box: c.querySelector("span") || c,
        options: boxes.map(labelOf).filter(Boolean),
        value: () => labelOf(boxes.find((b) => b.checked) || {}) || "",
      };
    }
    return null;
  }

  function headings() {
    return [...document.querySelectorAll("strong, b")].filter((el) => /^[IVXLC]+\s*[.)]/.test(textOf(el)));
  }

  function sectionOf(box, list) {
    let found = "";
    for (const h of list) {
      if (h.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING) found = textOf(h);
      else break;
    }
    return found;
  }

  // Mọi ô ĐANG HIỆN theo thứ tự trên tờ khai. Khối địa chỉ đang ẩn (vd "Nước ngoài" khi chọn "Trong
  // nước") không còn ô con nào → tự rơi khỏi danh sách.
  function slots() {
    const out = [];
    let lastLabel = "";
    for (const c of document.querySelectorAll(SLOT_SELECTOR)) {
      const name = c.getAttribute("name");
      const tag = c.tagName.toLowerCase();
      if (tag !== "x-select-area" && c.parentElement?.closest("x-select-area")) continue;
      const found = tag === "x-select-area" ? areaSlots(c, name) : [simpleSlot(c, name, tag)];
      for (const slot of found) {
        if (!slot || !visible(slot.box)) continue;
        // Nhãn cụt ("số:", ": số", rỗng) đi sau một ô khác cùng dòng → ghép nhãn ô trước cho rõ nghĩa.
        const clean = slot.label.replace(/^\(\s*\d+\s*\)\s*/, "").replace(/^[:\s–-]+|[:\s–-]+$/g, "");
        if (clean.length < 5 && lastLabel) slot.label = clean ? `${lastLabel} – ${clean}` : lastLabel;
        if (slot.role !== "diaChi" && slot.role !== "tinh" && slot.role !== "xa") {
          lastLabel = slot.label.replace(/^\(\s*\d+\s*\)\s*/, "").replace(/^[:\s–-]+|[:\s–-]+$/g, "");
        }
        out.push(slot);
      }
    }
    return out;
  }

  // ── Tô màu ──

  function clearMarks() {
    document.querySelectorAll(MARKS.map((m) => `.${m}`).join(",")).forEach((el) => el.classList.remove(...MARKS));
  }

  function markAll(required) {
    injectStyles();
    clearMarks();
    const need = new Set(required || []);
    const stats = { filled: 0, optional: 0, required: 0 };
    const list = slots();
    for (const slot of list) {
      slot.required = need.has(slot.name) || slot.marker;
      if (slot.value()) { slot.box.classList.add("autofill-filled"); stats.filled += 1; }
      else if (slot.required) { slot.box.classList.add("autofill-not-filled"); stats.required += 1; }
      else { slot.box.classList.add("tlnd-fr-optional"); stats.optional += 1; }
    }
    lastStatsKey = JSON.stringify(stats);
    return { list, stats };
  }

  // Sau lượt tô đầu tiên (fieldReviewMark), theo dõi tờ khai: công dân gõ / chọn thẳng trên trang thì ~1 giây sau tô
  // lại màu, đếm lại và báo sidebar khi số ô đổi (sidebar chuyển BE: __event:field_review_status → hiện nút Xem trước
  // to khi ô bắt buộc về 0). Trợ lý tự điền trong vòng hỏi cũng đếm lại ở next() nên không báo trùng.
  const WATCH_DEBOUNCE_MS = 1000;
  let watchRequired = null;
  let watchTimer = null;
  let lastStatsKey = "";
  function onFormEdited() {
    if (!watchRequired || !document.querySelector(SLOT_SELECTOR)) return;
    clearTimeout(watchTimer);
    watchTimer = setTimeout(() => {
      const before = lastStatsKey;
      const { stats } = markAll(watchRequired);
      if (lastStatsKey === before) return;
      try {
        chrome.runtime.sendMessage({ __tlnd: "fieldReviewStats", stats }, () => void chrome.runtime.lastError);
      } catch (_) { /* extension vừa reload: bỏ lượt báo này */ }
    }, WATCH_DEBOUNCE_MS);
  }
  document.addEventListener("input", onFormEdited, true);
  document.addEventListener("change", onFormEdited, true);

  // ── Con trỏ + ô đang hỏi ──

  let hintTarget = null;
  function placeHint() {
    const hint = document.getElementById("tlnd-fr-hint");
    if (!hint || !hintTarget) return;
    const r = hintTarget.getBoundingClientRect();
    hint.style.left = `${Math.max(8, Math.min(r.left, innerWidth - 370))}px`;
    hint.style.top = `${Math.min(r.bottom + 8, innerHeight - 40)}px`;
  }
  addEventListener("scroll", placeHint, true);
  addEventListener("resize", placeHint);

  function cursorEl() {
    let cur = document.getElementById("tlnd-fr-cursor");
    if (!cur) {
      cur = document.createElement("div");
      cur.id = "tlnd-fr-cursor";
      cur.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2l15 9-6.5 1.8L9.5 20z" '
        + 'fill="#fff" stroke="#1b2130" stroke-width="1.6" stroke-linejoin="round"/></svg>';
      cur.style.transform = `translate(${Math.round(innerWidth / 2)}px, 40px)`;
      document.body.appendChild(cur);
    }
    return cur;
  }

  function unfocus() {
    document.querySelectorAll(`.${ASKING}`).forEach((el) => el.classList.remove(ASKING));
    document.getElementById("tlnd-fr-hint")?.remove();
    document.getElementById("tlnd-fr-cursor")?.classList.remove("show", "click");
    hintTarget = null;
  }

  const ASK_HINT = "Trợ lý đang hỏi ô này · công dân nói vào mic hoặc gõ ở khung trợ lý";

  function focusSlot(slot, hintText = ASK_HINT) {
    return focusBox(slot.box, hintText);
  }

  async function focusBox(box, hintText = ASK_HINT) {
    injectStyles();
    unfocus();
    box.scrollIntoView({ block: "center", behavior: "smooth" });
    await sleep(450);
    const cur = cursorEl();
    const r = box.getBoundingClientRect();
    cur.classList.add("show");
    cur.style.transform = `translate(${Math.round(r.left + Math.min(r.width / 2, 120))}px, `
      + `${Math.round(r.top + r.height * 0.55)}px)`;
    await sleep(650);
    cur.classList.remove("click");
    void cur.offsetWidth;
    cur.classList.add("click");
    box.classList.add(ASKING);
    const hint = document.createElement("div");
    hint.id = "tlnd-fr-hint";
    hint.textContent = hintText;
    document.body.appendChild(hint);
    hintTarget = box;
    placeHint();
  }

  // Con trỏ + khung gợi ý dùng chung cho form SurveyJS của trang nộp một trang (content/field-review-surveyjs.js).
  H.fieldReviewPointer = { focus: focusBox, unfocus };

  // Danh sách lựa chọn của ô chọn: mở dropdown đọc chữ rồi đóng lại (danh sách Tỉnh/Xã nạp sau khi mở).
  async function readOptions(slot, wait = 2500) {
    if (slot.kind === "radio") return slot.options || [];
    if (slot.kind !== "select" || !slot.header) return [];
    const box = () => slot.widget?.querySelector(".input-field-select-options");
    const texts = () => (box() ? [...box().querySelectorAll("div")] : [])
      .map(textOf).filter((t) => t && !isPlaceholder(t));
    slot.header.click();
    for (let waited = 0; waited < wait && !texts().length; waited += 150) await sleep(150);
    // Danh sách Quốc gia hơn 200 nước — cắt ngắn là mất các nước vần cuối (Thụy Điển, Việt Nam…).
    const options = [...new Set(texts())].slice(0, 400);
    if (box()) slot.header.click();
    return options;
  }

  // ── Danh sách Xã không nạp ──
  // Cổng hay hỏng nạp danh sách Xã sau khi chọn Tỉnh (dropdown Xã rỗng). Chọn lại ĐÚNG tỉnh cũ thì giá trị không
  // đổi nên cổng không nạp lại → đổi sang tỉnh liền kề rồi chọn lại tỉnh cũ (hai lần). Vẫn rỗng thì tick lại ô
  // phạm vi "Trong nước/Khác" cho cổng dựng lại cả khối, rồi điền lại các ô đang có của khối (trừ Xã).

  const RELOAD_HINT = "Cổng chưa tải danh sách xã · trợ lý đang chọn lại tỉnh";

  function areaData(name) {
    const data = {};
    for (const s of slots()) {
      if (s.name === name && s.role && s.role !== "xa" && s.value()) data[s.role] = s.value();
    }
    return data;
  }

  async function fillArea(name, data) {
    try {
      await H.fillForm([{ name, comp: "x-select-area", value: data }]);
    } catch (e) {
      console.warn("[TLND] chọn lại tỉnh lỗi:", e);
    }
  }

  async function tick(box) {
    box.click();
    if (!box.checked) {
      box.checked = true;
      box.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // Ô tích phạm vi đứng trên khối địa chỉ (tìm ngược lên tối đa 5 cấp, bỏ ô tích nằm trong chính khối).
  async function toggleScope(area) {
    let node = area?.parentElement;
    for (let level = 0; node && level < 5; level += 1, node = node.parentElement) {
      for (const group of node.querySelectorAll("x-radio")) {
        if (group.contains(area) || area.contains(group)) continue;
        const boxes = [...group.querySelectorAll('input[type="checkbox"]')];
        const labelOf = (b) => fold(textOf(group.querySelector(`label[for="${CSS.escape(b.id)}"]`)));
        const current = boxes.find((b) => b.checked);
        const other = boxes.find((b) => b !== current);
        if (!current || !other || !boxes.some((b) => labelOf(b).includes("trong nuoc"))) continue;
        await tick(other);
        await sleep(400);
        await tick(current);
        await sleep(600);
        return true;
      }
    }
    return false;
  }

  async function wardOptions(name) {
    const find = (role) => slots().find((s) => s.name === name && s.role === role);
    const keep = areaData(name);
    if (!keep.tinh || typeof H.fillForm !== "function") return [];
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const tinh = find("tinh");
      if (!tinh) break;
      await focusSlot(tinh, RELOAD_HINT);
      if (attempt < 2) {
        const all = await readOptions(tinh);
        const at = all.findIndex((o) => fold(o) === fold(keep.tinh));
        const other = (at >= 0 && (all[at + 1] || all[at - 1])) || all.find((o) => fold(o) !== fold(keep.tinh));
        if (!other) break;
        await fillArea(name, { ...keep, tinh: other });
        await sleep(700);
      } else if (!(await toggleScope(tinh.area))) {
        break;
      }
      await fillArea(name, keep);
      const xa = find("xa");
      const options = xa ? await readOptions(xa, 4000) : [];
      if (options.length) return options;
    }
    // Không chữa được vẫn phải trả khối về đúng tỉnh đang có (lượt chữa có thể dừng ở tỉnh liền kề).
    if (fold(find("tinh")?.value()) !== fold(keep.tinh)) await fillArea(name, keep);
    return [];
  }

  // ── Điền một ô bằng engine fill-legacy ──

  function areaValue(slot, list, value) {
    const data = {};
    for (const s of list) {
      if (s.area !== slot.area || !s.role) continue;
      const v = s.value();
      if (v) data[s.role] = v;
    }
    data[slot.role] = value;
    // Đổi Tỉnh thì Xã cũ không còn thuộc tỉnh mới → bỏ, để công dân được hỏi lại Xã.
    if (slot.role === "tinh") delete data.xa;
    return data;
  }

  async function applyValue(slot, list, value) {
    if (typeof H.fillForm !== "function") return false;
    const field = slot.comp === "x-select-area"
      ? { name: slot.name, comp: "x-select-area", value: slot.plain ? value : areaValue(slot, list, value) }
      : { name: slot.name, comp: slot.comp, value };
    try {
      await H.fillForm([field]);
    } catch (e) {
      console.warn("[TLND] bổ sung ô lỗi:", e);
      return false;
    }
    await sleep(200);
    const fresh = slots().find((s) => s.key === slot.key);
    return !!fresh?.value();
  }

  function publicField(slot, options, section, province = "") {
    return {
      key: slot.key, name: slot.name, role: slot.role || "", kind: slot.kind, yearOnly: !!slot.yearOnly,
      label: slot.label, group: slot.group || "", section, required: !!slot.required, options,
      value: slot.value(),
      // Ô Xã mà Tỉnh đã có nhưng chữa xong cổng vẫn không nạp danh sách xã → BE mời tải lại / bỏ qua.
      ...(province ? { optionsFailed: true, province } : {}),
    };
  }

  async function next(msg) {
    const skip = new Set(Array.isArray(msg.skip) ? msg.skip : []);
    let applied = null;
    if (msg.apply && msg.apply.key) {
      const target = slots().find((s) => s.key === msg.apply.key);
      const ok = target ? await applyValue(target, slots(), String(msg.apply.value ?? "")) : false;
      applied = { key: msg.apply.key, ok };
      // Điền không được thì không hỏi lại ô đó ngay ở lượt này (BE cũng ghi vào danh sách bỏ qua).
      if (!ok) skip.add(msg.apply.key);
    }
    let { list, stats } = markAll(msg.required);
    // focus: công dân xin sửa ô vừa điền → về đúng ô đó dù đã có giá trị; không thì ô trống kế tiếp.
    // requiredFirst (BE luồng bản 2): hỏi hết ô bắt buộc trống trước rồi mới tới ô không bắt buộc.
    let slot = (msg.focus && list.find((s) => s.key === msg.focus))
      || (msg.requiredFirst && list.find((s) => !s.value() && s.required && !skip.has(s.key)))
      || list.find((s) => !s.value() && !skip.has(s.key));
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats }; }
    let options = await readOptions(slot);
    let province = "";
    if (!options.length && slot.role === "xa" && areaData(slot.name).tinh) {
      options = await wardOptions(slot.name);
      // Chọn lại tỉnh / dựng lại khối làm mất viền và có thể thay phần tử → tô lại, lấy lại ô.
      ({ list, stats } = markAll(msg.required));
      slot = list.find((s) => s.key === slot.key) || slot;
      if (!options.length) province = areaData(slot.name).tinh || "";
    }
    await focusSlot(slot);
    return {
      ok: true, applied, field: publicField(slot, options, sectionOf(slot.box, headings()), province), stats,
    };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // all_frames: chỉ frame chứa tờ khai eForm trả lời, frame khác im lặng.
    if (H.detectFormKind?.() !== "legacy" || !document.querySelector(SLOT_SELECTOR)) return;
    if (action === "fieldReviewMark") {
      watchRequired = msg.required || [];
      sendResponse({ ok: true, stats: markAll(msg.required).stats });
      return;
    }
    if (action === "fieldReviewStop") {
      unfocus();
      sendResponse({ ok: true });
      return;
    }
    if (action === "fieldReviewNext") {
      next(msg).then(sendResponse).catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
      return true;
    }
  });
})();
