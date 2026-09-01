const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");
const attachCore = fs.readFileSync(path.join(__dirname, "..", "content", "attach-core.js"), "utf8");

assert.match(sidebar, /action:\s*"collectAttachmentContext"/);
assert.match(sidebar, /attachment_context:\s*attachmentResult\?\.attachmentContext\s*\|\|\s*\{\}/);
assert.match(sidebar, /supportsSourceSegments:\s*true/);
assert.match(sidebar, /supportsAttachmentContext:\s*true/);
assert.match(attachCore, /attachmentContext:\s*collectAttachmentContext\(\)/);
assert.match(attachCore, /url:\s*location\.href/);
assert.match(attachCore, /hasAttachmentTableHeader/);
assert.match(attachCore, /"ten thanh phan ho so", "dinh kem tep tin"/);
assert.match(attachCore, /hasFileControl:\s*rows\.some/);
