const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Guard phát hành: manifest, nhãn phiên bản trên header panel và changelog phải khớp nhau.
// SUY RA từ manifest chứ không ghim số cụ thể — bản trước ghim "1.15" nên test tự hỏng ngay khi
// lên 1.16 và không còn bắt được lỗi lệch thật.
const root = path.join(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const changelogSource = fs.readFileSync(path.join(root, "changelog.js"), "utf8");
const sandbox = {};
vm.runInNewContext(`${changelogSource}\nglobalThis.releases = APP_RELEASES;`, sandbox);

const latest = sandbox.releases[0];
assert.equal(latest.version, manifest.version, "Mục changelog đầu tiên phải là phiên bản trong manifest");

// Nhãn panel dạng "<version> · <ngày/tháng>". Số đọc từ manifest LÚC CHẠY (gõ tay từng trôi thật) nên
// không thể lệch; chỉ còn ngày ghi tay — phải trùng phần ngày/tháng của changelog.
assert.match(
  content,
  /const APP_VERSION_LABEL = [\s\S]{0,300}?chrome\.runtime\.getManifest\(\)\.version/,
  "Nhãn phiên bản ở header panel phải đọc số từ manifest",
);
const dateMatch = /const APP_RELEASE_DATE = "([^"]+)"/.exec(content);
assert.ok(dateMatch, "content.js phải khai báo APP_RELEASE_DATE");
const labelDate = dateMatch[1];

const [d, m] = latest.date.split("/");
assert.equal(labelDate, `${d}/${m}`, "Ngày trên header panel lệch ngày changelog");

assert.ok(Array.isArray(latest.items) && latest.items.length >= 1, "Changelog phải mô tả thay đổi");
assert.ok(latest.items.every((it) => typeof it === "string" && it.trim()), "Mục changelog không được rỗng");

console.log(`release version: manifest, panel label and changelog ${manifest.version} are consistent`);
