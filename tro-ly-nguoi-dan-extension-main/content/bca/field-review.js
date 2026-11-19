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
// Cổng DVC Bộ Công an thứ hai (dichvucong.bocongan.gov.vn, eForm Nth: hộ chiếu, mẫu con dấu, thị thực, thẻ tạm trú — cờ
// supportsBcaNthReview, user 19/11/2026) dùng chung bộ đọc này cho tô ô + vòng "Bổ sung các thông tin còn thiếu": ô chọn là
// bootstrap-select (<select> ẩn, nút .dropdown-toggle hiện), chỉ đọc ô của form kê khai (ô CongDan_* hoặc cùng <form>), bỏ
// bảng Thành phần hồ sơ, mã xác nhận, ô chọn ngôn ngữ. Nút đi tiếp ở cổng này là "Đồng ý và tiếp tục" (BE, lệnh lc_next).
(() => {
  if (window.__TLND_FIELD_REVIEW_BCA__) return;
  window.__TLND_FIELD_REVIEW_BCA__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.dancuquocgia.gov.vn";
  const NTH_HOST = "dichvucong.bocongan.gov.vn";
  const NTH_FORM_SEL = 'input[name^="CongDan_"]:not([type="hidden"]):not([type="file"]), textarea[name^="CongDan_"]';
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-bca-field-review-style";
  const SKIP_TYPES = /^(hidden|button|submit|reset|file|image|checkbox|password|search|color|range)$/;
  const LABEL_SEL = "label, .control-label, .col-form-label, .title-input";
  const FOLLOWING = Node.DOCUMENT_POSITION_FOLLOWING;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  // "Số tài khoản (*)" (eForm Nth) → bỏ cả cặp ngoặc của dấu *.
  const cleanLabel = (s) => String(s || "").replace(/\(\s*[*＊]\s*\)/g, "").replace(/[*＊]/g, "").replace(/\s+/g, " ")
    .replace(/[\s:]+$/, "").trim();
  const fold = (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const nthPage = () => location.hostname === NTH_HOST;
  // eForm Nth: trang nhập thông tin = ô CongDan_* NHÌN THẤY (cùng dấu hiệu bcaKeKhaiForm của content.js); trang chọn trường
  // hợp / xác nhận nộp không có.
  const nthForm = () => Array.from(document.querySelectorAll(NTH_FORM_SEL)).some(shown);
  const ourPage = () => window.top === window
    && (location.hostname === HOST ? H.detectFormKind?.() === "standard" : nthPage() && nthForm());

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
      // bootstrap-select (eForm Nth): <select> ẩn trong / ngay trước div.bootstrap-select, ô công dân thấy là nút mở menu.
      const bs = el.closest(".bootstrap-select") || (next?.classList?.contains("bootstrap-select") ? next : null);
      if (bs) return bs.querySelector("button.dropdown-toggle") || bs;
    }
    return el;
  }

  // eForm Nth: chỉ ô của form kê khai. Bỏ ô trong bảng Thành phần hồ sơ (ô Số bản cạnh ô chọn tệp), mục Giấy tờ khác, mã
  // xác nhận và ô chọn ngôn ngữ đầu trang. Ô không mang tên CongDan_* (Nơi nhận, tài khoản ngân hàng…) phải cùng <form>
  // với ô CongDan_*.
  function nthScoped(el) {
    const name = String(el.getAttribute("name") || "");
    if (el.closest("tr")?.querySelector('input[type="file"]') || el.closest("li")?.querySelector('input[type="file"]')) {
      return false;
    }
    if (/^(HoSoOnline_|GiayToCuaHoSoOnline_)/.test(name)) return false;
    if (/captcha|xacnhan|xac_nhan|ngon_?ngu/i.test(`${el.id || ""} ${name}`)) return false;
    if (/^CongDan_/.test(name)) return true;
    const form = document.querySelector(NTH_FORM_SEL)?.closest("form");
    return !!form && form.contains(el);
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
  const counted = (c) => !SKIP_TYPES.test(c.type || "") && !c.closest(".select2-container, .bs-searchbox")
    && (c.type === "radio" ? radioShown(c) : shown(boxOf(c)));

  // Nhãn gần nhất phía trước `target` trong `container`; giữa nhãn và ô có ô khác (không tính các radio cùng nhóm
  // `group`) thì nhãn đó là của ô khác → null.
  function precedingLabel(container, target, group = []) {
    const labels = Array.from(container.querySelectorAll(LABEL_SEL)).filter((l) => !target.contains(l)
      && !l.contains(target) && !optionLabel(l) && !isErrorNode(l) && textOf(l) && shown(l)
      && (l.compareDocumentPosition(target) & FOLLOWING));
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

  // Dấu * cổng vẽ bằng CSS (".required::after { content: '*' }", trang Thông báo lưu trú) không nằm trong textContent
  // → đọc cả nội dung ::before / ::after của nhãn và các thẻ con của nhãn.
  function pseudoStar(el) {
    for (const pseudo of ["::after", "::before"]) {
      let content = "";
      try { content = getComputedStyle(el, pseudo).content || ""; } catch (_) { content = ""; }
      if (content !== "none" && /[*＊]/.test(content)) return true;
    }
    return false;
  }

  const REQUIRED_MARK_SEL = ".required, .text-danger, .red, .star, .asterisk, .mandatory, .text-red, .require";

  function markedLabel(label) {
    if (!label) return false;
    if (/[*＊]/.test(label.textContent || "") || label.matches(REQUIRED_MARK_SEL)) return true;
    if (label.querySelector(REQUIRED_MARK_SEL)) return true;
    if ([label, ...Array.from(label.querySelectorAll("*")).slice(0, 8)].some(pseudoStar)) return true;
    // "<label>Tên</label><span class="text-danger">*</span>": dấu * đứng ngay sau nhãn.
    const after = label.nextElementSibling;
    return !!after && /^[*＊]$/.test(textOf(after));
  }

  // Lời cổng báo dưới ô sau khi bấm nộp ("Vui lòng chọn loại hình cơ sở lưu trú", "Trường này không được để trống").
  const ERROR_TEXT = /^(vui long (chon|nhap|dien|cung cap)|truong nay|khong duoc (de|bo) trong|bat buoc|ban chua (chon|nhap))/;
  const ERROR_SEL = ".error, .invalid-feedback, .help-block, .text-danger, .field-validation-error, .error-message, "
    + ".validation-message, .validate-error, .msg-error, .parsley-errors-list";
  const isErrorNode = (el) => !!el && (/-error$/.test(el.id || "") || el.classList?.contains("error")
    || ERROR_TEXT.test(fold(textOf(el))));

  // Ô cổng đã gắn lỗi "bắt buộc" (sau lần bấm nộp bị chặn): coi là ô bắt buộc dù nhãn không có dấu * đọc được.
  function portalFlagged(el, box) {
    if (el.getAttribute("aria-invalid") === "true") return true;
    if ([el, box].some((n) => n?.classList && (n.classList.contains("is-invalid")
      || n.classList.contains("input-validation-error")))) return true;
    const own = [
      el.id ? document.getElementById(`${el.id}-error`) : null,
      ...(el.id ? Array.from(document.querySelectorAll(`label.error[for="${CSS.escape(el.id)}"]`)) : []),
      ...(el.name ? Array.from(document.querySelectorAll(`[data-valmsg-for="${CSS.escape(el.name)}"]`)) : []),
    ];
    if (own.some((n) => n && shown(n) && textOf(n))) return true;
    // Dòng lỗi trong khối riêng của ô (khối không chứa ô khác).
    let wrap = box?.parentElement || el.parentElement;
    for (let level = 0; wrap && level < 3; wrap = wrap.parentElement, level += 1) {
      if (controlsIn(wrap).some((c) => c !== el && counted(c) && c.type !== "radio")) break;
      if (Array.from(wrap.querySelectorAll(ERROR_SEL)).some((n) => shown(n) && !n.contains(el)
        && ERROR_TEXT.test(fold(textOf(n))))) return true;
    }
    return false;
  }

  // Nhãn không nằm trong thẻ label quen (trang Thông báo lưu trú: "Loại hình cơ sở lưu trú *" là span/div trơn) → lấy
  // chữ đứng ngay trước ô trong khối riêng của ô (khối không chứa ô khác). Bỏ chữ trong ô chọn / select2 / dòng lỗi.
  function looseLabel(anchor, group = []) {
    let wrap = anchor.parentElement;
    let best = null;
    for (let level = 0; wrap && level < 4; wrap = wrap.parentElement, level += 1) {
      if (controlsIn(wrap).some((c) => c !== anchor && !group.includes(c) && counted(c))) break;
      const walker = document.createTreeWalker(wrap, NodeFilter.SHOW_TEXT);
      let star = false;
      let found = null;
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!(node.compareDocumentPosition(anchor) & FOLLOWING)) break; // chỉ chữ đứng trước ô
        const host = node.parentElement;
        const text = String(node.textContent || "").replace(/\s+/g, " ").trim();
        if (!text || !host || host.closest("select, option, script, style, .select2-container, [id^='tlnd']")
          || host.closest(ERROR_SEL.replace(/\.text-danger, /, "")) || isErrorNode(host) || !shown(host)) continue;
        if (/^[*＊]+$/.test(text)) { if (found) star = true; continue; }
        found = host;
        star = /[*＊]/.test(text);
      }
      if (found) {
        // Lên tới thẻ bao trọn cả nhãn ("Loại hình <b>cơ sở</b> lưu trú") nhưng không bao ô.
        let el = found;
        while (el.parentElement && el.parentElement !== wrap && !el.parentElement.contains(anchor)
          && textOf(el.parentElement).length <= 150) el = el.parentElement;
        const text = cleanLabel(textOf(el));
        if (text && text.length <= 150) { best = { text, marked: star || markedLabel(el) }; break; }
      }
    }
    return best;
  }

  // → { text, marked }: nhãn của ô + nhãn có dấu * hay không. Radio: `anchor` = radio đầu nhóm, `group` = cả nhóm.
  function labelOf(el, anchor, group = []) {
    if (el.id && el.type !== "radio") {
      // Bỏ nhãn lỗi jQuery validate (<label class="error" for=id>Vui lòng chọn …</label>) — không phải tên ô.
      const own = Array.from(document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`))
        .find((l) => textOf(l) && !isErrorNode(l));
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
    return looseLabel(anchor, group) || { text: hintOf(el), marked: false };
  }

  // Tên HTML (accomStay_cboACCOMMODATION_TYPE, data[x], txtNAME) không đọc cho công dân.
  const htmlName = (text) => /^[\w.\-[\]#:]+$/.test(text) && (/[_[\]]/.test(text) || /[a-z][A-Z]/.test(text));

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
      if (nthPage() && !nthScoped(el)) continue;
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
        // Không đọc được nhãn: hỏi theo tên phần (BE bỏ "(phần)" khi nhãn trùng phần), không đưa tên HTML ra.
        label: (text && !htmlName(text) ? text : "") || sectionOf(el) || "Ô còn trống", section: sectionOf(el),
        marker: marked || el.required || el.getAttribute("aria-required") === "true"
          || portalFlagged(group[0] || el, box),
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
