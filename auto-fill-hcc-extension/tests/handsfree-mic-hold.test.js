const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");

// Chạy thật hàm micHeld với trạng thái giả (hàm chỉ đọc biến của sidebar).
function micHeld(vars) {
  const src = sidebar.match(/function micHeld\(\) \{[\s\S]*?\n  \}/)[0];
  const names = ["lastState", "loginPageNow", "docsReceived", "uploadsInFlight", "docsChangedAt", "DOCS_SETTLE_MS"];
  // eslint-disable-next-line no-new-func
  return new Function(...names, `${src}; return micHeld();`)(...names.map((n) => vars[n]));
}
const base = { loginPageNow: false, docsReceived: false, uploadsInFlight: 0, docsChangedAt: 0, DOCS_SETTLE_MS: 5000 };

test("rảnh tay: mic nghỉ ở trang đăng nhập, rời trang đăng nhập thì mở lại", () => {
  assert.equal(micHeld({ ...base, lastState: "guide_login", loginPageNow: true }), true);
  assert.equal(micHeld({ ...base, lastState: "guide_login", loginPageNow: null }), true, "chưa đọc được trang → nghỉ cho chắc");
  assert.equal(micHeld({ ...base, lastState: "guide_login", loginPageNow: false }), false);
});

test("rảnh tay: bước scan / QR nghỉ tới khi có tệp, hết đợt đang tải và ~5 giây không có tệp mới", () => {
  const docs = { ...base, lastState: "collecting_docs" };
  assert.equal(micHeld({ ...docs, docsReceived: false }), true);
  assert.equal(micHeld({ ...docs, docsReceived: true, uploadsInFlight: 1, docsChangedAt: 0 }), true);
  assert.equal(micHeld({ ...docs, docsReceived: true, docsChangedAt: Date.now() }), true, "tệp vừa về, máy quét còn trả tờ sau");
  assert.equal(micHeld({ ...docs, docsReceived: true, docsChangedAt: Date.now() - 6000 }), false);
  assert.equal(micHeld({ ...base, lastState: "qr_waiting" }), true);
});

test("các bước khác không bị ảnh hưởng", () => {
  for (const state of ["greet", "ask_doc_method", "reviewing", "attaching", "done", "owner_waiting_next"]) {
    assert.equal(micHeld({ ...base, lastState: state }), false, state);
  }
});

test("mọi đường tự mở mic đều xét micHeld; đang nghe mà vào bước nghỉ thì tắt, trừ khi công dân tự bấm mic", () => {
  assert.match(sidebar, /function micWanted\(\) \{[\s\S]*?&& !micHeld\(\)/);
  assert.match(sidebar, /function listenWhenQuiet\(\) \{\s*if \(.*\|\| micHeld\(\)\) \{/);
  assert.match(sidebar, /if \(voiceListening && !micByHand && micHeld\(\)\) \{\s*pauseMic\(\)/);
  assert.match(sidebar, /else \{ micByHand = true; startVoice\(\); \}/);
  assert.match(sidebar, /loginPageNow = !!ctx\.loginPage;/);
  assert.match(sidebar, /uploadsInFlight \+= 1;[\s\S]*?finally \{\s*uploadsInFlight = Math\.max\(0, uploadsInFlight - 1\);/);
});
