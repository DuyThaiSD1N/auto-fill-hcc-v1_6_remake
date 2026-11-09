const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

assert.doesNotMatch(source, /_areaSelectDeadline|_areaBudgetLeft/);
assert.match(source, /const STANDARD_AREA_FIELD_BUDGET_MS = 5000;/);
assert.match(source, /fillStandardSelectAll\(candidates, f\.value, occurrence, deadline, root\)/);
assert.match(source, /fillStandardSelectAny\(sel, value, names, occurrence, deadline, root\)/);
assert.match(source, /fillFormioSelectComponent\(el, value, names, deadline\)/);
assert.match(source, /pickChoicesItem\(el, value, deadline\)/);

const start = source.indexOf("function standardFieldIdentity(field)");
const end = source.indexOf("\n  // Chỉ kết luận", start);
assert.ok(start >= 0 && end > start, "Không tách được helper ngân sách dropdown");

let now = 1_000;
const sandbox = {
  Date: { now: () => now },
  fieldCandidates: (field) => [field.name],
  standardOccurrence: (value) => Number.isInteger(value) && value >= 0 ? value : null,
  STANDARD_AREA_FIELD_BUDGET_MS: 5_000,
};
vm.runInNewContext(`
  ${source.slice(start, end)}
  globalThis.identity = standardFieldIdentity;
  globalThis.deadline = standardFieldDeadline;
`, sandbox);

const first = { name: "data[province]", occurrence: 0 };
const second = { name: "data[province]", occurrence: 1 };
assert.notEqual(sandbox.identity(first), sandbox.identity(second));

const budgets = new Map();
assert.equal(sandbox.deadline(budgets, first), 6_000);

// Ô occurrence=0 đã hết 5 giây không được làm occurrence=1 mất ngân sách.
now = 6_200;
assert.equal(sandbox.deadline(budgets, first), 6_000);
assert.equal(sandbox.deadline(budgets, second), 11_200);
assert.equal(budgets.size, 2);

console.log("standard select budget: independent name + occurrence deadlines passed");

// Đổi Tỉnh xong, ô Xã còn danh sách tỉnh CŨ (cổng Lai Châu nạp lại bằng AJAX) → coi là đang nạp, không dừng sớm.
assert.match(source, /const awaitingCascade = plainNativeSource && standardSelectAwaitingCascade\(select\);/);
assert.match(source, /states\.every\(\(state\) => state\.awaitingCascade && !state\.hasValue\)/);
assert.match(source, /const cascade = snapshotStandardAreaCascade\(candidates, occurrence, root\);/);
assert.match(source, /if \(ok\) commitStandardAreaCascade\(cascade\);/);

const cascadeStart = source.indexOf("  const STANDARD_AREA_CASCADE_RELOAD_MS");
const cascadeEnd = source.indexOf("  function isPostbackAddressField(f)", cascadeStart);
assert.ok(cascadeStart >= 0 && cascadeEnd > cascadeStart, "Không tách được helper chờ danh sách xã nạp lại");

const fakeSelect = (name, values) => ({ name, id: "", value: values[0], options: values.map((value) => ({ value })) });
const tinh = fakeSelect("CongDan_maTinhThanh", ["01", "12"]);
const xa = fakeSelect("CongDan_maPhuongXa", ["hn1", "hn2", "hn3"]);
const hoTen = fakeSelect("CongDan_gioiTinhCongDan", ["0", "1"]);
let clock = 50_000;
const cascadeBox = {
  Date: { now: () => clock },
  Map,
  document: { querySelectorAll: () => [tinh, xa, hoTen] },
  findStandardSelects: (names) => [tinh, xa, hoTen].filter((sel) => names.includes(sel.name)),
  isAreaSelectName: (name) => /matinh|maphuongxa/.test(String(name || "").toLowerCase()),
};
vm.runInNewContext(`
  ${source.slice(cascadeStart, cascadeEnd)}
  globalThis.snap = snapshotStandardAreaCascade;
  globalThis.commit = commitStandardAreaCascade;
  globalThis.awaiting = standardSelectAwaitingCascade;
`, cascadeBox);

// Chọn lại đúng tỉnh đang có → không đánh dấu gì.
cascadeBox.commit(cascadeBox.snap(["CongDan_maTinhThanh"], null, null));
assert.equal(cascadeBox.awaiting(xa), false);

// Đổi Hà Nội → Lai Châu: ô Xã còn danh sách Hà Nội là ĐANG NẠP; ô không thuộc địa bàn không bị đụng.
const snapshot = cascadeBox.snap(["CongDan_maTinhThanh"], null, null);
tinh.value = "12";
cascadeBox.commit(snapshot);
assert.equal(cascadeBox.awaiting(xa), true);
assert.equal(cascadeBox.awaiting(tinh), false);
assert.equal(cascadeBox.awaiting(hoTen), false);

// Cổng nạp xong danh sách Lai Châu → hết chờ, quay về luật "đã ổn định" như cũ.
xa.options = ["lc1", "lc2"].map((value) => ({ value }));
assert.equal(cascadeBox.awaiting(xa), false);

// Cổng không bao giờ nạp lại → hết hạn chờ thì cũng thôi.
xa.options = ["hn1", "hn2", "hn3"].map((value) => ({ value }));
assert.equal(cascadeBox.awaiting(xa), true);
clock += 8_001;
assert.equal(cascadeBox.awaiting(xa), false);

console.log("standard select cascade: ward list of the old province waits for reload passed");
