// Chạy THẬT script của trang điện thoại Auto Fill (render_mobile_page) với DOM + XHR giả.
// argv[2] = file JS của trang, argv[3] = kịch bản. In JSON kết quả ra stdout.
const fs = require("node:fs");
const vm = require("node:vm");

const src = fs.readFileSync(process.argv[2], "utf8");
const scenario = process.argv[3];

function el() {
  return {
    textContent: "", innerHTML: "", disabled: false, hidden: false, className: "", src: "", title: "",
    style: {}, children: [], classList: { add() {}, remove() {} },
    append(...c) { this.children.push(...c); }, appendChild(c) { this.children.push(c); },
    addEventListener(t, fn) { (this.on ||= {})[t] = fn; }, click() { this.on?.click?.(); },
    getContext() { return { drawImage() {} }; },
  };
}
const els = {};
const document = {
  getElementById: (id) => (els[id] ||= el()),
  createElement: () => el(),
  addEventListener() {}, head: el(), visibilityState: "visible",
};

const requests = [];
let active = 0, maxActive = 0;
const plan = { fail: new Map() }; // tên tệp -> số lần lỗi mạng trước khi thành công; -1 = 413
if (scenario === "retry") plan.fail.set("b.pdf", 1);
if (scenario === "reject") plan.fail.set("b.pdf", -1);
const hang = new Set(scenario === "stall" ? ["b.pdf"] : []); // lần đầu treo, không nhích byte nào

class FakeXHR {
  constructor() { this.upload = {}; this.headers = {}; }
  open(m, url) { this.url = url; }
  setRequestHeader(k, v) { this.headers[k] = v; }
  abort() { this.onabort?.(); }
  send(fd) {
    const file = fd.get("files");
    const req = { name: file.name, key: fd.get("client_key"), url: this.url, token: this.headers["X-Upload-Token"] };
    requests.push(req);
    active += 1; maxActive = Math.max(maxActive, active);
    if (hang.delete(file.name)) { this.onabort = ((orig) => () => { active -= 1; orig?.(); })(this.onabort); return; }
    setTimeout(() => {
      this.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 100 });
      setTimeout(() => {
        active -= 1;
        const left = plan.fail.get(file.name);
        if (left === -1) { this.status = 413; this.responseText = JSON.stringify({ detail: "Ảnh quá nặng." }); return this.onload(); }
        if (left > 0) { plan.fail.set(file.name, left - 1); return this.onerror(); }
        this.upload.onload?.();
        this.status = 200;
        this.responseText = JSON.stringify({ accepted: [{ fid: "f-" + file.name }], received: requests.filter((r) => r.ok).length + 1 });
        req.ok = true;
        this.onload();
      }, 5);
    }, 5);
  }
}

class FD { constructor() { this.m = {}; } append(k, v, name) { this.m[k] = name ? { ...v, name } : v; } get(k) { return this.m[k]; } }

const ctx = {
  document, window: { isSecureContext: false, addEventListener() {} }, navigator: {},
  location: { hash: "#token=TK", protocol: "https:", host: "x" }, URLSearchParams, console,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  XMLHttpRequest: FakeXHR, FormData: FD, WebSocket: function () {},
  // Hẹn giờ "treo 30s / chờ trả lời 60s" không được nổ trong test; chờ gửi lại (1,5s…) rút về 5ms.
  setTimeout: (fn, ms) => (scenario === "stall" && ms === 30000 ? setTimeout(fn, 30) : ms >= 10000 ? setTimeout(fn, 1e7).unref() : setTimeout(fn, Math.min(ms, 5))), clearTimeout, Promise, JSON, Math, Number, String, Date, Array,
  crypto: { randomUUID: (() => { let i = 0; return () => "k" + (++i); })() },
  Image: class { set src(_) { setTimeout(() => this.onload?.(), 0); } },
};
ctx.window.crypto = ctx.crypto;
ctx.window.addEventListener = () => {};
vm.createContext(ctx);
vm.runInContext(src, ctx);

const pdf = (name) => ({ name, type: "application/pdf", size: 100 });
els.pdf.on.change({ target: { files: [pdf("a.pdf"), pdf("b.pdf"), pdf("c.pdf")], value: "" } });

(async () => {
  els.sendBtn.click();
  await new Promise((r) => setTimeout(r, 400));
  if (scenario === "reject") {
    // Gửi lại: chỉ tệp còn trong khay đi tiếp
    requests.length = 0;
    plan.fail.delete("b.pdf");
    els.sendBtn.click();
    await new Promise((r) => setTimeout(r, 200));
  }
  console.log(JSON.stringify({ requests, maxActive, stat: els.stat.textContent, count: els.count.textContent,
    sendBtn: els.sendBtn.textContent }));
})();
