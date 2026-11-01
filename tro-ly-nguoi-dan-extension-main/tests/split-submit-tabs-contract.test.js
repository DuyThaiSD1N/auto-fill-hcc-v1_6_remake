// Đính tách nhiều tab: BE chỉ mời đánh giá khi mọi tab đã nộp → extension phải gửi MÃ TAB kèm
// cú bấm / event submitted và báo tab tách bị đóng.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const background = strip(fs.readFileSync(path.join(root, "background.js"), "utf8"));

test("sidebar khai cờ supportsSplitSubmitTabs", () => {
  assert.match(sidebar, /supportsSplitSubmitTabs: true/);
});

test("cú bấm nộp gửi mã tab: tab gốc = TAB_ID, tab tách = splitTabId do background chuyển", () => {
  assert.match(sidebar, /let clickTabId = Number\(TAB_ID\) \|\| 0;/);
  assert.match(sidebar, /submitClickedRelay"\) \{[\s\S]{0,40}?clickTabId = Number\(msg\.splitTabId\) \|\| 0;/);
  assert.match(sidebar, /__event:submit_clicked:[\s\S]*?tab_id: clickTabId/);
  assert.match(background, /__tlnd: "submitClickedRelay", originTabId, splitTabId: tabId/);
});

test("event submitted của tab gốc mang mã tab", () => {
  assert.match(sidebar, /__event:submitted:\$\{JSON\.stringify\(\{ tab_id: Number\(TAB_ID\) \|\| 0 \}\)\}/);
});

test("tab tách đóng → báo sidebar tab gốc, đọc bản đồ trước khi xoá", () => {
  assert.match(background, /onRemoved\.addListener\(\(tabId\) => \{\s*void relaySplitTabClosed\(tabId\);\s*void forgetSplitTabOrigin/);
  assert.match(background, /__tlnd: "splitTabClosedRelay", originTabId, splitTabId: tabId/);
  assert.match(sidebar, /__tlnd === "splitTabClosedRelay"[\s\S]*?String\(msg\.originTabId \|\| ""\) !== String\(TAB_ID\)[\s\S]*?__event:split_tab_closed:/);
});
