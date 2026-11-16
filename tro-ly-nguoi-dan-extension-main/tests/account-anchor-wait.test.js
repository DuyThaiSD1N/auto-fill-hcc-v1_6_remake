// Tờ khai tư pháp form cũ: sidebar báo khối người yêu cầu đã có dữ liệu tài khoản chưa (taiKhoan) để BE chờ có mốc
// tài khoản rồi mới chạy lượt trích ở bước Kê khai.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const raw = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");
const src = raw.replace(/^\s*\/\/.*$/gm, "");

function anchorState() {
  const start = raw.indexOf("const ACCOUNT_ANCHOR_WAIT_MS");
  const end = raw.indexOf("async function readPageContext()");
  let now = 0;
  const fn = new Function("Date", `${raw.slice(start, end)}; return accountAnchorState;`)({ now: () => now });
  return { fn, tick: (ms) => { now += ms; } };
}

test("trạng thái khối người yêu cầu: không tờ khai / có tài khoản / đang chờ / chờ quá lâu", () => {
  const { fn, tick } = anchorState();
  assert.equal(fn(null), "");
  assert.equal(fn({ formContext: { applicantFullname: "" } }), "cho");
  tick(4000);
  assert.equal(fn({ formContext: {} }), "cho");
  assert.equal(fn({ formContext: { applicantIdentityNumber: "001000000001" } }), "co");
  assert.equal(fn({ formContext: {} }), "cho");
  tick(10000);
  assert.equal(fn({ formContext: {} }), "khong");
});

test("khai cờ, đưa taiKhoan vào chữ ký watcher, page_status và page_context", () => {
  assert.match(src, /supportsAccountAnchorWait: true,/);
  assert.match(src, /\|\$\{ctx\.taiKhoan \|\| ""\}\|\$\{ctx\.lienThongHome \? 1 : 0\}`;/);
  assert.match(src, /taiKhoan: String\(c\.taiKhoan \|\| ""\),/);
  assert.match(src, /taiKhoan: String\(ctx\?\.taiKhoan \|\| ""\),/);
  assert.match(src, /taiKhoan: accountAnchorState\(formResult\),/);
  assert.match(src, /sendToContent\(\{ action: "collectFormContext" \}\),\s*\]\);\s*if \(ctx && typeof ctx === "object"\) ctx\.taiKhoan = accountAnchorState\(form\);/);
});
