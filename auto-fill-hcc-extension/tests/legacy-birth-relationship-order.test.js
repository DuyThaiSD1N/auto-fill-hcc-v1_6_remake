const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

const helperStart = source.indexOf('const LEGACY_BIRTH_RELATION_NAME = "quanhe"');
const helperEnd = source.indexOf("\nfunction legacyScalarMatches", helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "Không tách được helper sắp thứ tự QuanHe");

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
  { name: "NgaySinhChon", comp: "x-date" },
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
assert.doesNotMatch(
  source,
  /target\.click\(\);\s*target\.checked = true;\s*target\.dispatchEvent/,
  "Không được phát change trùng ngay sau click",
);
assert.match(
  source,
  /isLegacyRelationDriver\(field\) \? 350 : 200/,
  "Ô tích quan hệ phải có nhịp chờ riêng trước khi điền khối nhân thân",
);
assert.match(
  source,
  /LEGACY_RELATION_NAMES = \[LEGACY_BIRTH_RELATION_NAME, "nyc_quanhe"/,
  "Ô tích quan hệ của trích lục (NYC_QuanHe) cũng phải được coi là driver",
);
assert.match(
  source,
  /if \(!isBirthRelation\) \{[\s\S]*?b\.dispatchEvent\(new Event\("change"/,
  "QuanHe không được change option cũ rồi mới click option mới",
);

console.log("legacy birth relationship order: driver first and idempotent radio passed");
