// Trang hộ tịch mới nộp xong KHÔNG chuyển trang, chỉ hiện toast "Gửi hồ sơ thành công" vài giây.
// content.js theo dõi DOM để bắt ngay và giữ dấu tới khi sidebar báo đã nhận; sidebar báo "đã nộp"
// ở mọi bước khi BE cho phép (submit_anywhere). Chạy THẬT đoạn bắt toast trong vm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

const fold = content.slice(content.indexOf("  const foldLabel = (s) =>"), content.indexOf("  function matchSubmitClick(el)"));
const toast = content.slice(content.indexOf("  let submitToastAt = 0;"), content.indexOf("  // Capture-phase: cổng có thể stopPropagation"));

function page(pathname = "/nop-ho-so") {
  let observer = null;
  const ctx = vm.createContext({
    IS_TOP_FRAME: true, Date, RegExp, String,
    submitRules: { "dichvucong.gov.vn": { urlPattern: "^/nop-ho-so$", buttonText: ["luu va nop ho so"] } },
    location: { hostname: "dichvucong.gov.vn", pathname, hash: "" },
    document: { documentElement: {} },
    MutationObserver: class { constructor(cb) { observer = cb; } observe() {} },
  });
  vm.runInContext(`${fold}\n${toast}\nthis.api = { seen: () => submitToastAt, ack: () => { submitToastAt = 0; } };`, ctx);
  const add = (text) => observer([{ type: "childList", addedNodes: [{ nodeType: 1, textContent: text }] }]);
  return { api: ctx.api, add };
}

test("toast hiện là giữ dấu ngay, tắt rồi vẫn còn dấu tới khi sidebar xác nhận", () => {
  const p = page();
  p.add("Đang lưu…");
  assert.equal(p.api.seen(), 0);
  p.add("Gửi hồ sơ thành công");
  assert.ok(p.api.seen() > 0);
  p.add(""); // toast tắt
  assert.ok(p.api.seen() > 0);
  p.api.ack();
  assert.equal(p.api.seen(), 0, "hồ sơ kế tiếp trên cùng trang phải bắt lại từ đầu");
});

test("sai trang nộp hoặc khối chữ lớn (cả form dựng lại) thì không tính", () => {
  const other = page("/ho-so-cua-toi");
  other.add("Gửi hồ sơ thành công");
  assert.equal(other.api.seen(), 0);
  const p = page();
  p.add("Gửi hồ sơ thành công " + "x".repeat(500));
  assert.equal(p.api.seen(), 0);
});

test("trang trả dấu toast cho watcher; sidebar xác nhận lại để xoá dấu", () => {
  assert.match(content, /submittedToast: !!submitToastAt,/);
  assert.match(content, /msg\?\.action === "ackSubmitToast" && IS_TOP_FRAME\) \{\s*submitToastAt = 0;/);
});

test("sidebar: khai cờ luồng tự động; toast báo ở mọi bước CHỈ khi BE cho phép", () => {
  assert.match(sidebar, /supportsTpmAutoFlow: true,/);
  assert.match(sidebar, /\(lastState === "done" && \(ctx\.submitted \|\| ctx\.submittedToast\)\)\s*(\/\/[^\n]*\n\s*)*\|\| \(ctx\.submittedToast && lastReplyData\?\.submit_anywhere\)/);
  assert.match(sidebar, /if \(ctx\.submittedToast\) void sendToContent\(\{ action: "ackSubmitToast" \}\);\s*ask\("__event:submitted", "system"\);/);
});
