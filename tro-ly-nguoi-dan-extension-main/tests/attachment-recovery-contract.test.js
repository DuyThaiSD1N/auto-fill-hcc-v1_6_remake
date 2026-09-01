const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("mọi câu lệnh gửi kèm page context đang mở", () => {
  assert.match(sidebar, /sendToContent\(\{ action: "getPageContext" \}\)/);
  assert.match(sidebar, /page_context:\s*\{[\s\S]*\.\.\.docsCompletePagePayload\(effectivePageResult\)/);
});

test("watcher không hết hạn cục bộ ở bất kỳ chặng chuyển trang nào", () => {
  assert.doesNotMatch(sidebar, /watcherTicks\s*>\s*60/);
  assert.match(sidebar, /if \(!isWatchedState\(\)\)/);
  for (const state of [
    "guide_login",
    "ask_doc_method",
    "qr_waiting",
    "collecting_docs",
    "owner_waiting_next",
    "attaching",
    "done",
    "filling",
  ]) {
    assert.match(sidebar, new RegExp(`"${state}"`));
  }
});

test("trang đính kèm vẫn được probe lại để phục hồi event bị mất", () => {
  assert.match(sidebar, /const attachRecoveryProbe = lastState === "attaching"/);
  assert.match(sidebar, /watcherTicks % 5 === 0/);
});

test("action đính kèm có dispatch id, ACK và heartbeat để lease không kẹt", () => {
  assert.match(sidebar, /a\.dispatch_id/);
  assert.match(sidebar, /sendAttachLeaseSignal\("attach_started"/);
  assert.match(sidebar, /sendAttachLeaseSignal\("attach_heartbeat"/);
  assert.match(sidebar, /dispatch_id:\s*dispatchId/);
});

test("WebSocket tự nối lại và phiên upload được khôi phục sau reload", () => {
  assert.match(sidebar, /ws\.onclose = \(\) =>/);
  assert.match(sidebar, /uploadWsReconnectTimer = setTimeout\(connect, delay\)/);
  assert.match(sidebar, /if \(conv\.upload_session_id\)/);
  assert.match(sidebar, /subscribeUploadSession\(conv\.upload_session_id\)/);
});
