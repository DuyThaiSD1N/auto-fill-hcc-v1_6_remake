// Bổ sung ô còn trống trên trang nộp hồ sơ cổng Bắc Ninh (dichvucong.bacninh.gov.vn, Liferay, 4 tab cùng trang): tab
// "Chọn cơ quan tiếp nhận" → khối người ủy quyền (ô doiTuongKhac*, nạp bằng AJAX sau khi chọn loại đối tượng), tab
// "Nhập đơn đăng ký" → eForm (ô element_<số>, nhãn ở title). Cùng giao thức fieldReviewMark / fieldReviewNext /
// fieldReviewStop với content/field-review.js nên sidebar và BE (chat/field_review) dùng chung; file này chỉ khác cách
// đọc / ghi ô:
//   - chỉ ô của tab đang mở, đang hiện, sửa được; ô tích / radio để công dân tự tích (nhãn trùng giữa các mục);
//   - tên ô = khoá class eform-element-<Khoá> (ô đơn) hoặc đuôi id doiTuongKhac* (khối ủy quyền) — khớp NO_ASK của BE;
//   - cổng không đánh dấu ô bắt buộc → chỉ ô BE khai REQUIRED là bắt buộc;
//   - ô chọn select2: lựa chọn "-- Chọn … --" / "Chưa có thông tin" coi là trống; ghi bằng engine Bắc Ninh
//     (H.fillFormBacNinh, comp bn-select); ô chữ ghi thẳng vào đúng phần tử (khoá class có thể trùng giữa các mục);
//   - phần (section) của ô đơn = tiêu đề mục gần nhất phía trên (nhãn "3. Bên bảo đảm" hoặc đoạn <p> "4. Bên nhận bảo
//     đảm"); số mục BE bỏ khi đọc;
//   - trang hoàn thiện thông tin tài khoản (/vneidsso, portlet _taikhoan_sso_vneid_): chỉ ô tab "Thông tin chung", ô có
//     dấu * ở nhãn là bắt buộc, ô khoá (họ tên / số định danh / ngày sinh cổng lấy từ VNeID) không hỏi;
//   - BE khai MIRROR "ô trả lời=ô ghi kèm" (ô tiêu đề mang đúng giá trị ô dưới): trả lời xong ghi kèm nếu ô kia trống.
(() => {
  if (window.__TLND_FIELD_REVIEW_BACNINH__) return;
  window.__TLND_FIELD_REVIEW_BACNINH__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const PFX = "_org_bn_hoso_noptructuyen_";
  const ASKING = "tlnd-fr-asking";
  const OPTIONAL = "tlnd-fr-optional";
  const MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default", OPTIONAL];
  const STYLE_ID = "tlnd-bacninh-field-review-style";
  // Lớp chung của mọi ô eForm, không phải khoá ngữ nghĩa của ô.
  const GENERIC_CLASSES = new Set(["text", "textarea", "date", "label", "checkbox", "radio", "select", "number"]);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
    .replace(/\s+/g, " ").trim().toLowerCase();
  // Bỏ dấu *, số chú thích của mẫu đơn "(14)", dấu ":" cuối.
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s*\(\d+\)/g, "").replace(/\s+/g, " ")
    .replace(/\s*:\s*$/, "").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const tab = () => (typeof H.bacNinhTab === "function" ? H.bacNinhTab() : 0);
  const ACCOUNT_MARK = "_taikhoan_sso_vneid_";
  // Pane tab "Thông tin chung" của form tài khoản (li…TabsId ↔ div…TabsSection như trang nộp hồ sơ).
  function accountRoot() {
    if (typeof H.bacNinhAccountForm !== "function" || !H.bacNinhAccountForm()) return null;
    const li = document.querySelector('li[data-tab-name="thongtinchung"]');
    const id = String(li?.id || "");
    return id.endsWith("TabsId") ? document.getElementById(id.slice(0, -"TabsId".length) + "TabsSection") : null;
  }
  const ourPage = () => tab() === 1 || tab() === 2 || !!accountRoot();

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

  const isPlaceholder = (text) => {
    const t = fold(text).replace(/^-+\s*|\s*-+$/g, "");
    return !t || t.startsWith("chon ") || t === "chua co thong tin";
  };

  function rawLabel(el) {
    for (let p = el.parentElement, depth = 0; p && depth < 4; p = p.parentElement, depth++) {
      const label = p.querySelector(":scope > label");
      if (label && textOf(label)) return textOf(label);
    }
    return "";
  }

  function accountSlots(root, skip) {
    const out = [];
    for (const el of root.querySelectorAll(`input[name*="${ACCOUNT_MARK}"], select[name*="${ACCOUNT_MARK}"], textarea[name*="${ACCOUNT_MARK}"]`)) {
      const type = String(el.getAttribute("type") || "").toLowerCase();
      if (["hidden", "file", "checkbox", "radio", "button", "submit", "reset"].includes(type)) continue;
      const kind = el.tagName === "SELECT" ? "select" : /\bdatepicker\b/.test(el.className) ? "date" : "text";
      const box = kind === "select" ? selectBox(el) : el;
      if (!shown(box) || el.disabled || el.readOnly) continue;
      const name = String(el.name).split("_").pop();
      if (!name || skip.has(name)) continue;
      const legend = textOf(el.closest("fieldset")?.querySelector("legend"));
      out.push({
        key: name, name, fillName: name, kind, el, box, label: ownLabel(el), section: cleanLabel(legend),
        marker: rawLabel(el).includes("*"),
        value: () => (kind === "select" ? selectValue(el) : String(el.value || "").trim()),
        options: () => (kind === "select"
          ? [...new Set(Array.from(el.options).map(textOf).filter((t) => !isPlaceholder(t)))].slice(0, 400) : []),
      });
    }
    return out;
  }

  function ownLabel(el) {
    if (el.id) {
      const byFor = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      const text = cleanLabel(byFor?.getAttribute("title") || textOf(byFor));
      if (text) return text;
    }
    // Khối ủy quyền: <div class="col…"><label>Họ và tên *</label><div class="form-group…"><input></div></div>.
    for (let p = el.parentElement, depth = 0; p && depth < 4; p = p.parentElement, depth++) {
      const label = p.querySelector(":scope > label");
      if (label && textOf(label)) return cleanLabel(textOf(label));
    }
    return cleanLabel(el.getAttribute("title") || el.getAttribute("placeholder") || "");
  }

  function formKey(el) {
    const keys = Array.from(el.classList).filter((c) => c.startsWith("eform-element-"))
      .map((c) => c.slice("eform-element-".length)).filter((k) => k && !GENERIC_CLASSES.has(k));
    return keys.pop() || String(el.name || "").replace(PFX, "");
  }

  function sections(root) {
    const map = new Map();
    let current = "";
    // Tiêu đề mục có khi là nhãn của một ô, có khi chỉ là đoạn <p> của mẫu đơn.
    for (const label of root.querySelectorAll("label, p")) {
      const text = cleanLabel(label.getAttribute("title") || textOf(label));
      const top = text.match(/^(\d+)\.\s+\S/);
      const sub = text.match(/^(\d+)\.\d+\./);
      if (top && !sub) current = text;
      else if (sub && !current.startsWith(`${sub[1]}.`) && !current.startsWith(`Mục ${sub[1]}`)) current = `Mục ${sub[1]}`;
      const target = label.getAttribute("for");
      if (target) map.set(target, current);
    }
    return map;
  }

  function selectBox(el) {
    const next = el.nextElementSibling;
    return next?.classList.contains("select2") ? next : el;
  }

  function selectValue(el) {
    const option = el.selectedOptions?.[0];
    const text = textOf(option);
    return option && el.value && el.value !== "0" && !isPlaceholder(text) ? text : "";
  }

  // Mọi ô ĐANG HIỆN, sửa được, của tab đang mở, theo thứ tự trên trang.
  function slots(noAsk) {
    const skip = new Set(noAsk || []);
    const account = accountRoot();
    if (account) return accountSlots(account, skip);
    const out = [];
    const current = tab();
    const root = document.getElementById(current === 1 ? `${PFX}thongTinChuHoSoDoiTuongKhacDv` : `${PFX}dvNhapDonDangKy`);
    if (!root || (current !== 1 && current !== 2)) return out;
    const sectionOf = current === 2 ? sections(root) : new Map();
    const prefix = current === 1 ? `${PFX}doiTuongKhac` : `${PFX}element_`;
    for (const el of root.querySelectorAll(`input[name^="${prefix}"], textarea[name^="${prefix}"], select[name^="${prefix}"]`)) {
      const type = String(el.getAttribute("type") || "").toLowerCase();
      if (["hidden", "file", "checkbox", "radio", "button"].includes(type)) continue;
      const kind = el.tagName === "SELECT" ? "select" : /\b(datepicker|eform-element-date)\b/.test(el.className) ? "date"
        : "text";
      const box = kind === "select" ? selectBox(el) : el;
      if (!shown(box) || el.disabled || (kind === "text" && el.readOnly)) continue;
      const name = current === 1 ? String(el.name).slice(PFX.length) : formKey(el);
      if (!name || skip.has(name)) continue;
      out.push({
        key: String(el.name).slice(PFX.length), name, fillName: String(el.name).slice(PFX.length), kind, el, box,
        label: ownLabel(el),
        section: sectionOf.get(el.id) || "",
        value: () => (kind === "select" ? selectValue(el) : String(el.value || "").trim()),
        options: () => (kind === "select"
          ? [...new Set(Array.from(el.options).map(textOf).filter((t) => !isPlaceholder(t)))].slice(0, 400) : []),
      });
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
      slot.required = need.has(slot.name) || !!slot.marker;
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

  // ── Điền một ô ──

  function mirrorTarget(name, rules) {
    const pair = (rules?.mirror || []).map((m) => String(m).split("=")).find(([from]) => from === name);
    if (!pair) return null;
    const el = document.querySelector(`#${PFX}dvNhapDonDangKy [class~="eform-element-${pair[1]}"]`);
    return el && /^(INPUT|TEXTAREA)$/.test(el.tagName) ? el : null;
  }

  async function applyValue(slot, value, rules) {
    try {
      if (slot.kind === "select") {
        if (typeof H.fillFormBacNinh !== "function") return false;
        await H.fillFormBacNinh([{ name: slot.fillName, comp: "bn-select", value }]);
      } else {
        H.setNativeValue(slot.el, value, { typing: true, commit: true });
        H.markFilled?.(slot.el);
        const twin = mirrorTarget(slot.name, rules);
        if (twin && !String(twin.value || "").trim()) {
          H.setNativeValue(twin, value, { typing: true, commit: true });
          H.markFilled?.(twin);
        }
      }
    } catch (e) {
      console.warn("[TLND] bổ sung ô lỗi:", e);
      return false;
    }
    await sleep(300);
    return !!slot.value();
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
      const ok = target ? await applyValue(target, String(msg.apply.value ?? ""), msg) : false;
      applied = { key: msg.apply.key, ok };
      if (!ok) skip.add(msg.apply.key);
      await sleep(300); // chọn Tỉnh xong cổng mới nạp danh sách Xã
    }
    const { list, stats } = markAll(msg);
    // Ô chọn chưa có lựa chọn (Xã chờ chọn Tỉnh) chưa hỏi được → hỏi ô khác trước, lượt sau quét lại.
    const askable = (s) => !s.value() && !skip.has(s.key) && (s.kind !== "select" || s.options().length > 0);
    const slot = (msg.focus && list.find((s) => s.key === msg.focus || s.name === msg.focus))
      || (msg.requiredFirst && list.find((s) => s.required && askable(s)))
      || list.find(askable);
    if (!slot) { unfocus(); return { ok: true, applied, field: null, stats }; }
    await focusSlot(slot);
    return { ok: true, applied, field: publicField(slot), stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // Chỉ trang nộp hồ sơ Bắc Ninh đang ở tab khối ủy quyền / tab đơn trả lời; cổng khác có bộ đọc riêng.
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
