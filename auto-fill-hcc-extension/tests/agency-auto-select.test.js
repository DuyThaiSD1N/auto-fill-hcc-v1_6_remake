/**
 * content/agency-select.js — tự chọn Tỉnh/Xã ở khối "Chọn cơ quan thực hiện" (dichvucong.gov.vn).
 *
 * Dựng DOM giả mô phỏng đúng combobox của cổng (button[aria-haspopup=listbox] + listbox rời, danh
 * sách xã CHỈ nạp sau khi chọn tỉnh) rồi chạy thật kịch bản click để chắc thứ tự thao tác đúng.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "content", "agency-select.js"), "utf8");

// ---------- mini DOM ----------
function parseStep(step) {
  const tag = (step.match(/^[a-zA-Z0-9]+/) || [""])[0];
  const not = step.match(/:not\(\[([\w-]+)\]\)/);
  const attrs = [];
  const attrRe = /\[([\w-]+)(?:([*^]?=)"([^"]*)")?\]/g;
  let m;
  const withoutNot = step.replace(/:not\([^)]*\)/g, "");
  while ((m = attrRe.exec(withoutNot))) attrs.push({ name: m[1], op: m[2], value: m[3] });
  // Selector class (.modal): KHÔNG bỏ qua — bỏ qua thì ".modal" khớp mọi thẻ, mọi trang đều bị coi
  // là có modal và test cho kết quả dương tính giả.
  const classes = (withoutNot.replace(/\[[^\]]*\]/g, "").match(/\.[\w-]+/g) || [])
    .map((c) => c.slice(1));
  return { tag, attrs, classes, notAttr: not ? not[1] : null };
}

function matchesStep(node, step) {
  const { tag, attrs, classes, notAttr } = typeof step === "string" ? parseStep(step) : step;
  if (tag && node.tagName !== tag.toUpperCase()) return false;
  if (notAttr && node.getAttribute(notAttr) !== null) return false;
  if (classes?.length) {
    const own = String(node.getAttribute("class") || "").split(/\s+/).filter(Boolean);
    if (!classes.every((c) => own.includes(c))) return false;
  }
  for (const a of attrs) {
    const actual = node.getAttribute(a.name);
    if (actual === null) return false;
    if (!a.op) continue;
    if (a.op === "=" && actual !== a.value) return false;
    if (a.op === "*=" && !actual.includes(a.value)) return false;
    if (a.op === "^=" && !actual.startsWith(a.value)) return false;
  }
  return true;
}

function descendants(node, out = []) {
  for (const child of node.children) { out.push(child); descendants(child, out); }
  return out;
}

function matchAll(rootNode, selector) {
  const groups = selector.split(",").map((g) => g.trim()).filter(Boolean);
  const found = [];
  for (const node of descendants(rootNode)) {
    for (const group of groups) {
      const steps = group.split(/\s+/).map(parseStep);
      if (!matchesStep(node, steps[steps.length - 1])) continue;
      let ok = true;
      let cursor = node.parentElement;
      for (let i = steps.length - 2; i >= 0; i -= 1) {
        while (cursor && !matchesStep(cursor, steps[i])) cursor = cursor.parentElement;
        if (!cursor) { ok = false; break; }
        cursor = cursor.parentElement;
      }
      if (ok && !found.includes(node)) found.push(node);
    }
  }
  return found;
}

class N {
  constructor(tag, attrs = {}, text = "") {
    this.tagName = String(tag).toUpperCase();
    this.attrs = { ...attrs };
    this.children = [];
    this.parentElement = null;
    this._text = text;
    this.onclick = null;
    this.disabled = false;
    this.hidden = false;
  }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  set textContent(v) { this._text = String(v); this.children = []; }
  append(...kids) {
    for (const kid of kids) { kid.parentElement = this; this.children.push(kid); }
    return this;
  }
  remove() {
    const kids = this.parentElement?.children;
    if (kids) kids.splice(kids.indexOf(this), 1);
    this.parentElement = null;
  }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getBoundingClientRect() { return { width: this.hidden ? 0 : 200, height: this.hidden ? 0 : 24 }; }
  get value() { return this._value === undefined ? "" : this._value; }
  set value(v) { this._value = String(v); }
  click() { if (typeof this.onclick === "function") this.onclick(); }
  scrollIntoView() {}
  dispatchEvent(evt) {
    const handler = this["on" + (evt?.type || "")];
    if (typeof handler === "function") handler.call(this, evt);
    return true;
  }
  querySelector(sel) { return matchAll(this, sel)[0] || null; }
  querySelectorAll(sel) { return matchAll(this, sel); }
  closest(sel) {
    let node = this;
    while (node) { if (matchesStep(node, sel)) return node; node = node.parentElement; }
    return null;
  }
}

// ---------- trang giả: khối "Chọn cơ quan thực hiện" ----------
function buildPage({ provinces, wardsByProvince, maxRendered = Infinity,
  commitOn = "click", swapToInput = false, results = null, infoModalAfterSubmit = false }) {
  const body = new N("body");
  const card = new N("div", { class: "border rounded-xs" });
  const title = new N("div", { class: "font-medium" }, "Chọn cơ quan thực hiện");
  const form = new N("form", { class: "w-full" });
  card.append(title, form);
  body.append(card);

  const clicks = [];
  let openList = null;

  const makeCombo = (placeholder, optionsFor) => {
    const slot = new N("div", { class: "mt-4" });
    form.append(slot);
    const button = new N("button", { type: "button", "aria-haspopup": "listbox", "aria-expanded": "false" });
    const label = new N("span", { class: "text-gray-400 text-base truncate" }, placeholder);
    button.append(label, new N("div", { class: "shrink-0" }));
    slot.append(button);

    // Sau khi có giá trị, cổng thay hẳn ô bằng <input value="…"> + nút × (xem ảnh DevTools).
    let filled = null;
    const commit = (text) => {
      if (!swapToInput) { label.textContent = text; return; }
      // React vứt hẳn <button> cũ -> nhãn của nó KHÔNG được cập nhật. Ai cache node cũ sẽ đọc ra
      // placeholder mãi mãi, đúng như lỗi gặp trên cổng thật.
      if (!filled) {
        filled = new N("input", { type: "text", class: "custom-input-typography" });
        filled.onclick = openDropdown;
        button.remove();
        slot.append(filled);
        slot.append(new N("button", { class: "shrink-0" }, "×"));
      }
      filled.value = text;
    };
    const currentText = () => (filled ? filled.value : label.textContent);
    // Dropdown thật của cổng: PORTAL gắn cuối <body> (position: fixed), gồm ô tìm kiếm là ANH EM
    // của <ul role="listbox">, option là <li> THƯỜNG (không role="option"), danh sách lọc theo ô gõ.
    const openDropdown = () => {
      if (openList) { openList.panel.remove(); openList = null; button.setAttribute("aria-expanded", "false"); return; }
      const panel = new N("div", { class: "bg-white border border-gray-200 rounded-lg shadow-lg" });
      const searchBox = new N("div", { class: "p-2 border-b bg-white transition-all" });
      const search = new N("input", { type: "text", class: "w-full bg-white rounded-md" });
      searchBox.append(search);
      const list = new N("ul", { role: "listbox", class: "max-h-56 overflow-auto py-1" });
      panel.append(searchBox, list);

      const render = (query) => {
        list.children = [];
        const norm = (s) => s.toLowerCase();
        const all = optionsFor();
        const shown = query ? all : all.slice(0, maxRendered);
        for (const text of shown) {
          if (query && !norm(text).includes(norm(query))) continue;
          const option = new N("li", {}, text);   // KHÔNG có role="option"
          // Cổng thật chốt lựa chọn ở mousedown (chạy trước blur); .click() đơn thuần không ăn.
          option["on" + commitOn] = () => {
            commit(text);
            panel.remove();
            openList = null;
            button.setAttribute("aria-expanded", "false");
            clicks.push("chọn " + text);
          };
          list.append(option);
          option.parentElement = list;
        }
      };
      search.oninput = () => render(search.value);
      render("");

      body.append(panel);
      openList = { panel, search, render };
      button.setAttribute("aria-expanded", "true");
    };
    button.onclick = openDropdown;
    button.onmousedown = null;
    return { get label() { return { get textContent() { return currentText(); } }; } };
  };

  const province = makeCombo("-- Chọn Tỉnh/ Thành phố --", () => provinces);
  // Cổng chỉ nạp phường/xã SAU khi đã chọn tỉnh — giống hành vi thật.
  const ward = makeCombo("-- Chọn Phường/ Xã --", () => wardsByProvince[province.label.textContent] || []);

  const confirm = new N("button", { class: "bg-primary" }, "Nộp hồ sơ");
  confirm.onclick = () => {
    clicks.push("bấm Nộp hồ sơ");
    // Trang thật chuyển sang "Danh sách dịch vụ công": mỗi dịch vụ 1 thẻ kèm nút "Nộp trực tuyến".
    for (const title of (results || [])) {
      const row = new N("div", { class: "grid grid-cols-12" });
      row.append(new N("div", { class: "font-semibold text-xl" }, title));
      const submit = new N("button", { class: "bg-primary" });
      submit.append(new N("div", {}).append(new N("span", {}, "Nộp trực tuyến")));
      submit.onclick = () => {
        clicks.push("bấm Nộp trực tuyến: " + title);
        if (!infoModalAfterSubmit) return;
        // Cổng chặn modal "Thông tin chung" trước wizard hồ sơ.
        const dialog = new N("div", { role: "dialog" });
        dialog.append(new N("div", {}, "Thông tin chung"));
        const ok = new N("button", {}, "Xác nhận");
        ok.onclick = () => {
          clicks.push("bấm Xác nhận modal");
          dialog.remove();
          body.append(new N("div", {}, "Kê khai thông tin"));
        };
        dialog.append(ok);
        body.append(dialog);
      };
      row.append(submit);
      body.append(row);
    }
  };
  form.append(confirm);

  return { body, card, province, ward, confirm, clicks };
}

/** Ctor giả có setter `value` trên prototype — giống hệt cách React chặn/ghi value thật. */
function nativeInputCtor() {
  function HTMLInputElement() {}
  Object.defineProperty(HTMLInputElement.prototype, "value", {
    configurable: true,
    set(v) { this._value = String(v); },
    get() { return this._value === undefined ? "" : this._value; },
  });
  return HTMLInputElement;
}

// ---------- chạy script trong sandbox ----------
const allStops = [];

function runScript(page, armValue) {
  const storage = { autofill_agency_autoselect: armValue };
  const toasts = [];
  const listeners = [];
  const timers = [];
  const sandbox = {
    console: { log() {}, warn() {} },
    setTimeout,
    clearTimeout,
    setInterval: (fn, ms) => {      // watcher SPA: giữ lại để test được nhịp hồi sau đăng nhập
      const id = setInterval(fn, ms);
      timers.push(id);
      return id;
    },
    Date,
    location: { hostname: "dichvucong.gov.vn", href: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/x" },
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    HTMLInputElement: nativeInputCtor(),
    Event,
    // realClick bắn pointer/mouse; sandbox phải có ctor thật thì handler on<type> mới chạy.
    MouseEvent: class MouseEvent extends Event {},
    PointerEvent: class PointerEvent extends Event {},
    document: {
      readyState: "complete",
      body: page.body,
      addEventListener() {},
      querySelectorAll: (sel) => matchAll(page.body, sel),
      querySelector: (sel) => matchAll(page.body, sel)[0] || null,
    },
    chrome: {
      // Popup hỏi trạng thái luồng qua message -> giữ listener để test gọi được.
      runtime: { onMessage: { addListener: (fn) => { listeners.push(fn); } } },
      storage: {
        local: {
          async get(key) { return { [key]: storage[key] }; },
          async set(items) { Object.assign(storage, items); },
          async remove(key) { delete storage[key]; },
        },
      },
    },
  };
  sandbox.window = sandbox;
  sandbox.window.top = sandbox;
  sandbox.window.__HCC__ = { showPageToast: (msg, kind) => toasts.push({ msg, kind }) };
  vm.runInNewContext(source, sandbox, { filename: "agency-select.js" });
  const ask = (action) => new Promise((resolve) => {
    let answered = false;
    for (const fn of listeners) {
      const kept = fn({ action }, null, (res) => { answered = true; resolve(res); });
      if (kept === true) return;   // handler trả lời bất đồng bộ
    }
    if (!answered) resolve(null);
  });
  const stop = () => timers.forEach(clearInterval);
  allStops.push(stop);
  return { storage, toasts, ask, stop };
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const provinces = ["Thành phố Hà Nội", "Tỉnh Tuyên Quang", "Tỉnh Lâm Đồng"];
  const wardsByProvince = {
    "Tỉnh Tuyên Quang": ["Phường Hà Giang 1", "Phường Hà Giang 2", "Xã Yên Sơn"],
    "Tỉnh Lâm Đồng": ["Xã Đơn Dương", "Phường Lâm Viên - Đà Lạt"],
  };

  // --- 1. Luồng chuẩn: điền đủ tỉnh + xã rồi bấm nút xác nhận ---
  let page = buildPage({ provinces, wardsByProvince, results: ["Thủ tục đăng ký kết hôn"] });
  let ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2", procedureKey: "ket-hon",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(2500);

  assert.equal(page.province.label.textContent, "Tỉnh Tuyên Quang", "chưa chọn đúng tỉnh");
  assert.equal(page.ward.label.textContent, "Phường Hà Giang 2", "chưa chọn đúng phường/xã");
  assert.deepEqual(page.clicks, [
    "chọn Tỉnh Tuyên Quang", "chọn Phường Hà Giang 2",
    "bấm Nộp hồ sơ", "bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn",
  ]);
  assert.equal(storageArm(ctx), undefined, "phải xóa cờ sau khi chạy xong (tránh lặp ở trang kết quả)");
  assert.equal(ctx.toasts.at(-1).kind, "success");

  // --- 2. Không có cờ -> KHÔNG đụng vào trang (cán bộ tự duyệt cổng bằng tay) ---
  page = buildPage({ provinces, wardsByProvince });
  runScript(page, undefined);
  await wait(600);
  assert.deepEqual(page.clicks, [], "không có cờ thì không được tự bấm gì");
  assert.equal(page.province.label.textContent, "-- Chọn Tỉnh/ Thành phố --");

  // --- 3. Cờ quá hạn -> bỏ qua và dọn cờ ---
  page = buildPage({ provinces, wardsByProvince });
  ctx = runScript(page, {
    province: "Tỉnh Lâm Đồng", ward: "Xã Đơn Dương", at: Date.now() - 11 * 60 * 1000,
  });
  await wait(400);
  assert.deepEqual(page.clicks, [], "cờ quá hạn thì không được thao tác");
  assert.equal(storageArm(ctx), undefined, "cờ quá hạn phải bị xóa");

  // --- 4. Xã không có trong danh sách cổng -> dừng, báo người dùng, KHÔNG bấm xác nhận ---
  page = buildPage({ provinces, wardsByProvince });
  ctx = runScript(page, {
    province: "Tỉnh Lâm Đồng", ward: "Phường Không Tồn Tại", at: Date.now(),
  });
  await wait(6500);   // script gõ ô tìm kiếm rồi còn chờ hết timeout mới chịu bỏ cuộc
  assert.equal(page.province.label.textContent, "Tỉnh Lâm Đồng", "vẫn phải chọn được tỉnh");
  assert.ok(!page.clicks.includes("bấm Nộp hồ sơ"), "không được bấm xác nhận khi thiếu phường/xã");
  assert.match(ctx.toasts.at(-1).msg, /Phường\/Xã/);
  assert.equal(ctx.toasts.at(-1).kind, "warning");

  // --- 5. Khớp được kể cả khi cổng ghi thiếu/thừa tiền tố cấp hành chính ---
  page = buildPage({
    provinces: ["Tuyên Quang"], wardsByProvince: { "Tuyên Quang": ["Hà Giang 2"] }, results: ["Thủ tục đăng ký kết hôn"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(1500);
  assert.equal(page.province.label.textContent, "Tuyên Quang");
  assert.equal(page.ward.label.textContent, "Hà Giang 2");
  assert.ok(page.clicks.includes("bấm Nộp hồ sơ"));

  // --- 6. Danh sách dài, tỉnh đích CHƯA render (ul max-h-56 / ảo hóa) -> phải gõ ô tìm kiếm ---
  const manyProvinces = [
    ...Array.from({ length: 20 }, (_, i) => `Tỉnh Khác ${i + 1}`),
    "Tỉnh Tuyên Quang",
  ];
  page = buildPage({
    provinces: manyProvinces,
    wardsByProvince: { "Tỉnh Tuyên Quang": ["Phường Hà Giang 2"] },
    maxRendered: 5,
    results: ["Thủ tục đăng ký kết hôn"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(2500);
  assert.equal(page.province.label.textContent, "Tỉnh Tuyên Quang",
    "phải gõ vào ô tìm kiếm để lôi tỉnh nằm ngoài phần đã render");
  assert.equal(page.ward.label.textContent, "Phường Hà Giang 2");
  assert.ok(page.clicks.includes("bấm Nộp hồ sơ"));

  // --- 7. Option chỉ ăn MOUSEDOWN (chạy trước blur) — .click() đơn thuần vô hiệu ---
  page = buildPage({ provinces, wardsByProvince, commitOn: "mousedown", results: ["Thủ tục đăng ký kết hôn"] });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(2500);
  assert.equal(page.province.label.textContent, "Tỉnh Tuyên Quang",
    "phải bắn mousedown, không chỉ .click()");
  assert.equal(page.ward.label.textContent, "Phường Hà Giang 2");
  assert.ok(page.clicks.includes("bấm Nộp hồ sơ"));

  // --- 8. Chọn xong cổng thay <button><span> bằng <input value> -> phải dò LẠI ô, không cache node ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown", swapToInput: true, results: ["Thủ tục đăng ký kết hôn"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(2500);
  assert.equal(page.province.label.textContent, "Tỉnh Tuyên Quang",
    "ô đổi sang <input> vẫn phải xác minh đúng");
  assert.equal(page.ward.label.textContent, "Phường Hà Giang 2");
  assert.ok(page.clicks.includes("bấm Nộp hồ sơ"));

  // --- 9. Bấm "Nộp hồ sơ" xong phải bấm luôn "Nộp trực tuyến" để vào biểu mẫu ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown", swapToInput: true,
    results: ["Thủ tục đăng ký kết hôn"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(3000);
  assert.deepEqual(page.clicks, [
    "chọn Tỉnh Tuyên Quang", "chọn Phường Hà Giang 2",
    "bấm Nộp hồ sơ", "bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn",
  ]);
  assert.equal(storageArm(ctx), undefined, "xong hết phải sạch cờ");
  assert.match(ctx.toasts.at(-1).msg, /mở biểu mẫu kê khai/);

  // --- 10. Nhiều dịch vụ cùng hiện -> bấm ĐÚNG thẻ mang tên thủ tục, không bấm bừa cái đầu ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown",
    results: ["Thủ tục đăng ký lại kết hôn", "Thủ tục đăng ký kết hôn"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(3000);
  assert.ok(page.clicks.includes("bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn"));
  assert.ok(!page.clicks.includes("bấm Nộp trực tuyến: Thủ tục đăng ký lại kết hôn"),
    "không được bấm nhầm thủ tục khác");

  // --- 11. Không xác định được thẻ nào -> KHÔNG bấm bừa, nhắc người dùng tự bấm ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown",
    results: ["Dịch vụ A", "Dịch vụ B"],
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", at: Date.now(),
  });
  await wait(18000);
  assert.ok(!page.clicks.some((c) => c.startsWith("bấm Nộp trực tuyến")),
    "không khớp thẻ nào thì tuyệt đối không bấm");
  assert.match(ctx.toasts.at(-1).msg, /Mời bấm "Nộp trực tuyến"/);
  assert.equal(storageArm(ctx), undefined);

  // --- 12. Sau đăng nhập: popup hỏi trạng thái + nhờ bấm Xác nhận ở modal "Thông tin chung" ---
  page = buildPage({ provinces, wardsByProvince });
  const modal = new N("div", { role: "dialog" });
  modal.append(new N("div", {}, "Thông tin chung"));
  const confirmModalBtn = new N("button", {}, "Xác nhận");
  confirmModalBtn.onclick = () => {
    page.clicks.push("bấm Xác nhận modal");
    modal.remove();
    page.body.append(new N("div", {}, "Kê khai thông tin"));   // sang bước kê khai
  };
  modal.append(confirmModalBtn);
  page.body.append(modal);

  ctx = runScript(page, undefined);   // KHÔNG có cờ: chặng này do popup chủ động hỏi
  await wait(300);
  let state = await ctx.ask("getPortalFlowState");
  assert.equal(state.infoModal, true, "phải nhận ra modal Thông tin chung");
  assert.equal(state.formReady, false);

  const confirmed = await ctx.ask("confirmInfoModal");
  assert.equal(confirmed.ok, true);
  assert.equal(confirmed.formReady, true, "bấm Xác nhận xong phải sang bước Kê khai thông tin");
  assert.ok(page.clicks.includes("bấm Xác nhận modal"));

  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.formReady, true);
  assert.equal(state.infoModal, false);

  // --- 13. autoConfirm: một mạch chọn cơ quan -> Nộp trực tuyến -> Xác nhận -> vào bước kê khai ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown",
    results: ["Thủ tục đăng ký kết hôn"], infoModalAfterSubmit: true,
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", autoConfirm: true, at: Date.now(),
  });
  await wait(4000);
  assert.deepEqual(page.clicks, [
    "chọn Tỉnh Tuyên Quang", "chọn Phường Hà Giang 2",
    "bấm Nộp hồ sơ", "bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn", "bấm Xác nhận modal",
  ]);
  assert.equal(storageArm(ctx), undefined, "hết chuỗi phải sạch cờ");
  assert.match(ctx.toasts.at(-1).msg, /bước kê khai/);

  // --- 14. autoConfirm: false -> dừng ngay sau "Nộp trực tuyến", KHÔNG tự bấm Xác nhận ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown",
    results: ["Thủ tục đăng ký kết hôn"], infoModalAfterSubmit: true,
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", autoConfirm: false, at: Date.now(),
  });
  await wait(3000);
  assert.ok(page.clicks.includes("bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn"));
  assert.ok(!page.clicks.includes("bấm Xác nhận modal"),
    "thủ tục tắt autoConfirm thì không được tự bấm Xác nhận");

  // --- 15. Đăng nhập lâu: modal hiện MUỘN -> giữ cờ, watcher tự vào tiếp, KHÔNG bắt bấm lại ---
  page = buildPage({
    provinces, wardsByProvince, commitOn: "mousedown",
    results: ["Thủ tục đăng ký kết hôn"],   // KHÔNG dựng modal ngay: giả cảnh còn ở trang đăng nhập
  });
  ctx = runScript(page, {
    province: "Tỉnh Tuyên Quang", ward: "Phường Hà Giang 2",
    procedureLabel: "Thủ tục đăng ký kết hôn", autoConfirm: true, at: Date.now(),
  });
  // Phải chờ QUÁ cửa sổ 8s của chặng Xác nhận thì mới đúng cảnh "đăng nhập lâu" — chờ ngắn hơn là
  // confirmStage còn đang trong waitFor, chưa đi tới nhánh quyết định giữ hay bỏ cờ.
  await wait(10500);
  assert.ok(page.clicks.includes("bấm Nộp trực tuyến: Thủ tục đăng ký kết hôn"));
  assert.ok(!page.clicks.includes("bấm Xác nhận modal"), "chưa có modal thì chưa bấm gì");
  assert.equal(storageArm(ctx)?.stage, "confirm",
    "hết cửa sổ chờ mà chưa thấy modal thì vẫn phải GIỮ cờ để đăng nhập xong tự chạy tiếp");

  // Người dân đăng nhập xong: cổng render modal (URL không đổi).
  const lateModal = new N("div", { role: "dialog" });
  lateModal.append(new N("div", {}, "Thông tin chung"));
  const lateOk = new N("button", {}, "Xác nhận");
  lateOk.onclick = () => {
    page.clicks.push("bấm Xác nhận modal");
    lateModal.remove();
    page.body.append(new N("div", {}, "Kê khai thông tin"));
  };
  lateModal.append(lateOk);
  page.body.append(lateModal);

  await wait(3000);
  assert.ok(page.clicks.includes("bấm Xác nhận modal"),
    "đăng nhập xong watcher phải tự bấm Xác nhận, không cần bấm lại Đi đến thủ tục");
  assert.equal(storageArm(ctx), undefined, "xong chuỗi phải sạch cờ");
  allStops.forEach((stop) => stop());   // dọn watcher của mọi ca, không thì node không thoát

  // --- 16. Xác nhận xong rơi vào bước "Thông tin chủ hồ sơ": phải DẶN, và chưa cho quét ---
  page = buildPage({ provinces, wardsByProvince });
  const ownerModal = new N("div", { role: "dialog" });
  ownerModal.append(new N("div", {}, "Thông tin chung"));
  const ownerOk = new N("button", {}, "Xác nhận");
  ownerOk.onclick = () => {
    page.clicks.push("bấm Xác nhận modal");
    ownerModal.remove();
    page.body.append(new N("div", {}, "Thông tin chủ hồ sơ"));   // wizard bước 1, CHƯA phải form
  };
  ownerModal.append(ownerOk);
  page.body.append(ownerModal);

  ctx = runScript(page, undefined);
  await wait(300);
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.infoModal, true);
  assert.equal(state.ownerInfo, false, "còn modal thì chưa tính là bước chủ hồ sơ");

  await ctx.ask("confirmInfoModal");
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.formReady, false, "bước chủ hồ sơ KHÔNG phải bước kê khai");
  assert.equal(state.ownerInfo, true, "phải nhận ra bước Thông tin chủ hồ sơ");
  assert.match(state.ownerStepHint, /bấm "Xác nhận"/, "phải có câu dặn bấm Xác nhận");

  // Điền xong, người dân bấm Xác nhận -> sang bước kê khai -> lúc này mới quét được.
  page.body.append(new N("div", {}, "Kê khai thông tin"));
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.formReady, true);
  assert.equal(state.ownerInfo, false);

  // --- 17. "Thông tin chung" là MỤC trong wizard (không phải modal) -> vẫn phải bấm Xác nhận ---
  page = buildPage({ provinces, wardsByProvince });
  const stepBox = new N("div", { class: "wizard-step" });     // KHÔNG có role="dialog"
  stepBox.append(new N("div", { class: "title" }, "Thông tin chung"));
  const stepOk = new N("button", {}, "Xác nhận");
  stepOk.onclick = () => {
    page.clicks.push("bấm Xác nhận mục Thông tin chung");
    stepBox.remove();
    page.body.append(new N("div", {}, "Thông tin chủ hồ sơ"));
  };
  stepBox.append(stepOk);
  page.body.append(stepBox);

  ctx = runScript(page, undefined);
  await wait(300);
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.infoModal, true, 'dạng mục trong wizard cũng phải nhận ra "Thông tin chung"');

  await ctx.ask("confirmInfoModal");
  assert.ok(page.clicks.includes("bấm Xác nhận mục Thông tin chung"));
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.ownerInfo, true, "bấm xong phải sang bước chủ hồ sơ và có lời dặn");

  // --- 18. Leo quá tay: khối ngoài cùng có NHIỀU nút Xác nhận -> KHÔNG bấm bừa ---
  page = buildPage({ provinces, wardsByProvince });
  const outer = new N("div", {});
  const inner = new N("div", {});
  inner.append(new N("div", {}, "Thông tin chung"));
  outer.append(inner);
  outer.append(new N("button", {}, "Xác nhận"));   // nút của bước KHÁC, cùng khối cha
  outer.append(new N("button", {}, "Xác nhận"));
  page.body.append(outer);

  ctx = runScript(page, undefined);
  await wait(300);
  state = await ctx.ask("getPortalFlowState");
  assert.equal(state.infoModal, false, "nhập nhằng nhiều nút Xác nhận thì không nhận, khỏi bấm nhầm");

  console.log("agency auto-select: 18 ca (mousedown, đổi input, tìm kiếm, nộp trực tuyến, xác nhận modal/mục, dặn bước chủ hồ sơ) — passed");
  // Script đang test còn vài vòng waitFor chạy nền (cố ý: đó là hành vi chờ trang của nó) nên node
  // sẽ không tự thoát. Assert đã xong hết -> thoát hẳn, không để runner tưởng test treo.
  process.exit(0);
})();

function storageArm(ctx) { return ctx.storage.autofill_agency_autoselect; }
