const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

const helperStart = source.indexOf('const LEGACY_BIRTH_RELATION_NAME = "quanhe"');
const helperEnd = source.indexOf("\nfunction legacyScalarMatches", helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "Không tách được helper sắp thứ tự QuanHe");
assert.match(
  source,
  /window\.__TLND__\s*\|\|\s*\(window\.__TLND__\s*=\s*\{\}\)/,
  "Engine legacy phải đăng ký đúng namespace của Trợ lý nhân dân",
);

const sandbox = {
  fieldCandidates: (field) => [field.name, ...(field.aliases || [])],
};
vm.runInNewContext(`
  ${source.slice(helperStart, helperEnd)}
  globalThis.orderFields = orderLegacyFields;
`, sandbox);

const lateRelation = [
  { name: "LoaiDangKy", comp: "x-radio" },
  { name: "HoVaTenC", comp: "x-input" },
  { name: "HoTenKS", comp: "x-input" },
  { name: "NgaySinhChon", comp: "x-input" },
  { name: "HoTenMeKS", comp: "x-input" },
  { name: "QuanHe", comp: "x-radio", value: "ChaDe" },
  { name: "HoTenChaKS", comp: "x-input" },
];

assert.deepEqual(
  Array.from(sandbox.orderFields(lateRelation), (field) => field.name),
  ["LoaiDangKy", "HoVaTenC", "QuanHe", "HoTenKS", "NgaySinhChon", "HoTenMeKS", "HoTenChaKS"],
  "QuanHe phải được chọn sau người yêu cầu nhưng trước con/cha/mẹ",
);

const alreadyEarly = [
  { name: "QuanHe", comp: "x-radio", value: "MeDe" },
  { name: "HoVaTenC", comp: "x-input" },
  { name: "HoTenKS", comp: "x-input" },
];
assert.deepEqual(
  Array.from(sandbox.orderFields(alreadyEarly), (field) => field.name),
  alreadyEarly.map((field) => field.name),
  "Không được đảo lại response đã có QuanHe ở trước field phụ thuộc",
);

const unrelated = [
  { name: "QuanHe", comp: "x-radio" },
  { name: "NguoiMat_HoTen", comp: "x-input" },
];
assert.deepEqual(
  Array.from(sandbox.orderFields(unrelated), (field) => field.name),
  unrelated.map((field) => field.name),
  "Không được đổi thứ tự QuanHe của thủ tục không phải khai sinh",
);

assert.match(
  source,
  /if \(target\.checked\) \{[\s\S]*?return true;[\s\S]*?target\.click\(\);/,
  "Radio đã chọn sẵn phải thoát sớm, không phát change làm reset form",
);
assert.match(
  source,
  /if \(!isBirthRelation\) \{[\s\S]*?target\.checked = true;[\s\S]*?target\.dispatchEvent/,
  "Radio thủ tục khác phải giữ nguyên hành vi cũ",
);
assert.match(
  source,
  /birthRelationshipForm[\s\S]*?legacyFieldHasName\(field, LEGACY_BIRTH_RELATION_NAME\)[\s\S]*?isBirthRelationDriver \? 350 : 200/,
  "QuanHe phải có nhịp chờ riêng trước khi điền con/cha/mẹ",
);
assert.match(
  source,
  /if \(isBirthRelationshipForm\) armLegacyStabilityGuard/,
  "Stability guard chỉ được bật cho mẫu khai sinh có QuanHe",
);
assert.match(
  source,
  /if \(isBirthRelationshipForm\) \{[\s\S]*?repairLostLegacyFields[\s\S]*?\} else \{[\s\S]*?reapplyEmptyTextFields/,
  "Thủ tục khác phải tiếp tục dùng pass fill cũ",
);

console.log("legacy birth relationship order: driver first and idempotent radio passed");
