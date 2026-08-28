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
  // Cổng đăng ký doanh nghiệp qua mạng: thiếu match là panel không mount và luồng tự tiến tới
  // thủ tục thành lập doanh nghiệp im lặng không chạy.
  "https://dangkyquamang.dkkd.gov.vn/*",
];
const contentMatches = new Set(manifest.content_scripts?.flatMap((entry) => entry.matches || []));
const resourceMatches = new Set(
  manifest.web_accessible_resources?.flatMap((entry) => entry.matches || []),
);
for (const match of portalMatches) {
  assert.ok(contentMatches.has(match), `Content script chưa được phép chạy tại: ${match}`);
  assert.ok(resourceMatches.has(match), `Popup resource chưa được phép tải tại: ${match}`);
}

// Khai trong manifest mà quên thêm file (hoặc đổi tên) thì Chrome bỏ qua CẢ khối content_scripts.
for (const entry of manifest.content_scripts || []) {
  for (const file of [...(entry.js || []), ...(entry.css || [])]) {
    assert.ok(fs.existsSync(path.join(root, file)), `Không tìm thấy content script: ${file}`);
  }
}

// popup.sendToContent re-inject content script khi tab đang mở chưa có bản mới (hay gặp ngay sau khi
// reload extension). Danh sách đó PHẢI khớp manifest: thiếu một file thì tab vừa re-inject chạy thiếu
// tính năng một cách IM LẶNG — panel vẫn hiện nên rất khó lần ra (đã từng mất nhận diện thủ tục ở cổng
// ĐKKD qua mạng vì thiếu content/procedures/enterprise-registration.js).
const popupSource = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const injectMatch = popupSource.match(/files: \[("api\/config\.js"[\s\S]*?)\],/);
assert.ok(injectMatch, "Không tách được danh sách re-inject trong popup.sendToContent");
const injected = JSON.parse(`[${injectMatch[1]}]`);
const isolatedEntry = (manifest.content_scripts || []).find((entry) => entry.world !== "MAIN");
assert.deepEqual(
  injected,
  isolatedEntry.js,
  "Danh sách re-inject của popup.sendToContent phải khớp content_scripts.js trong manifest.json",
);

console.log("manifest: Firefox background.scripts + Chrome service_worker passed");
