const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const mainSource = fs.readFileSync(path.join(root, "content/formio-select-main.js"), "utf8");
const contentSource = fs.readFileSync(path.join(root, "content.js"), "utf8");
const popupSource = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

const REQUEST = "__HCC_FORMIO_SELECT_REQUEST__";
const RESULT = "__HCC_FORMIO_SELECT_RESULT__";
const TARGET_ATTR = "data-hcc-formio-select-target";

// Môi trường tối thiểu: 1 ô select Form.io (khối bọc id="ew1") + form giả có everyComponent.
function setup({ dataSrc = "url", server = [], initial = [], multiple = false, caseSensitive = false } = {}) {
  const listeners = new Map();
  const attrs = new Map();
  const wrapper = {
    id: "ew1",
    querySelector: () => (comp.shown ? { textContent: comp.shown } : null),
    querySelectorAll: () => [],
  };
  const select = {
    name: "data[dichVu]",
    closest: (sel) => (sel.startsWith(".formio-component") ? wrapper : null),
  };
  const comp = {
    id: "ew1",
    key: "dichVu",
    component: { type: "select", dataSrc, multiple },
    selectOptions: initial,
    loading: false,
    dataValue: "",
    shown: "",
    searches: [],
    setCalls: [],
    updateItems(term, force) {
      this.searches.push({ term, force });
      this.loading = true;
      setTimeout(() => {
        const t = String(term || "");
        const hit = (label) => (caseSensitive ? label.includes(t) : label.toLowerCase().includes(t.toLowerCase()));
        this.selectOptions = server
          .filter((label) => !t || hit(label))
          .map((label, i) => ({ value: { _id: `id${i}`, ten: label }, label: `<span>${label}</span>` }));
        this.loading = false;
      }, 30);
    },
    setValue(value) {
      this.setCalls.push(value);
      this.dataValue = value && typeof value === "object" ? { ...value } : value;
      this.shown = value?.ten || value?.TenMuc || "";
    },
  };
  const form = { everyComponent: (fn) => fn(comp) };
  const document = {
    documentElement: { setAttribute: (k, v) => attrs.set(k, v) },
    addEventListener: (type, fn) => listeners.set(type, [...(listeners.get(type) || []), fn]),
    removeEventListener: (type, fn) => listeners.set(type, (listeners.get(type) || []).filter((x) => x !== fn)),
    dispatchEvent: (ev) => { (listeners.get(ev.type) || []).forEach((fn) => fn(ev)); return true; },
    querySelector: (sel) => (sel.includes(TARGET_ATTR) && select.requestId && sel.includes(select.requestId) ? select : null),
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init?.detail; } }
  class DOMParser {
    parseFromString(html) { return { body: { textContent: String(html).replace(/<[^>]+>/g, "") } }; }
  }
  const window = { Formio: { forms: { f1: form } } };
  class Event { constructor(type, init) { this.type = type; this.bubbles = !!init?.bubbles; } }
  // Như trình duyệt: InputEvent (UIEvent) luôn có detail = 0.
  class InputEvent extends Event { constructor(type, init) { super(type, init); this.detail = 0; } }
  const context = { window, document, CustomEvent, Event, InputEvent, DOMParser, CSS: { escape: (s) => s }, setTimeout, clearTimeout, console };
  vm.runInNewContext(mainSource, context);

  const request = (value) => new Promise((resolve) => {
    const requestId = `r${Math.random()}`;
    select.requestId = requestId;
    document.addEventListener(RESULT, (ev) => {
      const data = JSON.parse(ev.detail);
      if (data.requestId === requestId) resolve(data);
    });
    document.dispatchEvent(new CustomEvent(REQUEST, { detail: JSON.stringify({ requestId, value }) }));
  });
  return { comp, attrs, request, select };
}

// Choices giả như JS custom của cổng Bộ XD dựng: kết quả API vào kho Choices, KHÔNG vào comp.selectOptions.
function fakeChoices(comp, select, { pages = [], keywordResults = null, delay = 30 } = {}) {
  const store = [];
  let page = 0;
  const loadPage = () => setTimeout(() => {
    (pages[page] || []).forEach((label) => store.push({ value: `id_${label}`, label }));
    page += 1;
  }, delay);
  const calls = [];
  select.dispatchEvent = (ev) => {
    if (ev.type !== "change") return true;
    const picked = store.find((c) => c.value === comp.choices.selected);
    comp.dataValue = picked.value;
    comp.shown = picked.label;
    return true;
  };
  comp.choices = {
    _store: { get choices() { return store; } },
    passedElement: { element: select },
    input: {
      element: {
        value: "",
        dispatchEvent(ev) {
          calls.push(["input", this.value]);
          // Đúng cách JS custom Nước sản xuất đọc từ khoá: detail có giá trị (kể cả 0 của InputEvent) thì dùng detail.
          const detailValue = ev && ev.detail && ev.detail.value;
          const keyword = String((detailValue !== undefined ? detailValue : this.value) || "").trim();
          if (ev.type === "input" && keywordResults && keyword) {
            setTimeout(() => { store.splice(0, store.length, ...keywordResults.map((label) => ({ value: `id_${label}`, label }))); }, delay);
          }
          return true;
        },
      },
    },
    choiceList: {
      element: {
        scrollTop: 0,
        scrollHeight: 100,
        dispatchEvent(ev) { if (ev.type === "scroll") { calls.push(["scroll"]); loadPage(); } return true; },
      },
    },
    showDropdown() { calls.push(["show"]); if (!store.length) loadPage(); },
    hideDropdown() { calls.push(["hide"]); },
    setChoiceByValue(value) { calls.push(["pick", value]); this.selected = value; },
  };
  return { store, calls };
}

const TAI = "Xe ô tô tải kinh doanh vận tải hàng hóa thông thường và xe taxi tải";

test("cầu nối báo sẵn sàng qua thuộc tính trên documentElement", () => {
  const { attrs } = setup();
  assert.equal(attrs.get("data-hcc-formio-select-ready"), "1");
});

test("tải từ xa theo từ khoá rồi chọn ĐÚNG option, không lấy option ngắn nằm lọt trong giá trị", async () => {
  const { comp, request } = setup({ server: ["Xe taxi", TAI, "Xe buýt"], initial: [{ value: { ten: "Xe taxi" }, label: "Xe taxi" }] });
  const res = await request(TAI);
  assert.equal(res.handled, true);
  assert.equal(res.ok, true);
  assert.equal(res.label, TAI);
  assert.equal(comp.searches[0].term, TAI);
  assert.equal(comp.searches[0].force, true);
  assert.equal(comp.setCalls.length, 1);
  assert.equal(comp.setCalls[0].ten, TAI, "setValue phải nhận đúng value object của option thật");
});

test("danh sách từ xa không có option khớp → handled, để trống, KHÔNG chọn 'Xe taxi'", async () => {
  const { comp, request } = setup({ server: ["Xe taxi", "Xe buýt"] });
  const res = await request(TAI);
  assert.equal(res.handled, true);
  assert.equal(res.ok, false);
  assert.equal(comp.setCalls.length, 0);
  assert.equal(comp.searches.at(-1).term, "", "lượt cuối tải danh sách mặc định không từ khoá");
});

test("danh sách mặc định (không từ khoá) cứu được khi server không tìm ra theo từ khoá", async () => {
  const { comp, request } = setup({ server: ["Hợp tác xã", "Liên hiệp hợp tác xã"], caseSensitive: true });
  const res = await request("hợp tác xã");
  assert.equal(res.ok, true);
  assert.equal(res.label, "Hợp tác xã");
  assert.equal(comp.searches.at(-1).term, "");
  assert.equal(comp.setCalls.length, 1);
});

test("option tốt nhất ở danh sách đã bị thay → nạp lại danh sách đó trước setValue", async () => {
  const { comp, request } = setup({ server: ["Sở Xây dựng tỉnh Quảng Trị", "Sở Xây dựng tỉnh Quảng Ngãi"] });
  const res = await request("Quảng Trị");
  assert.equal(res.ok, true);
  assert.deepEqual(comp.searches.map((s) => s.term), ["Quảng Trị", "", "Quảng Trị"]);
  assert.equal(comp.setCalls[0].ten, "Sở Xây dựng tỉnh Quảng Trị");
  assert.ok(comp.selectOptions.some((o) => o.value.ten === "Sở Xây dựng tỉnh Quảng Trị"));
});

test("khớp theo ranh giới từ: 'Viet' không khớp 'Soviet Union'", async () => {
  const { request } = setup({ server: ["Soviet Union", "Viet Nam"] });
  const res = await request("Viet");
  assert.equal(res.label, "Viet Nam");
});

const opts = (labels, code = false) =>
  labels.map((label, i) => ({ value: code ? `MA_${i}` : { _id: `id${i}`, TenMuc: label }, label: `<span>${label}</span>` }));

test("nguồn custom (nạp sẵn): chọn thẳng trong selectOptions, KHÔNG gọi updateItems (gõ tìm làm cổng nạp lại)", async () => {
  const { comp, request } = setup({ dataSrc: "custom", initial: opts(["Công ty Cổ phần, TNHH, TNHH MTV", "Hợp tác xã", "Hộ kinh doanh"]) });
  const res = await request("Hợp tác xã");
  assert.equal(res.handled, true);
  assert.equal(res.ok, true);
  assert.equal(comp.searches.length, 0);
  assert.equal(comp.setCalls[0].TenMuc, "Hợp tác xã");
});

test("nguồn custom nạp trễ: chờ danh sách về rồi mới chọn", async () => {
  const { comp, request } = setup({ dataSrc: "custom", initial: [] });
  comp.choices = { showDropdown() {}, hideDropdown() {} };
  setTimeout(() => { comp.selectOptions = opts(["Tỉnh Quảng Ngãi", "Tỉnh Quảng Trị"]); }, 200);
  const res = await request("Tỉnh Quảng Trị");
  assert.equal(res.ok, true);
  assert.equal(comp.setCalls[0].TenMuc, "Tỉnh Quảng Trị");
});

test("ô nạp lười (panel Thêm phương tiện): mở dropdown MỘT lần qua Choices, KHÔNG gọi updateItems, rồi chọn", async () => {
  const { comp, request } = setup({ dataSrc: "custom", initial: [] });
  const calls = [];
  comp.choices = {
    showDropdown(preventFocus) {
      calls.push(["show", preventFocus]);
      setTimeout(() => { comp.selectOptions = opts(["Ô tô khách", "Ô tô tải", "Ô tô con"]); }, 40);
    },
    hideDropdown() { calls.push(["hide"]); },
  };
  const started = Date.now();
  const res = await request("Ô tô tải");
  assert.equal(res.ok, true);
  assert.equal(comp.searches.length, 0);
  assert.deepEqual(calls, [["show", true], ["hide"]]);
  assert.equal(comp.setCalls[0].TenMuc, "Ô tô tải");
  assert.ok(Date.now() - started < 1000, "danh sách về là chọn ngay, không chờ hết hạn");
});

test("nguồn custom không có option khớp → handled=true, để trống (không lùi về gõ DOM làm cổng nạp lại)", async () => {
  const { comp, request } = setup({ dataSrc: "custom", initial: opts(["Trắng", "Đen"]) });
  const started = Date.now();
  const res = await request("Bạc");
  assert.equal(res.handled, true);
  assert.equal(res.ok, false);
  assert.equal(res.reason, "no-match");
  assert.equal(comp.setCalls.length, 0);
  assert.ok(Date.now() - started < 500, "không có chỗ cuộn → không chờ trang kế");
});

test("JS custom đổ option vào Choices (selectOptions rỗng): mở dropdown, đọc kho Choices, chọn như cán bộ bấm", async () => {
  const { comp, request, select } = setup({ dataSrc: "custom", initial: [] });
  const { calls } = fakeChoices(comp, select, { pages: [["Ô tô khách", "Ô tô tải", "Ô tô con"]] });
  const started = Date.now();
  const res = await request("Ô tô tải");
  assert.equal(res.ok, true);
  assert.equal(res.label, "Ô tô tải");
  assert.equal(comp.dataValue, "id_Ô tô tải");
  assert.equal(comp.searches.length, 0, "không gọi updateItems");
  assert.equal(comp.setCalls.length, 0, "mục chỉ có trong Choices → không setValue");
  assert.deepEqual(calls.map((c) => c[0]), ["show", "hide", "pick"]);
  assert.ok(Date.now() - started < 1000);
});

test("mục nằm ở trang sau (không có tìm từ khoá): cuộn để cổng nạp trang kế tới khi thấy", async () => {
  const { comp, request, select } = setup({ dataSrc: "custom", initial: [] });
  const { calls } = fakeChoices(comp, select, { pages: [["Trắng", "Đen", "Đỏ"], ["Xanh", "Bạc"]] });
  const res = await request("Bạc");
  assert.equal(res.ok, true);
  assert.equal(comp.dataValue, "id_Bạc");
  assert.equal(calls.filter((c) => c[0] === "scroll").length, 1);
  assert.equal(calls.filter((c) => c[0] === "input").length, 0, "không gõ từ khoá khi cổng không tìm theo từ khoá");
});

test("JS custom có gửi keyword (Nước sản xuất): gõ từ khoá MỘT lần rồi chọn từ kết quả server", async () => {
  const { comp, request, select } = setup({ dataSrc: "custom", initial: [] });
  comp.component.data = { custom: "const body = { category: 'C_QuocGia' }; if (keyword) body.keyword = keyword;" };
  const { calls } = fakeChoices(comp, select, { pages: [["Afghanistan", "Albania"]], keywordResults: ["Viet Nam"] });
  const res = await request("Viet");
  assert.equal(res.ok, true);
  assert.equal(res.label, "Viet Nam");
  assert.deepEqual(calls.filter((c) => c[0] === "input"), [["input", "Viet"]]);
});

test("nguồn values lưu MÃ: khớp theo nhãn hoặc theo mã, setValue nhận mã", async () => {
  const { comp, request } = setup({ dataSrc: "values", initial: opts(["Xe taxi", "Xe buýt"], true) });
  const res = await request("Xe buýt");
  assert.equal(res.ok, true);
  assert.equal(comp.setCalls[0], "MA_1");
});

test("danh sách nạp sẵn không có option khớp → handled=false, đường DOM cũ xử lý như trước", async () => {
  const { comp, request } = setup({ dataSrc: "values", initial: opts(["Xe taxi", "Xe buýt"], true) });
  const res = await request(TAI);
  assert.equal(res.handled, false);
  assert.equal(res.reason, "no-match");
  assert.equal(comp.setCalls.length, 0);
});

test("select nhiều nạp sẵn: THAY toàn bộ mục đang chọn bằng các mục cần điền", async () => {
  const { comp, request } = setup({
    dataSrc: "custom",
    multiple: true,
    initial: opts(["Kinh doanh vận tải hành khách công cộng bằng xe buýt", "Kinh doanh vận tải hàng hóa bằng xe ô tô"]),
  });
  comp.setValue = function (value) { this.setCalls.push(value); this.dataValue = value.map((v) => ({ ...v })); };
  const res = await request("Kinh doanh vận tải hàng hóa bằng xe ô tô");
  assert.equal(res.ok, true);
  assert.equal(comp.setCalls[0].length, 1);
  assert.equal(comp.setCalls[0][0].TenMuc, "Kinh doanh vận tải hàng hóa bằng xe ô tô");
});

test("nguồn từ xa nhưng select nhiều / nguồn lạ → handled=false", async () => {
  for (const o of [{ multiple: true }, { dataSrc: "indexeddb" }]) {
    const { comp, request } = setup({ ...o, server: [TAI] });
    const res = await request(TAI);
    assert.equal(res.handled, false);
    assert.equal(comp.searches.length, 0);
  }
});

test("content.js hỏi cầu nối TRƯỚC đường searchOnce/DOM, trừ ô Tỉnh/Xã", () => {
  const branch = contentSource.slice(contentSource.indexOf('} else if (f.comp === "dom-select") {'));
  const viaMain = branch.indexOf("fillFormioRemoteSelectViaMain(el, f.value)");
  const searchOnce = branch.indexOf("fillChoicesSearchOnce(el, f.value)");
  assert.ok(viaMain > 0 && viaMain < searchOnce);
  assert.match(branch.slice(0, viaMain), /if \(!isAreaSelectField\(f\)\)/);
  assert.match(branch, /if \(viaMain\?\.handled\) \{\s*ok = !!viaMain\.ok;/);
});

test("manifest nạp cầu nối ở MAIN world trên đúng các cổng của content script chính; popup re-inject cả nó", () => {
  const entry = manifest.content_scripts.find((cs) => (cs.js || []).includes("content/formio-select-main.js"));
  assert.ok(entry);
  assert.equal(entry.world, "MAIN");
  assert.equal(entry.all_frames, true);
  assert.deepEqual(entry.matches, manifest.content_scripts[0].matches);
  assert.match(popupSource, /world: "MAIN",[\s\S]{0,200}files: \[[^\]]*"content\/formio-select-main\.js"/);
});
