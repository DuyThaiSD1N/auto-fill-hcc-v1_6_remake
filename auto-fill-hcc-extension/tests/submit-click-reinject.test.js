// Popup nạp lại content.js vào trang đang mở khi trang chưa trả lời kịp (cổng chậm/treo). Mỗi lần nạp chạy lại khối
// nghe cú bấm Gửi hồ sơ → trước đây cộng thêm một bộ nghe, MỘT cú bấm thành nhiều mốc nộp (hồ sơ báo 25 lần nộp).
// Chạy THẬT khối đó trong vm, nạp nhiều lần trên cùng một document.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = src.indexOf("    const onSubmitClick = (e) => {");
const endMarker = 'document.addEventListener("click", onSubmitClick, true);';
const snippet = src.slice(start, src.indexOf(endMarker, start) + endMarker.length);

function fakePage() {
  const listeners = new Set();
  const document = {
    addEventListener: (type, fn) => { if (type === "click") listeners.add(fn); },
    removeEventListener: (type, fn) => { if (type === "click") listeners.delete(fn); },
  };
  const sent = [];
  const window = {};
  const button = { id: "kt_gui-ho-so", tagName: "BUTTON", textContent: "Gửi hồ sơ", closest: () => button };
  const inject = () => vm.runInContext(`(() => {
    let lastSubmitClickAt = 0;
    const submitRules = { "dichvucongnganhtuphap.moj.gov.vn": { urlPattern: "^/nop-ho-so/(\\\\d+)$",
      buttonIds: ["kt_gui-ho-so"], buttonText: ["gui ho so"] } };
    const SUBMIT_CLICKABLE = "button";
    const foldSubmitLabel = (s) => String(s || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
    const rememberPendingSubmit = () => {};
    const sendSubmitClick = (click) => sent.push(click);
    ${snippet}
  })();`, ctx);
  const ctx = vm.createContext({
    window, document, sent, Date, Math, RegExp, String,
    location: { hostname: "dichvucongnganhtuphap.moj.gov.vn", pathname: "/nop-ho-so/148996", hash: "" },
    crypto: { randomUUID: () => `c-${sent.length}-${Math.random()}` },
  });
  return { inject, sent, listeners, click: () => [...listeners].forEach((fn) => fn({ target: button })) };
}

test("nạp lại content.js nhiều lần: một cú bấm Gửi hồ sơ vẫn chỉ một mốc nộp", () => {
  const page = fakePage();
  for (let i = 0; i < 4; i++) page.inject();
  assert.equal(page.listeners.size, 1);
  page.click();
  assert.equal(page.sent.length, 1);
});

test("vòng dò chữ nộp thành công cũng gỡ bản của lần nạp trước", () => {
  assert.match(src, /clearInterval\(window\.__AUTOFILL_HCC_SUBMIT_SEEN_TIMER__\)[\s\S]{0,80}window\.__AUTOFILL_HCC_SUBMIT_SEEN_TIMER__ = setInterval/);
});
