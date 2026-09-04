const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const settingsHtml = fs.readFileSync(path.join(root, "settings.html"), "utf8");
const settings = fs.readFileSync(path.join(root, "settings.js"), "utf8");

assert.doesNotMatch(html, /id="splitDocumentsToggle"/);
assert.match(
  html,
  /id="guideBtn"[\s\S]*?id="settingsBtn"/,
  "Bánh răng cài đặt phải nằm cạnh nút Hướng dẫn"
);
assert.match(popup, /chrome\.runtime\.getURL\("settings\.html"\)/);

assert.match(settingsHtml, /<title>Cài đặt extension<\/title>/);
assert.match(settingsHtml, /id="splitDocumentsSetting" type="checkbox"/);
assert.doesNotMatch(settingsHtml, /id="splitDocumentsSetting"[^>]*\bchecked\b/);
assert.match(settingsHtml, /Có tách hồ sơ khi đính kèm/);
assert.match(settingsHtml, /Hai mặt CCCD cùng chủ thể vẫn được gộp thành một tài liệu/);

assert.match(settings, /const SPLIT_DOCUMENTS_SETTING_KEY = "autofill_attach_split_documents"/);
assert.match(settings, /chrome\.storage\.local\.get\(\{ \[SPLIT_DOCUMENTS_SETTING_KEY\]: false \}\)/);
assert.match(
  settings,
  /\[SPLIT_DOCUMENTS_SETTING_KEY\]: splitDocumentsSetting\.checked === true/
);

assert.match(popup, /const SPLIT_DOCUMENTS_SETTING_KEY = "autofill_attach_split_documents"/);
assert.match(popup, /await restoreSplitDocumentsSetting\(\)/);
assert.match(popup, /chrome\.storage\.onChanged\.addListener/);
assert.match(popup, /options\.splitDocuments = !!attachSplitDocuments/);
assert.match(popup, /let attachSplitDocuments = false/);

const splitModeSet = popup.match(/const SPLIT_MODE_PROCEDURES = new Set\(\[([^\]]*)\]\)/);
assert.ok(splitModeSet, "Không tìm thấy danh sách thủ tục tách nhiều hồ sơ/tab");
assert.doesNotMatch(splitModeSet[1], /ket-hon/, "Kết hôn không được dùng nhầm splitMode đa-tab");

const multiTabBranch = popup.match(
  /if \(attachSplitMode && isSplitEligibleProcedure\(\) && sendFiles\.length > 1\)/
);
assert.ok(multiTabBranch, "Luồng đa-tab phải tiếp tục chỉ phụ thuộc splitMode cũ");
assert.doesNotMatch(multiTabBranch[0], /attachSplitDocuments/);

console.log("marriage document split setting: standalone page, default off and no multi-tab passed");
