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
    /await selectInfoSubject\(dialog, executionSubject\)[\s\S]*await clickUntilClosed\(dialog, btn\)/,
  );
  assert.match(portal, /async function clickUntilClosed\(dialog, btn\) \{[\s\S]*?clickLikeUser\(btn\);/);
  assert.match(portal, /\[TLND-InfoModal\]/);
});

test("portal engine stays generic: backend owns business keys and option values", () => {
  assert.doesNotMatch(portal, /authorized_person/);
  assert.doesNotMatch(portal, /canhan/);
});

test("modal Thông tin chung: chờ cổng nạp xong mới bấm, bấm lại tới khi modal đóng, chỉ báo ok khi đã đóng", () => {
  assert.match(portal, /const settled = await settleInfoCombos\(dialog\);/);
  assert.match(portal, /const result = await clickUntilClosed\(dialog, btn\);\s*if \(!result\.closed\) \{\s*throw new Error/);
  assert.match(portal, /return \{ ok: true, closed: true, clicks: result\.clicks/);
  assert.match(portal, /const INFO_CLOSE_MS = \d+;/);
});

test("sidebar: modal đã đóng thì báo trang ngay và mở lại hạn mức; hồ sơ mới đặt lại hạn mức", () => {
  assert.match(sidebar, /if \(res\?\.closed\) infoModalTries = 0;\s*else await new Promise\(\(r\) => setTimeout\(r, 1200\)\);/);
  assert.match(sidebar, /submittedReported = false;\s*infoModalTries = 0;/);
});
