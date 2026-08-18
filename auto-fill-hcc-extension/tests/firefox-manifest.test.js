const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

assert.equal(manifest.manifest_version, 3);
assert.deepEqual(
  manifest.background?.scripts,
  ["background.js"],
  "Firefox MV3 cần background.scripts vì chưa chạy background.service_worker",
);
assert.equal(
  manifest.background?.service_worker,
  "background.js",
  "Chrome MV3 vẫn phải giữ background.service_worker",
);

for (const script of manifest.background.scripts) {
  assert.ok(fs.existsSync(path.join(root, script)), `Không tìm thấy background script: ${script}`);
}
assert.ok(
  fs.existsSync(path.join(root, manifest.background.service_worker)),
  `Không tìm thấy service worker: ${manifest.background.service_worker}`,
);

const portalMatches = [
  "https://dichvucong.quangngai.gov.vn/*",
  "https://dichvucong.khanhhoa.gov.vn/*",
];
const contentMatches = new Set(manifest.content_scripts?.flatMap((entry) => entry.matches || []));
const resourceMatches = new Set(
  manifest.web_accessible_resources?.flatMap((entry) => entry.matches || []),
);
for (const match of portalMatches) {
  assert.ok(contentMatches.has(match), `Content script chưa được phép chạy tại: ${match}`);
  assert.ok(resourceMatches.has(match), `Popup resource chưa được phép tải tại: ${match}`);
}

// Mọi file khai trong manifest phải tồn tại thật (thêm content script mà quên file = hỏng im lặng).
const isolatedEntry = manifest.content_scripts.find((entry) => !entry.world);
for (const file of isolatedEntry.js) {
  assert.ok(fs.existsSync(path.join(root, file)), `Không tìm thấy content script: ${file}`);
}

// popup.js tự inject lại content script khi tab chưa có (sendToContent). Hai danh sách phải KHỚP,
// nếu không thì tính năng chỉ chạy ở tab mới mở mà chết ở tab đang mở sẵn.
const popupSource = fs.readFileSync(path.join(root, "popup.js"), "utf8");
// Lấy đúng lô isolated-world (lô chứa content.js), bỏ qua lô MAIN-world đứng trước.
const injectedLists = [...popupSource.matchAll(/files: \[([^\]]+)\]/g)]
  .map((m) => (m[1].match(/"([^"]+)"/g) || []).map((s) => s.slice(1, -1)))
  .filter((list) => list.includes("content.js"));
assert.equal(injectedLists.length, 1, "popup.js phải có đúng 1 danh sách inject content script");
const injectedFiles = injectedLists[0];
assert.deepEqual(
  injectedFiles,
  isolatedEntry.js,
  "Danh sách inject trong popup.js lệch với manifest.content_scripts",
);

console.log("manifest: Firefox background.scripts + Chrome service_worker + inject list passed");
