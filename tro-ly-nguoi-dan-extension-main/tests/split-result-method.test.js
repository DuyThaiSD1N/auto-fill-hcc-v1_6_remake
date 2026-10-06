// Tách nhiều hồ sơ (chứng thực bản sao): hồ sơ 2…N cũng được gạt sẵn "bản giấy có đóng dấu" ở
// bước Thông tin nhận kết quả. Hồ sơ chính do sidebar gạt theo lệnh BE; tab tách chạy khung hồ sơ
// phụ CHỈ ĐỌC nên nhận lệnh gạt qua thông tin tab (BE → sidebar → background → companion) rồi tự
// gạt trên chính trang của nó — và KHÔNG được đè lựa chọn công dân đã tự đổi.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const LENH = {
  method: "paper",
  label: "Nhận kết quả bản giấy có đóng dấu",
  allLabels: ["Nhận kết quả bản giấy có đóng dấu", "Nhận kết quả trực tuyến", "Dịch vụ bưu chính công ích"],
  needsInput: false,
  options: [
    { key: "paper", label: "Nhận kết quả bản giấy có đóng dấu", icon: "📄", desc: "Bản giấy", needsInput: false },
    { key: "online", label: "Nhận kết quả trực tuyến", icon: "🌐", desc: "Bản điện tử", needsInput: false },
    { key: "postal", label: "Dịch vụ bưu chính công ích", icon: "📮", desc: "Bưu điện trả", needsInput: true },
  ],
};

// ── Engine gạt công tắc: chạy thật selectResultMethod với công tắc giả ──
function loadEngine(state) {
  const src = read("content/portal-dvc.js");
  const start = src.indexOf("  async function selectResultMethod(");
  const end = src.indexOf("  chrome.runtime.onMessage.addListener", start);
  const ctx = {
    fold: (s) => String(s || "").toLowerCase(),
    sleep: async () => {},
    resultSwitchByLabel: (label) => (label in state ? { label } : null),
    resultSwitchOn: (sw) => state[sw.label] === true,
    setResultSwitch: async (sw, on) => { state[sw.label] = on; return true; },
    missingResultFields: () => [],
  };
  vm.createContext(ctx);
  vm.runInContext(src.slice(start, end) + "\nthis.selectResultMethod = selectResultMethod;", ctx);
  return ctx.selectResultMethod;
}

const tatCa = () => Object.fromEntries(LENH.allLabels.map((l) => [l, false]));

test("chưa công tắc nào bật → gạt bản giấy", async () => {
  const state = tatCa();
  const res = await loadEngine(state)({ ...LENH, onlyIfUnset: true });
  assert.equal(res.ok, true);
  assert.notEqual(res.skipped, true);
  assert.equal(state[LENH.label], true);
});

test("công dân đã tự chọn bưu chính → onlyIfUnset KHÔNG đè", async () => {
  const state = { ...tatCa(), "Dịch vụ bưu chính công ích": true };
  const res = await loadEngine(state)({ ...LENH, onlyIfUnset: true });
  assert.equal(res.skipped, true);
  assert.equal(state["Dịch vụ bưu chính công ích"], true, "tắt lựa chọn của công dân là sai");
  assert.equal(state[LENH.label], false);
});

test("hồ sơ chính (không onlyIfUnset) giữ hành vi cũ: bật cái chọn, tắt cái khác", async () => {
  const state = { ...tatCa(), "Nhận kết quả trực tuyến": true };
  await loadEngine(state)({ ...LENH });
  assert.equal(state[LENH.label], true);
  assert.equal(state["Nhận kết quả trực tuyến"], false);
});

// ── Khung hồ sơ phụ: chạy thật gatSanKetQua ──
function loadCompanion({ resultMethod, replies }) {
  const src = read("companion.js");
  const start = src.indexOf("  const ngu = (ms)");
  const end = src.indexOf("  async function docBuocHienTai()", start);
  const sent = [];
  const appended = [];
  const el = () => {
    const node = { className: "", innerHTML: "", children: [], listeners: {} };
    node.appendChild = (c) => node.children.push(c);
    node.addEventListener = (t, fn) => { node.listeners[t] = fn; };
    return node;
  };
  const ctx = {
    BUOC_NHAN_KET_QUA: 4,
    theHoSo: { ordinal: 2, total: 4, resultMethod },
    setTimeout: (fn) => fn(),
    guiToiTrang: async (payload) => { sent.push(payload); return replies.shift() ?? null; },
    document: { createElement: el },
    $messages: { appendChild: (n) => appended.push(n) },
    window: { escapeHtml: (x) => String(x) },
    veCount: 0,
  };
  vm.createContext(ctx);
  vm.runInContext(
    "let daGatKetQua = false, ketQuaDangChon = '', dangDoiKetQua = false, loiVuaRoi = '';\n"
      + "async function ve() { veCount += 1; }\n"
      + src.slice(start, end)
      + "\nObject.assign(this, { gatSanKetQua, chonKetQua, veCardKetQua, baoDoiKetQua });"
      // defineProperty chứ không Object.assign: assign chép GIÁ TRỊ getter lúc nạp, không theo dõi.
      + "\nObject.defineProperty(this, 'state', { get() {"
      + " return { ketQuaDangChon, loiVuaRoi, daGatKetQua }; } });",
    ctx,
  );
  const api = { sent, appended };
  for (const k of ["gatSanKetQua", "chonKetQua", "veCardKetQua", "baoDoiKetQua"]) api[k] = ctx[k];
  Object.defineProperty(api, "state", { get: () => ctx.state });
  Object.defineProperty(api, "veCount", { get: () => ctx.veCount });
  return api;
}

test("khung phụ gạt ở bước 4, gửi onlyIfUnset, và chỉ gạt MỘT lần", async () => {
  const { gatSanKetQua, sent } = loadCompanion({ resultMethod: LENH, replies: [{ ok: true, missing: [] }] });
  const bao = await gatSanKetQua(4);
  assert.match(bao, /Em đã chọn sẵn \*\*Nhận kết quả bản giấy có đóng dấu\*\*/);
  assert.equal(sent.length, 1);
  assert.equal(sent[0].action, "selectResultMethod");
  assert.equal(sent[0].onlyIfUnset, true);
  assert.equal(await gatSanKetQua(4), "", "vẽ lại không được gạt lần hai");
  assert.equal(sent.length, 1);
});

test("khung phụ không gạt trước bước 4, và không gạt khi BE không gửi lệnh", async () => {
  const early = loadCompanion({ resultMethod: LENH, replies: [] });
  assert.equal(await early.gatSanKetQua(3), "");
  assert.equal(early.sent.length, 0, "đang ở bước đính kèm thì chưa có công tắc nào để gạt");
  const none = loadCompanion({ resultMethod: null, replies: [] });
  assert.equal(await none.gatSanKetQua(4), "");
  assert.equal(none.sent.length, 0, "bản BE cũ không gửi lệnh → giữ như cũ, công dân tự chọn");
});

test("trang chưa dựng xong công tắc → hỏi lại; vẫn hỏng thì báo và cho lượt sau thử lại", async () => {
  const slow = loadCompanion({ resultMethod: LENH, replies: [null, { ok: true, missing: [] }] });
  assert.match(await slow.gatSanKetQua(4), /Em đã chọn sẵn/);
  assert.equal(slow.sent.length, 2);
  const fail = loadCompanion({ resultMethod: LENH, replies: [null, null, null, null, { ok: true }] });
  assert.match(await fail.gatSanKetQua(4), /chưa chọn sẵn được/);
  assert.match(await fail.gatSanKetQua(4), /Em đã chọn sẵn/, "hỏng thì lượt vẽ sau được thử lại");
});

test("công dân đã tự chọn → khung phụ im lặng", async () => {
  const { gatSanKetQua } = loadCompanion({ resultMethod: LENH, replies: [{ ok: true, skipped: true }] });
  assert.equal(await gatSanKetQua(4), "");
});

// ── Đường truyền lệnh: sidebar → background → thông tin tab ──
test("sidebar chuyển lệnh vào hàng đợi, background lưu vào thông tin tab tách", () => {
  const sidebar = strip(read("sidebar.js"));
  const start = sidebar.slice(sidebar.indexOf('action: "startSplitAttachQueue"'));
  assert.match(start.slice(0, 700), /resultMethod:\s*a\.resultMethod\s*\|\|\s*null/);
  const bg = strip(read("background.js"));
  assert.match(bg, /resultMethod:\s*cleanResultMethod\(msg\.resultMethod\)/);
  assert.match(bg, /resultMethod:\s*state\.resultMethod\s*\|\|\s*null/);
  const companion = strip(read("companion.js"));
  assert.match(companion, /const baoGatKetQua = await gatSanKetQua\(step\);/);
});

test("background chỉ giữ đúng các trường của lệnh gạt", () => {
  const src = read("background.js");
  const start = src.indexOf("function cleanResultMethod(");
  const end = src.indexOf("async function rememberSplitTabInfo(", start);
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(src.slice(start, end) + "\nthis.cleanResultMethod = cleanResultMethod;", ctx);
  assert.equal(ctx.cleanResultMethod(null), null);
  assert.equal(ctx.cleanResultMethod({ label: "" }), null);
  const out = ctx.cleanResultMethod({ ...LENH, type: "select_result_method", la: "<script>" });
  assert.deepEqual(Object.keys(out).sort(), ["allLabels", "label", "method", "needsInput", "options"]);
  assert.equal(out.label, LENH.label);
});

// ── Card 3 lựa chọn ở khung phụ ──
test("card chỉ hiện từ bước 4 và đánh dấu cách đang bật", async () => {
  const c = loadCompanion({ resultMethod: LENH, replies: [{ ok: true, missing: [] }] });
  c.veCardKetQua(3);
  assert.equal(c.appended.length, 0, "chưa tới bước nhận kết quả thì chưa có công tắc để chọn");
  await c.gatSanKetQua(4);
  c.veCardKetQua(4);
  const card = c.appended[0];
  assert.equal(card.className, "result-methods");
  assert.deepEqual(card.children.map((o) => o.className), ["opt picked", "opt", "opt"]);
});

test("bấm cách khác → gạt đúng công tắc, KHÔNG onlyIfUnset, đổi dấu chọn, vẽ lại", async () => {
  const c = loadCompanion({ resultMethod: LENH, replies: [{ ok: true, missing: [] }] });
  await c.chonKetQua(LENH.options[1]);
  assert.equal(c.sent[0].action, "selectResultMethod");
  assert.equal(c.sent[0].label, "Nhận kết quả trực tuyến");
  assert.deepEqual(c.sent[0].allLabels, LENH.allLabels, "phải kèm nhãn cả ba để tắt cái đang bật");
  assert.notEqual(c.sent[0].onlyIfUnset, true, "lựa chọn chủ động phải tắt được cái đang bật");
  assert.equal(c.state.ketQuaDangChon, "online");
  assert.equal(c.state.daGatKetQua, true, "đã chọn chủ động thì lượt vẽ sau không tự gạt đè");
  assert.match(c.state.loiVuaRoi, /Em đã chọn \*\*Nhận kết quả trực tuyến\*\* trên trang/);
  assert.equal(c.veCount, 1);
});

test("bấm lại đúng cách đang chọn → không gạt gì", async () => {
  const c = loadCompanion({ resultMethod: LENH, replies: [{ ok: true, missing: [] }] });
  await c.gatSanKetQua(4); // gạt sẵn bản giấy
  const truoc = c.sent.length;
  await c.chonKetQua(LENH.options[0]);
  assert.equal(c.sent.length, truoc);
});

test("câu báo sau khi đổi cách: bưu chính nhắc điền, thiếu ô thì nêu tên ô, hỏng thì bảo gạt tay", () => {
  const c = loadCompanion({ resultMethod: LENH, replies: [] });
  const postal = LENH.options[2];
  assert.match(c.baoDoiKetQua(postal, { ok: true, missing: [] }), /không điền hộ địa chỉ/);
  assert.match(c.baoDoiKetQua(postal, { ok: true, missing: ["Địa chỉ"] }), /Trang còn thiếu \*\*Địa chỉ\*\*/);
  assert.match(c.baoDoiKetQua(LENH.options[1], { ok: true, missing: [] }), /bấm \*\*Gửi hồ sơ\*\*/);
  assert.match(c.baoDoiKetQua(postal, { ok: false }), /chưa gạt được công tắc/);
});

test("công dân đã tự bật trên trang → card đánh dấu đúng cái đó", async () => {
  const c = loadCompanion({
    resultMethod: LENH, replies: [{ ok: true, skipped: true, current: "Dịch vụ bưu chính công ích" }],
  });
  await c.gatSanKetQua(4);
  assert.equal(c.state.ketQuaDangChon, "postal");
});

test("background giữ danh sách lựa chọn, lọc bỏ mục thiếu key/nhãn", () => {
  const src = read("background.js");
  const start = src.indexOf("function cleanResultMethod(");
  const end = src.indexOf("async function rememberSplitTabInfo(", start);
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(src.slice(start, end) + "\nthis.cleanResultMethod = cleanResultMethod;", ctx);
  const out = ctx.cleanResultMethod({ ...LENH, options: [...LENH.options, { key: "", label: "x" }] });
  assert.equal(out.options.length, 3);
  assert.deepEqual(Object.keys(out.options[2]).sort(), ["desc", "icon", "key", "label", "needsInput"]);
  assert.equal(out.options[2].needsInput, true);
});
