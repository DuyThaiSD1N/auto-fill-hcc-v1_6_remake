const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const changelogSource = fs.readFileSync(path.join(root, "changelog.js"), "utf8");
const sandbox = {};
vm.runInNewContext(`${changelogSource}\nglobalThis.releases = APP_RELEASES;`, sandbox);

assert.equal(manifest.version, "1.15");
assert.match(content, /const APP_VERSION_LABEL = "1\.15 · 27\/8"/);
assert.equal(sandbox.releases[0].version, manifest.version);
assert.equal(sandbox.releases[0].date, "27/8/2026");
assert.ok(sandbox.releases[0].items.length >= 5, "Changelog 1.15 phải mô tả đủ nhóm thay đổi chính");

console.log("release version: manifest, panel label and changelog 1.15 are consistent");
