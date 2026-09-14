const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

assert.doesNotMatch(source, /_areaSelectDeadline|_areaBudgetLeft/);
assert.match(source, /const STANDARD_AREA_FIELD_BUDGET_MS = 5000;/);
assert.match(source, /fillStandardSelectAll\(candidates, f\.value, occurrence, deadline\)/);
assert.match(source, /fillStandardSelectAny\(sel, value, names, occurrence, deadline\)/);
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
