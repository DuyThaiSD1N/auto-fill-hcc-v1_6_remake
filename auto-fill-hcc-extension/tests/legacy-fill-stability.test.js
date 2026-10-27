const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

assert.doesNotMatch(
  source,
  /await sleep\(400\);\s*await reapplyEmptyTextFields/,
  "Không được chờ cứng 400ms trước pass ổn định của mọi hồ sơ"
);
assert.match(source, /await sleep\(120\);\s*const repaired = await repairLostLegacyFields\(fields, filledNames\)/);
assert.match(source, /function armLegacyStabilityGuard\(fields, filledNames\)/);
assert.match(source, /new MutationObserver\(\(\) => schedule\(\)\)/);
assert.match(source, /\[350, 1000, 1800\]/, "Guard phải có checkpoint bắt reset value không đổi DOM");
assert.match(
  source,
  /!eligibleNames \|\| eligibleNames\.has\(field\.name\)/,
  "Chỉ retry field từng điền thành công để không tốn thời gian với option không tồn tại"
);
assert.match(source, /refreshRequestedLegacyMarks\(fields\)/, "Màu phải được tính lại từ giá trị cuối");

const helperStart = source.indexOf("const LEGACY_REPAIRABLE_COMPS");
const helperEnd = source.indexOf("\nfunction findLegacyRadioTarget", helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "Không tách được helper so khớp legacy");
const sandbox = {
  norm: (value) => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase(),
};
vm.runInNewContext(`
  ${source.slice(helperStart, helperEnd)}
  globalThis.scalarMatches = legacyScalarMatches;
  globalThis.choiceMatches = legacyChoiceMatches;
`, sandbox);

assert.equal(sandbox.scalarMatches("012 147 000 040", "012147000040"), true);
assert.equal(sandbox.scalarMatches("04", "4"), true);
assert.equal(sandbox.scalarMatches("Vũ Đình Tuyến", "VŨ ĐÌNH TUYẾN"), true);
assert.equal(sandbox.scalarMatches("", "VŨ ĐÌNH TUYẾN"), false);
assert.equal(sandbox.choiceMatches("-- Chọn --", "Việt Nam"), false);
assert.equal(sandbox.choiceMatches("Thẻ căn cước công dân", "Căn cước công dân"), true);

console.log("legacy fill stability: adaptive retry and final-value marks passed");
