const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("extension công bố contract chốt giấy tờ theo trang hiện tại", () => {
  assert.match(sidebar, /supportsPageBoundDocsComplete:\s*true/);
  assert.match(sidebar, /function docsCompletePagePayload\(ctx\)/);
  assert.match(sidebar, /pageContextCaptured:\s*!!ctx\?\.ok/);
  assert.match(sidebar, /wizardStep:\s*Number\(ctx\?\.wizardStep\) \|\| 0/);
  assert.match(sidebar, /declarationTarget:\s*!!ctx\?\.declarationTarget/);
  assert.match(sidebar, /attachmentTarget:\s*!!ctx\?\.attachmentTarget/);
  assert.match(sidebar, /attachmentComponentCount:\s*Array\.isArray/);
  assert.match(sidebar, /attachmentResult\?\.attachmentContext\?\.components/);
  assert.match(sidebar, /attachmentResult\.attachmentContext\.components\.length/);
});

test("nút chốt và WebSocket complete đều đọc lại page context trước khi gọi backend", () => {
  assert.match(sidebar, /submitDocsComplete\(c\.send, "chip", c\.label\)/);
  assert.match(sidebar, /submitDocsComplete\("__event:docs_complete", "system"\)/);
  assert.match(sidebar, /ask\(`\$\{command\}:\$\{JSON\.stringify\(payload\)\}`/);
});

test("watcher theo dõi đổi bước khi đang chọn hoặc tải giấy tờ", () => {
  for (const state of ["ask_doc_method", "qr_waiting", "collecting_docs"]) {
    assert.match(sidebar, new RegExp(`"${state}"`));
  }
  assert.match(sidebar, /watchesDocsTarget/);
  assert.match(sidebar, /a\.type === "update_docs_done_chip"/);
  assert.match(sidebar, /updateDocsDoneChipLabel\(a\.label,\s*a\.labelHmong\)/);
});

test("đổi bước mà hỏi lại thì lời hỏi cũ bị gỡ khỏi khung chat", () => {
  // Gỡ phải chạy TRƯỚC khi dựng lời hỏi mới, nếu không xoá luôn cái vừa dựng —
  // vì vậy đọc action ngay trong renderReply chứ không đợi runActions.
  assert.match(sidebar, /a\.type === "drop_stale_ask" && a\.tag === "doc_method"/);
  assert.match(sidebar, /function dropStaleDocMethodAsk\(\)/);
  assert.match(sidebar, /querySelectorAll\('\[data-ask="doc-method"\]'\)/);
  // Cả bong bóng mở đầu lẫn thẻ QR/Scan đều phải mang mốc, gỡ nửa vời là còn lại rác.
  assert.match(sidebar, /\$botBubble\.dataset\.ask = "doc-method"/);
  assert.match(sidebar, /el\.dataset\.ask = "doc-method"/);
});
