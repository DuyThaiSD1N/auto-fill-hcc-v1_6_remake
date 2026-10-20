// WS phiên giấy tờ đứt rồi nối lại: sự kiện phát lúc đứt không được gửi lại → phải đọc lại tiến độ
// phiên, và bù `docs_complete` nếu điện thoại đã chốt trong lúc đứt mà hội thoại vẫn chờ giấy tờ.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const js = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");
const fn = js.slice(js.indexOf("function subscribeUploadSession(sid)"), js.indexOf("connect();\n  }", js.indexOf("function subscribeUploadSession(sid)")));

test("chỉ đồng bộ lại ở lần NỐI LẠI, không phải lần mở đầu", () => {
  assert.match(fn, /if \(everOpened\) \{\s*void resyncAfterReconnect\(\);[\s\S]*?\}\s*everOpened = true;/);
  assert.match(fn, /let everOpened = false;/);
});

test("đồng bộ lại = đọc lại phiên (vẽ lại tiến độ + mở khoá nút) và kéo ngầm tệp mới", () => {
  const r = fn.slice(fn.indexOf("async function resyncAfterReconnect()"), fn.indexOf("function scheduleReconnect()"));
  assert.match(r, /generation !== uploadWsGeneration \|\| sid !== uploadSid\) return;/);
  assert.match(r, /data = await loadUploadSessionFiles\(\);/);
  assert.match(r, /void prefetchSessionFiles\(uploadSid\);/);
});

test("bù docs_complete chỉ khi phiên đã chốt, có tệp, chưa gửi, và hội thoại còn chờ giấy tờ", () => {
  const r = fn.slice(fn.indexOf("async function resyncAfterReconnect()"), fn.indexOf("function scheduleReconnect()"));
  assert.match(r, /if \(p\.complete && got > 0 && !completeSent\s*&& \["qr_waiting", "collecting_docs"\]\.includes\(lastState\)\) \{\s*completeSent = true;\s*void submitDocsComplete\("__event:docs_complete", "system"\);/);
});

test("loadUploadSessionFiles vẽ lại tiến độ từ phiên (nguồn của việc mở khoá nút Đã đưa đủ)", () => {
  assert.match(js, /if \(data\?\.progress\) renderDocProgress\(data\.progress, \{ preserveScroll: true \}\);/);
});
