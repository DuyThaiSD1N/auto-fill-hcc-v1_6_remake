const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = source.indexOf("function isOwnerDossierCheckboxField(field)");
const end = source.indexOf("\n  async function fillFormStandard(fields)", start);

assert.ok(start >= 0 && end > start, "Không tách được helper sắp thứ tự người nộp/chủ hồ sơ");

const sandbox = {
  fieldCandidates: (field) => [field.name, ...(field.aliases || [])],
  isPostbackAddressField: (field) => field.area === true,
};

vm.runInNewContext(`
  ${source.slice(start, end)}
  globalThis.orderFields = orderStandardFields;
`, sandbox);

const selfSubmit = [
  { name: "data[ownerFullname]", comp: "dom-input" },
  { name: "data[isOwnerDossier]", comp: "dom-checkbox", value: true },
  { name: "data[fullname]", comp: "dom-input" },
  { name: "data[province]", comp: "dom-select", area: true },
];

assert.deepEqual(
  Array.from(sandbox.orderFields(selfSubmit), (field) => field.name),
  ["data[ownerFullname]", "data[fullname]", "data[province]", "data[isOwnerDossier]"],
  "Phải tick người nộp là chủ hồ sơ sau khi đã điền xong người nộp và địa chỉ",
);

const represented = [
  { name: "data[ownerFullname]", comp: "dom-input" },
  { name: "data[isOwnerDossierCheck]", comp: "dom-checkbox", value: false },
  { name: "data[fullname]", comp: "dom-input" },
];

assert.deepEqual(
  Array.from(sandbox.orderFields(represented), (field) => field.name),
  ["data[isOwnerDossierCheck]", "data[ownerFullname]", "data[fullname]"],
  "Phải bỏ tick trước để mở phần chủ hồ sơ khi người nộp là người đại diện",
);

console.log("owner dossier fill order: false first, true last passed");
