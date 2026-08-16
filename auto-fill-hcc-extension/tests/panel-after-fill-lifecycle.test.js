const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const popupSource = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

const helperStart = popupSource.indexOf("function hasMeaningfulFieldValue(field)");
const helperEnd = popupSource.indexOf("\nasync function dispatchFill", helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "Không tách được rule dữ liệu dùng được");

const sandbox = {};
vm.runInNewContext(`
  ${popupSource.slice(helperStart, helperEnd)}
  globalThis.hasUsableProcessData = hasUsableProcessData;
  globalThis.buildFillDetails = buildFillDetails;
`, sandbox);

assert.equal(sandbox.hasUsableProcessData([]), false);
assert.equal(sandbox.hasUsableProcessData([{ name: "a", value: "", default: false }]), false);
assert.equal(sandbox.hasUsableProcessData([{ name: "a", value: "mặc định", default: true }]), false);
assert.equal(sandbox.hasUsableProcessData([{ name: "a", value: "Nguyễn Văn A" }]), true);
assert.equal(sandbox.hasUsableProcessData([{ name: "a", value: 0 }]), true);
assert.equal(sandbox.hasUsableProcessData([{ name: "a", value: false }]), true);

const details = sandbox.buildFillDetails(
  { filled: 18, notFound: ["field_a", "field_a", "lỗi có khoảng trắng"], errors: ["raw"] },
  ["raw OCR"],
  21,
);
assert.deepEqual(
  Array.from(details),
  [
    "Có 3 thông tin chưa được điền.",
    "Mã ô hỗ trợ: field_a.",
    "Có 1 cảnh báo khi điền biểu mẫu.",
    "Có 1 cảnh báo khi đọc hồ sơ.",
  ],
);

const dispatchStart = popupSource.indexOf("async function dispatchFill");
const dispatchEnd = popupSource.indexOf("\n// ===== Rà soát bbox", dispatchStart);
const dispatchSource = popupSource.slice(dispatchStart, dispatchEnd);
const minimizeIndex = dispatchSource.indexOf('action: "minimizePanelForFill"');
const fillIndex = dispatchSource.indexOf('action: "fillFields"');
const completeIndex = dispatchSource.indexOf('action: "markPanelFillComplete"');
assert.ok(minimizeIndex >= 0 && minimizeIndex < fillIndex, "Phải thu nhỏ panel trước khi bắt đầu fill DOM");
assert.ok(fillIndex < completeIndex, "Chỉ arm tự mở màn đính kèm sau khi fill kết thúc");
assert.match(dispatchSource, /filled === 0[\s\S]*?restorePanelAfterFillFailure/);
assert.match(dispatchSource, /Đã điền \$\{filled\} thông tin/);
assert.doesNotMatch(dispatchSource, /\$\{filled\}\s*\/\s*\$\{allFields\.length\}/);

assert.match(contentSource, /const SS_AUTO_MIN = "__af_panel_auto_min"/);
assert.match(contentSource, /phase: "filling"/);
assert.match(contentSource, /phase: "filled"/);
assert.match(contentSource, /state\.phase !== "filled" \|\| !hasAttachmentTarget\(\)/);
assert.match(contentSource, /restorePanel\(\); \/\/ đồng thời xoá cờ → chỉ tự mở đúng một lần/);
assert.match(contentSource, /location\.hostname\.includes\("hokinhdoanh\.dkkd\.gov\.vn"\)/);
assert.match(contentSource, /minimizePanel\(\{ preserveAuto: true \}\)/);

async function testDispatchRuntime() {
  const events = [];
  const runtime = {
    console: { warn: (...args) => events.push(["warn", ...args]) },
    currentUser: null,
    currentConfig: () => ({ key: "procedure-a" }),
    buildBusinessDefaults: () => null,
    setStatus: (message, type, detailItems = []) => events.push(["status", message, type, detailItems]),
    showPageToast: async (message, kind) => runtime.sendToContent({ action: "showPageToast", message, kind }),
    sendToContent: async (payload) => {
      events.push(["action", payload.action]);
      if (payload.action === "minimizePanelForFill") return { ok: true, minimized: true };
      if (payload.action === "fillFields") return runtime.fillResponse;
      return { ok: true };
    },
    fillResponse: { filled: 1, notFound: ["field_b"], errors: [] },
  };
  vm.runInNewContext(`
    ${popupSource.slice(helperStart, dispatchEnd)}
    globalThis.dispatchFill = dispatchFill;
  `, runtime);

  await runtime.dispatchFill([
    { name: "field_a", value: "A" },
    { name: "field_b", value: "B" },
  ], []);
  assert.deepEqual(
    events.filter((event) => event[0] === "action").map((event) => event[1]),
    ["minimizePanelForFill", "fillFields", "showPageToast", "markPanelFillComplete"],
  );
  const partialStatus = events.findLast((event) => event[0] === "status");
  assert.equal(partialStatus[1], "Đã điền 1 thông tin. Vui lòng rà soát các ô còn trống.");
  assert.equal(partialStatus[2], "warn");

  events.length = 0;
  runtime.fillResponse = { filled: 0, notFound: ["field_a"], errors: [] };
  await runtime.dispatchFill([{ name: "field_a", value: "A" }], []);
  assert.deepEqual(
    events.filter((event) => event[0] === "action").map((event) => event[1]),
    ["minimizePanelForFill", "fillFields", "restorePanelAfterFillFailure"],
  );
  assert.equal(events.findLast((event) => event[0] === "status")[2], "err");

  events.length = 0;
  await runtime.dispatchFill([{ name: "default_a", value: "A", default: true }], []);
  assert.deepEqual(events.filter((event) => event[0] === "action"), []);
}

testDispatchRuntime().then(() => {
  console.log("panel after-fill lifecycle: usable data, action order and recovery passed");
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
