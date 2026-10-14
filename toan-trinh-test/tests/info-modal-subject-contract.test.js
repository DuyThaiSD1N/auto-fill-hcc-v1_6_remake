const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const portal = fs.readFileSync(path.join(root, "content", "portal-dvc.js"), "utf8");

test("sidebar renders backend execution-subject options and sends only the selected key", () => {
  assert.match(sidebar, /card\.executionSubject/);
  assert.match(sidebar, /Đối tượng thực hiện/);
  assert.match(sidebar, /__action:set_execution_subject:/);
  assert.match(sidebar, /JSON\.stringify\(\{ key: o\.key \}\)/);
  assert.doesNotMatch(sidebar, /Người khác ủy quyền/);
});

test("chọn phường xã hoặc đối tượng không ép danh sách thủ tục cuộn xuống cuối", () => {
  assert.match(sidebar, /const preserveScroll = uiOptions\?\.preserveScroll === true/);
  assert.match(sidebar, /if \(!preserveScroll\) showTyping\(\)/);
  assert.match(
    sidebar,
    /__action:set_location:[\s\S]{0,300}\{ preserveScroll: true \}/,
  );
  assert.match(
    sidebar,
    /__action:set_execution_subject:[\s\S]{0,250}\{ preserveScroll: true \}/,
  );
  assert.match(sidebar, /requestAnimationFrame\(restorePreservedScroll\)/);
});

test("sidebar forwards the resolved backend contract to the portal content engine", () => {
  assert.match(sidebar, /action:\s*"confirmInfoModal"/);
  assert.match(sidebar, /executionSubject:\s*a\.executionSubject \|\| null/);
  assert.match(sidebar, /\[TLND-InfoModal\]\[sidebar\]/);
});

test("portal selects the exact subject inside the visible modal before confirming", () => {
  assert.match(portal, /infoSubjectCombobox\(dialog\)/);
  assert.match(portal, /leafByText\("Đối tượng thực hiện", dialog\)/);
  assert.match(portal, /button\[role="combobox"\]/);
  assert.match(portal, /await openAndCollect\(combobox\)/);
  assert.match(portal, /fold\(value\) === fold\(target\)/);
  assert.match(
    portal,
    /await selectInfoSubject\(dialog, executionSubject\)[\s\S]*clickLikeUser\(btn\)/,
  );
  assert.match(portal, /\[TLND-InfoModal\]/);
});

test("portal engine stays generic: backend owns business keys and option values", () => {
  assert.doesNotMatch(portal, /authorized_person/);
  assert.doesNotMatch(portal, /canhan/);
});
