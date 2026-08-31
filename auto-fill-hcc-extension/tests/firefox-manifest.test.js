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

console.log("manifest: Firefox background.scripts + Chrome service_worker passed");
