const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const worker = fs.readFileSync(path.join(root, "content/split-attach.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

assert.match(sidebar, /SPLIT_ATTACH_PROCEDURES = new Set\(\["chung-thuc-ban-sao", "chung-thuc-chu-ky"\]\)/);
assert.match(sidebar, /a\.mode === "split" && supportsSplitAttach\(a\.procedure\)/);
assert.match(sidebar, /buildSignatureSplitBundles/);
assert.match(sidebar, /action: "getDossierUrl"/);
assert.match(sidebar, /itemsStorageKey: SPLIT_STAGE_KEY/);
assert.match(
  sidebar,
  /monitorSplitQueue\(queueId, bundles\.length, a\.dispatch_id \|\| ""\)/,
  "split queue phải giữ cùng dispatch id để heartbeat/report gia hạn đúng action",
);
assert.match(sidebar, /__action:attach_report/);
assert.doesNotMatch(sidebar, /openDossierTabAndAttach/);

const openStart = background.indexOf("async function openNextSplitQueueItemUnlocked");
const openEnd = background.indexOf("async function finishSplitQueueTabUnlocked", openStart);
const open = background.slice(openStart, openEnd);
assert.ok(open.indexOf('chrome.tabs.create({ url: "about:blank", active: true })') >= 0);
assert.ok(open.indexOf("await setPendingMap(pending)") < open.indexOf("await chrome.tabs.update"));
assert.match(background, /getSplitAttachQueueStatus/);
assert.match(background, /status = "done"/);

assert.match(worker, /window\.top !== window/);
assert.match(worker, /document\.hidden/);
assert.match(worker, /H\.attachFilesByPlan\(files, attachments/);
assert.match(worker, /action: ok \? "clearPendingAttach" : "failPendingAttach"/);
assert.match(worker, /MAX_RELOADS_PER_CODE = 3/);

const scripts = manifest.content_scripts[0].js;
assert.ok(scripts.indexOf("content/split-attach.js") > scripts.indexOf("content/attach-core.js"),
  "split worker phải nạp sau attach-core");
console.log("TLND split FE-BE contract passed");
