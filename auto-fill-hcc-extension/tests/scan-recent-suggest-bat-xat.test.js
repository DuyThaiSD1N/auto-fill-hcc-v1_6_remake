// Gợi ý tệp đã quét gần đây — CHỈ tài khoản xã Bát Xát, tắt được ở Cài đặt (mặc định bật).
// Quầy quét TRƯỚC rồi mới mở trợ lý: liệt kê tệp trong 2 giờ gần nhất chưa có trong hồ sơ để cán bộ
// tự chọn. KHÔNG tự thêm (nhánh đoán lô theo khoảng cách thời gian đã gỡ vì kéo nhầm giấy người khác).
// Chạy THẬT đoạn code của popup.js trong vm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const settingsJs = fs.readFileSync(path.join(root, "settings.js"), "utf8");
const settingsHtml = fs.readFileSync(path.join(root, "settings.html"), "utf8");
const popupHtml = fs.readFileSync(path.join(root, "popup.html"), "utf8");

const slice = (from, to) => {
  const i = popup.indexOf(from);
  const j = popup.indexOf(to, i);
  assert.ok(i >= 0 && j > i, `không tìm thấy đoạn ${from}`);
  return popup.slice(i, j);
};
const snippet = [
  slice("function normalizeProcedureSearch(", "\n}\n") + "\n}\n",
  slice("function isBatXatUser(", "\n}\n") + "\n}\n",
  slice("// ===== Gợi ý tệp đã quét gần đây", "function ensureScanAgentConnected() {"),
].join("\n");

function popupWith({ xa, enabled = true, disk, files = [], now = Date.parse("2026-10-09T08:00:00Z") }) {
  const store = {};
  const listEl = { hidden: true, textContent: "", children: [], appendChild(c) { this.children.push(c); } };
  const ctx = vm.createContext({
    console: { info() {}, warn() {} }, Date: Object.assign(function (v) { return new Date(v); }, { now: () => now, parse: Date.parse }),
    Number, String, Set, Math,
    EMBEDDED_TAB_ID: 7, files, currentUser: { xa }, scanRecentSuggestEnabled: enabled,
    scanRecentListEl: listEl,
    scanAgentHelpers: { listFiles: async () => ({ files: disk }) },
    chrome: { storage: { local: { set: (o) => Object.assign(store, o), get: async () => store } } },
    document: { createElement: () => ({ append() {}, addEventListener() {} }) },
  });
  vm.runInContext(`${snippet}\nthis.api = { attemptScanRecentSuggest, resetScanRecentSuggestState,
    pending: () => scanRecentPending, setNewest: (v) => { scanNewestMs = v; } };`, ctx);
  return { api: ctx.api, listEl, store };
}

const iso = (minAgo) => new Date(Date.parse("2026-10-09T08:00:00Z") - minAgo * 60000).toISOString();

test("tài khoản Bát Xát: liệt kê tệp ≤2 giờ, mới nhất trước, bỏ tệp đã có trong hồ sơ — không tự thêm", async () => {
  const disk = [
    { rel: "a.pdf", mtime: iso(5) }, { rel: "b.pdf", mtime: iso(90) },
    { rel: "cu.pdf", mtime: iso(150) }, { rel: "da-co.pdf", mtime: iso(3) },
  ];
  const files = [{ fromScan: true, rel: "da-co.pdf" }];
  const { api, listEl } = popupWith({ xa: "Xã Bát Xát", disk, files });
  await api.attemptScanRecentSuggest();
  assert.deepEqual(api.pending().map((f) => f.rel), ["a.pdf", "b.pdf"]);
  assert.equal(listEl.hidden, false);
  assert.equal(files.length, 1, "không tự thêm tệp nào vào hồ sơ");
});

test("xã khác, hoặc Bát Xát đã TẮT ở Cài đặt: không gợi ý", async () => {
  const disk = [{ rel: "a.pdf", mtime: iso(5) }];
  for (const opt of [{ xa: "Phường Yên Bái" }, { xa: "Xã Bát Xát", enabled: false }, { xa: "" }]) {
    const { api, listEl } = popupWith({ ...opt, disk });
    await api.attemptScanRecentSuggest();
    assert.equal(api.pending().length, 0, JSON.stringify(opt));
    assert.equal(listEl.hidden, true);
  }
});

test("Phiên mới: không gợi ý lại tệp của công dân trước (watermark)", async () => {
  const disk = [{ rel: "nguoi-truoc.pdf", mtime: iso(10) }, { rel: "nguoi-moi.pdf", mtime: iso(1) }];
  const { api, store } = popupWith({ xa: "Xã Bát Xát", disk });
  api.setNewest(Date.parse(iso(10))); // phiên trước đã nhận tệp quét lúc 10 phút trước
  api.resetScanRecentSuggestState();
  assert.equal(store.autofill_scan_watermark_7, Date.parse(iso(10)));
  await api.attemptScanRecentSuggest();
  assert.deepEqual(api.pending().map((f) => f.rel), ["nguoi-moi.pdf"]);
});

test("không còn nhánh tự thêm lô tệp có sẵn trên đĩa", () => {
  for (const dau of ["attemptBatchImport", "phanTichBatchGanNhat", "BATCH_AUTO_MAX_AGE_MS"]) {
    assert.ok(!popup.includes(dau), `popup.js còn "${dau}"`);
  }
  const fn = slice("async function addScanRecentItems(", "\n}\n");
  assert.ok(!/tuDong:\s*true/.test(fn), "chọn từ danh sách gợi ý phải là cán bộ bấm, không phải tự động");
});

test("gọi gợi ý ở chọn thủ tục + lúc nối máy quét; reset ở Phiên mới / đổi thủ tục / đăng xuất", () => {
  assert.match(popup, /ensureScanAgentConnected\(\);\s*\/\/[^\n]*\n\s*\/\/[^\n]*\n\s*void attemptScanRecentSuggest\(\);/);
  assert.match(popup, /await reconcileScanAgentFiles\(helpers\);\s*await attemptScanRecentSuggest\(\);/);
  assert.equal((popup.match(/resetScanRecentSuggestState\(\); \/\//g) || []).length, 3);
  assert.equal((popup.match(/await restoreScanWatermark\(\);/g) || []).length, 2);
  assert.match(popupHtml, /<div id="scanRecentList" class="scan-recent-list" hidden><\/div>/);
});

test("Cài đặt: công tắc chỉ hiện cho tài khoản Bát Xát, mặc định BẬT", () => {
  assert.match(settingsHtml, /<section id="scanRecentSection"[^>]* hidden>/);
  assert.match(settingsHtml, /<input id="scanRecentSuggestSetting" type="checkbox" checked>/);
  assert.match(settingsJs, /scanRecentSection\.hidden = !isBatXatAccount\(store\?\.\[LAST_USER_KEY\]\);/);
  assert.match(settingsJs, /store\?\.\[SCAN_RECENT_SUGGEST_KEY\] !== false/);
  assert.match(popup, /scanRecentSuggestEnabled = result\[SCAN_RECENT_SUGGEST_KEY\] !== false;/);
  for (const f of [popup, settingsJs]) assert.match(f, /"autofill_scan_recent_suggest"/);
  assert.match(popup, /LAST_USER_KEY = "autofill_last_user"/);
  assert.match(settingsJs, /LAST_USER_KEY = "autofill_last_user"/);
});
