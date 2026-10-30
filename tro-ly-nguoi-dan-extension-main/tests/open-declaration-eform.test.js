// Tờ khai nằm trong bảng Thành phần hồ sơ (nuôi con nuôi dòng 5): trợ lý tự bấm "Khai tờ khai" ĐÚNG dòng.
// Chạy thật content/guided-steps.js trong vm với DOM giả: bảng có dòng 5 (đơn xin nhận con nuôi) và dòng 6 (đơn đăng ký
// nhu cầu) — mỗi dòng hai nút như cổng thật (bố cục điện thoại ẩn + máy tính hiện).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");

function makeDom() {
  const clicks = [];
  const rows = [5, 6].map((stt) => {
    const tr = {
      textContent: stt === 5 ? "5 - Đơn xin nhận con nuôi Bắt buộc Khai tờ khai" : "6 - Đơn đăng ký nhu cầu Khai tờ khai",
      querySelector: (sel) => (sel === "td" ? { textContent: String(stt) } : null),
    };
    return tr;
  });
  const button = (tr, visible) => ({
    textContent: "Khai tờ khai",
    offsetParent: visible ? {} : null,
    closest: (sel) => (sel === "tr" ? tr : null),
    scrollIntoView() {},
    dispatchEvent(ev) { if (ev.type === "click") clicks.push(tr); return true; },
    click() { clicks.push(tr); },
    focus() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 10, height: 10 }),
  });
  const buttons = rows.flatMap((tr) => [button(tr, false), button(tr, true)]);
  const document = {
    querySelectorAll: (sel) => (sel === "button" ? buttons : []),
    querySelector: () => null,
    addEventListener() {}, dispatchEvent() {},
  };
  return { document, clicks, rows };
}

function load(dom) {
  const listeners = [];
  const Ev = function (type) { this.type = type; };
  const ctx = vm.createContext({
    window: { __TLND__: {} }, document: dom.document, console,
    chrome: { runtime: { onMessage: { addListener: (fn) => listeners.push(fn) }, sendMessage() {} } },
    setInterval() { return 0; }, setTimeout, clearTimeout,
    MouseEvent: Ev, PointerEvent: Ev, KeyboardEvent: Ev, Event: Ev,
  });
  vm.runInContext(read("content/guided-steps.js"), ctx);
  return (msg) => {
    let out;
    for (const fn of listeners) {
      fn(msg, {}, (res) => { out = res; });
      if (out) break;
    }
    return out && JSON.parse(JSON.stringify(out)); // object tạo trong vm khác prototype → so qua JSON

  };
}

test("bấm đúng nút Khai tờ khai của dòng tờ khai (theo STT), không bấm dòng 6", () => {
  const dom = makeDom();
  const send = load(dom);
  assert.deepEqual(send({ action: "openDeclarationEform", row: 5, label: "Đơn xin nhận con nuôi" }), { ok: true, clicked: true });
  assert.ok(dom.clicks.length >= 1 && dom.clicks.every((tr) => tr === dom.rows[0]));
});

test("không khớp STT thì theo tên tờ khai; không có dòng nào khớp thì báo không bấm được", () => {
  const dom = makeDom();
  const send = load(dom);
  assert.deepEqual(send({ action: "openDeclarationEform", row: 9, label: "Đơn xin nhận con nuôi" }), { ok: true, clicked: true });
  assert.ok(dom.clicks.every((tr) => tr === dom.rows[0]));
  const dom2 = makeDom();
  assert.deepEqual(load(dom2)({ action: "openDeclarationEform", row: 9, label: "giấy tờ khác" }), { ok: false, clicked: false });
  assert.equal(dom2.clicks.length, 0);
});

test("sidebar: khai cờ, mở xong chờ ĐÚNG mẫu rồi mới gửi lệnh điền; không mở được thì báo BE", () => {
  const sidebar = read("sidebar.js");
  assert.match(sidebar, /supportsOpenEform: true,/);
  assert.match(sidebar, /a\.type === "open_eform"\) \{\s*setTimeout\(\(\) => \{ void runOpenEform\(a\); \}, 0\);/);
  const fn = sidebar.match(/async function runOpenEform\(a\) \{[\s\S]*?\n  \}/)[0];
  assert.match(fn, /action: "openDeclarationEform", row: a\.row/);
  assert.match(fn, /formContext\?\.formVariant === a\.variant/);
  assert.match(fn, /if \(opened\) await ask\("__action:fill_eform", "system"\);/);
  assert.match(fn, /__event:eform_open_failed:/);
  // Mở sẵn lúc vừa tới bước (fill:false): mở xong để đó, không gửi lệnh điền / báo lỗi trước khi có giấy tờ.
  assert.match(fn, /if \(a\.fill === false\) return;\s*if \(opened\) await ask\("__action:fill_eform"/);
});
